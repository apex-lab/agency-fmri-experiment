from util.events import EventMarker
from util.ems import EMS
from time import sleep
import numpy as np

ems = EMS()
marker = EventMarker()

def trial():
    '''
    sends TTL trigger and EMS pulse consecutively

    runs through custom cable that lowers output voltage to a recordable
    level, and then we record it with stimtrack

    pulse times can then be compared with TTL trigger times
    '''
    marker.send(2) # send trigger
    ems.pulse(2) # initiate pulse

for i in range(500):
    print('trial %d'%(i + 1))
    sleep(1 + np.random.random())
    trial()

# close serial connections
print('Done!')
ems.close()
marker.close()
