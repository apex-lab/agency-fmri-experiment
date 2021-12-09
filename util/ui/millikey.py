from psychopy import core
from psychopy.hardware.keyboard import Keyboard
from psychtoolbox import hid
import platform
import warnings

def catch_windows():
    if platform.system() != 'Windows':
        return False
    warnings.warn(
    '''
    PsychHID driver can only distinguish different keyboards on Linux/Mac.
    Defaulting to treat all input devices as a unified keyboard!
    '''
    )
    return True

class MilliKey:
    '''
    A wrapper intended for LabHackers MilliKey, though it would really work for
    any USB Keyboard if its name is specified on init (or many button boxes).

    The MilliKey will give you precise timing, though, and a keyboard won't.
    '''
    def __init__(self, dev_name = 'LabHackers MilliKey'):
        '''
        Initializes the specified input device using PsychToolBox 3's PsychHID
        backend, which bypasses operating systems' standard keyboard
        APIs, instead using event sniffing to detect keypress events.

        If you're using a keyboard, your timing will still be imperfect due to
        jitter introduced by the keyboard harware, but it will be better, and
        if you use a USB Button Box, like the MilliKey, you'll likely get
        millisecond latencies and negligible jitter. See:
        https://blog.labhackers.com/?p=285
        '''
        Keyboard.backend = 'ptb' # specify PsychHID backend
        self.rt_clock = core.Clock()
        if catch_windows() or dev_name is None:
            self.kb = Keyboard(clock = self.rt_clock)
        else:
            self.kb = self._get_device(dev_name)
        # check to make sure psychopy didn't switch backends upon init,
        assert(Keyboard.backend == 'ptb') # e.g. if PTB isn't installed

    def _get_device(self, dev_name):
        '''
        this will likely only work on linux and mac
        '''
        devs = hid.get_keyboard_indices()
        idxs = devs[0]
        names = devs[1]
        try:
            idx = [idxs[i] for i, nm in enumerate(names) if nm == dev_name][0]
        except:
            raise Exception(
        'Cannot find %s! Available devices are %s.'%(dev_name, ', '.join(names))
            )
        return Keyboard(idx, clock = self.rt_clock)

    def reset(self):
        '''
        resets reaction time clock and flushes keypress buffer
        '''
        self.rt_clock.reset()
        self.kb.clearEvents()

    def waitPress(self, timeout = float('inf'), reset = True):
        '''
        waits for next button press or until timeout

        timeout (float): in seconds

        Returns:
            (key pressed, response time) if didn't time out;
            if timed out, returns (None, None)

            Response time is relative to last rt_clock reset and is stamped
            asyncronously to the experiment process, so it will be accurate
            even if you stop actively polling to do something else.
        '''
        if reset:
            self.reset()
        key = self.kb.waitKeys(
            maxWait = timeout,
            waitRelease = False,
            clear = False # we instead flush buffer in .reset()
        )
        if key is None: # no response before timeout
            return None, None
        else:
            return key[0].name, key[0].rt
