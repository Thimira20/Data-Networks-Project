# Netmiko Router Automation — EE8203 Project

## EE8203/EC8205 — Section 4.1: Netmiko Python Automation

> Automates router configuration (R-CORE, R-EDGE) and SNMP deployment
> across all network devices using Python + Netmiko.

---

## What Gets Configured

### Script 01 — Router Configuration (`01_configure_routers.py`)

| Device | Configuration Applied |
|---|---|
| **R-CORE** | Interface IPs (Gi0/0, Gi0/1), OSPF Area 0, ACL-INFRASTRUCTURE-PROTECT |
| **R-EDGE** | Interface IPs (Gi0/0, Gi0/1 DHCP), OSPF Area 0, NAT overload (PAT), ACL-WAN-INBOUND |

### Script 02 — SNMP Push (`02_configure_snmp_all.py`)

Pushes to ALL 10 devices (2 routers + 4 L3 switches + 4 L2 switches):
- `snmp-server community public RO`
- `snmp-server community private RW`
- `snmp-server host 10.10.40.100 version 2c public`
- `snmp-server enable traps`

### Script 03 — Verification (`03_verify_config.py`)

Runs `show` commands on all devices and logs output for review.

---

## File Structure

```
netmiko-automation/
├── inventory.yaml              ← Device inventory (ALL parameters)
├── 01_configure_routers.py     ← R-CORE + R-EDGE configuration
├── 02_configure_snmp_all.py    ← SNMP push to ALL 10 devices
├── 03_verify_config.py         ← Verification (show commands)
├── README.md                   ← This guide
└── logs/                       ← Auto-created log files
    ├── router_config_YYYY-MM-DD_HH-MM-SS.log
    ├── snmp_config_YYYY-MM-DD_HH-MM-SS.log
    └── verification_YYYY-MM-DD_HH-MM-SS.log
```

---

## Running the Scripts

```bash
cd /root/automation/netmiko-automation

# Step 1: Configure routers (interfaces, OSPF, NAT, ACLs)
python3 01_configure_routers.py

# Step 2: Push SNMP to all devices
python3 02_configure_snmp_all.py

# Step 3: Verify all configuration
python3 03_verify_config.py
```

---

## Key Features

- **Idempotent**: Re-running scripts does NOT create duplicate config
- **Error handling**: Per-device try/except — one failure doesn't stop others
- **Timestamped logs**: Every run creates a new log file in `logs/`
- **YAML inventory**: All parameters externalized — no hardcoded values

---

## Required Python Libraries

| Library | Install Command | Purpose |
|---|---|---|
| `netmiko` | `pip3 install netmiko` | SSH automation for Cisco IOS |
| `pyyaml` | `pip3 install pyyaml` | Parse YAML inventory file |
| Python 3.8+ | Pre-installed on Ubuntu | Script runtime |
