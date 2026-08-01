# Complete Guide: Network Automation with Netmiko on GNS3

## EE8203/EC8205 — Section 4.1: Netmiko Python Automation

> This guide covers **every step** from zero to running the automation scripts.
> Nothing is assumed. Follow each phase in order.

---

## Table of Contents

- [Phase 0 — Understand What We're Doing](#phase-0)
- [Phase 1 — Enable SSH on ALL Network Devices](#phase-1)
- [Phase 2 — Fix VLAN 99 Management Connectivity](#phase-2)
- [Phase 3 — Setup Docker Ubuntu Controller in GNS3](#phase-3)
- [Phase 4 — Install Python & Libraries on Ubuntu](#phase-4)
- [Phase 5 — Deploy & Run Automation Scripts](#phase-5)
- [Phase 6 — Demonstrate Idempotency for Report](#phase-6)
- [Troubleshooting](#troubleshooting)
- [File Structure](#file-structure)

---

## Phase 0 — Understand What We're Doing <a name="phase-0"></a>

Your GNS3 network is **already configured manually**. The automation scripts
**re-apply the same configuration via SSH**, proving you can manage devices
programmatically.

| If the device is... | Script behaviour | What this proves |
|---|---|---|
| **Already configured** | Detects existing config → "SKIPPING (idempotent)" | Safe to re-run |
| **Factory default / reset** | Pushes full config from scratch | Script works for deployment |

**For your report, demonstrate BOTH** — run on working network (shows idempotency),
then reset one router and run again (shows actual deployment).

**Execution flow:**

```
┌────────────────────────────────────────────────────────────┐
│ Docker Ubuntu Container (gns3/ubuntu:noble)                │
│ IP: 10.99.99.100/24 on VLAN 99                            │
│                                                            │
│ Python3 + Netmiko ──SSH──→ R-CORE (10.0.0.2)              │
│                    ──SSH──→ R-EDGE (10.0.1.2)              │
│                    ──SSH──→ SW-Core (10.99.99.1)           │
│                    ──SSH──→ SW-D-DEIE (10.99.99.11)        │
│                    ──SSH──→ ... all 10 devices              │
└────────────────────────────────────────────────────────────┘
```

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
crypto key generate rsa general-keys modulus 1024

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
crypto key generate rsa general-keys modulus 1024
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
crypto key generate rsa general-keys modulus 1024
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
crypto key generate rsa general-keys modulus 1024
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
crypto key generate rsa general-keys modulus 1024
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

#### SW-A-DCEE

```
enable
configure terminal
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

#### SW-A-DMME

```
enable
configure terminal
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

#### SW-A-DIS

```
enable
configure terminal
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

---

### 1.5 Verify SSH on ALL Devices — Checklist

Run `show ip ssh` on every device from its GNS3 console:

| Device | Console Command | Expected Output |
|---|---|---|
| R-CORE | `show ip ssh` | SSH Enabled - version 2.0 |
| R-EDGE | `show ip ssh` | SSH Enabled - version 2.0 |
| SW-Core | `show ip ssh` | SSH Enabled - version 2.0 |
| SW-D-DEIE | `show ip ssh` | SSH Enabled - version 2.0 |
| SW-D-DCEE | `show ip ssh` | SSH Enabled - version 2.0 |
| SW-D-DMME | `show ip ssh` | SSH Enabled - version 2.0 |
| SW-D-DIS | `show ip ssh` | SSH Enabled - version 2.0 |
| SW-A-DEIE | `show ip ssh` | SSH Enabled - version 2.0 |
| SW-A-DCEE | `show ip ssh` | SSH Enabled - version 2.0 |
| SW-A-DMME | `show ip ssh` | SSH Enabled - version 2.0 |
| SW-A-DIS | `show ip ssh` | SSH Enabled - version 2.0 |

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

> Change `GigabitEthernet1/0` to match the actual port you connected the cable to.

### 3.4 Start and Configure the Docker Container

Start the Docker container (right-click → Start), then open its console.

#### Configure eth0 (Management VLAN 99)

```bash
# Set static IP on management interface
ip addr add 10.99.99.100/24 dev eth0
ip link set eth0 up
```

#### Configure eth1 (Internet via NAT node)

```bash
# Get internet access via DHCP on the NAT interface
dhclient eth1 2>/dev/null || (ip link set eth1 up && udhcpc -i eth1 2>/dev/null)
```

> If `dhclient` isn't available, try: `ip addr add 192.168.122.100/24 dev eth1 && ip route add default via 192.168.122.1`
> (GNS3 NAT node default subnet is 192.168.122.0/24, gateway 192.168.122.1)

#### Set default route for management (important!)

```bash
# Remove any existing default route
ip route del default 2>/dev/null

# Default route via NAT node (for internet/package downloads)
ip route add default via 192.168.122.1

# Add specific routes for campus network (via VLAN 99 gateway)
ip route add 10.0.0.0/8 via 10.99.99.1
```

#### Configure DNS

```bash
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
```

#### Test connectivity

```bash
# Test management network
ping -c 2 10.99.99.1       # SW-Core (must work)

# Test internet (for package downloads)
ping -c 2 8.8.8.8          # Google DNS (must work via NAT node)
```

### 3.5 Make Network Configuration Persistent

GNS3 Docker container filesystems **are persistent** within the project
(changes survive stop/start). But network config set with `ip addr` is
**in-memory only** — lost on container restart. Fix this with a startup script:

```bash
# Create the persistent startup script
cat > /root/startup.sh << 'SCRIPT'
#!/bin/bash
# ============================================
# Network Automation Controller — Startup Script
# This runs every time the container starts
# ============================================

echo "[*] Configuring network interfaces..."

# eth0: Management VLAN 99
ip addr flush dev eth0
ip addr add 10.99.99.100/24 dev eth0
ip link set eth0 up

# eth1: Internet via GNS3 NAT node
ip link set eth1 up
# Try DHCP first, fall back to static
dhclient eth1 2>/dev/null || ip addr add 192.168.122.100/24 dev eth1

# Routing
ip route del default 2>/dev/null
ip route add default via 192.168.122.1      # Internet via NAT
ip route add 10.0.0.0/8 via 10.99.99.1      # Campus via SW-Core

# DNS
echo "nameserver 8.8.8.8" > /etc/resolv.conf

echo "[*] Network ready."
echo "    Management: 10.99.99.100 (eth0)"
echo "    Internet:   via NAT node (eth1)"
SCRIPT

chmod +x /root/startup.sh
```

**Make it run automatically on every login:**

```bash
# Add to .bashrc so it runs when you open the console
echo '' >> /root/.bashrc
echo '# Auto-configure network on login' >> /root/.bashrc
echo 'if [ ! -f /tmp/.network_configured ]; then' >> /root/.bashrc
echo '    /root/startup.sh' >> /root/.bashrc
echo '    touch /tmp/.network_configured' >> /root/.bashrc
echo 'fi' >> /root/.bashrc
```

> The `/tmp/.network_configured` flag prevents the script from running multiple times
> if you open multiple terminal tabs. It resets on container restart (since /tmp is volatile).

**Test persistence:** Stop the container → Start it again → Open console →
network should auto-configure.

---

## Phase 4 — Install Python & Libraries <a name="phase-4"></a>

Inside the Docker container console:

```bash
# Update package manager
apt update

# Install Python3, pip, SSH client, and text editor
apt install -y python3 python3-pip openssh-client iputils-ping nano

# Install Netmiko and YAML parser
pip3 install netmiko pyyaml --break-system-packages
```

> **Why `--break-system-packages`?** Ubuntu 24.04 blocks pip installs outside a
> virtual environment by default. This flag overrides it. Alternatively:
> ```bash
> python3 -m venv /root/venv
> source /root/venv/bin/activate
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
mkdir -p /root/netmiko_automation/logs
cd /root/netmiko_automation
```

### 5.2 Copy Scripts into the Container

**Option A — Type/paste each file manually:**

```bash
nano inventory.yaml           # Paste content, Ctrl+O to save, Ctrl+X to exit
nano 01_configure_routers.py
nano 02_configure_snmp_all.py
nano 03_verify_config.py
```

**Option B — Use SCP from your Windows PC** (if you can reach the Docker IP):

```powershell
scp "d:\8th sem\DAta Networks\Project\netmiko_automation\*" root@10.99.99.100:/root/netmiko_automation/
```

**Option C — Clone from GitHub:**

```bash
apt install -y git
cd /root
git clone https://github.com/YOUR_USERNAME/Data-Networks-Project.git
cp -r Data-Networks-Project/netmiko_automation/* /root/netmiko_automation/
```

### 5.3 Verify SSH Connectivity to ALL Devices

**Before running any script**, test SSH from the Docker container to every device:

```bash
# ── Switches on VLAN 99 (direct + via static routes) ──
ssh -o StrictHostKeyChecking=no admin@10.99.99.1     # SW-Core
ssh -o StrictHostKeyChecking=no admin@10.99.99.11    # SW-D-DEIE
ssh -o StrictHostKeyChecking=no admin@10.99.99.12    # SW-D-DCEE
ssh -o StrictHostKeyChecking=no admin@10.99.99.13    # SW-D-DMME
ssh -o StrictHostKeyChecking=no admin@10.99.99.14    # SW-D-DIS
ssh -o StrictHostKeyChecking=no admin@10.99.99.21    # SW-A-DEIE
ssh -o StrictHostKeyChecking=no admin@10.99.99.22    # SW-A-DCEE
ssh -o StrictHostKeyChecking=no admin@10.99.99.23    # SW-A-DMME
ssh -o StrictHostKeyChecking=no admin@10.99.99.24    # SW-A-DIS

# ── Routers (via OSPF routing through SW-Core) ──
ssh -o StrictHostKeyChecking=no admin@10.0.0.2       # R-CORE
ssh -o StrictHostKeyChecking=no admin@10.0.1.2       # R-EDGE
```

For each test: enter password `admin123`, you should see the device prompt
(e.g., `R-CORE#`). Type `exit` to disconnect.

> **If SSH fails with "Unable to negotiate"**: The device uses older SSH algorithms.
> Try: `ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa admin@<IP>`
> If this works, uncomment the `disabled_algorithms` line in each Python script's
> `build_connection_params()` function.

> **If SSH fails with "Connection refused"**: SSH is not enabled on that device.
> Go back to Phase 1 and configure SSH on that device.

> **If SSH fails with "No route to host"**: Routing issue. Go back to Phase 2
> and verify the static routes are in place.

### 5.4 Run the Scripts (In Order)

```bash
cd /root/netmiko_automation

# Script 1: Configure R-CORE and R-EDGE
# (interfaces, OSPF, NAT overload, router ACLs)
python3 01_configure_routers.py

# Script 2: Push SNMP to ALL 10 devices
# (community strings, trap destination)
python3 02_configure_snmp_all.py

# Script 3: Verify all configuration
# (runs show commands on every device)
python3 03_verify_config.py
```

### 5.5 Check Log Files

```bash
ls -la logs/
cat logs/router_config_*.log
cat logs/snmp_config_*.log
cat logs/verification_*.log
```

---

## Phase 6 — Demonstrate Idempotency for Report <a name="phase-6"></a>

### Step 1: Show "Already Configured" (Idempotent Run)

Run the scripts on your already-configured network:

```bash
python3 01_configure_routers.py
# Expected: "SKIPPING (idempotent)" for everything
```

**Screenshot this output** — it proves re-running doesn't create duplicates.

### Step 2: Reset One Router and Re-Deploy

```
! In GNS3, open R-EDGE console:
R-EDGE# write erase
R-EDGE# reload
! Wait for reload...

! Re-enable SSH (minimum needed for Netmiko to connect):
Router> enable
Router# configure terminal
Router(config)# hostname R-EDGE
R-EDGE(config)# ip domain-name campus.uor.lk
R-EDGE(config)# username admin privilege 15 secret admin123
R-EDGE(config)# crypto key generate rsa general-keys modulus 1024
R-EDGE(config)# ip ssh version 2
R-EDGE(config)# line vty 0 4
R-EDGE(config-line)# transport input ssh
R-EDGE(config-line)# login local
R-EDGE(config-line)# exit
R-EDGE(config)# interface GigabitEthernet0/0
R-EDGE(config-if)# ip address 10.0.1.2 255.255.255.252
R-EDGE(config-if)# no shutdown
R-EDGE(config-if)# end
R-EDGE# write memory
```

> You need the interface IP and SSH configured manually so Netmiko can reach
> and authenticate to the device. The script will then push the rest.

Now run the script again:

```bash
python3 01_configure_routers.py
# Expected: R-CORE shows "SKIPPING", R-EDGE shows actual config being pushed
```

**Screenshot this output** — it proves the script can deploy from scratch.

---

## Troubleshooting <a name="troubleshooting"></a>

| Problem | Cause | Fix |
|---|---|---|
| `show ip ssh` says "not enabled" | Missing hostname or domain-name | Set both, then re-run `crypto key generate rsa` |
| `crypto key generate rsa` fails | Image has no crypto support | Use telnet: change `transport input telnet`, use `device_type: cisco_ios_telnet` |
| `Connection timed out` (Netmiko) | Device unreachable from Docker | Run `ping <IP>` from Docker, check Phase 2 routes |
| `Authentication failed` | Wrong credentials | Verify `username admin privilege 15 secret admin123` on device |
| SSH works but says `% Bad secrets` | Enable password mismatch | Set `secret` in inventory.yaml to match device's enable secret |
| `No matching key exchange` | Old SSH algorithms on c7200 | Uncomment `disabled_algorithms` in Python scripts |
| Docker loses IP on restart | Network not persistent | Run `/root/startup.sh` or check Phase 3.5 .bashrc setup |
| Docker can't install pip packages | No internet on eth1 | Check NAT node connection, run `dhclient eth1` |
| `ModuleNotFoundError: netmiko` | pip install failed or venv not activated | Re-run `pip3 install netmiko pyyaml --break-system-packages` |
| Ping to switch works but SSH refused | SSH not configured | Go back to Phase 1, configure SSH on that switch |
| Script connects but hangs | Device sending unexpected prompts | Add `verbose=True` to `ConnectHandler()` call for debugging |

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

| Library | Install Command | Purpose |
|---|---|---|
| `netmiko` | `pip3 install netmiko` | SSH automation for Cisco IOS |
| `pyyaml` | `pip3 install pyyaml` | Parse YAML inventory file |
| Python 3.8+ | Pre-installed on Ubuntu Noble | Script runtime |
