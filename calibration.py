from util.ems import EMS
from time import sleep
import numpy as np
from util.ui.ui import get_keyboard

stimulator = EMS()
kb = get_keyboard('DELL DELL USB Keyboard')

n_tries = 10 # per level
stim_level = None
for level in np.arange(1, 25):
    print('\nTesting intensity level %d mA...'%level)
    successes = 0
    for i in range(n_tries):
        sleep(np.random.random()) # so subject can't anticipate timing
        # check if we can elicit a button press
        kb.clearEvents() # clear buffer
        stimulator.pulse(intensity = level)
        key = kb.waitKeys(maxWait = .5, waitRelease = False, keyList = ['space'])
        if not key is None:
            successes += 1
    print('%d/%d attempts succesful at level %d.'%(successes, n_tries, level))
    if successes == n_tries: # if we can consistently get a press...
        stim_level = level   # then that's the intensity we'll use.
        break
if stim_level is None:
    raise Exception('Could not calibrate stimulator!')
else:
    print('Stimulation level set to %d'%stim_level)
