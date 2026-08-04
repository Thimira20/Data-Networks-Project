# Zabbix 6.x LTS Deployment Guide — FoE-UoR Campus Network

## Table of Contents
1. [Architecture Decision: Where Does VM-ZABBIX Go?](#1-architecture-decision)
2. [Create the VM-ZABBIX Appliance in GNS3](#2-create-vm-zabbix-in-gns3)
3. [Network Connectivity — Wiring & IP Assignment](#3-network-connectivity)
4. [ACL Verification — Ensure SNMP/ICMP Traffic Flows](#4-acl-verification)
5. [Install Zabbix 6.0 LTS on Ubuntu 22.04](#5-install-zabbix)
6. [Host Onboarding — Add All Devices](#6-host-onboarding)
7. [Triggers and Alerts Configuration](#7-triggers-and-alerts)
8. [Dashboard Creation — "FoE-UoR Network"](#8-dashboard-creation)
9. [Export Dashboard JSON](#9-export-dashboard)
10. [Verification Checklist](#10-verification)

---

## 1. Architecture Decision: Where Does VM-ZABBIX Go? {#1-architecture-decision}

### Answer: You Need a NEW VM — Do NOT Reuse UbuntuDockerGuest-1

> [!IMPORTANT]
> Your project specification explicitly says **"VM-ZABBIX"** as a separate entity. The existing `UbuntuDockerGuest-1` is your automation host sitting in **VLAN 99 (MGMT)**. VM-ZABBIX must live in the **DIS VLAN (VLAN 40)** with IP **`10.10.40.100`**.

**Why a separate VM?**
- The project spec lists `VM-ZABBIX` as a distinct VM role
- Your ACLs are already designed for a Zabbix server at `10.10.40.100` (look at `ACL-DIS-IN` — it permits SNMP and ICMP from `host 10.10.40.100` to management/router subnets)
- Your SNMP trap destination in `inventory.yaml` already points to `10.10.40.100`
- Separation of concerns: automation VM ≠ monitoring VM

### Where Does It Connect?

```
                          SW-CORE
                            │
                         Gi1/0 (trunk)
                            │
                         SW-A-DIS
                          /    \
                     Gi0/1    Gi0/2
                       │        │
                     PC7      PC8
                    (VPCS)   (VPCS)
```

**VM-ZABBIX connects to SW-A-DIS** — this is the access switch for the DIS/Server-Farm department (VLAN 40). You will connect it to one of SW-A-DIS's access ports.

> [!NOTE]
> Looking at your topology, SW-A-DIS has:
> - `Gi0/0` → uplink trunk to SW-CORE (`Gi1/0`)
> - `Gi0/1` → PC7 (VLAN 40 access port)
> - `Gi0/2` → PC8 (VLAN 40 access port)
>
> You have two options:
> 1. **Replace PC7 or PC8** with VM-ZABBIX (simplest — just disconnect one VPCS)
> 2. **Add a new port** if your IOSvL2 switch image has more interfaces (e.g., `Gi0/3`, `Gi1/0`)
>
> **Recommendation: Replace PC8 with VM-ZABBIX** (or add to a free port). One VPCS endpoint in DIS is enough for testing.

---

## 2. Create the VM-ZABBIX Appliance in GNS3 {#2-create-vm-zabbix-in-gns3}

You have two approaches. Pick whichever matches your GNS3 setup:

### Option A: QEMU/KVM VM (Recommended for Full Ubuntu)

This is the proper way — run a full Ubuntu 22.04 VM inside GNS3.

#### Step 2A.1: Download Ubuntu 22.04 Server ISO

Download the Ubuntu 22.04.x LTS **Server** ISO (not Desktop — it's lighter):
- URL: `https://releases.ubuntu.com/22.04/`
- File: `ubuntu-22.04.5-live-server-amd64.iso` (~1.8 GB)

#### Step 2A.2: Create a QEMU VM in GNS3

1. In GNS3: **Edit → Preferences → QEMU → Qemu VMs → New**
2. Configure:
   - **Name:** `VM-ZABBIX`
   - **RAM:** `2048 MB` (minimum; 4096 MB recommended for Zabbix)
   - **vCPUs:** `2`
   - **Disk:** Create a new QCOW2 disk, at least **20 GB**
   - **CD/DVD:** Browse to the Ubuntu 22.04 ISO
   - **Network:** 1 adapter (e1000 or virtio)
3. Boot the VM and install Ubuntu 22.04 Server
   - During install, configure a static IP or use DHCP temporarily (we'll set static later)

### Option B: Docker Container (Lighter, Works Like Your Automation VM)

If your GNS3 already runs Docker well (like `UbuntuDockerGuest-1`), you can use a Docker container. However, Zabbix needs MySQL/PostgreSQL, Apache/Nginx — it's heavier than a simple automation container.

#### Step 2B.1: Use the Official Zabbix Docker Appliance

GNS3 Marketplace has a "Zabbix Appliance" template, or you can create one:

1. In GNS3: **Edit → Preferences → Docker → Docker containers → New**
2. Image: `ubuntu:22.04`
3. Name: `VM-ZABBIX`
4. Adapters: 1
5. Start command: `/bin/bash`

> [!WARNING]
> Docker containers lose data on restart unless you configure volumes. For a university project demo, this is usually fine. For production, use Option A (QEMU VM).

---

## 3. Network Connectivity — Wiring & IP Assignment {#3-network-connectivity}

### Step 3.1: Connect VM-ZABBIX to SW-A-DIS in GNS3

1. In the GNS3 canvas, **drag** the VM-ZABBIX node
2. Draw a link: `VM-ZABBIX eth0` → `SW-A-DIS Gi0/2` (or replace PC8's connection)
3. If replacing PC8: right-click PC8 → Delete, then connect VM-ZABBIX in its place

### Step 3.2: Verify the Switch Port is in VLAN 40

On **SW-A-DIS**, verify the port is an access port in VLAN 40:

```
enable
show running-config interface GigabitEthernet0/2
```

You should see:
```
interface GigabitEthernet0/2
 switchport mode access
 switchport access vlan 40
```

If it's not configured, set it:
```
enable
configure terminal
interface GigabitEthernet0/2
 switchport mode access
 switchport access vlan 40
 spanning-tree portfast
 no shutdown
exit
end
write memory
```

### Step 3.3: Configure Static IP on VM-ZABBIX

On the VM-ZABBIX Ubuntu machine, configure the network interface with the IP `10.10.40.100`:

```bash
# Check which interface name your VM has
ip link show
```

Typically it will be `eth0`, `ens3`, or `ens4`. Let's assume `eth0`.

#### For Netplan (Ubuntu 22.04 default):

```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

Replace contents with:

```yaml
network:
  version: 2
  ethernets:
    eth0:                        # Change to your actual interface name
      addresses:
        - 10.10.40.100/24
      routes:
        - to: default
          via: 10.10.40.1        # SW-Core VLAN 40 SVI is the gateway
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Apply the configuration:

```bash
sudo netplan apply
```

#### Verify connectivity:

```bash
# Verify IP assignment
ip addr show eth0

# Ping the VLAN 40 gateway (SW-Core SVI)
ping -c 3 10.10.40.1

# Ping a management switch (this tests cross-VLAN routing)
ping -c 3 10.99.99.1

# Ping a router
ping -c 3 10.0.0.2

# Test internet (needed to download Zabbix packages)
ping -c 3 8.8.8.8
```

> [!IMPORTANT]
> If `ping 10.99.99.1` works but `ping 8.8.8.8` fails, VM-ZABBIX might not have internet access. Check:
> 1. Is `10.10.40.0/24` in R-EDGE's NAT ACL? Looking at your inventory, the NAT `acl_number: 100` only permits `10.99.99.0`, `10.10.10.0`, `10.10.20.0` — **NOT** `10.10.40.0`!
> 2. You'll need to add `10.10.40.0/24` to the NAT ACL on R-EDGE to give VM-ZABBIX internet access for package downloads:
>
> ```
> R-EDGE# configure terminal
> R-EDGE(config)# access-list 100 permit ip 10.10.40.0 0.0.0.255 any
> R-EDGE(config)# end
> R-EDGE# write memory
> ```
>
> After Zabbix is installed, you can remove this if DIS shouldn't have permanent internet access.

---

## 4. ACL Verification — Ensure SNMP/ICMP Traffic Flows {#4-acl-verification}

Your ACLs are **already designed** to allow Zabbix monitoring traffic. Let's verify what's in place.

### 4.1: ACL-DIS-IN (on SW-Core, VLAN 40 SVI)

This ACL controls traffic **leaving** the DIS VLAN. Your existing rules already include:

```
! Already configured on SW-Core:
ip access-list extended ACL-DIS-IN
 permit udp host 10.10.40.100 10.99.99.0 0.0.0.255 eq 161    ← SNMP to switches
 permit udp host 10.10.40.100 10.0.0.0 0.0.0.255 eq 161      ← SNMP to R-CORE link
 permit udp host 10.10.40.100 10.0.1.0 0.0.0.255 eq 161      ← SNMP to R-EDGE link
 permit icmp host 10.10.40.100 10.99.99.0 0.0.0.255           ← ICMP ping to switches
 permit icmp host 10.10.40.100 10.0.0.0 0.0.0.255             ← ICMP ping to R-CORE
 permit icmp host 10.10.40.100 10.0.1.0 0.0.0.255             ← ICMP ping to R-EDGE
```

✅ **This is already perfect for Zabbix SNMP polling and ICMP monitoring.**

### 4.2: ACL-MGMT-IN (on SW-Core, VLAN 99 SVI)

This ACL needs to allow **SNMP responses** from switches back to Zabbix. Check:

```
 permit udp 10.99.99.0 0.0.0.255 host 10.10.40.100 eq 162    ← SNMP traps TO Zabbix
 permit udp 10.99.99.0 0.0.0.255 host 10.10.40.100 eq 161    ← SNMP queries TO Zabbix
 permit icmp 10.99.99.0 0.0.0.255 host 10.10.40.100           ← ICMP TO Zabbix
```

✅ **Already configured.**

### 4.3: What Might Be Missing

You may need to add ACL rules for SNMP to the **routed point-to-point subnets** (`10.0.10.0/30`, `10.0.20.0/30`, `10.0.30.0/30`) if you want Zabbix to poll distribution switch routed interfaces directly. However, since all switches have VLAN 99 management IPs and SNMP is configured to listen on all interfaces, polling via the `10.99.99.x` management IPs is sufficient.

> [!TIP]
> **SNMP traffic flow for Zabbix polling a switch:**
> ```
> VM-ZABBIX (10.10.40.100)  ──SNMP GET──►  SW-A-DEIE (10.99.99.21)
>     │                                           │
>     ├─ Leaves VLAN 40 SVI → ACL-DIS-IN ✅       │
>     ├─ Routed via SW-Core OSPF                  │
>     └─ Enters VLAN 99 SVI → no inbound ACL      │
>                                                  │
>     ◄──SNMP RESPONSE──────────────────────────────
>     │
>     ├─ Leaves VLAN 99 SVI → ACL-MGMT-IN ✅
>     └─ Routed back to VLAN 40
> ```

---

## 5. Install Zabbix 6.0 LTS on Ubuntu 22.04 {#5-install-zabbix}

> [!IMPORTANT]
> All commands below are run **inside VM-ZABBIX** (the Ubuntu 22.04 machine). Make sure it has internet access first (Step 3.3).

### Step 5.1: Update the System

```bash
sudo apt update && sudo apt upgrade -y
```

### Step 5.2: Install MySQL (MariaDB) Database Server

Zabbix needs a database backend. MariaDB is the recommended choice:

```bash
# Install MariaDB server
sudo apt install -y mariadb-server mariadb-client

# Start and enable MariaDB
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Secure the installation (set root password, remove test DB, etc.)
sudo mysql_secure_installation
```

During `mysql_secure_installation`:
- **Enter current password for root:** (press Enter — no password yet)
- **Switch to unix_socket authentication?** → `n`
- **Change the root password?** → `Y` → set to `ZabbixDB123!` (or your choice)
- **Remove anonymous users?** → `Y`
- **Disallow root login remotely?** → `Y`
- **Remove test database?** → `Y`
- **Reload privilege tables?** → `Y`

### Step 5.3: Create the Zabbix Database

```bash
sudo mysql -u root -p
```

Enter the root password you just set, then run these SQL commands:

```sql
-- Create the Zabbix database with UTF-8 support
CREATE DATABASE zabbix CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

-- Create a dedicated Zabbix user
CREATE USER 'zabbix'@'localhost' IDENTIFIED BY 'ZabbixDB123!';

-- Grant full permissions on the zabbix database
GRANT ALL PRIVILEGES ON zabbix.* TO 'zabbix'@'localhost';

-- Enable log_bin_trust_function_creators (required for Zabbix schema import)
SET GLOBAL log_bin_trust_function_creators = 1;

-- Apply changes
FLUSH PRIVILEGES;

-- Exit MySQL
QUIT;
```

> [!NOTE]
> **Why `log_bin_trust_function_creators`?** Zabbix's database schema includes stored functions. MySQL's binary logging requires this setting to allow non-SUPER users to create functions. Without it, the schema import will fail.

### Step 5.4: Install Zabbix 6.0 LTS Packages

```bash
# Download and install the Zabbix repository configuration package
wget https://repo.zabbix.com/zabbix/6.0/ubuntu/pool/main/z/zabbix-release/zabbix-release_6.0-5+ubuntu22.04_all.deb

sudo dpkg -i zabbix-release_6.0-5+ubuntu22.04_all.deb

# Update apt to include the new Zabbix repository
sudo apt update

# Install Zabbix server, web frontend, and agent
sudo apt install -y zabbix-server-mysql zabbix-frontend-php zabbix-apache-conf zabbix-sql-scripts zabbix-agent
```

**What each package does:**
| Package | Purpose |
|---------|---------|
| `zabbix-server-mysql` | The Zabbix server daemon (the brain — polls devices, evaluates triggers) |
| `zabbix-frontend-php` | The web UI (PHP-based, runs on Apache) |
| `zabbix-apache-conf` | Apache configuration files for Zabbix |
| `zabbix-sql-scripts` | SQL schema files to initialize the database |
| `zabbix-agent` | Agent to monitor VM-ZABBIX itself (optional but good practice) |

### Step 5.5: Import the Zabbix Database Schema

This populates the empty `zabbix` database with all required tables, triggers, and initial data:

```bash
sudo zcat /usr/share/zabbix-sql-scripts/mysql/server.sql.gz | mysql --default-character-set=utf8mb4 -uzabbix -p zabbix
```

Enter the Zabbix DB user password (`ZabbixDB123!`).

> [!WARNING]
> This import takes **2–5 minutes** depending on VM performance. Do NOT interrupt it. There will be no output until it completes — just wait.

After the import completes, disable the function creators flag (no longer needed):

```bash
sudo mysql -u root -p -e "SET GLOBAL log_bin_trust_function_creators = 0;"
```

### Step 5.6: Configure the Zabbix Server

Edit the main Zabbix server configuration file:

```bash
sudo nano /etc/zabbix/zabbix_server.conf
```

Find and set the database password line (around line 129):

```ini
# Before (commented out):
# DBPassword=

# After (uncommented with your password):
DBPassword=ZabbixDB123!
```

### Step 5.7: Configure PHP Timezone

Edit the Apache Zabbix config:

```bash
sudo nano /etc/zabbix/apache.conf
```

Find the `php_value date.timezone` line (there are TWO — one for `mod_php` and one for `php-fpm`). Uncomment and set your timezone:

```apache
php_value date.timezone Asia/Colombo
```

> [!NOTE]
> `Asia/Colombo` is the timezone for Sri Lanka (UTC+5:30). This matches your system time.

### Step 5.8: Start All Services

```bash
# Restart and enable all Zabbix services
sudo systemctl restart zabbix-server zabbix-agent apache2
sudo systemctl enable zabbix-server zabbix-agent apache2

# Verify all services are running
sudo systemctl status zabbix-server
sudo systemctl status apache2
sudo systemctl status zabbix-agent
```

All three should show `active (running)`.

### Step 5.9: Complete the Web Setup Wizard

1. Open a web browser **from a PC that can reach `10.10.40.100`**
   - From your host machine: `http://10.10.40.100/zabbix`
   - If using GNS3 with NAT, you may need to access via the GNS3 VM's IP

2. The Zabbix setup wizard appears:
   - **Step 1 — Welcome:** Click "Next step"
   - **Step 2 — Prerequisites:** All should show green ✅. If any fail, install the missing PHP module
   - **Step 3 — Database:** 
     - Database type: `MySQL`
     - Database host: `localhost`
     - Database port: `0` (default)
     - Database name: `zabbix`
     - Database user: `zabbix`
     - Database password: `ZabbixDB123!`
   - **Step 4 — Zabbix server:**
     - Host: `localhost`
     - Port: `10051`
     - Name: `FoE-UoR Zabbix Server`
   - **Step 5 — GUI settings:**
     - Default time zone: `Asia/Colombo`
     - Default theme: `Dark` (looks better for presentations!)
   - **Step 6 — Summary:** Review and click "Next step"
   - **Step 7 — Complete!** Click "Finish"

3. **Login credentials:**
   - Username: `Admin` (capital A!)
   - Password: `zabbix`

> [!CAUTION]
> **Change the default password immediately!** Go to: User icon (top-right) → User settings → Change password.

---

## 6. Host Onboarding — Add All Devices {#6-host-onboarding}

### 6.1: Understanding the Monitoring Architecture

```
VM-ZABBIX (10.10.40.100)
    │
    ├──► R-CORE   (10.0.0.2)     via SNMP community "public"
    ├──► R-EDGE   (10.0.1.1)     via SNMP community "public"
    ├──► SW-Core  (10.99.99.1)   via SNMP community "public"
    ├──► SW-D-DEIE (10.99.99.11) via SNMP community "public"
    ├──► SW-D-DCEE (10.99.99.12) via SNMP community "public"
    ├──► SW-D-DMME (10.99.99.13) via SNMP community "public"
    ├──► SW-A-DEIE (10.99.99.21) via SNMP community "public"
    ├──► SW-A-DCEE (10.99.99.22) via SNMP community "public"
    ├──► SW-A-DMME (10.99.99.23) via SNMP community "public"
    └──► SW-A-DIS  (10.99.99.24) via SNMP community "public"
```

### 6.2: Create Host Groups

Before adding hosts, organize them into logical groups.

1. Go to: **Configuration → Host groups → Create host group**
2. Create these groups:

| Group Name | Purpose |
|-----------|---------|
| `FoE Routers` | R-CORE, R-EDGE |
| `FoE Distribution Switches` | SW-Core, SW-D-DEIE, SW-D-DCEE, SW-D-DMME |
| `FoE Access Switches` | SW-A-DEIE, SW-A-DCEE, SW-A-DMME, SW-A-DIS |

### 6.3: Add Each Host (Step-by-Step for R-CORE — Repeat for All)

1. Go to: **Configuration → Hosts → Create host**

2. **Host tab:**
   - **Host name:** `R-CORE`
   - **Visible name:** `R-CORE (Core Router)`
   - **Groups:** Select `FoE Routers`
   - **Interfaces:** Click **Add** → choose **SNMP**
     - **IP address:** `10.0.0.2`
     - **DNS name:** (leave empty)
     - **Connect to:** `IP`
     - **Port:** `161`
     - **SNMP version:** `SNMPv2`
     - **SNMP community:** `{$SNMP_COMMUNITY}` (we'll set this as a macro)

3. **Templates tab:**
   - Click **Select** → type `Cisco IOS SNMP` in the search
   - Select: **`Template Net Cisco IOS SNMPv2`**
   - This template automatically discovers and monitors:
     - All interfaces (up/down status, traffic, errors)
     - CPU utilization
     - Memory usage
     - ICMP ping availability
     - Device uptime

4. **Macros tab:**
   - Click **Add**
   - **Macro:** `{$SNMP_COMMUNITY}`
   - **Value:** `public`

5. Click **Add** to save the host.

### 6.4: Complete Host List — Add All 10 Devices

Repeat Step 6.3 for every device. Here's the reference table:

| Host Name | Visible Name | Group | SNMP IP | Template |
|-----------|-------------|-------|---------|----------|
| `R-CORE` | R-CORE (Core Router) | FoE Routers | `10.0.0.2` | Template Net Cisco IOS SNMPv2 |
| `R-EDGE` | R-EDGE (Edge Router) | FoE Routers | `10.0.1.1` | Template Net Cisco IOS SNMPv2 |
| `SW-Core` | SW-Core (Core L3 Switch) | FoE Distribution Switches | `10.99.99.1` | Template Net Cisco IOS SNMPv2 |
| `SW-D-DEIE` | SW-D-DEIE (Dist DEIE) | FoE Distribution Switches | `10.99.99.11` | Template Net Cisco IOS SNMPv2 |
| `SW-D-DCEE` | SW-D-DCEE (Dist DCEE) | FoE Distribution Switches | `10.99.99.12` | Template Net Cisco IOS SNMPv2 |
| `SW-D-DMME` | SW-D-DMME (Dist DMME) | FoE Distribution Switches | `10.99.99.13` | Template Net Cisco IOS SNMPv2 |
| `SW-A-DEIE` | SW-A-DEIE (Access DEIE) | FoE Access Switches | `10.99.99.21` | Template Net Cisco IOS SNMPv2 |
| `SW-A-DCEE` | SW-A-DCEE (Access DCEE) | FoE Access Switches | `10.99.99.22` | Template Net Cisco IOS SNMPv2 |
| `SW-A-DMME` | SW-A-DMME (Access DMME) | FoE Access Switches | `10.99.99.23` | Template Net Cisco IOS SNMPv2 |
| `SW-A-DIS` | SW-A-DIS (Access DIS) | FoE Access Switches | `10.99.99.24` | Template Net Cisco IOS SNMPv2 |

> [!TIP]
> **Shortcut: Set the SNMP community globally.** Instead of adding `{$SNMP_COMMUNITY}` = `public` on every host, set it once:
> - Go to: **Administration → General → Macros**
> - Add: `{$SNMP_COMMUNITY}` = `public`
> - Now all hosts inherit this value automatically.

### 6.5: Verify Host Connectivity

After adding all hosts, wait 2–3 minutes for initial discovery, then:

1. Go to: **Monitoring → Hosts**
2. Check the **Availability** column:
   - 🟢 Green `SNMP` icon = device is responding to SNMP polls ✅
   - 🔴 Red `SNMP` icon = device is unreachable ❌ → check ACLs and routing

3. If any host shows red, troubleshoot from VM-ZABBIX:

```bash
# Test SNMP connectivity manually
snmpwalk -v2c -c public 10.99.99.1 sysDescr.0

# Expected output (example):
# SNMPv2-MIB::sysDescr.0 = STRING: Cisco IOS Software, ...
```

If `snmpwalk` isn't installed:
```bash
sudo apt install -y snmp snmp-mibs-downloader
```

---

## 7. Triggers and Alerts Configuration {#7-triggers-and-alerts}

The **Template Net Cisco IOS SNMPv2** already includes many built-in triggers. Here's what's covered and what you need to add:

### 7.1: Device Unreachable (ICMP Ping Timeout > 3 Consecutive Polls)

**Already included in the template!** ✅

The template includes `Template Module ICMP Ping` which has:
- **Trigger:** `Unavailable by ICMP ping`
- **Expression:** `max(/Template Net Cisco IOS SNMPv2/icmpping,#3)=0`
- **Meaning:** If the last 3 ICMP ping checks all returned 0 (fail) → FIRE trigger

**Verify it exists:**
1. Go to: **Configuration → Hosts → R-CORE → Triggers**
2. Look for: `Unavailable by ICMP ping`
3. It should already be there from the template

### 7.2: Interface Down — Alert Within One Polling Cycle

**Already included in the template!** ✅

The template uses SNMP discovery to find all interfaces and creates triggers automatically:
- **Trigger:** `Interface {#IFNAME}: Link down`
- **Expression:** `{TEMPLATE:net.if.status[ifOperStatus.{#SNMPINDEX}].last()}=2`
- **Meaning:** When `ifOperStatus` = 2 (down) → FIRE immediately (one poll cycle)

**Verify:**
1. Go to: **Configuration → Hosts → R-CORE → Discovery rules**
2. Click on `Network interfaces discovery`
3. Click **Trigger prototypes** → you should see the "Link down" trigger prototype

### 7.3: High CPU Utilisation — Trigger When CPU > 80% for 60 Seconds

**Already included in the template!** ✅

The template monitors CPU via `1.3.6.1.4.1.9.2.1.58.0` (Cisco `cpmCPUTotal5min` or `avgBusy5`):
- **Trigger:** `High CPU utilization`
- **Expression uses:** `min(/host/system.cpu.util,5m)>{$CPU.UTIL.CRIT}`
- **Default threshold:** `{$CPU.UTIL.CRIT}` = `90%`

**To match the requirement (80% for 60 seconds), modify the macro:**

1. Go to: **Configuration → Hosts → R-CORE → Macros**
2. Change (or add) **inherited macro:**
   - **Macro:** `{$CPU.UTIL.CRIT}`
   - **Value:** `80`
3. Repeat for all hosts

> [!NOTE]
> If the built-in trigger uses `min(,5m)`, you might need to create a custom trigger for the exact "60 seconds" requirement. To do this:
>
> 1. Go to: **Configuration → Hosts → R-CORE → Triggers → Create trigger**
> 2. Name: `CPU utilization over 80% for 60s`
> 3. Severity: `High`
> 4. Expression: `min(/R-CORE/system.cpu.util[cpmCPUTotal5minRev.1],60s)>80`
>
> This fires when the minimum CPU value over the last 60 seconds is above 80%.

### 7.4: Custom Trigger (Student-Defined) — High Memory Utilisation

This is your custom trigger. **Justification for the report:** Memory exhaustion on network devices can cause process crashes, routing protocol failures, and packet drops before the device becomes completely unreachable. Monitoring memory proactively prevents cascading outages.

**Create the trigger:**

1. Go to: **Configuration → Hosts → R-CORE → Triggers → Create trigger**
2. Configure:
   - **Name:** `High memory utilization (>{$MEMORY.UTIL.MAX}%)`
   - **Severity:** `Warning`
   - **Expression:** `min(/R-CORE/vm.memory.util[snmp],5m)>{$MEMORY.UTIL.MAX}`
   - **Description:** `Memory utilization exceeds threshold. This can cause routing protocol instability, SNMP timeouts, and inability to process new connections. Custom trigger defined for project requirement 5.2.`
3. Add the macro on the host:
   - **Macro:** `{$MEMORY.UTIL.MAX}`
   - **Value:** `90`

Repeat for all devices.

> [!TIP]
> **Alternative custom trigger ideas** (pick one that you can actually demonstrate):
> - **High interface error rate**: `last(/host/net.if.in.errors[ifInErrors.{#SNMPINDEX}])>100` — trigger when input errors exceed 100
> - **Device restarted**: Trigger on `sysUpTime` dropping below a threshold (device rebooted)
> - **OSPF neighbor loss**: Monitor the number of OSPF neighbors and trigger if it drops

---

## 8. Dashboard Creation — "FoE-UoR Network" {#8-dashboard-creation}

### Step 8.1: Create the Dashboard

1. Go to: **Monitoring → Dashboards**
2. Click: **Create dashboard**
3. **Name:** `FoE-UoR Network`
4. Click **Apply**

### Step 8.2: Add Widget — Host Availability Map

This shows all your devices with green/red indicators.

1. Click **Edit dashboard** → **Add widget**
2. Configure:
   - **Type:** `Geomap` or `Host navigator` or `Problems by severity`
   
   For a cleaner **availability map** style:
   - **Type:** `Host availability`
   - **Name:** `Device Availability`
   - **Host groups:** Select `FoE Routers`, `FoE Distribution Switches`, `FoE Access Switches`
   - **Interface type:** `SNMP`

   **Alternatively, use a "Map" widget with a custom network map:**
   1. First create a map: **Monitoring → Maps → Create map**
   2. Name: `FoE Campus Topology`
   3. Add elements for each device, connecting them with links
   4. Then add it as a widget: Type = `Map`, Map = `FoE Campus Topology`

### Step 8.3: Add Widget — Interface Traffic Graphs for Core Devices

1. Click **Add widget**
2. Configure:
   - **Type:** `Graph (classic)` or `Graph prototype`
   - **Name:** `R-CORE Traffic — Fa0/0 (to R-EDGE)`
   - **Resource → Graph:** Select the auto-discovered interface graph for R-CORE's `Fa0/0`

3. Repeat for key interfaces:
   - `R-CORE Fa1/0` (to SW-Core)
   - `R-EDGE Fa0/0` (to R-CORE)
   - `R-EDGE Fa1/0` (to Internet)
   - `SW-Core Gi0/1` (to R-CORE)

> [!NOTE]
> The template auto-discovers interfaces and creates graphs. You just need to reference them in the dashboard widget. If graphs haven't appeared yet, wait 10–15 minutes for the first SNMP discovery cycle to complete.

### Step 8.4: Add Widget — Open Trigger Count

1. Click **Add widget**
2. Configure:
   - **Type:** `Trigger overview` or `Problems`
   - **Name:** `Active Problems`
   - **Host groups:** All three FoE groups
   - **Show:** `Recent problems` or `Problems`
   - **Severity filter:** Show from `Warning` and above

### Step 8.5: Optional — Add More Widgets

To make the dashboard impressive for your project:

| Widget Type | Content | Purpose |
|------------|---------|---------|
| `System information` | Zabbix server stats | Shows server health |
| `Clock` | Current time | Visual flair |
| `Data overview` | CPU utilization for all hosts | At-a-glance CPU across network |
| `Graph` | R-EDGE NAT translations | Shows internet usage |
| `Top hosts` | Top 5 by CPU/memory/traffic | Identifies bottlenecks |

### Step 8.6: Save the Dashboard

1. Click **Save changes** in the top-right corner

---

## 9. Export Dashboard JSON {#9-export-dashboard}

### Step 9.1: Export the Dashboard

1. Go to: **Monitoring → Dashboards**
2. Select your `FoE-UoR Network` dashboard
3. Click the **⋮** (three dots) or the **Share** button
4. Select **Export**

**Alternative (more reliable) method via Configuration:**

1. Go to: **Configuration → Templates** (dashboards can be exported from here if they're on a template)

**OR** use the Zabbix API:

```bash
# Run this on VM-ZABBIX
curl -s -X POST http://localhost/zabbix/api_jsonrpc.php \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "dashboard.get",
    "params": {
      "output": "extend",
      "selectWidgets": "extend",
      "filter": { "name": "FoE-UoR Network" }
    },
    "auth": "YOUR_AUTH_TOKEN",
    "id": 1
  }' | python3 -m json.tool > foe_uor_dashboard.json
```

To get the auth token:
```bash
curl -s -X POST http://localhost/zabbix/api_jsonrpc.php \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "user.login",
    "params": { "username": "Admin", "password": "YOUR_PASSWORD" },
    "id": 1
  }'
```

### Step 9.2: Save the Exported JSON

Copy the exported JSON file to your project directory for submission. Name it `FoE-UoR_Network_Dashboard.json`.

---

## 10. Verification Checklist {#10-verification}

Use this checklist to ensure everything is working before submission:

### Connectivity
- [ ] VM-ZABBIX can ping all 10 managed devices
- [ ] `snmpwalk -v2c -c public <device_ip> sysDescr.0` returns Cisco IOS info for all devices
- [ ] Zabbix web UI accessible at `http://10.10.40.100/zabbix`

### Host Onboarding (Section 5.1)
- [ ] All 10 devices added as hosts in Zabbix
- [ ] All hosts show green SNMP availability icon
- [ ] All hosts use `Template Net Cisco IOS SNMPv2`
- [ ] Host groups created: Routers, Distribution Switches, Access Switches

### Triggers (Section 5.2)
- [ ] **Device unreachable:** Shut down a device in GNS3 → trigger fires within 3 polls (~3 minutes)
- [ ] **Interface down:** `shutdown` an interface on a device → trigger fires within 1 poll cycle (~1 minute)
- [ ] **High CPU:** Macro `{$CPU.UTIL.CRIT}` set to `80` on all hosts
- [ ] **Custom trigger:** High memory utilization trigger created and documented

### Dashboard (Section 5.3)
- [ ] Dashboard named `FoE-UoR Network` exists
- [ ] Contains host availability map
- [ ] Contains interface traffic graphs for core devices
- [ ] Contains open trigger count widget
- [ ] Dashboard exported as JSON file

### Demonstration Tips

To **demonstrate triggers firing** during your project presentation:

1. **Device unreachable:** In GNS3, right-click a device → **Stop**. Wait ~3 minutes → the dashboard shows a red problem.

2. **Interface down:** On any router:
   ```
   R-CORE# configure terminal
   R-CORE(config)# interface FastEthernet0/0
   R-CORE(config-if)# shutdown
   ```
   Wait ~1 minute → Zabbix shows "Interface Fa0/0: Link down" trigger.
   Then bring it back up: `no shutdown`

3. **Take a screenshot** of each triggered alarm for your report.

---

## Quick Reference — All IP Addresses

| Device | Management IP | SNMP Community | VLAN |
|--------|--------------|----------------|------|
| R-CORE | 10.0.0.2 | public | Router link |
| R-EDGE | 10.0.1.1 | public | Router link |
| SW-Core | 10.99.99.1 | public | VLAN 99 |
| SW-D-DEIE | 10.99.99.11 | public | VLAN 99 |
| SW-D-DCEE | 10.99.99.12 | public | VLAN 99 |
| SW-D-DMME | 10.99.99.13 | public | VLAN 99 |
| SW-A-DEIE | 10.99.99.21 | public | VLAN 99 |
| SW-A-DCEE | 10.99.99.22 | public | VLAN 99 |
| SW-A-DMME | 10.99.99.23 | public | VLAN 99 |
| SW-A-DIS | 10.99.99.24 | public | VLAN 99 |
| VM-ZABBIX | 10.10.40.100 | — | VLAN 40 |
