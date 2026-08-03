# Ansible Switch Automation — EE8203 Project

## EE8203/EC8205 — Section 4.2: Ansible Network Automation

> This guide covers deploying and running the Ansible playbooks for switch configuration.
> Ansible is already installed on VM-AUTO (Ubuntu Docker container).

---

## Table of Contents

- [Architecture Overview](#architecture)
- [Directory Structure](#directory-structure)
- [Prerequisites](#prerequisites)
- [Installation (One-Time)](#installation)
- [Running the Playbooks](#running)
- [Expected Outputs](#expected-outputs)
- [Verification](#verification)
- [Rollback](#rollback)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview <a name="architecture"></a>

This Ansible project manages **two distinct switch layers**:

### Layer 3 — Distribution Switches (Multilayer)

| Switch | Dept | MGMT IP | Routed Uplink | Dept SVI |
|---|---|---|---|---|
| SW-D-DEIE | DEIE | 10.99.99.11 | Gi0/0 → 10.0.10.2/30 | VLAN 10 → 10.10.10.1/24 |
| SW-D-DCEE | DCEE | 10.99.99.12 | Gi0/2 → 10.0.20.2/30 | VLAN 20 → 10.10.20.1/24 |
| SW-D-DMME | DMME | 10.99.99.13 | Gi0/3 → 10.0.30.2/30 | VLAN 30 → 10.10.30.1/24 |

**L3 features configured by Ansible:**
- `ip routing` enabled
- Routed uplink to SW-CORE (`no switchport`, /30 IP)
- Department VLAN SVI (default gateway for hosts)
- MGMT VLAN 99 SVI
- OSPF process 1 (area 0) — advertises subnets
- Static /32 return route for Docker (10.99.99.100)
- `ip default-gateway` **removed** (invalid on L3)

### Layer 2 — Access Switches

| Switch | Dept | MGMT IP | Default Gateway | Why |
|---|---|---|---|---|
| SW-A-DEIE | DEIE | 10.99.99.21 | 10.99.99.11 | Local dist (SW-D-DEIE) |
| SW-A-DCEE | DCEE | 10.99.99.22 | 10.99.99.12 | Local dist (SW-D-DCEE) |
| SW-A-DMME | DMME | 10.99.99.23 | 10.99.99.13 | Local dist (SW-D-DMME) |
| SW-A-DIS  | DIS  | 10.99.99.24 | 10.99.99.1  | SW-CORE (no dist switch) |

**L2 features configured by Ansible:**
- Trunk uplinks to distribution switch (or SW-CORE for DIS)
- Access ports with PortFast for PCs
- `ip default-gateway` set to local distribution switch
- STP priority (32768, lower than dist switches)

> **Note:** SW-CORE is NOT managed by Ansible. It has L3 routing, ACLs, and OSPF
> that are already configured manually. SW-A-DIS connects directly to SW-CORE
> (there is no SW-D-DIS distribution switch in the topology).

### Deployment Sequence

| Step | Play | Hosts | Role | What It Does |
|---|---|---|---|---|
| 1 | VLANs | all_switches | `vlans` | Creates VLANs 10, 20, 30, 40, 99, 100 |
| 2 | Trunking | all_switches | `trunking` | Configures trunk links (dot1q, native VLAN 100) |
| 3 | Access Ports | all_switches | `access_ports` | Assigns PC-facing ports to department VLANs |
| 4 | STP | all_switches | `stp` | Sets STP mode (rapid-pvst) and priorities |
| 5 | **L3 Distribution** | dist_switches | `l3_distribution` | ip routing, routed uplinks, SVIs, OSPF, static routes |
| 6 | **L2 Gateway** | access_switches | `l2_gateway` | Sets ip default-gateway on access switches |
| 7 | Save | all_switches | (task) | Writes running-config to NVRAM |

---

## Directory Structure <a name="directory-structure"></a>

```
ansible-project/
├── ansible.cfg                  # Ansible config (inventory path, timeouts)
├── README.md                    # This guide
├── site.yml                     # Master playbook — 7 ordered plays
├── inventory/
│   └── hosts                    # Switch groups: dist_switches, access_switches
├── group_vars/
│   ├── all.yml                  # Shared: credentials, VLANs, trunk defaults
│   ├── dist_switches.yml        # L3: ip_routing, OSPF defaults, Docker route
│   └── access_switches.yml     # L2: default-gateway flag, STP, portfast
├── host_vars/
│   ├── SW-D-DEIE.yml            # L3: Gi0/0→routed, Gi0/2→trunk, VLAN 10 SVI
│   ├── SW-D-DCEE.yml            # L3: Gi0/2→routed, Gi0/0→trunk, VLAN 20 SVI
│   ├── SW-D-DMME.yml            # L3: Gi0/3→routed, Gi0/0→trunk, VLAN 30 SVI
│   ├── SW-A-DEIE.yml            # L2: Gi0/0,Gi0/2→VLAN10, Gi0/1→trunk, gw→.11
│   ├── SW-A-DCEE.yml            # L2: Gi0/1,Gi0/2→VLAN20, Gi0/0→trunk, gw→.12
│   ├── SW-A-DMME.yml            # L2: Gi0/1,Gi0/2→VLAN30, Gi0/0→trunk, gw→.13
│   └── SW-A-DIS.yml             # L2: Gi0/0,Gi0/1→VLAN40, Gi1/0→trunk, gw→.1
├── roles/
│   ├── vlans/tasks/main.yml     # VLAN creation role
│   ├── trunking/tasks/main.yml  # Trunk port configuration role
│   ├── access_ports/tasks/main.yml  # Access port assignment role
│   ├── stp/tasks/main.yml      # STP configuration role
│   ├── l3_distribution/tasks/main.yml  # L3 dist: routing, SVIs, OSPF
│   └── l2_gateway/tasks/main.yml      # L2 access: default-gateway
└── playbooks/
    └── rollback.yml             # Rollback to clean baseline (incl. L3)
```

---

## Prerequisites <a name="prerequisites"></a>

Before running the playbooks, ensure:

1. **SSH is enabled** on all 7 switches (done in Phase 1)
2. **VLAN 99 management connectivity** is working from VM-AUTO (done in Phase 2)
3. **VM-AUTO can SSH** to all switches:
   ```bash
   ssh admin@10.99.99.11   # SW-D-DEIE
   ssh admin@10.99.99.12   # SW-D-DCEE
   ssh admin@10.99.99.13   # SW-D-DMME
   ssh admin@10.99.99.21   # SW-A-DEIE
   ssh admin@10.99.99.22   # SW-A-DCEE
   ssh admin@10.99.99.23   # SW-A-DMME
   ssh admin@10.99.99.24   # SW-A-DIS
   ```

---

## Installation (One-Time) <a name="installation"></a>

On the VM-AUTO Docker container:

```bash
# Install the Cisco IOS Ansible collection
ansible-galaxy collection install cisco.ios

# Verify installation
ansible --version
ansible-galaxy collection list | grep cisco.ios
```

### Copy Files to VM-AUTO

**Option A — Git clone:**
```bash
cd /root
git clone https://github.com/Thimira20/Data-Networks-Project.git
cp -r Data-Networks-Project/automation/ansible-project /root/ansible-project
```

**Option B — Manual paste:**
```bash
mkdir -p /root/ansible-project
cd /root/ansible-project
# Paste each file using nano
```

---

## Running the Playbooks <a name="running"></a>

```bash
cd /root/ansible-project

# ── Full deployment (all 7 steps in order) ────────────────
ansible-playbook site.yml -v

# ── Dry-run (check what WOULD change, no actual changes) ─
ansible-playbook site.yml --check --diff

# ── Run individual roles using tags ───────────────────────
ansible-playbook site.yml --tags vlans            # Only VLANs
ansible-playbook site.yml --tags trunking         # Only trunks
ansible-playbook site.yml --tags access_ports     # Only access ports
ansible-playbook site.yml --tags stp              # Only STP
ansible-playbook site.yml --tags l3_distribution  # Only L3 dist config
ansible-playbook site.yml --tags l2_gateway       # Only L2 gateways
ansible-playbook site.yml --tags save             # Only save config

# ── Target specific switch groups ─────────────────────────
ansible-playbook site.yml --limit SW-A-DEIE       # Single switch
ansible-playbook site.yml --limit dist_switches   # Distribution only
ansible-playbook site.yml --limit access_switches # Access only

# ── Syntax check (no connection needed) ──────────────────
ansible-playbook site.yml --syntax-check
```

---

## Expected Outputs <a name="expected-outputs"></a>

### First Run (Fresh Deployment)

```
PLAY [Step 1 — Create VLANs on all switches] ***********************

TASK [vlans : Create VLANs with names] *****************************
changed: [SW-D-DEIE] => (item=VLAN 10 (VLAN_DEIE))
changed: [SW-D-DEIE] => (item=VLAN 20 (VLAN_DCEE))
...

PLAY [Step 2 — Configure trunk ports on all switches] **************

TASK [trunking : Configure trunk encapsulation and description] ****
changed: [SW-D-DEIE] => (item=GigabitEthernet0/2 → TRUNK_TO_SW-A-DEIE)
...

PLAY [Step 5 — Configure L3 distribution] **************************

TASK [l3_distribution : L3 Distribution — Enable ip routing] *******
changed: [SW-D-DEIE]
changed: [SW-D-DCEE]
changed: [SW-D-DMME]

TASK [l3_distribution : L3 Distribution — Configure routed uplink] *
changed: [SW-D-DEIE]   (GigabitEthernet0/0 → 10.0.10.2/30)
changed: [SW-D-DCEE]   (GigabitEthernet0/2 → 10.0.20.2/30)
changed: [SW-D-DMME]   (GigabitEthernet0/3 → 10.0.30.2/30)

TASK [l3_distribution : L3 Distribution — Create department VLAN SVI]
changed: [SW-D-DEIE]   (Vlan10 → 10.10.10.1/24)
changed: [SW-D-DCEE]   (Vlan20 → 10.10.20.1/24)
changed: [SW-D-DMME]   (Vlan30 → 10.10.30.1/24)

TASK [l3_distribution : L3 Distribution — Configure OSPF process] **
changed: [SW-D-DEIE]   (router-id 3.3.3.11)
changed: [SW-D-DCEE]   (router-id 3.3.3.12)
changed: [SW-D-DMME]   (router-id 3.3.3.13)

PLAY [Step 6 — Set L2 access switch default gateways] **************

TASK [l2_gateway : L2 Gateway — Set ip default-gateway] ************
changed: [SW-A-DEIE]   (10.99.99.11)
changed: [SW-A-DCEE]   (10.99.99.12)
changed: [SW-A-DMME]   (10.99.99.13)
changed: [SW-A-DIS]    (10.99.99.1)

PLAY RECAP *********************************************************
SW-D-DEIE   : ok=16  changed=12  unreachable=0  failed=0
SW-D-DCEE   : ok=16  changed=12  unreachable=0  failed=0
SW-D-DMME   : ok=16  changed=12  unreachable=0  failed=0
SW-A-DEIE   : ok=15  changed=11  unreachable=0  failed=0
SW-A-DCEE   : ok=15  changed=11  unreachable=0  failed=0
SW-A-DMME   : ok=15  changed=11  unreachable=0  failed=0
SW-A-DIS    : ok=15  changed=11  unreachable=0  failed=0
```

### Second Run (Idempotent — No Changes)

```
PLAY RECAP *********************************************************
SW-D-DEIE   : ok=16  changed=0   unreachable=0  failed=0
...
```

---

## Verification <a name="verification"></a>

### Verify L3 Distribution Switches

```bash
# Check ip routing is enabled
ansible dist_switches -m cisco.ios.ios_command -a "commands='show ip route'"

# Check OSPF neighbors
ansible dist_switches -m cisco.ios.ios_command -a "commands='show ip ospf neighbor'"

# Check SVIs are up
ansible dist_switches -m cisco.ios.ios_command -a "commands='show ip interface brief'"

# Check routed uplink
ansible dist_switches -m cisco.ios.ios_command -a "commands='show interfaces trunk'"

# Check Docker return route
ansible dist_switches -m cisco.ios.ios_command -a "commands='show ip route static'"
```

### Verify L2 Access Switches

```bash
# Check default gateway
ansible access_switches -m cisco.ios.ios_command -a "commands='show running-config | include default-gateway'"

# Check trunks
ansible access_switches -m cisco.ios.ios_command -a "commands='show interfaces trunk'"

# Check VLANs
ansible all_switches -m cisco.ios.ios_command -a "commands='show vlan brief'"
```

---

## Rollback <a name="rollback"></a>

To revert ALL automation changes and restore switches to clean baseline:

```bash
cd /root/ansible-project
ansible-playbook playbooks/rollback.yml -v
```

The rollback playbook runs in 3 phases:
1. **L3 Rollback** (dist switches): Removes OSPF, SVIs, static routes, disables ip routing, converts routed ports back to trunks
2. **L2 Rollback** (access switches): Removes ip default-gateway
3. **Baseline Reset** (all switches): Resets interfaces, removes VLANs, resets STP

⚠️ **WARNING:** Rollback will disrupt management connectivity!

---

## Troubleshooting <a name="troubleshooting"></a>

| Symptom | Likely Cause | Fix |
|---|---|---|
| `show ip route` shows "Default gateway is X" on dist switch | `ip routing` not enabled | Run: `ansible-playbook site.yml --tags l3_distribution --limit SW-D-XXXX` |
| OSPF neighbour not forming on dist switch | `passive-interface default` blocking uplink | Check `ospf_active_interface` in host_vars matches actual interface |
| Access switch can't reach Docker/Zabbix | Wrong `ip default-gateway` | Verify host_vars `default_gateway` → `.11`, `.12`, `.13`, or `.1` |
| SVI shows `up/down` on dist switch | VLAN has no active ports | Check trunk downlink is up: `show interfaces trunk` |
| `ip default-gateway` still present on dist switch | L3 role didn't remove it | Run: `ansible-playbook site.yml --tags l3_distribution` |
| VLAN 99 not reachable across dist switches | Missing Docker /32 return route | Check `show ip route 10.99.99.100` on dist switches |
| R-CORE has no OSPF routes | OSPF adjacency not formed | Check `show ip ospf neighbor` on SW-CORE |

### Manual Connectivity Test from Docker

```bash
# Management VLAN reachability
ping -c 3 10.99.99.1      # SW-Core
ping -c 3 10.99.99.11     # SW-D-DEIE
ping -c 3 10.99.99.12     # SW-D-DCEE
ping -c 3 10.99.99.13     # SW-D-DMME
ping -c 3 10.99.99.21     # SW-A-DEIE
ping -c 3 10.99.99.22     # SW-A-DCEE
ping -c 3 10.99.99.23     # SW-A-DMME
ping -c 3 10.99.99.24     # SW-A-DIS
```
