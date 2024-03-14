import sys
import struct
import wrapper
from wrapper import recv_from_any_link, send_to_link

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])

    # Convert MAC addresses to human-readable format
    dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
    src_mac = ':'.join(f'{b:02x}' for b in src_mac)

    # ethertype is already in correct format (2-byte integer)

    return dest_mac, src_mac, ethertype


def main():

    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    interfaces = range(0, wrapper.init() + 1)

    while True:
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype = parse_ethernet_header(data)

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')
        print("Received frame of size {} on interface {}".format(length, interface))

        # TODO: For each other port/interface
        # TODO: Send the data using send_to_any_link


if __name__ == "__main__":
    main()
