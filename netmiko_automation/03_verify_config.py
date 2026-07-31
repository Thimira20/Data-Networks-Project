#!/usr/bin/env python3
"""
03_verify_config.py — Post-Configuration Verification Script
=============================================================
EE8203/EC8205 Design & Management of Data Networks
University of Ruhuna — 8th Semester Project

Purpose:
    Connects to all network devices and runs verification commands
    to confirm that the automated configuration was applied correctly.
    Outputs are formatted for both console review and log file.

What It Verifies:
    On Routers (R-CORE, R-EDGE):
      - Interface IP addressing (show ip interface brief)
      - OSPF neighbor adjacencies (show ip ospf neighbor)
      - OSPF learned routes (show ip route ospf)
      - NAT translations (show ip nat translations) — R-EDGE only
      - Access lists (show access-lists)
      - SNMP configuration (show snmp)
    
    On All Switches:
      - SNMP community strings (show snmp community)

Usage:
    python3 03_verify_config.py

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

# ── Verification commands per device role ─────────────────────
# Each role has a list of show commands to execute.
VERIFICATION_COMMANDS = {
    "core_router": [
        ("show ip interface brief",  "Interface Status"),
        ("show ip ospf neighbor",    "OSPF Adjacencies"),
        ("show ip route ospf",       "OSPF Learned Routes"),
        ("show access-lists",        "Access Control Lists"),
        ("show snmp",                "SNMP Status"),
    ],
    "edge_router": [
        ("show ip interface brief",     "Interface Status"),
        ("show ip ospf neighbor",       "OSPF Adjacencies"),
        ("show ip route ospf",          "OSPF Learned Routes"),
        ("show ip nat translations",    "NAT Translation Table"),
        ("show ip nat statistics",      "NAT Statistics"),
        ("show access-lists",           "Access Control Lists"),
        ("show snmp",                   "SNMP Status"),
    ],
    "l3_switch": [
        ("show snmp",                   "SNMP Status"),
        ("show snmp community",         "SNMP Communities"),
        ("show ip interface brief",     "Interface Status"),
    ],
    "l2_switch": [
        ("show snmp",                   "SNMP Status"),
        ("show snmp community",         "SNMP Communities"),
    ],
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def setup_logging():
    """Create log directory and return timestamped log file path."""
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(LOG_DIR, f"verification_{timestamp}.log")
    return log_file, timestamp


def log(log_file, message, also_print=True):
    """Write timestamped message to log file and optionally to console."""
    timestamped = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(timestamped + "\n")
    if also_print:
        print(timestamped)


def log_raw(log_file, text, also_print=True):
    """Write raw text (no timestamp) to log file. Used for command output."""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")
    if also_print:
        print(text)


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


# ============================================================
# VERIFICATION FUNCTION
# ============================================================

def verify_device(device, role, credentials, log_file):
    """
    Connect to a device, run all verification commands for its role,
    and log the output.
    
    Args:
        device:      Device dict from inventory
        role:        Device role string (core_router, edge_router, etc.)
        credentials: Shared credentials dict
        log_file:    Path to log file
        
    Returns:
        bool: True if device was verified successfully, False on error
    """
    hostname = device["hostname"]
    host = device["host"]
    
    # Get the verification commands for this role
    commands = VERIFICATION_COMMANDS.get(role, [])
    if not commands:
        log(log_file, f"  ⚠ No verification commands defined for role: {role}")
        return True  # Not a failure, just nothing to verify
    
    log(log_file, f"Connecting to {hostname} ({host})...")

    try:
        # ── Connect via SSH ───────────────────────────────────
        conn_params = build_connection_params(device, credentials)
        connection = ConnectHandler(**conn_params)
        connection.enable()
        log(log_file, f"  ✓ Connected to {hostname}")

        # ── Run each verification command ─────────────────────
        for command, description in commands:
            log(log_file, f"\n  ┌─ {description}: '{command}'")
            log_raw(log_file, f"  │")
            
            try:
                # Send the show command and capture output
                output = connection.send_command(command)
                
                if output.strip():
                    # Indent each line of output for clean formatting
                    for line in output.strip().splitlines():
                        log_raw(log_file, f"  │  {line}")
                else:
                    log_raw(log_file, f"  │  (no output)")
                    
            except Exception as cmd_error:
                log_raw(log_file, 
                    f"  │  ⚠ Command failed: {type(cmd_error).__name__}: {cmd_error}")
            
            log_raw(log_file, f"  └─{'─' * 50}")

        # ── Disconnect ────────────────────────────────────────
        connection.disconnect()
        log(log_file, f"\n  ✓ Verification complete for {hostname}\n")
        return True

    except NetmikoTimeoutException:
        log(log_file, f"  ✗ FAILED: Connection to {hostname} ({host}) timed out")
        return False

    except NetmikoAuthenticationException:
        log(log_file, f"  ✗ FAILED: Authentication failed for {hostname} ({host})")
        return False

    except Exception as e:
        log(log_file, f"  ✗ FAILED: {type(e).__name__}: {e}")
        return False


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """
    Main function — runs verification commands on all devices.
    
    Workflow:
      1. Load inventory
      2. Verify routers (detailed: interfaces, OSPF, NAT, ACLs, SNMP)
      3. Verify L3 switches (SNMP + interfaces)
      4. Verify L2 switches (SNMP)
      5. Print summary
    """
    # ── Setup ─────────────────────────────────────────────────
    log_file, timestamp = setup_logging()
    
    banner = (
        f"\n{'=' * 60}\n"
        f"  NETMIKO VERIFICATION SCRIPT\n"
        f"  EE8203 — Post-Configuration Verification\n"
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

    credentials = inventory["credentials"]
    success_count = 0
    fail_count = 0
    total = 0

    # ── Section 1: Verify Routers ─────────────────────────────
    log(log_file, f"\n{'═' * 60}")
    log(log_file, f"  SECTION 1: ROUTER VERIFICATION")
    log(log_file, f"{'═' * 60}\n")
    
    for device in inventory.get("routers", []):
        total += 1
        # Determine role from inventory
        role = device.get("role", "core_router")
        
        if verify_device(device, role, credentials, log_file):
            success_count += 1
        else:
            fail_count += 1

    # ── Section 2: Verify L3 Switches ─────────────────────────
    log(log_file, f"\n{'═' * 60}")
    log(log_file, f"  SECTION 2: L3 SWITCH VERIFICATION")
    log(log_file, f"{'═' * 60}\n")
    
    for device in inventory.get("l3_switches", []):
        total += 1
        if verify_device(device, "l3_switch", credentials, log_file):
            success_count += 1
        else:
            fail_count += 1

    # ── Section 3: Verify L2 Switches ─────────────────────────
    log(log_file, f"\n{'═' * 60}")
    log(log_file, f"  SECTION 3: L2 SWITCH VERIFICATION")
    log(log_file, f"{'═' * 60}\n")
    
    for device in inventory.get("l2_switches", []):
        total += 1
        if verify_device(device, "l2_switch", credentials, log_file):
            success_count += 1
        else:
            fail_count += 1

    # ── Summary ───────────────────────────────────────────────
    summary = (
        f"\n{'=' * 60}\n"
        f"  VERIFICATION SUMMARY\n"
        f"  ─────────────────────────────────────\n"
        f"  Total devices:     {total}\n"
        f"  Verified OK:       {success_count}\n"
        f"  Failed:            {fail_count}\n"
        f"  Log file:          {log_file}\n"
        f"{'=' * 60}\n"
    )
    log(log_file, summary)

    if fail_count > 0:
        log(log_file, 
            f"  ⚠ {fail_count} device(s) failed verification.\n"
            f"    Review the log file for details.\n"
        )
        sys.exit(1)
    else:
        log(log_file, "  ✓ All devices verified successfully!\n")


# ── Run the script ────────────────────────────────────────────
if __name__ == "__main__":
    main()
