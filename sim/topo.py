#!/usr/bin/python3

import time
import sys
import signal
import threading

from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.util import dumpNodeConnections


N_HOSTS = 4
LOGFILE = "/tmp/debug.txt"

BASE_FORMATS = {
        "host_name": "host{}",
        "hub_if_name": "r-{}",
        "host_if_name": "h-{}",
        "hub_ip": "192.168.1.{}",
        "host_ip": "192.168.1.{}",
        "hub_ip6": "fec0::{:x}:1",
        "hub_llip6": "fe80::{:x}:1",
        "host_ip6": "fd00::{:x}:2",
        "host_llip6": "fe80::{:x}:2",
        "hub_mac": "DE:FE:C8:ED:00:{:02x}",
        "host_mac": "DE:AD:BE:EF:00:{:02x}",
}


def get(value, host):
    return BASE_FORMATS[value].format(host)

class SinglehubTopo(Topo):
    "Single hub connected to n hosts."
    def build(self, n=2):
        hub = self.addHost('hub', ip=None)
        # Python's range(N) generates 0..N-1
        for h in range(n):
            host = self.addHost(get("host_name", h), ip=None)
            i1 = get("host_if_name", h)
            i2 = get("hub_if_name", h)
            self.addLink(host, hub, intfName1=i1, intfName2=i2)


class NetworkManager(object):
    def __init__(self, net, n_hosts):
        self.net = net
        self.hub = self.net.get("hub")
        self.hosts = []
        for i in range(n_hosts):
            h = self.net.get(get("host_name", i))
            self.hosts.append(h)

    def setup_ifaces(self):
        for i in range(len(self.hosts)):


            host_ip = get("host_ip", i)
            host_ip6 = get("host_ip6", i)
            host_llip6 = get("host_ip6", i)
            h_if = get("host_if_name", i)

            self.hosts[i].setIP(host_ip, prefixLen=24, intf=h_if)
            self.hub.setIP(get("hub_ip", 10 + i), prefixLen=24,
                              intf=get("hub_if_name", i))


    def setup_macs(self):
        for i, host in enumerate(self.hosts):
            h_mac = get("host_mac", i)
            h_if = get("host_if_name", i)
            host.cmd("ifconfig {} hw ether {}".format(h_if, h_mac))

            r_mac = get("hub_mac", i)
            r_if = get("hub_if_name", i)
            self.hub.cmd("ifconfig {} hw ether {}".format(r_if, r_mac))

    def disable_unneeded(self):
        def disable_ipv6_autoconf(host):
            host.cmd("sysctl -w net.ipv6.conf.all.autoconf=0")
            host.cmd("sysctl -w net.ipv6.conf.all.accept_ra=0")

        def disable_ipv6(host):
            host.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1')
            host.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1')

        def disable_nic_checksum(host, iface):
            host.cmd('ethtool iface {} --offload rx off tx off'.format(iface))
            host.cmd('ethtool -K {} tx-checksum-ip-generic off'.format(iface))

        def disable_arp(host, iface):
            host.cmd("ip link set dev {} arp off".format(iface))

        disable_ipv6_autoconf(self.hub)
        disable_ipv6(self.hub)

        for i, host in enumerate(self.hosts):
            h_if = get("host_if_name", i)
            r_if = get("hub_if_name", i)

            disable_ipv6_autoconf(host)
            disable_ipv6(host)

            disable_nic_checksum(host, h_if)
            disable_nic_checksum(self.hub, h_if)

            disable_arp(host, h_if)
            disable_arp(self.hub, h_if)

        # we want complete control over these actions
        self.hub.cmd('sysctl -w net.ipv4.ip_forward=0')
        self.hub.cmd('sysctl -w net.ipv4.icmp_echo_ignore_all=1')

    def add_default_routes(self):
        for i, host in enumerate(self.hosts):
            ip = get("hub_ip", i)
            ip6 = get("hub_llip6", i)
            h_if = get("host_if_name", i)

            host.cmd("ip -4 route add default via {} dev {}".format(ip, h_if))
            host.cmd("ip -6 route add default via {} dev {}".format(ip6, h_if))

    def setup(self):
        self.disable_unneeded()
        self.setup_ifaces()
        self.setup_macs()
        self.add_default_routes()

        for i in range(len(self.hosts)):
            for j in range(len(self.hosts)):
                if j != i:
                    h_mac = get("host_mac", j)
                    h_ip = get("host_ip", j)
                    self.hosts[i].cmd("arp -s {} {}".format(h_ip, h_mac))

def signal_handler(signal, frame):
    sys.exit(0)

def main():
    topo = SinglehubTopo(n=N_HOSTS)

    net = Mininet(topo, controller=None)
    net.start()

    nm = NetworkManager(net, N_HOSTS)
    nm.setup()

    net.startTerms()
    signal.signal(signal.SIGINT, signal_handler)
    forever = threading.Event()
    forever.wait()

    net.stop()

topos = { "mytopo": (lambda : SinglehubTopo()) }


if __name__ == "__main__":
    # Tell mininet to print useful information
    setLogLevel("info")
    main()

