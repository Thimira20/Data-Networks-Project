Searched for "VLAN 99"
Viewed Network_Implementation_Guide.md:50-75
Viewed Network_Implementation_Guide.md:320-360

### What is VLAN 99?

**VLAN 99** is a **Management VLAN (MGMT)**. 

In a network, switches carry user data traffic for various departments (e.g., DEIE on VLAN 10, DCEE on VLAN 20, DMME on VLAN 30). However, network administrators also need a way to **remote log in (via SSH or Telnet)** to the switches to configure them, check status, or fix issues.

Instead of mixing administrative traffic with regular student/staff traffic, we isolate administrative access onto a dedicated network segment—**VLAN 99 (`10.99.99.0/24`)**.

---

### Line-by-Line Breakdown of the Commands

When you configure an Access or Distribution Switch (like `SW-D-DEIE`):

```cisco
configure terminal
 interface vlan 99
  ip address 10.99.99.11 255.255.255.0
  no shutdown
 ip default-gateway 10.99.99.1
end
```

1. **`interface vlan 99`**
   Layer 2 switches only forward Ethernet frames based on MAC addresses. They don't naturally have IP addresses on physical ports. This command creates a **Switch Virtual Interface (SVI)** on VLAN 99—a virtual network card for the switch itself so it can participate in IP networking.

2. **`ip address 10.99.99.11 255.255.255.0`**
   Assigns a unique IP address to this specific switch inside the management subnet (`10.99.99.0/24`).

3. **`no shutdown`**
   Turns the virtual VLAN 99 interface **ON**.

4. **`ip default-gateway 10.99.99.1`**
   Because Layer 2 switches **cannot route packets** between different subnets, they only know how to communicate directly with devices inside their own subnet (`10.99.99.x`). 
   This command tells the switch: *"If you need to send a packet to an IP address outside `10.99.99.0/24`, send it to `10.99.99.1` (`SW-Core`), and let `SW-Core` route it."*

---

### Working Example: Step-by-Step Scenario

#### **The Scenario:**
- **Network Admin PC**: Located in the DEIE lab (`VLAN 10`, IP: `10.10.10.10`).
- **Target Switch**: `SW-D-DEIE` (`VLAN 99`, IP: `10.99.99.11`).
- **Core Switch**: `SW-Core` (Acts as the inter-VLAN router with IP `10.10.10.1` on VLAN 10 and IP `10.99.99.1` on VLAN 99).

---

#### **Traffic Flow (Step-by-Step):**

```
 [ Admin PC ]  ---(VLAN 10)--->  [ SW-Core ]  ---(VLAN 99)--->  [ SW-D-DEIE ]
 (10.10.10.10)                 (10.99.99.1)                   (10.99.99.11)
```

1. **Admin initiates SSH connection:**
   The Admin at PC `10.10.10.10` opens a terminal and types: `ssh admin@10.99.99.11`.

2. **Packet arrives at SW-Core:**
   Because `10.99.99.11` is on a different subnet than the PC (`10.10.10.10`), the Admin PC sends the SSH packet to its default gateway: `SW-Core` (`10.10.10.1`).

3. **SW-Core routes the packet to VLAN 99:**
   `SW-Core` is a Layer 3 switch with `ip routing` enabled. It checks its routing table, sees `10.99.99.0/24` is directly connected on `VLAN 99`, and forwards the frame across the trunk link to `SW-D-DEIE`.

4. **SW-D-DEIE receives the SSH request:**
   `SW-D-DEIE` accepts the request on its `interface vlan 99` (`10.99.99.11`).

5. **SW-D-DEIE needs to send a REPLY back to Admin PC (`10.10.10.10`):**
   *Here is why `ip default-gateway` is essential:*
   - `SW-D-DEIE` looks at the destination IP of the response: `10.10.10.10`.
   - `SW-D-DEIE` checks its own subnet: `10.99.99.0/24`.
   - It notices `10.10.10.10` is **NOT on its local subnet**.
   - Since `SW-D-DEIE` is an L2 switch without a full routing table, it checks its configured `ip default-gateway`.
   - It sees `ip default-gateway 10.99.99.1` and forwards the reply packet to `SW-Core`.

6. **SW-Core routes reply back to Admin PC:**
   `SW-Core` receives the reply on VLAN 99, routes it back to VLAN 10, and delivers it to `10.10.10.10`.

7. **Result:** The SSH session successfully connects!

---

### What happens if you forget `ip default-gateway`?

If you configure `interface vlan 99` with IP `10.99.99.11` **WITHOUT** setting `ip default-gateway 10.99.99.1`:

- Pinging `SW-D-DEIE` directly from `SW-Core` (`10.99.99.1`) will **WORK** (because both are in the `10.99.99.0/24` subnet).
- Connecting/Pinging `SW-D-DEIE` from any Admin PC (`10.10.10.10` or outside subnets) will **FAIL**. The switch will receive the incoming packet, but will **drop the response** because it has no default gateway to send out-of-subnet traffic to.