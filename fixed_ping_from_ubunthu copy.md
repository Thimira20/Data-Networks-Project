# Docker Connectivity Fix — Root Cause Analysis & Solution

## Your Test Results

| Destination | IP          | Result         | Root Cause                                                     |
| ----------- | ----------- | -------------- | -------------------------------------------------------------- |
| SW-Core     | 10.99.99.1  | ✅ Works       | Same L2 VLAN 99 segment — direct delivery                      |
| SW-D-DEIE   | 10.99.99.11 | ❌ Unreachable | **VLAN 99 L2 split** — different L2 island after L3 conversion |
| R-CORE      | 10.0.0.2    | ❌ Filtered    | **ACL blocks ICMP** — only SSH (TCP 22) is permitted           |
| R-EDGE      | 10.0.1.2    | ❌ Filtered    | **ACL blocks ICMP** — only SSH (TCP 22) is permitted           |

There are **two separate problems**. Let me explain each.

---

## Problem 1: R-CORE and R-EDGE Show "Filtered" (ACL Issue)

### Why It Happens

Your `ACL-MGMT-IN` on SW-Core's VLAN 99 SVI controls what traffic can **leave** the management VLAN. Look at the rules:

```
permit tcp 10.99.99.0 0.0.0.255 10.0.0.0 0.0.0.255 eq 22   ← SSH only
permit tcp 10.99.99.0 0.0.0.255 10.0.1.0 0.0.0.255 eq 22   ← SSH only
...
permit icmp 10.99.99.0 0.0.0.255 host 10.10.40.100          ← ICMP to Zabbix only
permit icmp 10.99.99.0 0.0.0.255 10.99.99.0 0.0.0.255       ← ICMP within MGMT only
...
deny ip 10.99.99.0 0.0.0.255 any                             ← EVERYTHING ELSE DENIED
```

When Docker (10.99.99.100) pings R-CORE (10.0.0.2):

- **ICMP** packet enters VLAN 99 SVI → hits `ACL-MGMT-IN`
- No rule permits ICMP to `10.0.0.0/30` → falls through to `deny ip any` → **BLOCKED**
- The device sends back ICMP "administratively prohibited" → shows as **"filtered"**

> [!IMPORTANT]
> **Key insight: "Filtered" means the ACL is blocking ICMP (ping), but SSH (TCP 22) IS permitted by the ACL!** Your Netmiko scripts use SSH, not ping. So **Netmiko connections to R-CORE and R-EDGE should actually work** even though ping fails.

### Fix for Problem 1

Add ICMP permit rules to `ACL-MGMT-IN` for the router link subnets.

**On SW-Core:**

```
enable
configure terminal

ip access-list extended ACL-MGMT-IN
 ! Insert these BEFORE the deny rules (use sequence numbers)
 15 permit icmp 10.99.99.0 0.0.0.255 10.0.0.0 0.0.0.3
 16 permit icmp 10.99.99.0 0.0.0.255 10.0.1.0 0.0.0.3
 17 permit icmp 10.99.99.0 0.0.0.255 10.0.10.0 0.0.0.3
 18 permit icmp 10.99.99.0 0.0.0.255 10.0.20.0 0.0.0.3
 19 permit icmp 10.99.99.0 0.0.0.255 10.0.30.0 0.0.0.3
exit

end
write memory
```

> [!NOTE]
> If sequence numbers don't work on your IOSvL2, remove the entire ACL and re-create it with the new rules included. See Section "Full ACL Rebuild" at the bottom.

After this fix, `ping 10.0.0.2` and `ping 10.0.1.2` from Docker will **succeed**.

---

## Problem 2: SW-D-DEIE Shows "Unreachable" (VLAN 99 L2 Split)

This is the more serious problem. It's a **side effect of the L3 distribution switch conversion** that wasn't addressed at conversion time.

### Why It Happens

**Before L3 conversion** — VLAN 99 was one big L2 domain:

```
Docker ──(VLAN 99)── SW-Core ──(trunk)── SW-D-DEIE ──(trunk)── SW-A-DEIE
                     10.99.99.1            10.99.99.11            10.99.99.21
              All on the same L2 VLAN 99 broadcast domain
                     ARP works everywhere ✅
```

**After L3 conversion** — the trunks became routed links, splitting VLAN 99:

```
       ISLAND 1 (L2)                    ISLAND 2 (L2)
┌─────────────────────┐          ┌─────────────────────┐
│ Docker  10.99.99.100│          │ SW-D-DEIE 10.99.99.11│
│ SW-Core 10.99.99.1  │──ROUTED──│ SW-A-DEIE 10.99.99.21│
│ SW-A-DIS 10.99.99.24│ 10.0.10  │                     │
└─────────────────────┘  /30     └─────────────────────┘
  VLAN 99 is here           ↑         VLAN 99 is here too
  (separate L2 domain)      │         (separate L2 domain)
                     No trunk = no L2 bridge!
```

There are now **4 separate L2 islands** all using `10.99.99.0/24`:

| Island       | Devices                   | VLAN 99 IPs   |
| ------------ | ------------------------- | ------------- |
| 1: SW-Core   | SW-Core, SW-A-DIS, Docker | .1, .24, .100 |
| 2: SW-D-DEIE | SW-D-DEIE, SW-A-DEIE      | .11, .21      |
| 3: SW-D-DCEE | SW-D-DCEE, SW-A-DCEE      | .12, .22      |
| 4: SW-D-DMME | SW-D-DMME, SW-A-DMME      | .13, .23      |

When Docker pings 10.99.99.11:

1. Docker sees 10.99.99.11 is in the **same subnet** (10.99.99.0/24) → sends ARP request "who has 10.99.99.11?"
2. ARP broadcast only reaches Island 1 (SW-Core's local VLAN 99 segment)
3. SW-D-DEIE is on Island 2 → **ARP never reaches it** → "Destination unreachable"

Even if Docker sends to its gateway (10.99.99.1), SW-Core also has 10.99.99.0/24 as a **connected route** via its VLAN 99 SVI, so it tries to ARP locally → same failure.

### Fix for Problem 2: Static /32 Host Routes

The fix is elegant: add **/32 host routes** on SW-Core pointing to each distribution switch's routed port IP. A /32 route is more specific than the /24 connected route, so it wins the routing lookup.

**On SW-Core:**

```
enable
configure terminal

! Route MGMT traffic to distribution switch islands via routed links
! /32 host routes override the /24 connected route (longest match wins)
ip route 10.99.99.11 255.255.255.255 10.0.10.2
ip route 10.99.99.21 255.255.255.255 10.0.10.2
ip route 10.99.99.12 255.255.255.255 10.0.20.2
ip route 10.99.99.22 255.255.255.255 10.0.20.2
ip route 10.99.99.13 255.255.255.255 10.0.30.2
ip route 10.99.99.23 255.255.255.255 10.0.30.2

end
write memory
```

**How it works now:**

```
Docker pings 10.99.99.11:
  1. Docker → gateway 10.99.99.1 (SW-Core)
  2. SW-Core routing table lookup for 10.99.99.11:
     - Connected: 10.99.99.0/24 via VLAN 99    (matches, /24)
     - Static:    10.99.99.11/32 via 10.0.10.2  (matches, /32) ← WINS!
  3. SW-Core forwards to 10.0.10.2 (SW-D-DEIE routed port)
  4. SW-D-DEIE: 10.99.99.11 is my own VLAN 99 SVI → delivered ✅
```

**On each distribution switch** — add a return route for Docker:

```
! On SW-D-DEIE:
enable
configure terminal
ip route 10.99.99.100 255.255.255.255 10.0.10.1
end
write memory

! On SW-D-DCEE:
enable
configure terminal
ip route 10.99.99.100 255.255.255.255 10.0.20.1
end
write memory

! On SW-D-DMME:
enable
configure terminal
ip route 10.99.99.100 255.255.255.255 10.0.30.1
end
write memory
```

**Why?** Without this, when SW-D-DEIE sends a reply to 10.99.99.100, it looks up 10.99.99.0/24 (connected) → tries to ARP locally → Docker is on Island 1, not here → fails. The /32 route forces the reply through SW-Core.

**On each access switch** — change default-gateway to local distribution switch:

```
! On SW-A-DEIE:
enable
configure terminal
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.11
end
write memory

! On SW-A-DCEE:
enable
configure terminal
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.12
end
write memory

! On SW-A-DMME:
enable
configure terminal
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.13
end
write memory
```

**Why?** L2 access switches use `ip default-gateway` for their own management traffic (SSH replies, etc.). After the L3 split, SW-Core (10.99.99.1) is unreachable from the access switch's VLAN 99 segment. The local distribution switch IS reachable (same L2 island) and can route the traffic.

> [!NOTE]
> SW-A-DIS keeps `ip default-gateway 10.99.99.1` because it connects directly to SW-Core via trunk (Island 1) — no change needed.

---

## Summary: All Changes Needed

### 1. On SW-Core (3 changes)

```
enable
configure terminal

! ─── Fix 1: Add ICMP permits to ACL for router pings ───
ip access-list extended ACL-MGMT-IN
 15 permit icmp 10.99.99.0 0.0.0.255 10.0.0.0 0.0.0.3
 16 permit icmp 10.99.99.0 0.0.0.255 10.0.1.0 0.0.0.3
 17 permit icmp 10.99.99.0 0.0.0.255 10.0.10.0 0.0.0.3
 18 permit icmp 10.99.99.0 0.0.0.255 10.0.20.0 0.0.0.3
 19 permit icmp 10.99.99.0 0.0.0.255 10.0.30.0 0.0.0.3
exit

! ─── Fix 2: Static host routes to reach other VLAN 99 islands ───
ip route 10.99.99.11 255.255.255.255 10.0.10.2
ip route 10.99.99.21 255.255.255.255 10.0.10.2
ip route 10.99.99.12 255.255.255.255 10.0.20.2
ip route 10.99.99.22 255.255.255.255 10.0.20.2
ip route 10.99.99.13 255.255.255.255 10.0.30.2
ip route 10.99.99.23 255.255.255.255 10.0.30.2

end
write memory
```

### 2. On Each Distribution Switch (return route for Docker)

```
! SW-D-DEIE:
ip route 10.99.99.100 255.255.255.255 10.0.10.1

! SW-D-DCEE:
ip route 10.99.99.100 255.255.255.255 10.0.20.1

! SW-D-DMME:
ip route 10.99.99.100 255.255.255.255 10.0.30.1
```

### 3. On Access Switches (change default-gateway)

```
enable
configure terminal
! SW-A-DEIE:
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.11

enable
configure terminal
! SW-A-DCEE:
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.12

enable
configure terminal
! SW-A-DMME:
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.13

! SW-A-DIS — NO CHANGE (stays at 10.99.99.1, still on SW-Core's VLAN 99)
```

---

## Verification After Applying Fixes

From the Docker container:

```bash
# These should ALL succeed now:
ping -c 3 10.99.99.1      # SW-Core (was working)
ping -c 3 10.99.99.11     # SW-D-DEIE (was broken — fixed by static routes)
ping -c 3 10.99.99.12     # SW-D-DCEE
ping -c 3 10.99.99.13     # SW-D-DMME
ping -c 3 10.99.99.21     # SW-A-DEIE
ping -c 3 10.99.99.22     # SW-A-DCEE
ping -c 3 10.99.99.23     # SW-A-DMME
ping -c 3 10.99.99.24     # SW-A-DIS
ping -c 3 10.0.0.2        # R-CORE (was filtered — fixed by ACL)
ping -c 3 10.0.1.2        # R-EDGE (was filtered — fixed by ACL)
```

Verify the static routes on SW-Core:

```
show ip route static
```

Expected: six `/32` routes pointing to distribution switches.

---

## Full ACL Rebuild (If Sequence Numbers Don't Work)

If your IOSvL2 doesn't support inserting ACL rules by sequence number, remove and rebuild the entire ACL:

```
enable
configure terminal

! Remove the old ACL (the interface binding stays, just the rules are cleared)
no ip access-list extended ACL-MGMT-IN

! Rebuild with ICMP rules included
ip access-list extended ACL-MGMT-IN
 permit tcp 10.99.99.0 0.0.0.255 10.99.99.0 0.0.0.255 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.0.0 0.0.0.255 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.1.0 0.0.0.255 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.10.0 0.0.0.3 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.20.0 0.0.0.3 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.30.0 0.0.0.3 eq 22
 permit udp 10.99.99.0 0.0.0.255 host 10.10.40.100 eq 162
 permit udp 10.99.99.0 0.0.0.255 host 10.10.40.100 eq 161
 permit icmp 10.99.99.0 0.0.0.255 host 10.10.40.100
 permit icmp 10.99.99.0 0.0.0.255 10.99.99.0 0.0.0.255
 permit icmp 10.99.99.0 0.0.0.255 10.0.0.0 0.0.0.3
 permit icmp 10.99.99.0 0.0.0.255 10.0.1.0 0.0.0.3
 permit icmp 10.99.99.0 0.0.0.255 10.0.10.0 0.0.0.3
 permit icmp 10.99.99.0 0.0.0.255 10.0.20.0 0.0.0.3
 permit icmp 10.99.99.0 0.0.0.255 10.0.30.0 0.0.0.3
 deny ip 10.99.99.0 0.0.0.255 10.10.10.0 0.0.0.255
 deny ip 10.99.99.0 0.0.0.255 10.10.20.0 0.0.0.255
 deny ip 10.99.99.0 0.0.0.255 10.10.30.0 0.0.0.255
 deny ip 10.99.99.0 0.0.0.255 10.10.40.0 0.0.0.255
 deny ip 10.99.99.0 0.0.0.255 any
exit

end
write memory
```

> [!WARNING]
> When you `no ip access-list extended ACL-MGMT-IN`, the ACL binding on the VLAN 99 SVI (`ip access-group ACL-MGMT-IN in`) remains but points to an empty/non-existent ACL. This means **all traffic is permitted** until you re-create the ACL. Work quickly, or do this during a maintenance window.

---

## Why Your 4×4 Reachability Matrix Still Works

The 4×4 matrix tests traffic between department VLANs (10, 20, 30, 40) — these use:

- Department SVIs on distribution switches (10.10.10.1, 10.10.20.1, etc.)
- Routed point-to-point links between SW-Core and distribution switches
- OSPF routing

**None of this uses VLAN 99.** That's why inter-VLAN routing works perfectly but management-plane access from VLAN 99 to other VLAN 99 islands is broken. The data plane and management plane are separate, and only the management plane has this split-subnet issue.
