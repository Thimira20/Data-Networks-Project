# Walkthrough: Campus Network Device Configurations

We have generated individual Cisco IOS configuration files (`.txt`) for all 11 devices in the campus network topology. Each file contains a complete sequence of commands to set up naming, local AAA credentials, SSH, SNMPv2c, VLANs, trunks, spanning tree parameters, SVIs/interfaces, dynamic routing (OSPF), NAT translation, and inter-VLAN ACLs.

## Generated Files

Here are links to the generated configuration files in your project directory:

### 1. Core Backbone
- [SW-Core.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/SW-Core.txt) - Layer-3 Collapsed Core Switch configuration. Includes SVIs, inter-VLAN routing, and extended ACLs.
- [R-CORE.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/R-CORE.txt) - Core Router configuration connecting the campus backbone to the edge.
- [R-EDGE.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/R-EDGE.txt) - Edge Router configuration providing WAN/Internet access and NAT overload.

### 2. Department-Specific Layer-2 Switches
- **DEIE (VLAN 10):**
  - [SW-D-DEIE.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/SW-D-DEIE.txt) - Distribution Switch.
  - [SW-A-DEIE.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/SW-A-DEIE.txt) - Access Switch (Fa0/1-2 assigned to VLAN 10).
- **DCEE (VLAN 20):**
  - [SW-D-DCEE.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/SW-D-DCEE.txt) - Distribution Switch.
  - [SW-A-DCEE.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/SW-A-DCEE.txt) - Access Switch (Fa0/1-2 assigned to VLAN 20).
- **DMME (VLAN 30):**
  - [SW-D-DMME.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/SW-D-DMME.txt) - Distribution Switch.
  - [SW-A-DMME.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/SW-A-DMME.txt) - Access Switch (Fa0/2-3 assigned to VLAN 30).
- **DIS (VLAN 40 - Server Farm):**
  - [SW-D-DIS.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/SW-D-DIS.txt) - Distribution Switch.
  - [SW-A-DIS.txt](file:///d:/8th%20sem/DAta%20Networks/Project/VLAN_CONFIG/SW-A-DIS.txt) - Access Switch (Fa0/2-3 assigned to VLAN 40).

---

## Technical Configuration Highlights

### 1. Inter-VLAN Routing & Collapsed Core Design
- **Gateway SVIs** are placed on the collapsed core switch `SW-Core`:
  - `Vlan 10` = `10.10.10.1` (DEIE)
  - `Vlan 20` = `10.10.20.1` (DCEE)
  - `Vlan 30` = `10.10.30.1` (DMME)
  - `Vlan 40` = `10.10.40.1` (DIS)
  - `Vlan 99` = `10.99.99.1` (MGMT)
- `ip routing` is enabled on `SW-Core` to handle inter-VLAN routing internally.
- Distribution and Access switches operate purely as Layer-2 switches with a default gateway: `ip default-gateway 10.99.99.1`.

### 2. Departmental Traffic Filtering (Extended ACLs)
The ACLs are applied **inbound** on the SVIs of `SW-Core` to filter traffic at the first Layer-3 boundary:
- **DEIE (`ACL-DEIE-IN`)**: Permits traffic to DIS (`10.10.40.0/24`) and any external destination (Internet). Denies access to DCEE (`10.10.20.0/24`), DMME (`10.10.30.0/24`), and MGMT (`10.99.99.0/24`).
- **DCEE (`ACL-DCEE-IN`)**: Permits HTTP/HTTPS (tcp ports 80/443) to DIS (`10.10.40.0/24`) and any external destination (Internet). Denies all other traffic to internal subnets.
- **DMME (`ACL-DMME-IN`)**: Denies all traffic to all internal subnets and the Internet. Completely isolated.
- **DIS (`ACL-DIS-IN`)**: Permits incoming established sessions back to DCEE, normal traffic to DEIE, and lets `VM-ZABBIX` (`10.10.40.100`) send SNMP (UDP 161) and ICMP (ping) to all management and router subnets.
- **MGMT (`ACL-MGMT-IN`)**: Restricts SSH (TCP 22) traffic only to the MGMT subnet and the router subnets.

### 3. Dynamic Routing & PAT (NAT Overload)
- **OSPF Process 1 (Single Area 0)** is configured on `SW-Core`, `R-CORE`, and `R-EDGE`.
- OSPF routes are propagated between `SW-Core` ↔ `R-CORE` ↔ `R-EDGE`.
- **Edge Internet & NAT (PAT)**:
  - `R-EDGE` interface `Gig0/0/1` obtains its IP dynamically via DHCP from the ISP/Internet Cloud and is marked as `ip nat outside`.
  - `R-EDGE` interface `Gig0/0/0` is marked as `ip nat inside`.
  - OSPF default route propagation is enabled on `R-EDGE` using `default-information originate`.
  - The standard access list `NAT_ACL` matches only DEIE (`10.10.10.0/24`) and DCEE (`10.10.20.0/24`) networks. This access list is translated using `ip nat inside source list NAT_ACL interface gigabitEthernet 0/0/1 overload`.

---

## Deployment & Verification Instructions

### 1. Copy-Paste Deployment
For each device in Packet Tracer:
1. Open the device's CLI console.
2. Enter privileged exec mode (`enable`).
3. Copy the entire contents of the respective `.txt` file and paste it directly into the CLI console.
4. Verify there are no syntax errors during parsing.

### 2. Verification Command Cheat Sheet
- **Check Interfaces**: `show ip interface brief` (verify all VLAN interfaces and physical links show `up / up`).
- **Check VLANs & Trunks**: 
  - `show vlan brief`
  - `show interfaces trunk` (native VLAN 100 should show on active switchport trunks).
- **Check Routing Table & OSPF**:
  - `show ip route` (verify connected and OSPF learned routes).
  - `show ip ospf neighbor` (verify state is `FULL` between `SW-Core` ↔ `R-CORE` and `R-CORE` ↔ `R-EDGE`).
- **Check NAT Translations (on R-EDGE)**:
  - `show ip nat translations`
  - `show ip nat statistics`

### 3. Access Control matrix (Expected Results)
| Source PC | Destination IP | Traffic Type | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **DEIE PC** (`10.10.10.10`) | **DIS Server** (`10.10.40.10`) | Any | **Success** |
| **DEIE PC** (`10.10.10.10`) | **DCEE PC** (`10.10.20.10`) | Any | **Blocked** |
| **DEIE PC** (`10.10.10.10`) | **Internet** (`8.8.8.8`) | Any | **Success** (NAT Overloaded via R-EDGE) |
| **DCEE PC** (`10.10.20.10`) | **DIS Web Server** (`10.10.40.10`) | HTTP/HTTPS | **Success** |
| **DCEE PC** (`10.10.20.10`) | **DIS Web Server** (`10.10.40.10`) | Ping / ICMP | **Blocked** |
| **DCEE PC** (`10.10.20.10`) | **Internet** (`8.8.8.8`) | Any | **Success** (NAT Overloaded via R-EDGE) |
| **DMME PC** (`10.10.30.10`) | **DIS Server** (`10.10.40.10`) | Any | **Blocked** |
| **DMME PC** (`10.10.30.10`) | **Internet** (`8.8.8.8`) | Any | **Blocked** (no NAT overload permit) |
| **VM-Zabbix** (`10.10.40.100`) | **SW-A-DEIE** (`10.99.99.21`) | SNMP (UDP 161) | **Success** |
