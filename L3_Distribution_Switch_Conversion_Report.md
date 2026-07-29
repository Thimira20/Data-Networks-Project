# Distribution Switch L2 → L3 Conversion Report

## 1. Overview & Objective

**Goal:** Convert the three distribution switches (**SW-D-DEIE**, **SW-D-DCEE**, **SW-D-DMME**) from Layer 2 switches to **Layer 3 (multilayer) switches** so they can participate in OSPF routing and perform inter-VLAN routing alongside SW-Core.

> [!IMPORTANT]
> Per the project spec, there is **no SW-D-DIS** (no distribution switch for the DIS/Server-Farm department — only SW-A-DIS connects directly to SW-Core). Only 3 distribution switches are converted.

### What Changes

| Aspect                    | Before (L2)                     | After (L3)                                                                                                  |
| ------------------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Uplink to SW-Core         | Trunk (switchport)              | **Routed port** (`no switchport`) with /30 IP                                                               |
| Downlink to Access SW     | Trunk (switchport)              | Trunk (switchport) — **unchanged**                                                                          |
| `ip routing`              | ❌ Not enabled                  | ✅ Enabled                                                                                                  |
| SVIs for department VLANs | ❌ None (only VLAN 99 for mgmt) | ✅ SVI with gateway IP for its own department VLAN                                                          |
| `ip default-gateway`      | ✅ Used (L2 behaviour)          | ❌ **Removed** (L3 uses routing table instead)                                                              |
| OSPF                      | ❌ Not running                  | ✅ OSPF process 1, area 0                                                                                   |
| MGMT VLAN 99 SVI          | Has IP (mgmt only)              | Keeps IP — now also advertised in OSPF                                                                      |
| Inter-VLAN routing        | All done by SW-Core             | Each dist switch **routes its own VLAN locally** — traffic only goes to SW-Core for cross-department or WAN |

### What Stays the Same

- All VLAN definitions (10, 20, 30, 40, 99, 100) — no changes
- Trunk links from distribution → access switches — no changes
- Access switch configurations — **no changes at all**
- PC IPs and gateways — **gateways change** (see Section 2)
- SW-Core remains the core L3 switch and OSPF backbone
- R-CORE configuration — no changes

---

## 2. New Address Plan

### 2.1 Point-to-Point Links: SW-Core ↔ Distribution Switches (/30)

The trunk links between SW-Core and each distribution switch are **converted to routed point-to-point links**. Each link gets a dedicated /30 subnet.

| Link                | Subnet       | SW-Core IP | Distribution SW IP | SW-Core Interface | Dist SW Interface |
| ------------------- | ------------ | ---------- | ------------------ | ----------------- | ----------------- |
| SW-Core ↔ SW-D-DEIE | 10.0.10.0/30 | 10.0.10.1  | 10.0.10.2          | Gi0/2             | Gi0/2             |
| SW-Core ↔ SW-D-DCEE | 10.0.20.0/30 | 10.0.20.1  | 10.0.20.2          | Gi0/1             | Gi0/2             |
| SW-Core ↔ SW-D-DMME | 10.0.30.0/30 | 10.0.30.1  | 10.0.30.2          | Gi0/3             | Gi0/0             |

> [!NOTE]
> The existing SW-Core Gi0/4 trunk to SW-D-DIS is **removed** (no SW-D-DIS in the design). SW-A-DIS connects directly to SW-Core via a **trunk** link (unchanged).

### 2.2 Department VLAN Gateways — Moved to Distribution Switches

Each distribution switch now hosts the SVI gateway for **its own department VLAN only**. SW-Core **no longer** holds those per-department SVIs.

| VLAN | Name      | Subnet        | Old Gateway (SW-Core) | **New Gateway (Dist SW)**                                           |
| ---- | --------- | ------------- | --------------------- | ------------------------------------------------------------------- |
| 10   | VLAN_DEIE | 10.10.10.0/24 | 10.10.10.1            | **10.10.10.1 on SW-D-DEIE**                                         |
| 20   | VLAN_DCEE | 10.10.20.0/24 | 10.10.20.1            | **10.10.20.1 on SW-D-DCEE**                                         |
| 30   | VLAN_DMME | 10.10.30.0/24 | 10.10.30.1            | **10.10.30.1 on SW-D-DMME**                                         |
| 40   | VLAN_DIS  | 10.10.40.0/24 | 10.10.40.1            | **10.10.40.1 on SW-Core** (unchanged — no dist switch for DIS)      |
| 99   | MGMT      | 10.99.99.0/24 | 10.99.99.1            | **10.99.99.1 on SW-Core** (unchanged — MGMT backbone stays on core) |

> [!IMPORTANT]
> **PC default gateways do NOT change!** The IPs stay the same (e.g. 10.10.10.1), they just now live on the distribution switch instead of SW-Core. PCs don't need reconfiguration.

### 2.3 MGMT VLAN 99 IPs — Unchanged

| Device    | MGMT IP     |
| --------- | ----------- |
| SW-Core   | 10.99.99.1  |
| SW-D-DEIE | 10.99.99.11 |
| SW-D-DCEE | 10.99.99.12 |
| SW-D-DMME | 10.99.99.13 |
| SW-A-DEIE | 10.99.99.21 |
| SW-A-DCEE | 10.99.99.22 |
| SW-A-DMME | 10.99.99.23 |

---

## 3. Configuration Commands

> [!CAUTION]
> **Save your Packet Tracer / GNS3 file before starting!** Take a snapshot so you can roll back if anything breaks.

### 3.1 SW-D-DEIE — Convert to Layer 3

```
enable
configure terminal

! ============================================================
! STEP 1: Remove L2-only default gateway (not valid on L3)
! ============================================================
no ip default-gateway

! ============================================================
! STEP 2: Enable Layer 3 routing
! ============================================================
ip routing

! ============================================================
! STEP 3: Convert uplink to SW-Core from trunk → routed port
! ============================================================
interface GigabitEthernet 0/0
 description ROUTED_LINK_TO_SW-CORE
 no switchport trunk encapsulation dot1q
 no switchport trunk native vlan 100
 no switchport trunk allowed vlan 10,20,30,40,99,100
 no switchport mode trunk
 no switchport
 ip address 10.0.10.2 255.255.255.252
 no shutdown
exit

! ============================================================
! STEP 4: Downlink to access switch — STAYS as trunk (no change)
! GigabitEthernet 0/2 — trunk to SW-A-DEIE (already configured)
! ============================================================

! ============================================================
! STEP 5: Create SVI for department VLAN (this switch is gateway)
! ============================================================
interface vlan 10
 description GW_VLAN_DEIE
 ip address 10.10.10.1 255.255.255.0
 no shutdown
exit

! ============================================================
! STEP 6: MGMT SVI — already exists, just verify it's up
! ============================================================
interface vlan 99
 description MGMT_INTERFACE
 ip address 10.99.99.11 255.255.255.0
 no shutdown
exit

! ============================================================
! STEP 7: OSPF — advertise department subnet + mgmt + p2p link
! ============================================================
router ospf 1
 router-id 3.3.3.11
 network 10.0.10.0 0.0.0.3 area 0
 network 10.10.10.0 0.0.0.255 area 0
 network 10.99.99.0 0.0.0.255 area 0
 passive-interface default
 no passive-interface GigabitEthernet 0/0
exit

end
write memory
```

---

### 3.2 SW-D-DCEE — Convert to Layer 3

```
enable
configure terminal

! ============================================================
! STEP 1: Remove L2-only default gateway
! ============================================================
no ip default-gateway

! ============================================================
! STEP 2: Enable Layer 3 routing
! ============================================================
ip routing

! ============================================================
! STEP 3: Convert uplink to SW-Core from trunk → routed port
! ============================================================
interface GigabitEthernet 0/2
 description ROUTED_LINK_TO_SW-CORE
 no switchport trunk encapsulation dot1q
 no switchport trunk native vlan 100
 no switchport trunk allowed vlan 10,20,30,40,99,100
 no switchport mode trunk
 no switchport
 ip address 10.0.20.2 255.255.255.252
 no shutdown
exit

! ============================================================
! STEP 4: Downlink to access switch — STAYS as trunk (no change)
! GigabitEthernet 0/0 — trunk to SW-A-DCEE (already configured)
! ============================================================

! ============================================================
! STEP 5: Create SVI for department VLAN (this switch is gateway)
! ============================================================
interface vlan 20
 description GW_VLAN_DCEE
 ip address 10.10.20.1 255.255.255.0
 no shutdown
exit

! ============================================================
! STEP 6: MGMT SVI — already exists, just verify it's up
! ============================================================
interface vlan 99
 description MGMT_INTERFACE
 ip address 10.99.99.12 255.255.255.0
 no shutdown
exit

! ============================================================
! STEP 7: OSPF — advertise department subnet + mgmt + p2p link
! ============================================================
router ospf 1
 router-id 3.3.3.12
 network 10.0.20.0 0.0.0.3 area 0
 network 10.10.20.0 0.0.0.255 area 0
 network 10.99.99.0 0.0.0.255 area 0
 passive-interface default
 no passive-interface GigabitEthernet 0/2
exit

end
write memory
```

---

### 3.3 SW-D-DMME — Convert to Layer 3

```
enable
configure terminal

! ============================================================
! STEP 1: Remove L2-only default gateway
! ============================================================
no ip default-gateway

! ============================================================
! STEP 2: Enable Layer 3 routing
! ============================================================
ip routing

! ============================================================
! STEP 3: Convert uplink to SW-Core from trunk → routed port
! ============================================================
interface GigabitEthernet 0/3
 description ROUTED_LINK_TO_SW-CORE
 no switchport trunk encapsulation dot1q
 no switchport trunk native vlan 100
 no switchport trunk allowed vlan 10,20,30,40,99,100
 no switchport mode trunk
 no switchport
 ip address 10.0.30.2 255.255.255.252
 no shutdown
exit

! ============================================================
! STEP 4: Downlink to access switch — STAYS as trunk (no change)
! GigabitEthernet 0/0 — trunk to SW-A-DMME (already configured)
! ============================================================

! ============================================================
! STEP 5: Create SVI for department VLAN (this switch is gateway)
! ============================================================
interface vlan 30
 description GW_VLAN_DMME
 ip address 10.10.30.1 255.255.255.0
 no shutdown
exit

! ============================================================
! STEP 6: MGMT SVI — already exists, just verify it's up
! ============================================================
interface vlan 99
 description MGMT_INTERFACE
 ip address 10.99.99.13 255.255.255.0
 no shutdown
exit

! ============================================================
! STEP 7: OSPF — advertise department subnet + mgmt + p2p link
! ============================================================
router ospf 1
 router-id 3.3.3.13
 network 10.0.30.0 0.0.0.3 area 0
 network 10.10.30.0 0.0.0.255 area 0
 network 10.99.99.0 0.0.0.255 area 0
 passive-interface default
 no passive-interface GigabitEthernet 0/3
exit

end
write memory
```

---

### 3.4 SW-Core — Update to Match New Design

SW-Core needs to:

1. **Remove** the old trunk links to distribution switches (replace with routed ports)
2. **Remove** the SVIs for VLANs 10, 20, 30 (those gateways now live on dist switches)
3. **Keep** SVIs for VLAN 40 (DIS — no dist switch) and VLAN 99 (MGMT)
4. **Add** new routed point-to-point interfaces
5. **Update** OSPF to advertise the new /30 links and stop advertising moved VLAN subnets

```
enable
configure terminal

! ============================================================
! STEP 1: Remove old trunk interfaces to distribution switches
!         (these become routed ports)
! ============================================================

! --- Gi0/2 was trunk to SW-D-DCEE ---
interface GigabitEthernet 0/2
 description ROUTED_LINK_TO_SW-D-DCEE
 no switchport trunk encapsulation dot1q
 no switchport trunk native vlan 100
 no switchport trunk allowed vlan 10,20,30,40,99,100
 no switchport mode trunk
 no switchport
 ip address 10.0.20.1 255.255.255.252
 no shutdown
exit

! --- Gi0/0 was trunk to SW-D-DEIE ---
interface GigabitEthernet 0/0
 description ROUTED_LINK_TO_SW-D-DEIE
 no switchport trunk encapsulation dot1q
 no switchport trunk native vlan 100
 no switchport trunk allowed vlan 10,20,30,40,99,100
 no switchport mode trunk
 no switchport
 ip address 10.0.10.1 255.255.255.252
 no shutdown
exit

! --- Gi0/3 was trunk to SW-D-DMME ---
interface GigabitEthernet 0/3
 description ROUTED_LINK_TO_SW-D-DMME
 no switchport trunk encapsulation dot1q
 no switchport trunk native vlan 100
 no switchport trunk allowed vlan 10,20,30,40,99,100
 no switchport mode trunk
 no switchport
 ip address 10.0.30.1 255.255.255.252
 no shutdown
exit

! ============================================================
! STEP 2: Remove old SVIs for VLANs 10, 20, 30
!         (gateways moved to distribution switches)
! ============================================================
no interface vlan 10
no interface vlan 20
no interface vlan 30

! ============================================================
! STEP 3: Keep SVIs for VLAN 40 (DIS) and VLAN 99 (MGMT)
!         (verify they're correct — no changes needed)
! ============================================================
interface vlan 40
 description GW_VLAN_DIS
 ip address 10.10.40.1 255.255.255.0
 no shutdown
exit

interface vlan 99
 description GW_VLAN_MGMT
 ip address 10.99.99.1 255.255.255.0
 no shutdown
exit

! ============================================================
! STEP 4: Update OSPF — new p2p links, remove old VLAN networks
! ============================================================
no router ospf 1

router ospf 1
 router-id 1.1.1.1
 ! Point-to-point link to R-CORE
 network 10.0.0.0 0.0.0.3 area 0
 ! Point-to-point links to distribution switches
 network 10.0.10.0 0.0.0.3 area 0
 network 10.0.20.0 0.0.0.3 area 0
 network 10.0.30.0 0.0.0.3 area 0
 ! Directly connected subnets (DIS + MGMT only)
 network 10.10.40.0 0.0.0.255 area 0
 network 10.99.99.0 0.0.0.255 area 0
 ! Only form adjacencies on routed links
 passive-interface default
 no passive-interface GigabitEthernet 0/0
 no passive-interface GigabitEthernet 1/0
 no passive-interface GigabitEthernet 0/2
 no passive-interface GigabitEthernet 0/3
exit

end
write memory
```

> [!WARNING]
> **Interface Gi0/0 on SW-Core** is the routed link to R-CORE (`10.0.0.1/30`). In the original config this was listed as `Gi0/1` in one place — double check which physical port your R-CORE cable is actually plugged into in GNS3/Packet Tracer, and use that interface name consistently.

---

### 3.5 SW-A-DIS — Direct Trunk to SW-Core (No Change Needed)

Since there is no SW-D-DIS, the access switch SW-A-DIS connects **directly to SW-Core** via a trunk. This config is **already correct** — no changes.

The SW-Core still holds the VLAN 40 SVI (10.10.40.1) as the gateway for DIS hosts.

---

### 3.6 Access Switches (SW-A-DEIE, SW-A-DCEE, SW-A-DMME) — No Changes

Access switches remain pure L2. Their trunk uplinks to the distribution switches are **unchanged**. Their `ip default-gateway 10.99.99.1` pointing to SW-Core VLAN 99 SVI is still correct (SW-Core still owns 10.99.99.1).

---

## 4. Updated Network Topology Diagram

```
                          Internet Cloud
                               |
                          [ R-EDGE ]
                           10.0.1.2
                               |  10.0.1.0/30
                           10.0.1.1
                          [ R-CORE ]
                           10.0.0.2
                               |  10.0.0.0/30
                           10.0.0.1
                      ┌──[ SW-CORE (L3) ]──┐
                      │    VLAN 40 GW      │
                      │    VLAN 99 GW      │
                      │                    │
           Gi0/2      │       Gi0/1        │   Gi0/3          Gi0/4(trunk)
         10.0.10.1    │     10.0.20.1      │  10.0.30.1         │
           /30        │       /30          │    /30             │
         10.0.10.2    │     10.0.20.2      │  10.0.30.2         │
              │       │         │          │      │             │
    ┌─────────┘       │    ┌────┘          │   ┌──┘             │
    │                 │    │               │   │                │
[ SW-D-DEIE (L3) ]   │  [ SW-D-DCEE (L3)]│ [ SW-D-DMME (L3)] │
  VLAN 10 GW         │    VLAN 20 GW      │   VLAN 30 GW      │
  10.10.10.1          │    10.10.20.1      │   10.10.30.1       │
    │ trunk           │      │ trunk       │     │ trunk        │
    │                 │      │             │     │              │
[ SW-A-DEIE (L2) ]   │  [ SW-A-DCEE (L2)]│ [ SW-A-DMME (L2)]  │
    │                 │      │             │     │          [ SW-A-DIS (L2) ]
  ┌─┴─┐              │    ┌─┴─┐           │   ┌─┴─┐           ┌─┴─┐
 PC0  PC1            │   PC6  PC7         │  PC4  PC5       DIS_PCs/Servers
VLAN10               │   VLAN20           │  VLAN30          VLAN40
```

---

## 5. OSPF Adjacency Summary (After Conversion)

| Adjacency           | Subnet       | Device A (IP)       | Device B (IP)         |
| ------------------- | ------------ | ------------------- | --------------------- |
| SW-Core ↔ R-CORE    | 10.0.0.0/30  | SW-Core (10.0.0.1)  | R-CORE (10.0.0.2)     |
| SW-Core ↔ SW-D-DEIE | 10.0.10.0/30 | SW-Core (10.0.10.1) | SW-D-DEIE (10.0.10.2) |
| SW-Core ↔ SW-D-DCEE | 10.0.20.0/30 | SW-Core (10.0.20.1) | SW-D-DCEE (10.0.20.2) |
| SW-Core ↔ SW-D-DMME | 10.0.30.0/30 | SW-Core (10.0.30.1) | SW-D-DMME (10.0.30.2) |

**Total OSPF neighbours on SW-Core:** 4 (R-CORE + 3 distribution switches)

---

## 6. Verification Commands & Expected Output

### 6.1 On Each Distribution Switch (SW-D-DEIE / DCEE / DMME)

#### Check `ip routing` is enabled

```
show ip route
```

**Expected:** A full routing table with `C` (connected) and `O` (OSPF) routes — NOT the "Default gateway is X" message you see on L2 switches.

#### Check routed uplink is up

```
show ip interface brief
```

**Expected:**

```
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/2     10.0.10.2       YES manual up                    up       ← routed link
Vlan10                 10.10.10.1      YES manual up                    up       ← SVI gateway
Vlan99                 10.99.99.11     YES manual up                    up       ← MGMT
```

#### Check OSPF neighbour

```
show ip ospf neighbor
```

**Expected:** One neighbour (SW-Core) in **FULL** state:

```
Neighbor ID     Pri   State       Dead Time   Address         Interface
1.1.1.1           1   FULL/...    00:00:3x    10.0.10.1       GigabitEthernet0/2
```

#### Check OSPF routes learned

```
show ip route ospf
```

**Expected:** Routes to other departments' subnets learned via OSPF:

```
O    10.10.20.0/24 [110/x] via 10.0.10.1, GigabitEthernet0/2
O    10.10.30.0/24 [110/x] via 10.0.10.1, GigabitEthernet0/2
O    10.10.40.0/24 [110/x] via 10.0.10.1, GigabitEthernet0/2
O    10.0.0.0/30   [110/x] via 10.0.10.1, GigabitEthernet0/2
```

#### Check the trunk downlink to access switch is still working

```
show interfaces trunk
```

**Expected:** Gi0/1 (or whichever port faces the access switch) is listed as trunk, carrying VLANs 10, 99, etc.

#### Check `ip default-gateway` is REMOVED

```
show running-config | include default-gateway
```

**Expected:** No output (empty). If it still shows `ip default-gateway`, it must be removed — it interferes with L3 routing.

---

### 6.2 On SW-Core

#### Check OSPF neighbours (should be 4)

```
show ip ospf neighbor
```

**Expected:**

```
Neighbor ID     Pri   State       Dead Time   Address         Interface
2.2.2.2           1   FULL/...    00:00:3x    10.0.0.2        Gi0/0      ← R-CORE
3.3.3.11          1   FULL/...    00:00:3x    10.0.10.2       Gi0/2      ← SW-D-DEIE
3.3.3.12          1   FULL/...    00:00:3x    10.0.20.2       Gi0/1      ← SW-D-DCEE
3.3.3.13          1   FULL/...    00:00:3x    10.0.30.2       Gi0/3      ← SW-D-DMME
```

#### Check routing table

```
show ip route
```

**Expected:** Mix of `C` (connected) for local /30 links + VLAN 40/99, and `O` (OSPF) for the department subnets now owned by dist switches:

```
C    10.0.0.0/30    is directly connected, GigabitEthernet0/0
C    10.0.10.0/30   is directly connected, GigabitEthernet0/2
C    10.0.20.0/30   is directly connected, GigabitEthernet0/1
C    10.0.30.0/30   is directly connected, GigabitEthernet0/3
C    10.10.40.0/24  is directly connected, Vlan40
C    10.99.99.0/24  is directly connected, Vlan99
O    10.10.10.0/24  [110/x] via 10.0.10.2, GigabitEthernet0/2
O    10.10.20.0/24  [110/x] via 10.0.20.2, GigabitEthernet0/1
O    10.10.30.0/24  [110/x] via 10.0.30.2, GigabitEthernet0/3
```

#### Verify removed SVIs are gone

```
show ip interface brief | include Vlan
```

**Expected:** Only Vlan40 and Vlan99 remain. Vlan10, Vlan20, Vlan30 should NOT appear.

---

### 6.3 End-to-End Ping Tests

Run these from a **DEIE PC** (10.10.10.10):

| Test                   | Destination                  | Command            | Expected                     |
| ---------------------- | ---------------------------- | ------------------ | ---------------------------- |
| 1. Own gateway         | 10.10.10.1 (SW-D-DEIE SVI)   | `ping 10.10.10.1`  | ✅ Success                   |
| 2. Dist switch uplink  | 10.0.10.2 (SW-D-DEIE routed) | `ping 10.0.10.2`   | ✅ Success                   |
| 3. SW-Core p2p         | 10.0.10.1 (SW-Core side)     | `ping 10.0.10.1`   | ✅ Success                   |
| 4. Inter-VLAN: DCEE PC | 10.10.20.10                  | `ping 10.10.20.10` | ✅ Success (routed via OSPF) |
| 5. Inter-VLAN: DMME PC | 10.10.30.10                  | `ping 10.10.30.10` | ✅ Success                   |
| 6. Inter-VLAN: DIS PC  | 10.10.40.10                  | `ping 10.10.40.10` | ✅ Success                   |
| 7. R-CORE              | 10.0.0.2                     | `ping 10.0.0.2`    | ✅ Success                   |
| 8. MGMT switch         | 10.99.99.12 (SW-D-DCEE)      | `ping 10.99.99.12` | ✅ Success                   |

> [!TIP]
> Run `traceroute 10.10.20.10` from a DEIE PC to verify the path goes:
> `10.10.10.1 (SW-D-DEIE) → 10.0.10.1 (SW-Core) → 10.0.20.2 (SW-D-DCEE) → 10.10.20.10 (DCEE PC)`
> This proves inter-VLAN traffic is routing through the L3 fabric correctly.

---

## 7. Inter-VLAN Routing Flow (How It Works Now)

### Example: DEIE PC (10.10.10.10) pings DCEE PC (10.10.20.10)

```
1. DEIE PC → sends to default gateway 10.10.10.1
2. SW-A-DEIE → forwards frame on trunk (VLAN 10 tagged) to SW-D-DEIE
3. SW-D-DEIE → receives on SVI Vlan10 (10.10.10.1)
   - Checks routing table
   - OSPF route: 10.10.20.0/24 via 10.0.10.1 (SW-Core)
   - Forwards packet out Gi0/2 (routed link) to SW-Core
4. SW-Core → receives on Gi0/2 (10.0.10.1)
   - Checks routing table
   - OSPF route: 10.10.20.0/24 via 10.0.20.2 (SW-D-DCEE)
   - Forwards packet out Gi0/1 (routed link) to SW-D-DCEE
5. SW-D-DCEE → receives on Gi0/2 (10.0.20.2)
   - Destination 10.10.20.10 is in locally connected VLAN 20
   - Forwards frame on trunk (VLAN 20 tagged) to SW-A-DCEE
6. SW-A-DCEE → delivers frame to DCEE PC on access port
```

### Example: DEIE PC pings DIS Server (10.10.40.10) — no dist switch for DIS

```
1. DEIE PC → gateway 10.10.10.1 (SW-D-DEIE)
2. SW-D-DEIE → OSPF route to 10.10.40.0/24 via SW-Core
3. SW-Core → 10.10.40.0/24 is directly connected (Vlan40 SVI)
4. SW-Core → delivers frame via trunk to SW-A-DIS → DIS Server
```

---

## 8. Rollback Procedure (If Something Goes Wrong)

### To revert a distribution switch back to L2:

```
enable
configure terminal

! Remove OSPF
no router ospf 1

! Remove department SVI
no interface vlan 10    ! (or 20/30 depending on switch)

! Disable routing
no ip routing

! Convert routed port back to trunk
interface GigabitEthernet 0/2   ! (or 0/0 for DMME)
 switchport
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 100
 switchport trunk allowed vlan 10,20,30,40,99,100
 no shutdown
exit

! Restore L2 default gateway
ip default-gateway 10.99.99.1

end
write memory
```

Then restore the corresponding SW-Core trunk interface and SVIs as they were before.

---

## 9. Troubleshooting Checklist

| Symptom                                                               | Likely Cause                                                                             | Fix                                                                                                              |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `show ip route` shows "Default gateway is X" instead of routing table | `ip routing` not enabled                                                                 | `configure terminal` → `ip routing`                                                                              |
| OSPF neighbour stuck at INIT / never appears                          | Routed port not up, or `passive-interface default` blocking the link                     | Check `show ip interface brief` for up/up; ensure `no passive-interface GiX/Y` is set for the correct port       |
| SVI shows `up/down`                                                   | VLAN has no active ports, or VLAN not created                                            | Check `show vlan brief` — VLAN must exist AND have at least one active port (trunk counts)                       |
| Ping from PC fails to other VLAN                                      | OSPF routes not learned, or old `ip default-gateway` still present                       | Check `show ip route ospf` for routes; check `show run                                                           | include default-gateway` to ensure it's removed |
| `ip default-gateway` and `ip routing` both present                    | Conflict — `ip default-gateway` is ignored when `ip routing` is on, but causes confusion | Remove with `no ip default-gateway`                                                                              |
| MGMT SSH from Admin PC to dist switch fails                           | VLAN 99 not carried on trunk downlink after uplink became routed                         | VLAN 99 traffic still needs to flow on the access-side trunk; verify `show interfaces trunk` on dist→access link |

---

## 10. ACL Consideration

> [!NOTE]
> The existing ACLs (ACL-DEIE-IN, ACL-DCEE-IN, etc.) were applied on SVIs at SW-Core. Since VLAN 10/20/30 SVIs are now **removed from SW-Core** and created on the distribution switches instead, you have two options:
>
> **Option A (Recommended):** Move the ACLs to the distribution switches and apply them on the new SVIs there. Each switch only needs its own department's ACL.
>
> **Option B:** Apply ACLs on the routed interfaces at SW-Core (inbound on Gi0/1, Gi0/2, Gi0/3). This keeps ACLs centralized but requires rewriting them for routed-port context.
>
> For now, the conversion configs above do **not** include ACL migration. Handle ACLs as a separate step after verifying basic L3 connectivity works.
