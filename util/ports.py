from serial.tools import list_ports
import re

def print_ports():
    ports = list_ports.comports()
    for port, desc, hwid in sorted(ports):
        print("{}: {} [{}]".format(port, desc, hwid))

def find_port(serial_num):
    '''
    finds port handle with given hardware serial number
    '''
    ports = list_ports.comports()
    target_port = None
    for port, desc, hwid in sorted(ports):
        sn = re.findall('SER=(\w+)', hwid)
        if sn:
            if sn[0] == serial_num:
                target_port = port
                break
    if target_port is None:
        raise Exception('Serial number %s not found!'%serial_num)
    else:
        return target_port
