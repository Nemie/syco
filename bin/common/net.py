#!/usr/bin/env python
'''
Network related functions.

'''

__author__ = "daniel.lindh@cybercow.se"
__copyright__ = "Copyright 2011, The System Console project"
__maintainer__ = "Daniel Lindh"
__email__ = "syco@cybercow.se"
__credits__ = ["???"]
__license__ = "???"
__version__ = "1.0.0"
__status__ = "Production"

import os
import fcntl
import array
import struct
import socket
import platform

def get_all_interfaces():
    """
    Used to get a list of the up interfaces and associated IP addresses
    on this machine (linux only).

    Returns:
        Dictionary where key is the interface name, and value is the ip.
    """
    SIOCGIFCONF = 0x8912
    MAXBYTES = 8096

    arch = platform.architecture()[0]

    # I really don't know what to call these right now
    var1 = -1
    var2 = -1
    if arch == '32bit':
        var1 = 32
        var2 = 32
    elif arch == '64bit':
        var1 = 16
        var2 = 40
    else:
        raise OSError("Unknown architecture: %s" % arch)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', '\0' * MAXBYTES)
    outbytes = struct.unpack('iL', fcntl.ioctl(
        sock.fileno(),
        SIOCGIFCONF,
        struct.pack('iL', MAXBYTES, names.buffer_info()[0])
        ))[0]

    namestr = names.tostring()
    ret = {}
    for i in xrange(0, outbytes, var2):
        ret[namestr[i:i+var1].split('\0', 1)[0]] = socket.inet_ntoa(namestr[i+20:i+24])

    return ret  

def get_interface_ip(ifname):
    '''
    Get ip from a specific interface.

    Example:
    ip = get_interface_ip("eth0")

    '''
    interfaces = get_all_interfaces()
    if ifname in interfaces:
        return interfaces[ifname]
    else:
        return None;

# Cache variable for lan_ip
lan_ip = ""

def get_lan_ip():
    '''
    Get one of the external ips on the computer.

    Prioritize ips from interface in the following orders
    "br0", "bond0", "br1", "bond1", "eth0", "eth1", "eth2", "eth3"

    '''
    global lan_ip
    if (lan_ip==""):
        try:
            lan_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            pass

        if lan_ip == "" or (lan_ip.startswith("127.") and os.name != "nt"):
            interfaces = ["br0", "bond0", "br1", "bond1", 
                          "eth0", "eth1", "eth2", "eth3"]

            interface_list = get_all_interfaces()
            for ifname in interfaces:            
                if ifname in interface_list:
                   lan_ip = interface_list[ifname]
                   break

    return lan_ip

def reverse_ip(str):
    '''Reverse an ip from 1.2.3.4 to 4.3.2.1'''
    reverse_str=""
    for num in str.split("."):
        if (reverse_str):
            reverse_str = "." + reverse_str
        reverse_str = num + reverse_str
    return reverse_str

def get_ip_class_c(ip):
    '''Get a class c net from an ip. 1.2.3.4 will return 1.2.3'''
    new_ip = ""
    split_ip = ip.split(".")
    for i in range(3):
        if (new_ip):
            new_ip += "."
        new_ip = new_ip + split_ip[i]

    return new_ip 

def num_of_eth_interfaces():
    counter = 0
    interface_list = get_all_interfaces()
    for ifname in interface_list:
        if "eth" in ifname:
            counter += 1
    return counter

def get_host_name():
    return os.uname()[1]
    
if (__name__ == "__main__"):
    print "get_all_interfaces " + str(get_all_interfaces())
    print "get_interface_ip " + get_interface_ip("eth0")
    print "get_lan_ip " + get_lan_ip()
    print "reverse_ip " + reverse_ip("1.2.3.4")
    print "get_ip_class_c " + get_ip_class_c("1.2.3.4")
    print "num_of_eth_interfaces " + str(num_of_eth_interfaces())
    print "get_host_name " + get_host_name()