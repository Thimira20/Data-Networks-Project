# 4×4 Department Reachability Test Matrix — EE8203 Project

## 1. ACL Policy Summary (Quick Reference)

Based on your implemented ACLs, here is the inter-department policy that determines every cell in the matrix:

| # | Source | Destination | Action | What's Allowed |
|---|---|---|---|---|
| 1 | VLAN_DEIE (10) | VLAN_DIS (40) | **PERMIT all** | All IP traffic including ping |
| 2 | VLAN_DCEE (20) | VLAN_DIS (40) | **PERMIT HTTP/HTTPS only** | TCP 80 & 443 only — **ping (ICMP) is DENIED** |
| 3 | VLAN_DMME (30) | VLAN_DIS (40) | **DENY all** | Completely blocked |
| 4 | VLAN_DCEE (20) | VLAN_DEIE (10) | **DENY all** | Completely blocked |
| 5 | VLAN_DMME (30) | VLAN_DCEE (20) | **DENY all** | Completely blocked |
| 6 | VLAN_DMME (30) | Everything | **DENY all** | Fully isolated — no outbound traffic |
| 7 | VLAN_DIS (40) | VLAN_DEIE (10) | **PERMIT all** | All IP traffic including ping |
| 8 | VLAN_DIS (40) | VLAN_DCEE (20) | **PERMIT established TCP only** | Return TCP only — **ping (ICMP) is DENIED** |
| 9 | VLAN_DIS (40) | VLAN_DMME (30) | **DENY all** | Completely blocked |

### ACL Placement After L3 Conversion

| ACL Name | Applied On | Switch | Interface | Direction |
|---|---|---|---|---|
| ACL-DEIE-IN | VLAN 10 SVI | **SW-D-DEIE** | `interface vlan 10` | `in` |
| ACL-DCEE-IN | VLAN 20 SVI | **SW-D-DCEE** | `interface vlan 20` | `in` |
| ACL-DMME-IN | VLAN 30 SVI | **SW-D-DMME** | `interface vlan 30` | `in` |
| ACL-DIS-IN | VLAN 40 SVI | **SW-Core** | `interface vlan 40` | `in` |

---

## 2. Test PCs Used

| Department | VLAN | PC Name | IP Address | Default Gateway |
|---|---|---|---|---|
| DEIE | 10 | PC0 | 10.10.10.10 | 10.10.10.1 (SW-D-DEIE) |
| DCEE | 20 | PC6 | 10.10.20.10 | 10.10.20.1 (SW-D-DCEE) |
| DMME | 30 | PC4 | 10.10.30.10 | 10.10.30.1 (SW-D-DMME) |
| DIS | 40 | DIS-PC | 10.10.40.10 | 10.10.40.1 (SW-Core) |

---

## 3. The 4×4 Ping Matrix

> [!IMPORTANT]
> For a **ping to succeed**, the ACL must allow ICMP in **both directions** — the request from the source AND the reply from the destination. Even if one direction permits, the ping fails if the return is blocked.

| From ↓ \ To → | **DEIE** (10.10.10.10) | **DCEE** (10.10.20.10) | **DMME** (10.10.30.10) | **DIS** (10.10.40.10) |
|---|---|---|---|---|
| **DEIE** | ✅ Same VLAN | ❌ ACL denies DEIE→DCEE | ❌ ACL denies DEIE→DMME | ✅ ACL permits all |
| **DCEE** | ❌ ACL denies DCEE→DEIE | ✅ Same VLAN | ❌ ACL denies DCEE→DMME | ❌ Only TCP 80/443 (ICMP denied) |
| **DMME** | ❌ ACL denies DMME→any | ❌ ACL denies DMME→any | ✅ Same VLAN | ❌ ACL denies DMME→any |
| **DIS** | ✅ ACL permits DIS→DEIE | ❌ Only established TCP (ICMP denied) | ❌ ACL denies DIS→DMME | ✅ Same VLAN |

### Count: 4 pass ✅ (diagonal same-VLAN) + 2 pass ✅ (DEIE↔DIS) = **6 pass**, **10 fail**

---

## 4. The 4×4 Traceroute Path Matrix

| From ↓ \ To → | **DEIE** | **DCEE** | **DMME** | **DIS** |
|---|---|---|---|---|
| **DEIE** | Direct (L2) | ❌ Blocked at SW-D-DEIE | ❌ Blocked at SW-D-DEIE | ✅ DEIE→Core→DIS |
| **DCEE** | ❌ Blocked at SW-D-DCEE | Direct (L2) | ❌ Blocked at SW-D-DCEE | ❌ Blocked at SW-D-DCEE |
| **DMME** | ❌ Blocked at SW-D-DMME | ❌ Blocked at SW-D-DMME | Direct (L2) | ❌ Blocked at SW-D-DMME |
| **DIS** | ✅ DIS→Core→DEIE | ❌ Blocked at SW-Core | ❌ Blocked at SW-Core | Direct (L2) |

---

## 5. Expected Outputs — Every Cell

> [!NOTE]
> Outputs below are shown in **Packet Tracer PC command prompt** format. If you're using **GNS3 VPCs**, the format differs slightly — see Section 6 for GNS3 equivalents.

---

### Cell [1,1] — DEIE → DEIE (Same VLAN) ✅

**Ping:**
```
C:\>ping 10.10.10.11

Pinging 10.10.10.11 with 32 bytes of data:

Reply from 10.10.10.11: bytes=32 time<1ms TTL=128
Reply from 10.10.10.11: bytes=32 time<1ms TTL=128
Reply from 10.10.10.11: bytes=32 time<1ms TTL=128
Reply from 10.10.10.11: bytes=32 time<1ms TTL=128

Ping statistics for 10.10.10.11:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
```
> TTL=128 because the traffic stays within VLAN 10 (L2 switching, no L3 hops to decrement TTL).

**Traceroute:**
```
C:\>tracert 10.10.10.11

Tracing route to 10.10.10.11 over a maximum of 30 hops:

  1   1 ms      1 ms      1 ms      10.10.10.11

Trace complete.
```
> Only 1 hop — direct L2 delivery within the same VLAN.

---

### Cell [1,2] — DEIE → DCEE ❌

**Why blocked:** ACL-DEIE-IN (on SW-D-DEIE, `interface vlan 10 in`) has:
```
deny ip 10.10.10.0 0.0.0.255 10.10.20.0 0.0.0.255
```

**Ping:**
```
C:\>ping 10.10.20.10

Pinging 10.10.20.10 with 32 bytes of data:

Reply from 10.10.10.1: Destination host unreachable.
Reply from 10.10.10.1: Destination host unreachable.
Reply from 10.10.10.1: Destination host unreachable.
Reply from 10.10.10.1: Destination host unreachable.

Ping statistics for 10.10.20.10:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```
> The reply comes from `10.10.10.1` (SW-D-DEIE gateway) — this is the device that dropped the packet and sent back the ICMP unreachable.

**Traceroute:**
```
C:\>tracert 10.10.20.10

Tracing route to 10.10.20.10 over a maximum of 30 hops:

  1   10.10.10.1      reports: Destination host unreachable.

Trace complete.
```
> Blocked at hop 1 (SW-D-DEIE). The packet never leaves the distribution switch.

---

### Cell [1,3] — DEIE → DMME ❌

**Why blocked:** ACL-DEIE-IN has:
```
deny ip 10.10.10.0 0.0.0.255 10.10.30.0 0.0.0.255
```

**Ping:**
```
C:\>ping 10.10.30.10

Pinging 10.10.30.10 with 32 bytes of data:

Reply from 10.10.10.1: Destination host unreachable.
Reply from 10.10.10.1: Destination host unreachable.
Reply from 10.10.10.1: Destination host unreachable.
Reply from 10.10.10.1: Destination host unreachable.

Ping statistics for 10.10.30.10:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```

**Traceroute:**
```
C:\>tracert 10.10.30.10

Tracing route to 10.10.30.10 over a maximum of 30 hops:

  1   10.10.10.1      reports: Destination host unreachable.

Trace complete.
```

---

### Cell [1,4] — DEIE → DIS ✅

**Why allowed:**
- **Outbound:** ACL-DEIE-IN permits `permit ip 10.10.10.0 0.0.0.255 10.10.40.0 0.0.0.255`
- **Return:** ACL-DIS-IN permits `permit ip 10.10.40.0 0.0.0.255 10.10.10.0 0.0.0.255`

**Path:** PC0 → SW-A-DEIE (L2) → SW-D-DEIE → SW-Core → SW-A-DIS (L2) → DIS-PC

**Ping:**
```
C:\>ping 10.10.40.10

Pinging 10.10.40.10 with 32 bytes of data:

Reply from 10.10.40.10: bytes=32 time=1ms TTL=126
Reply from 10.10.40.10: bytes=32 time=1ms TTL=126
Reply from 10.10.40.10: bytes=32 time=1ms TTL=126
Reply from 10.10.40.10: bytes=32 time=1ms TTL=126

Ping statistics for 10.10.40.10:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
```
> TTL=126 → started at 128, decremented by 2 L3 hops (SW-D-DEIE, SW-Core).

**Traceroute:**
```
C:\>tracert 10.10.40.10

Tracing route to 10.10.40.10 over a maximum of 30 hops:

  1   1 ms      1 ms      1 ms      10.10.10.1
  2   1 ms      1 ms      1 ms      10.0.10.1
  3   2 ms      1 ms      1 ms      10.10.40.10

Trace complete.
```

**Hop-by-hop explanation:**
| Hop | IP | Device | What happened |
|---|---|---|---|
| 1 | 10.10.10.1 | SW-D-DEIE (VLAN 10 SVI) | Default gateway; ACL permits, routes toward SW-Core |
| 2 | 10.0.10.1 | SW-Core (Gi0/2 interface) | Receives on /30 link, routes to VLAN 40 (connected) |
| 3 | 10.10.40.10 | DIS-PC (destination) | Delivered via SW-A-DIS |

---

### Cell [2,1] — DCEE → DEIE ❌

**Why blocked:** ACL-DCEE-IN has:
```
deny ip 10.10.20.0 0.0.0.255 10.10.10.0 0.0.0.255
```

**Ping:**
```
C:\>ping 10.10.10.10

Pinging 10.10.10.10 with 32 bytes of data:

Reply from 10.10.20.1: Destination host unreachable.
Reply from 10.10.20.1: Destination host unreachable.
Reply from 10.10.20.1: Destination host unreachable.
Reply from 10.10.20.1: Destination host unreachable.

Ping statistics for 10.10.10.10:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```
> Reply from `10.10.20.1` = SW-D-DCEE (the gateway that dropped the packet).

**Traceroute:**
```
C:\>tracert 10.10.10.10

Tracing route to 10.10.10.10 over a maximum of 30 hops:

  1   10.10.20.1      reports: Destination host unreachable.

Trace complete.
```

---

### Cell [2,2] — DCEE → DCEE (Same VLAN) ✅

**Ping:**
```
C:\>ping 10.10.20.11

Pinging 10.10.20.11 with 32 bytes of data:

Reply from 10.10.20.11: bytes=32 time<1ms TTL=128
Reply from 10.10.20.11: bytes=32 time<1ms TTL=128
Reply from 10.10.20.11: bytes=32 time<1ms TTL=128
Reply from 10.10.20.11: bytes=32 time<1ms TTL=128

Ping statistics for 10.10.20.11:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
```

**Traceroute:**
```
C:\>tracert 10.10.20.11

Tracing route to 10.10.20.11 over a maximum of 30 hops:

  1   1 ms      1 ms      1 ms      10.10.20.11

Trace complete.
```

---

### Cell [2,3] — DCEE → DMME ❌

**Why blocked:** ACL-DCEE-IN has:
```
deny ip 10.10.20.0 0.0.0.255 10.10.30.0 0.0.0.255
```

**Ping:**
```
C:\>ping 10.10.30.10

Pinging 10.10.30.10 with 32 bytes of data:

Reply from 10.10.20.1: Destination host unreachable.
Reply from 10.10.20.1: Destination host unreachable.
Reply from 10.10.20.1: Destination host unreachable.
Reply from 10.10.20.1: Destination host unreachable.

Ping statistics for 10.10.30.10:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```

**Traceroute:**
```
C:\>tracert 10.10.30.10

Tracing route to 10.10.30.10 over a maximum of 30 hops:

  1   10.10.20.1      reports: Destination host unreachable.

Trace complete.
```

---

### Cell [2,4] — DCEE → DIS ❌ (Ping fails — only HTTP/HTTPS allowed)

**Why blocked for ping:** ACL-DCEE-IN has:
```
permit tcp 10.10.20.0 0.0.0.255 10.10.40.0 0.0.0.255 eq 80    ← TCP only
permit tcp 10.10.20.0 0.0.0.255 10.10.40.0 0.0.0.255 eq 443   ← TCP only
deny ip 10.10.20.0 0.0.0.255 10.10.40.0 0.0.0.255              ← catches ICMP
```
> Ping uses ICMP, not TCP. The `permit tcp` rules don't match ICMP, so the `deny ip` catches and blocks the ping.

**Ping:**
```
C:\>ping 10.10.40.10

Pinging 10.10.40.10 with 32 bytes of data:

Reply from 10.10.20.1: Destination host unreachable.
Reply from 10.10.20.1: Destination host unreachable.
Reply from 10.10.20.1: Destination host unreachable.
Reply from 10.10.20.1: Destination host unreachable.

Ping statistics for 10.10.40.10:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```

**Traceroute:**
```
C:\>tracert 10.10.40.10

Tracing route to 10.10.40.10 over a maximum of 30 hops:

  1   10.10.20.1      reports: Destination host unreachable.

Trace complete.
```

> [!TIP]
> **For the report**, note that while ping fails, a web browser from DCEE → DIS server (port 80/443) **would work**. This demonstrates the ACL correctly allows only HTTP/HTTPS, not all traffic.

---

### Cell [3,1] — DMME → DEIE ❌

**Why blocked:** ACL-DMME-IN (fully isolated) has:
```
deny ip 10.10.30.0 0.0.0.255 10.10.10.0 0.0.0.255
```

**Ping:**
```
C:\>ping 10.10.10.10

Pinging 10.10.10.10 with 32 bytes of data:

Reply from 10.10.30.1: Destination host unreachable.
Reply from 10.10.30.1: Destination host unreachable.
Reply from 10.10.30.1: Destination host unreachable.
Reply from 10.10.30.1: Destination host unreachable.

Ping statistics for 10.10.30.10:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```
> Reply from `10.10.30.1` = SW-D-DMME.

**Traceroute:**
```
C:\>tracert 10.10.10.10

Tracing route to 10.10.10.10 over a maximum of 30 hops:

  1   10.10.30.1      reports: Destination host unreachable.

Trace complete.
```

---

### Cell [3,2] — DMME → DCEE ❌

**Why blocked:** ACL-DMME-IN has:
```
deny ip 10.10.30.0 0.0.0.255 10.10.20.0 0.0.0.255
```

**Ping:**
```
C:\>ping 10.10.20.10

Pinging 10.10.20.10 with 32 bytes of data:

Reply from 10.10.30.1: Destination host unreachable.
Reply from 10.10.30.1: Destination host unreachable.
Reply from 10.10.30.1: Destination host unreachable.
Reply from 10.10.30.1: Destination host unreachable.

Ping statistics for 10.10.20.10:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```

**Traceroute:**
```
C:\>tracert 10.10.20.10

Tracing route to 10.10.20.10 over a maximum of 30 hops:

  1   10.10.30.1      reports: Destination host unreachable.

Trace complete.
```

---

### Cell [3,3] — DMME → DMME (Same VLAN) ✅

**Ping:**
```
C:\>ping 10.10.30.11

Pinging 10.10.30.11 with 32 bytes of data:

Reply from 10.10.30.11: bytes=32 time<1ms TTL=128
Reply from 10.10.30.11: bytes=32 time<1ms TTL=128
Reply from 10.10.30.11: bytes=32 time<1ms TTL=128
Reply from 10.10.30.11: bytes=32 time<1ms TTL=128

Ping statistics for 10.10.30.11:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
```

**Traceroute:**
```
C:\>tracert 10.10.30.11

Tracing route to 10.10.30.11 over a maximum of 30 hops:

  1   1 ms      1 ms      1 ms      10.10.30.11

Trace complete.
```

---

### Cell [3,4] — DMME → DIS ❌

**Why blocked:** ACL-DMME-IN has:
```
deny ip 10.10.30.0 0.0.0.255 10.10.40.0 0.0.0.255
```

**Ping:**
```
C:\>ping 10.10.40.10

Pinging 10.10.40.10 with 32 bytes of data:

Reply from 10.10.30.1: Destination host unreachable.
Reply from 10.10.30.1: Destination host unreachable.
Reply from 10.10.30.1: Destination host unreachable.
Reply from 10.10.30.1: Destination host unreachable.

Ping statistics for 10.10.40.10:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```

**Traceroute:**
```
C:\>tracert 10.10.40.10

Tracing route to 10.10.40.10 over a maximum of 30 hops:

  1   10.10.30.1      reports: Destination host unreachable.

Trace complete.
```

---

### Cell [4,1] — DIS → DEIE ✅

**Why allowed:**
- **Outbound:** ACL-DIS-IN permits `permit ip 10.10.40.0 0.0.0.255 10.10.10.0 0.0.0.255`
- **Return:** ACL-DEIE-IN permits `permit ip 10.10.10.0 0.0.0.255 10.10.40.0 0.0.0.255`

**Path:** DIS-PC → SW-A-DIS (L2) → SW-Core → SW-D-DEIE → SW-A-DEIE (L2) → PC0

**Ping:**
```
C:\>ping 10.10.10.10

Pinging 10.10.10.10 with 32 bytes of data:

Reply from 10.10.10.10: bytes=32 time=1ms TTL=126
Reply from 10.10.10.10: bytes=32 time=1ms TTL=126
Reply from 10.10.10.10: bytes=32 time=1ms TTL=126
Reply from 10.10.10.10: bytes=32 time=1ms TTL=126

Ping statistics for 10.10.10.10:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
```
> TTL=126 → 2 L3 hops (SW-Core, SW-D-DEIE).

**Traceroute:**
```
C:\>tracert 10.10.10.10

Tracing route to 10.10.10.10 over a maximum of 30 hops:

  1   1 ms      1 ms      1 ms      10.10.40.1
  2   1 ms      1 ms      1 ms      10.0.10.2
  3   2 ms      1 ms      1 ms      10.10.10.10

Trace complete.
```

**Hop-by-hop explanation:**
| Hop | IP | Device | What happened |
|---|---|---|---|
| 1 | 10.10.40.1 | SW-Core (VLAN 40 SVI) | Default gateway for DIS; ACL permits, routes toward SW-D-DEIE |
| 2 | 10.0.10.2 | SW-D-DEIE (Gi0/2 routed link) | Receives on /30 link, delivers to VLAN 10 |
| 3 | 10.10.10.10 | DEIE PC (destination) | Delivered via SW-A-DEIE |

---

### Cell [4,2] — DIS → DCEE ❌

**Why blocked:** ACL-DIS-IN has:
```
permit tcp 10.10.40.0 0.0.0.255 established 10.10.20.0 0.0.0.255   ← TCP established only
deny ip 10.10.40.0 0.0.0.255 10.10.20.0 0.0.0.255                  ← catches ICMP ping
```
> Only return TCP traffic (established connections initiated by DCEE) is allowed. New ICMP (ping) from DIS to DCEE is **denied**.

**Ping:**
```
C:\>ping 10.10.20.10

Pinging 10.10.20.10 with 32 bytes of data:

Reply from 10.10.40.1: Destination host unreachable.
Reply from 10.10.40.1: Destination host unreachable.
Reply from 10.10.40.1: Destination host unreachable.
Reply from 10.10.40.1: Destination host unreachable.

Ping statistics for 10.10.20.10:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```
> Reply from `10.10.40.1` = SW-Core (where ACL-DIS-IN is applied on VLAN 40 SVI).

**Traceroute:**
```
C:\>tracert 10.10.20.10

Tracing route to 10.10.20.10 over a maximum of 30 hops:

  1   10.10.40.1      reports: Destination host unreachable.

Trace complete.
```

---

### Cell [4,3] — DIS → DMME ❌

**Why blocked:** ACL-DIS-IN has:
```
deny ip 10.10.40.0 0.0.0.255 10.10.30.0 0.0.0.255
```

**Ping:**
```
C:\>ping 10.10.30.10

Pinging 10.10.30.10 with 32 bytes of data:

Reply from 10.10.40.1: Destination host unreachable.
Reply from 10.10.40.1: Destination host unreachable.
Reply from 10.10.40.1: Destination host unreachable.
Reply from 10.10.40.1: Destination host unreachable.

Ping statistics for 10.10.30.10:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```

**Traceroute:**
```
C:\>tracert 10.10.30.10

Tracing route to 10.10.30.10 over a maximum of 30 hops:

  1   10.10.40.1      reports: Destination host unreachable.

Trace complete.
```

---

### Cell [4,4] — DIS → DIS (Same VLAN) ✅

**Ping:**
```
C:\>ping 10.10.40.11

Pinging 10.10.40.11 with 32 bytes of data:

Reply from 10.10.40.11: bytes=32 time<1ms TTL=128
Reply from 10.10.40.11: bytes=32 time<1ms TTL=128
Reply from 10.10.40.11: bytes=32 time<1ms TTL=128
Reply from 10.10.40.11: bytes=32 time<1ms TTL=128

Ping statistics for 10.10.40.11:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
```

**Traceroute:**
```
C:\>tracert 10.10.40.11

Tracing route to 10.10.40.11 over a maximum of 30 hops:

  1   1 ms      1 ms      1 ms      10.10.40.11

Trace complete.
```

---

## 6. GNS3 VPC Expected Outputs (If Using GNS3 Instead)

If you're using GNS3 VPCs instead of Packet Tracer PCs, the command syntax and output format differ:

### Successful Ping (GNS3 VPC)
```
VPCS> ping 10.10.40.10
84 bytes from 10.10.40.10 icmp_seq=1 ttl=62 time=15.432 ms
84 bytes from 10.10.40.10 icmp_seq=2 ttl=62 time=12.891 ms
84 bytes from 10.10.40.10 icmp_seq=3 ttl=62 time=11.234 ms
84 bytes from 10.10.40.10 icmp_seq=4 ttl=62 time=10.567 ms
84 bytes from 10.10.40.10 icmp_seq=5 ttl=62 time=9.891 ms
```
> Note: VPC default TTL is 64 (not 128). So TTL=62 = 64 - 2 hops.

### Failed Ping (GNS3 VPC)
```
VPCS> ping 10.10.20.10
*10.10.10.1 icmp_seq=1 ttl=255 time=5.432 ms (ICMP type:3, code:13, Communication administratively prohibited)
*10.10.10.1 icmp_seq=2 ttl=255 time=4.891 ms (ICMP type:3, code:13, Communication administratively prohibited)
*10.10.10.1 icmp_seq=3 ttl=255 time=3.567 ms (ICMP type:3, code:13, Communication administratively prohibited)
*10.10.10.1 icmp_seq=4 ttl=255 time=3.234 ms (ICMP type:3, code:13, Communication administratively prohibited)
*10.10.10.1 icmp_seq=5 ttl=255 time=2.891 ms (ICMP type:3, code:13, Communication administratively prohibited)
```
> `ICMP type:3, code:13` = **Communication administratively prohibited** — this is the explicit ACL deny message.

### Successful Traceroute (GNS3 VPC)
```
VPCS> trace 10.10.40.10
trace to 10.10.40.10, 8 hops max, press Ctrl+C to stop
 1   10.10.10.1   5.123 ms  4.567 ms  3.891 ms
 2   10.0.10.1    8.234 ms  7.891 ms  6.543 ms
 3   *10.10.40.10   12.345 ms (ICMP type:3, code:3, Destination port unreachable)
```

### Failed Traceroute (GNS3 VPC)
```
VPCS> trace 10.10.20.10
trace to 10.10.20.10, 8 hops max, press Ctrl+C to stop
 1   *10.10.10.1   5.123 ms (ICMP type:3, code:13, Communication administratively prohibited)
```

---

## 7. Screenshot Checklist

For each of the 16 cells, take **one screenshot** showing:

| What to capture | How |
|---|---|
| The PC name/identity | Visible in the window title or prompt |
| The `ping` command and full output | Run `ping X.X.X.X` |
| The `tracert`/`trace` command and full output | Run `tracert X.X.X.X` (Packet Tracer) or `trace X.X.X.X` (GNS3) |

> [!TIP]
> You can combine both ping and traceroute in **one screenshot** per cell if you run them back-to-back in the same command prompt window. This gives you 16 screenshots total for the full matrix.

### Suggested Screenshot Naming Convention

```
Cell_1-1_DEIE_to_DEIE.png
Cell_1-2_DEIE_to_DCEE.png
Cell_1-3_DEIE_to_DMME.png
Cell_1-4_DEIE_to_DIS.png
Cell_2-1_DCEE_to_DEIE.png
Cell_2-2_DCEE_to_DCEE.png
Cell_2-3_DCEE_to_DMME.png
Cell_2-4_DCEE_to_DIS.png
Cell_3-1_DMME_to_DEIE.png
Cell_3-2_DMME_to_DCEE.png
Cell_3-3_DMME_to_DMME.png
Cell_3-4_DMME_to_DIS.png
Cell_4-1_DIS_to_DEIE.png
Cell_4-2_DIS_to_DCEE.png
Cell_4-3_DIS_to_DMME.png
Cell_4-4_DIS_to_DIS.png
```

---

## 8. Summary Observation for Report

> In the completed 4×4 matrix, inter-VLAN connectivity is **strictly controlled by ACLs**:
>
> - **DEIE ↔ DIS**: Full bidirectional access (engineering staff need full server farm access)
> - **DCEE → DIS**: HTTP/HTTPS only (web-only access) — ping fails, browsers work
> - **DMME**: Completely isolated — cannot reach any other department
> - **DIS → DCEE**: Only return traffic (established TCP sessions) — no new connections from DIS
> - **All other cross-department pairs**: Denied
>
> The **diagonal cells** (same VLAN) always succeed because intra-VLAN traffic is switched at Layer 2 and never hits the L3 ACL.
>
> The **traceroute results** confirm the L3 routed path through the distribution and core switches, proving the Layer 3 conversion is working correctly alongside the ACL enforcement.

---

## 9. Quick Verify: ACL Hit Counters

After running all 16 tests, check the ACL hit counters on each L3 switch to confirm packets were actually processed by the ACLs:

**On SW-D-DEIE:**
```
show access-lists ACL-DEIE-IN
```
**Expected output:**
```
Extended IP access list ACL-DEIE-IN
    10 permit ip 10.10.10.0 0.0.0.255 10.10.40.0 0.0.0.255 (8 matches)
    20 deny ip 10.10.10.0 0.0.0.255 10.10.20.0 0.0.0.255 (4 matches)
    30 deny ip 10.10.10.0 0.0.0.255 10.10.30.0 0.0.0.255 (4 matches)
    40 deny ip 10.10.10.0 0.0.0.255 10.99.99.0 0.0.0.255
    50 permit ip 10.10.10.0 0.0.0.255 any
```
> The `(X matches)` counter proves the ACL is actively filtering traffic. Include this in your report as additional evidence.

**On SW-D-DCEE:**
```
show access-lists ACL-DCEE-IN
```

**On SW-D-DMME:**
```
show access-lists ACL-DMME-IN
```

**On SW-Core:**
```
show access-lists ACL-DIS-IN
```
