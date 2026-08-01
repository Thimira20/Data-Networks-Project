# Docker Connectivity Fix — Root Cause Analysis & Complete Solution

## Overview

This document covers **all fixes** needed to restore full connectivity from the UbuntuDockerGuest-1 container (10.99.99.100) to every device in the network, including internet access for package installation (`apt-get`, `pip install`).

**Five separate problems** were identified and fixed:

| # | Problem | Symptom | Root Cause | Fix Location |
|---|---------|---------|------------|--------------|
| 1 | Can't ping distribution/access switches | Destination unreachable | VLAN 99 L2 split after L3 conversion | SW-Core + Dist switches |
| 2 | Can't ping R-CORE/R-EDGE | Packet filtered | ACL missing ICMP permits | SW-Core ACL |
| 3 | OSPF adjacency not forming with R-CORE | No route propagation | `passive-interface` on Gi0/1 | SW-Core OSPF |
| 4 | R-EDGE completely unconfigured | No internet path | Interfaces down, no NAT | R-EDGE |
| 5 | R-EDGE can't reach internet | Default route ARP failure | Interface-based route on Ethernet | R-EDGE route |

---

## Problem 1: Distribution/Access Switches Unreachable (VLAN 99 L2 Split)

### Why It Happens

After converting distribution switches to L3 (routed ports), VLAN 99 is no longer a single L2 broadcast domain. It's split into **4 separate L2 islands**:

```
       ISLAND 1 (L2)                    ISLAND 2 (L2)
┌─────────────────────┐          ┌─────────────────────┐
│ Docker  10.99.99.100│          │ SW-D-DEIE 10.99.99.11│
│ SW-Core 10.99.99.1  │──ROUTED──│ SW-A-DEIE 10.99.99.21│
│ SW-A-DIS 10.99.99.24│ 10.0.10  │                     │
└─────────────────────┘  /30     └─────────────────────┘
```

| Island | Devices | VLAN 99 IPs |
|--------|---------|-------------|
| 1: SW-Core | SW-Core, SW-A-DIS, Docker | .1, .24, .100 |
| 2: SW-D-DEIE | SW-D-DEIE, SW-A-DEIE | .11, .21 |
| 3: SW-D-DCEE | SW-D-DCEE, SW-A-DCEE | .12, .22 |
| 4: SW-D-DMME | SW-D-DMME, SW-A-DMME | .13, .23 |

Docker sends ARP for 10.99.99.11 → broadcast stays on Island 1 → never reaches Island 2.

### Fix: Static /32 Host Routes + Return Routes

**/32 host routes override the /24 connected route** (longest prefix match wins).

**On SW-Core:**

```
enable
configure terminal

ip route 10.99.99.11 255.255.255.255 10.0.10.2
ip route 10.99.99.21 255.255.255.255 10.0.10.2
ip route 10.99.99.12 255.255.255.255 10.0.20.2
ip route 10.99.99.22 255.255.255.255 10.0.20.2
ip route 10.99.99.13 255.255.255.255 10.0.30.2
ip route 10.99.99.23 255.255.255.255 10.0.30.2

end
write memory
```

**On each distribution switch (return route for Docker):**

```
! SW-D-DEIE:
ip route 10.99.99.100 255.255.255.255 10.0.10.1

! SW-D-DCEE:
ip route 10.99.99.100 255.255.255.255 10.0.20.1

! SW-D-DMME:
ip route 10.99.99.100 255.255.255.255 10.0.30.1
```

**On each access switch (change default-gateway to local distribution switch):**

```
! SW-A-DEIE:
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.11

! SW-A-DCEE:
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.12

! SW-A-DMME:
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.13

! SW-A-DIS — NO CHANGE (stays at 10.99.99.1, still on Island 1)
```

> [!NOTE]
> After applying, the first 1-2 pings to access switches (.21, .22, .23) may drop due to ARP cache warmup. This is normal — subsequent pings will succeed.

---

## Problem 2: R-CORE/R-EDGE Show "Packet Filtered" (ACL Issue)

### Why It Happens

`ACL-MGMT-IN` on SW-Core's VLAN 99 SVI only permitted ICMP to management subnet and Zabbix — not to router link subnets (10.0.0.0/30, 10.0.1.0/30). Traffic fell through to the `deny ip ... any` rule.

### Fix: Full ACL Rebuild on SW-Core

Sequence number insertion may not work on IOSvL2, so **rebuild the entire ACL**:

```
enable
configure terminal

no ip access-list extended ACL-MGMT-IN

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
 permit ip 10.99.99.0 0.0.0.255 any
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
> When you `no ip access-list extended ACL-MGMT-IN`, the binding on VLAN 99 SVI remains but points to an empty ACL — **all traffic is permitted** until you re-create it. Work quickly.

> [!IMPORTANT]
> **Security note:** The `permit ip 10.99.99.0 0.0.0.255 any` rule (needed for internet access via NAT) must appear **before** the `deny` rules, but be aware it makes the deny rules ineffective for management VLAN sources. If you later want to restrict management-to-data-VLAN traffic while keeping internet access, replace it with a more specific permit for internet-bound traffic only.

---

## Problem 3: OSPF Not Forming Adjacency with R-CORE

### Why It Happens

SW-Core had `passive-interface default` but **forgot to exclude Gi0/1** (the interface facing R-CORE):

```
passive-interface default          ← All interfaces passive
no passive-interface GigabitEthernet0/0   ← to SW-D-DEIE ✅
no passive-interface GigabitEthernet0/2   ← to SW-D-DCEE ✅
no passive-interface GigabitEthernet0/3   ← to SW-D-DMME ✅
no passive-interface GigabitEthernet1/0   ← to SW-A-DIS  ✅
! GigabitEthernet0/1 (to R-CORE) — MISSING! ❌
```

No OSPF hellos sent → no adjacency → R-CORE never learns routes to internal networks → can't route return traffic.

### Fix on SW-Core

```
enable
configure terminal
router ospf 1
 no passive-interface GigabitEthernet0/1
end
write memory
```

**Expected result:** OSPF adjacency forms within seconds:

```
%OSPF-5-ADJCHG: Process 1, Nbr 10.0.1.2 on GigabitEthernet0/1 from LOADING to FULL, Loading Done
```

Verify: `show ip ospf neighbor` should show R-CORE (10.0.1.2) as FULL.

---

## Problem 4: R-EDGE Completely Unconfigured

### Why It Happens

R-EDGE had all interfaces `administratively down` with no IP addresses. The NAT configuration had never been applied.

### Interface Mapping

```
R-EDGE f0/0  ──── R-CORE f0/0     (10.0.1.0/30 link)
R-EDGE f1/0  ──── NAT1 cloud      (DHCP from GNS3)
```

| Interface | IP | Role |
|-----------|-----|------|
| f0/0 | 10.0.1.1/30 | Internal (NAT inside) |
| f1/0 | DHCP (e.g. 192.168.42.239) | Internet (NAT outside) |

### Fix: Full R-EDGE Configuration

```
enable
configure terminal

interface FastEthernet0/0
 ip address 10.0.1.1 255.255.255.252
 ip nat inside
 no shutdown
exit

interface FastEthernet1/0
 ip address dhcp
 ip nat outside
 no shutdown
exit

access-list 100 permit ip 10.99.99.0 0.0.0.255 any
access-list 100 permit ip 10.10.10.0 0.0.0.255 any
access-list 100 permit ip 10.10.20.0 0.0.0.255 any

ip nat inside source list 100 interface FastEthernet1/0 overload

! Return route for all internal 10.x.x.x traffic
ip route 10.0.0.0 255.0.0.0 10.0.1.2

end
write memory
```

Wait for DHCP assignment:
```
%DHCP-6-ADDRESS_ASSIGN: Interface FastEthernet1/0 assigned DHCP address 192.168.42.239
```

---

## Problem 5: R-EDGE Can't Reach Internet (Default Route Issue)

### Why It Happens

Using an **interface** as the next-hop on a multi-access (Ethernet) network:

```
ip route 0.0.0.0 0.0.0.0 FastEthernet1/0    ← WRONG for Ethernet
```

This makes the router ARP for **every destination IP** (e.g., 8.8.8.8) directly on f1/0. The GNS3 NAT cloud doesn't respond to ARP for arbitrary IPs → packet dropped.

### Fix: Use the DHCP Gateway IP

After R-EDGE gets its DHCP address, note the subnet (e.g., 192.168.42.239/24 → gateway is 192.168.42.1):

```
enable
configure terminal
ip route 0.0.0.0 0.0.0.0 192.168.42.1
end
write memory
```

> [!NOTE]
> The gateway IP depends on your GNS3 NAT cloud. Common values: `192.168.122.1`, `192.168.42.1`, or `10.0.2.2`. Check with `ping 192.168.42.1` first to confirm reachability.

### Also needed — R-CORE default route to R-EDGE

R-CORE needs a default route pointing to R-EDGE, **using R-EDGE's IP (not R-CORE's own)**:

```
! On R-CORE:
enable
configure terminal
ip route 0.0.0.0 0.0.0.0 10.0.1.1
router ospf 1
 default-information originate
end
write memory
```

> [!CAUTION]
> R-CORE's interface on the 10.0.1.0/30 link is **10.0.1.2** (not .1). The next-hop must be R-EDGE's IP: **10.0.1.1**. Using 10.0.1.2 will fail with `%Invalid next hop address (it's this router)`.

---

## Complete Configuration Order

Apply changes in this order to minimize disruption:

### Step 1: SW-Core (ACL + routes + OSPF)

```
enable
configure terminal

! Fix 1: ACL rebuild (see Problem 2 for full ACL)
no ip access-list extended ACL-MGMT-IN
ip access-list extended ACL-MGMT-IN
 ! ... (full ACL from Problem 2 section above)
exit

! Fix 2: Static /32 host routes for VLAN 99 islands
ip route 10.99.99.11 255.255.255.255 10.0.10.2
ip route 10.99.99.21 255.255.255.255 10.0.10.2
ip route 10.99.99.12 255.255.255.255 10.0.20.2
ip route 10.99.99.22 255.255.255.255 10.0.20.2
ip route 10.99.99.13 255.255.255.255 10.0.30.2
ip route 10.99.99.23 255.255.255.255 10.0.30.2

! Fix 3: Enable OSPF on R-CORE facing interface
router ospf 1
 no passive-interface GigabitEthernet0/1
exit

end
write memory
```

### Step 2: Distribution Switches (return routes)

```
! SW-D-DEIE:
ip route 10.99.99.100 255.255.255.255 10.0.10.1

! SW-D-DCEE:
ip route 10.99.99.100 255.255.255.255 10.0.20.1

! SW-D-DMME:
ip route 10.99.99.100 255.255.255.255 10.0.30.1
```

### Step 3: Access Switches (change default-gateway)

```
! SW-A-DEIE: ip default-gateway 10.99.99.11
! SW-A-DCEE: ip default-gateway 10.99.99.12
! SW-A-DMME: ip default-gateway 10.99.99.13
! SW-A-DIS:  NO CHANGE (keep 10.99.99.1)
```

### Step 4: R-EDGE (full NAT setup)

See Problem 4 + Problem 5 sections above. Key: use **gateway IP** for default route, not interface.

### Step 5: R-CORE (default route + OSPF propagation)

```
enable
configure terminal
ip route 0.0.0.0 0.0.0.0 10.0.1.1
router ospf 1
 default-information originate
end
write memory
```

---

## Verification

### From Docker — all should succeed:

```bash
ping -c 3 10.99.99.1      # SW-Core
ping -c 3 10.99.99.11     # SW-D-DEIE
ping -c 3 10.99.99.12     # SW-D-DCEE
ping -c 3 10.99.99.13     # SW-D-DMME
ping -c 3 10.99.99.21     # SW-A-DEIE
ping -c 3 10.99.99.22     # SW-A-DCEE
ping -c 3 10.99.99.23     # SW-A-DMME
ping -c 3 10.99.99.24     # SW-A-DIS
ping -c 3 10.0.0.2        # R-CORE
ping -c 3 10.0.1.1        # R-EDGE
ping -c 3 8.8.8.8         # Internet
```

### Key verification commands:

```
! SW-Core:
show ip ospf neighbor          # Should show R-CORE as FULL
show ip route static           # Should show six /32 routes
show ip access-lists ACL-MGMT-IN

! R-CORE:
show ip ospf neighbor          # Should show SW-Core + R-EDGE as FULL
show ip route 0.0.0.0          # Default via 10.0.1.1

! R-EDGE:
show ip interface brief        # f0/0 and f1/0 both up with IPs
show ip nat translations       # Should show active translations
ping 8.8.8.8                   # Should succeed from R-EDGE itself
```

### After internet works — install automation dependencies:

```bash
apt-get update && apt-get install -y python3 python3-pip
pip install netmiko pyyaml
```

---

## Why the 4×4 Reachability Matrix Still Works

The 4×4 matrix tests traffic between department VLANs (10, 20, 30, 40) using department SVIs, routed point-to-point links, and OSPF. **None of this uses VLAN 99.** The data plane and management plane are separate — only the management plane had the split-subnet issue.
