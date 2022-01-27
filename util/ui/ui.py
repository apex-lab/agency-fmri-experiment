from psychopy import visual
from time import time, sleep
import numpy as np

from psychopy.hardware.keyboard import Keyboard
from psychtoolbox import hid
from .cedrus import RBx20

# fix psychtoolbox issue for older versions of psychopy
import ctypes
xlib = ctypes.cdll.LoadLibrary("libX11.so")
xlib.XInitThreads()

# placeholders to be replaced in the main script
def on_trial_start():
    return None
def on_stimulate():
    return None

def get_keyboard(dev_name):
    devs = hid.get_keyboard_indices()
    idxs = devs[0]
    names = devs[1]
    try:
        idx = [idxs[i] for i, nm in enumerate(names) if nm == dev_name][0]
    except:
        raise Exception(
    'Cannot find %s! Available devices are %s.'%(dev_name, ', '.join(names))
        )
    return Keyboard(idx)

class EventHandler:

    def __init__(self, is_test = False, **win_kwargs):

        self.is_test = is_test

        self.input = RBx20()
        self.kb = get_keyboard('Dell Dell USB Entry Keyboard')
        self.win = visual.Window(**win_kwargs)

        # placeholder callables to be replaced in the main script
        self.on_trial_start = on_trial_start # code to send trigger
        self.on_stimulate = on_stimulate # code to apply stimulation / trigger

        # just for communication between methods
        self.rt = None
        self.pressed_first = None

    def waitPress(self):
        '''
        waits for subject to press response box
        '''
        if self.is_test:
            sleep(.1)
        else:
            self.input.waitPress()

    def _get_rt(self, stimulation = None):
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

    def get_rt(self, stimulation = None):
        self.on_trial_start() # should send trigger to EEG amp
        if self.is_test:
            fake_rt = np.random.uniform(.2, .4)
            sleep(fake_rt)
            self.rt = fake_rt
            self.pressed_first = False
            return fake_rt, False
        else:
            return self._get_rt(stimulation)

    def rt_trial(self, stimulation = None):

        # prepare "go" cue for subject
        rect = visual.Rect(self.win, width = 2, height = 2, fillColor = "white")
        msg = visual.TextStim(
            self.win,
            text = "Go!",
            color = "black",
            pos = (0, 0)
        )
        rect.draw()
        msg.draw()

        # begin trial on next screen flip
        if stimulation is None:
            self.win.callOnFlip(self.get_rt)
        else:
            self.win.callOnFlip(self.get_rt, stimulation * 1e3)
        self.win.flip()

        # remove text from screen to provide feedback that press was registered
        rect = visual.Rect(self.win, width = 2, height = 2, color = "black")
        rect.draw()
        self.win.flip()

        # retrieve would-be return values of .get_rt()
        rt = self.rt
        pressed_first = self.pressed_first
        if rt < .5: # just to keep the trial length somewhat consistent
            sleep(.5 - rt)
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
        sleep(wait_secs)

    def get_response(self):
        self.display('Did you cause the movement?')
        if self.is_test:
            sleep(.2)
            return np.random.choice([0, 1])
        else:
            key = self.kb.waitKeys(keyList = ['b', 'm'])
            if key.name == 'b':
                return 1
            else:
                return 0
