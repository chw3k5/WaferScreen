#! /usr/bin/env python
import sys
from PyQt4 import Qt
import adr_system
import TempLogger


def main():

    qtapp = Qt.QApplication(sys.argv)  #setup plot window

    my_adr = adr_system.AdrSystem(app=qtapp)
    my_adr.adr_control.AutoMag(StartHour = 15, StartMinute = 27, DaysFromNow = 0, Maguptime = 4, Magdowntime = 4, Holdtime = 4)
    #adr.AutoMag(StartHour = 7, StartMinute = 15, DaysFromNow = 1, Maguptime = 30, Magdowntime = 45, Holdtime = 60)


    TempLogger.main(sys.argv, app = qtapp, startdata = True, Timerstep=5000)

if __name__ == '__main__': main()
