#! /usr/bin/env python
import sys
from PyQt4 import Qt
import adrcontrol
import TempLogger


def main():

    qtapp = Qt.QApplication(sys.argv)  #setup plot window

    adr = adrcontrol.Adrcontrol(app = qtapp)

    #adr.AutoMag(StartHour = 8, StartMinute = 47, DaysFromNow = 0, Maguptime = 30, Magdowntime = 45, Holdtime = 75)
    #adr.AutoMag(StartHour = 3, StartMinute = 0, DaysFromNow = 3, Maguptime = 30, Magdowntime = 45, Holdtime = 240)
    adr.AutoMag(StartHour = 3, StartMinute = 0, DaysFromNow = 1, Maguptime = 30, Magdowntime = 45, Holdtime = 240)

    TempLogger.main(sys.argv, app = qtapp, startdata = True, Timerstep=5000)

if __name__ == '__main__': main()
