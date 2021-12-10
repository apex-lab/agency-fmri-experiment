import serial
import singlepulse
import time

class Poke(object):
        def __init__(self,name,channel,pulse_width,min_amp_val,max_amp_val,slope_decay,delay_val,repetitions):
                self.name = name
                self.channel = channel
                self.pulse_width = pulse_width
		self.min_amp_val = min_amp_val
		self.max_amp_val = max_amp_val
		self.slope_decay = slope_decay
		self.delay_val = delay_val
		self.repetitions = repetitions

        def play(self,ems): #this is a very regid definition of gesture
            for x in range(self.repetitions):
                	if x > 0 and (self.min_amp_val+x/self.slope_decay) < self.max_amp_val:
                        	cmd1 = singlepulse.generate(self.channel,self.pulse_width,self.min_amp_val+x/self.slope_decay)
                	elif (self.min_amp_val+x/self.slope_decay) >= self.max_amp_val:
                        	cmd1 = singlepulse.generate(self.channel,self.pulse_width,self.max_amp_val)
                	else: cmd1 = singlepulse.generate(self.channel,self.pulse_width,self.min_amp_val)
                	ems.write(cmd1)
                	time.sleep(self.delay_val)


        def sweepDown(self,ems): #this is a very regid definition of gesture
        	for x in range(self.repetitions):
                	if x > 0 and (self.max_amp_val-x/self.slope_decay) > self.min_amp_val:
                        	cmd1 = singlepulse.generate(self.channel,self.pulse_width,self.max_amp_val-x/self.slope_decay)
                        	#print  self.max_amp_val-x/self.slope_decay
                	elif (self.max_amp_val-x/self.slope_decay) <= self.min_amp_val:
                        	cmd1 = singlepulse.generate(self.channel,self.pulse_width,self.min_amp_val)
                        	#print "mined out at " + str(self.min_amp_val)
                	else: cmd1 = singlepulse.generate(self.channel,self.pulse_width,self.max_amp_val)
                	ems.write(cmd1)
                	time.sleep(self.delay_val)

        def getChannel(self):
            return self.channel
