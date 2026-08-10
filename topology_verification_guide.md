# Quick Topology Verification & Testing Guide
## Campus Data Network — FoE-UoR Network Project

This simple quick-reference guide provides exact **Ping tests**, **SSH commands**, **Verification commands**, and **Protocol checks** tailored to your GNS3 campus network topology.

---

## 1. Quick Device IP Cheat Sheet

| Device | Device Type | Management IP (VLAN 99) | Gateway / Role |
| :--- | :--- | :--- | :--- |
| **R-CORE** | Core Router | `10.0.0.2` (Fa1/0) | OSPF Core & LAN Interconnect |
| **R-EDGE** | Edge Router | `10.0.1.1` (Fa0/0) | WAN Gateway & NAT |
| **SW-Core** | Core L3 Switch | `10.99.99.1` (Vlan99 SVI) | L3 Core & Central ACL Enforcement |
| **SW-D-DEIE** | Distribution L3 | `10.99.99.11` (Vlan99 SVI) | Gateway for DEIE (`10.10.10.1`) |
| **SW-D-DCEE** | Distribution L3 | `10.99.99.12` (Vlan99 SVI) | Gateway for DCEE (`10.10.20.1`) |
| **SW-D-DMME** | Distribution L3 | `10.99.99.13` (Vlan99 SVI) | Gateway for DMME (`10.10.30.1`) |
| **SW-A-DEIE** | Access L2 | `10.99.99.21` (Vlan99 SVI) | Access ports for PC1, PC2 (VLAN 10) |
| **SW-A-DCEE** | Access L2 | `10.99.99.22` (Vlan99 SVI) | Access ports for PC3, PC4 (VLAN 20) |
| **SW-A-DMME** | Access L2 | `10.99.99.23` (Vlan99 SVI) | Access ports for PC5, PC6 (VLAN 30) |
| **SW-A-DIS** | Access L2 | `10.99.99.24` (Vlan99 SVI) | Access ports for PC7, PC8, Zabbix (VLAN 40) |

---

## 2. SSH Management Commands

From **Ubuntu Management Terminal**, SSH into any device using credentials `admin` / `admin123`:

```bash
# Core & Edge Routers
ssh admin@10.0.0.2      # R-CORE
ssh admin@10.0.1.1      # R-EDGE

# Core & Distribution Switches
ssh admin@10.99.99.1    # SW-Core
ssh admin@10.99.99.11   # SW-D-DEIE
ssh admin@10.99.99.12   # SW-D-DCEE
ssh admin@10.99.99.13   # SW-D-DMME

# Access Switches
ssh admin@10.99.99.21   # SW-A-DEIE
ssh admin@10.99.99.22   # SW-A-DCEE
ssh admin@10.99.99.23   # SW-A-DMME
ssh admin@10.99.99.24   # SW-A-DIS
```

---

## 3. End-to-End Ping Connectivity Matrix

Run these pings from VPCS / End hosts in GNS3:

### Test 1: Department PC to Gateway (Default Gateway Check)
* **From PC1 (DEIE):** `ping 10.10.10.1`  *(Success - 100%)*
* **From PC3 (DCEE):** `ping 10.10.20.1`  *(Success - 100%)*
* **From PC5 (DMME):** `ping 10.10.30.1`  *(Success - 100%)*
* **From PC7 (DIS):**  `ping 10.10.40.1`  *(Success - 100%)*

### Test 2: Department PC to DIS Server Farm (Allowed Traffic)
* **From PC1 (DEIE):** `ping 10.10.40.10` *(Success - 100%)*

### Test 3: Inter-Department Isolation (ACL Block Test)
* **From PC1 (DEIE):** `ping 10.10.20.10`
  * **Expected Result:** `*10.10.10.1 ... Communication administratively prohibited` *(ICMP Type 3 Code 13 - Proves ACL is working!)*
* **From PC1 (DEIE):** `ping 10.10.30.10`
  * **Expected Result:** `*10.10.10.1 ... Communication administratively prohibited`

### Test 4: WAN & Internet Reachability
* **From Ubuntu Terminal / R-CORE:** `ping 8.8.8.8` *(Success - Tests NAT & ISP Link)*

---

## 4. Protocol Verification Commands (Cisco CLI)

Run these commands inside Cisco CLI (`enable` mode) to verify each network protocol:

### A. Verify OSPF Dynamic Routing
```cisco
show ip ospf neighbor
# Expected: All neighbors show status 'FULL/BDR' or 'FULL/DR'

show ip route ospf
# Expected: Displays routes learned via OSPF (10.0.x.x, 10.10.x.x, 10.99.99.0/24)
```

### B. Verify Layer 2 Trunking & VLANs
```cisco
show vlan brief
# Expected: VLANs 10, 20, 30, 40, 99, 100 display status 'active' (NOT act/lshut)

show interfaces trunk
# Expected: Trunk status 'trunking', Native VLAN 100, Allowed VLANs 10,20,30,40,99,100
```

### C. Verify Spanning Tree Protocol (STP)
```cisco
show spanning-tree summary
# Expected: Mode is Rapid-PVST

show spanning-tree vlan 10
# Expected on Distribution switches: 'This bridge is the root' for department VLAN
# Expected on Access switches: Root port points uplink to Distribution switch
```

### D. Verify Access Control Lists (ACLs)
```cisco
show ip access-lists
# Expected: Displays match counters increasing for permit/deny rules

show ip interface Vlan10
# Expected: Inbound access list is set (e.g., 'Inbound access list is ACL_DEIE_IN')
```

### E. Verify SNMP Monitoring Telemetry
```cisco
show run | include snmp
# Expected:
#   snmp-server community public RO
#   snmp-server host 10.10.40.100 version 2c public
```

---

## 5. Zabbix Monitoring Quick Check

1. **Open Zabbix Web UI:** `http://10.10.40.100/zabbix` (or `http://192.168.255.128:9090/zabbix`)
2. **Navigate to:** **Monitoring → Hosts**
3. **Verify:**
   * `R-CORE`, `R-EDGE`, `SW-Core` → 🟢 **Green (SNMP)**
   * `SW-D-DEIE`, `SW-D-DCEE`, `SW-D-DMME` → 🟢 **Green (SNMP)**
   * `SW-A-DEIE`, `SW-A-DCEE`, `SW-A-DMME`, `SW-A-DIS` → 🟢 **Green (SNMP)**
