#! /usr/bin/env python
import sys
from PyQt4 import Qt
import adrcontrol
from time import sleep

import bluebox
#import clock_card as clock
#import dfb_card as dfb
#import ra8_card as ra8

minutesToMeasure = 1
root_directory = '/home/pcuser/data/texas/20090929/'
voltage_source_select='tower'
bias_address=19
normal_volt = 2.0
pause_after_bias_set = 2  #in seconds

def main():

    qtapp = Qt.QApplication(sys.argv)  #setup plot window

    adr = adrcontrol.Adrcontrol(app = qtapp)
    bias_source0 = bluebox.BlueBox(port='vbox', version=voltage_source_select, address=bias_address, channel=0)
    bias_source1 = bluebox.BlueBox(port='vbox', version=voltage_source_select, address=bias_address, channel=1)
    bias_source2 = bluebox.BlueBox(port='vbox', version=voltage_source_select, address=bias_address, channel=2)
    bias_source3 = bluebox.BlueBox(port='vbox', version=voltage_source_select, address=bias_address, channel=3)
    bias_source4 = bluebox.BlueBox(port='vbox', version=voltage_source_select, address=bias_address, channel=4)
    bias_source5 = bluebox.BlueBox(port='vbox', version=voltage_source_select, address=bias_address, channel=5)    
    bias_source6= bluebox.BlueBox(port='vbox', version=voltage_source_select, address=bias_address, channel=6)
    bias_source7 = bluebox.BlueBox(port='vbox', version=voltage_source_select, address=bias_address, channel=7)

    sleep(2)

    print 'Base Warm Up Rate' 
    
    bias_source0.setvolt(0)
    bias_source1.setvolt(0)
    bias_source2.setvolt(0)
    bias_source3.setvolt(0)
    bias_source4.setvolt(0)
    bias_source5.setvolt(0)
    bias_source6.setvolt(0)
    bias_source7.setvolt(0)
        
    sleep(pause_after_bias_set)
        
    filepath = root_directory + 'BaseWarmUp'
    adr.MonitorWarmUpRate(minutesToMeasure = minutesToMeasure, filepath = filepath)

    bias_source0.setvolt(normal_volt)
    bias_source1.setvolt(0)
    bias_source2.setvolt(0)
    bias_source3.setvolt(0)
    bias_source4.setvolt(0)
    bias_source5.setvolt(0)
    bias_source6.setvolt(0)
    bias_source7.setvolt(0)
    
    sleep(pause_after_bias_set)    

    print 'One Bay On'
    filepath = root_directory + 'OneBaysOn'
    adr.MonitorWarmUpRate(minutesToMeasure = minutesToMeasure, filepath = filepath)    

    bias_source0.setvolt(normal_volt)
    bias_source1.setvolt(normal_volt)
    bias_source2.setvolt(normal_volt)
    bias_source3.setvolt(normal_volt)
    bias_source4.setvolt(0)
    bias_source5.setvolt(0)
    bias_source6.setvolt(0)
    bias_source7.setvolt(0)
    
    sleep(pause_after_bias_set)    

    print 'Four Bays On'
    filepath = root_directory + 'FourBaysOn'
    adr.MonitorWarmUpRate(minutesToMeasure = minutesToMeasure, filepath = filepath)
    
    bias_source0.setvolt(normal_volt)
    bias_source1.setvolt(normal_volt)
    bias_source2.setvolt(normal_volt)
    bias_source3.setvolt(normal_volt)
    bias_source4.setvolt(normal_volt)
    bias_source5.setvolt(normal_volt)
    bias_source6.setvolt(normal_volt)
    bias_source7.setvolt(normal_volt)

    sleep(pause_after_bias_set)

    print 'Eight Bays On'
    filepath = root_directory + 'EightBaysOn'
    adr.MonitorWarmUpRate(minutesToMeasure = minutesToMeasure, filepath = filepath)        


if __name__ == '__main__': main()

