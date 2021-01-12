#!/usr/bin/python
'''
cycle the velma_adr
usage Automag_velma.py <hour> <min> <daysfromnow>
'''

#import adrcontrol
import adr_system
import time
import sys

usage='Automag_velma.py <hour> <min> <daysfromnow>'

N = len(sys.argv)
if N == 1: # if no arguments given use default (start at 5 am tomorrow)
    hour = 5
    min = 0
    daysfromnow=1
elif N == 4: # if arguments given, use them
    hour = int(sys.argv[1])
    min = int(sys.argv[2])
    daysfromnow = int(sys.argv[3])
else:
    print 'Unknown length of arguments.  Abort!\n%s'%usage
    sys.exit()

print 'Automaging velma.  MAKE SURE YOU\'RE IN RAMP MODE AND THAT THE HEATSWITCH IS CLOSED!'
monitortime = 2.0 # hours to monitor temperature after mag cycle
#my_adr = adrcontrol.Adrcontrol()
#qtapp = Qt.QApplication(sys.argv)
#my_adr = adr_system.AdrSystem(app=qtapp)
my_adr = adr_system.AdrSystem()
my_adr.adr_control.AutoMag(hour,min,daysfromnow,25,30,40) # Maguptime, Magdowntime, Holdtime
#my_adr.AutoMag(hour,min,daysfromnow,35,40,40)
t=time.time() # time after magcycle completes in epoch units
thold=t+3600*monitortime
my_adr.adr_control.MonitorTemperature(time.localtime(thold))

