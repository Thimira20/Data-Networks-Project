#!/usr/bin/env python3
"""
01_configure_routers.py — Netmiko Router Configuration Script
==============================================================
EE8203/EC8205 Design & Management of Data Networks
University of Ruhuna — 8th Semester Project

Purpose:
    Automates the full configuration of R-CORE and R-EDGE routers
    via SSH, including:
      - Interface IP addressing (Static and DHCP)
      - OSPF dynamic routing
      - NAT overload (PAT) rules on R-EDGE
      - ACL deployment on both routers

Requirements Satisfied:
    ✓ Device parameters loaded from inventory.yaml (not hardcoded)
    ✓ Connects via SSH on the management plane
    ✓ Automates interfaces, OSPF, NAT, ACLs
    ✓ Structured error handling (try/except)
    ✓ Timestamped log file output
    ✓ Idempotency — re-running does not create duplicate config
    ✓ Well-commented and readable code

Usage:
    python3 01_configure_routers.py

Author: [Your Name / Group]
Date:   2026-07-31
"""

# ============================================================
# IMPORTS
# ============================================================
import yaml          # For reading the YAML inventory file
import os            # For file path operations
import sys           # For sys.exit on fatal errors
import time          # For sleep delays during DHCP configuration
from datetime import datetime  # For timestamped logging

# Netmiko — the core SSH automation library for network devices
from netmiko import (
    ConnectHandler,                    # Creates SSH sessions to devices
    NetmikoTimeoutException,           # Raised when device is unreachable
    NetmikoAuthenticationException,    # Raised when credentials are wrong
)

# ============================================================
# GLOBAL CONSTANTS
# ============================================================
# All paths are relative to this script's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(SCRIPT_DIR, "inventory.yaml")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")


# ============================================================
# ROUTER-SPECIFIC ACL DEFINITIONS
# ============================================================
# These ACLs are deployed ON THE ROUTERS (not switches).
# Switch ACLs (ACL-DEIE-IN, ACL-DCEE-IN, etc.) are already
# applied on L3 switch SVIs and are handled separately.

ROUTER_ACLS = {
    "R-CORE": {
        # Infrastructure protection ACL — filters traffic entering R-CORE
        "acl_name": "ACL-INFRASTRUCTURE-PROTECT",
        "acl_commands": [
            "ip access-list extended ACL-INFRASTRUCTURE-PROTECT",
            " remark --- Allow OSPF routing protocol ---",
            " permit ospf any any",
            " remark --- Allow SSH management from MGMT VLAN ---",
            " permit tcp 10.99.99.0 0.0.0.255 any eq 22",
            " remark --- Allow SNMP polling from NMS server ---",
            " permit udp host 10.10.40.100 any eq 161",
            " remark --- Allow ICMP for troubleshooting ---",
            " permit icmp any any",
            " remark --- Allow all campus traffic (10.x.x.x) ---",
            " permit ip 10.0.0.0 0.255.255.255 any",
            " remark --- Deny and log everything else ---",
            " deny ip any any log",
            "exit",
        ],
    },
    "R-EDGE": {
        # WAN anti-spoofing ACL — blocks RFC1918 private IPs from internet
        "acl_name": "ACL-WAN-INBOUND",
        "acl_commands": [
            "ip access-list extended ACL-WAN-INBOUND",
            " remark --- Anti-spoofing: block private IPs from WAN ---",
            " deny ip 10.0.0.0 0.255.255.255 any",
            " deny ip 172.16.0.0 0.15.255.255 any",
            " deny ip 192.168.0.0 0.0.255.255 any",
            " remark --- Block loopback spoofing ---",
            " deny ip 127.0.0.0 0.255.255.255 any",
            " remark --- Allow all legitimate inbound traffic ---",
            " permit ip any any",
            "exit",
        ],
        # Apply ACL to the WAN-facing interface (FastEthernet1/0)
        "apply_interface": "FastEthernet1/0",
        "apply_direction": "in",
    },
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def setup_logging():
    """
    Create the logs directory (if it doesn't exist) and return
    a timestamped log file path.
    
    Returns:
        tuple: (log_file_path, timestamp_string)
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(LOG_DIR, f"router_config_{timestamp}.log")
    return log_file, timestamp


def log(log_file, message, also_print=True):
    """
    Write a timestamped message to both the log file and console.
    
    Args:
        log_file:   Path to the log file
        message:    The message string to log
        also_print: If True, also print to console (default: True)
    """
    timestamped = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(timestamped + "\n")
    if also_print:
        print(timestamped)


def load_inventory(inventory_path):
    """
    Load and parse the YAML inventory file.
    
    Args:
        inventory_path: Absolute path to inventory.yaml
        
    Returns:
        dict: Parsed inventory data
        
    Raises:
        FileNotFoundError: If inventory file doesn't exist
        yaml.YAMLError:    If YAML syntax is invalid
    """
    with open(inventory_path, "r", encoding="utf-8") as f:
        inventory = yaml.safe_load(f)
    return inventory


def build_connection_params(device, credentials):
    """
    Build Netmiko connection parameters dictionary from inventory data.
    
    This function merges device-specific info (IP, type) with shared
    credentials (username, password) into the format Netmiko expects.
    
    Args:
        device:      Device dict from inventory (hostname, host, device_type)
        credentials: Shared credentials dict (username, password, secret)
        
    Returns:
        dict: Ready-to-use Netmiko connection parameters
    """
    return {
        "device_type": device["device_type"],
        "host":        device["host"],
        "username":    credentials["username"],
        "password":    credentials["password"],
        "secret":      credentials.get("secret", credentials["password"]),
        "timeout":     30,        # Seconds to wait for TCP connection
        "session_timeout": 120,   # Increased: DHCP interfaces may delay prompts
        "banner_timeout":  30,    # Seconds to wait for SSH banner
    }


def check_config_exists(connection, check_string):
    """
    Check if a specific config string exists in the running configuration.
    This is the core IDEMPOTENCY mechanism — if the config already exists,
    we skip pushing it to avoid duplicates.
    
    Args:
        connection:   Active Netmiko connection object
        check_string: String to search for in 'show running-config'
        
    Returns:
        bool: True if config already exists, False if it needs to be pushed
    """
    # Use IOS pipe filter to search running-config efficiently
    output = connection.send_command(
        f"show running-config | include {check_string}"
    )
    return bool(output.strip())


# ============================================================
# CONFIGURATION BUILDER FUNCTIONS
# ============================================================

def build_interface_commands(interface_config):
    """
    Build IOS interface configuration commands from inventory data.
    
    Args:
        interface_config: Dict with keys: name, description, ip_address,
                         subnet_mask, and optionally nat_direction
    
    Returns:
        list: List of IOS commands to configure the interface.
    """
    name = interface_config["name"]
    is_dhcp = interface_config["ip_address"] == "dhcp"

    if is_dhcp:
        # ── DHCP interface ────────────────────────────────────────────────
        # Bring interface up first, then request DHCP address.
        commands = [
            f"interface {name}",
            f" description {interface_config['description']}",
            " no shutdown",
            " ip address dhcp",
        ]
        nat_dir = interface_config.get("nat_direction")
        if nat_dir:
            commands.append(f" ip nat {nat_dir}")
            
        # Appending 'exit' returns to (config)# mode and flushes the prompt
        commands.append("exit")
        return commands
    else:
        # ── Static IP interface ───────────────────────────────────────────
        commands = [
            f"interface {name}",
            f" description {interface_config['description']}",
            f" ip address {interface_config['ip_address']} {interface_config['subnet_mask']}",
        ]
        nat_dir = interface_config.get("nat_direction")
        if nat_dir:
            commands.append(f" ip nat {nat_dir}")
        commands.append(" no shutdown")
        commands.append("exit")
        return commands


def build_ospf_commands(ospf_config):
    """
    Build OSPF configuration commands from inventory data.
    """
    pid = ospf_config["process_id"]
    commands = [f"router ospf {pid}"]
    
    if "router_id" in ospf_config:
        commands.append(f" router-id {ospf_config['router_id']}")
    
    for net in ospf_config["networks"]:
        commands.append(
            f" network {net['network']} {net['wildcard']} area {net['area']}"
        )
    
    if ospf_config.get("default_originate"):
        commands.append(" default-information originate")
    
    commands.append("exit")
    return commands


def build_nat_commands(nat_config):
    """
    Build NAT overload (PAT) configuration commands from inventory data.
    Only applicable to R-EDGE.
    """
    commands = []
    
    if "acl_number" in nat_config:
        acl_id = str(nat_config["acl_number"])
        for net_entry in nat_config["permitted_networks"]:
            commands.append(
                f"access-list {acl_id} permit ip "
                f"{net_entry['network']} {net_entry['wildcard']} any"
            )
    else:
        acl_id = nat_config["acl_name"]
        commands.append(f"ip access-list standard {acl_id}")
        commands.append(" remark --- NAT: Only permitted departments get internet ---")
        for net_entry in nat_config["permitted_networks"]:
            commands.append(f" permit {net_entry['network']} {net_entry['wildcard']}")
        commands.append("exit")
    
    outside_if = nat_config["outside_interface"]
    commands.append(
        f"ip nat inside source list {acl_id} "
        f"interface {outside_if} overload"
    )
    return commands


def build_static_route_commands(static_routes):
    """
    Build static route configuration commands from inventory data.
    """
    commands = []
    for route in static_routes:
        commands.append(
            f"ip route {route['destination']} {route['mask']} {route['next_hop']}"
        )
    return commands


# ============================================================
# MAIN CONFIGURATION FUNCTION
# ============================================================

def configure_router(device, credentials, log_file):
    """
    Connect to a single router and apply all configuration sections.
    Implements idempotency by checking existing config before each push.
    """
    hostname = device["hostname"]
    host = device["host"]
    changes_made = 0
    sections_skipped = 0

    log(log_file, f"Connecting to {hostname} ({host})...")

    try:
        # ── Step 1: Establish SSH connection ──────────────────
        conn_params = build_connection_params(device, credentials)
        connection = ConnectHandler(**conn_params)
        
        connection.enable()
        # Suppress console logging to prevent async syslog messages from corrupting prompt matching
        connection.send_command("no logging console")
        log(log_file, f"  ✓ SSH connection established to {hostname}")

        # ── Step 2: Configure Interfaces ──────────────────────
        for iface in device.get("interfaces", []):
            iface_name = iface["name"]
            is_dhcp = iface["ip_address"] == "dhcp"
            check_str = "ip address dhcp" if is_dhcp else iface["ip_address"]

            if check_config_exists(connection, check_str):
                log(log_file, f"  → {iface_name} already configured — SKIPPING (idempotent)")
                sections_skipped += 1
            else:
                log(log_file, f"  → Configuring {iface_name}...")

                if is_dhcp:
                    log(log_file, f"    [DHCP] Sending interface commands via timing channel...")
                    # Enter configuration mode explicitly
                    connection.config_mode()
                    
                    # Send interface setup commands
                    connection.send_command_timing(f"interface {iface_name}")
                    connection.send_command_timing(f"description {iface['description']}")
                    connection.send_command_timing("no shutdown")
                    
                    if iface.get("nat_direction"):
                        connection.send_command_timing(f"ip nat {iface['nat_direction']}")
                    
                    # Send DHCP command — delay_factor=10 gives ~20s for DHCP discovery
                    log(log_file, f"    [DHCP] Requesting IP address (non-blocking timing)...")
                    connection.send_command_timing("ip address dhcp", delay_factor=10)
                    
                    # Allow time for async DHCP syslog messages to flush
                    time.sleep(3)
                    connection.clear_buffer()
                    
                    # Exit interface and config mode cleanly
                    connection.send_command_timing("exit")
                    connection.exit_config_mode()
                else:
                    commands = build_interface_commands(iface)
                    output = connection.send_config_set(commands)
                    log(log_file, f"    Device output:\n{output}", also_print=False)

                log(log_file, f"  ✓ {iface_name} configured successfully")
                changes_made += 1

        # ── Step 3: Configure OSPF ────────────────────────────
        ospf_config = device.get("ospf")
        if ospf_config:
            check_str = f"router ospf {ospf_config['process_id']}"
            if check_config_exists(connection, check_str):
                log(log_file, f"  → OSPF process {ospf_config['process_id']} already configured — SKIPPING (idempotent)")
                sections_skipped += 1
            else:
                log(log_file, f"  → Configuring OSPF process {ospf_config['process_id']}...")
                commands = build_ospf_commands(ospf_config)
                output = connection.send_config_set(commands)
                log(log_file, f"    Device output:\n{output}", also_print=False)
                log(log_file, f"  ✓ OSPF configured successfully")
                changes_made += 1

        # ── Step 4: Configure NAT (R-EDGE only) ──────────────
        nat_config = device.get("nat")
        if nat_config:
            check_str = str(nat_config.get("acl_number", nat_config.get("acl_name", "")))
            if check_config_exists(connection, f"ip nat inside source list {check_str}"):
                log(log_file, f"  → NAT (ACL {check_str}) already configured — SKIPPING (idempotent)")
                sections_skipped += 1
            else:
                log(log_file, f"  → Configuring NAT overload (PAT)...")
                commands = build_nat_commands(nat_config)
                output = connection.send_config_set(commands)
                log(log_file, f"    Device output:\n{output}", also_print=False)
                log(log_file, f"  ✓ NAT configured successfully")
                changes_made += 1

        # ── Step 4b: Configure Static Routes ──────────────────
        static_routes = device.get("static_routes")
        if static_routes:
            first_route = static_routes[0]
            check_str = f"ip route {first_route['destination']}"
            if check_config_exists(connection, check_str):
                log(log_file, f"  → Static routes already configured — SKIPPING (idempotent)")
                sections_skipped += 1
            else:
                log(log_file, f"  → Configuring static routes...")
                commands = build_static_route_commands(static_routes)
                output = connection.send_config_set(commands)
                log(log_file, f"    Device output:\n{output}", also_print=False)
                log(log_file, f"  ✓ Static routes configured successfully")
                changes_made += 1

        # ── Step 5: Deploy Router ACLs ────────────────────────
        acl_info = ROUTER_ACLS.get(hostname)
        if acl_info:
            acl_name = acl_info["acl_name"]
            if check_config_exists(connection, acl_name):
                log(log_file, f"  → ACL '{acl_name}' already exists — SKIPPING (idempotent)")
                sections_skipped += 1
            else:
                log(log_file, f"  → Deploying ACL '{acl_name}'...")
                output = connection.send_config_set(acl_info["acl_commands"])
                log(log_file, f"    Device output:\n{output}", also_print=False)
                
                if "apply_interface" in acl_info:
                    apply_cmds = [
                        f"interface {acl_info['apply_interface']}",
                        f" ip access-group {acl_name} {acl_info['apply_direction']}",
                        "exit",
                    ]
                    output = connection.send_config_set(apply_cmds)
                    log(log_file, f"  ✓ ACL applied to {acl_info['apply_interface']} ({acl_info['apply_direction']})")
                
                log(log_file, f"  ✓ ACL '{acl_name}' deployed successfully")
                changes_made += 1

        # ── Step 6: Save configuration to NVRAM ──────────────
        log(log_file, f"  → Saving configuration (write memory)...")
        save_output = connection.send_command(
            "write memory",
            expect_string=r"\[OK\]|#",
            read_timeout=30
        )
        log(log_file, f"  ✓ Configuration saved to NVRAM")

        # ── Step 7: Disconnect cleanly ────────────────────────
        connection.disconnect()
        log(log_file, 
            f"  ✓ {hostname} complete — "
            f"{changes_made} changes applied, "
            f"{sections_skipped} sections skipped (idempotent)"
        )
        return True, changes_made

    # ── Error Handling ────────────────────────────────────────
    except NetmikoTimeoutException:
        log(log_file, f"  ✗ FAILED: Connection to {hostname} ({host}) timed out!")
        log(log_file, f"    Troubleshoot:")
        log(log_file, f"      1. Is the device powered on in GNS3?")
        log(log_file, f"      2. Can you ping {host} from this machine?")
        log(log_file, f"      3. Is SSH enabled on the device?")
        return False, 0

    except NetmikoAuthenticationException:
        log(log_file, f"  ✗ FAILED: Authentication failed for {hostname} ({host})")
        log(log_file, f"    Troubleshoot:")
        log(log_file, f"      1. Check username/password in inventory.yaml")
        log(log_file, f"      2. Verify: 'username admin privilege 15 secret admin123'")
        return False, 0

    except Exception as e:
        log(log_file, 
            f"  ✗ FAILED: Unexpected error on {hostname}: "
            f"{type(e).__name__}: {e}"
        )
        return False, 0


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    log_file, timestamp = setup_logging()
    
    banner = (
        f"\n{'=' * 60}\n"
        f"  NETMIKO ROUTER CONFIGURATION SCRIPT\n"
        f"  EE8203 — Network Automation with Python (Netmiko)\n"
        f"  Timestamp: {timestamp}\n"
        f"{'=' * 60}"
    )
    log(log_file, banner)

    try:
        inventory = load_inventory(INVENTORY_FILE)
        log(log_file, f"\n✓ Inventory loaded: {INVENTORY_FILE}")
    except FileNotFoundError:
        log(log_file, f"\n✗ ERROR: Inventory file not found: {INVENTORY_FILE}")
        log(log_file, f"  Make sure inventory.yaml is in the same folder as this script.")
        sys.exit(1)
    except yaml.YAMLError as e:
        log(log_file, f"\n✗ ERROR: Invalid YAML syntax in inventory: {e}")
        sys.exit(1)

    credentials = inventory["credentials"]
    routers = inventory["routers"]
    total_devices = len(routers)
    success_count = 0
    total_changes = 0

    log(log_file, f"  Found {total_devices} routers to configure\n")

    for idx, device in enumerate(routers, start=1):
        log(log_file, f"\n[{idx}/{total_devices}] {'─' * 50}")
        
        success, changes = configure_router(device, credentials, log_file)
        
        if success:
            success_count += 1
            total_changes += changes

    summary = (
        f"\n{'=' * 60}\n"
        f"  SUMMARY\n"
        f"  ─────────────────────────────────────\n"
        f"  Devices attempted:  {total_devices}\n"
        f"  Devices successful: {success_count}\n"
        f"  Devices failed:     {total_devices - success_count}\n"
        f"  Total changes:      {total_changes}\n"
        f"  Log file:           {log_file}\n"
        f"{'=' * 60}"
    )
    log(log_file, summary)

    if success_count < total_devices:
        sys.exit(1)


if __name__ == "__main__":
    main()