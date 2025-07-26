---
date: 2025-07-26
categories:
  - homelab
authors:
  - silk
tags:
  - homelab
comments: true
---

# Proxmox Complete Microsegmentation with OPNsense

## Goal

The goal state for this setup is:

- OPNsense acts as a core firewall and regulates access between all VMs.
- All VMs share the same bridge interface to reduce setup needed for each VM.
- VMs cannot spoof their IP address or MAC address to circumvent firewall controls.

pfSense will likely work with this setup as well, but was not tested.

## Overview

To achieve the goal, we:

- Create a bridge interface in Proxmox that all VMs (including the OPNsense VM) will share.
- Using `ebtables`, block traffic on the bridge at Layer 2 unless to/from the OPNsense VM.
- With Layer 2 traffic between the VMs blocked, there are no ARP replies for VM IP addresses. To solve this, we enable Proxy ARP in OPNsense.
- Using Proxmox's built-in firewall, we enable the IP and MAC filter options to resolve IP and MAC spoofing.

## 0. Decide the VM subnet

This guide will assume `10.10.10.0/24` as the subnet for the VMs with `10.10.10.1` as the OPNsense gateway.

## 1. Enable Firewall Settings on the Datacenter

The firewall needs to be enabled at the Datacenter level and the VM level. Enabling the firewall on the node is not required.

1. Navigate to **Datacenter > Firewall > Options**.
2. Change **Firewall** to **Yes**.

## 2. Create the Proxmox Bridge Interface

Add the interface on your Proxmox node.

1. Navigate to **Your Node > System > Network**.
2. Click **Create > Linux Bridge**.
3. Type your interface name. This documentation will use `vmbr1`.
4. Leave all other fields as default (IP/CIDRs blank, VLAN aware off, no bridge ports).
5. Click **Create**.

## 3. Add and configure the interface to OPNsense

This guide will not go into details on how to add the interface to OPNsense (I forgot exactly how I did it, and I don't feel like redoing it), however the key points are:

- Add the interface as a LAN interface.
- Do not enable the Proxmox Firewall on the OPNsense VM.
- Do not specify a VLAN tag in Proxmox.

**Important:** Proxy ARP must be enabled on the interface in OPNsense. This is required as we are going to block Layer-2 traffic between the VMs, and so OPNsense must advertise its MAC address as owning all IPs in the subnet.

1. Navigate to **Interfaces > Virtual IPs > Settings**.
2. Click the **+** (Add) button.
3. For **Mode**, select **Proxy ARP**.
4. For **Interface**, select the added LAN interface.
5. For **Network / Address**, input `10.10.10.0/24` (or your subnet).
6. Click **Save**.

For testing purposes, a rule to allow pinging the gateway from all sources on the LAN interface was added.

## 4. Configure the Proxmox Bridge Interface

SSH into the Proxmox node to conduct some advanced configuration of the bridge interface.

Run `brctl show vmbr1` to see the interfaces attached to the bridge (replace `vmbr1` with your bridge). Example output:

```
root@yournode:~# brctl show vmbr1
bridge name     bridge id               STP enabled     interfaces
vmbr1           8000.624b81ab2fd5       no              tap101i1
```

Here we can see `tap101i` is the interface used by the OPNsense VM that is attached to the `vmbr1` bridge.

Now we can configure the interface to only allow traffic from VMs to OPNsense and vice-versa using ebtables. No traffic allowed between other VMs.

1. Run this command: `nano /etc/network/interfaces`
2. Add `post-up` and `post-down` lines to the `vmbr1` interface, such that the configuration looks like this (swap `vmbr1` for your bridge and `tap101i1` for your OPNsense VM interface):
   ```
   ...
   auto vmbr1
   iface vmbr1 inet static
           bridge-ports none
           bridge-stp off
           bridge-fd 0
           post-up   ebtables -A FORWARD --logical-in vmbr1 -o tap101i1 -j ACCEPT
           post-up   ebtables -A FORWARD -i tap101i1 --logical-out vmbr1 -j ACCEPT
           post-up   ebtables -A FORWARD --logical-in vmbr1 --logical-out vmbr1 -j DROP
           post-down ebtables -D FORWARD --logical-in vmbr1 -o tap101i1 -j ACCEPT
           post-down ebtables -D FORWARD -i tap101i1 --logical-out vmbr1 -j ACCEPT
           post-down ebtables -D FORWARD --logical-in vmbr1 --logical-out vmbr1 -j DROP
   #LAN Microsegmented
   ...
   ```
3. Apply the network interface changes with this command: `ifreload -a`

## 5. Setup a VM

This guide will not go into details of the VM setup, except related specifically to networking. Key points inside the VM (or Cloud-Init) are:

- Configure your VM's IP/CIDR to the desired IP and subnet (i.e. `10.10.10.3/24`).
- Configure your VM's gateway to the OPNsense VM's IP (i.e. `10.10.10.1`).

In the Proxmox interface:

1. Add `vmbr1` (or your bridge) to your VM as a network device. Ensure the `Firewall` option is checked.
2. Navigate to `Your VM > Firewall > Options`.
3. Set `Firewall` to `Yes`.
4. Set `DHCP` to `No`.
5. Set `MAC filter` to `Yes`.
6. Set `IP filter` to `Yes`.
7. Set `Input Policy` to `ACCEPT` (input firewall rules will be configured in OPNsense).
8. Set `Output Policy` to `ACCEPT` (output firewall rules will be configured in OPNsense).

In addition to these Firewall options, we need to make Proxmox aware of the VM's intended IP address so the `IP filter` setting will behave properly.

1. Navigate to `Your VM > Firewall > IPSet`.
2. Click `Create`.
3. For `Name`, enter `ipfilter-net0`.
4. Click `OK`.
5. Click `Add` (top-right of interface).
6. Enter the VM's IP address (i.e. `10.10.10.3`).
7. Reboot the VM.

Repeat this testing for a second VM to test inter-VM connectivity.

## 6. Testing

### 6.1 Inter-VM Connectivity

To test inter-VM connectivity:

1. From one VM, attempt to ping the other VM (this should fail/timeout): `ping 10.10.10.4`
2. In OPNsense interface, add a firewall rule that allows ICMP from `10.10.10.3` to `10.10.10.4`.
3. Attempt to ping the other VM again (this should succeed): `ping 10.10.10.4`

### 6.2. VM IP Spoofing

Testing IP-spoofing (on an Ubuntu VM):

```sh
# Attempt to ping other VM (should succeed)
ping 10.10.10.4

# Change IP address to one not defined in VM's IPSet
nano /etc/netplan/50-cloud-init.yaml
netplan apply

# Attempt to ping other VM (should fail)
ping 10.10.10.4
```

### 6.3. VM MAC Spoofing

Test MAC-spoofing (on an Ubuntu VM):

```sh
# Attempt to ping other VM (should succeed)
ping 10.10.10.4

# Change MAC address to one not defined on VM's interface.
# This can be done by adding a line to the interface's configuration.
#     match:
#         macaddress: 01:23:45:67:89:ab
# +   macaddress: de:de:de:de:de:de # added line, spoofed mac address
nano /net/netplan/50-cloud-init.yaml
netplan apply

# Attempt to ping other VM (should fail)
ping 10.10.10.4
```


In order to revert the spoofed changes, you may need to populate the original MAC address in both locations in the configuration, prior to restoring the original configuration:

```yaml
match:
    macaddress: 01:23:45:67:89:ab
macaddress: 01:23:45:67:89:ab
```

Restore unspoofed MAC address:
```sh
netplan apply
```

Restore the original configuration:
```yaml
match:
    macaddress: 01:23:45:67:89:ab
# no second macaddress line
```

Apply changes for the last time:
```sh
netplan apply
```

## Done

Now you should have VM-level/complete microsegmentation setup. Enjoy the cloud-like control to your heart's content.

If you find any issues/comments with this setup, or a method to bypass the firewall controls, feel free to contact me.