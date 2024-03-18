#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def create_bdpu(length, root_prio, root_id, cost, sender_prio, sender_id):
    

    ssap = struct.pack('!H', 0x42)
    dst_mac = b'\x01\x80\xc2\x00\x00\x00'
    frame_length = struct.pack('!H', length)
    eth_header = dst_mac + get_switch_mac() + frame_length + b'\x42\x42\x03'
    pid = b'\x00\x00\x00\x00\x00' # 2b protocol id +  1b version id + 1b bdpu type + 1b flags
    
    bpdu_payload = pid + struct.pack('!b', root_prio) + b'\x00' + root_id + struct.pack('!I', cost) + struct.pack('!b', sender_prio) + b'\x00' + sender_id + b'\x80\x04\x01\x00\x14\x00\x02\x00\x0f\x00'

    bpdu_frame = eth_header + bpdu_payload
    return bpdu_frame

def parse_bdpu(data):
    return data[22:23], data[30:34], data[34:35]
own_bridge_ID = 0
root_bridge_ID = 0
def send_bdpu_every_sec(data, interfaces):
    while True:
        # TODO Send BDPU every second if necessary
        if(own_bridge_ID == root_bridge_ID):
            for port in interfaces:
                send_to_link(port, data, 60)
                time.sleep(1)

def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    vlan_ids = {}
    mac_table = {}
    ports_state = [None] * num_interfaces 
    file_path = "configs/switch" + switch_id + ".cfg"
    with open(file_path, 'r') as file:
        lines = file.readlines()
    switch_prio = int(lines[0].strip())
    for line in lines[1:]:
        split_line = line.strip().split()
        vlan_ids[split_line[0]] = split_line[1]
    vlan_ids = dict(zip(interfaces, list(vlan_ids.values())))
    trunk_ports = []
    for port in interfaces:
        if vlan_ids[port] == "T":
            ports_state[port] = 0
            trunk_ports.append(port)


    own_bridge_ID = switch_prio
    root_bridge_ID = own_bridge_ID
    root_path_cost = 0
    
    root_port = 0
    bdpu_data = create_bdpu(38, switch_prio, get_switch_mac(), root_path_cost, switch_prio, get_switch_mac())
    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec,args=(bdpu_data,trunk_ports))
    t.start()

    # Printing interface names

    for port in interfaces:
        if ports_state[port] != None:
            ports_state[port] = 1
    
    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        
        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        if ethertype != 38:
            # Print the MAC src and MAC dst in human readable format
            dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
            src_mac = ':'.join(f'{b:02x}' for b in src_mac)

            # Note. Adding a VLAN tag can be as easy as
            # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]


            if vlan_id == -1:
                vlan_id = vlan_ids[interface]
            
            mac_table[src_mac] = interface
            send_ports = []
            header_ports = []
            no_header_ports = []
            if dest_mac != "ff:ff:ff:ff":
                if dest_mac in mac_table:
                    send_ports.append(mac_table[dest_mac])
                else:
                    for port in interfaces:
                        if port != interface:
                            send_ports.append(port)
            else:
                for port in interfaces:
                    if port != interface:
                        send_ports.append(port)

            for port in send_ports:
                if ports_state[port] == 1 or ports_state[port] == None:
                    if vlan_ids[port] == vlan_ids[interface] and vlan_ids[interface] != "T":
                        no_header_ports.append(port)
                    if vlan_ids[port] == vlan_ids[interface] and vlan_ids[interface] == "T":
                        header_ports.append(port)
                    if vlan_ids[port] != "T" and vlan_ids[interface] == "T" and vlan_id == int(vlan_ids[port]):
                        no_header_ports.append(port)
                    if vlan_ids[port] == "T" and vlan_ids[interface] != "T":
                        header_ports.append(port)

            for port in header_ports:
                vlan_tag = create_vlan_tag(int(vlan_id))
                send_data = data[:12] + vlan_tag + data[12:]
                send_to_link(port, send_data, length + 4)
            for port in no_header_ports:
                if vlan_ids[port] != "T" and vlan_ids[interface] == "T":
                    send_data = data[0:12] + data[16:]
                    send_to_link(port, send_data, length - 4)
                else: 
                    send_to_link(port, data, length)

        else:
            BDPUroot_ID, BDPUsender_cost, BDPUsender_ID = parse_bdpu(data)
            BDPUroot_ID = int.from_bytes(BDPUroot_ID, byteorder='big')
            BDPUsender_ID = int.from_bytes(BDPUsender_ID, byteorder='big')
            BDPUsender_cost = int.from_bytes(BDPUsender_cost, byteorder='big')
            if BDPUroot_ID < root_bridge_ID:
                root_port =  interface
                root_bridge_ID = BDPUroot_ID
                root_path_cost = BDPUsender_cost + 10
                if ports_state[interface] == 0:
                    ports_state[interface] == 1
                for port in interfaces:
                    if ports_state[port] != None and port != interface:
                        create_bdpu(60, root_bridge_ID, get_switch_mac(), root_path_cost, own_bridge_ID, get_switch_mac())
            elif BDPUroot_ID == root_bridge_ID:
                    if interface == root_port and BDPUsender_cost + 10 < root_path_cost:
                        root_path_cost = BDPUsender_cost + 10
                    elif interface != root_port:
                            if BDPUsender_cost > root_path_cost:
                                ports_state[interface] = 1
            elif BDPUsender_ID == root_bridge_ID:
                ports_state[interface] = 0

if __name__ == "__main__":
    main()
