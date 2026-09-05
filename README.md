# Data Networks Project

This project documents the design and implementation of a campus network with VLAN segmentation, trunking, inter-VLAN routing, management connectivity, OSPF routing, and automation support.

## Topology Overview

![Network Topology](network%20topology/topology.png)

## Project Highlights

- VLAN design for multiple departments
- Access and trunk switch configuration
- Inter-VLAN routing on the core multilayer switch
- Management VLAN for device administration
- Routed link between the core switch and core router
- OSPF routing for dynamic network reachability
- Automation artifacts for Python, Netmiko, and Ansible

## Network Devices

- `R-CORE` — core router
- `R-EDGE` — edge/WAN router
- `SW-Core` — core Layer 3 switch
- Distribution switches:
  - `SW-D-DEIE`
  - `SW-D-DCEE`
  - `SW-D-DMME`
  - `SW-D-DIS`
- Access switches:
  - `SW-A-DEIE`
  - `SW-A-DCEE`
  - `SW-A-DMME`
  - `SW-A-DIS`

## Addressing Summary

### VLANs

- VLAN 10 — `VLAN_DEIE` — `10.10.10.0/24`
- VLAN 20 — `VLAN_DCEE` — `10.10.20.0/24`
- VLAN 30 — `VLAN_DMME` — `10.10.30.0/24`
- VLAN 40 — `VLAN_DIS` — `10.10.40.0/24`
- VLAN 99 — `MGMT` — `10.99.99.0/24`
- VLAN 100 — `NATIVE` — unused native VLAN for trunk links

### Core Link

- `SW-Core` ↔ `R-CORE`
- Network: `10.0.0.0/30`
- `SW-Core`: `10.0.0.1`
- `R-CORE`: `10.0.0.2`

## Repository Contents

Some useful files in this repo:

- `Network_Implementation_Guide.md` — step-by-step implementation guide
- `topology.png` — network topology diagram
- `VLAN_CONFIG/` — VLAN configuration files
- `automation/` and `netmiko_automation/` — automation-related scripts and files
- `trunk_config.md` — trunking reference
- `zabbix_deployment_guide.md` — monitoring deployment guide

## How to Use

1. Open the topology image above to understand the design.
2. Follow `Network_Implementation_Guide.md` for implementation steps.
3. Apply the configuration files in the correct order:
   - hostnames
   - VLANs
   - access ports
   - trunk links
   - SVIs and routing
   - management IPs
   - OSPF
   - PC IP settings
4. Verify connectivity using the test steps in the guide.

## Verification

After setup, the project should support:

- Successful ping within the same VLAN
- Successful inter-VLAN communication
- Management access to switches via VLAN 99
- OSPF neighbor adjacency between `SW-Core` and `R-CORE`

## Notes

This repository contains multiple related network design and automation artifacts. If you want, I can also help you turn this into a more polished README with sections like Features, Setup, Usage, and Screenshots.

## License

No license was found in the repository.
