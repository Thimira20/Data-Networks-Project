#!/usr/bin/env python3
"""
02_configure_snmp_all.py — SNMP Configuration Push to ALL Devices
=================================================================
EE8203/EC8205 Design & Management of Data Networks
University of Ruhuna — 8th Semester Project

Purpose:
    Pushes SNMPv2c community strings and trap destination configuration
    to ALL network devices (routers + L3 switches + L2 switches).
    This enables Zabbix/NMS monitoring across the entire campus network.

SNMP Configuration Applied:
    - snmp-server community public RO     (read-only for monitoring)
    - snmp-server community private RW    (read-write for management)
    - snmp-server host 10.10.40.100 version 2c public  (trap destination)
    - snmp-server enable traps            (enable trap notifications)

Requirements Satisfied:
    ✓ Device inventory from YAML file (no hardcoded parameters)
    ✓ SSH connection via VLAN 99 management plane
    ✓ SNMPv2c community + trap config on ALL devices
    ✓ Structured error handling — continues on failure
    ✓ Timestamped log file
    ✓ Idempotency — checks before pushing

Usage:
    python3 02_configure_snmp_all.py

Author: [Your Name / Group]
Date:   2026-07-31
"""

# ============================================================
# IMPORTS
# ============================================================
import yaml
import os
import sys
from datetime import datetime
from netmiko import (
    ConnectHandler,
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)

# ============================================================
# GLOBAL CONSTANTS
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(SCRIPT_DIR, "inventory.yaml")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def setup_logging():
    """Create log directory and return timestamped log file path."""
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(LOG_DIR, f"snmp_config_{timestamp}.log")
    return log_file, timestamp


def log(log_file, message, also_print=True):
    """Write timestamped message to log file and optionally to console."""
    timestamped = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(timestamped + "\n")
    if also_print:
        print(timestamped)


def load_inventory(inventory_path):
    """Load and parse the YAML inventory file."""
    with open(inventory_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_connection_params(device, credentials):
    """Build Netmiko connection parameters from inventory data."""
    return {
        "device_type": device["device_type"],
        "host":        device["host"],
        "username":    credentials["username"],
        "password":    credentials["password"],
        "secret":      credentials.get("secret", credentials["password"]),
        "timeout":     30,
        "session_timeout": 60,
        "banner_timeout":  30,
    }


def get_all_devices(inventory):
    """
    Collect ALL devices from all inventory groups into a single flat list.
    This is used because SNMP must be pushed to EVERY device.
    
    Args:
        inventory: Parsed inventory dict from YAML
        
    Returns:
        list: All device dicts from routers + l3_switches + l2_switches
    """
    all_devices = []
    
    # Add routers
    for device in inventory.get("routers", []):
        all_devices.append(device)
    
    # Add L3 switches
    for device in inventory.get("l3_switches", []):
        all_devices.append(device)
    
    # Add L2 switches
    for device in inventory.get("l2_switches", []):
        all_devices.append(device)
    
    return all_devices


def build_snmp_commands(snmp_config, device=None):
    """
    Build SNMP configuration commands from inventory settings.
    Optionally includes device-specific monitoring adjustments (L2 default route & router duplex mode).
    
    Args:
        snmp_config: Dict with keys: community_ro, community_rw,
                     trap_destination, snmp_version
        device:      Optional device dict from inventory
    
    Returns:
        list: IOS CLI commands for SNMP and monitoring optimization
    """
    community_ro = snmp_config["community_ro"]
    community_rw = snmp_config["community_rw"]
    trap_dest = snmp_config["trap_destination"]
    version = snmp_config["snmp_version"]
    
    commands = [
        # Read-only community string — used by NMS for polling
        f"snmp-server community {community_ro} RO",
        # Read-write community string — used for SNMP set operations
        f"snmp-server community {community_rw} RW",
        # Trap destination — where SNMP traps/notifications are sent
        f"snmp-server host {trap_dest} version {version} {community_ro}",
        # Enable all standard SNMP traps
        "snmp-server enable traps",
    ]

    # Device-specific monitoring & gateway enhancements
    if device:
        hostname = device.get("hostname", "")
        # For L2 switches: ensure static default route exists for cross-VLAN Zabbix reachability
        if hostname.startswith("SW-A-"):
            commands.append("ip default-gateway 10.99.99.1")
            commands.append("ip route 0.0.0.0 0.0.0.0 10.99.99.1")

    return commands


# ============================================================
# SNMP CONFIGURATION FUNCTION
# ============================================================

def configure_snmp_on_device(device, credentials, snmp_commands, log_file):
    """
    Connect to a single device and push SNMP configuration.
    
    Idempotency: Checks if SNMP community strings already exist.
    If they do, the device is skipped to avoid duplicate config.
    
    Error handling: If a device fails, the function returns False
    but does NOT abort the entire script — the next device is attempted.
    
    Args:
        device:        Device dict from inventory
        credentials:   Shared credentials dict
        snmp_commands: List of SNMP IOS CLI commands
        log_file:      Path to log file
        
    Returns:
        tuple: (success: bool, was_changed: bool)
    """
    hostname = device["hostname"]
    host = device["host"]

    try:
        # ── Connect via SSH ───────────────────────────────────
        conn_params = build_connection_params(device, credentials)
        connection = ConnectHandler(**conn_params)
        connection.enable()

        # ── Idempotency Check ─────────────────────────────────
        # Check if SNMP community is already configured
        existing_snmp = connection.send_command(
            "show running-config | include snmp-server community"
        )
        
        if "community" in existing_snmp.lower():
            # SNMP already configured — skip to avoid duplicates
            log(log_file, 
                f"  [{hostname:.<20s}] ({host:>15s}) "
                f"✓ SNMP already present — SKIPPED (idempotent)")
            connection.disconnect()
            return True, False  # Success, but no changes made

        # ── Push SNMP Configuration ───────────────────────────
        output = connection.send_config_set(snmp_commands)
        log(log_file, f"    Device output:\n{output}", also_print=False)

        # ── Save to NVRAM ─────────────────────────────────────
        connection.send_command(
            "write memory",
            expect_string=r"\[OK\]|#",
            read_timeout=30
        )

        # ── Disconnect ────────────────────────────────────────
        connection.disconnect()
        log(log_file, 
            f"  [{hostname:.<20s}] ({host:>15s}) "
            f"✓ SNMP configured successfully")
        return True, True  # Success, changes were made

    # ── Error Handling ────────────────────────────────────────
    # These exceptions do NOT stop the script — it continues
    # to the next device. This is important when managing many
    # devices: one failure shouldn't block the rest.
    
    except NetmikoTimeoutException:
        log(log_file, 
            f"  [{hostname:.<20s}] ({host:>15s}) "
            f"✗ FAILED — Connection timed out")
        return False, False

    except NetmikoAuthenticationException:
        log(log_file, 
            f"  [{hostname:.<20s}] ({host:>15s}) "
            f"✗ FAILED — Authentication error")
        return False, False

    except Exception as e:
        log(log_file, 
            f"  [{hostname:.<20s}] ({host:>15s}) "
            f"✗ FAILED — {type(e).__name__}: {e}")
        return False, False


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """
    Main function — pushes SNMP config to every device in the inventory.
    
    Workflow:
      1. Load inventory and SNMP settings from YAML
      2. Build SNMP command list
      3. Iterate over ALL devices (routers + switches)
      4. Push config with idempotency check
      5. Report summary
    """
    # ── Setup ─────────────────────────────────────────────────
    log_file, timestamp = setup_logging()
    
    banner = (
        f"\n{'=' * 60}\n"
        f"  NETMIKO SNMP CONFIGURATION SCRIPT\n"
        f"  EE8203 — Push SNMPv2c to ALL Network Devices\n"
        f"  Timestamp: {timestamp}\n"
        f"{'=' * 60}"
    )
    log(log_file, banner)

    # ── Load Inventory ────────────────────────────────────────
    try:
        inventory = load_inventory(INVENTORY_FILE)
        log(log_file, f"\n✓ Inventory loaded: {INVENTORY_FILE}")
    except FileNotFoundError:
        log(log_file, f"\n✗ ERROR: Inventory file not found: {INVENTORY_FILE}")
        sys.exit(1)
    except yaml.YAMLError as e:
        log(log_file, f"\n✗ ERROR: Invalid YAML: {e}")
        sys.exit(1)

    # ── Prepare ───────────────────────────────────────────────
    credentials = inventory["credentials"]
    snmp_config = inventory["snmp"]
    all_devices = get_all_devices(inventory)
    total = len(all_devices)
    
    # ── Configure Each Device ─────────────────────────────────
    for idx, device in enumerate(all_devices, start=1):
        log(log_file, f"  [{idx:02d}/{total}] ", also_print=False)
        
        # Build device-specific SNMP commands
        snmp_cmds = build_snmp_commands(snmp_config, device)

        success, was_changed = configure_snmp_on_device(
            device, credentials, snmp_cmds, log_file
        )
        
        if success:
            success_count += 1
            if was_changed:
                changed_count += 1
            else:
                skipped_count += 1
        else:
            failed_count += 1

    # ── Summary ───────────────────────────────────────────────
    summary = (
        f"\n{'=' * 60}\n"
        f"  SUMMARY\n"
        f"  ─────────────────────────────────────\n"
        f"  Total devices:      {total}\n"
        f"  Successful:         {success_count}\n"
        f"    ├─ Changed:       {changed_count}\n"
        f"    └─ Skipped:       {skipped_count} (already configured)\n"
        f"  Failed:             {failed_count}\n"
        f"  Log file:           {log_file}\n"
        f"{'=' * 60}"
    )
    log(log_file, summary)

    if failed_count > 0:
        log(log_file, 
            f"\n  ⚠ {failed_count} device(s) failed. Check the log for details."
        )
        sys.exit(1)


# ── Run the script ────────────────────────────────────────────
if __name__ == "__main__":
    main()
