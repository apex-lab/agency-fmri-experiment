from .ems_interface.tools_and_abstractions import SerialThingy
from .ems_interface.modules import singlepulse
from ..ports import find_port

SERIAL_NUMBER = 'HMYID101'
serial_response_active = False

class EMS:

    def __init__(self, fake = False):
        if fake:
            port = ''
        else:
            port = find_port(SERIAL_NUMBER)
        self.is_fake = fake
        self.ems = SerialThingy.SerialThingy(fake)
        self.ems.open_port(port, serial_response_active)

    def pulse(self, intensity, channel = 1, width = 200, repetitions = 3):
        one_pulse = singlepulse.generate(channel, width, intensity)
        for i in range(repetitions):
            self.ems.write(one_pulse)

    def close(self):
        if not self.is_fake:
            self.ems.ser.close()

    def __del__(self):
        self.close()
