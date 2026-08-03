# Walkthrough — Network Automation Project

## Summary

Created the complete **automation project** under `automation/` with two sub-projects:

```
automation/
├── ansible-project/     ← Switch automation (VLANs, trunks, access ports, STP)
│   ├── ansible.cfg
│   ├── README.md
│   ├── site.yml                    ← Master playbook
│   ├── inventory/hosts             ← 7 switches (3 dist + 4 access)
│   ├── group_vars/
│   │   ├── all.yml                 ← Credentials, VLANs, trunk defaults
│   │   ├── dist_switches.yml       ← STP priority 24576
│   │   └── access_switches.yml    ← STP priority 32768, portfast
│   ├── host_vars/                  ← Per-switch interface mappings
│   │   ├── SW-D-DEIE.yml
│   │   ├── SW-D-DCEE.yml
│   │   ├── SW-D-DMME.yml
│   │   ├── SW-A-DEIE.yml
│   │   ├── SW-A-DCEE.yml
│   │   ├── SW-A-DMME.yml
│   │   └── SW-A-DIS.yml
│   ├── roles/
│   │   ├── vlans/tasks/main.yml
│   │   ├── trunking/tasks/main.yml
│   │   ├── access_ports/tasks/main.yml
│   │   └── stp/tasks/main.yml
│   └── playbooks/
│       └── rollback.yml            ← Restore clean baseline (<5 min)
│
└── netmiko-automation/  ← Router automation (interfaces, OSPF, NAT, ACLs, SNMP)
    ├── inventory.yaml              ← 10 devices (SW-D-DIS removed)
    ├── 01_configure_routers.py     ← R-CORE + R-EDGE config
    ├── 02_configure_snmp_all.py    ← SNMP push to all 10 devices
    ├── 03_verify_config.py         ← Post-config verification
    └── README.md
```

**Total: 22 files created**

---

## Key Corrections Applied

| Correction | What Changed |
|---|---|
| **SW-D-DIS removed** | No such switch in topology — SW-A-DIS connects directly to SW-CORE |
| **SW-D-DEIE interfaces** | Gi0/0→SW-CORE, Gi0/2→SW-A-DEIE (was Gi0/1, Gi0/2) |
| **SW-D-DMME interfaces** | Gi0/3→SW-CORE, Gi0/0→SW-A-DMME (was Gi0/0, Gi0/2) |
| **SW-A-DIS interfaces** | Gi0/0→PC8, Gi0/1→PC7, **Gi1/0**→SW-CORE (was Gi0/0, Gi0/2, Gi0/1) |
| **Inventory updated** | SW-D-DIS removed from `inventory.yaml` — now 10 devices total |

---

## Interface Mapping Summary (All 7 Switches)

### Distribution Switches (trunk-only)

| Switch | Port → Destination | Mode |
|---|---|---|
| **SW-D-DEIE** | Gi0/0 → SW-CORE | trunk |
| | Gi0/2 → SW-A-DEIE | trunk |
| **SW-D-DCEE** | Gi0/2 → SW-CORE | trunk |
| | Gi0/0 → SW-A-DCEE | trunk |
| **SW-D-DMME** | Gi0/3 → SW-CORE | trunk |
| | Gi0/0 → SW-A-DMME | trunk |

### Access Switches (access + trunk)

| Switch | Port → Destination | Mode | VLAN |
|---|---|---|---|
| **SW-A-DEIE** | Gi0/0 → PC1 | access | 10 |
| | Gi0/2 → PC2 | access | 10 |
| | Gi0/1 → SW-D-DEIE | trunk | — |
| **SW-A-DCEE** | Gi0/1 → PC3 | access | 20 |
| | Gi0/2 → PC4 | access | 20 |
| | Gi0/0 → SW-D-DCEE | trunk | — |
| **SW-A-DMME** | Gi0/1 → PC5 | access | 30 |
| | Gi0/2 → PC6 | access | 30 |
| | Gi0/0 → SW-D-DMME | trunk | — |
| **SW-A-DIS** | Gi0/0 → PC8 | access | 40 |
| | Gi0/1 → PC7 | access | 40 |
| | Gi1/0 → SW-CORE | trunk | — |

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

# Full deployment
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
# Ansible ad-hoc verification
cd /root/automation/ansible-project
ansible all_switches -m cisco.ios.ios_command -a "commands='show vlan brief'"
ansible all_switches -m cisco.ios.ios_command -a "commands='show interfaces trunk'"
```
