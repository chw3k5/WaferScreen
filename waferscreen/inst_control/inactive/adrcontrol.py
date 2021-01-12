import sys
import math
import time
from PyQt4 import Qt
from scipy import linspace
import numpy as np
import dataplot
import lakeshore370
import zaber
import lr700
import dataplot_mpl

#########################################################################
#
# ADR Controller Class
#
# THIS IS OBSOLETE AND NO LONGER USED, LOOK AT ADRCONTROL_MPL.PY
#
# by Doug Bennett
##########################################################################


class Adrcontrol(object):
    '''
    Provides control of ADR Systems
    '''

######################################################################################
    # Adrcontrol class

    def __init__(self, tempcontrolpad = 13, app = None):
        '''Provides control of ADR Systems
        '''
        
        if app is None:
            self.app = Qt.QApplication(sys.argv) #setup plot window
        else:
            self.app = app

        self.logfolder = '/home/pcuser/data/ADRLogs/'
        self.tccheckfolder = '/home/pcuser/data/'

        self.maguptime = 1.0
        self.magdowntime = 0.5
        self.pausetime = 5.0
        #This is the value to change to try and get 9 A
        # self.vmax = 0.60  # Velma
        #self.vmax = 0.77  # Horton with filter
        self.vmax = 0.89    # Mystery Machine
        self.rshunt = 100
        self.iupend = self.vmax / self.rshunt / 0.01*100
        self.idownend = 0.0

        self.tempcontrol = lakeshore370.Lakeshore370(pad=tempcontrolpad)
        self.heatswitch = zaber.Zaber()
        self.bridge = lr700.LR700(pad=17)
        
        print('WARNING: this is deprecated, please use adrcontrol_mpl.py instead')


########################################### Public Methods #################################################

    def MagUp(self, starttime = None, maguptime = None, iupend = None ):
        '''
        ADR Magup - starttime is a time string, maguptime is in minutes and iupend is % of max(10 mA)
        '''

        if starttime is None:
            starttime = time.localtime() #now

        if maguptime is None:
            maguptime = self.maguptime

        if iupend is None:
            iupend = self.iupend


        logfolder = self.logfolder
        filename_startime = time.strftime("%Y_%m_%d_%H_%M", starttime)
        display_startime = time.strftime("%a, %d %b %Y %H:%M", starttime)

        self.tempcontrol.MagUpSetup()
        time.sleep(3)        

        print 'Lakeshore ready to ramp'

        # wait untul time to start
        while time.time() < time.mktime(starttime):
            timetillstart = (time.mktime(starttime)-time.time())/60
            #print 'Time to Magup %d minutes' % timetillstart
            time.sleep(30)

        currentHeaterOutput = self.tempcontrol.GetManualHeaterOut() #Always start at current output

        magupsteps = math.ceil(maguptime*60/self.pausetime)
        iupbegin = currentHeaterOutput
        iupvalues = linspace(iupbegin,iupend,magupsteps)

        print 'Ramping Up....'

        #app2 = Qt.QApplication(sys.argv) #setup plot window
        maguplot = dataplot.DataPlot() #setup plot
        maguplot.setTitle('MagUp ' + display_startime)
        maguplot.YAxisLabel('ADR Temperature (K)')

        logfile = open(logfolder + filename_startime + 'MagUpLog' + '.txt', 'w') #open logfile

        t0 = time.time() #current time in seconds

        for ivalue in iupvalues:
            self.tempcontrol.SetManualHeaterOut(ivalue)
            #print ivalue
            currentTemperature = self.tempcontrol.GetTemperature()
            x = (time.time()-t0)/60  #time in minutes
            y = currentTemperature
            maguplot.AddPointPlot(x,y)
            logfile.write('%(first)f\t%(second)f\t%(third)f\n' % {'first': x, 'second': y, 'third': ivalue})

            time.sleep(self.pausetime)

        logfile.close()

        maguplot.exportPDF('/home/pcuser/data/ADRLogs/' + filename_startime + 'MagUp' + '.pdf')
        maguplot.close() #close plot
        #app2 = None  #erase QApp (There can be only one)
           
    def MagDown(self, starttime = None, magdowntime = None, idownend = None ):
        '''
        ADR Mag Down - starttime is a time string, magdowntime is in minutes and idownend is % of max(10 mA)
        '''

        if starttime is None:
            starttime = time.localtime()

        if magdowntime is None:
            magdowntime = self.magdowntime

        if idownend is None:
            idownend = self.idownend

        logfolder = self.logfolder
        filename_startime = time.strftime("%Y_%m_%d_%H_%M", starttime)
        display_startime = time.strftime("%a, %d %b %Y %H:%M", starttime)

        self.tempcontrol.DemagSetup()
        time.sleep(3)

        print 'Lakeshore ready to demag'

        while time.time() < time.mktime(starttime):
            timetillstart = (time.mktime(starttime)-time.time())/60
            #print 'Time to Demag %d minutes' % timetillstart
            time.sleep(30)

        currentHeaterOutput = self.tempcontrol.GetManualHeaterOut()

        magdownsteps = math.ceil(magdowntime*60/self.pausetime)
        idownbegin = currentHeaterOutput
        idownvalues = linspace(idownbegin,idownend,magdownsteps)

        print 'Ramping Down...'

        #app3 = Qt.QApplication(sys.argv) #setup plot window
        magdownplot = dataplot.DataPlot()  #setup plot
        magdownplot.setTitle('DeMag ' + display_startime)
        magdownplot.YAxisLabel('ADR Temperature (K)')

        logfile = open(logfolder + filename_startime + 'MagDownLog' + '.txt', 'w')

        t0 = time.time()  #current time in seconds


        for ivalue in idownvalues:
            self.tempcontrol.SetManualHeaterOut(ivalue)
            #print ivalue
            currentTemperature = self.tempcontrol.GetTemperature()
            x = (time.time()-t0)/60
            y = currentTemperature
            magdownplot.AddPointPlot(x,y)
            logfile.write('%(first)f\t%(second)f\t%(third)f\n' % {'first': x, 'second': y, 'third': ivalue})
            time.sleep(self.pausetime)

        logfile.close()

        magdownplot.exportPDF('/home/pcuser/data/ADRLogs/' + filename_startime + 'MagDown' + '.pdf')
        magdownplot.close()  #close plot
        #app3 = None   #erase QApp (There can be only one)

           
    def MonitorTemperature(self, stoptime = None):
        '''
        Monitor Temperatrue between Mag up and down - stoptime is a time string 
        '''

        if stoptime is None:
            stoptime = time.localtime()

        logfolder = self.logfolder
        filename_stoptime = time.strftime("%Y_%m_%d_%H_%M", stoptime)
        display_stoptime = time.strftime("%a, %d %b %Y %H:%M", stoptime)

        x = np.zeros(0, float)
        y = np.zeros(0, float)
        #app4 = Qt.QApplication(sys.argv)  #setup plot window
        #tempmonplot = dataplot.DataPlot()  #setup plot
        #tempmonplot.setTitle('MagHold ' + display_stoptime)
        #tempmonplot.YAxisLabel('ADR Temperature (K)')
        tempmonplot = dataplot_mpl.dataplot_mpl(title='MagHold '+display_stoptime, y_label='ADR Temperature (K)')
        curve = tempmonplot.figure.axes.plot(x, y, 'black')
        tempmonplot.show()
        b = self.app.processEvents()

        logfile = open(logfolder + filename_stoptime + 'MagHoldLog' + '.txt', 'w')

        t0 = time.time() #current time in seconds


        while time.time() < time.mktime(stoptime):
            currentTemperature = self.tempcontrol.GetTemperature()
            newx = (time.time()-t0)/60
            x = np.append(x,newx)
            y = np.append(y,currentTemperature)
            #tempmonplot.AddPointPlot(x,y)
            curve[0].set_data(x, y)
            logfile.write('%(first)f\t%(second)f\n' % {'first': newx, 'second': currentTemperature})
            time.sleep(10)
            tempmonplot.update()
            b = self.app.processEvents()

        logfile.close()

        #replace with export pdf from new class
        #tempmonplot.exportPDF('/home/pcuser/data/ADRLogs/' + filename_stoptime + 'MagHold' + '.pdf')
        tempmonplot.close()  #close plot
        #app4 = None   #erase QApp (There can be only one)

    def AutoMag(self, StartHour = 4, StartMinute = 0, DaysFromNow = 1, Maguptime = 45, Magdowntime = 60, Holdtime = 180):
        '''
        Automag cycle - StartHour 0-23 and StartMinute 0-59 are integers, daysFrom Now is an integer and
        Maguptime, Magdowntime and Holdtime are in minutes
        '''

        print 'Starting AutoMag Sequence'

        startMaguptime = self.TomorrowAtHour(timehour = StartHour, timeminute = StartMinute, daysfromnow = DaysFromNow)
        print 'Starting Magup on ' + time.strftime("%a, %d %b %Y %H:%M", startMaguptime)

        startDemagtime = time.localtime(time.mktime(startMaguptime) + Maguptime*60 + Holdtime*60)
        print 'Starting Demag on ' + time.strftime("%a, %d %b %Y %H:%M", startDemagtime)

        openHeatSwitchtime = time.localtime(time.mktime(startDemagtime) - 3*60) # 3 minutes before Demag

        finishDemagtime = time.localtime(time.mktime(startDemagtime) + Magdowntime*60)
        print 'Should Finish Demag on ' + time.strftime("%a, %d %b %Y %H:%M", finishDemagtime)

        self.MagUp(starttime = startMaguptime, maguptime = Maguptime)

        print 'Finished MagUp'

        self.MonitorTemperature(stoptime = openHeatSwitchtime) #monitor temperature unitl it is time to demag

        print 'Opening Heat Switch'
        self.heatswitch.OpenHeatSwitch()


        print 'Ready for Demag'

        self.MagDown(starttime = startDemagtime, magdowntime = Magdowntime)

        print 'Finished Demag'

        return True

           
    def TomorrowAtHour(self, timehour = 4, timeminute = 0, daysfromnow = 1):
        '''
        Returns time string for a given hour 0-23 and minute 0-59 on daysfromnow
        '''
        
        nowtime = time.localtime()
        tomorrow = time.localtime(time.mktime(nowtime)+daysfromnow*24*60*60) #Add days to current time
        starttime =  tomorrow[0:3] + (timehour,) + (timeminute,) + (0,)  + tomorrow[6:]
        return starttime

    def TcCheckMagUp(self, starttime = None, maguptime = None, iupend = None ):
        '''
        ADR Magup - starttime is a time string, maguptime is in minutes and iupend is % of max(10 mA)
        '''

        if starttime is None:
            starttime = time.localtime() #now

        if maguptime is None:
            maguptime = self.maguptime

        if iupend is None:
            iupend = self.iupend


        logfolder = self.tccheckfolder
        filename_startime = time.strftime("%Y_%m_%d_%H_%M", starttime)
        display_startime = time.strftime("%a, %d %b %Y %H:%M", starttime)

        self.tempcontrol.MagUpSetup()
        time.sleep(3)        

        print 'Lakeshore ready to ramp'

        # wait untul time to start
        while time.time() < time.mktime(starttime):
            timetillstart = (time.mktime(starttime)-time.time())/60
            #print 'Time to Magup %d minutes' % timetillstart
            time.sleep(30)

        currentHeaterOutput = self.tempcontrol.GetManualHeaterOut() #Always start at current output

        magupsteps = math.ceil(maguptime*60/self.pausetime)
        iupbegin = currentHeaterOutput
        iupvalues = linspace(iupbegin,iupend,magupsteps)

        print 'Ramping Up....'

        #app2 = Qt.QApplication(sys.argv) #setup plot window
        maguplot = dataplot.DataPlot() #setup plot
        maguplot.setTitle('MagUp ' + display_startime)
        maguplot.YAxisLabel('Resistance (Ohm)')
        maguplot.XAxisLabel('ADR Temperature (K)')

        logfile = open(logfolder + filename_startime + 'TcMagUpLog' + '.txt', 'w') #open logfile

        t0 = time.time() #current time in seconds

        for ivalue in iupvalues:
            self.tempcontrol.SetManualHeaterOut(ivalue)
            #print ivalue
            time.sleep(self.pausetime)
            currentTemperature = self.tempcontrol.GetTemperature()
            currentResistance = self.bridge.GetResistance()
            x = (time.time()-t0)/60  #time in minutes
            y = currentTemperature
            z = currentResistance
            maguplot.AddPointPlot(y,z)
            logfile.write('%(first)f\t%(second)f\t%(third)f\t%(fourth)f\n' % {'first': x, 'second': y, 'third': z, 'fourth': ivalue})

            

        logfile.close()

        maguplot.exportPDF('/home/pcuser/data/' + filename_startime + 'TcMagUp' + '.pdf')
        maguplot.close() #close plot
        #app2 = None  #erase QApp (There can be only one)
           
    def TcCheckMagDown(self, starttime = None, magdowntime = None, idownend = None ):
        '''
        ADR Mag Down - starttime is a time string, magdowntime is in minutes and idownend is % of max(10 mA)
        '''

        if starttime is None:
            starttime = time.localtime()

        if magdowntime is None:
            magdowntime = self.magdowntime

        if idownend is None:
            idownend = self.idownend

        logfolder = self.tccheckfolder
        filename_startime = time.strftime("%Y_%m_%d_%H_%M", starttime)
        display_startime = time.strftime("%a, %d %b %Y %H:%M", starttime)

        self.tempcontrol.DemagSetup()
        time.sleep(3)

        print 'Lakeshore ready to demag'

        while time.time() < time.mktime(starttime):
            timetillstart = (time.mktime(starttime)-time.time())/60
            #print 'Time to Demag %d minutes' % timetillstart
            time.sleep(30)

        currentHeaterOutput = self.tempcontrol.GetManualHeaterOut()

        magdownsteps = math.ceil(magdowntime*60/self.pausetime)
        idownbegin = currentHeaterOutput
        idownvalues = linspace(idownbegin,idownend,magdownsteps)

        print 'Ramping Down...'

        #app3 = Qt.QApplication(sys.argv) #setup plot window
        magdownplot = dataplot.DataPlot()  #setup plot
        magdownplot.setTitle('DeMag ' + display_startime)
        magdownplot.YAxisLabel('Resistance (Ohm)')
        magdownplot.XAxisLabel('ADR Temperature (K)')

        logfile = open(logfolder + filename_startime + 'TcMagDownLog' + '.txt', 'w')

        t0 = time.time()  #current time in seconds


        for ivalue in idownvalues:
            self.tempcontrol.SetManualHeaterOut(ivalue)
            #print ivalue
            time.sleep(self.pausetime)
            currentTemperature = self.tempcontrol.GetTemperature()
            currentResistance = self.bridge.GetResistance()
            x = (time.time()-t0)/60
            y = currentTemperature
            z = currentResistance
            magdownplot.AddPointPlot(y,z)
            logfile.write('%(first)f\t%(second)f\t%(third)f\t%(fourth)f\n' % {'first': x, 'second': y, 'third': z, 'fourth': ivalue})
            

        logfile.close()

        magdownplot.exportPDF('/home/pcuser/data/' + filename_startime + 'MagDown' + '.pdf')
        magdownplot.close()  #close plot
        #app3 = None   #erase QApp (There can be only one)


    def TcCheckAutoMag(self, StartHour = 4, StartMinute = 0, DaysFromNow = 1, Maguptime = 45, Magdowntime = 60, Holdtime = 180):
        '''
        TcCheck Automag cycle - StartHour 0-23 and StartMinute 0-59 are integers, daysFrom Now is an integer and
        Maguptime, Magdowntime and Holdtime are in minutes
        '''

        print 'Starting AutoMag Sequence'

        startMaguptime = self.TomorrowAtHour(timehour = StartHour, timeminute = StartMinute, daysfromnow = DaysFromNow)
        print 'Starting Magup on ' + time.strftime("%a, %d %b %Y %H:%M", startMaguptime)

        startDemagtime = time.localtime(time.mktime(startMaguptime) + Maguptime*60 + Holdtime*60)
        print 'Starting Demag on ' + time.strftime("%a, %d %b %Y %H:%M", startDemagtime)

        openHeatSwitchtime = time.localtime(time.mktime(startDemagtime) - 3*60) # 3 minutes before Demag

        finishDemagtime = time.localtime(time.mktime(startDemagtime) + Magdowntime*60)
        print 'Should Finish Demag on ' + time.strftime("%a, %d %b %Y %H:%M", finishDemagtime)

        self.TcCheckMagUp(starttime = startMaguptime, maguptime = Maguptime, iupend = 40)

        print 'Finished MagUp'

        self.MonitorTemperature(stoptime = openHeatSwitchtime) #monitor temperature unitl it is time to demag

        #print 'Opening Heat Switch'
        #self.heatswitch.OpenHeatSwitch()


        print 'Ready for Demag'

        self.TcCheckMagDown(starttime = startDemagtime, magdowntime = Magdowntime, idownend = 0)

        print 'Finished Demag'


        return True
        
        
    def MonitorWarmUpRate(self, minutesToMeasure = 5, filepath = '/home/pcuser/data/texas/nothingOn'):
        '''
        Monitor Temperatrue during a warm up rate 
            '''

        starttime = time.localtime()
        stoptime = time.localtime(time.mktime(starttime) + minutesToMeasure*60) 

        #filename_stoptime = time.strftime("%Y_%m_%d_%H_%M", stoptime)
        display_stoptime = time.strftime("%a, %d %b %Y %H:%M", stoptime)
        print display_stoptime

        tempmonplot = dataplot.DataPlot()  #setup plot
        tempmonplot.setTitle(filepath)
        tempmonplot.YAxisLabel('ADR Temperature (K)')

        logfile = open(filepath + '.dat', 'w')

        t0 = time.time() #current time in seconds


        while time.time() < time.mktime(stoptime):
            currentTemperature = self.tempcontrol.GetTemperature()
            x = (time.time()-t0)/60
            y = currentTemperature
            tempmonplot.AddPointPlot(x,y)
            logfile.write('%(first)f\t%(second)f\n' % {'first': x, 'second': y})
            time.sleep(2)

        logfile.close()

        tempmonplot.exportPDF(filepath + '.pdf')
        tempmonplot.close()  #close plot
           
