from psychopy import visual
from time import time, sleep
import numpy as np

from psychopy.hardware.keyboard import Keyboard
from psychtoolbox import hid

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

    def __init__(self, rt_key = 'space', kb_name = 'Dell Dell USB Entry Keyboard',
                        is_test = False, **win_kwargs):

        self.is_test = is_test

        self.kb = get_keyboard(kb_name)
        self.win = visual.Window(**win_kwargs)

        # placeholder callables to be replaced in the main script
        self.on_trial_start = on_trial_start # code to send trigger
        self.on_stimulate = on_stimulate # code to apply stimulation / trigger

        # just for communication between methods
        self.rt = None
        self.pressed_first = None
        self.rt_key = rt_key

    def waitPress(self):
        '''
        waits for subject to press response box
        '''
        if self.is_test:
            sleep(.1)
        else:
            self.kb.waitKeys(keyList = [self.rt_key], clear = True)

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
        k = [self.rt_key] # the key used for RT measurements
        self.kb.clearEvents()
        self.kb.clock.reset()
        if stimulation is None:
            keys = self.kb.waitKeys(
                clear = False, waitRelease = False,
                keyList = k
                )
            self.rt = keys[0].rt
            self.pressed_first = True
            return self.rt, self.pressed_first
        keys = self.kb.waitKeys(
            clear = False, maxWait = stimulation,
            waitRelease = False, keyList = k
            )
        self.on_stimulate() # should apply a pulse and send trigger to amp
        if keys:
            pressed_first = True
        else:
            keys = self.kb.waitKeys(
                clear = False, waitRelease = False,
                keyList = k
                )
            pressed_first = False
        # store in class before returning for when call on flip
        self.rt = keys[0].rt # and therefore can't see return values
        self.pressed_first = pressed_first
        return self.rt, self.pressed_first

    def get_rt(self, stimulation = None):
        self.on_trial_start() # should send trigger to EEG amp
        if self.is_test:
            fake_rt = np.random.uniform(.2, .4)
            sleep(fake_rt)
            self.rt = fake_rt
            if stimulation is None:
                self.pressed_first = False
            else:
                self.pressed_first = (fake_rt < stimulation)
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
            self.win.callOnFlip(self.get_rt, stimulation * 1e-3)
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
        return (1e3 * rt), pressed_first

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
        self.display('Did you cause the button press?')
        if self.is_test:
            sleep(.2)
            return np.random.choice([0, 1])
        else:
            key = self.kb.waitKeys(keyList = ['b', 'm'])[0]
            if key.name == 'b':
                return 1
            elif key.name == 'm':
                return 0
            else:
                raise ValueError("that shouldn't have happened")
