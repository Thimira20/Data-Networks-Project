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

| If the device is...         | Script behaviour                                  | What this proves            |
| --------------------------- | ------------------------------------------------- | --------------------------- |
| **Already configured**      | Detects existing config → "SKIPPING (idempotent)" | Safe to re-run              |
| **Factory default / reset** | Pushes full config from scratch                   | Script works for deployment |

**For your report, demonstrate BOTH scenarios:**

1. Run on your working network → show "idempotent/skipped" output
2. Reset R-EDGE to defaults → run again → show fresh config applied

---

## Phase 1 — Enable SSH on ALL Network Devices <a name="phase-1"></a>

> **WHY:** Netmiko connects to devices via SSH. Without SSH enabled, the scripts
> cannot connect. This is the chicken-and-egg step — you must configure SSH
> **manually via GNS3 console** before automation can begin.
>
> **Reference:** This follows the same procedure as the workshop guide
> "Enabling SSH on Cisco IOS Switches" section.

### What SSH Needs (4 things)

Every Cisco IOS device requires these to accept SSH connections:

1. **Hostname** — must be set (not the default `Switch` or `Router`)
2. **Domain name** — needed to generate RSA key pair (hostname + domain = key label)
3. **RSA key pair** — the encryption key for SSH
4. **VTY lines** — configured for SSH + local authentication

### 1.1 Routers (R-CORE, R-EDGE) — Already Done ✅

Your router configs already include SSH setup. **Verify** by opening each router's
GNS3 console and running:

```
show ip ssh
```

**Expected:** `SSH Enabled - version 2.0` (or 1.99). If you see this, skip to
Phase 1.2.

**If SSH is NOT enabled**, paste this into each router's console:

```
enable
configure terminal

! ── SSH Prerequisites ──
hostname R-CORE
ip domain-name campus.uor.lk

! ── Create local user for SSH login ──
username admin privilege 15 secret admin123

! ── Generate RSA key pair (MUST come AFTER hostname + domain-name) ──
crypto key generate rsa general-keys modulus 2048

! ── Enable SSH version 2 ──
ip ssh version 2

! ── Configure VTY lines to accept SSH only ──
line vty 0 4
 transport input ssh
 login local
exit

end
write memory
```

Repeat for R-EDGE (change hostname to `R-EDGE`).

```
enable
configure terminal

! ── SSH Prerequisites ──
hostname R-EDGE
ip domain-name campus.uor.lk

! ── Create local user for SSH login ──
username admin privilege 15 secret admin123

! ── Generate RSA key pair (MUST come AFTER hostname + domain-name) ──
crypto key generate rsa general-keys modulus 2048

! ── Enable SSH version 2 ──
ip ssh version 2

! ── Configure VTY lines to accept SSH only ──
line vty 0 4
 transport input ssh
 login local
exit

end
write memory
```

---

### 1.2 SW-Core — Configure SSH

Open SW-Core's GNS3 console and paste:

```
enable
configure terminal

! ── SSH Configuration ──
! hostname SW-Core                    ← already set, skip if prompt shows SW-Core
ip domain-name campus.uor.lk
username admin privilege 15 secret admin123
crypto key generate rsa general-keys modulus 1024
ip ssh version 2

line vty 0 15
 transport input ssh
 login local
exit

end
write memory
```

> **Note:** Switches use `line vty 0 15` (16 VTY lines) instead of `0 4` (5 lines).
> Both work, but 0 15 allows more simultaneous SSH sessions.

**Verify:**

```
show ip ssh
```

Expected: `SSH Enabled - version 2.0`

```
show running-config | include username
```

Expected: `username admin privilege 15 secret ...`

---

### 1.3 Distribution Switches — Configure SSH

These switches are **missing SSH** in your current config. Open each one's GNS3
console and paste the commands below.

#### SW-D-DEIE

```
enable
configure terminal
ip domain-name campus.uor.lk
username admin privilege 15 secret admin123
crypto key generate rsa general-keys modulus 2048
ip ssh version 2
line vty 0 15
 transport input ssh
 login local
exit
end
write memory
```

#### SW-D-DCEE

```
enable
configure terminal
ip domain-name campus.uor.lk
username admin privilege 15 secret admin123
crypto key generate rsa general-keys modulus 2048
ip ssh version 2
line vty 0 15
 transport input ssh
 login local
exit
end
write memory
```

#### SW-D-DMME

```
enable
configure terminal
ip domain-name campus.uor.lk
username admin privilege 15 secret admin123
crypto key generate rsa general-keys modulus 2048
ip ssh version 2
line vty 0 15
 transport input ssh
 login local
exit
end
write memory
```

#### SW-D-DIS

```
enable
configure terminal
ip domain-name campus.uor.lk
username admin privilege 15 secret admin123
crypto key generate rsa general-keys modulus 2048
ip ssh version 2
line vty 0 15
 transport input ssh
 login local
exit
end
write memory
```

---

### 1.4 Access Switches — Configure SSH

SW-A-DEIE already has SSH ✅. The others need it.

```
enable
configure terminal
ip domain-name campus.uor.lk
username admin privilege 15 secret admin123
crypto key generate rsa general-keys modulus 2048
ip ssh version 2
line vty 0 15
 transport input ssh
 login local
exit
end
write memory
```

#### SW-A-DCEE

```
enable
configure terminal
ip domain-name campus.uor.lk
username admin privilege 15 secret admin123
crypto key generate rsa general-keys modulus 2048
ip ssh version 2
line vty 0 15
 transport input ssh
 login local
exit
end
write memory
```

#### SW-A-DMME

```
enable
configure terminal
ip domain-name campus.uor.lk
username admin privilege 15 secret admin123
crypto key generate rsa general-keys modulus 2048
ip ssh version 2
line vty 0 15
 transport input ssh
 login local
exit
end
write memory
```

#### SW-A-DIS

```
enable
configure terminal
ip domain-name campus.uor.lk
username admin privilege 15 secret admin123
crypto key generate rsa general-keys modulus 2048
ip ssh version 2
line vty 0 15
 transport input ssh
 login local
exit
end
write memory
```

---

### 1.5 Verify SSH on ALL Devices — Checklist

Run `show ip ssh` on every device from its GNS3 console:

| Device    | Console Command | Expected Output           |
| --------- | --------------- | ------------------------- |
| R-CORE    | `show ip ssh`   | SSH Enabled - version 2.0 |
| R-EDGE    | `show ip ssh`   | SSH Enabled - version 2.0 |
| SW-Core   | `show ip ssh`   | SSH Enabled - version 2.0 |
| SW-D-DEIE | `show ip ssh`   | SSH Enabled - version 2.0 |
| SW-D-DCEE | `show ip ssh`   | SSH Enabled - version 2.0 |
| SW-D-DMME | `show ip ssh`   | SSH Enabled - version 2.0 |
| SW-D-DIS  | `show ip ssh`   | SSH Enabled - version 2.0 |
| SW-A-DEIE | `show ip ssh`   | SSH Enabled - version 2.0 |
| SW-A-DCEE | `show ip ssh`   | SSH Enabled - version 2.0 |
| SW-A-DMME | `show ip ssh`   | SSH Enabled - version 2.0 |
| SW-A-DIS  | `show ip ssh`   | SSH Enabled - version 2.0 |

> **If `show ip ssh` returns "SSH has not been enabled":** The `crypto key generate rsa`
> command probably wasn't accepted. Check that both `hostname` and `ip domain-name`
> are set FIRST, then re-run `crypto key generate rsa general-keys modulus 1024`.

> **If your IOSvL2 image doesn't support SSH at all** (no `crypto` command available):
> Use telnet instead. Change `transport input ssh` to `transport input telnet` and
> update `device_type` in inventory.yaml from `cisco_ios` to `cisco_ios_telnet`.

---

## Phase 2 — Fix VLAN 99 Management Connectivity <a name="phase-2"></a>

> **WHY:** After the L3 distribution switch conversion, VLAN 99 is split into 4
> separate L2 islands. The Docker controller can only reach SW-Core directly.
> Distribution and access switches need routing fixes. Also, the ACL blocks ICMP
> to routers (ping fails, but SSH works).

### 2.1 Update ACL-MGMT-IN on SW-Core

Your current ACL permits SSH to routers but blocks ICMP (ping). Also need SSH
permits for the distribution switch point-to-point links.

**On SW-Core console:**

```
enable
configure terminal

! Remove the old ACL and rebuild with complete rules
no ip access-list extended ACL-MGMT-IN

ip access-list extended ACL-MGMT-IN
 remark ---- SSH management access ----
 permit tcp 10.99.99.0 0.0.0.255 10.99.99.0 0.0.0.255 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.0.0 0.0.0.255 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.1.0 0.0.0.255 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.10.0 0.0.0.3 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.20.0 0.0.0.3 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.30.0 0.0.0.3 eq 22
 remark ---- SNMP monitoring ----
 permit udp 10.99.99.0 0.0.0.255 host 10.10.40.100 eq 162
 permit udp 10.99.99.0 0.0.0.255 host 10.10.40.100 eq 161
 remark ---- ICMP for troubleshooting ----
 permit icmp 10.99.99.0 0.0.0.255 host 10.10.40.100
 permit icmp 10.99.99.0 0.0.0.255 10.99.99.0 0.0.0.255
 permit icmp 10.99.99.0 0.0.0.255 10.0.0.0 0.0.0.3
 permit icmp 10.99.99.0 0.0.0.255 10.0.1.0 0.0.0.3
 permit icmp 10.99.99.0 0.0.0.255 10.0.10.0 0.0.0.3
 permit icmp 10.99.99.0 0.0.0.255 10.0.20.0 0.0.0.3
 permit icmp 10.99.99.0 0.0.0.255 10.0.30.0 0.0.0.3
 remark ---- Block MGMT from reaching user VLANs ----
 deny ip 10.99.99.0 0.0.0.255 10.10.10.0 0.0.0.255
 deny ip 10.99.99.0 0.0.0.255 10.10.20.0 0.0.0.255
 deny ip 10.99.99.0 0.0.0.255 10.10.30.0 0.0.0.255
 deny ip 10.99.99.0 0.0.0.255 10.10.40.0 0.0.0.255
 deny ip 10.99.99.0 0.0.0.255 any
exit

end
write memory
```

### 2.2 Add Static /32 Host Routes on SW-Core

These override the connected /24 route, forcing MGMT traffic to distribution
switch islands through the routed links.

**On SW-Core console:**

```
enable
configure terminal

! Route to SW-D-DEIE island (SW-D-DEIE + SW-A-DEIE)
ip route 10.99.99.11 255.255.255.255 10.0.10.2
ip route 10.99.99.21 255.255.255.255 10.0.10.2

! Route to SW-D-DCEE island (SW-D-DCEE + SW-A-DCEE)
ip route 10.99.99.12 255.255.255.255 10.0.20.2
ip route 10.99.99.22 255.255.255.255 10.0.20.2

! Route to SW-D-DMME island (SW-D-DMME + SW-A-DMME)
ip route 10.99.99.13 255.255.255.255 10.0.30.2
ip route 10.99.99.23 255.255.255.255 10.0.30.2

end
write memory
```

### 2.3 Add Return Routes on Distribution Switches

Each distribution switch needs a route back to the Docker container.

**On SW-D-DEIE console:**

```
enable
configure terminal
ip route 10.99.99.100 255.255.255.255 10.0.10.1
end
write memory
```

**On SW-D-DCEE console:**

```
enable
configure terminal
ip route 10.99.99.100 255.255.255.255 10.0.20.1
end
write memory
```

**On SW-D-DMME console:**

```
enable
configure terminal
ip route 10.99.99.100 255.255.255.255 10.0.30.1
end
write memory
```

### 2.4 Update Access Switch Default Gateways

After L3 conversion, access switches behind distribution switches can no longer
reach SW-Core (10.99.99.1) directly on VLAN 99. Change their default gateway to
their local distribution switch.

**On SW-A-DEIE console:**

```
enable
configure terminal
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.11
end
write memory
```

**On SW-A-DCEE console:**

```
enable
configure terminal
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.12
end
write memory
```

**On SW-A-DMME console:**

```
enable
configure terminal
no ip default-gateway 10.99.99.1
ip default-gateway 10.99.99.13
end
write memory
```

> **SW-A-DIS — NO CHANGE** — it connects directly to SW-Core via trunk,
> so its default-gateway 10.99.99.1 still works.

---

## Phase 3 — Setup Docker Ubuntu Controller in GNS3 <a name="phase-3"></a>

### 3.1 Add the Docker Container Node

1. In GNS3: **Edit → Preferences → Docker containers → New**
2. Image: `gns3/ubuntu:noble` (pull from Docker Hub if not available)
3. Name: `Automation-Controller`
4. Adapters: **2** (eth0 for MGMT, eth1 for Internet/package downloads)
5. Start command: `/bin/bash`
6. Click **Apply → OK**
7. Drag the new node onto your GNS3 workspace

### 3.2 Connect to GNS3 Topology

Draw **two cables** from the Docker container:

```
                    ┌──────────────────┐
          eth0 ─────│  Docker Ubuntu   │───── eth1
            │       │ Automation-Ctrl  │        │
            │       └──────────────────┘        │
            │                                   │
     SW-Core (any free port)              GNS3 NAT Node
     e.g. GigabitEthernet1/0              (for internet)
```

**Cable 1 — eth0 → SW-Core:**

- Connect Docker's `eth0` to any unused port on SW-Core (e.g., Gi1/0 or Gi3/3)
- If no ports are free: right-click SW-Core in GNS3 → **Configure** → increase adapter count

**Cable 2 — eth1 → GNS3 NAT node:**

- Add a **NAT** node: right-click workspace → Add node → search "NAT"
- Connect Docker's `eth1` to the NAT node
- This gives the container internet access for downloading packages

### 3.3 Configure SW-Core Port for Docker (VLAN 99 Access)

**On SW-Core console** — configure the port where Docker is connected:

```
enable
configure terminal
interface GigabitEthernet1/0
 description AUTOMATION_CONTROLLER_DOCKER
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

   > **Note on Netplan:** GNS3 Docker container images do **not** use `netplan` or `systemd`. Using the `ip addr` / `ip route` commands above is all that is required. If a default route already exists (`RTNETLINK answers: File exists`), it can be safely ignored.

5. **Test connectivity** from the Docker container:

   ```bash
   ping -c 3 10.99.99.1     # SW-Core (should succeed immediately)
   ping -c 3 10.99.99.11    # SW-D-DEIE (should succeed)
   ping -c 3 10.0.0.2       # R-CORE (should succeed — routed via OSPF)
   ping -c 3 10.0.1.2       # R-EDGE (should succeed — routed via OSPF)
   ```

   > **If pings to R-CORE/R-EDGE fail with `Packet filtered`:** An ACL on SW-Core or R-CORE is dropping ICMP (ping) packets. Test SSH directly (`ssh admin@10.0.0.2`), as management policies permit SSH (TCP 22) even if ping is blocked.
   >
   > **If pings to SW-D-DEIE (10.99.99.11) fail with `Destination Host Unreachable`:** Check that SW-D-DEIE is powered on, `interface Vlan99` is configured with `ip address 10.99.99.11 255.255.255.0` and `no shutdown`, and the trunk port to SW-Core is UP and allowing VLAN 99.

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

> **Why `--break-system-packages`?** Ubuntu 24.04 blocks pip installs outside a
> virtual environment by default. This flag overrides it. Alternatively:
>
> ```bash
> python3 -m venv /root/netmiko_env
> source /root/netmiko_env/bin/activate
> pip install netmiko pyyaml
> # Add 'source /root/venv/bin/activate' to /root/.bashrc for persistence
> ```

**Verify installation:**

```bash
python3 -c "import netmiko; print(f'Netmiko version: {netmiko.__version__}')"
python3 -c "import yaml; print('PyYAML OK')"
```

Expected:

```
Netmiko version: 4.x.x
PyYAML OK
```

> **Packages ARE persistent** in GNS3 Docker containers. Once installed, they
> survive container stop/start. You do NOT need to reinstall them each time.

---

## Phase 5 — Deploy & Run Automation Scripts <a name="phase-5"></a>

### 5.1 Create Script Directory

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
>
> ```bash
> ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 admin@10.0.0.2
> ```
>
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

| Problem                              | Cause                                    | Fix                                                                              |
| ------------------------------------ | ---------------------------------------- | -------------------------------------------------------------------------------- |
| `show ip ssh` says "not enabled"     | Missing hostname or domain-name          | Set both, then re-run `crypto key generate rsa`                                  |
| `crypto key generate rsa` fails      | Image has no crypto support              | Use telnet: change `transport input telnet`, use `device_type: cisco_ios_telnet` |
| `Connection timed out` (Netmiko)     | Device unreachable from Docker           | Run `ping <IP>` from Docker, check Phase 2 routes                                |
| `Authentication failed`              | Wrong credentials                        | Verify `username admin privilege 15 secret admin123` on device                   |
| SSH works but says `% Bad secrets`   | Enable password mismatch                 | Set `secret` in inventory.yaml to match device's enable secret                   |
| `No matching key exchange`           | Old SSH algorithms on c7200              | Uncomment `disabled_algorithms` in Python scripts                                |
| Docker loses IP on restart           | Network not persistent                   | Run `/root/startup.sh` or check Phase 3.5 .bashrc setup                          |
| Docker can't install pip packages    | No internet on eth1                      | Check NAT node connection, run `dhclient eth1`                                   |
| `ModuleNotFoundError: netmiko`       | pip install failed or venv not activated | Re-run `pip3 install netmiko pyyaml --break-system-packages`                     |
| Ping to switch works but SSH refused | SSH not configured                       | Go back to Phase 1, configure SSH on that switch                                 |
| Script connects but hangs            | Device sending unexpected prompts        | Add `verbose=True` to `ConnectHandler()` call for debugging                      |

---

## File Structure <a name="file-structure"></a>

```
netmiko_automation/
├── inventory.yaml              ← Device inventory (YAML) — ALL parameters here
├── 01_configure_routers.py     ← R-CORE + R-EDGE: interfaces, OSPF, NAT, ACLs
├── 02_configure_snmp_all.py    ← SNMP push to ALL 10 devices
├── 03_verify_config.py         ← Runs show commands, logs output
├── README.md                   ← This guide
└── logs/                       ← Auto-created timestamped log files
    ├── router_config_YYYY-MM-DD_HH-MM-SS.log
    ├── snmp_config_YYYY-MM-DD_HH-MM-SS.log
    └── verification_YYYY-MM-DD_HH-MM-SS.log
```

## Required Python Libraries

| Library     | Install Command               | Purpose                      |
| ----------- | ----------------------------- | ---------------------------- |
| `netmiko`   | `pip3 install netmiko`        | SSH automation for Cisco IOS |
| `pyyaml`    | `pip3 install pyyaml`         | Parse YAML inventory file    |
| Python 3.8+ | Pre-installed on Ubuntu Noble | Script runtime               |
