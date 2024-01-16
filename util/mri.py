from time import perf_counter as time
from time import sleep
from multiprocessing import Process, Event
import sys

from util.logging import TSVLogger
from .ui import get_keyboard


def record_TRs(stop_event, start_event, sub, run, kb_name, mri_key):
	kb = get_keyboard(kb_name)
	log = TSVLogger(sub, run, 'TR', ['timestamp'])
	first_TR = True 
	try: # in case we're interrupted by main process
		while True:
			assert(not stop_event.is_set())
			keys = kb.getKeys([mri_key], waitRelease = False, clear = True)
			if keys:
				t = time()
				log.write(timestamp = t)
				if first_TR:
					start_event.set()
	except:
		log.close()

class TRSync:

	def __init__(self, sub, run, kb_name, mri_key):
		self.sub = sub
		self.run = run
		self.kb_name = kb_name
		self.mri_key = mri_key

	def start(self):
		self._stop_event = Event()
		self._start_event = Event()
		self._process = Process(
			target = record_TRs,
			args = (
				self._stop_event, self._start_event,
				 self.sub, self.run, 
				 self.kb_name, self.mri_key
				 )
			)
		self._process.start()

	def stop(self):
		self._stop_event.set()
		self._process.join()

	@property
	def received_first_TR(self):
		return self._start_event.is_set()

	def wait_until_first_TR(self, poll_time = .05):
		while not self.received_first_TR:
			sleep(poll_time)
		return

	def __del__(self):
		self.stop()
