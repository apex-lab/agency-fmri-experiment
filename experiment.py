from concurrent.futures import ThreadPoolExecutor, wait
from time import sleep
from warnings import warn
from sys import stdout
import numpy as np
import pandas as pd
import os

from util.oed.logistic import LogisticOptimalDesign
from util.ui import EventHandler
from util.logging import TSVLogger
from util.ems import EMS
from util.mri import TRSync
from psychopy import event, core

from time import perf_counter as time

## CONFIG ######################################################################

TEST_MODE = False

KB_NAME = 'PST Inc. Celeritas Dev'
RT_KEY = '9'

# range of stimulation times to consider
STIM_INTERVAL_START = 0 # in milliseconds relative to RT trial start
STIM_INTERVAL_END = 1000

# trial counts (per block)
BLOCK_DURATION = 60*10

MRI_EMULATED_KEY = 's' # key to be 'pressed' on keyboard every TR

## BLOCK DEFINITIONS #################################################################
def baseline_block(ui, log, run, tr_listener):

	t0 = time()
	print('\nBeginning baseline test.')
	if run == '01':
		ui.display(
		'''
		You will now start a reaction time test. Please press
		the button as quickly as possible when you see "Go!"
		(press to continue)
		'''
		)
		ui.waitPress()
	else:
		ui.display(
		'''
		You will now start an ordinary reaction time test,
		without the help of the muscle stimulator.
		It will be just like the block you did today.
		(press to continue)
		'''
		)
		ui.waitPress()
	ui.display(
	'''
	Please let the experimenter know if you have any questions.
	Otherwise, you may begin.
	(press to start)
	'''
	)
	ui.waitPress()
	ui.display(
	'''
	Waiting for MRI... starting momentarily!
	'''
	)
	print('\n\nWaiting for MRI!')
	tr_listener.wait_until_first_TR()

	clock = core.Clock()
	clock.reset()
	trial = 0
	while clock.getTime() < BLOCK_DURATION:
		
		trial += 1

		# wait until subject is ready
		ui.display('Press button to begin trial.')
		ui.waitPress()

		# variable fixation (2-4 seconds) and then start trial
		ui.fixation_cross(2 + 2*np.random.random())
		rt, _ = ui.rt_trial() # cues movement and collects response time

		# record trial data to log file
		log.write(
			trial_type = 'baseline',
			trial = trial,
			rt = rt,
			)

	print('\nEnding baseline block at %d minutes.'%((time() - t0)/60))
	return


def stimulation_block(ui, log, run, tr_listener, priors):

	## initialize optimal experiment design object
	des = LogisticOptimalDesign(
		candidate_designs = np.arange(STIM_INTERVAL_START, STIM_INTERVAL_END),
		**priors
	)
	executor = ThreadPoolExecutor(max_workers = 1) # for asyncronous model fitting

	## now start stimulation trials
	t0 = time()
	print('Displaying instructions...')
	if run == '02':
		ui.display(
		'''
		You have finished the first block. Please read the following
		instructions carefully, and let the experimenter know
		if you have any questions.
		(press to continue)
		'''
		)
		ui.waitPress()
		ui.display(
		'''
		Now, the muscle stimulator will also attempt to move your finger
		to press the button around the same time you are trying to press.
		(press to continue)
		'''
		)
		ui.waitPress()
		ui.display(
		'''
		Please continue trying to press the button (on your own) as
		quickly as possible. Sometimes the muscle stimulator will
		move your finger before you do, but you should try to beat it.
		(press to continue)
		'''
		)
		ui.waitPress()
		ui.display(
		'''
		After each trial, you will be asked whether you or the
		stimulator caused your finger to press the button.
		(press to continue)
		'''
		)
		ui.waitPress()
		ui.display(
		'''
		Please let the experimenter know if you have any questions.
		Otherwise, you may begin.
		(press to start)
		'''
		)
		ui.waitPress()
	else:
		ui.display(
		'''
		You will now complete another block of the reaction time task,
		once again competing with the muscle stimulator.
		(press to continue)
		'''
		)
		ui.waitPress()
		ui.display(
		'''
		The instructions are the same as before.
		If you have any questions, please ask.
		Otherwise, you may begin.
		(press to start)
		'''
		)
		ui.waitPress()
	ui.display(
	'''
	Waiting for MRI... starting momentarily!
	'''
	)
	print('\n\nWaiting for MRI!')
	tr_listener.wait_until_first_TR()
	print('\nBeginning stimulation block.')

	clock = core.Clock()
	clock.reset()
	trial = 0
	while clock.getTime() < BLOCK_DURATION:
		
		trial += 1
		
		ui.display('Press button to begin trial.')
		ui.waitPress()
		ui.fixation_cross(2 + 2*np.random.random())

		if trial > 1: # wait until model has finished updating from last trial
			wait([model_updated]) # though it should already be done by now

		# select next stimulation latency via Bayesian optimization
		params = des.get_param_estimates()
		stim_latency = des.get_next_x('bopt')
		rt, pf = ui.rt_trial(stimulation = stim_latency)

		# solicit subject's agency judgment
		resp = ui.get_response()
		# and use it to start updating the logistic model
		_resp = 1 if pf else resp # discount trials subjects actually caused press
		model_updated = executor.submit(des.update_model, stim_latency, _resp)
		log.write(
			trial_type = 'stimulation',
			trial = trial,
			intensity = intensity,
			latency = stim_latency,
			rt = rt,
			pressed_first = pf,
			agency = resp,
			**params
			)

	print('\nEnding stimulation block at %d minutes.'%((time() - t0)/60))
	return

def get_priors(sub, run, dir):
	'''
	constructs priors for Bayesian Optimization
	'''
	prev_run = '%02d'%(int(run) - 1)
	prev_run_f = os.path.join( # path to previous log file
		dir, 'sub-%s_run-%s_log-%s.tsv'%(sub, prev_run, 'beh')
		)
	df = pd.read_csv(prev_run_f, sep = '\t')
	if run == '02':
		pretest_rts = df.rt
		priors = dict(
			alpha_mean = np.mean(pretest_rts) - 40, # RT minus preemptive gain
			alpha_scale = np.std(pretest_rts),
			beta_mean = 0.017, # average slope from Kasahara et al. (2018)
			beta_scale = 0.005, # encompasses all observed values from Kasahara
		)
	else:
		# use posterior from last time, but add a bit of uncertainty
		priors = dict(
			alpha_mean = df.alpha_mean.iloc[-1],
			alpha_scale = df.alpha_scale.iloc[-1] * 1.5,
			beta_mean = df.beta_mean.iloc[-1],
			beta_scale = df.beta_scale.iloc[-1] * 1.5
		)
	return priors


if __name__ == '__main__':

	## set up muscle stimulator
	stimulator = EMS(TEST_MODE)
	if TEST_MODE:
		warn('Script started in test mode!')

	## get run params from experimenter
	subj_num = input("Enter subject number: ")
	sub = '%02d'%int(subj_num)
	run_num = int(input("Enter run number: "))
	assert(run_num > 0 & run_num < 10)
	run = '%02d'%int(run_num)
	intensity = input("Enter stimulation intensity: ")
	intensity = int(intensity)

	## set up log files
	ev_log = TSVLogger(sub, run, 'events', ['event', 'timestamp'])
	beh_log = TSVLogger(
		sub, run, 'beh',
		fields = [
			'trial_type', 'trial', 'intensity',
			'latency', 'rt', 'pressed_first',
			'agency', 'timestamp',
			'alpha_mean', 'alpha_scale',
			'alpha_mu', 'alpha_sigma',
			'beta_mean', 'beta_scale',
			'beta_mu', 'beta_sigma'
			]
		)

	tr_listener = TRSync(sub, run, KB_NAME, MRI_EMULATED_KEY)
	tr_listener.start()
	print('\n\nListening for TRs!\n\n')

	## setup user interface / event EventHandler
	ui = EventHandler(
		rt_key = RT_KEY,
		kb_name = KB_NAME,
		is_test = TEST_MODE,
		size = (1920, 1080),
		color = (-1, -1, -1),
		screen = -1,
		units = "norm",
		fullscr = False,
		pos = (0, 0),
		allowGUI = False
	)
	def on_trial_start(): # tell event handler how to send triggers
		t = time()
		ev_log.write(event = 'start', timestamp = t)
	ui.on_trial_start = on_trial_start
	def on_stimulate(): # and tell it how to apply stimulation
		'''
		stimulation instructions for event handler
		'''
		t = time()
		stimulator.pulse(intensity)
		ev_log.write(event = 'stimulation', timestamp = t)
	ui.on_stimulate = on_stimulate

	ui.win.winHandle.activate() # move window to front

	## run a task block
	if run in ['01', '09']:
		baseline_block(ui, beh_log, run, tr_listener)
	else:
		priors = get_priors(sub, run, beh_log.dir)
		stimulation_block(ui, beh_log, run, tr_listener, priors)

	## notify subject that experiment has ended
	ui.display(
	'''
	You have completed the experiment!
	Please continue to stay still until instructed otherwise.
	The experimenter will be with you shortly.
	'''
	) # and notify experiment
	print('\n\nExperiment has finished!\nIs MRI finsihed?')
	input('\nPress enter to end script.')

	## clean up and end run
	tr_listener.stop()
	beh_log.close()
	ev_log.close()
