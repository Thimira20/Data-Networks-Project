# Method of Procedure (MOP): Campus Network Deployment & Automation
## EE8203 — Design and Management of Data Networks

---

## MOP Section 1 — Document Header

| Attribute | Details |
|---|---|
| **Project Title** | Hapugala Campus Network Layer 3 Conversion, Security Enforcement & Automation |
| **Module Code** | EE8203 - Design and Management of Data Networks |
| **Institution** | Department of Electrical & Information Engineering, University of Ruhuna |
| **Document Version** | 1.0 (Official Method of Procedure) |
| **Date of Execution** | August 2026 |
| **Target Completion Window**| 4 Hours (Maintenance Window 00:00 - 04:00) |
| **Lead Engineer(s)** | Network Engineering Group (EE8203 Group Project Team) |
| **Course Assessor** | Course Lecturer / Examiner |

---

## MOP Section 2 — Scope and Objectives

### 2.1 Scope of Implementation
This Method of Procedure defines the step-by-step operational steps to:
1. Transition campus distribution switches (**SW-D-DEIE**, **SW-D-DCEE**, **SW-D-DMME**) to a Layer 3 Multilayer Distribution Architecture with point-to-point `/30` routed uplinks to **SW-CORE**.
2. Deploy single-area **OSPF Area 0** dynamic routing across all Layer 3 routers (**R-CORE**, **R-EDGE**) and multilayer switches.
3. Provision Port Address Translation (NAT Overload) on **R-EDGE**, granting internet access exclusively to DEIE and DCEE subnets.
4. Enforce inter-departmental security boundaries using Extended Named ACLs inbound on switch SVIs.
5. Automate router provisioning via Python/Netmiko scripts and switch configuration via Ansible roles (`vlans`, `trunking`, `access_ports`, `stp`, `l3_distribution`, `l2_gateway`).
6. Onboard all 10 infrastructure devices into Zabbix 6.0 LTS via SNMPv2c.

### 2.2 Devices in Scope

```
[ Routers ]
 - R-EDGE  (WAN Gateway / NAT Overload / Default Static Route)
 - R-CORE  (Core Router / OSPF Transit)

[ Multilayer Layer 3 Switches ]
 - SW-CORE   (Core L3 Switch / Server Farm SVI / Transit Backbone)
 - SW-D-DEIE (Distribution L3 Switch - DEIE Gateway)
 - SW-D-DCEE (Distribution L3 Switch - DCEE Gateway)
 - SW-D-DMME (Distribution L3 Switch - DMME Gateway)

[ Layer 2 Access Switches ]
 - SW-A-DEIE (Access L2 Switch - DEIE Workstations)
 - SW-A-DCEE (Access L2 Switch - DCEE Workstations)
 - SW-A-DMME (Access L2 Switch - DMME Workstations)
 - SW-A-DIS  (Access L2 Switch - DIS Server Zone & Hosts)

[ Virtual Machines / Hosts ]
 - VM-AUTO   (Ubuntu 22.04 Automation Container - 10.99.99.100)
 - VM-ZABBIX (Ubuntu 22.04 Zabbix Server - 10.10.40.100)
```

### 2.3 Out of Scope
- Internal ISP router configuration beyond the simulated next-hop (`203.0.113.1`).
- Physical cabling changes outside the GNS3 virtual workspace topology.

---

## MOP Section 3 — Prerequisites and Pre-Checks

Before executing any configuration changes, the lead engineer must execute the following validation commands from **VM-AUTO** (`10.99.99.100`):

| # | Prerequisite Verification Item | Command / Action | Expected Output | Status (Pass/Fail) |
|---|---|---|---|---|
| 3.1 | GNS3 Topology Active | Verify all 13 nodes are powered on in GNS3 GUI. | All nodes green / active in canvas. | `[ PASS ]` |
| 3.2 | Out-of-Band Management Reachability | `fping -g 10.99.99.0/24` | 10.99.99.1, .11, .12, .13, .21, .22, .23, .24 respond. | `[ PASS ]` |
| 3.3 | Ansible Engine & Inventory Pre-check | `cd /root/automation/ansible-project && ansible all_switches -m ping` | `"ping": "pong"` returned for all 7 switches. | `[ PASS ]` |
| 3.4 | Netmiko Environment & Python Dependencies | `python3 -c "import netmiko; import yaml; print(netmiko.__version__)"` | Version output printed without error (e.g. `4.1.2`). | `[ PASS ]` |
| 3.5 | Zabbix Monitoring Platform Web Access | `curl -I http://10.10.40.100/zabbix` | `HTTP/1.1 200 OK` or `302 Found`. | `[ PASS ]` |

---

## MOP Section 4 — Risk Assessment & Mitigation Matrix

| Risk Identified | Likelihood | Impact | Preventive Mitigation Strategy |
|---|---|---|---|
| **ACL locks out SSH Management Access** | Medium | High | Apply ACLs strictly inbound to data VLAN SVIs (`Vlan10`, `Vlan20`, `Vlan30`); keep management SVI (`Vlan99`) unblocked during application. Ensure SSH console fallback is available. |
| **Automation script overwrites active switch config** | Low | Medium | Execute GNS3 topology snapshot (`Snapshot_Baseline_Pre_Automation`) prior to script runs. Test playbooks with `ansible-playbook site.yml --check --diff` first. |
| **VLAN 99 Management Plane Isolation (L2 Split)** | High | High | Immediately after converting distribution uplinks to `/30` routed ports, apply `/32` static host routes on `SW-CORE` (`10.99.99.11` via `10.0.10.2`, etc.) and set local access switch default gateways. |
| **OSPF Adjacency Failure due to Passive Interface** | Medium | Medium | Explicitly define `no passive-interface` on active transit uplinks under OSPF configuration. |
| **NAT Overload Translation Failure for Internet Egress** | Low | Medium | Verify NAT access-list permits `10.10.10.0/24` and `10.10.20.0/24` and verify `ip nat inside/outside` interface bindings on R-EDGE. |

---

## MOP Section 5 — Step-by-Step Execution Procedure

### Phase 1: Baseline L2/L3 Physical & Interface Provisioning

#### Step 1.1: Provision Base VLANs and Trunks on Access Switches
- **Action**: Execute Ansible VLAN and trunking roles on access switches:
  ```bash
  cd /root/automation/ansible-project
  ansible-playbook site.yml --tags "vlans,trunking,access_ports,stp"
  ```
- **Expected Output**: All plays succeed with `failed=0`.
- **Verification Command**:
  ```bash
  ansible access_switches -m cisco.ios.ios_command -a "commands='show vlan brief'"
  ```

---

### Phase 2: Layer 3 Distribution Conversion & OSPF Routing Setup

#### Step 2.1: Convert Distribution Uplinks to Layer 3 `/30` Ports & Configure SVIs
- **Action**: Apply Layer 3 distribution playbook to **SW-D-DEIE**, **SW-D-DCEE**, **SW-D-DMME**:
  ```bash
  ansible-playbook site.yml --tags "l3_distribution"
  ```
- **Expected Output**: Interfaces `Gi0/0` (DEIE), `Gi0/2` (DCEE), `Gi0/3` (DMME) converted to `no switchport` with assigned `/30` IP addresses; departmental SVIs enabled.
- **Verification Command**:
  ```bash
  ansible dist_switches -m cisco.ios.ios_command -a "commands='show ip interface brief'"
  ```

#### Step 2.2: Apply Host Routes on SW-CORE to Prevent Management Plane Split
- **Action**: Connect to **SW-CORE** CLI and apply `/32` host routes for distribution/access switches:
  ```cisco
  SW-CORE# configure terminal
  ip route 10.99.99.11 255.255.255.255 10.0.10.2
  ip route 10.99.99.21 255.255.255.255 10.0.10.2
  ip route 10.99.99.12 255.255.255.255 10.0.20.2
  ip route 10.99.99.22 255.255.255.255 10.0.20.2
  ip route 10.99.99.13 255.255.255.255 10.0.30.2
  ip route 10.99.99.23 255.255.255.255 10.0.30.2
  end
  write memory
  ```
- **Expected Output**: Command accepted without syntax errors.
- **Verification Command**: `show ip route static | include 10.99.99.` — confirm 6 host routes active.

#### Step 2.3: Execute Netmiko Router Provisioning Script (R-CORE & R-EDGE)
- **Action**: Execute Netmiko router automation script from **VM-AUTO**:
  ```bash
  cd /root/automation/netmiko-automation
  python3 01_configure_routers.py
  ```
- **Expected Output**: Netmiko connects to `R-CORE` and `R-EDGE`, provisions IP addresses, OSPF Area 0, static routes, and NAT overload rules. Log shows `Successfully configured R-CORE` and `R-EDGE`.
- **Verification Command**:
  ```bash
  python3 03_verify_config.py
  ```

---

### Phase 3: Inter-Departmental Security Policy (ACL) Deployment

#### Step 3.1: Apply Inbound Extended ACLs on Distribution & Core SVIs
- **Action**: Deploy ACL configurations onto `SW-D-DEIE`, `SW-D-DCEE`, `SW-D-DMME`, and `SW-CORE`:
  ```cisco
  ! On SW-D-DEIE:
  interface Vlan10
   ip access-group ACL-DEIE-IN in
  
  ! On SW-D-DCEE:
  interface Vlan20
   ip access-group ACL-DCEE-IN in
  
  ! On SW-D-DMME:
  interface Vlan30
   ip access-group ACL-DMME-IN in
  
  ! On SW-CORE:
  interface Vlan40
   ip access-group ACL-DIS-IN in
  ```
- **Expected Output**: Access groups bound to target SVI interfaces.
- **Verification Command**:
  ```bash
  ansible dist_switches -m cisco.ios.ios_command -a "commands='show ip interface vlan 10'"
  ```

---

### Phase 4: Network Monitoring System (Zabbix) Onboarding

#### Step 4.1: Push SNMPv2c Community String & Trap Destinations
- **Action**: Run Netmiko SNMP deployment script:
  ```bash
  cd /root/automation/netmiko-automation
  python3 02_configure_snmp_all.py
  ```
- **Expected Output**: `snmp-server community public_foe_snmp RO` and `snmp-server host 10.10.40.100` configured across all 10 devices.
- **Verification Command**: `snmpwalk -v2c -c public_foe_snmp 10.99.99.1 sysUpTime.0` executed from **VM-ZABBIX**.

#### Step 4.2: Import Zabbix Dashboard & Validate Triggers
- **Action**: Import `zabbix_foe_uor_dashboard.json` via Zabbix Web Interface (`Configuration -> Dashboards -> Import`).
- **Expected Output**: Dashboard `FoE-UoR Network` appears with green host indicators.
- **Verification Command**: Temporarily shut an unused access interface on `SW-A-DEIE` (`shutdown`) and verify trigger alert fires in Zabbix within 60 seconds.

---

## MOP Section 6 — Comprehensive Test Plan

Upon completing deployment, the lead engineer must complete the full test matrix:

1. **$4 \times 4$ Department Reachability Matrix**: Run ICMP ping and traceroute across all 16 client endpoint pairs (PC-DEIE, PC-DCEE, PC-DMME, PC-DIS). Confirm exactly 6 PASS and 10 FAIL outcomes matching Section 3.2 of the Final Report.
2. **Ansible Idempotency Check**: Run `ansible-playbook site.yml --check` and verify `changed=0` across all hosts.
3. **Netmiko Execution Log Verification**: Inspect `netmiko_execution.log` and verify zero error entries.
4. **Zabbix Alerting Verification**: Shutdown interface `Gi0/2` on `SW-A-DEIE`, observe Zabbix dashboard trigger firing with red alert indicator, then issue `no shutdown` and observe automatic trigger resolution.

---

## MOP Section 7 — Rollback Procedure

If a critical failure occurs during deployment that cannot be remediated within 15 minutes, execute the appropriate rollback procedure:

### 7.1 Manual Emergency Revert (Console Access)
If management access to a device is lost due to an ACL locking out SSH:
1. Connect directly to the device via Serial/Console cable in GNS3.
2. Remove the offending ACL binding:
   ```cisco
   configure terminal
   interface Vlan10 (or affected SVI)
    no ip access-group ACL-DEIE-IN in
   end
   ```

### 7.2 Automated Switch Rollback (Ansible)
To restore all switches to the clean pre-deployment baseline:
```bash
cd /root/automation/ansible-project
ansible-playbook playbooks/rollback.yml
```
*Effect*: Removes custom SVIs, OSPF processes, routed uplinks, and custom VLANs, restoring default Layer 2 trunking state within 3 minutes.

### 7.3 Total Infrastructure Rollback (GNS3 Snapshot)
In the event of unrecoverable systemic error:
1. In GNS3 GUI, select `Manage Snapshots`.
2. Select `Snapshot_Baseline_Pre_Automation`.
3. Click `Restore Snapshot` and restart all virtual nodes. Total recovery time: < 5 minutes.

---

## MOP Section 8 — Post-Implementation Review

*To be completed by lead engineer following change window execution:*

| Review Item | Outcome / Notes |
|---|---|
| **Execution Summary** | All 6 deployment phases executed successfully within the allotted maintenance window. |
| **Planned vs Actual Scope** | 100% of planned items implemented without unexpected scope creep. |
| **Deviations from Plan** | Added explicit `/32` host routes on `SW-CORE` to maintain management reachability following distribution L3 conversion (documented in Section 6.1 of Technical Report). |
| **Key Lessons Learned** | Converting distribution switches to Layer 3 splits flat management VLANs; explicit host routing or dedicated OOB management links must be planned in advance. |
| **Sign-off Status** | **APPROVED & ACCEPTED** by Lead Network Engineer. |
