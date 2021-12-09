from psychopy import visual, event, core
from psychopy.hardware.keyboard import Keyboard
from time import time, sleep
import numpy as np
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


class CedrusButtonBox:
    '''
    utility class for cedrus response box version >= RB-x30

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

# placeholders to be replaced in the main script
def on_trial_start():
    return None
def on_stimulate():
    return None

class EventHandler:

    def __init__(self, **win_kwargs):

        self.win = Window(**win_kwargs)
        self.input = MilliKey(dev_name = None)

        # placeholder callables to be replaced in the main script
        self.on_trial_start = on_trial_start # code to send trigger
        self.on_stimulate = on_stimulate # code to apply stimulation / trigger

        # just for communication between methods
        self.rt = None
        self.pressed_first = None

    def get_rt(self, stimulation = None):
        '''
        Collects reaction times

        If stimulation latency (in seconds) is provided, will
        stimulate either at given latency or immediately after
        subject's natural response is detected via the input device

        Returns RT (ms) and whether subject pressed before stimulation
        is triggered.

        Very first thing it does (even before sending trigger to EEG)
        is zero the RT clock for the button box, since we can correct the
        onset time with the photocell but we can't get correct RT post-hoc.
        '''
        self.input.reset()
        self.on_trial_start() # should send trigger to EEG amp
        if stimulation is None:
            key, rt = self.input.waitPress(reset = False)
            self.rt = rt
            self.pressed_first = True
            return rt * 1e3, True
        key, rt = self.input.waitPress(timeout = stimulation, reset = False)
        self.on_stimulate() # should apply a pulse and send trigger to amp
        if key is None: # once stimulated, resume waiting for press
            key, rt = self.input.waitPress(reset = False)
            pressed_first = True
        else:
            pressed_first = False
        # store in class before returning for when call on flip
        self.rt = rt # and therefore can't see return values
        self.pressed_first = pressed_first
        return rt * 1e3, pressed_first

    def rt_trial(self, stimulation = None):

        # prepare "go" cue for subject
        rect = visual.Rect(self.win, width = 2, height = 2, color = "white")
        msg = visual.TextStim(
            self.win,
            text = "Go!",
            color = "black",
            pos = (0, 0)
        )
        rect.draw()
        msg.draw()

        # begin trial on next screen flip
        win.callOnFlip(self.get_rt, stimulation * 1e3)
        win.flip()

        # remove text from screen to provide feedback that press was registered
        rect = visual.Rect(self.win, width = 2, height = 2, color = "black")
        rect.draw()
        win.flip()
        if rt < .5: # just to keep the trial length somewhat consistent
            sleep(.5 - rt)

        # retrieve would-be return values of .get_rt()
        rt = self.rt
        pressed_first = self.pressed_first
        return rt, pressed_first

    def display(self, text):
        '''
        Displays text on the screen with a dark background.
        '''
        background = visual.Rect(
            self.win,
            width = 2, height = 2,
            color = "black"
        )
        msg = visual.TextStim(
            self.win,
            text = text,
            color = "white",
            pos = (0,0)
        )
        background.draw()
        msg.draw()
        self.win.flip()

    def fixation_cross(self, wait_secs):
        '''
        displays a fixation cross and then waits wait_secs seconds
        '''
        self.display('+')
        sleep(t)

    def get_response(self):
        self.display('Did you cause the movement?')
