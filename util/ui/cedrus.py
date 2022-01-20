from serial import Serial
from psychopy import core
from ..ports import find_port

class RBx20:
    '''
    wrapper for Cedrus RB-x20 Response Box

    Expects box to be set to ascii protocol (switch 1 in down position
    and switch 2 up). Will throw likely throw error otherwise.

    Last two switches control the baud rate. Make sure hardware and software
    baud rates (as set in __init__) match. If switches 3 & 4 are both down,
    the baud rate is 19200.
    '''
    def __init__(self, serial_num = 'FTCGRG4Q', baudrate = 19200):
        self.port = find_port(serial_num)
        self.ser = Serial(self.port, baudrate = baudrate)
        self.rt_clock = core.Clock()

    def reset(self):
        '''
        Flushes the input buffer and resets the reaction time clock.
        '''
        self.rt_clock.reset()
        self.ser.reset_input_buffer() # flush

    def waitKeys(self, timeout = None, reset = True):
        '''
        Returns key pressed and reaction time (relative to last reset)
        or None, None if times out
        '''
        if reset:
            self.reset()
        self.ser.timeout = timeout # None is no timeout
        press = self.ser.read(1)
        rt = self.rt_clock.getTime()
        if press == b'':
            return None, None
        key = int(press) # ascii character to key number
        return key, rt

    def waitPress(self, **kwargs):
        key, rt = self.waitKeys(**kwargs)
        return key, rt

    def getNext(self):
        '''
        returns whatever is next in the buffer, or None, None if nothing
        '''
        key, rt = self.waitKeys(timeout = 0, reset = False)
        return key, rt

    def close(self):
        self.ser.close()

    def __del__(self):
        self.close()


class CedrusButtonBox:
    '''
    utility class for cedrus response box version >= RB-x30

    In theory, timing should be a bit better than the RBx20 class
    since timestamps are assigned asyncronously onboard the box.

    This hasn't actually been tested, since I wrote it not realizing my
    RB-620 button box didn't use the same XID protocol as the newer boxes.
    It's here in case it helps anyone ¯\_(ツ)_/¯
    '''
    def __init__(self):
        from pyxid2 import get_xid_devices
        devices = get_xid_devices()
        assert(devices[0].is_response_device())
        self.dev = devices[0] # assume there's only one
        self.dev.reset_base_timer()
        self.reset()

    def reset(self):
        '''
        resets reaction time clock and flushes input buffer
        '''
        self.dev.reset_rt_timer()
        self.dev.clear_response_queue()

    def waitPress(self, timeout = float('inf'), reset = True):
        '''
        waits for next button press or until timeout

        timeout (float): in seconds

        Returns:
            (key pressed, response time) if didn't time out;
            if timed out, returns (None, None)
        '''
        if reset:
            self.reset()
        t0 = time()
        while not self.dev.has_response():
            self.dev.poll_for_response()
            if time() > t0 + timeout:
                return None, None
        resp = dev.get_next_response()
        return resp['key'], resp['time']
