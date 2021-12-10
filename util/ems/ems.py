from .ems_interface.tools_and_abstractions import SerialThingy
from .ems_interface.modules import singlepulse
from ..ports import find_port

SERIAL_NUMBER = 'HMYID101'
port = find_port(SERIAL_NUMBER)
serial_response_active = False

class EMS:

    def __init__(self, fake = False):
        self.ems = SerialThingy.SerialThingy(fake)
        self.ems.open_port(port, serial_response_active)

    def pulse(self, intensity, channel = 1, width = 400):
        self.ems.write(singlepulse.generate(channel, width, intensity))

    def close(self):
        self.ems.ser.close()

    def __del__(self):
        self.close()
