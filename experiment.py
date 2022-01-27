from concurrent.futures import ThreadPoolExecutor, wait
from time import time, sleep
from sys import stdout
import numpy as np

from util.oed.logistic import LogisticOptimalDesign
from util.events import EventMarker
from util.ui import EventHandler
from util.write import TSVWriter
from util.ems import EMS

TEST_MODE = True

STIM_INTERVAL_START = 50 # in milliseconds relative to RT trial start
STIM_INTERVAL_END = 350

PRETEST_TRIALS = 50
STIMULATION_TRIALS = 250
POSTTEST_TRIALS = 50

# initialize helpers
marker = EventMarker()
stimulator = EMS(TEST_MODE)
subj_num = input("Enter subject number: ")
subj_num = int(subj_num)
intensity = input("Enter stimulation intensity: ")
intensity = float(intensity)
log = TSVWriter(subj_num)
ui = EventHandler(
	TEST_MODE,
	size = (1920, 1080),
	color = (-1, -1, -1),
	screen = -1,
	units = "norm",
	fullscr = False,
	pos = (0, 0),
	allowGUI = False
)
def on_trial_start(): # tell event handler how to send triggers
	marker.send(1)
ui.on_trial_start = on_trial_start

def on_stimulate():
	'''
	stimulation instructions for event handler
	'''
	channel = 1
	pulse_width = 400 # microseconds
	marker.send(2) # send trigger at same time
	stimulator._send_single_pulse(channel, pulse_width, intensity)
ui.on_stimulate = on_stimulate

# wait for experimenter to continue
input('\nPress enter to continue...')

## reaction time pretest
t0 = time()
print('\nBeginning pretest at 0 minutes.')
ui.display(
'''
You will now start the reaction time test. Please press
the button as quickly as possible when you see "Go!"
(press to continue)
'''
)
ui.waitPress()
pretest_rts = log.pretest_rts # pick up where left off

for trial in range(len(pretest_rts), PRETEST_TRIALS):
	# keep experimenter in the loop via console
	stdout.write("\rTrial {0:03d}".format(trial) + "/%d"%PRETEST_TRIALS)
	stdout.flush()

	# wait until subject is ready
	ui.display('Press button to begin trial.')
	ui.waitPress()

	# variable fixation (2-4 seconds) and then start trial
	ui.fixation_cross(2 + 2*np.random.random())
	rt, _ = ui.rt_trial() # cues movement and collects response time
	pretest_rts.append(rt)

	# record trial data to log file
	log.write('pretest', trial + 1, 0., -1., rt, True, True)

print('\nEnding pretest at %d minutes.'%((time() - t0)/60))


## initialize optimal experiment design object
des = LogisticOptimalDesign(
	# specify priors
	alpha_mean = np.mean(pretest_rts) - 80, # RT minus preemptive gain
	alpha_scale = np.std(pretest_rts) * 1.2, # add a little extra variability
	beta_mean = 0.017, # average slope from Kasahara et al. (2018)
	beta_scale = 0.005, # encompasses all observed values from Kasahara
	candidate_designs = np.arange(STIM_INTERVAL_START, STIM_INTERVAL_END)
)
executor = ThreadPoolExecutor(max_workers = 1) # for asyncronous model fitting
if len(log.xs) > 0: # pick up where left off if starting from the middle
	model_updated = executor.submit(des.update_model, log.xs, log.ys)

## now start stimulation trials
print('\nBeginning stimulation block at %d minutes.'%((time() - t0)/60))
ui.display(
'''
Now the muscle stimulator will try to help you press faster.
Still try to press the button as quickly as possible.
(press to continue)
'''
)
ui.waitPress()
ui.display(
'''
After each trial, you will be asked whether you or the
stimulator first caused your finger to move.
(press to continue)
'''
)
ui.waitPress()

for trial in range(len(log.xs), STIMULATION_TRIALS):
	stdout.write("\rTrial {0:03d}".format(trial) + "/%d"%STIMULATION_TRIALS)
	stdout.flush()
	ui.display('Press button to begin trial.')
	ui.waitPress()
	ui.fixation_cross(2 + 2*np.random.random())

	if trial != 0: # wait until model has finished updating from last trial
		wait([model_updated]) # though it should already be done by now

	# select next stimulation latency via Bayesian optimization
	stim_latency = des.get_next_x('bopt')
	rt, pf = ui.rt_trial(stimulation = stim_latency)

	# solicit subject's agency judgment
	resp = ui.get_response()
	# and use it to start updating the logistic model
	model_updated = executor.submit(des.update_model, stim_latency, resp)
	log.write('stimulation', trial + 1, intensity, stim_latency, rt, pf, resp)

print('\nEnding stimulation block at %d minutes.'%((time() - t0)/60))

## and finally the posttest
print('\nBeginning posttest at %d minutes.'%((time() - t0)/60))
ui.display(
'''
Almost done! You will do a final block of reaction
time testing without the help of the stimulator.
(press to continue)
'''
)
ui.waitPress()
for trial in range(log.n_posttest, POSTTEST_TRIALS):
	stdout.write("\rTrial {0:03d}".format(trial) + "/%d"%POSTTEST_TRIALS)
	stdout.flush()
	ui.display('Press button to begin trial.')
	ui.waitPress()
	ui.fixation_cross(2 + 2*np.random.random())
	rt, _ = ui.rt_trial()
	log.write('posttest', trial + 1, 0., -1., rt, True, True)
print('\nEnding posttest at %d minutes.'%((time() - t0)/60))


## clean up and end experiment
marker.close()
ui.display( # notify subject that experiment has ended
'''
You have completed the experiment!
The experimenter will be with you shortly.
'''
) # and notify experiment
print('Experiment has finished!')
Input('Press enter to end script...')
