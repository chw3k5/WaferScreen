#! /usr/bin/env python
import sys
from PyQt4 import Qt

import adr_system
import lakeshore370_thermometer
import TempLoggerN


def main():

    qtapp = Qt.QApplication(sys.argv)  #setup plot window
    my_adr = adr_system.AdrSystem(app=qtapp)
    pickle_file_name = 'automag_logs.pkl'
    datestring = my_adr.adr_control.AutoMag(StartHour=9, StartMinute=22, DaysFromNow=0, Maguptime=4, Magdowntime=4, Holdtime=4)
    #adr.AutoMag(StartHour = 7, StartMinute = 15, DaysFromNow = 1, Maguptime = 30, Magdowntime = 45, Holdtime = 60)


#    TempLogger.main(sys.argv, app = qtapp, startdata = True, Timerstep=5000)

    print "Done with automag."
    print "Plot hold temperature."

    t1 = lakeshore370_thermometer.Lakeshore370Thermometer(address=1, name='ADR', \
                                                          lakeshore=my_adr.temperature_controller)
    #filename_holdtime = time.strftime("%Y_%m_%d_%H_%M", starttime)

    log_folder = "/home/pcuser/data/ADRLogs/"
    logfilename = "PostMag.txt"
    therms = [t1]
    tempmon = TempLoggerN.TempLogger(thermometers=therms, timerstep=6000, temperature_delay=5000, \
                                     log_folder=log_folder, log_file_name=logfilename, \
                                     pickle_datestring=datestring, pickle_key="MagMeasure", pickle_file_name=pickle_file_name, \
                                     temp_title='Automag Hold Temperature', resist_title='Resistance')
    tempmon.resize(900, 600)
    tempmon.show()
    tempmon.start_event()
    sys.exit(qtapp.exec_())

if __name__ == '__main__': main()