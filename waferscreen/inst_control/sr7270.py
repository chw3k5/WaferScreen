import math
from time import sleep
import time
import struct
import numpy

import serial_instrument

#########################################################################
#
# Zaber Stepper Motor Class
#
# Class to control the the signal recovery lock-in amplifier via serial 
# port.
#
# by Doug Bennett
##########################################################################


class SR7270(serial_instrument.SerialInstrument):

######################################################################################
    # Zaber class

    def __init__(self, port='lockin', baud=19200, shared=True, unit=0):
        '''Serial - parameters:
        port - a logical portname defined in namedserialrc
        baud -  19200 for lock-in 
        shared - allow other processes to open this device
                 only works on posix
        unit - Unit number. 0 for all. 
        '''

        super(SR7270, self).__init__(port, baud, shared)

        self.manufacturer = 'Ametek'
        self.model_number = '7270'

        self.port = port
        self.baud = baud
        self.shared = shared
        self.unit = unit

########################################### Private Methods #################################################

    def __sendCommand(self, cmd):
        '''send a command over the serial port '''
        self.serial.write(cmd)


    def __askFloat(self, cmd):
        '''send a command and get a float in return. Has error handling for empty returns.'''
        self.serial.write(cmd)
        result = self.serial.readline()
        float_result = numpy.nan
        if len(result) > 0:
            # If the number is the first thing returned after a quary it will have a * in front
            if result[0] == '*':
                float_result = float(result[1:])
            else:
                float_result = float(result)
        
        return float_result

########################################### Public Methods #################################################


    def close(self):
        self.serial.close()

    def setInputMode(self, state='voltage'):
        '''Set the input mode configuration of the lock-in.'''
        
        if state == 'voltage':
            cmd = 'IMODE 0\r\n'
        elif state == 'current_high':
            cmd = 'IMODE 1\r\n'
        elif state == 'current_low':
            cmd = 'IMODE 2\r\n'
        else:
            print('Imode state is not valid')
            cmd = 'IMODE 0\r\n'
            
        self.__sendCommand(cmd)

    def setVMode(self, state='A-B'):
        '''Set the voltage input configuration of the lock-in.'''
        
        if state == 'A':
            cmd = 'VMODE 1\r\n'
        elif state == 'A-B':
            cmd = 'VMODE 3\r\n'
        elif state == '-B':
            cmd = 'VMODE 2\r\n'
        elif state == 'ground':
            cmd = 'VMODE 0\r\n'
        else:
            print('Vmode state is not valid')
            cmd = 'VMODE 3\r\n'
            
        self.__sendCommand(cmd)

    def setSignalShieldFloat(self, state='ground'):
        '''Set the state of the shield of the input connectors.'''
        
        if state == 'float':
            cmd = 'FLOAT 1\r\n'
        elif state == 'ground':
            cmd = 'FLOAT 0\r\n'
        else:
            print('Shield state is not valid')
            cmd = 'FLOAT 0\r\n'
            
        self.__sendCommand(cmd)

    def setInputCouplingState(self, state='dc'):
        '''Set the state of the shield of the input connectors.'''
        
        if state == 'dc':
            cmd = 'DCCOUPLE 1\r\n'
        elif state == 'ac':
            cmd = 'DCCOUPLE 0\r\n'
        else:
            print('Input coupling state is not valid')
            cmd = 'DCCOUPLE 1\r\n'
            
        self.__sendCommand(cmd)

    def setSensitivity(self, sense='21'):
        '''Set the sensitivity of the lock-in.'''
        
        #Put in the ranges
        
        cmd = 'SEN 21 1\r\n'
            
        self.__sendCommand(cmd)

    def setAutoSensitivity(self):
        '''Set the sensitivity level automatically based on the input.'''
        
        cmd = 'AS\r\n'
            
        self.__sendCommand(cmd)

    def setAutoMeasure(self):
        '''Set the sensitivity level automatically and perform auto-phase
        to maximize X and minimize Y.'''
        
        cmd = 'ASM\r\n'
            
        self.__sendCommand(cmd)

    def setAutoACGain(self, state='auto'):
        '''Set the state of auto AC gain control.'''
        
        if state == 'auto':
            cmd = 'AUTOMATIC 1\r\n'
        elif state == 'manual':
            cmd = 'AUTOMATIC 0\r\n'
        else:
            print('Auto AC Gain State is not valid')
            cmd = 'AUTOMATIC 0\r\n'
            
        self.__sendCommand(cmd)

    def setLineFreqFilter(self, state='60Hz'):
        '''Set the state of the line frequency filter.'''
        
        if state == 'off':
            cmd = 'LF 0 0\r\n'
        elif state == '60Hz':
            cmd = 'LF 1 0\r\n'
        elif state == '120Hz':
            cmd = 'LF 2 0\r\n'
        elif state == 'both':
            cmd = 'LF 3 0\r\n'
        else:
            print('Line frequency filter selection is not valid')
            cmd = 'LF 1 0\r\n'
            
        self.__sendCommand(cmd)

    def setReferenceMode(self, state='single'):
        '''Set the reference mode for the lock-in.'''
        
        if state == 'single':
            cmd = 'REFMODE 0\r\n'
        elif state == 'dual_harmonic':
            cmd = 'REFMODE 1\r\n'
        elif state == 'dual_reference':
            cmd = 'REFMODE 2\r\n'
        else:
            print('Reference mode is not valid')
            cmd = 'REFMODE 0\r\n'
            
        self.__sendCommand(cmd)

    def setReferenceSource(self, state='internal'):
        '''Set the source channel of the reference channel.'''
        
        if state == 'internal':
            cmd = 'IE 0\r\n'
        elif state == 'external_rear':
            cmd = 'IE 1\r\n'
        elif state == 'external_front':
            cmd = 'IE 2\r\n'
        else:
            print('Reference channel is not valid')
            cmd = 'IE 0\r\n'
            
        self.__sendCommand(cmd)

    def setAutoPhase(self):
        '''Automatically null the phase.'''
        
        cmd = 'AQN\r\n'
            
        self.__sendCommand(cmd)

    def getX(self):
        '''Return the measured X channel as a float.'''
        
        cmd = 'X.\r\n'
        result = self.__askFloat(cmd)
        
        return result

    def getY(self):
        '''Return the measured Y channel as a float.'''
        
        cmd = 'Y.\r\n'
        result = self.__askFloat(cmd)
        
        return result

    def getMag(self, simulate=False):
        '''Return the measured magnitude as a float.'''
        
        cmd = 'MAG.\r\n'
        if simulate is True:
            result = time.time()
        else:
            result = self.__askFloat(cmd)
        
        return result

    def getPhase(self):
        '''Return the measured phase as a float.'''
        
        cmd = 'PHA.\r\n'
        result = self.__askFloat(cmd)
        
        return result

    def setIntOscAmp(self, voltage_level=1.0):
        '''Set the voltage level of the internal oscillator (0 to 5 V rms).'''
        
        if voltage_level > 5:
            osc_voltage = 5.0
        elif voltage_level < 0:
            osc_voltage = 0.0
        else:
            osc_voltage = voltage_level
            
        cmd = 'OA. ' + str(osc_voltage) + '\r\n'
            
        self.__sendCommand(cmd)

    def setIntOscFreq(self, frequency=100.0):
        '''Set the frequency (in Hz) of the internal oscillator (0 to 250 kHz).'''
        
        if frequency > 2.5e5:
            osc_frequency = 2.5e5
        elif frequency < 0:
            osc_frequency = 0.0
        else:
            osc_frequency = frequency
            
        cmd = 'OF. ' + str(osc_frequency) + '\r\n'
            
        self.__sendCommand(cmd)
        
    def setDisplayMode(self, state='on'):
        '''Turn the display off and on.'''
        
        if state == 'on':
            cmd = 'LTS 1\r\n'
        elif state == 'off':
            cmd = 'LTS 0\r\n'
        else:
            print('Display mode is not valid')
            cmd = 'LTS 1\r\n'
            
        self.__sendCommand(cmd)