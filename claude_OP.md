Which device is which
Project role	Your screenshot device	Belongs to
R-CORE (router)	Router0 (ISR4331)	Center
SW-CORE (core L3 switch)	Multilayer Switch4 (center)	Center
SW-D-DEIE (distribution)	SW-D-DEIE	DEIE (bottom-left)
SW-A-DEIE (access)	SW-A-DEIE	DEIE
SW-D-DCEE	Multilayer Switch3 (top-left)	DCEE
SW-A-DCEE	Multilayer Switch2 (top-left)	DCEE
SW-D-DMME	Switch7 (top-right)	DMME
SW-A-DMME	Multilayer Switch6 (top-right)	DMME
SW-D-DIS	Multilayer Switch5 (bottom-right)	DIS (servers)
SW-A-DIS	Switch (bottom-right)	DIS
⚠️ Note: The project asks for two routers (R-CORE + R-EDGE). Your topology has one. That's fine for now — R-EDGE is only needed for internet + NAT, which comes after Section 3.3. We'll use your single router as R-CORE and add R-EDGE later.

Part 1 — Key words you must understand first
Read these once; every step below uses them.

VLAN (Virtual LAN): a way to split one switch into several separate mini-networks. Two PCs in different VLANs cannot talk unless a router/Layer-3 device connects them. We use one VLAN per department so departments are isolated by default.
Access port: a switch port that belongs to one VLAN. Used for end devices (PCs).
Trunk port: a switch port that carries many VLANs between switches at once. It labels each frame with a VLAN tag (802.1Q) so the other switch knows which VLAN it came from.
Native VLAN: the one VLAN on a trunk sent without a tag. We move it to an unused VLAN (100) for security.
L2 switch vs L3 switch: A Layer-2 switch only forwards frames inside VLANs (no routing). A Layer-3 (multilayer) switch can also route between VLANs.
SVI (interface vlan X): a virtual Layer-3 interface on a switch that holds an IP and acts as the default gateway for that VLAN. This is how a Layer-3 switch does inter-VLAN routing (moving traffic between VLANs).
Routed port (no switchport): a switch port turned into a plain router interface with its own IP. Used for the link between the core switch and the router.
OSPF: a dynamic routing protocol. Devices automatically tell each other "here are the networks I can reach," so you don't hand-write every route.
Wildcard mask: OSPF's "backwards" subnet mask. 0 = must match, 255 = ignore. A /24 network → 0.0.0.255.
Management VLAN (99): a separate VLAN used only to log in and manage switches, kept away from user traffic.
Part 2 — The design decision (the big "why")
Where does inter-VLAN routing happen? I recommend doing all routing on SW-CORE (this is called a collapsed-core design). Distribution and access switches stay as Layer-2 (they just carry VLANs upward on trunks).

Why this choice for you:

All department gateways live in one place (SW-CORE) → far fewer commands, far fewer mistakes for a beginner.
The management VLAN 99 (10.99.99.0/24) can then truly span every switch — exactly what the project asks.
OSPF only runs between SW-CORE ↔ R-CORE → simple to understand and verify.
It still satisfies the requirements: three-layer hierarchy ✓, VLANs + trunking ✓, inter-VLAN routing on the core L3 switch ✓, OSPF between L3 switch and router ✓.
(In your report you can justify distribution switches being L3-capable as "reserved for future routing/HSRP and scalability" — that's a legitimate engineering rationale.)

Part 3 — The master plan (fill these tables into your design doc)
VLANs (create on every switch):

VLAN	Name	Subnet	Gateway (on SW-CORE)
10	VLAN_DEIE	10.10.10.0/24	10.10.10.1
20	VLAN_DCEE	10.10.20.0/24	10.10.20.1
30	VLAN_DMME	10.10.30.0/24	10.10.30.1
40	VLAN_DIS	10.10.40.0/24	10.10.40.1
99	MGMT	10.99.99.0/24	10.99.99.1
100	NATIVE	(unused)	—
Switch management IPs (VLAN 99):

Device	Mgmt IP
SW-CORE	10.99.99.1 (this is also the gateway)
SW-D-DEIE / DCEE / DMME / DIS	10.99.99.11 / .12 / .13 / .14
SW-A-DEIE / DCEE / DMME / DIS	10.99.99.21 / .22 / .23 / .24
Router link (routed, /30 = 2 usable IPs): SW-CORE Gig1/0/2 = 10.0.0.1 ↔ R-CORE Gig0/0/0 = 10.0.0.2

PCs (set gateway = the .1 of their subnet):

PC	VLAN	IP	Gateway
PC0, PC1 (DEIE)	10	10.10.10.10 / .11	10.10.10.1
PC6, PC7 (DCEE)	20	10.10.20.10 / .11	10.10.20.1
PC4, PC5 (DMME)	30	10.10.30.10 / .11	10.10.30.1
PC2, PC3 (DIS)	40	10.10.40.10 / .11	10.10.40.1
Part 4 — Step-by-step configuration
Do the phases in order. I'll show the DEIE department fully as a worked example; the other three departments are identical except for the VLAN number and IPs from the tables above.

How to type commands: click a device → CLI tab. enable gets you to privileged mode; configure terminal (conf t) enters config mode.

Phase A — Name every device (do on all)

enable
configure terminal
 hostname SW-CORE      ! use the correct name per the mapping table
end
write memory           ! saves config so a reload doesn't lose it
Why: clear names make the rest of the project (SSH, automation, Zabbix) sane.

Phase B — Create all VLANs (do on EVERY switch, core + all 8)

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
Why: a switch can only carry/tag a VLAN it actually knows about. The core also needs every VLAN to exist before its gateway (SVI) will turn on.

Phase C — Access switch: PC ports (worked example: SW-A-DEIE)
PC0 and PC1 plug into Fa0/1 and Fa0/2 here.


configure terminal
 interface range fastEthernet 0/1 - 2
  switchport mode access          ! this port belongs to ONE vlan (end-device port)
  switchport access vlan 10       ! put DEIE PCs into VLAN 10
  spanning-tree portfast          ! port goes active instantly (safe: PCs can't loop)
end
For the other access switches: same commands, just change vlan 10 → 20 (SW-A-DCEE), 30 (SW-A-DMME), 40 (SW-A-DIS), and use whichever ports the PCs are plugged into.

Phase D — Trunk links (switch-to-switch)
A trunk is needed on both ends of every switch-to-switch cable: access↔distribution and distribution↔core.

Example — SW-A-DEIE uplink to SW-D-DEIE (port Fa0/3 in your screenshot):


configure terminal
 interface fastEthernet 0/3
  switchport trunk encapsulation dot1q   ! REQUIRED on 3560 before "mode trunk"
  switchport mode trunk                  ! carry many VLANs on this link
  switchport trunk native vlan 100       ! untagged frames use unused VLAN 100 (security)
end
Repeat on the other end (SW-D-DEIE's port facing the access switch), and on both ends of the SW-D-DEIE ↔ SW-CORE link.

Why encapsulation dot1q: the 3560 switch supports more than one trunk "language," so you must explicitly pick 802.1Q (the modern standard) before it lets you make the port a trunk.
Why native VLAN 100: attackers can abuse the default native VLAN 1; moving it to an unused VLAN closes that hole.

On the distribution switches you only configure trunks (one down to access, one up to core). That's all they do in this design — pass VLANs through.

Phase E — SW-CORE: turn on routing + create gateways
This is the heart of the network.


configure terminal
 ip routing                       ! MASTER SWITCH: allows this L3 switch to route between VLANs

 interface vlan 10
  ip address 10.10.10.1 255.255.255.0   ! gateway for DEIE PCs
 interface vlan 20
  ip address 10.10.20.1 255.255.255.0
 interface vlan 30
  ip address 10.10.30.1 255.255.255.0
 interface vlan 40
  ip address 10.10.40.1 255.255.255.0
 interface vlan 99
  ip address 10.99.99.1 255.255.255.0   ! gateway for management
end
Why: each interface vlan X (an SVI) is the door between that VLAN and the rest of the network. Without ip routing, these doors stay locked and departments can't reach each other or the internet.

Also make SW-CORE the spanning-tree root (best practice, keeps the tree predictable):


configure terminal
 spanning-tree vlan 1-100 root primary
end
Phase F — Management IPs on the Layer-2 switches
On each access & distribution switch (they can't route, so they need a gateway):


configure terminal
 interface vlan 99
  ip address 10.99.99.11 255.255.255.0   ! use this device's IP from the table
  no shutdown
 ip default-gateway 10.99.99.1           ! send off-subnet traffic to SW-CORE
end
Why: this gives you a single IP to SSH into each switch later (needed for Netmiko/Ansible/Zabbix). ip default-gateway is how a non-routing switch reaches other networks.

Phase G — The routed link SW-CORE ↔ R-CORE
On SW-CORE (port Gig1/0/2 toward the router):


configure terminal
 interface gigabitEthernet 1/0/2
  no switchport                       ! turn this into a real router-style port
  ip address 10.0.0.1 255.255.255.252 ! /30 point-to-point link
  no shutdown
end
On R-CORE (Router0):


configure terminal
 interface gigabitEthernet 0/0/0
  ip address 10.0.0.2 255.255.255.252
  no shutdown
end
Why a routed port here: the link between two Layer-3 devices carries no VLANs — it's a pure router-to-router hop, so we give it plain IPs instead of trunking.

Phase H — OSPF (dynamic routing)
On SW-CORE:


configure terminal
 router ospf 1
  network 10.0.0.0 0.0.0.3 area 0        ! the router link
  network 10.10.10.0 0.0.0.255 area 0    ! DEIE
  network 10.10.20.0 0.0.0.255 area 0    ! DCEE
  network 10.10.30.0 0.0.0.255 area 0    ! DMME
  network 10.10.40.0 0.0.0.255 area 0    ! DIS
  network 10.99.99.0 0.0.0.255 area 0    ! management
  passive-interface default             ! don't send OSPF out to PCs...
  no passive-interface gigabitEthernet 1/0/2   ! ...only talk OSPF toward the router
end
On R-CORE:


configure terminal
 router ospf 1
  network 10.0.0.0 0.0.0.3 area 0
end
Why OSPF: SW-CORE tells R-CORE "I can reach all the 10.10.x.0 department networks." Later, R-EDGE will inject a default route so those departments reach the internet — OSPF spreads that automatically. passive-interface stops the switch from wasting effort (and leaking info) by sending routing messages toward PCs. area 0 is OSPF's mandatory backbone area (Section 3.3 requires single area 0).

Phase I — Configure the PCs
On each PC → Desktop → IP Configuration, enter the IP, subnet 255.255.255.0, and gateway from the PC table (e.g., PC0: IP 10.10.10.10, gateway 10.10.10.1).

Part 5 — Verify it works (do this, screenshots become report evidence)
Run these on SW-CORE:


show ip interface brief      ! all VLAN interfaces + Gig1/0/2 should be "up / up"
show vlan brief              ! confirm VLANs exist and ports are assigned
show ip route                ! you should see connected 10.10.x.0 nets + an OSPF route
show ip ospf neighbor        ! must show R-CORE as FULL (adjacency formed)
Then from PC0 (DEIE), open Command Prompt and ping:


ping 10.10.10.1     ! own gateway   -> must succeed
ping 10.10.20.10    ! a DCEE PC      -> must succeed (inter-VLAN routing works!)
ping 10.10.40.10    ! a DIS server   -> must succeed
ping 10.0.0.2       ! the router     -> must succeed (OSPF/routing works!)
If all four succeed, your network up to Section 3.3 is complete: VLANs, trunking, inter-VLAN routing, and OSPF are all working.

If a ping fails, check in this order: VLAN exists on all switches (Phase B) → PC IP/gateway correct → trunk up on both ends (Phase D) → ip routing is on (Phase E) → show ip ospf neighbor shows FULL (Phase H).

What comes next (so you see the road ahead)
Add R-EDGE + a "Cloud" for the internet → static default route + NAT overload (finishes Section 3.3's internet part).
Section 3.4 — ACLs: the inter-department permit/deny rules + your 4×4 ping matrix.
Move to GNS3 and repeat with real Cisco IOS images (same concepts, same commands).
Want me to (a) save this whole guide as a Markdown file in your project folder for reference, (b) write out the exact per-device command sets for DCEE, DMME, and DIS (copy-paste ready), or (c) continue into adding R-EDGE + NAT? Tell me which and I'll do it.