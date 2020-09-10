'''
SRS Sim928 Isolated Voltage Source
Created on October 24, 2014
@author: bennettd
'''

import gpib_instrument
from lookup import Lookup
from time import sleep
import serial_instrument
import serial

class SRS_SIM928(serial_instrument.SerialInstrument):
    """
    The SRS SIM928 Isolated Voltage Source *serial* communication class (Incomplete)
    """


    def __init__(self, port='srs', sim_port = 1):
        '''
        Constructor  The PAD (Primary GPIB Address) is the only required parameter
	    '''

        super(SRS_SIM928, self).__init__(port, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
        

        self.manufacturer = 'Stanford Research Systems'
        self.model_number = 'SIM928'
        self.description  = 'Isolated Voltage Source'
        
        self.sim_port = sim_port
        
        #self.compare_identity()
        
        self.vmax = 10.0
        self.vmin = 10.0

    def simWrite(self, sim_port, cmd):
        '''Write a command to one of the SIM ports.'''
        
        commandstring = 'SNDT ' + str(sim_port) + ', "' + cmd + '"'
        self.write(commandstring)
        
    def simWriteRead(self, sim_port, cmd, max_bytes=80):
        
        commandstring = 'SNDT ' + str(sim_port) +', "' + cmd + '"'
        self.write(commandstring)
        sleep(0.03)
        recievestring = 'GETN? '+ str(sim_port) + ', ' + str(max_bytes)
        result = self.ask(recievestring)

        return result

    def simPortInputBytes(self):
        
        recievestring = 'NINP? '+ str(self.sim_port)
        result = self.ask(recievestring)
        
        return result   
    
    def simPortOutputBytes(self):
        
        recievestring = 'NOUT? '+ str(self.sim_port)
        result = self.ask(recievestring)
        
        return result     

    def setOutputOn(self):
        '''Set the voltage'''
            
        cmd = 'OPON'
        self.simWrite(self.sim_port, cmd)

    def setOutputOff(self):
        '''Set the voltage'''
            
        cmd = 'OPOF'
        self.simWrite(self.sim_port, cmd)
        
    def setVoltage(self, voltage):
        '''Set the voltage'''
            
        cmd = 'VOLT ' + str(voltage)
        self.simWrite(self.sim_port, cmd)
        
    def setvolt(self,voltage):
        '''Wrapper for SetVoltage. '''
        
        self.setVoltage(voltage)

    def getVoltage(self):
        '''Get the current offset voltage'''
        
        cmd = 'VOLT?'
        result = self.simWriteRead(self.sim_port, cmd)
        float_answer = float(result[5:])
        
        return float_answer
