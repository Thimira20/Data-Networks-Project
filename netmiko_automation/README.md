# Netmiko Network Automation — Setup & Usage Guide

## EE8203/EC8205 — Section 4.1: Netmiko Python Automation (Routers)

---

## Table of Contents

1. [What This Automation Does (And Doesn't Do)](#1-what-this-automation-does)
2. [File Structure](#2-file-structure)
3. [Step 0 — Connect the Docker Ubuntu Container to GNS3](#step-0)
4. [Step 1 — Install Dependencies Inside the Container](#step-1)
5. [Step 2 — Copy Scripts into the Container](#step-2)
6. [Step 3 — Verify SSH Connectivity](#step-3)
7. [Step 4 — Run the Scripts](#step-4)
8. [Expected Outputs](#5-expected-outputs)
9. [How to Demonstrate Idempotency](#6-idempotency-demo)
10. [Troubleshooting](#7-troubleshooting)

---

## 1. What This Automation Does (And Doesn't Do) <a name="1-what-this-automation-does"></a>

Your GNS3 network is **already configured manually**. These scripts automate the
**same configuration** via Python + Netmiko SSH, proving you can manage network
devices programmatically instead of typing CLI commands one by one.

| If the device is... | Script behaviour | What this proves |
|---|---|---|
| **Already configured** (your current state) | Detects existing config → reports "SKIPPING (idempotent)" | Script is safe to re-run; no duplicate config |
| **Factory default / reset** | Pushes full configuration from scratch | Script actually works for deployment |

**For your report, demonstrate BOTH scenarios:**
1. Run on your working network → show "idempotent/skipped" output
2. Reset R-EDGE to defaults → run again → show fresh config applied

---

## 2. File Structure <a name="2-file-structure"></a>

```
netmiko_automation/
├── inventory.yaml              ← Device inventory (IPs, credentials, config params)
├── 01_configure_routers.py     ← Automates R-CORE + R-EDGE (interfaces, OSPF, NAT, ACLs)
├── 02_configure_snmp_all.py    ← Pushes SNMPv2c to ALL 10 devices
├── 03_verify_config.py         ← Runs show commands and reports results
├── README.md                   ← This file
└── logs/                       ← Auto-created: timestamped log files
    ├── router_config_2026-07-31_16-30-00.log
    ├── snmp_config_2026-07-31_16-35-00.log
    └── verification_2026-07-31_16-40-00.log
```

---

## 3. Step 0 — Connect the Docker Ubuntu Container to GNS3 <a name="step-0"></a>

The Docker container (`gns3/ubuntu:noble`) is your **automation controller node**.
It must be connected to the VLAN 99 management network to reach all devices via SSH.

### Where to Connect

Connect the Docker container to **SW-Core** on any available port, configured as a
**VLAN 99 access port**.

```
              [ SW-CORE ]
             /  |  |  \   \
          Gi0/0 ... Gi0/3  Gi1/0  ← Connect Docker here
            ↓              ↓
         R-CORE     🐧 Docker Ubuntu
                    IP: 10.99.99.100/24
                    GW: 10.99.99.1
```

### Step-by-Step in GNS3

1. **Add the Docker container** to your GNS3 topology:
   - Right-click the workspace → **Add a node** → **End Devices** → **ubuntu-noble**
   - (If it's not listed, go to **Edit → Preferences → Docker containers** and add
     the image `gns3/ubuntu:noble`)

2. **Connect it to SW-Core**:
   - Draw a cable from the Docker container's `eth0` to an **unused port** on SW-Core
     (e.g., `GigabitEthernet1/0` or any free port).
   - If SW-Core doesn't have free ports, right-click SW-Core → **Configure** → increase
     the **Adapters** count, then reconnect.

3. **Configure the SW-Core port as VLAN 99 access**:
   ```
   enable
   configure terminal
   interface GigabitEthernet1/0
    description AUTOMATION_CONTROLLER
    switchport access vlan 99
    switchport mode access
    spanning-tree portfast
    no shutdown
   exit
   end
   write memory
   ```
   > **Note:** If SW-Core's uplink ports are routed (`no switchport`), other ports
   > can still be regular switchports. The switch supports both modes simultaneously.

   > **Note:** If your IOSvL2 doesn't accept `switchport access vlan 99`, check that
   > VLAN 99 exists first (`show vlan brief`). If not, create it: `vlan 99` → `name MGMT`.

4. **Configure the Docker container's network**:
   - Start the Docker container (right-click → Start)
   - Open its console (right-click → Console, or double-click)
   - Inside the container terminal:

   ```bash
   # Set IP address on eth0
   ip addr add 10.99.99.100/24 dev eth0
   ip link set eth0 up

   # Set default gateway (SW-Core's VLAN 99 SVI)
   ip route add default via 10.99.99.1
   ```

   For **persistent** network config (survives reboot), create a netplan file:
   ```bash
   cat > /etc/netplan/01-mgmt.yaml << 'EOF'
   network:
     version: 2
     ethernets:
       eth0:
         addresses:
           - 10.99.99.100/24
         routes:
           - to: default
             via: 10.99.99.1
   EOF
   netplan apply
   ```

5. **Test connectivity** from the Docker container:
   ```bash
   ping -c 3 10.99.99.1     # SW-Core (should succeed immediately)
   ping -c 3 10.99.99.11    # SW-D-DEIE (should succeed)
   ping -c 3 10.0.0.2       # R-CORE (should succeed — routed via OSPF)
   ping -c 3 10.0.1.2       # R-EDGE (should succeed — routed via OSPF)
   ```

   > **If pings to R-CORE/R-EDGE fail:** These IPs are reached via OSPF routing
   > through SW-Core. Make sure OSPF is working (`show ip ospf neighbor` on SW-Core
   > should show R-CORE as FULL).

---

## 4. Step 1 — Install Dependencies Inside the Docker Container <a name="step-1"></a>

Inside the Docker Ubuntu console:

```bash
# Update package list
apt update

# Install Python3, pip, and SSH client
apt install -y python3 python3-pip openssh-client nano

# Install the required Python libraries
pip3 install netmiko pyyaml --break-system-packages
```

> **Why `--break-system-packages`?** Ubuntu Noble (24.04) blocks pip installs outside
> a virtual environment by default. This flag overrides that restriction. Alternatively,
> use a venv:
> ```bash
> python3 -m venv /root/netmiko_env
> source /root/netmiko_env/bin/activate
> pip install netmiko pyyaml
> ```

---

## 5. Step 2 — Copy Scripts into the Container <a name="step-2"></a>

### Option A: Type/Paste Directly (Simplest)

In the Docker console, create the files manually:

```bash
mkdir -p /root/netmiko_automation
cd /root/netmiko_automation
nano inventory.yaml        # Paste the YAML content, save with Ctrl+O, exit Ctrl+X
nano 01_configure_routers.py
nano 02_configure_snmp_all.py
nano 03_verify_config.py
```

### Option B: Git Clone (If You've Pushed to GitHub)

```bash
apt install -y git
cd /root
git clone https://github.com/YOUR_USERNAME/Data-Networks-Project.git
cd Data-Networks-Project/netmiko_automation
```

### Option C: SCP from Host PC

If your Windows PC can reach the Docker container:
```powershell
scp -r "d:\8th sem\DAta Networks\Project\netmiko_automation\*" root@10.99.99.100:/root/netmiko_automation/
```

---

## 6. Step 3 — Verify SSH Connectivity Before Running Scripts <a name="step-3"></a>

Test SSH access from the Docker container to each device type:

```bash
# Test SSH to SW-Core (direct VLAN 99)
ssh admin@10.99.99.1

# Test SSH to R-CORE (routed)
ssh admin@10.0.0.2

# Test SSH to R-EDGE (routed via R-CORE)
ssh admin@10.0.1.2

# Test SSH to an access switch
ssh admin@10.99.99.21
```

For each test, you should see:
```
Password: admin123
R-CORE#
```

Type `exit` to disconnect after each test.

> **If SSH fails with "Unable to negotiate" or "no matching key exchange":**
> The c7200 may use older SSH algorithms. Add this to the SSH command:
> ```bash
> ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 admin@10.0.0.2
> ```
> If this is the issue, uncomment the `disabled_algorithms` line in each script's
> `build_connection_params()` function.

---

## 7. Step 4 — Run the Scripts <a name="step-4"></a>

Run in this order:

```bash
cd /root/netmiko_automation

# Script 1: Configure R-CORE and R-EDGE (interfaces, OSPF, NAT, ACLs)
python3 01_configure_routers.py

# Script 2: Push SNMP to ALL devices (routers + switches)
python3 02_configure_snmp_all.py

# Script 3: Verify everything
python3 03_verify_config.py
```

Each script creates a timestamped log file in the `logs/` directory.

---

## 8. Expected Outputs <a name="5-expected-outputs"></a>

### Script 1 — First Run (already configured)
```
[16:30:00] ============================================================
[16:30:00]   NETMIKO ROUTER CONFIGURATION SCRIPT
[16:30:00]   EE8203 — Network Automation with Python (Netmiko)
[16:30:00]   Timestamp: 2026-07-31_16-30-00
[16:30:00] ============================================================
[16:30:00] ✓ Inventory loaded: /root/netmiko_automation/inventory.yaml
[16:30:00]   Found 2 routers to configure

[16:30:00] [1/2] ──────────────────────────────────────────────────
[16:30:02] Connecting to R-CORE (10.0.0.2)...
[16:30:04]   ✓ SSH connection established to R-CORE
[16:30:05]   → GigabitEthernet0/0 already configured — SKIPPING (idempotent)
[16:30:06]   → GigabitEthernet0/1 already configured — SKIPPING (idempotent)
[16:30:07]   → OSPF process 1 already configured — SKIPPING (idempotent)
[16:30:08]   → ACL 'ACL-INFRASTRUCTURE-PROTECT' already exists — SKIPPING (idempotent)
[16:30:09]   → Saving configuration (write memory)...
[16:30:10]   ✓ R-CORE complete — 0 changes applied, 4 sections skipped (idempotent)

[16:30:10] [2/2] ──────────────────────────────────────────────────
[16:30:12] Connecting to R-EDGE (10.0.1.2)...
[16:30:14]   ✓ SSH connection established to R-EDGE
[16:30:15]   → GigabitEthernet0/0 already configured — SKIPPING (idempotent)
[16:30:16]   → GigabitEthernet0/1 already configured — SKIPPING (idempotent)
[16:30:17]   → OSPF process 1 already configured — SKIPPING (idempotent)
[16:30:18]   → NAT (NAT_ACL) already configured — SKIPPING (idempotent)
[16:30:19]   → Deploying ACL 'ACL-WAN-INBOUND'...         ← NEW ACL deployed!
[16:30:20]   ✓ ACL applied to GigabitEthernet0/1 (in)
[16:30:21]   ✓ R-EDGE complete — 1 changes applied, 4 sections skipped (idempotent)

[16:30:22] ============================================================
[16:30:22]   SUMMARY
[16:30:22]   Devices attempted:  2
[16:30:22]   Devices successful: 2
[16:30:22]   Total changes:      1
[16:30:22]   Log file:           logs/router_config_2026-07-31_16-30-00.log
[16:30:22] ============================================================
```

### Script 2 — SNMP Push
```
[16:35:00]   [R-CORE..............] (       10.0.0.2) ✓ SNMP already present — SKIPPED
[16:35:02]   [R-EDGE..............] (       10.0.1.2) ✓ SNMP already present — SKIPPED
[16:35:04]   [SW-Core.............] (     10.99.99.1) ✓ SNMP already present — SKIPPED
[16:35:06]   [SW-D-DEIE...........] (    10.99.99.11) ✓ SNMP configured successfully
[16:35:08]   [SW-D-DCEE...........] (    10.99.99.12) ✓ SNMP configured successfully
...
```

---

## 9. How to Demonstrate Idempotency (For Report) <a name="6-idempotency-demo"></a>

1. **First run** — scripts apply config (or skip if already present)
2. **Second run** — scripts detect everything is already configured, skip everything
3. **Show both log files side-by-side** in your report

To demonstrate fresh deployment:
```bash
# In GNS3, open R-EDGE console and factory reset:
R-EDGE# write erase
R-EDGE# reload

# Wait for R-EDGE to boot, then re-enable SSH manually:
# (The script can't connect without SSH being pre-configured)
R-EDGE> enable
R-EDGE# configure terminal
R-EDGE(config)# hostname R-EDGE
R-EDGE(config)# username admin privilege 15 secret admin123
R-EDGE(config)# ip domain-name campus.uor.lk
R-EDGE(config)# crypto key generate rsa general-keys modulus 1024
R-EDGE(config)# line vty 0 4
R-EDGE(config-line)# transport input ssh
R-EDGE(config-line)# login local
R-EDGE(config-line)# end
R-EDGE# write memory

# Now run the script — it will configure R-EDGE from scratch:
python3 01_configure_routers.py
```

---

## 10. Troubleshooting <a name="7-troubleshooting"></a>

| Problem | Cause | Fix |
|---|---|---|
| `Connection timed out` | Device unreachable | Check: `ping <device_ip>` from Docker container |
| `Authentication failed` | Wrong credentials | Check `inventory.yaml` username/password |
| `No matching key exchange` | Old SSH algorithms on c7200 | Uncomment `disabled_algorithms` in scripts |
| `SNMP command not recognized` | Device doesn't support SNMP | Some IOSvL2 images lack SNMP — check `show snmp ?` |
| Docker can't ping anything | IP/gateway not set on container | Run `ip addr show eth0` and check |
| Docker pings switches but not routers | OSPF not routing from VLAN 99 | Check `show ip route` on SW-Core |
| `ModuleNotFoundError: netmiko` | Python packages not installed | Run `pip3 install netmiko pyyaml` |

---

## Required Libraries

| Library | Version | Purpose |
|---|---|---|
| `netmiko` | ≥4.0 | SSH automation for Cisco IOS devices |
| `pyyaml` | ≥6.0 | Parse YAML inventory files |
| `Python` | ≥3.8 | Script runtime |

Install: `pip3 install netmiko pyyaml`
