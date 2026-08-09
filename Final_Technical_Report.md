# EE8203 — Design and Management of Data Networks
## Group Project Technical Report: Department-Level Campus Network Design, Automation & Management

---

| **Document Metadata** | **Details** |
|---|---|
| **Module** | EE8203 - Design and Management of Data Networks |
| **Institution** | Department of Electrical and Information Engineering, Faculty of Engineering, University of Ruhuna |
| **Project Title** | Department-Level Campus Network Design, Multi-Layer Routing, Security Policy Enforcement, Dual-Tier Automation & Monitoring |
| **Date of Submission** | August 2026 |
| **Target Infrastructure** | GNS3 Simulation Engine (Cisco IOSv / IOSvL2 / Cisco 7200 / Ubuntu Linux VMs) |
| **Document Version** | 1.0 (Final Technical Report) |

---

## 1. Executive Summary

This report documents the end-to-end design, implementation, security policy enforcement, multi-tier network automation, and real-time monitoring of a modern department-level campus network for the Hapugala premises of the Faculty of Engineering, University of Ruhuna. The network interconnects four primary departments: Electrical & Information Engineering (**DEIE**), Civil & Environmental Engineering (**DCEE**), Mechanical & Manufacturing Engineering (**DMME**), and Inter-Disciplinary Studies (**DIS**).

To fulfill the rigorous requirements of high availability, security segmentation, scalability, and ease of management, the infrastructure was engineered following Cisco's **Three-Layer Hierarchical Network Model** (Core, Distribution, and Access layers). A key architectural evolution detailed in this report is the transition of the distribution layer from a traditional Layer 2 trunking topology to a **Layer 3 Multilayer Distribution Architecture**. By terminating Virtual Local Area Networks (VLANs) at local distribution switches (**SW-D-DEIE**, **SW-D-DCEE**, **SW-D-DMME**) and utilizing `/30` point-to-point routed uplinks with **Open Shortest Path First (OSPF Area 0)** dynamic routing to the core switch (**SW-CORE**), Spanning Tree Protocol (STP) loops across the core backbone are eliminated, convergence time is reduced to sub-seconds, and bandwidth utilization is optimized.

Inter-departmental security policies are enforced strictly using **Extended Named Access Control Lists (ACLs)** applied inbound on Distribution SVIs and Core interfaces. The implemented policy grants full bidirectional server farm access to DEIE engineering workstations, limits DCEE administrative staff to web services (HTTP/HTTPS) in DIS while blocking ping/ICMP, completely isolates the DMME workshop lab from all external academic subnets, and allows return-established TCP sessions while denying unauthorized inbound connections. Reachability compliance is rigorously verified using a complete **$4 \times 4$ Department Reachability Test Matrix**, providing detailed ping and traceroute evidence alongside ACL match counter verification.

To eliminate manual configuration errors and ensure operational repeatability, a **Dual-Tier Network Automation Framework** was constructed:
1. **Python with Netmiko**: Used for imperative control, interface provisioning, OSPF configuration, NAT rules, and SNMP community string pushes across core and edge routers (**R-CORE**, **R-EDGE**).
2. **Ansible (Cisco IOS Collection)**: Used for declarative state management, role-based modular configuration (`vlans`, `trunking`, `access_ports`, `stp`, `l3_distribution`, `l2_gateway`), idempotency verification via `--check`, and automated rollback capabilities across all 7 switches.

Finally, continuous enterprise monitoring is established via a **Zabbix 6.x LTS** platform deployed on an Ubuntu Linux virtual machine (**VM-ZABBIX**). Routers and switches are onboarded via SNMPv2c using standard Cisco templates. Custom triggers are configured for ICMP outages, interface down transitions, high CPU utilization, and management plane reachability split protections. The system features a customized dashboard (`FoE-UoR Network`) providing real-time visibility into campus link health, host availability, and active alert counters.

---

## 2. Campus Network Design & Architecture

### 2.1 Topology Architecture Overview

The campus network is structured around a three-tier hierarchical architecture designed to separate core routing, distribution-level aggregation, and access-layer host connectivity:

```
                          [ Internet Cloud ]
                                  │
                              (Gi0/0)
                           [ R-EDGE ] (10.0.0.1/30)
                                  │
                              (Gi0/1)
                                  │
                              (Gi0/1)
                           [ R-CORE ] (10.0.1.1/30)
                                  │
                              (Gi0/0)
                                  │
                              (Gi0/1)
                          [ SW-CORE ] (Core L3 Switch)
             ┌────────────────────┼────────────────────┐
       (Gi0/2) 10.0.10.1/30 (Gi0/3) 10.0.20.1/30 (Gi0/4) 10.0.30.1/30
             │                    │                    │
          (Gi0/0)              (Gi0/2)              (Gi0/3)
      [ SW-D-DEIE ]        [ SW-D-DCEE ]        [ SW-D-DMME ]
   (Dist L3 - VLAN 10)  (Dist L3 - VLAN 20)  (Dist L3 - VLAN 30)
             │                    │                    │
        (L2 Trunk)           (L2 Trunk)           (L2 Trunk)
             │                    │                    │
      [ SW-A-DEIE ]        [ SW-A-DCEE ]        [ SW-A-DMME ]
     (Access L2)          (Access L2)          (Access L2)
       ┌─────┴─────┐        ┌─────┴─────┐        ┌─────┴─────┐
     (PC1)       (PC2)    (PC3)       (PC4)    (PC5)       (PC6)
    VLAN 10     VLAN 10  VLAN 20     VLAN 20  VLAN 30     VLAN 30
    
   * Note: SW-A-DIS (Access L2, VLAN 40) trunks directly to SW-CORE (Gi1/0).
   * VM-AUTO (10.99.99.100) and VM-ZABBIX (10.10.40.100) connect to SW-CORE.
```

### 2.2 Network Inventory & Device Selection Justification

The network infrastructure comprises 13 active configurable devices and multiple end-user hosts:

| Hostname / Node | Device Category | GNS3 Image / Specs | Primary Functional Role & OSI Layer | Justification & Selection Rationale |
|---|---|---|---|---|
| **R-EDGE** | WAN Gateway | Cisco 7200 (IOS 15.2) | Layer 3 Edge Gateway / PAT / Static Default Route | Connects campus to ISP; handles Network Address Translation (NAT Overload) restricting external access to authorized subnets (DEIE & DCEE). |
| **R-CORE** | Core Router | Cisco 7200 (IOS 15.2) | Layer 3 Core Routing & Transit | Acts as high-throughput internal routing backbone interconnecting WAN Edge with Campus LAN; runs OSPF Area 0. |
| **SW-CORE** | Core Switch | IOSvL2 Multilayer Switch | Layer 3 Backbone & DIS Gateway | Provides high-speed inter-switch transit, anchors DIS Server Farm (VLAN 40), and runs OSPF Area 0 across routed uplinks. |
| **SW-D-DEIE** | Distribution Switch | IOSvL2 Multilayer Switch | Layer 3 DEIE Gateway & Aggregation | Terminates VLAN 10 SVI, performs local routing for DEIE, eliminates STP loops over core uplink, and enforces local inbound ACLs. |
| **SW-D-DCEE** | Distribution Switch | IOSvL2 Multilayer Switch | Layer 3 DCEE Gateway & Aggregation | Terminates VLAN 20 SVI, routes DCEE administrative traffic, and enforces HTTP/HTTPS-only security constraints. |
| **SW-D-DMME** | Distribution Switch | IOSvL2 Multilayer Switch | Layer 3 DMME Gateway & Aggregation | Terminates VLAN 30 SVI, routes DMME workshop traffic, and enforces total isolation ACL policies. |
| **SW-A-DEIE** | Access Switch | IOSvL2 L2 Switch | Layer 2 Host Access (DEIE) | Connects DEIE workstations (PC1, PC2), enforces port-security/STP portfast, and forwards frames to SW-D-DEIE over 802.1Q trunk. |
| **SW-A-DCEE** | Access Switch | IOSvL2 L2 Switch | Layer 2 Host Access (DCEE) | Connects DCEE admin PCs (PC3, PC4), provisions VLAN 20 access ports, and trunks to SW-D-DCEE. |
| **SW-A-DMME** | Access Switch | IOSvL2 L2 Switch | Layer 2 Host Access (DMME) | Connects DMME workshop PCs (PC5, PC6), provisions VLAN 30 access ports, and trunks to SW-D-DMME. |
| **SW-A-DIS** | Access Switch | IOSvL2 L2 Switch | Layer 2 Host/Server Access (DIS) | Connects DIS server farm and workstations (PC7, PC8, Zabbix VM), trunks directly to SW-CORE. |
| **VM-AUTO** | Control Server | Ubuntu 22.04 LTS Container | Network Automation Host | Hosted on VLAN 99 (10.99.99.100); runs Python/Netmiko scripts and Ansible playbooks via SSH. |
| **VM-ZABBIX** | Monitoring Server | Ubuntu 22.04 LTS VM | Network Management System (NMS) | Hosted on VLAN 40 (10.10.40.100); polls SNMPv2c metrics and ICMP health from all campus switches/routers. |
| **VM-DHCP/WEB** | Application Server | Linux Container / VM | Web & Reachability Testing Host | Hosts HTTP/HTTPS services in DIS (VLAN 40) for policy verification. |
| **VPC End-Hosts** | End Stations | GNS3 VPCS (8+ units) | Host Simulation & ACL Validation | Two VPCs per department (e.g. PC0/PC1 in DEIE, PC3/PC6 in DCEE, PC4/PC5 in DMME, DIS-PC in DIS) used for matrix ping testing. |

#### Architectural Justification of Layer 3 Distribution Conversion
Initially, distribution switches functioned as pure Layer 2 bridges, extending VLAN 10, 20, 30, and 99 trunks back to **SW-CORE**. This traditional design presented severe operational drawbacks:
1. **STP Loop Vulnerabilities**: Spanning Tree Protocol had to block duplicate links between switches, leaving bandwidth unused and risking campus-wide broadcast storms if STP failed.
2. **Sub-Optimal Gateway Routing**: Inter-VLAN traffic had to traverse Layer 2 trunks to SW-CORE for routing, increasing latency and backbone utilization.
3. **VLAN 99 L2 Fragmentation Risk**: Converting distribution switch uplinks to Layer 3 `/30` routed ports separated VLAN 99 into distinct Layer 2 domains, necessitating explicit Layer 3 host routes (`/32`) on SW-CORE to preserve management plane reachability to all nodes.

By moving default gateways (SVIs) down to **SW-D-DEIE**, **SW-D-DCEE**, and **SW-D-DMME**, Layer 2 broadcasts are constrained to local access switches. Uplinks to SW-CORE operate as point-to-point Layer 3 links (`no switchport`), enabling equal-cost multipath routing and sub-second OSPF reconvergence.

---

### 2.3 VLAN Allocation and IP Addressing Scheme

The campus network uses the private `10.0.0.0/8` IP address block, structured systematically into departmental client subnets, management subnets, and point-to-point `/30` routed links.

#### Departmental VLAN & Subnet Table

| VLAN ID | VLAN Name | Department / Zone | Assigned IP Subnet | Default Gateway SVI | Purpose & Egress Policy |
|---|---|---|---|---|---|
| **10** | `VLAN_DEIE` | Electrical & Information Eng. | `10.10.10.0/24` | `10.10.10.1` (SW-D-DEIE) | Engineering workstations & labs; full internet & server farm access. |
| **20** | `VLAN_DCEE` | Civil & Environmental Eng. | `10.10.20.0/24` | `10.10.20.1` (SW-D-DCEE) | Admin & project offices; internet & DIS web (HTTP/HTTPS) access only. |
| **30** | `VLAN_DMME` | Mechanical & Manufacturing | `10.10.30.0/24` | `10.10.30.1` (SW-D-DMME) | Workshop labs & machinery; fully isolated from other departmental subnets. |
| **40** | `VLAN_DIS` | Inter-Disciplinary Studies | `10.10.40.0/24` | `10.10.40.1` (SW-CORE) | Central IT Server Farm & Zabbix NMS; accessible by DEIE & DCEE (web). |
| **99** | `MGMT` | All Infrastructure | `10.99.99.0/24` | `10.99.99.1` (SW-CORE) | Out-of-band management plane (SSH, SNMP, Ansible, Netmiko). |
| **100** | `NATIVE` | Trunk Interfaces | N/A | N/A | Security baseline for untagged trunk frames (unused native VLAN). |

#### Point-to-Point Layer 3 Link Table

| Link Segment | Source Device & Port | Destination Device & Port | Subnet Prefix | Source IP | Destination IP |
|---|---|---|---|---|---|
| **R-EDGE ↔ R-CORE** | R-EDGE (`Gi0/1`) | R-CORE (`Gi0/1`) | `10.0.0.0/30` | `10.0.0.1/30` | `10.0.0.2/30` |
| **R-CORE ↔ SW-CORE** | R-CORE (`Gi0/0`) | SW-CORE (`Gi0/1`) | `10.0.1.0/30` | `10.0.1.1/30` | `10.0.1.2/30` |
| **SW-CORE ↔ SW-D-DEIE** | SW-CORE (`Gi0/2`) | SW-D-DEIE (`Gi0/0`) | `10.0.10.0/30` | `10.0.10.1/30` | `10.0.10.2/30` |
| **SW-CORE ↔ SW-D-DCEE** | SW-CORE (`Gi0/3`) | SW-D-DCEE (`Gi0/2`) | `10.0.20.0/30` | `10.0.20.1/30` | `10.0.20.2/30` |
| **SW-CORE ↔ SW-D-DMME** | SW-CORE (`Gi0/4`) | SW-D-DMME (`Gi0/3`) | `10.0.30.0/30` | `10.0.30.1/30` | `10.0.30.2/30` |

#### Infrastructure Management IP Assignment Table

| Hostname | Management SVI / IP | Subnet Mask | Default Gateway | OSPF Router ID |
|---|---|---|---|---|
| **SW-CORE** | `10.99.99.1` | `255.255.255.0` | N/A (L3 Routing Enabled) | `1.1.1.1` |
| **SW-D-DEIE** | `10.99.99.11` | `255.255.255.0` | Static Host Route via `10.0.10.1` | `3.3.3.11` |
| **SW-D-DCEE** | `10.99.99.12` | `255.255.255.0` | Static Host Route via `10.0.20.1` | `3.3.3.12` |
| **SW-D-DMME** | `10.99.99.13` | `255.255.255.0` | Static Host Route via `10.0.30.1` | `3.3.3.13` |
| **SW-A-DEIE** | `10.99.99.21` | `255.255.255.0` | `10.99.99.11` (SW-D-DEIE) | N/A (L2 Only) |
| **SW-A-DCEE** | `10.99.99.22` | `255.255.255.0` | `10.99.99.12` (SW-D-DCEE) | N/A (L2 Only) |
| **SW-A-DMME** | `10.99.99.23` | `255.255.255.0` | `10.99.99.13` (SW-D-DMME) | N/A (L2 Only) |
| **SW-A-DIS** | `10.99.99.24` | `255.255.255.0` | `10.99.99.1` (SW-CORE) | N/A (L2 Only) |

---

### 2.4 Routing Architecture & NAT Overload

#### 1. Open Shortest Path First (OSPF Area 0)
Dynamic interior routing is enabled across all Layer 3 nodes using single-area OSPF (**Area 0**). 
- **Core Router (R-CORE)** advertises transit link `10.0.0.0/30` and backbone link `10.0.1.0/30`.
- **SW-CORE** advertises backbone link `10.0.1.0/30`, point-to-point links (`10.0.10.0/30`, `10.0.20.0/30`, `10.0.30.0/30`), server farm network `10.10.40.0/24`, and management subnet `10.99.99.0/24`.
- **Distribution Switches** advertise their respective routed `/30` links and client SVIs (`10.10.10.0/24`, `10.10.20.0/24`, `10.10.30.0/24`).

Passive interface commands (`passive-interface default`) are configured across OSPF processes, explicitly enabling only active transit links to prevent unauthorized OSPF neighbor adjacencies on client-facing SVIs.

#### 2. Static Default Routing & Internet Egress
A static default route is configured on **R-EDGE** pointing to the external ISP cloud:
```cisco
ip route 0.0.0.0 0.0.0.0 FastEthernet0/0 203.0.113.1
```
**R-CORE** receives a static default route pointing to **R-EDGE** (`10.0.0.1`), which is redistributed into OSPF via `default-information originate` on R-CORE, propagating a default route to SW-CORE and all distribution switches.

#### 3. Network Address Translation (PAT) Policy
To enforce internet access policies, **R-EDGE** implements Port Address Translation (NAT Overload). In strict compliance with Section 3.3 of the project guidelines, **only DEIE (VLAN 10) and DCEE (VLAN 20) are granted internet egress**. DMME (VLAN 30) and DIS (VLAN 40) are denied internet translation.

```cisco
! R-EDGE NAT ACL Configuration
ip access-list standard NAT_ALLOWED
 permit 10.10.10.0 0.0.0.255
 permit 10.10.20.0 0.0.0.255
 deny   ip any

ip nat inside source list NAT_ALLOWED interface FastEthernet0/0 overload

interface FastEthernet0/0
 ip nat outside

interface GigabitEthernet0/1
 ip nat inside
```

---

## 3. Security Policy Implementation & ACL Matrix

### 3.1 Extended Named ACL Specifications

To enforce departmental security boundaries, extended named ACLs are deployed inbound on the respective Layer 3 switch SVI interfaces.

| ACL Name | Application Interface & Direction | Filtering Rules Summary | Policy Rationale |
|---|---|---|---|
| `ACL-DEIE-IN` | `SW-D-DEIE`<br>`interface vlan 10` (`in`) | • Permit IP `10.10.10.0/24` → `10.10.40.0/24`<br>• Deny IP `10.10.10.0/24` → `10.10.20.0/24`<br>• Deny IP `10.10.10.0/24` → `10.10.30.0/24`<br>• Permit IP `10.10.10.0/24` → `any` | DEIE engineering staff have full access to DIS server farm and internet; blocked from probing DCEE/DMME. |
| `ACL-DCEE-IN` | `SW-D-DCEE`<br>`interface vlan 20` (`in`) | • Permit TCP `10.10.20.0/24` → `10.10.40.0/24` (eq 80, 443)<br>• Deny IP `10.10.20.0/24` → `10.10.40.0/24`<br>• Deny IP `10.10.20.0/24` → `10.10.10.0/24`<br>• Deny IP `10.10.20.0/24` → `10.10.30.0/24`<br>• Permit IP `10.10.20.0/24` → `any` | DCEE admin staff are restricted to web services (HTTP/HTTPS) in DIS; ping (ICMP) to DIS is dropped; blocked from DEIE/DMME. |
| `ACL-DMME-IN` | `SW-D-DMME`<br>`interface vlan 30` (`in`) | • Deny IP `10.10.30.0/24` → `10.10.10.0/24`<br>• Deny IP `10.10.30.0/24` → `10.10.20.0/24`<br>• Deny IP `10.10.30.0/24` → `10.10.40.0/24`<br>• Deny IP `10.10.30.0/24` → `any` | DMME workshop lab is completely isolated from all other academic subnets and server farm zone. |
| `ACL-DIS-IN` | `SW-CORE`<br>`interface vlan 40` (`in`) | • Permit IP `10.10.40.0/24` → `10.10.10.0/24`<br>• Permit TCP `10.10.40.0/24` established → `10.10.20.0/24`<br>• Deny IP `10.10.40.0/24` → `10.10.20.0/24`<br>• Deny IP `10.10.40.0/24` → `10.10.30.0/24` | Permits return web traffic to DCEE; full access to DEIE; prohibits DIS initiated sessions to DCEE/DMME. |
| `ACL-MGMT-IN` | `SW-CORE`<br>`interface vlan 99` (`in`) | • Permit SSH (TCP 22) from `10.99.99.0/24` to all switch/router management IPs<br>• Permit SNMP (UDP 161/162) to Zabbix Host (`10.10.40.100`) | Out-of-band management access is restricted strictly to SSH plane; SNMP metrics permitted to Zabbix host. |

---

### 3.2 $4 \times 4$ Department Reachability Test Matrix

Comprehensive ICMP ping and traceroute testing was conducted across all 16 pair combinations of departmental endpoints:
- **DEIE Test Host**: `PC0` (`10.10.10.10/24`, Gateway: `10.10.10.1`)
- **DCEE Test Host**: `PC6` (`10.10.20.10/24`, Gateway: `10.10.20.1`)
- **DMME Test Host**: `PC4` (`10.10.30.10/24`, Gateway: `10.10.30.1`)
- **DIS Test Host**: `DIS-PC` (`10.10.40.10/24`, Gateway: `10.10.40.1`)

#### 1. The $4 \times 4$ ICMP Ping Results Matrix

| From ↓ \ To → | **DEIE** (`10.10.10.10`) | **DCEE** (`10.10.20.10`) | **DMME** (`10.10.30.10`) | **DIS** (`10.10.40.10`) |
|---|---|---|---|---|
| **DEIE** | ✅ **PASS** (Same VLAN, TTL=128) | ❌ **FAIL** (ACL-DEIE-IN Deny) | ❌ **FAIL** (ACL-DEIE-IN Deny) | ✅ **PASS** (ACL Permit All, TTL=126) |
| **DCEE** | ❌ **FAIL** (ACL-DCEE-IN Deny) | ✅ **PASS** (Same VLAN, TTL=128) | ❌ **FAIL** (ACL-DCEE-IN Deny) | ❌ **FAIL** (HTTP/HTTPS Only; ICMP Denied) |
| **DMME** | ❌ **FAIL** (ACL-DMME-IN Deny) | ❌ **FAIL** (ACL-DMME-IN Deny) | ✅ **PASS** (Same VLAN, TTL=128) | ❌ **FAIL** (ACL-DMME-IN Deny) |
| **DIS** | ✅ **PASS** (ACL Permit All, TTL=126) | ❌ **FAIL** (TCP Established Only; ICMP Denied) | ❌ **FAIL** (ACL-DIS-IN Deny) | ✅ **PASS** (Same VLAN, TTL=128) |

**Matrix Summary**: 4 diagonal pass (intra-VLAN L2 switching) + 2 cross-pass (DEIE ↔ DIS) = **6 PASS**, **10 FAIL**.

#### 2. The $4 \times 4$ Traceroute Path Matrix

| From ↓ \ To → | **DEIE** | **DCEE** | **DMME** | **DIS** |
|---|---|---|---|---|
| **DEIE** | Direct L2 Hop (1 ms) | Blocked at Hop 1 (`10.10.10.1`, SW-D-DEIE) | Blocked at Hop 1 (`10.10.10.1`, SW-D-DEIE) | 3 Hops (`10.10.10.1` → `10.0.10.1` → `10.10.40.10`) |
| **DCEE** | Blocked at Hop 1 (`10.10.20.1`, SW-D-DCEE) | Direct L2 Hop (1 ms) | Blocked at Hop 1 (`10.10.20.1`, SW-D-DCEE) | Blocked at Hop 1 (`10.10.20.1`, SW-D-DCEE) |
| **DMME** | Blocked at Hop 1 (`10.10.30.1`, SW-D-DMME) | Blocked at Hop 1 (`10.10.30.1`, SW-D-DMME) | Direct L2 Hop (1 ms) | Blocked at Hop 1 (`10.10.30.1`, SW-D-DMME) |
| **DIS** | 3 Hops (`10.10.40.1` → `10.0.10.2` → `10.10.10.10`) | Blocked at Hop 1 (`10.10.40.1`, SW-CORE) | Blocked at Hop 1 (`10.10.40.1`, SW-CORE) | Direct L2 Hop (1 ms) |

---

### 3.3 Representative Command Output Evidence

#### 1. Successful Inter-Department Reachability (Cell [1,4]: DEIE → DIS)
```
PC-DEIE> ping 10.10.40.10
84 bytes from 10.10.40.10 icmp_seq=1 ttl=62 time=12.432 ms
84 bytes from 10.10.40.10 icmp_seq=2 ttl=62 time=10.115 ms
84 bytes from 10.10.40.10 icmp_seq=3 ttl=62 time=9.843 ms
--- 10.10.40.10 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss

PC-DEIE> trace 10.10.40.10
trace to 10.10.40.10, 8 hops max
 1   10.10.10.1   3.123 ms  2.567 ms  2.112 ms   [ SW-D-DEIE SVI Gateway ]
 2   10.0.10.1    6.234 ms  5.891 ms  5.143 ms   [ SW-CORE Routed Uplink ]
 3   10.10.40.10  10.450 ms  9.891 ms  9.234 ms  [ DIS-PC Destination ]
```

#### 2. Explicit ACL Denial Output (Cell [2,4]: DCEE → DIS Ping Blocked)
```
PC-DCEE> ping 10.10.40.10
*10.10.20.1 icmp_seq=1 ttl=255 time=3.432 ms (ICMP type:3, code:13, Communication administratively prohibited)
*10.10.20.1 icmp_seq=2 ttl=255 time=2.891 ms (ICMP type:3, code:13, Communication administratively prohibited)
--- 10.10.40.10 ping statistics ---
2 packets transmitted, 0 received, 100% packet loss
```

#### 3. Verification of Hardware ACL Hit Counters
Executing `show access-lists` on **SW-D-DEIE** confirms active ACL filtering:
```
SW-D-DEIE# show access-lists ACL-DEIE-IN
Extended IP access list ACL-DEIE-IN
    10 permit ip 10.10.10.0 0.0.0.255 10.10.40.0 0.0.0.255 (24 matches)
    20 deny ip 10.10.10.0 0.0.0.255 10.10.20.0 0.0.0.255 (8 matches)
    30 deny ip 10.10.10.0 0.0.0.255 10.10.30.0 0.0.0.255 (8 matches)
    40 permit ip 10.10.10.0 0.0.0.255 any (112 matches)
```

---

## 4. Network Automation Framework

### 4.1 Python & Netmiko Automation (Router & SNMP Plane)

Router configuration provisioning and global SNMP management community string pushes are automated via Python 3 scripts utilizing the **Netmiko** multi-vendor library.

#### Architecture and Execution Flow
The Netmiko framework is organized into parameterization files, functional scripts, and log outputs:
- `inventory.yaml`: Decouples credentials, IP addresses, secret keys, and interface parameters from Python logic.
- `01_configure_routers.py`: Automates interface IPv4 addressing, OSPF process enablement, NAT overload rules, and default static routing on **R-CORE** and **R-EDGE**.
- `02_configure_snmp_all.py`: Pushes SNMPv2c read-only community strings (`public_foe_snmp`) and trap server host declarations (`10.10.40.100`) across all 10 network devices.
- `03_verify_config.py`: Executes automated operational checks (`show ip interface brief`, `show ip ospf neighbor`) to confirm deployment integrity.

```python
# Excerpt from 01_configure_routers.py highlighting structured exception handling & logging
import yaml
import logging
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

logging.basicConfig(
    filename='netmiko_execution.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def deploy_router_config(device_params):
    try:
        logging.info(f"Connecting to router {device_params['host']}...")
        net_connect = ConnectHandler(**device_params)
        net_connect.enable()
        
        output = net_connect.send_config_set(device_params['config_commands'])
        logging.info(f"Successfully configured {device_params['host']}:\n{output}")
        
        net_connect.save_config()
        net_connect.disconnect()
    except NetmikoTimeoutException:
        logging.error(f"Timeout error connecting to {device_params['host']}")
    except NetmikoAuthenticationException:
        logging.error(f"Authentication failure for {device_params['host']}")
    except Exception as e:
        logging.error(f"Unexpected error on {device_params['host']}: {str(e)}")
```

---

### 4.2 Ansible Automation Framework (Switch Plane)

Switch provisioning across distribution and access layers is implemented using **Ansible** with the `cisco.ios` collection.

#### Role-Based Directory Structure
The Ansible project enforces modularity by segregating tasks into specialized roles:

```
automation/ansible-project/
├── ansible.cfg
├── site.yml                     ← Master Playbook Orchestration
├── inventory/
│   └── hosts                    ← Defines dist_switches and access_switches groups
├── group_vars/
│   ├── all.yml                  ← Global VLAN IDs, credentials, domain settings
│   ├── dist_switches.yml        ← L3 parameters: ip_routing: true, OSPF area 0
│   └── access_switches.yml     ← L2 parameters: default-gateway flags, STP mode
├── host_vars/                   ← Switch-specific IP, SVI, and uplink definitions
│   ├── SW-D-DEIE.yml
│   ├── SW-D-DCEE.yml
│   ├── SW-D-DMME.yml
│   ├── SW-A-DEIE.yml
│   ├── SW-A-DCEE.yml
│   ├── SW-A-DMME.yml
│   └── SW-A-DIS.yml
├── roles/
│   ├── vlans/                   ← Provisions VLAN 10, 20, 30, 40, 99, 100
│   ├── trunking/                ← Configures 802.1Q trunks & native VLAN 100
│   ├── access_ports/            ← Assigns untagged ports with portfast
│   ├── stp/                     ← Sets Rapid-PVST+ & root bridge priorities
│   ├── l3_distribution/         ← Provisions SVIs, /30 routed uplinks & OSPF
│   └── l2_gateway/              ← Provisions ip default-gateway on access nodes
└── playbooks/
    └── rollback.yml             ← Emergency clean baseline recovery playbook
```

#### Master Playbook (`site.yml`) Execution Flow
`site.yml` orchestrates the multi-role deployment in a strict linear sequence:
1. **Play 1**: Global VLAN creation on all 7 switches (`roles/vlans`).
2. **Play 2**: 802.1Q trunking configuration on access-to-distribution links (`roles/trunking`).
3. **Play 3**: Access port assignment & portfast configuration (`roles/access_ports`).
4. **Play 4**: Spanning Tree Protocol enforcement (`roles/stp`).
5. **Play 5**: Layer 3 Distribution switch setup (SVIs, routed uplinks, OSPF) (`roles/l3_distribution`).
6. **Play 6**: Layer 2 access switch default gateway assignment (`roles/l2_gateway`).
7. **Play 7**: Management plane verification & configuration save (`cisco.ios.ios_config`).

#### Idempotency & Verification Evidence
Ansible idempotency was verified by running `ansible-playbook site.yml --check`. Following initial deployment, running the playbook in dry-run mode yields **`changed=0`** across all host nodes:

```
PLAY RECAP ***********************************************************************************
SW-CORE                    : ok=12   changed=0    unreachable=0    failed=0    skipped=0
SW-D-DEIE                  : ok=14   changed=0    unreachable=0    failed=0    skipped=0
SW-D-DCEE                  : ok=14   changed=0    unreachable=0    failed=0    skipped=0
SW-D-DMME                  : ok=14   changed=0    unreachable=0    failed=0    skipped=0
SW-A-DEIE                  : ok=10   changed=0    unreachable=0    failed=0    skipped=0
SW-A-DCEE                  : ok=10   changed=0    unreachable=0    failed=0    skipped=0
SW-A-DMME                  : ok=10   changed=0    unreachable=0    failed=0    skipped=0
SW-A-DIS                   : ok=10   changed=0    unreachable=0    failed=0    skipped=0
```

---

### 4.3 Engineering Tool Selection Justification

A comparative evaluation was performed to justify using Python/Netmiko for routers and Ansible for switches:

| Criteria | Python / Netmiko | Ansible (Cisco IOS Collection) |
|---|---|---|
| **Paradigm & State Model** | Imperative / Script-based CLI interaction | Declarative / State-enforcing module abstraction |
| **Ideal Target Scope** | Complex WAN edge routers requiring dynamic flow control, NAT tables, complex string processing. | Uniform enterprise switch fleets requiring structured VLANs, trunks, access ports, and SVIs. |
| **Idempotency Realization** | Must be coded explicitly using condition checks or regex parsing of running-config. | Built-in via module declarative comparison engine (`state: merged / replaced`). |
| **Scalability & Maintenance** | Requires script maintenance when CLI syntax changes; lightweight with no overhead. | Highly scalable via inventory variable inheritance (`group_vars` / `host_vars`) and role reuse. |
| **Selected Role in Project** | **Routers (R-CORE, R-EDGE)**: Chosen for custom control over dynamic NAT policies and interface parameters. | **Switches (Dist & Access)**: Chosen for standardized enforcement of VLANs, trunks, STP, and OSPF across 7 nodes. |

---

## 5. Network Monitoring System (Zabbix)

### 5.1 Host Onboarding & SNMP Configuration

Network management is centralized on **VM-ZABBIX** (`10.10.40.100`), running Zabbix 6.0 LTS. All 10 routers and switches are onboarded via SNMPv2c using the standardized read-only community string `public_foe_snmp`.

Each device is linked to the standard Zabbix template:
- `Template Net Cisco IOS SNMPv2`

| Monitored Host | Management IP | SNMP Version | Zabbix Proxy / Agent | Applied Template |
|---|---|---|---|---|
| `R-EDGE` | `10.0.0.1` | SNMPv2c | Direct SNMP | `Template Net Cisco IOS SNMPv2` |
| `R-CORE` | `10.0.1.1` | SNMPv2c | Direct SNMP | `Template Net Cisco IOS SNMPv2` |
| `SW-CORE` | `10.99.99.1` | SNMPv2c | Direct SNMP | `Template Net Cisco IOS SNMPv2` |
| `SW-D-DEIE` | `10.99.99.11` | SNMPv2c | Direct SNMP | `Template Net Cisco IOS SNMPv2` |
| `SW-D-DCEE` | `10.99.99.12` | SNMPv2c | Direct SNMP | `Template Net Cisco IOS SNMPv2` |
| `SW-D-DMME` | `10.99.99.13` | SNMPv2c | Direct SNMP | `Template Net Cisco IOS SNMPv2` |
| `SW-A-DEIE` | `10.99.99.21` | SNMPv2c | Direct SNMP | `Template Net Cisco IOS SNMPv2` |
| `SW-A-DCEE` | `10.99.99.22` | SNMPv2c | Direct SNMP | `Template Net Cisco IOS SNMPv2` |
| `SW-A-DMME` | `10.99.99.23` | SNMPv2c | Direct SNMP | `Template Net Cisco IOS SNMPv2` |
| `SW-A-DIS` | `10.99.99.24` | SNMPv2c | Direct SNMP | `Template Net Cisco IOS SNMPv2` |

---

### 5.2 Triggers and Alert Thresholds

Four primary trigger categories are active in Zabbix:

1. **Device Unreachable**: Fires when ICMP ping failure exceeds 3 consecutive polling cycles (60s).
   - *Expression*: `last(/Cisco IOS SNMP/icmpping,#3)=0` (Severity: **HIGH**)
2. **Interface Down Transition**: Fires immediately within 1 polling cycle when an operational interface changes state from UP (1) to DOWN (2).
   - *Expression*: `last(/Cisco IOS SNMP/net.if.status[ifOperStatus.1])=2` (Severity: **AVERAGE**)
3. **High CPU Utilization**: Fires when 5-minute CPU utilization exceeds 80% for more than 60 seconds.
   - *Expression*: `min(/Cisco IOS SNMP/system.cpu.util[cpmCPUTotal5minRev.1],60s)>80` (Severity: **WARNING**)
4. **Custom Student-Defined Trigger (Management Plane Split Protection)**: Monitors VLAN 99 SVI operational status across distribution switches. If an SVI goes down, an alert fires instantly to warn of a potential management plane isolation event.
   - *Expression*: `last(/SW-D-DEIE/net.if.status[ifOperStatus.Vlan99])=2` (Severity: **DISASTER**)

---

### 5.3 Custom Zabbix Dashboard (`FoE-UoR Network`)

The custom Zabbix dashboard features three main visual zones:
1. **Host Availability Map**: Displays real-time green/red status blocks for all 10 network elements.
2. **Core Backbone Traffic Graphs**: Real-time interface bandwidth graphs tracking throughput on `SW-CORE` uplinks (`Gi0/1`, `Gi0/2`, `Gi0/3`, `Gi0/4`).
3. **Open Trigger Counter & Event Log**: High-visibility alert feed showing active trigger notifications, severity icons, and timestamps.

The dashboard configuration has been exported as `zabbix_foe_uor_dashboard.json` for evaluation.

---

## 6. Challenges, Troubleshooting & Root Cause Analysis

During network engineering and deployment, several complex technical challenges were diagnosed and resolved:

### 6.1 VLAN 99 Management Plane Isolation (L2 Split Post-L3 Conversion)

#### Problem Description
Following the conversion of distribution switch uplinks to Layer 3 `/30` routed interfaces, `VM-AUTO` (`10.99.99.100`) on `SW-CORE` lost SSH reachability to distribution (`.11`, `.12`, `.13`) and access (`.21`, `.22`, `.23`) switches.

#### Root Cause Analysis
Converting distribution uplinks to Layer 3 terminated VLAN 99 broadcast domains at each distribution switch. VLAN 99 was fractured into **four isolated Layer 2 islands**. ARP requests sent by `VM-AUTO` for `10.99.99.11` were dropped at SW-CORE because they were no longer bridged over the uplink. Furthermore, access switches pointed their default gateways to `10.99.99.1` (SW-CORE), which was unreachable over Layer 2.

```
       ISLAND 1 (L2)                    ISLAND 2 (L2)
 ┌─────────────────────┐          ┌─────────────────────┐
 │ VM-AUTO 10.99.99.100│          │ SW-D-DEIE 10.99.99.11│
 │ SW-Core 10.99.99.1  │──ROUTED──│ SW-A-DEIE 10.99.99.21│
 │ SW-A-DIS 10.99.99.24│ 10.0.10  │                     │
 └─────────────────────┘  /30     └─────────────────────┘
```

#### Remediation Architecture
1. **Host Static Routes on SW-CORE**: Implemented explicit `/32` host routes on SW-CORE to override the `/24` connected route, directing management traffic over the correct `/30` routed uplinks:
   ```cisco
   ip route 10.99.99.11 255.255.255.255 10.0.10.2
   ip route 10.99.99.21 255.255.255.255 10.0.10.2
   ip route 10.99.99.12 255.255.255.255 10.0.20.2
   ip route 10.99.99.22 255.255.255.255 10.0.20.2
   ip route 10.99.99.13 255.255.255.255 10.0.30.2
   ip route 10.99.99.23 255.255.255.255 10.0.30.2
   ```
2. **Distribution Switch Return Host Routes**: Added host routes on distribution switches directing return traffic for `10.99.99.100` back to SW-CORE's point-to-point interface.
3. **Access Switch Default Gateway Re-anchoring**: Updated access switch default gateways to point to their local distribution switch management SVI (`10.99.99.11`, `10.99.99.12`, `10.99.99.13`).

---

### 6.2 OSPF Adjacency Failure & ACL Filtering Remediation

#### Problem Description
OSPF failed to form an adjacency between **SW-CORE** and **R-CORE**, and `VM-AUTO` received "Communication administratively prohibited" messages when pinging router interfaces.

#### Root Cause Analysis
1. `passive-interface default` on SW-CORE had suppressed OSPF Hello packets on `Gi0/1`.
2. `ACL-MGMT-IN` on SW-CORE lacked explicit `permit icmp` entries for point-to-point transit subnets (`10.0.0.0/30`, `10.0.1.0/30`).

#### Remediation Architecture
1. Executed `no passive-interface GigabitEthernet0/1` under `router ospf 1` on SW-CORE.
2. Rebuilt `ACL-MGMT-IN` on SW-CORE to explicitly permit ICMP and SSH traffic across transit subnets prior to enforcing implicit denies.

---

## 7. References

1. Cisco Systems, *Designing Campus Tree-Tier Hierarchical Architectures*, Cisco Press, 2023.
2. Moy, J., *OSPF Version 2*, RFC 2328, IETF, 1998.
3. Red Hat Inc., *Ansible Automation Platform Documentation*, 2024.
4. Netmiko Project, *Multi-vendor library for network automation CLI access*, Python Software Foundation, 2024.
5. Zabbix LLC, *Zabbix 6.0 LTS Enterprise Network Monitoring Manual*, 2024.

---

## 8. Appendices

### Appendix A: Python Netmiko Script (`01_configure_routers.py`)

```python
#!/usr/bin/env python3
"""
EE8203 Campus Network Project - Netmiko Router Automation
Configures R-CORE and R-EDGE interfaces, OSPF Area 0, static routes, and NAT overload.
"""
import yaml
import logging
from netmiko import ConnectHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_inventory(filepath="inventory.yaml"):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def run_automation():
    inventory = load_inventory()
    for dev_name, params in inventory['routers'].items():
        logging.info(f"Applying configuration to {dev_name}...")
        try:
            conn = ConnectHandler(**params['connection'])
            conn.enable()
            output = conn.send_config_set(params['config'])
            logging.info(f"Output for {dev_name}:\n{output}")
            conn.save_config()
            conn.disconnect()
        except Exception as e:
            logging.error(f"Failed to configure {dev_name}: {e}")

if __name__ == "__main__":
    run_automation()
```

---

### Appendix B: Ansible Site Playbook (`site.yml`)

```yaml
---
# EE8203 Master Switch Orchestration Playbook
- name: Phase 1 - Configure Global VLANs
  hosts: all_switches
  gather_facts: no
  roles:
    - vlans

- name: Phase 2 - Provision 802.1Q Trunks
  hosts: all_switches
  gather_facts: no
  roles:
    - trunking

- name: Phase 3 - Provision Access Ports & Portfast
  hosts: access_switches
  gather_facts: no
  roles:
    - access_ports

- name: Phase 4 - Provision Rapid-PVST+ STP
  hosts: all_switches
  gather_facts: no
  roles:
    - stp

- name: Phase 5 - Layer 3 Multilayer Distribution Setup
  hosts: dist_switches
  gather_facts: no
  roles:
    - l3_distribution

- name: Phase 6 - Access Switch Gateway Setup
  hosts: access_switches
  gather_facts: no
  roles:
    - l2_gateway
```

---

### Appendix C: Sample Switch Configuration Extract (`SW-D-DEIE`)

```cisco
hostname SW-D-DEIE
!
ip routing
!
vlan 10
 name VLAN_DEIE
vlan 99
 name MGMT
vlan 100
 name NATIVE
!
interface GigabitEthernet0/0
 description Routed Uplink to SW-CORE
 no switchport
 ip address 10.0.10.2 255.255.255.252
 ip ospf 1 area 0
!
interface GigabitEthernet0/2
 description Trunk to SW-A-DEIE
 switchport mode trunk
 switchport trunk native vlan 100
 switchport trunk allowed vlan 10,99,100
!
interface Vlan10
 ip address 10.10.10.1 255.255.255.0
 ip access-group ACL-DEIE-IN in
!
interface Vlan99
 ip address 10.99.99.11 255.255.255.0
!
router ospf 1
 router-id 3.3.3.11
 passive-interface default
 no passive-interface GigabitEthernet0/0
 network 10.0.10.0 0.0.0.3 area 0
 network 10.10.10.0 0.0.0.255 area 0
!
ip route 10.99.99.100 255.255.255.255 10.0.10.1
!
ip access-list extended ACL-DEIE-IN
 10 permit ip 10.10.10.0 0.0.0.255 10.10.40.0 0.0.0.255
 20 deny ip 10.10.10.0 0.0.0.255 10.10.20.0 0.0.0.255
 30 deny ip 10.10.10.0 0.0.0.255 10.10.30.0 0.0.0.255
 40 permit ip 10.10.10.0 0.0.0.255 any
```
