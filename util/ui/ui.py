from psychopy import visual
from time import time, sleep
import numpy as np
from .cedrus import RBx20
from .millikey import MilliKey

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
