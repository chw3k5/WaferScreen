import sys
import math
import time
from PyQt4.QtGui import QApplication

from scipy import linspace
import numpy as np
#import lr700
import dataplot_mpl
import lakeshore370_thermometer
import tespickle

#########################################################################
#
# ADR Controller Class
#
# Look into inheritance for this class?
#
# by Doug Bennett and Frank Schima
##########################################################################


class Adrcontrol(object):
    '''
    Provides control of ADR Systems
    '''

######################################################################################
    # Adrcontrol class

    def __init__(self, temperature_controller, vmax, heat_switch, heater_resistance=1, app=None, logfolder='/home/pcuser/data/ADRLogs/', tccheckfolder='/home/pcuser/data/', pickle_file_name='automag_logs.pkl', thermometers=None):
        '''Constructor: 
           temperature_controller = pointer to instrument class object (lakeshore370 only currently)
           heat_switch = pointer to instrument class object (zaber only currently)
        '''
        
        if app is None:
            self.app = QApplication(sys.argv) #setup plot window
        else:
            self.app = app

        self.logfolder = logfolder
        self.tccheckfolder = tccheckfolder
        self.pickle_file_name = pickle_file_name
        
        if thermometers is None:
            default_thermometer = lakeshore370_thermometer.Lakeshore370Thermometer(address=1, name='ADR', \
                                                                                   lakeshore=temperature_controller)
            self.thermometers =  [default_thermometer]
        else:
            self.thermometers = thermometers

        self.maguptime = 1.0
        self.magdowntime = 0.5
        self.pausetime = 5.0
        #This is the value to change to try and get 9 A
        # self.vmax = 0.60  # Velma
        #self.vmax = 0.77  # Horton with filter
        #self.vmax = 0.68    # Mystery Machine
        
        self.vmax = vmax
        self.heater_resistance = heater_resistance
        
        self.rshunt = 100
        self.iupend = self.vmax / self.rshunt / 0.01*100
        self.idownend = 0.0

        self.tempcontrol = temperature_controller
        self.heatswitch = heat_switch
        #self.bridge = lr700.LR700(pad=17)
        
        # Create the pickle
        self.gamma = {}


########################################### Public Methods #################################################

    def addThermometers(self, thermometers):
        self.thermometers = thermometers

    def magUp(self, starttime = None, maguptime = None, iupend = None, mag_up_dict=None):
        '''
        ADR magUp - starttime is a time string, maguptime is in minutes and iupend is % of max(10 mA)
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

        self.tempcontrol.magUpSetup(heater_resistance=self.heater_resistance)
        time.sleep(3)        

        print 'Lakeshore ready to ramp'

        # wait untul time to start
        while time.time() < time.mktime(starttime):
            timetillstart = (time.mktime(starttime)-time.time())/60
            #print 'Time to Magup %d minutes' % timetillstart
            time.sleep(30)

        #if self.heatswitch != None:
        #    # Close heat switch
        #    print 'Closing Heat Switch ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        #    self.heatswitch.CloseHeatSwitch()
        #else:
        #    print "No heat switch to close."

        currentHeaterOutput = self.tempcontrol.getManualHeaterOut() #Always start at current output

        magupsteps = math.ceil(maguptime*60/self.pausetime)
        iupbegin = currentHeaterOutput
        iupvalues = linspace(iupbegin,iupend,magupsteps)

        print 'Ramping Up....'

        #app2 = Qt.QApplication(sys.argv) #setup plot window
        magupplot = dataplot_mpl.dataplot_mpl() #setup plot
        magupplot.set_title('MagUp ' + display_startime)
        magupplot.set_y_axis_label('ADR Temperature (K)')
        magupplot.set_x_axis_label('Time (min)')
        #print "setting bounds %i->%i" % (0, self.maguptime)
        magupplot.setXAxisBounds(x_min=0, x_max=self.maguptime)
        blank_array = []
        magupplotlines = []
        for thermometer in self.thermometers:
            magupplotlines.append(magupplot.addLine(thermometer.name, blank_array, blank_array))
        magupplot.show()
        b = self.app.processEvents()

        logfile = open(logfolder + filename_startime + 'MagUpLog' + '.txt', 'w') #open logfile

        t0 = time.time() #current time in seconds

        data_dict={}
        for (offset, thermometer) in enumerate(self.thermometers):
            data_dict[offset] = {}
            data_dict[offset]['t'] = np.zeros(0, float)
            data_dict[offset]['r'] = np.zeros(0, float)

        for ivalue in iupvalues:
            self.tempcontrol.setManualHeaterOut(ivalue)
            #print ivalue
            x = (time.time()-t0)/60  #time in minutes
            for (offset, thermometer) in enumerate(self.thermometers):
                currentTemperature = self.tempcontrol.getTemperature(thermometer.address)
                currentResistance = self.tempcontrol.getResistance(thermometer.address)
                y = currentTemperature
                data_dict[offset]['t']=np.append(data_dict[offset]['t'], currentTemperature)
                data_dict[offset]['r']=np.append(data_dict[offset]['r'], currentResistance)
                #t[offset] = np.append(t[offset], currentTemperature)
                #r[offset] = np.append(r[offset], currentResistance)
                magupplotlines[offset].addPoint(x,y)

            magupplot.update()
            b = self.app.processEvents()
            logfile.write('%(first)f\t%(second)f\t%(third)f\n' % {'first': x, 'second': y, 'third': ivalue})

            time.sleep(self.pausetime)

        logfile.close()

        magupplot.exportPDF(self.logfolder + filename_startime + 'MagUp' + '.pdf')
        magupplot.close() #close plot
        
        if mag_up_dict is not None:
            for (offset, thermometer) in enumerate(self.thermometers):
                time_string = "time_%i" % offset
                temp_string = "temperature_%i" % offset
                resist_string = "resistance_%i" % offset
                mag_up_dict[time_string] = magupplotlines[offset].xdata
                mag_up_dict[temp_string] = magupplotlines[offset].ydata
                mag_up_dict[resist_string] = data_dict[offset]['r']
            mag_up_dict['current'] = iupvalues

        #app2 = None  #erase QApp (There can be only one)
           
    def magDown(self, starttime = None, magdowntime = None, idownend = None, mag_down_dict=None):
        '''
        ADR Mag Down - starttime is a time string, magdowntime is in minutes and idownend is % of max(10 mA)
        '''

        if starttime is None:
            starttime = time.localtime()

        if magdowntime is None:
            magdowntime = self.magdowntime

        if idownend is None:
            idownend = self.idownend

        filename_startime = time.strftime("%Y_%m_%d_%H_%M", starttime)
        display_startime = time.strftime("%a, %d %b %Y %H:%M", starttime)

        self.tempcontrol.demagSetup(heater_resistance=self.heater_resistance)
        time.sleep(3)

        print 'Lakeshore ready to demag'

        while time.time() < time.mktime(starttime):
            timetillstart = (time.mktime(starttime)-time.time())/60
            #print 'Time to Demag %d minutes' % timetillstart
            time.sleep(30)

        currentHeaterOutput = self.tempcontrol.getManualHeaterOut()

        magdownsteps = math.ceil(magdowntime*60/self.pausetime)
        idownbegin = currentHeaterOutput
        idownvalues = linspace(idownbegin,idownend,magdownsteps)

        print 'Ramping Down...'

        #app3 = Qt.QApplication(sys.argv) #setup plot window
        magdownplot = dataplot_mpl.dataplot_mpl()  #setup plot
        magdownplot.set_title('DeMag ' + display_startime)
        magdownplot.set_x_axis_label('Time (min)')
        magdownplot.set_y_axis_label('ADR Temperature (K)')
        magdownplot.setXAxisBounds(x_min=0, x_max=self.magdowntime)
        blank_array = []
        magdownplotlines = []
        for thermometer in self.thermometers:
            magdownplotlines.append(magdownplot.addLine(thermometer.name, blank_array, blank_array))      
        magdownplot.show()
        b = self.app.processEvents()

        logfile = open(self.logfolder + filename_startime + 'MagDownLog' + '.txt', 'w')

        t0 = time.time()  #current time in seconds

        data_dict={}
        for (offset, thermometer) in enumerate(self.thermometers):
            data_dict[offset] = {}
            data_dict[offset]['t'] = np.zeros(0, float)
            data_dict[offset]['r'] = np.zeros(0, float)

        for ivalue in idownvalues:
            self.tempcontrol.setManualHeaterOut(ivalue)
            #print ivalue
            x = (time.time()-t0)/60  #time in minutes
            for (offset, thermometer) in enumerate(self.thermometers):
                currentTemperature = self.tempcontrol.getTemperature(thermometer.address)
                currentResistance = self.tempcontrol.getResistance(thermometer.address)
                y = currentTemperature
                data_dict[offset]['t']=np.append(data_dict[offset]['t'], currentTemperature)
                data_dict[offset]['r']=np.append(data_dict[offset]['r'], currentResistance)
                #t[offset] = np.append(t[offset], currentTemperature)
                #r[offset] = np.append(r[offset], currentResistance)
                magdownplotlines[offset].addPoint(x,y)
            magdownplot.update()
            b = self.app.processEvents()
            logfile.write('%(first)f\t%(second)f\t%(third)f\n' % {'first': x, 'second': y, 'third': ivalue})
            time.sleep(self.pausetime)

        logfile.close()

        magdownplot.exportPDF(self.logfolder + filename_startime + 'MagDown' + '.pdf')
        magdownplot.close()  #close plot
        #app3 = None   #erase QApp (There can be only one)
            
        if mag_down_dict is not None:
            for (offset, thermometer) in enumerate(self.thermometers):
                time_string = "time_%i" % offset
                temp_string = "temperature_%i" % offset
                resist_string = "resistance_%i" % offset
                mag_down_dict[time_string] = magdownplotlines[offset].xdata
                mag_down_dict[temp_string] = magdownplotlines[offset].ydata
                mag_down_dict[resist_string] = data_dict[offset]['r']
            mag_down_dict['current'] = idownvalues


    def monitorTemperature(self, stoptime = None, mag_hold_dict=None):
        '''
        Monitor Temperature between Mag up and down - stoptime is a time string 
        '''

        if stoptime is None:
            stoptime = time.localtime()

        filename_stoptime = time.strftime("%Y_%m_%d_%H_%M", stoptime)
        display_stoptime = time.strftime("%a, %d %b %Y %H:%M", stoptime)

        x = np.zeros(0, float)
        y = np.zeros(0, float)
        r = np.zeros(0, float)

        tempmonplot = dataplot_mpl.dataplot_mpl(title='MagHold '+display_stoptime, x_label="Time (min)", y_label='ADR Temperature (K)')
        plotlines = []
        for thermometer in self.thermometers:
            plotlines.append(tempmonplot.addLine(thermometer.name, x, y))      
        tempmonplot.show()
        b = self.app.processEvents()

        logfile = open(self.logfolder + filename_stoptime + 'MagHoldLog' + '.txt', 'w')

        t0 = time.time() #current time in seconds

        data_dict={}
        for (offset, thermometer) in enumerate(self.thermometers):
            data_dict[offset] = {}
            data_dict[offset]['t'] = np.zeros(0, float)
            data_dict[offset]['r'] = np.zeros(0, float)
            
        while time.time() < time.mktime(stoptime):
            x = (time.time()-t0)/60  #time in minutes
            for (offset, thermometer) in enumerate(self.thermometers):
                currentTemperature = self.tempcontrol.getTemperature(thermometer.address)
                currentResistance = self.tempcontrol.getResistance(thermometer.address)
                y = currentTemperature
                data_dict[offset]['t']=np.append(data_dict[offset]['t'], currentTemperature)
                data_dict[offset]['r']=np.append(data_dict[offset]['r'], currentResistance)
                #t[offset] = np.append(t[offset], currentTemperature)
                #r[offset] = np.append(r[offset], currentResistance)
                plotlines[offset].addPoint(x,y)
            tempmonplot.update()
            b = self.app.processEvents()
            logfile.write('%(first)f\t%(second)f\n' % {'first': x, 'second': currentTemperature})
            time.sleep(10)

        logfile.close()

        tempmonplot.exportPDF(self.logfolder + filename_stoptime + 'MagHold' + '.pdf')
        tempmonplot.close()  #close plot
        #app4 = None   #erase QApp (There can be only one)
            
        if mag_hold_dict is not None:
            for (offset, thermometer) in enumerate(self.thermometers):
                time_string = "time_%i" % offset
                temp_string = "temperature_%i" % offset
                resist_string = "resistance_%i" % offset
                mag_hold_dict[time_string] = plotlines[offset].xdata
                mag_hold_dict[temp_string] = plotlines[offset].ydata
                mag_hold_dict[resist_string] = data_dict[offset]['r']


    def autoMag(self, StartHour=4, StartMinute=0, DaysFromNow=1, Maguptime=45, Magdowntime=60, Holdtime=180):
        '''
        Automag cycle - StartHour 0-23 and StartMinute 0-59 are integers, daysFrom Now is an integer and
        Maguptime, Magdowntime and Holdtime are in minutes
        '''

        print 'Starting AutoMag Sequence'
        
        # Fix time if attempting to start before now. 
        currenttime_array = time.localtime()
        currentHour = currenttime_array[3]
        currentMinute = currenttime_array[4]
        if DaysFromNow*24*60 + StartHour*60 + StartMinute < currentHour*60 + currentMinute:
            print "Fixing the times"
            StartHour = currentHour
            StartMinute = currentMinute

        # Create the dictionary
        #automag_dict = {}
        self.gamma = tespickle.TESPickle(self.logfolder + self.pickle_file_name)
        #self.gamma.gamma = automag_dict

        datestring = time.strftime("%Y-%m-%d %H:%M:%S", currenttime_array)
        print 'datestring', datestring
        self.gamma.gamma[datestring] = {}
        self.gamma.gamma[datestring]['MagUp'] = {}
        self.gamma.gamma[datestring]['MagHold'] = {}
        self.gamma.gamma[datestring]['MagDown'] = {}
        self.gamma.gamma[datestring]['MagMeasure'] = {}
        
        startMaguptime = self.TomorrowAtHour(timehour = StartHour, timeminute = StartMinute, daysfromnow = DaysFromNow)
        print 'Starting      Magup on ' + time.strftime("%a, %d %b %Y %H:%M", startMaguptime)

        startHoldtime = time.localtime(time.mktime(startMaguptime) + Maguptime*60)
        print 'Starting       Hold on ' + time.strftime("%a, %d %b %Y %H:%M", startHoldtime)

        startDemagtime = time.localtime(time.mktime(startMaguptime) + Maguptime*60 + Holdtime*60)

        openHeatSwitchtime = time.localtime(time.mktime(startDemagtime) - 3*60) # 3 minutes before Demag
        print 'Open Heat Switch    on ' + time.strftime("%a, %d %b %Y %H:%M", openHeatSwitchtime)
        print 'Starting      Demag on ' + time.strftime("%a, %d %b %Y %H:%M", startDemagtime)

        finishDemagtime = time.localtime(time.mktime(startDemagtime) + Magdowntime*60)
        print 'Should Finish Demag on ' + time.strftime("%a, %d %b %Y %H:%M", finishDemagtime)

        print "Starting Magup ", time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

        self.magUp(starttime=startMaguptime, maguptime=Maguptime, mag_up_dict=self.gamma.gamma[datestring]['MagUp'])

        print 'Finished Magup ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

        self.gamma.savePickle()

        # Mag Hold
        # monitor temperature until it is time to demag
        self.monitorTemperature(stoptime=openHeatSwitchtime, mag_hold_dict=self.gamma.gamma[datestring]['MagHold'])

        self.gamma.savePickle()

        # Open heat switch
        print 'Opening Heat Switch ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        self.heatswitch.OpenHeatSwitch()

        # Demag
        print 'Starting Demag ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

        self.magDown(starttime=startDemagtime, magdowntime=Magdowntime, mag_down_dict=self.gamma.gamma[datestring]['MagDown'])

        print 'Finished Demag ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

        self.gamma.savePickle()

        return datestring

           
    def TomorrowAtHour(self, timehour = 4, timeminute = 0, daysfromnow = 1):
        '''
        Returns time string for a given hour 0-23 and minute 0-59 on daysfromnow
        '''
        
        nowtime = time.localtime()
        tomorrow = time.localtime(time.mktime(nowtime)+daysfromnow*24*60*60) #Add days to current time
        starttime =  tomorrow[0:3] + (timehour,) + (timeminute,) + (0,)  + tomorrow[6:]
        return starttime


    # These methods have been renamed and will eventually be derpreciated

    def MagUp(self, starttime = None, maguptime = None, iupend = None, mag_up_dict=None):
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

        self.tempcontrol.magUpSetup(heater_resistance=self.heater_resistance)
        time.sleep(3)        

        print 'Lakeshore ready to ramp'

        # wait untul time to start
        while time.time() < time.mktime(starttime):
            timetillstart = (time.mktime(starttime)-time.time())/60
            #print 'Time to Magup %d minutes' % timetillstart
            time.sleep(30)

        #if self.heatswitch != None:
        #    # Close heat switch
        #    print 'Closing Heat Switch ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        #    self.heatswitch.CloseHeatSwitch()
        #else:
        #    print "No heat switch to close."

        currentHeaterOutput = self.tempcontrol.getManualHeaterOut() #Always start at current output

        magupsteps = math.ceil(maguptime*60/self.pausetime)
        iupbegin = currentHeaterOutput
        iupvalues = linspace(iupbegin,iupend,magupsteps)

        print 'Ramping Up....'

        #app2 = Qt.QApplication(sys.argv) #setup plot window
        magupplot = dataplot_mpl.dataplot_mpl() #setup plot
        magupplot.set_title('MagUp ' + display_startime)
        magupplot.set_y_axis_label('ADR Temperature (K)')
        magupplot.set_x_axis_label('Time (min)')
        #print "setting bounds %i->%i" % (0, self.maguptime)
        magupplot.setXAxisBounds(x_min=0, x_max=self.maguptime)
        blank_array = []
        magupplotlines = []
        for thermometer in self.thermometers:
            magupplotlines.append(magupplot.addLine(thermometer.name, blank_array, blank_array))
        magupplot.show()
        b = self.app.processEvents()

        logfile = open(logfolder + filename_startime + 'MagUpLog' + '.txt', 'w') #open logfile

        t0 = time.time() #current time in seconds

        data_dict={}
        for (offset, thermometer) in enumerate(self.thermometers):
            data_dict[offset] = {}
            data_dict[offset]['t'] = np.zeros(0, float)
            data_dict[offset]['r'] = np.zeros(0, float)

        for ivalue in iupvalues:
            self.tempcontrol.setManualHeaterOut(ivalue)
            #print ivalue
            x = (time.time()-t0)/60  #time in minutes
            for (offset, thermometer) in enumerate(self.thermometers):
                currentTemperature = self.tempcontrol.getTemperature(thermometer.address)
                currentResistance = self.tempcontrol.getResistance(thermometer.address)
                y = currentTemperature
                data_dict[offset]['t']=np.append(data_dict[offset]['t'], currentTemperature)
                data_dict[offset]['r']=np.append(data_dict[offset]['r'], currentResistance)
                #t[offset] = np.append(t[offset], currentTemperature)
                #r[offset] = np.append(r[offset], currentResistance)
                magupplotlines[offset].addPoint(x,y)

            magupplot.update()
            b = self.app.processEvents()
            logfile.write('%(first)f\t%(second)f\t%(third)f\n' % {'first': x, 'second': y, 'third': ivalue})

            time.sleep(self.pausetime)

        logfile.close()

        magupplot.exportPDF(self.logfolder + filename_startime + 'MagUp' + '.pdf')
        magupplot.close() #close plot
        
        if mag_up_dict is not None:
            for (offset, thermometer) in enumerate(self.thermometers):
                time_string = "time_%i" % offset
                temp_string = "temperature_%i" % offset
                resist_string = "resistance_%i" % offset
                mag_up_dict[time_string] = magupplotlines[offset].xdata
                mag_up_dict[temp_string] = magupplotlines[offset].ydata
                mag_up_dict[resist_string] = data_dict[offset]['r']
            mag_up_dict['current'] = iupvalues

        #app2 = None  #erase QApp (There can be only one)
           
    def MagDown(self, starttime = None, magdowntime = None, idownend = None, mag_down_dict=None):
        '''
        ADR Mag Down - starttime is a time string, magdowntime is in minutes and idownend is % of max(10 mA)
        '''

        if starttime is None:
            starttime = time.localtime()

        if magdowntime is None:
            magdowntime = self.magdowntime

        if idownend is None:
            idownend = self.idownend

        filename_startime = time.strftime("%Y_%m_%d_%H_%M", starttime)
        display_startime = time.strftime("%a, %d %b %Y %H:%M", starttime)

        self.tempcontrol.demagSetup(heater_resistance=self.heater_resistance)
        time.sleep(3)

        print 'Lakeshore ready to demag'

        while time.time() < time.mktime(starttime):
            timetillstart = (time.mktime(starttime)-time.time())/60
            #print 'Time to Demag %d minutes' % timetillstart
            time.sleep(30)

        currentHeaterOutput = self.tempcontrol.getManualHeaterOut()

        magdownsteps = math.ceil(magdowntime*60/self.pausetime)
        idownbegin = currentHeaterOutput
        idownvalues = linspace(idownbegin,idownend,magdownsteps)

        print 'Ramping Down...'

        #app3 = Qt.QApplication(sys.argv) #setup plot window
        magdownplot = dataplot_mpl.dataplot_mpl()  #setup plot
        magdownplot.set_title('DeMag ' + display_startime)
        magdownplot.set_x_axis_label('Time (min)')
        magdownplot.set_y_axis_label('ADR Temperature (K)')
        magdownplot.setXAxisBounds(x_min=0, x_max=self.magdowntime)
        blank_array = []
        magdownplotlines = []
        for thermometer in self.thermometers:
            magdownplotlines.append(magdownplot.addLine(thermometer.name, blank_array, blank_array))      
        magdownplot.show()
        b = self.app.processEvents()

        logfile = open(self.logfolder + filename_startime + 'MagDownLog' + '.txt', 'w')

        t0 = time.time()  #current time in seconds

        data_dict={}
        for (offset, thermometer) in enumerate(self.thermometers):
            data_dict[offset] = {}
            data_dict[offset]['t'] = np.zeros(0, float)
            data_dict[offset]['r'] = np.zeros(0, float)

        for ivalue in idownvalues:
            self.tempcontrol.setManualHeaterOut(ivalue)
            #print ivalue
            x = (time.time()-t0)/60  #time in minutes
            for (offset, thermometer) in enumerate(self.thermometers):
                currentTemperature = self.tempcontrol.getTemperature(thermometer.address)
                currentResistance = self.tempcontrol.getResistance(thermometer.address)
                y = currentTemperature
                data_dict[offset]['t']=np.append(data_dict[offset]['t'], currentTemperature)
                data_dict[offset]['r']=np.append(data_dict[offset]['r'], currentResistance)
                #t[offset] = np.append(t[offset], currentTemperature)
                #r[offset] = np.append(r[offset], currentResistance)
                magdownplotlines[offset].addPoint(x,y)
            magdownplot.update()
            b = self.app.processEvents()
            logfile.write('%(first)f\t%(second)f\t%(third)f\n' % {'first': x, 'second': y, 'third': ivalue})
            time.sleep(self.pausetime)

        logfile.close()

        magdownplot.exportPDF(self.logfolder + filename_startime + 'MagDown' + '.pdf')
        magdownplot.close()  #close plot
        #app3 = None   #erase QApp (There can be only one)
            
        if mag_down_dict is not None:
            for (offset, thermometer) in enumerate(self.thermometers):
                time_string = "time_%i" % offset
                temp_string = "temperature_%i" % offset
                resist_string = "resistance_%i" % offset
                mag_down_dict[time_string] = magdownplotlines[offset].xdata
                mag_down_dict[temp_string] = magdownplotlines[offset].ydata
                mag_down_dict[resist_string] = data_dict[offset]['r']
            mag_down_dict['current'] = idownvalues


    def MonitorTemperature(self, stoptime = None, mag_hold_dict=None):
        '''
        Monitor Temperature between Mag up and down - stoptime is a time string 
        '''

        if stoptime is None:
            stoptime = time.localtime()

        filename_stoptime = time.strftime("%Y_%m_%d_%H_%M", stoptime)
        display_stoptime = time.strftime("%a, %d %b %Y %H:%M", stoptime)

        x = np.zeros(0, float)
        y = np.zeros(0, float)
        r = np.zeros(0, float)

        tempmonplot = dataplot_mpl.dataplot_mpl(title='MagHold '+display_stoptime, x_label="Time (min)", y_label='ADR Temperature (K)')
        plotlines = []
        for thermometer in self.thermometers:
            plotlines.append(tempmonplot.addLine(thermometer.name, x, y))      
        tempmonplot.show()
        b = self.app.processEvents()

        logfile = open(self.logfolder + filename_stoptime + 'MagHoldLog' + '.txt', 'w')

        t0 = time.time() #current time in seconds

        data_dict={}
        for (offset, thermometer) in enumerate(self.thermometers):
            data_dict[offset] = {}
            data_dict[offset]['t'] = np.zeros(0, float)
            data_dict[offset]['r'] = np.zeros(0, float)
            
        while time.time() < time.mktime(stoptime):
            x = (time.time()-t0)/60  #time in minutes
            for (offset, thermometer) in enumerate(self.thermometers):
                currentTemperature = self.tempcontrol.getTemperature(thermometer.address)
                currentResistance = self.tempcontrol.getResistance(thermometer.address)
                y = currentTemperature
                data_dict[offset]['t']=np.append(data_dict[offset]['t'], currentTemperature)
                data_dict[offset]['r']=np.append(data_dict[offset]['r'], currentResistance)
                #t[offset] = np.append(t[offset], currentTemperature)
                #r[offset] = np.append(r[offset], currentResistance)
                plotlines[offset].addPoint(x,y)
            tempmonplot.update()
            b = self.app.processEvents()
            logfile.write('%(first)f\t%(second)f\n' % {'first': x, 'second': currentTemperature})
            time.sleep(10)

        logfile.close()

        tempmonplot.exportPDF(self.logfolder + filename_stoptime + 'MagHold' + '.pdf')
        tempmonplot.close()  #close plot
        #app4 = None   #erase QApp (There can be only one)
            
        if mag_hold_dict is not None:
            for (offset, thermometer) in enumerate(self.thermometers):
                time_string = "time_%i" % offset
                temp_string = "temperature_%i" % offset
                resist_string = "resistance_%i" % offset
                mag_hold_dict[time_string] = plotlines[offset].xdata
                mag_hold_dict[temp_string] = plotlines[offset].ydata
                mag_hold_dict[resist_string] = data_dict[offset]['r']


    def AutoMag(self, StartHour=4, StartMinute=0, DaysFromNow=1, Maguptime=45, Magdowntime=60, Holdtime=180):
        '''
        Automag cycle - StartHour 0-23 and StartMinute 0-59 are integers, daysFrom Now is an integer and
        Maguptime, Magdowntime and Holdtime are in minutes
        '''

        print 'Starting AutoMag Sequence'
        
        # Fix time if attempting to start before now. 
        currenttime_array = time.localtime()
        currentHour = currenttime_array[3]
        currentMinute = currenttime_array[4]
        if DaysFromNow*24*60 + StartHour*60 + StartMinute < currentHour*60 + currentMinute:
            print "Fixing the times"
            StartHour = currentHour
            StartMinute = currentMinute

        # Create the dictionary
        #automag_dict = {}
        self.gamma = tespickle.TESPickle(self.logfolder + self.pickle_file_name)
        #self.gamma.gamma = automag_dict

        datestring = time.strftime("%Y-%m-%d %H:%M:%S", currenttime_array)
        print 'datestring', datestring
        self.gamma.gamma[datestring] = {}
        self.gamma.gamma[datestring]['MagUp'] = {}
        self.gamma.gamma[datestring]['MagHold'] = {}
        self.gamma.gamma[datestring]['MagDown'] = {}
        self.gamma.gamma[datestring]['MagMeasure'] = {}
        
        startMaguptime = self.TomorrowAtHour(timehour = StartHour, timeminute = StartMinute, daysfromnow = DaysFromNow)
        print 'Starting      Magup on ' + time.strftime("%a, %d %b %Y %H:%M", startMaguptime)

        startHoldtime = time.localtime(time.mktime(startMaguptime) + Holdtime*60)
        print 'Starting       Hold on ' + time.strftime("%a, %d %b %Y %H:%M", startHoldtime)

        startDemagtime = time.localtime(time.mktime(startMaguptime) + Maguptime*60 + Holdtime*60)

        openHeatSwitchtime = time.localtime(time.mktime(startDemagtime) - 3*60) # 3 minutes before Demag
        print 'Open Heat Switch    on ' + time.strftime("%a, %d %b %Y %H:%M", openHeatSwitchtime)
        print 'Starting      Demag on ' + time.strftime("%a, %d %b %Y %H:%M", startDemagtime)

        finishDemagtime = time.localtime(time.mktime(startDemagtime) + Magdowntime*60)
        print 'Should Finish Demag on ' + time.strftime("%a, %d %b %Y %H:%M", finishDemagtime)
               
        # Open heat switch
        print 'Closing Heat Switch ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        self.heatswitch.CloseHeatSwitch()

        print "Starting Magup ", time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

        self.MagUp(starttime=startMaguptime, maguptime=Maguptime, mag_up_dict=self.gamma.gamma[datestring]['MagUp'])

        print 'Finished Magup ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

        self.gamma.savePickle()

        # Mag Hold
        # monitor temperature until it is time to demag
        self.MonitorTemperature(stoptime=openHeatSwitchtime, mag_hold_dict=self.gamma.gamma[datestring]['MagHold'])

        self.gamma.savePickle()

        # Open heat switch
        print 'Opening Heat Switch ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        self.heatswitch.OpenHeatSwitch()

        # Demag
        print 'Starting Demag ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

        self.MagDown(starttime=startDemagtime, magdowntime=Magdowntime, mag_down_dict=self.gamma.gamma[datestring]['MagDown'])

        print 'Finished Demag ', time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

        self.gamma.savePickle()

        return datestring

           
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

        self.tempcontrol.magUpSetup()
        time.sleep(3)        

        print 'Lakeshore ready to ramp'

        # wait untul time to start
        while time.time() < time.mktime(starttime):
            timetillstart = (time.mktime(starttime)-time.time())/60
            #print 'Time to Magup %d minutes' % timetillstart
            time.sleep(30)

        currentHeaterOutput = self.tempcontrol.getManualHeaterOut() #Always start at current output

        magupsteps = math.ceil(maguptime*60/self.pausetime)
        iupbegin = currentHeaterOutput
        iupvalues = linspace(iupbegin,iupend,magupsteps)

        print 'Ramping Up....'

        #app2 = Qt.QApplication(sys.argv) #setup plot window
        maguplot = dataplot_mpl.dataplot_mpl() #setup plot
        maguplot.set_title('MagUp ' + display_startime)
        maguplot.set_y_axis_label('Resistance (Ohm)')
        maguplot.set_x_axis_label('ADR Temperature (K)')
        blank_array = []
        magupplotline = maguplot.addLine("Mag Up Temperature", blank_array, blank_array)

        logfile = open(logfolder + filename_startime + 'TcMagUpLog' + '.txt', 'w') #open logfile

        t0 = time.time() #current time in seconds

        for ivalue in iupvalues:
            self.tempcontrol.setManualHeaterOut(ivalue)
            #print ivalue
            time.sleep(self.pausetime)
            currentTemperature = self.tempcontrol.getTemperature()
            currentResistance = self.bridge.GetResistance()
            x = (time.time()-t0)/60  #time in minutes
            y = currentTemperature
            z = currentResistance
            magupplotline.addPoint(y,z)
            logfile.write('%(first)f\t%(second)f\t%(third)f\t%(fourth)f\n' % {'first': x, 'second': y, 'third': z, 'fourth': ivalue})
            maguplot.update()
            

        logfile.close()

        maguplot.exportPDF(logfolder + filename_startime + 'TcMagUp' + '.pdf')
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

        self.tempcontrol.demagSetup()
        time.sleep(3)

        print 'Lakeshore ready to demag'

        while time.time() < time.mktime(starttime):
            timetillstart = (time.mktime(starttime)-time.time())/60
            #print 'Time to Demag %d minutes' % timetillstart
            time.sleep(30)

        currentHeaterOutput = self.tempcontrol.getManualHeaterOut()

        magdownsteps = math.ceil(magdowntime*60/self.pausetime)
        idownbegin = currentHeaterOutput
        idownvalues = linspace(idownbegin,idownend,magdownsteps)

        print 'Ramping Down...'

        #app3 = Qt.QApplication(sys.argv) #setup plot window
        magdownplot = dataplot_mpl.dataplot_mpl()  #setup plot
        magdownplot.set_title('DeMag ' + display_startime)
        magdownplot.set_y_axis_label('Resistance (Ohm)')
        magdownplot.set_x_axis_label('ADR Temperature (K)')

        logfile = open(logfolder + filename_startime + 'TcMagDownLog' + '.txt', 'w')

        t0 = time.time()  #current time in seconds


        for ivalue in idownvalues:
            self.tempcontrol.setManualHeaterOut(ivalue)
            #print ivalue
            time.sleep(self.pausetime)
            currentTemperature = self.tempcontrol.getTemperature()
            currentResistance = self.bridge.GetResistance()
            x = (time.time()-t0)/60
            y = currentTemperature
            z = currentResistance
            magdownplot.addPoint(y,z)
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
        Monitor Temperature during a warm up rate 
            '''

        starttime = time.localtime()
        stoptime = time.localtime(time.mktime(starttime) + minutesToMeasure*60) 

        #filename_stoptime = time.strftime("%Y_%m_%d_%H_%M", stoptime)
        display_stoptime = time.strftime("%a, %d %b %Y %H:%M", stoptime)
        print display_stoptime

        tempmonplot = dataplot_mpl.dataplot_mpl()  #setup plot
        tempmonplot.set_title(filepath)
        tempmonplot.set_y_axis_label('ADR Temperature (K)')
        blank_array = []
        tempmonplotline = tempmonplot.addLine("Monitor Temperature", blank_array, blank_array)

        logfile = open(filepath + '.dat', 'w')

        t0 = time.time() #current time in seconds


        while time.time() < time.mktime(stoptime):
            currentTemperature = self.tempcontrol.getTemperature()
            x = (time.time()-t0)/60
            y = currentTemperature
            tempmonplotline.addPoint(x,y)
            logfile.write('%(first)f\t%(second)f\n' % {'first': x, 'second': y})
            time.sleep(2)

        logfile.close()

        tempmonplot.exportPDF(filepath + '.pdf')
        tempmonplot.close()  #close plot
           
