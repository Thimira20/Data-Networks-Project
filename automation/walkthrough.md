# Walkthrough — Network Automation Project

## Summary

Created the complete **automation project** under `automation/` with two sub-projects:

```
automation/
├── ansible-project/     ← Switch automation (L3 dist + L2 access)
│   ├── ansible.cfg
│   ├── README.md
│   ├── site.yml                    ← Master playbook (7 ordered plays)
│   ├── inventory/hosts             ← 7 switches (3 dist + 4 access)
│   ├── group_vars/
│   │   ├── all.yml                 ← Credentials, VLANs, trunk defaults
│   │   ├── dist_switches.yml       ← L3: ip_routing, OSPF, Docker route
│   │   └── access_switches.yml    ← L2: default-gateway, STP, portfast
│   ├── host_vars/                  ← Per-switch config (L3 or L2)
│   │   ├── SW-D-DEIE.yml          ← L3: routed uplink, VLAN 10 SVI, OSPF
│   │   ├── SW-D-DCEE.yml          ← L3: routed uplink, VLAN 20 SVI, OSPF
│   │   ├── SW-D-DMME.yml          ← L3: routed uplink, VLAN 30 SVI, OSPF
│   │   ├── SW-A-DEIE.yml          ← L2: trunk, access, gw→10.99.99.11
│   │   ├── SW-A-DCEE.yml          ← L2: trunk, access, gw→10.99.99.12
│   │   ├── SW-A-DMME.yml          ← L2: trunk, access, gw→10.99.99.13
│   │   └── SW-A-DIS.yml           ← L2: trunk, access, gw→10.99.99.1
│   ├── roles/
│   │   ├── vlans/tasks/main.yml
│   │   ├── trunking/tasks/main.yml
│   │   ├── access_ports/tasks/main.yml
│   │   ├── stp/tasks/main.yml
│   │   ├── l3_distribution/tasks/main.yml  ← NEW: ip routing, SVIs, OSPF
│   │   └── l2_gateway/tasks/main.yml       ← NEW: ip default-gateway
│   └── playbooks/
│       └── rollback.yml            ← Restore clean baseline (incl. L3)
│
└── netmiko-automation/  ← Router automation (interfaces, OSPF, NAT, ACLs, SNMP)
    ├── inventory.yaml              ← 10 devices (R-EDGE uses FastEthernet)
    ├── 01_configure_routers.py     ← R-CORE + R-EDGE config
    ├── 02_configure_snmp_all.py    ← SNMP push to all 10 devices
    ├── 03_verify_config.py         ← Post-config verification
    └── README.md
```

**Total: 24 files** (22 original + 2 new roles)

---

## Architecture: L3 Distribution / L2 Access Model

### Layer 3 — Distribution Switches (Multilayer)

After L3 conversion (see `L3_Distribution_Switch_Conversion_Report.md`), distribution switches are **multilayer L3 devices** with:

| Switch | Routed Uplink | Dept SVI | MGMT SVI | OSPF RID | Docker Route |
|---|---|---|---|---|---|
| **SW-D-DEIE** | Gi0/0 → 10.0.10.2/30 | VLAN 10 → 10.10.10.1/24 | VLAN 99 → .11 | 3.3.3.11 | via 10.0.10.1 |
| **SW-D-DCEE** | Gi0/2 → 10.0.20.2/30 | VLAN 20 → 10.10.20.1/24 | VLAN 99 → .12 | 3.3.3.12 | via 10.0.20.1 |
| **SW-D-DMME** | Gi0/3 → 10.0.30.2/30 | VLAN 30 → 10.10.30.1/24 | VLAN 99 → .13 | 3.3.3.13 | via 10.0.30.1 |

**Key:** Uplinks to SW-Core are `/30 routed ports` (not trunks). `ip default-gateway` is **removed**.

### Layer 2 — Access Switches

| Switch | Trunk Uplink | Access Ports | Default Gateway |
|---|---|---|---|
| **SW-A-DEIE** | Gi0/1 → SW-D-DEIE | Gi0/0 (PC1), Gi0/2 (PC2) VLAN 10 | 10.99.99.11 |
| **SW-A-DCEE** | Gi0/0 → SW-D-DCEE | Gi0/1 (PC3), Gi0/2 (PC4) VLAN 20 | 10.99.99.12 |
| **SW-A-DMME** | Gi0/0 → SW-D-DMME | Gi0/1 (PC5), Gi0/2 (PC6) VLAN 30 | 10.99.99.13 |
| **SW-A-DIS** | Gi1/0 → SW-CORE | Gi0/0 (PC8), Gi0/1 (PC7) VLAN 40 | 10.99.99.1 |

**Key:** Default gateways point to **local distribution switches** (not SW-CORE), fixing VLAN 99 L2 split issue.

### Trunk Interfaces (from `trunk_config.md`)

> Uplinks from distribution switches to SW-Core are Layer 3 **routed ports** (`no switchport`, /30 IPs). Only the downlinks to access switches operate as Layer 2 trunks.

| Switch | Port → Destination | Mode |
|---|---|---|
| **SW-D-DEIE** | Gi0/2 → SW-A-DEIE | trunk |
| **SW-D-DCEE** | Gi0/0 → SW-A-DCEE | trunk |
| **SW-D-DMME** | Gi0/0 → SW-A-DMME | trunk |
| **SW-A-DIS** | Gi1/0 → SW-CORE | trunk |

---

## Key Changes Made in This Refactoring

| Change | What Was Updated |
|---|---|
| **L3 Distribution Role** | NEW `roles/l3_distribution/` — enables ip routing, routed uplinks, SVIs, OSPF, Docker return routes |
| **L2 Gateway Role** | NEW `roles/l2_gateway/` — sets ip default-gateway on access switches |
| **site.yml** | Added Play 5 (L3 dist) and Play 6 (L2 gateway) to 7-step sequence |
| **host_vars (dist)** | Added routed_uplink, department_svi, mgmt_svi, OSPF, Docker route |
| **host_vars (access)** | Added default_gateway to each access switch |
| **group_vars** | dist_switches: ip_routing, OSPF defaults; access_switches: gateway flag |
| **rollback.yml** | Added L3 rollback phase (OSPF, SVIs, routes, ip routing) |
| **Netmiko inventory** | R-EDGE: FastEthernet (not GigabitEthernet), numbered ACL 100, static routes |
| **01_configure_routers.py** | Added static route deployment, numbered ACL support |

---

## How to Deploy on VM-AUTO

### Step 1: Copy files to Docker container

```bash
# On VM-AUTO (Ubuntu Docker container):
cd /root

# Option A: Git clone
git clone https://github.com/Thimira20/Data-Networks-Project.git
cp -r Data-Networks-Project/automation /root/automation

# Option B: Manual — create dirs and paste files
mkdir -p /root/automation/ansible-project
mkdir -p /root/automation/netmiko-automation
```

### Step 2: Install Cisco Ansible collection

```bash
ansible-galaxy collection install cisco.ios
```

### Step 3: Run Ansible switch automation

```bash
cd /root/automation/ansible-project

# Dry-run first
ansible-playbook site.yml --check --diff

# Full deployment (all 7 steps)
ansible-playbook site.yml -v
```

### Step 4: Run Netmiko router automation

```bash
cd /root/automation/netmiko-automation

python3 01_configure_routers.py
python3 02_configure_snmp_all.py
python3 03_verify_config.py
```

### Step 5: Verify everything

```bash
# L3 distribution verification
cd /root/automation/ansible-project
ansible dist_switches -m cisco.ios.ios_command -a "commands='show ip route'"
ansible dist_switches -m cisco.ios.ios_command -a "commands='show ip ospf neighbor'"

# L2 access verification
ansible access_switches -m cisco.ios.ios_command -a "commands='show running-config | include default-gateway'"

# Full verification
ansible all_switches -m cisco.ios.ios_command -a "commands='show vlan brief'"
ansible all_switches -m cisco.ios.ios_command -a "commands='show interfaces trunk'"
```
