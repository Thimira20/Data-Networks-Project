# EE8203 Campus Network — Implementation Guide (Phase 1: Design → Section 3.3 Routing)

This guide covers building the network in Cisco Packet Tracer (later repeated in GNS3), from
naming devices through OSPF routing. For every phase you get: **Commands**, **Why**, **How to
Verify**, and **How to Undo** (in case something breaks and you need to back out cleanly).

---

## 0. Keywords (read once, referenced throughout)

| Term | Meaning |
|---|---|
| **VLAN** | A way to split one switch into separate mini-networks. Devices in different VLANs cannot talk unless a router/L3 device connects them. |
| **Access port** | A switch port belonging to ONE VLAN. Used for end devices (PCs). |
| **Trunk port** | A switch port that carries MANY VLANs between switches, tagging each frame (802.1Q) so the other end knows which VLAN it belongs to. |
| **Native VLAN** | The one VLAN on a trunk sent *without* a tag. Moved to VLAN 100 (unused) for security. |
| **L2 vs L3 switch** | L2 only forwards within VLANs. L3 (multilayer) can also **route** between VLANs. |
| **SVI** (`interface vlan X`) | A virtual L3 interface on a switch — holds an IP, acts as the default gateway for that VLAN. This is how inter-VLAN routing happens. |
| **Routed port** (`no switchport`) | A switch port converted into a plain router-style port with its own IP. Used for switch↔router links. |
| **OSPF** | A dynamic routing protocol — routers/L3 switches automatically tell each other what networks they can reach. |
| **Wildcard mask** | OSPF's "inverted" subnet mask. `0` = must match, `255` = ignore. A /24 → `0.0.0.255`. |
| **MGMT VLAN (99)** | A separate VLAN used only to log in and manage devices, kept apart from user traffic. |

---

## 1. Device Name Mapping

| Project role | Hostname used |
|---|---|
| Core router | `R-CORE` |
| Edge/WAN router (added later) | `R-EDGE` |
| Core L3 switch | `SW-Core` |
| Distribution switches | `SW-D-DEIE`, `SW-D-DCEE`, `SW-D-DMME`, `SW-D-DIS` |
| Access switches | `SW-A-DEIE`, `SW-A-DCEE`, `SW-A-DMME`, `SW-A-DIS` |

> Design decision: **all inter-VLAN routing happens on SW-Core** (collapsed-core design).
> Distribution/access switches stay Layer-2 and just carry VLANs on trunks upward. This keeps
> every department's gateway in one place, makes MGMT VLAN 99 reachable everywhere, and keeps
> OSPF to a single, simple adjacency (SW-Core ↔ R-CORE).

---

## 2. Master Address Plan

**VLANs (created on every switch):**

| VLAN | Name | Subnet | Gateway (on SW-Core) |
|---|---|---|---|
| 10 | VLAN_DEIE | 10.10.10.0/24 | 10.10.10.1 |
| 20 | VLAN_DCEE | 10.10.20.0/24 | 10.10.20.1 |
| 30 | VLAN_DMME | 10.10.30.0/24 | 10.10.30.1 |
| 40 | VLAN_DIS  | 10.10.40.0/24 | 10.10.40.1 |
| 99 | MGMT | 10.99.99.0/24 | 10.99.99.1 |
| 100 | NATIVE | (unused, no IP) | — |

**Switch management IPs (VLAN 99):**

| Device | Mgmt IP |
|---|---|
| SW-Core | 10.99.99.1 (also the gateway) |
| SW-D-DEIE / DCEE / DMME / DIS | 10.99.99.11 / .12 / .13 / .14 |
| SW-A-DEIE / DCEE / DMME / DIS | 10.99.99.21 / .22 / .23 / .24 |

**Router link (point-to-point, /30):** SW-Core `Gig1/0/2` = `10.0.0.1` ↔ R-CORE `Gig0/0/0` = `10.0.0.2`

**PCs:**

| PC | VLAN | IP | Gateway |
|---|---|---|---|
| DEIE PCs | 10 | 10.10.10.10 / .11 | 10.10.10.1 |
| DCEE PCs | 20 | 10.10.20.10 / .11 | 10.10.20.1 |
| DMME PCs | 30 | 10.10.30.10 / .11 | 10.10.30.1 |
| DIS PCs | 40 | 10.10.40.10 / .11 | 10.10.40.1 |

---

## Phase A — Hostnames ✅ (already done, per `naming.txt`)

**Command pattern used:**
```
enable
configure terminal
 hostname SW-D-DEIE
end
write memory
```

**Verify:**
```
show running-config | include hostname
```
Expected: the prompt itself changes immediately, e.g. `SW-D-DEIE(config)#`.

**Undo (if named wrong):** just set it again — there's no separate "delete", a new hostname
simply overwrites the old one.
```
configure terminal
 hostname CorrectNameHere
end
write memory
```

---

## Phase B — Create VLANs ✅ (already done, per `create_VLANS.txt`)

**Command pattern used (run on every switch):**
```
configure terminal
 vlan 10
  name VLAN_DEIE
 vlan 20
  name VLAN_DCEE
 vlan 30
  name VLAN_DMME
 vlan 40
  name VLAN_DIS
 vlan 99
  name MGMT
 vlan 100
  name NATIVE
end
write memory
```

**Verify:**
```
show vlan brief
```
Expected: VLANs 10, 20, 30, 40, 99, 100 all listed with the correct names. At this point ports
still show under VLAN 1 (default) — that's normal, access assignment happens in Phase C.

**Undo — delete one VLAN:**
```
configure terminal
 no vlan 10
end
write memory
```
⚠️ Any port assigned to VLAN 10 becomes **inactive** (shown as "inactive" in `show vlan brief`)
until you either recreate VLAN 10 or reassign the port. Recreating the VLAN with the same
number/name restores those ports automatically.

**Undo — delete ALL VLANs configured so far:**
```
configure terminal
 no vlan 10
 no vlan 20
 no vlan 30
 no vlan 40
 no vlan 99
 no vlan 100
end
```

---

## Phase C — Access Ports ✅ (already done, per `access_swithecs_cofig.txt`)

**Command pattern used (example — adjust ports/VLAN per switch):**
```
configure terminal
 interface range fastEthernet 0/1 - 2
  switchport mode access
  switchport access vlan 10
  spanning-tree portfast
end
write memory
```
> Your files show DEIE/DCEE access switches using ports `Fa0/1-2` and DMME/DIS using
> `Fa0/2-3` — that's fine, just make sure it matches which physical ports your PCs are
> actually plugged into in Packet Tracer.

**Verify:**
```
show interfaces status
show vlan brief
```
Expected: the ports show `connected` and appear listed under the correct VLAN in `show vlan brief`
(e.g., Fa0/1, Fa0/2 under VLAN 10).

**Undo — revert one port range to factory default (cleanest method):**
```
configure terminal
 default interface range fastEthernet 0/1 - 2
end
```
This wipes **all** config on those ports (access vlan, portfast, everything) back to default in
one shot — you'll need to re-apply Phase C afterward if you only wanted to fix one line.

**Undo — revert manually (keeps other port settings untouched):**
```
configure terminal
 interface range fastEthernet 0/1 - 2
  no switchport access vlan
  no spanning-tree portfast
  switchport mode dynamic auto
end
```

---

## Phase D — Trunk Links (next step for you)

Do this on **both ends** of every switch-to-switch cable (access↔distribution,
distribution↔core).

**Commands (example: SW-A-DEIE port facing SW-D-DEIE):**
```
configure terminal
 interface fastEthernet 0/3
  switchport trunk encapsulation dot1q
  switchport mode trunk
  switchport trunk native vlan 100
end
write memory
```
Repeat with the matching port on SW-D-DEIE, and on both ends of SW-D-DEIE ↔ SW-Core.

**Why:** `encapsulation dot1q` picks the tagging standard (3560 switches support more than
one, so you must state it before trunk mode is accepted). Native VLAN 100 keeps untagged
traffic off VLAN 1, closing a common security hole.

**Verify:**
```
show interfaces trunk
```
Expected: the port is listed, mode shows `trunk`, and VLANs 10,20,30,40,99,100 (whichever
apply) appear as "allowed and active". Run this on **both ends** — if only one side shows
trunk, the link won't work correctly.

Also check:
```
show interfaces fastEthernet 0/3 switchport
```
Expected: `Administrative Mode: trunk`, `Operational Mode: trunk`, `Trunking Native Mode VLAN: 100`.

**Undo — revert one trunk port to access:**
```
configure terminal
 interface fastEthernet 0/3
  no switchport trunk encapsulation dot1q
  no switchport trunk native vlan
  switchport mode access
end
```
**Undo — full factory reset of that port:**
```
configure terminal
 default interface fastEthernet 0/3
end
```

---

## Phase E — SW-Core: Enable Routing + Gateways (SVIs)

**Commands:**
```
configure terminal
 ip routing

 interface vlan 10
  ip address 10.10.10.1 255.255.255.0
 interface vlan 20
  ip address 10.10.20.1 255.255.255.0
 interface vlan 30
  ip address 10.10.30.1 255.255.255.0
 interface vlan 40
  ip address 10.10.40.1 255.255.255.0
 interface vlan 99
  ip address 10.99.99.1 255.255.255.0
end
write memory
```

**Also set SW-Core as spanning-tree root (recommended):**
```
configure terminal
 spanning-tree vlan 1-100 root primary
end
```

**Why:** `ip routing` is the master switch that turns on Layer-3 routing for this switch.
Each SVI is a "door" between that VLAN and the rest of the network — without it, PCs in that
VLAN have no gateway and can't leave their own subnet.

**Verify:**
```
show ip interface brief
```
Expected: `Vlan10`, `Vlan20`, `Vlan30`, `Vlan40`, `Vlan99` all show the correct IP and
`up / up` status. (An SVI only comes up if VLAN exists AND at least one port in that VLAN is
active — if it shows `up / down`, check Phase B/C first.)
```
show vlan brief
show spanning-tree summary
```
Expected: for root check, `show spanning-tree vlan 10` should show "This bridge is the root".

**Undo — remove one gateway:**
```
configure terminal
 no interface vlan 10
end
```
**Undo — turn off routing completely (reverts SW-Core to plain L2 switch):**
```
configure terminal
 no ip routing
end
```
**Undo — remove root priority setting (restore default priority 32768):**
```
configure terminal
 spanning-tree vlan 1-100 priority 32768
end
```

---

## Phase F — Management IPs on Distribution/Access (L2) Switches

**Commands (example: SW-D-DEIE, IP 10.99.99.11):**
```
configure terminal
 interface vlan 99
  ip address 10.99.99.11 255.255.255.0
  no shutdown
 ip default-gateway 10.99.99.1
end
write memory
```
Repeat on every distribution and access switch using its own IP from the address plan table.

**Why:** these switches can't route, so they need one IP (via VLAN 99) to be reachable for
SSH/management, plus a default-gateway pointing at SW-Core to reach anything off their own
subnet.

**Verify:**
```
show ip interface brief | include Vlan99
show running-config | include default-gateway
```
Then **from SW-Core**, test reachability:
```
ping 10.99.99.11
```
Expected: success (4/4 or 5/5 replies).

**Undo:**
```
configure terminal
 interface vlan 99
  no ip address
  shutdown
 no ip default-gateway 10.99.99.11
end
```

---

## Phase G — Routed Link: SW-Core ↔ R-CORE

**On SW-Core** (port facing the router, e.g. `Gig1/0/2`):
```
configure terminal
 interface gigabitEthernet 0/1
  no switchport
  ip address 10.0.0.1 255.255.255.252
  no shutdown
end
```

**On R-CORE:**
```
configure terminal
 interface gigabitEthernet 0/0/0
  ip address 10.0.0.2 255.255.255.252
  no shutdown
end
```

**Why:** this link connects two Layer-3 devices directly — no VLANs to carry, so it's a plain
routed point-to-point link instead of a trunk.

**Verify:**
```
show ip interface brief
```
Expected: both ends show `10.0.0.1`/`10.0.0.2`, status `up / up`.
```
ping 10.0.0.2      ! run from SW-Core
```
Expected: success.

**Undo (SW-Core side — converts the port back to a normal switch port):**
```
configure terminal
 interface gigabitEthernet 1/0/2
  no ip address
  switchport
end
```
**Undo (R-CORE side):**
```
configure terminal
 interface gigabitEthernet 0/0/0
  no ip address
  shutdown
end
```

---

## Phase H — OSPF Routing

**On SW-Core:**
```
configure terminal
 router ospf 1
  network 10.0.0.0 0.0.0.3 area 0
  network 10.10.10.0 0.0.0.255 area 0
  network 10.10.20.0 0.0.0.255 area 0
  network 10.10.30.0 0.0.0.255 area 0
  network 10.10.40.0 0.0.0.255 area 0
  network 10.99.99.0 0.0.0.255 area 0
  passive-interface default
  no passive-interface gigabitEthernet 0/1
end
write memory
```

**On R-CORE:**
```
configure terminal
 router ospf 1
  network 10.0.0.0 0.0.0.3 area 0
end
write memory
```

**Why:** OSPF automatically shares "which networks I can reach" between SW-Core and R-CORE, so
you don't hand-write routes. `passive-interface default` + the one `no passive-interface`
exception stops OSPF chatter from going out toward PCs — it only exchanges info on the
router-facing link.

**Verify:**
```
show ip ospf neighbor
```
Expected: R-CORE listed with state **FULL** (this is the adjacency — if it's stuck at INIT or
EXSTART, check the Gig1/0/2 IPs/subnet match and the link is up first).
```
show ip route ospf
```
Expected: routes learned via OSPF appear marked with `O`.
```
show ip protocols
```
Expected: confirms OSPF process 1, area 0, and which interfaces are active/passive.

**Undo — remove the entire OSPF process (simplest full rollback):**
```
configure terminal
 no router ospf 1
end
```
**Undo — remove just one network statement:**
```
configure terminal
 router ospf 1
  no network 10.10.10.0 0.0.0.255 area 0
end
```

---

## Phase I — PC IP Configuration

On each PC: **Desktop → IP Configuration** → enter Static IP, Subnet Mask `255.255.255.0`,
Default Gateway per the PC table in Section 2.

**Verify:** open the PC's Command Prompt:
```
ipconfig
```
Expected: shows the IP/mask/gateway you just entered.

**Undo:** switch the PC back to **DHCP** in IP Configuration, or simply clear/retype the
static fields.

---

## 3. Final End-to-End Verification (run after Phase H is complete)

**On SW-Core:**
```
show ip interface brief
show vlan brief
show ip route
show ip ospf neighbor
```

**From a DEIE PC's Command Prompt:**
```
ping 10.10.10.1      ! own gateway            -> must succeed
ping 10.10.20.10     ! a DCEE PC               -> must succeed (inter-VLAN routing works)
ping 10.10.40.10     ! a DIS PC                -> must succeed
ping 10.0.0.2        ! the router R-CORE       -> must succeed (OSPF path works)
```

If all four succeed, Section 3.3 (VLANs, trunking, inter-VLAN routing, OSPF) is fully working.

**Troubleshooting order when a ping fails:**
1. VLAN exists on all switches (Phase B)
2. PC IP/gateway correct (Phase I)
3. Trunk up on **both ends** of every switch link (Phase D — check `show interfaces trunk`)
4. `ip routing` enabled + SVI is `up/up` (Phase E)
5. `show ip ospf neighbor` shows FULL (Phase H)

---

## 4. General Safety Tip

Before trying something you're unsure about, **save your Packet Tracer file under a new name**
(e.g. `project_before_ospf.pkt`) so you always have a known-good checkpoint to go back to —
this is the Packet Tracer equivalent of a GNS3 snapshot, and is exactly the habit the project's
MOP risk table expects ("take a snapshot before each change").

---

## 5. What's Next

1. **R-EDGE** — add a second router + simulated internet cloud, static default route, NAT
   overload (only VLAN_DEIE and VLAN_DCEE get internet egress).
2. **Section 3.4 — ACLs** — inter-department permit/deny rules, then the 4×4 reachability
   test matrix (ping + traceroute, screenshot each cell).
3. **Move to GNS3** — repeat this same design with real Cisco IOS/IOSv images.
