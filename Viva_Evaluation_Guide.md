# Data Networks Project — Comprehensive Viva & Evaluation Master Guide

**Course:** EE8203/EC8205 Design & Management of Data Networks  
**Department:** Electrical and Information Engineering / Computer Engineering, University of Ruhuna  

---

## Table of Contents
1. [Executive Summary & Campus Network Topology](#1-executive-summary--campus-network-topology)
2. [Step-by-Step Network Build & Command Breakdown](#2-step-by-step-network-build--command-breakdown)
   - [Phase 1: Physical Naming & VLAN Database](#phase-1-physical-naming--vlan-database)
   - [Phase 2: Access Ports & Spanning-Tree PortFast](#phase-2-access-ports--spanning-tree-portfast)
   - [Phase 3: Trunk Links & 802.1Q Encapsulation](#phase-3-trunk-links--8021q-encapsulation)
   - [Phase 4: Inter-VLAN Routing & SVIs](#phase-4-inter-vlan-routing--svis)
   - [Phase 5: Layer 2 vs. Layer 3 Distribution Architecture Shift](#phase-5-layer-2-vs-layer-3-distribution-architecture-shift)
   - [Phase 6: OSPF Dynamic Routing Configuration](#phase-6-ospf-dynamic-routing-configuration)
   - [Phase 7: Edge Router, WAN, & NAT Overload (PAT)](#phase-7-edge-router-wan--nat-overload-pat)
   - [Phase 8: Access Control Lists (ACLs) & Security Policy](#phase-8-access-control-lists-acls--security-policy)
   - [Phase 9: Management Plane (VLAN 99) & Zabbix NMS Monitoring](#phase-9-management-plane-vlan-99--zabbix-nms-monitoring)
3. [Network Automation Deep Dive: Netmiko vs. Ansible](#3-network-automation-deep-dive-netmiko-vs-ansible)
   - [Netmiko Automation Suite (Python Procedural)](#netmiko-automation-suite-python-procedural)
   - [Ansible Automation Suite (YAML Declarative Infrastructure-as-Code)](#ansible-automation-suite-yaml-declarative-infrastructure-as-code)
4. [Top 20 Viva Questions & Winning Answers](#4-top-20-viva-questions--winning-answers)

---

## 1. Executive Summary & Campus Network Topology

### 1.1 Verified Topology Diagram (Matching `topology.png`)

```
                                [ NAT1 Cloud ]
                                      │ (nat0)
                                      │
                                    (f1/0)
                                [   R-EDGE   ]  (WAN Edge Router)
                                    (f0/0)
                                      │
                                      │
                                    (f0/0)
                                [   R-CORE   ]  (Core Router)
                                    (f1/0)
                                      │
                                      │
                                    (Gi0/1)
                          ┌───── [  SW-CORE  ] ─────┬──────────────┐
                          │    (Gi0/0) (Gi0/2) (Gi0/3)             │ (Gi1/1)
                          │        │       │       │               │
                          │   (Gi0/0)   (Gi0/2)  (Gi0/3)      [ UbuntuDockerGuest-1 ]
                          │   SW-D-DEIE SW-D-DCEE SW-D-DMME      (Ansible/Netmiko Host)
                          │   (Gi0/2)   (Gi0/0)  (Gi0/0)           (eth0 - 10.99.99.100)
                          │        │       │       │
                          │   (Gi0/1)   (Gi0/0)  (Gi0/0)
                          │   SW-A-DEIE SW-A-DCEE SW-A-DMME
                          │   ┌───┴───┐ ┌───┴───┐ ┌───┴───┐
                          │  PC1     PC2 PC3   PC4 PC5   PC6
                          │  (VLAN10)   (VLAN20)  (VLAN30)
                          │
                          │ (Gi1/0)
                          └───────────┐
                                   (Gi1/0)
                                 [ SW-A-DIS ]  (DIS Access Switch — No Dist Switch!)
                                 ┌────┴────┐
                                PC7       PC8 (Or VM-ZABBIX NMS @ 10.10.40.100)
                              (VLAN40)  (VLAN40)
```

### 1.2 Master Port Interconnection Table (From `topology.png`)

| Source Device | Source Interface | Target Device | Target Interface | Link Type / Subnet / Role |
| :--- | :--- | :--- | :--- | :--- |
| **NAT1** | `nat0` | `R-EDGE` | `f1/0` | WAN Egress (Public IP / DHCP) |
| **R-EDGE** | `f0/0` | **R-CORE** | `f0/0` | Router-to-Router P2P (`10.0.0.4/30`) |
| **R-CORE** | `f1/0` | **SW-CORE** | `Gi0/1` | Core Router to Core Switch P2P (`10.0.0.0/30`) |
| **SW-CORE** | `Gi1/1` | **UbuntuDockerGuest-1**| `eth0` | Access Port (VLAN 99 MGMT - `10.99.99.100`) |
| **SW-CORE** | `Gi0/0` | **SW-D-DEIE** | `Gi0/0` | L3 Routed Link (`10.0.10.0/30`) |
| **SW-CORE** | `Gi0/2` | **SW-D-DCEE** | `Gi0/2` | L3 Routed Link (`10.0.20.0/30`) |
| **SW-CORE** | `Gi0/3` | **SW-D-DMME** | `Gi0/3` | L3 Routed Link (`10.0.30.0/30`) |
| **SW-CORE** | `Gi1/0` | **SW-A-DIS** | `Gi1/0` | L2 Trunk Link (VLAN 40 DIS & VLAN 99 MGMT) |
| **SW-D-DEIE**| `Gi0/2` | **SW-A-DEIE** | `Gi0/1` | L2 Trunk Link (VLAN 10 & 99) |
| **SW-D-DCEE**| `Gi0/0` | **SW-A-DCEE** | `Gi0/0` | L2 Trunk Link (VLAN 20 & 99) |
| **SW-D-DMME**| `Gi0/0` | **SW-A-DMME** | `Gi0/0` | L2 Trunk Link (VLAN 30 & 99) |
| **SW-A-DEIE**| `Gi0/0` / `Gi0/2` | **PC1** / **PC2** | `e0` / `e0` | Access Ports (VLAN 10 DEIE) |
| **SW-A-DCEE**| `Gi0/1` / `Gi0/2` | **PC3** / **PC4** | `e0` / `e0` | Access Ports (VLAN 20 DCEE) |
| **SW-A-DMME**| `Gi0/1` / `Gi0/2` | **PC5** / **PC6** | `e0` / `e0` | Access Ports (VLAN 30 DMME) |
| **SW-A-DIS** | `Gi0/1` / `Gi0/0` | **PC7** / **PC8 (Zabbix)**| `e0` / `e0` | Access Ports (VLAN 40 DIS) |

---

### 1.3 Master Addressing & VLAN Table

| VLAN ID | Subnet | Gateway IP | Dedicated Department / Purpose |
| :--- | :--- | :--- | :--- |
| **10** | `10.10.10.0/24` | `10.10.10.1` | **VLAN_DEIE** (Dept. of Electrical & Information Eng.) |
| **20** | `10.10.20.0/24` | `10.10.20.1` | **VLAN_DCEE** (Dept. of Civil & Environmental Eng.) |
| **30** | `10.10.30.0/24` | `10.10.30.1` | **VLAN_DMME** (Dept. of Mechanical & Mfg. Eng.) |
| **40** | `10.10.40.0/24` | `10.10.40.1` | **VLAN_DIS** (Dept. of Interdisciplinary Studies / Server Farm) |
| **99** | `10.99.99.0/24` | `10.99.99.1` | **MGMT** (Out-of-Band Management Plane for SSH/SNMP) |
| **100**| *None* | *None* | **NATIVE** (Unused Native VLAN for 802.1Q Security) |

### 1.4 Management IP Scheme (VLAN 99)

| Device Role | Hostname | Management IP | Gateway |
| :--- | :--- | :--- | :--- |
| Core Router | `R-CORE` | `10.99.99.254` (or `10.0.0.2` router link) | — |
| Edge Router | `R-EDGE` | `10.99.99.253` (or `10.0.0.6` router link) | — |
| Core L3 Switch | `SW-CORE` | `10.99.99.1` | Self (L3 Gateway) |
| Dist Switches | `SW-D-DEIE`, `DCEE`, `DMME` | `10.99.99.11`, `.12`, `.13` | `10.99.99.1` |
| Access Switches | `SW-A-DEIE`, `DCEE`, `DMME`, `DIS` | `10.99.99.21`, `.22`, `.23`, `.24` | `10.99.99.1` |
| Automation Host| `UbuntuDockerGuest-1` | `10.99.99.100` | `10.99.99.1` |

---

## 2. Step-by-Step Network Build & Command Breakdown

### Phase 1: Physical Naming & VLAN Database
#### What we did:
Configured distinct hostnames for all devices and created VLANs 10, 20, 30, 40, 99, and 100 on every switch.

#### Commands & Explanation:
```cisco
configure terminal
 hostname SW-A-DEIE
 vlan 10
  name VLAN_DEIE
 vlan 20
  name VLAN_DCEE
 vlan 30
  name VLAN_DMME
 vlan 40
  name VLAN_DIS
 vlan 99
  name MGMT
 vlan 100
  name NATIVE
end
write memory
```
* **Why `hostname`?** Uniquely identifies the device in prompt, logs, syslog messages, and SSH terminal.
* **Why create VLANs on ALL switches?** Switched traffic tagged with a VLAN ID will be dropped by a switch if that VLAN ID does not exist in its local VLAN database (`vlan.dat`).
* **Why VLAN 100 NATIVE?** IEEE 802.1Q sends untagged frames over the native VLAN. By default, Cisco uses VLAN 1. Leaving native VLAN as VLAN 1 opens vulnerability to **VLAN Hopping Attacks** (Double Tagging). Moving the native VLAN to an unused VLAN (VLAN 100) disables untagged traffic on production VLANs.

---

### Phase 2: Access Ports & Spanning-Tree PortFast
#### What we did:
Assigned PC-facing switchports to their respective department VLANs and enabled PortFast.

#### Commands & Explanation:
```cisco
configure terminal
 interface range gigabitEthernet 0/0 - 2
  switchport mode access
  switchport access vlan 10
  spanning-tree portfast
end
write memory
```
* **`switchport mode access`**: Forces the port to operate as an untagged access port (only belongs to one single VLAN). Disables Dynamic Trunking Protocol (DTP) negotiation to prevent rogue trunk negotiation.
* **`switchport access vlan 10`**: Assigns ingress untagged packets on this physical port to VLAN 10.
* **`spanning-tree portfast`**: Bypasses the Spanning Tree Protocol (STP) Listening and Learning states (which take 30 seconds: 15s listening + 15s learning) and immediately moves the port to the Forwarding state.
  * **Why?** End-user PCs do not cause switching loops. Delaying port startup by 30s can cause DHCP timeouts or PXE boot failures on client PCs.

---

### Phase 3: Trunk Links & 802.1Q Encapsulation
#### What we did:
Configured switch-to-switch links as 802.1Q trunks, carrying multiple department VLANs with Native VLAN 100.

#### Commands & Explanation (Example: `SW-A-DEIE Gi0/1` ↔ `SW-D-DEIE Gi0/2`):
```cisco
configure terminal
 interface gigabitEthernet 0/1
  switchport trunk encapsulation dot1q
  switchport mode trunk
  switchport trunk native vlan 100
  switchport trunk allowed vlan 10,20,30,40,99,100
end
write memory
```
* **`switchport trunk encapsulation dot1q`**: Defines IEEE 802.1Q as the framing format for tagging VLAN headers onto Ethernet frames (4-byte VLAN tag inserted into Ethernet header).
* **`switchport mode trunk`**: Sets the port into permanent trunking mode.
* **`switchport trunk native vlan 100`**: Specifies that untagged frames traversing this trunk link belong to VLAN 100.
* **`switchport trunk allowed vlan ...`**: Prunes unnecessary VLANs from traversing the link, saving link bandwidth and switch memory.

---

### Phase 4: Inter-VLAN Routing & SVIs
#### What we did:
Created Switch Virtual Interfaces (SVIs) on Layer 3 switches to serve as default gateways for each subnet, and enabled IP routing.

#### Commands & Explanation:
```cisco
configure terminal
 ip routing

 interface vlan 10
  ip address 10.10.10.1 255.255.255.0
  no shutdown
 interface vlan 20
  ip address 10.10.20.1 255.255.255.0
  no shutdown
 interface vlan 99
  ip address 10.99.99.1 255.255.255.0
  no shutdown
end
```
* **`ip routing`**: Globally enables the Layer 3 IP routing engine in Cisco IOS on multilayer switches. Without this command, the switch only acts as a Layer 2 bridge and will NOT route packets between SVIs.
* **`interface vlan X`**: Creates an SVI (Switch Virtual Interface), a virtual L3 interface representing a VLAN.
* **`ip address 10.10.10.1 255.255.255.0`**: Assigns the IP address that acts as the **Default Gateway** for host PCs in VLAN 10.
* **SVI Operational Status Rule**: An SVI stays `up/up` ONLY if:
  1. The VLAN exists in the VLAN database (`show vlan brief`).
  2. At least one physical port assigned to that VLAN (access or trunk) is active (`up/up`) and in STP forwarding state.

---

### Phase 5: Layer 2 vs. Layer 3 Distribution Architecture Shift
#### What we did:
Initially, all distribution switches operated at Layer 2 (L2 trunks to `SW-CORE`). We upgraded distribution switches (`SW-D-DEIE`, `SW-D-DCEE`, `SW-D-DMME`) to **Layer 3 Multilayer Switches**.

#### Comparison Matrix:

| Feature | Initial L2 Distribution Design | Advanced L3 Distribution Design |
| :--- | :--- | :--- |
| **Uplinks (Dist ↔ Core)** | L2 Trunk carrying all VLANs | **Routed Ports (`no switchport`)** with `/30` point-to-point subnets |
| **Inter-VLAN Routing** | Centralized on `SW-CORE` | **Distributed**: Each Dist switch routes its local VLAN |
| **STP Loop Exposure** | Spanning Tree spans from Access to Core | **STP blocked at Dist switch**; Uplinks are routed L3 links (no STP loops!) |
| **Gateways** | Hosted on `SW-CORE` | Hosted locally on local Distribution Switches |
| **Routing Protocols** | OSPF only between `SW-CORE` & `R-CORE` | **OSPF runs on Distribution Switches + SW-CORE + Routers** |

#### Converting Trunk to Routed Point-to-Point Link (Matching `topology.png`):
```cisco
! On SW-CORE (facing SW-D-DEIE)
interface gigabitEthernet 0/0
 no switchport
 ip address 10.0.10.1 255.255.255.252
 no shutdown

! On SW-D-DEIE (facing SW-CORE)
interface gigabitEthernet 0/0
 no switchport
 ip address 10.0.10.2 255.255.255.252
 no shutdown
```
* **`no switchport`**: Converts a Layer 2 switchport interface into a pure Layer 3 routed port (like a router interface). Disables L2 features (VLANs, STP, DTP, trunking) on this interface.
* **`255.255.255.252` (`/30` subnet)**: Provides exactly 2 usable IP addresses (`.1` and `.2`), conserving IP address space for point-to-point links.

---

### Phase 6: OSPF Dynamic Routing Configuration
#### What we did:
Configured OSPF (Open Shortest Path First) Area 0 to dynamically exchange routing tables across the campus backbone.

#### Commands & Explanation:
```cisco
! On SW-CORE
configure terminal
 router ospf 1
  router-id 1.1.1.1
  network 10.0.0.0 0.0.0.3 area 0      ! Link to R-CORE (f1/0 ↔ Gi0/1)
  network 10.0.10.0 0.0.0.3 area 0     ! Link to SW-D-DEIE (Gi0/0)
  network 10.0.20.0 0.0.0.3 area 0     ! Link to SW-D-DCEE (Gi0/2)
  network 10.0.30.0 0.0.0.3 area 0     ! Link to SW-D-DMME (Gi0/3)
  network 10.10.40.0 0.0.0.255 area 0   ! DIS VLAN 40
  network 10.99.99.0 0.0.0.255 area 0   ! MGMT VLAN 99
  passive-interface default
  no passive-interface gigabitEthernet 0/1
  no passive-interface gigabitEthernet 0/0
  no passive-interface gigabitEthernet 0/2
  no passive-interface gigabitEthernet 0/3
end
```
* **`router ospf 1`**: Enables OSPF process ID 1 (local significance on the device).
* **`router-id 1.1.1.1`**: Uniquely identifies the router in the OSPF Link-State Database (LSDB).
* **Wildcard Mask (`0.0.0.255`)**: OSPF uses inverted subnet masks.
  * Subnet Mask `/24` = `255.255.255.0`
  * Wildcard Mask = `255.255.255.255 - 255.255.255.0` = `0.0.0.255`.
  * `0` means "must match bit exactly", `255` means "ignore bit".
* **`passive-interface default` & `no passive-interface <int>`**:
  * **Why?** By default, OSPF sends Hello packets out of ALL interfaces matching `network` statements. Sending OSPF Hellos onto PC access VLANs or user ports is a **security risk** (unauthorized router injection) and wastes CPU/bandwidth.
  * `passive-interface default` blocks OSPF Hello packets on all interfaces, while still advertising their connected subnets into OSPF.
  * `no passive-interface <int>` selectively enables OSPF Hello exchanges ONLY on router-to-router / switch-to-switch links.

---

### Phase 7: Edge Router, WAN, & NAT Overload (PAT)
#### What we did:
Connected `R-EDGE` to the NAT1 Cloud (`f1/0`) and configured Network Address Translation (NAT Overload) to translate internal private IPs (`10.x.x.x`) into a single public IP.

#### Commands & Explanation (Exact interfaces from `topology.png`):
```cisco
! On R-EDGE
configure terminal
 interface fastEthernet 0/0
  description Connected to R-CORE (f0/0)
  ip address 10.0.0.6 255.255.255.252
  ip nat inside
  no shutdown

 interface fastEthernet 1/0
  description Connected to NAT1 Cloud (nat0)
  ip address 203.0.113.2 255.255.255.252
  ip nat outside
  no shutdown

! Define which subnets are allowed to access Internet (DEIE & DCEE per policy)
 access-list 1 permit 10.10.10.0 0.0.0.255
 access-list 1 permit 10.10.20.0 0.0.0.255

! Enable NAT Overload (Port Address Translation - PAT)
 ip nat inside source list 1 interface fastEthernet 1/0 overload

! Static Default Route to ISP
 ip route 0.0.0.0 0.0.0.0 203.0.113.1

! Redistribute Default Route into OSPF so campus devices learn WAN route
 router ospf 1
  default-information originate
end
```
* **`ip nat inside` / `ip nat outside`**: Identifies LAN-facing interfaces (`inside`) and WAN-facing interfaces (`outside`).
* **`overload` keyword (PAT)**: Allows thousands of private IP addresses to share a single public IP address by mapping internal IP + Source TCP/UDP Port to Public IP + Unique Translator Port.
* **`default-information originate`**: Instructs OSPF to inject a default route (`0.0.0.0/0`) into OSPF Area 0, telling `R-CORE` and `SW-CORE` to forward all external Internet traffic towards `R-EDGE`.

---

### Phase 8: Access Control Lists (ACLs) & Security Policy
#### What we did:
Deployed Extended Access Control Lists to enforce inter-department security policies.

#### Policy Requirements & ACL Structure:

| Department | Permitted Traffic Destinations | Denied Traffic |
| :--- | :--- | :--- |
| **DEIE (VLAN 10)** | DCEE, DMME, DIS, Internet WAN, MGMT | None (Full Access) |
| **DCEE (VLAN 20)** | DEIE, DIS, Internet WAN | DMME (VLAN 30) |
| **DMME (VLAN 30)** | DEIE, DIS | DCEE (VLAN 20), Internet WAN |
| **DIS (VLAN 40)** | All internal VLANs (Server Farm) | Internet WAN egress |

#### Sample Extended ACL (`ACL-DCEE-IN`):
```cisco
ip access-list extended ACL-DCEE-IN
 remark --- Deny DCEE access to DMME ---
 deny ip 10.10.20.0 0.0.0.255 10.10.30.0 0.0.0.255
 remark --- Allow DCEE to all other destinations ---
 permit ip 10.10.20.0 0.0.0.255 any
exit

interface vlan 20
 ip access-group ACL-DCEE-IN in
```
* **Extended ACL Range**: 100-199 or named ACLs (`ip access-list extended <NAME>`). Filters by source IP, destination IP, protocol (TCP/UDP/ICMP), and port numbers.
* **`in` keyword**: Applies the ACL to inbound traffic entering the switch interface from the host side. Inbound ACL filtering is most efficient because blocked packets are dropped immediately before lookup processing.
* **Implicit Deny Any Any**: Every Cisco ACL ends with an invisible `deny ip any any` statement. If traffic does not match an explicit `permit` rule, it is dropped!

---

### Phase 9: Management Plane (VLAN 99) & Zabbix NMS Monitoring
#### What we did:
Configured Out-of-Band SSH management on VLAN 99 and SNMPv2c communities for central monitoring via **Zabbix 6.0 LTS** (`10.10.40.100` on DIS port `SW-A-DIS Gi0/0`).

#### Commands & Explanation:
```cisco
! Enable SSH & AAA local authentication
username admin privilege 15 secret Cisco123!
ip domain-name foe.ruh.ac.lk
crypto key generate rsa modulus 2048
ip ssh version 2

line vty 0 4
 transport input ssh
 login local

! Configure SNMP for Zabbix Monitoring
snmp-server community public RO
snmp-server community private RW
snmp-server host 10.10.40.100 version 2c public
snmp-server enable traps
```
* **`crypto key generate rsa modulus 2048`**: Generates RSA key pair required for SSH encryption. 2048-bit modulus provides strong security.
* **`transport input ssh`**: Blocks unencrypted Telnet (Port 23) and forces SSH (Port 22) connections only.
* **SNMP RO vs RW**:
  * `public RO`: Read-Only community string allowing Zabbix NMS to query interface stats, CPU, memory, and bandwidth via SNMP OIDs.
  * `private RW`: Read-Write community string allowing management configuration updates over SNMP.
* **`snmp-server host 10.10.40.100 version 2c public`**: Configures the IP address of the Zabbix NMS server to receive asynchronous **SNMP Traps** (e.g. link Down events, power supply failure alerts).

---

## 3. Network Automation Deep Dive: Netmiko vs. Ansible

### 3.1 High-Level Architectural Comparison

| Dimension | **Netmiko** (Python Scripting) | **Ansible** (YAML Playbooks) |
| :--- | :--- | :--- |
| **Paradigm** | **Procedural** (Imperative code: explicit step-by-step logic) | **Declarative** (Desired State Configuration: defines *what* the network should look like) |
| **Execution Engine** | Python interpreter executing Paramiko/SSH calls | Ansible Engine running Python modules over SSH / `connection: network_cli` |
| **Agent Requirements** | Agentless (SSH native) | Agentless (SSH native, `gather_facts: false`) |
| **Host Node** | `UbuntuDockerGuest-1` (`10.99.99.100` on `SW-CORE Gi1/1`) | `UbuntuDockerGuest-1` (`10.99.99.100` on `SW-CORE Gi1/1`) |
| **Idempotency** | Must be manually coded in Python | **Built-in natively** by Cisco IOS Ansible collection modules |
| **Configuration Templating** | Python string formatting / Jinja2 | Native Jinja2 (`.j2`) integration |
| **Primary Project Use Case** | Bulk router setup, SNMP push, & structured verification | Modular, multi-role switch configuration (`site.yml`) & state enforcement |

---

### 3.2 Netmiko Automation Suite Breakdown

Location in Repository: `automation/netmiko-automation/`

```
automation/netmiko-automation/
├── inventory.yaml             # Centralized YAML device inventory & SSH credentials
├── 01_configure_routers.py    # Router provisioning (Interfaces, OSPF, NAT, ACLs)
├── 02_configure_snmp_all.py   # Global SNMP community & Trap push across ALL devices
├── 03_verify_config.py        # Automated validation & show command parsing
└── logs/                      # Timestamped execution logs
```

#### File 1: `inventory.yaml`
* **Purpose**: Decouples network inventory (IPs, hostnames, roles, device types, SSH credentials) from Python code.
* **Key Code Construct**:
  ```yaml
  routers:
    R-CORE:
      device_type: cisco_ios
      host: 10.99.99.254
      username: admin
      password: Password123!
      secret: Password123!
  ```
* **Why `device_type: cisco_ios`?** Instructs Netmiko's `ConnectHandler` to load the Cisco IOS prompt pattern driver (detecting `>`, `#`, `(config)#` prompts).

#### File 2: `01_configure_routers.py`
* **Purpose**: Automates provisioning of `R-CORE` and `R-EDGE`.
* **Key Code Breakdown & Netmiko Functions**:
  1. `ConnectHandler(**device)`: Establishes SSH connection to the target device using inventory dictionaries.
  2. `net_connect.enable()`: Enters Cisco Privileged EXEC mode (`#`) using the `secret` password.
  3. `net_connect.send_config_set(config_list)`: Sends a list of IOS configuration commands in `config term` mode. Automatically checks for prompt changes and syntax errors.
  4. `net_connect.save_config()`: Issues `write memory` / `copy running-config startup-config`.
  5. `net_connect.disconnect()`: Gracefully closes the SSH session.
* **Error Handling**: Wrapped in `try...except NetmikoTimeoutException` and `except NetmikoAuthenticationException`. If one router is down, the script logs the failure and continues to the next device without crashing.

#### File 3: `02_configure_snmp_all.py`
* **Purpose**: Iterates through every router, L3 switch, and L2 switch in `inventory.yaml` and pushes standard SNMP v2c monitoring parameters.
* **Why created?** Ensures 100% monitoring coverage for Zabbix without manually logging into 10 separate device consoles.

#### File 4: `03_verify_config.py`
* **Purpose**: Executes verification `show` commands on all devices and aggregates output into readable log files.
* **Key Netmiko Function**: `net_connect.send_command("show ip ospf neighbor")` (sends a read-only operational command and captures string output).

---

### 3.3 Ansible Automation Suite Breakdown

Location in Repository: `automation/ansible-project/`

```
automation/ansible-project/
├── ansible.cfg                # Ansible engine parameters & timeout settings
├── site.yml                   # Master playbook orchestrating configuration sequence
├── inventory/
│   └── hosts                  # INI inventory file with host groupings
├── playbooks/
│   └── rollback.yml           # Emergency rollback playbook
└── roles/                     # Modular Ansible Roles
    ├── vlans/                 # Role 1: Creates VLAN database
    ├── trunking/              # Role 2: Configures 802.1Q trunks
    ├── access_ports/          # Role 3: Assigns access VLANs & PortFast
    ├── stp/                   # Role 4: Configures Spanning Tree priorities
    ├── l3_distribution/       # Role 5: Configures L3 SVIs, routed links & OSPF
    └── l2_gateway/            # Role 6: Sets L2 access switch default gateways
```

#### File 1: `ansible.cfg`
* **Key Settings**:
  ```ini
  [defaults]
  inventory = ./inventory/hosts
  host_key_checking = False
  timeout = 30
  [persistent_connection]
  connect_timeout = 60
  command_timeout = 60
  ```
* **Why `host_key_checking = False`?** Prevents SSH execution failure when connecting to lab devices with self-signed SSH keys or changing host keys.

#### File 2: `inventory/hosts`
* **Structure**: Defines device groups (`[all_switches]`, `[dist_switches]`, `[access_switches]`) and connection variables:
  ```ini
  [dist_switches]
  SW-D-DEIE ansible_host=10.99.99.11
  SW-D-DCEE ansible_host=10.99.99.12
  SW-D-DMME ansible_host=10.99.99.13

  [all_switches:vars]
  ansible_connection=network_cli
  ansible_network_os=cisco.ios.ios
  ansible_user=admin
  ansible_password=Password123!
  ```
* **Why `ansible_connection=network_cli`?** Network switches do not run Python locally. `network_cli` tells Ansible to execute CLI commands over a persistent SSH connection from the control node (`UbuntuDockerGuest-1`).

#### File 3: Master Playbook (`site.yml`)
* **Execution Sequence**:
  1. Play 1 (`tags: [vlans]`): Runs `vlans` role on `all_switches`.
  2. Play 2 (`tags: [trunking]`): Runs `trunking` role on `all_switches`.
  3. Play 3 (`tags: [access_ports]`): Runs `access_ports` role on `all_switches`.
  4. Play 4 (`tags: [stp]`): Runs `stp` role on `all_switches`.
  5. Play 5 (`tags: [l3_distribution]`): Runs `l3_distribution` role **ONLY on `dist_switches`**.
  6. Play 6 (`tags: [l2_gateway]`): Runs `l2_gateway` role **ONLY on `access_switches`**.
  7. Play 7 (`tags: [save]`): Executes `cisco.ios.ios_config` with `save_when: always` (`write memory`).

#### Ansible Roles & Module Deep Dive:
1. **`roles/vlans/tasks/main.yml`**:
   * Uses module **`cisco.ios.ios_vlans`**.
   * Declaratively ensures VLAN IDs 10, 20, 30, 40, 99, 100 exist with proper names.
2. **`roles/trunking/tasks/main.yml`**:
   * Uses module **`cisco.ios.ios_l2_interfaces`**.
   * Sets `mode: trunk` and native VLAN 100 on uplink interfaces.
3. **`roles/access_ports/tasks/main.yml`**:
   * Uses module **`cisco.ios.ios_l2_interfaces`** and **`cisco.ios.ios_config`**.
   * Configures access VLAN assignments and enables `spanning-tree portfast`.
4. **`roles/l3_distribution/tasks/main.yml`**:
   * Uses modules **`cisco.ios.ios_l3_interfaces`** and **`cisco.ios.ios_ospfv2`**.
   * Configures `/30` routed uplink IPs, SVI gateway IPs, enables `ip routing`, and advertises subnets in OSPF Area 0.
5. **`playbooks/rollback.yml`**:
   * **Purpose**: Provides a safety net. Restores switches to a clean base state or wipes experimental VLAN/routing configurations in case of deployment errors.

---

## 4. Top 20 Viva Questions & Winning Answers

### Q1: What is the difference between a Layer 2 switch and a Layer 3 switch?
> **Answer:** A Layer 2 switch forwards Ethernet frames based solely on MAC addresses within the same VLAN. It cannot forward traffic between different VLANs. A Layer 3 (multilayer) switch contains both an L2 switching engine and an L3 IP routing engine. It can perform inter-VLAN routing using Switch Virtual Interfaces (SVIs) or routed ports at wire-speed using ASIC hardware.

### Q2: Why did we change the Native VLAN from VLAN 1 to VLAN 100?
> **Answer:** By default, IEEE 802.1Q trunks treat VLAN 1 as the untagged native VLAN. If user ports remain in VLAN 1, an attacker can launch a **VLAN Hopping Attack** by double-tagging Ethernet frames (outer tag = VLAN 1, inner tag = target VLAN). By moving the native VLAN to an unused VLAN (VLAN 100) and pruning it from user access ports, untagged traffic is isolated and VLAN hopping is mitigated.

### Q3: What is a Switch Virtual Interface (SVI) and what condition must be met for it to be 'up/up'?
> **Answer:** An SVI is a logical Layer 3 interface on a multilayer switch (`interface vlan X`) assigned an IP address to act as a default gateway for that VLAN. For an SVI to be in the `up/up` operational state, two conditions must be met:
> 1. The VLAN must exist in the switch's VLAN database (`vlan.dat`).
> 2. At least one physical port assigned to that VLAN (access or trunk) must be active (`up/up`) and in the STP Forwarding state.

### Q4: Why do we configure `spanning-tree portfast` on access ports?
> **Answer:** Normal STP interfaces transition through Blocking -> Listening (15s) -> Learning (15s) -> Forwarding (total 30 seconds delay). PCs and end devices connected to access ports do not create switching loops. PortFast allows access ports to immediately transition to the Forwarding state, preventing DHCP request timeouts and startup delays on workstations.

### Q5: What is the difference between an Access Port and a Trunk Port?
> **Answer:** An **Access Port** belongs to a single VLAN and transmits untagged Ethernet frames to end devices like PCs and IP phones. A **Trunk Port** connects switch-to-switch or switch-to-router and carries traffic for multiple VLANs simultaneously by prepending a 4-byte 802.1Q tag header to each frame.

### Q6: How does Inter-VLAN routing work in your design?
> **Answer:** In our Layer 3 distribution design, host PCs send packets destined for other subnets to their local Distribution Switch SVI (e.g. `10.10.10.1` on `SW-D-DEIE`). The Distribution switch inspects the IP header, performs an L3 routing table lookup, and either routes it directly to another local SVI or forwards it over a `/30` routed link (`no switchport`) via OSPF to `SW-CORE` / destination router.

### Q7: Why did we convert the Distribution switches from Layer 2 to Layer 3?
> **Answer:** Converting distribution switches to L3 provides three major architectural advantages:
> 1. **Eliminates Spanning Tree Loops**: Switch-to-Core links become routed Layer 3 point-to-point links (`no switchport`), removing STP loop topology on uplinks.
> 2. **Localized Gateway Processing**: Inter-VLAN traffic within a department is routed locally at the distribution switch without clogging the Core switch links.
> 3. **Faster Convergence**: OSPF routing converges in under 1 second during link failures, whereas STP topology changes take 30-50 seconds.

### Q8: What is a Wildcard Mask in OSPF and how do you calculate it?
> **Answer:** A wildcard mask is an inverted subnet mask used by OSPF to specify which IP address bits to check. A binary `0` means the bit must match exactly, while `255` means "don't care". It is calculated by subtracting the subnet mask from `255.255.255.255`.  
> *Example:* For subnet mask `255.255.255.0` (`/24`), Wildcard Mask = `255.255.255.255 - 255.255.255.0` = `0.0.0.255`.

### Q9: Why did we use `passive-interface default` in OSPF configuration?
> **Answer:** `passive-interface default` suppresses OSPF Hello packet broadcasts on all interfaces by default while still advertising their connected subnets. This prevents OSPF adjacency formation on end-user access ports (VLANs 10, 20, 30, 40), stopping malicious users from connecting a rogue router to hijack campus network traffic. We explicitly enable OSPF only on trusted core/distribution interfaces using `no passive-interface`.

### Q10: What is the function of `default-information originate` on R-EDGE?
> **Answer:** It tells the OSPF process on `R-EDGE` to generate a Type-5 External Link-State Advertisement (LSA) containing a default route (`0.0.0.0/0`) and flood it throughout OSPF Area 0. This automatically propagates the Internet egress path to `R-CORE` and `SW-CORE` without configuring manual static default routes on every switch.

### Q11: How does NAT Overload (PAT) work on R-EDGE?
> **Answer:** Port Address Translation (PAT) translates multiple private internal IP addresses (`10.x.x.x`) to a single public IP address on the WAN interface (`FastEthernet1/0`). It differentiates between different internal hosts by mapping each internal connection's IP + Source Port to the public IP + a unique external TCP/UDP port number in the NAT translation table (`show ip nat translations`).

### Q12: Explain the difference between Netmiko and Ansible.
> **Answer:** 
> * **Netmiko** is a Python library built on top of Paramiko. It is **procedural**—you write explicit Python code to handle SSH connections, send CLI commands, handle prompts, and parse outputs.
> * **Ansible** is an automation framework that is **declarative**. You write YAML playbooks defining the *desired state* of the network. Ansible handles connection management, module execution, idempotency, and error handling under the hood.

### Q13: What does 'Idempotency' mean in network automation and why is it important?
> **Answer:** Idempotency means executing an automation script or playbook multiple times results in the exact same network state without causing unintended side effects or duplicate commands. For example, running an idempotent Ansible VLAN role twice will create VLAN 10 on the first run, but on the second run, it detects VLAN 10 already exists and makes zero changes.

### Q14: How does Ansible connect to Cisco network devices without installing Python on the switch?
> **Answer:** Cisco switches run closed network operating systems (IOS) that cannot run local Python interpreters. Ansible solves this using `ansible_connection=network_cli` and `ansible_network_os=cisco.ios.ios`. The Ansible engine running on the Linux control node (`UbuntuDockerGuest-1`) translates YAML tasks into Cisco CLI commands and executes them over an SSH connection.

### Q15: What is the purpose of `gather_facts: false` in Ansible playbooks for network devices?
> **Answer:** By default, Ansible tries to execute a setup script on remote targets to collect system facts (Linux facts like `/etc/os-release`). Cisco switches do not support standard Linux facts commands. Setting `gather_facts: false` prevents Ansible from failing on startup and speeds up playbook execution.

### Q16: In Netmiko, what is the difference between `send_config_set()` and `send_command()`?
> **Answer:** 
> * `send_config_set()` is used for **configuration changes**. It automatically enters configuration mode (`config t`), sends a list of configuration commands, handles prompt changes, and exits configuration mode.
> * `send_command()` is used for **read-only operational verification** (e.g. `show ip route`, `show vlan brief`). It executes the command in EXEC mode and returns the raw string response.

### Q17: What exception handling did you implement in Netmiko scripts?
> **Answer:** We wrapped SSH connection attempts in `try...except` blocks catching:
> 1. `NetmikoTimeoutException`: Triggers if a device is offline or un-routable.
> 2. `NetmikoAuthenticationException`: Triggers if SSH username/password/enable secret is invalid.  
> Catching these errors allows the script to log the failure and cleanly continue configuring remaining network devices.

### Q18: What is Zabbix and how does it monitor our campus network?
> **Answer:** Zabbix is an enterprise open-source Network Monitoring System (NMS) deployed at `10.10.40.100` (connected to DIS access switch `SW-A-DIS`). It monitors network switches and routers using **SNMPv2c**. Zabbix polls SNMP OIDs (Object Identifiers) every 60 seconds to track CPU usage, memory utilization, bandwidth consumption, and interface packet errors. It also listens for asynchronous **SNMP Traps** sent by devices when links go down.

### Q19: Why are extended ACLs placed as close to the traffic source as possible?
> **Answer:** Placing extended ACLs close to the source (e.g. `in` on the ingress department SVI) ensures unwanted or prohibited traffic is dropped **immediately** upon entering the network. This prevents rogue packets from consuming backplane switching bandwidth, link capacity, and router processing power across the campus core.

### Q20: What is the purpose of `no switchport` command on a Catalyst switch interface?
> **Answer:** The `no switchport` command converts a Layer 2 switchport into a dedicated Layer 3 routed port. It removes all Layer 2 features (VLAN memberships, STP, DTP trunk negotiation) and enables direct IP address assignment (`ip address X.X.X.X Y.Y.Y.Y`), turning the interface into a point-to-point router link.

---
*End of Master Guide — Good luck with your Viva Evaluation!*
