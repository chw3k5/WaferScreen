#! /usr/bin/env python
import sys
import time

from PyQt4 import Qt

import adr_system
import lakeshore370_thermometer
import os
import numpy

import tempControlTupac


def main():
    daysFromNow = []
    while not type(daysFromNow) == type(int(1)):
        try:
	    print('Type a integer and press enter, 0 = today, 1 = tommorow, ...')	
            daysFromNow = int(input('How many days from now should tupac Automag? '))
        except ValueError:
            print('You screwed that up, try following the instructions')


    qtapp = Qt.QApplication(sys.argv)  #setup plot window
    my_adr = adr_system.AdrSystem(app=qtapp)
    t1 = lakeshore370_thermometer.Lakeshore370Thermometer(address=1, name='FAA GRT', \
          lakeshore=my_adr.temperature_controller)

#    print('logging temp for a long time')
#    t0 = time.time()
#    tempdata = []
#    timedata = []
#    while time.localtime()[3]<5 or time.localtime()[3]> 12:
#        timedata.append(time.time()-t0)
#        tempdata.append(my_adr.temperature_controller.getTemperature())
#        time.sleep(1)
#    numpy.savetxt('openHSwarmup.txt', [timedata,tempdata])

    therms = [t1]
    my_adr.adr_control.addThermometers(therms)
    pickle_file_name = 'automag_logs.pkl'
    for j in range(100):
        heaterOut = my_adr.temperature_controller.getHeaterOut()
        if heaterOut >0:
            my_adr.temperature_controller.setTemperatureSetPoint(0)
            print('heaterOut = %0.2f%%, setting to zero'%heaterOut)
            time.sleep(3)
        elif heaterOut == 0:
            print('setting relay to Ramp')
            my_adr.magnet_control_relay.setRelayToRamp()
            print('Closing heatswitch.')
            my_adr.adr_control.heatswitch.CloseHeatSwitch()
            break            
        else:
            raise ValueError('heaterOut = %0.2f%% <0'%heaterOut)

    

    #datestring = my_adr.adr_control.AutoMag(StartHour=4, StartMinute=0, DaysFromNow=1, Maguptime=30, Magdowntime=45, Holdtime=240)
    datestring = my_adr.adr_control.autoMag(StartHour=6, StartMinute=0, DaysFromNow=daysFromNow, Maguptime=30, Magdowntime=45, Holdtime=60)
    #adr.AutoMag(StartHour = 7, StartMinute = 15, DaysFromNow = 1, Maguptime = 30, Magdowntime = 45, Holdtime = 60)
    #my_adr.adr_control.MagDown(magdowntime=45)

#    TempLogger.main(sys.argv, app = qtapp, startdata = True, Timerstep=5000)
    if my_adr.temperature_controller.getHeaterOut() == 0:
        print "Done with automag."
#        print "Setting up temp control."
        my_adr.magnet_control_relay.setRelayToControl()
    else:
        raise ValueError('didnt demag back to zero heaterOut')

    print('waiting for 10 mins after demag before engaging temp control')
    del my_adr
    time.sleep(60*10)
    print('done waiting, setting up temp control')
    tTupac = tempControlTupac.TempControlTupac(tempTarget = 0.08)
    time.sleep(1)
    tTupac.goToTemp(0.08)
    print('temp control should be setup now')

    #filename_holdtime = time.strftime("%Y_%m_%d_%H_%M", starttime)

    #log_folder = "/home/pcuser/data/ADRLogs/"
#    log_folder = my_adr.logfolder
#    logfilename = time.strftime('%G%M%d_%H%M%S.log')


#    print('starting temp logger')
#    tempmon = TempLoggerN.TempLogger(thermometers=therms, timerstep=6000, temperature_delay=5000, \
#                                     log_folder=log_folder, log_file_name=logfilename, \
#                                     pickle_datestring=datestring, pickle_key="MagMeasure", pickle_file_name=pickle_file_name, \
#                                     temp_title='Automag Hold Temperature', resist_title='Resistance')
#    tempmon.resize(900, 600)
#    tempmon.show()
#    tempmon.start_event()
#    sys.exit(qtapp.exec_())
    print('starting temp logger')
    os.system('python TempLogger.py')

if __name__ == '__main__': main()
