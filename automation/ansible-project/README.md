# Ansible Switch Automation — EE8203 Project

## EE8203/EC8205 — Section 4.2: Ansible Network Automation

> This guide covers deploying and running the Ansible playbooks for switch configuration.
> Ansible is already installed on VM-AUTO (Ubuntu Docker container).

---

## Table of Contents

- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [Prerequisites](#prerequisites)
- [Installation (One-Time)](#installation)
- [Running the Playbooks](#running)
- [Expected Outputs](#expected-outputs)
- [Verification](#verification)
- [Rollback](#rollback)
- [Troubleshooting](#troubleshooting)

---

## Overview <a name="overview"></a>

This Ansible project automates the Layer 2 switch configuration for:

| Switch | Type | Department | MGMT IP |
|---|---|---|---|
| SW-D-DEIE | Distribution | DEIE | 10.99.99.11 |
| SW-D-DCEE | Distribution | DCEE | 10.99.99.12 |
| SW-D-DMME | Distribution | DMME | 10.99.99.13 |
| SW-A-DEIE | Access | DEIE | 10.99.99.21 |
| SW-A-DCEE | Access | DCEE | 10.99.99.22 |
| SW-A-DMME | Access | DMME | 10.99.99.23 |
| SW-A-DIS  | Access | DIS (Servers) | 10.99.99.24 |

> **Note:** SW-CORE is NOT managed by Ansible. It has L3 routing, ACLs, and OSPF
> that are already configured manually. SW-A-DIS connects directly to SW-CORE
> (there is no SW-D-DIS distribution switch in the topology).

### What Gets Configured

| Step | Role | What It Does |
|---|---|---|
| 1 | `vlans` | Creates VLANs 10, 20, 30, 40, 99, 100 with names |
| 2 | `trunking` | Configures trunk links (dot1q, native VLAN 100, allowed VLANs) |
| 3 | `access_ports` | Assigns PC-facing ports to department VLANs with PortFast |
| 4 | `stp` | Sets STP mode (rapid-pvst), priorities, and PortFast default |
| 5 | (save) | Writes running-config to NVRAM on all switches |

---

## Directory Structure <a name="directory-structure"></a>

```
ansible-project/
├── ansible.cfg                  # Ansible config (inventory path, timeouts)
├── README.md                    # This guide
├── site.yml                     # Master playbook — runs all roles in order
├── inventory/
│   └── hosts                    # Switch groups: dist_switches, access_switches
├── group_vars/
│   ├── all.yml                  # Shared: credentials, VLANs, trunk defaults
│   ├── dist_switches.yml        # Distribution: STP priority 24576
│   └── access_switches.yml     # Access: STP priority 32768, portfast
├── host_vars/
│   ├── SW-D-DEIE.yml            # Gi0/0→CORE, Gi0/2→SW-A-DEIE
│   ├── SW-D-DCEE.yml            # Gi0/2→CORE, Gi0/0→SW-A-DCEE
│   ├── SW-D-DMME.yml            # Gi0/3→CORE, Gi0/0→SW-A-DMME
│   ├── SW-A-DEIE.yml            # Gi0/0,Gi0/2→VLAN10, Gi0/1→trunk
│   ├── SW-A-DCEE.yml            # Gi0/1,Gi0/2→VLAN20, Gi0/0→trunk
│   ├── SW-A-DMME.yml            # Gi0/1,Gi0/2→VLAN30, Gi0/0→trunk
│   └── SW-A-DIS.yml             # Gi0/0,Gi0/1→VLAN40, Gi1/0→CORE
├── roles/
│   ├── vlans/tasks/main.yml     # VLAN creation role
│   ├── trunking/tasks/main.yml  # Trunk port configuration role
│   ├── access_ports/tasks/main.yml  # Access port assignment role
│   └── stp/tasks/main.yml      # STP configuration role
└── playbooks/
    └── rollback.yml             # Rollback to clean baseline
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
git clone https://github.com/YOUR_USERNAME/Data-Networks-Project.git
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

# ── Full deployment (all steps in order) ──────────────────
ansible-playbook site.yml -v

# ── Dry-run (check what WOULD change, no actual changes) ─
ansible-playbook site.yml --check --diff

# ── Run individual roles using tags ───────────────────────
ansible-playbook site.yml --tags vlans          # Only VLANs
ansible-playbook site.yml --tags trunking       # Only trunks
ansible-playbook site.yml --tags access_ports   # Only access ports
ansible-playbook site.yml --tags stp            # Only STP
ansible-playbook site.yml --tags save           # Only save config

# ── Target specific switches ─────────────────────────────
ansible-playbook site.yml --limit SW-A-DEIE     # Single switch
ansible-playbook site.yml --limit dist_switches # Distribution only
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
changed: [SW-D-DEIE] => (item=VLAN 30 (VLAN_DMME))
...

PLAY [Step 2 — Configure trunk ports on all switches] **************

TASK [trunking : Configure trunk encapsulation and description] ****
changed: [SW-D-DEIE] => (item=GigabitEthernet0/0 → TRUNK_TO_SW-CORE)
changed: [SW-D-DEIE] => (item=GigabitEthernet0/2 → TRUNK_TO_SW-A-DEIE)
...

PLAY RECAP *********************************************************
SW-D-DEIE   : ok=12  changed=8   unreachable=0  failed=0
SW-D-DCEE   : ok=12  changed=8   unreachable=0  failed=0
SW-D-DMME   : ok=12  changed=8   unreachable=0  failed=0
SW-A-DEIE   : ok=14  changed=10  unreachable=0  failed=0
SW-A-DCEE   : ok=14  changed=10  unreachable=0  failed=0
SW-A-DMME   : ok=14  changed=10  unreachable=0  failed=0
SW-A-DIS    : ok=14  changed=10  unreachable=0  failed=0
```

### Second Run (Idempotent — Already Configured)

```
PLAY RECAP *********************************************************
SW-D-DEIE   : ok=12  changed=0   unreachable=0  failed=0
SW-D-DCEE   : ok=12  changed=0   unreachable=0  failed=0
...
```

> `changed=0` on the second run proves **idempotency** — safe to re-run.

---

## Verification <a name="verification"></a>

After running the playbook, verify from VM-AUTO:

```bash
# Check VLANs on all switches
ansible all_switches -m cisco.ios.ios_command -a "commands='show vlan brief'"

# Check trunk ports
ansible all_switches -m cisco.ios.ios_command -a "commands='show interfaces trunk'"

# Check STP
ansible all_switches -m cisco.ios.ios_command -a "commands='show spanning-tree summary'"

# Check a specific switch
ansible SW-A-DEIE -m cisco.ios.ios_command -a "commands='show interfaces switchport'"
```

Or SSH into individual switches:
```bash
ssh admin@10.99.99.11
SW-D-DEIE# show vlan brief
SW-D-DEIE# show interfaces trunk
SW-D-DEIE# show spanning-tree
```

---

## Rollback <a name="rollback"></a>

To restore all switches to a clean baseline:

```bash
ansible-playbook playbooks/rollback.yml -v
```

This removes:
- All non-default VLANs (10, 20, 30, 40, 99, 100)
- Trunk and access port configurations
- STP customizations

> ⚠ **WARNING:** This will break management connectivity via VLAN 99.
> Only use for demonstrating rollback capability in the report.
> Re-run `site.yml` to restore the configuration.

**Target execution time:** < 5 minutes

---

## Troubleshooting <a name="troubleshooting"></a>

| Problem | Cause | Fix |
|---|---|---|
| `UNREACHABLE` on all switches | Network/SSH issue | Test `ssh admin@<IP>` from Docker container |
| `Authentication failed` | Wrong credentials | Verify `ansible_user`/`ansible_password` in `group_vars/all.yml` |
| `Unable to connect` timeout | GNS3 device slow | Increase `timeout` in `ansible.cfg` |
| `No module named cisco.ios` | Collection missing | Run `ansible-galaxy collection install cisco.ios` |
| `Provider error` or `connection error` | Wrong connection plugin | Ensure `ansible_connection: ansible.netcommon.network_cli` in `group_vars/all.yml` |
| VLANs created but trunk fails | Encapsulation not supported | Your switch image may not need `switchport trunk encapsulation dot1q` — remove that line from trunking role |
| `changed=0` on first run | Config already exists | This is correct if switches are already configured manually |
