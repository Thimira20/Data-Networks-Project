# EE8203 Campus Network — ACL Configuration Guide (Collapsed Core)

> **Important Correction:** We are using the **Collapsed Core** design. Even though the
> distribution switches *can* do Layer 3, using them for routing in this topology forces
> data traffic to cross VLAN 99 (MGMT) to reach the core. This violates the project rule
> that the Management VLAN must be isolated.
> 
> **Solution:** SW-Core handles ALL inter-VLAN routing. All SVIs and ACLs live on SW-Core.

---

## 1. Why Did Your Ping Fail?

In the previous test:
- `PC1 ping 10.10.20.10` returning `Administratively prohibited` from `10.10.10.1` was **SUCCESSFUL!** That was your DEIE ACL correctly blocking access to DCEE.
- `PC1 ping 10.10.40.10` returning `Administratively prohibited` from `10.99.99.1` was a **FAILURE**. Because data was routing over VLAN 99, the `ACL_MGMT_IN` on SW-Core (which only allows SSH) blocked your legitimate data traffic.

---

## 2. PREREQUISITE: Restore SW-Core as the Central Gateway

First, we must move the gateways (SVIs) back to SW-Core and turn the distribution switches back to Layer 2 mode.

### 2.1 On SW-D-DEIE, DCEE, and DMME (Run on ALL THREE)
```
enable
configure terminal
no ip routing
no router ospf 1
no interface vlan 10    ! (On DCEE use vlan 20, on DMME use vlan 30)
ip default-gateway 10.99.99.1
end
write memory
```

### 2.2 On SW-Core (Recreate SVIs and reset OSPF)
```
enable
configure terminal

interface vlan 10
 description GW_VLAN_DEIE
 ip address 10.10.10.1 255.255.255.0
 no shutdown

interface vlan 20
 description GW_VLAN_DCEE
 ip address 10.10.20.1 255.255.255.0
 no shutdown

interface vlan 30
 description GW_VLAN_DMME
 ip address 10.10.30.1 255.255.255.0
 no shutdown

router ospf 1
 network 10.10.10.0 0.0.0.255 area 0
 network 10.10.20.0 0.0.0.255 area 0
 network 10.10.30.0 0.0.0.255 area 0
 network 10.10.40.0 0.0.0.255 area 0
 passive-interface default
 no passive-interface gigabitEthernet 0/1   ! Link to R-CORE
exit
end
write memory
```

**Test before adding ACLs:** Ping from DEIE PC (10.10.10.10) to DIS server (10.10.40.10) — it must succeed!

---

## 3. Configure ACLs on SW-Core

Apply these commands **only on SW-Core**.

### 3.1 ACL for DEIE (VLAN 10)
```
enable
configure terminal
ip access-list extended ACL_DEIE_IN
 permit ip 10.10.10.0 0.0.0.255 10.10.40.0 0.0.0.255
 permit ip 10.10.10.0 0.0.0.255 10.0.0.0 0.0.0.3
 permit ip 10.10.10.0 0.0.0.255 10.0.1.0 0.0.0.3
 deny ip any any
exit
interface vlan 10
 ip access-group ACL_DEIE_IN in
exit
end
write memory
```

### 3.2 ACL for DCEE (VLAN 20)
```
enable
configure terminal
ip access-list extended ACL_DCEE_IN
 permit tcp 10.10.20.0 0.0.0.255 10.10.40.0 0.0.0.255 eq 80
 permit tcp 10.10.20.0 0.0.0.255 10.10.40.0 0.0.0.255 eq 443
 deny ip 10.10.20.0 0.0.0.255 10.10.10.0 0.0.0.255
 permit ip 10.10.20.0 0.0.0.255 10.0.0.0 0.0.0.3
 permit ip 10.10.20.0 0.0.0.255 10.0.1.0 0.0.0.3
 deny ip any any
exit
interface vlan 20
 ip access-group ACL_DCEE_IN in
exit
end
write memory
```

### 3.3 ACL for DMME (VLAN 30)
```
enable
configure terminal
ip access-list extended ACL_DMME_IN
 deny ip 10.10.30.0 0.0.0.255 10.10.40.0 0.0.0.255
 deny ip 10.10.30.0 0.0.0.255 10.10.20.0 0.0.0.255
 deny ip any any
exit
interface vlan 30
 ip access-group ACL_DMME_IN in
exit
end
write memory
```

### 3.4 ACL for DIS (VLAN 40)
```
enable
configure terminal
ip access-list extended ACL_DIS_IN
 permit udp host 10.10.40.100 10.10.10.0 0.0.0.255 eq 161
 permit udp host 10.10.40.100 10.10.20.0 0.0.0.255 eq 161
 permit udp host 10.10.40.100 10.10.30.0 0.0.0.255 eq 161
 permit udp host 10.10.40.100 10.99.99.0 0.0.0.255 eq 161
 permit udp host 10.10.40.100 10.0.0.0 0.0.0.3 eq 161
 permit udp host 10.10.40.100 10.0.1.0 0.0.0.3 eq 161
 permit ip 10.10.40.0 0.0.0.255 10.10.10.0 0.0.0.255
 permit tcp 10.10.40.0 0.0.0.255 10.10.20.0 0.0.0.255 established
 deny ip any any
exit
interface vlan 40
 ip access-group ACL_DIS_IN in
exit
end
write memory
```

### 3.5 ACL for MGMT (VLAN 99)
```
enable
configure terminal
ip access-list extended ACL_MGMT_IN
 permit tcp 10.99.99.0 0.0.0.255 10.10.10.0 0.0.0.255 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.10.20.0 0.0.0.255 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.10.30.0 0.0.0.255 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.10.40.0 0.0.0.255 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.0.0 0.0.0.3 eq 22
 permit tcp 10.99.99.0 0.0.0.255 10.0.1.0 0.0.0.3 eq 22
 permit ip 10.99.99.0 0.0.0.255 10.99.99.0 0.0.0.255
 deny ip any any
exit
interface vlan 99
 ip access-group ACL_MGMT_IN in
exit
end
write memory
```

---

## 4. Why This Works Better

1. **No Data on MGMT VLAN**: Data traffic stays on its own VLAN (10, 20, 30) all the way up to SW-Core. It never touches VLAN 99.
2. **Clean ACL Application**: Because data traffic never touches VLAN 99, `ACL_MGMT_IN` won't accidentally block it.
3. **OSPF Simplicity**: OSPF only needs to run on SW-Core and R-CORE. Distribution switches don't need OSPF.
4. **Matches Spec**: The project spec emphasizes separating management traffic from user traffic.

---

## 5. 4×4 Reachability Test Matrix

| From ↓ \ To → | DEIE | DCEE | DMME | DIS |
|----------------|:----:|:----:|:----:|:---:|
| **DEIE** | — | ❌ | ❌ | ✅ |
| **DCEE** | ❌ | — | ❌ | ❌ (ICMP) |
| **DMME** | ❌ | ❌ | — | ❌ |
| **DIS** | ✅ | ❌ | ❌ | — |

For each cell run `ping` and `traceroute`. Screenshot every result.
