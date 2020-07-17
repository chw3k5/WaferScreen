'''
SRS Sim928 Isolated Voltage Source
Created on October 24, 2014
@author: bennettd
'''

import gpib_instrument
from lookup import Lookup
from time import sleep

class SRS_SIM928(gpib_instrument.Gpib_Instrument):
    '''
    The SRS SIM928 Isolated Voltage Source GPIB communication class (Incomplete)
    '''


    def __init__(self, pad, port, board_number = 0, name = '', sad = 0, timeout = 17, send_eoi = 1, eos_mode = 0):
        '''
        Constructor  The PAD (Primary GPIB Address) is the only required parameter
	    '''

        super(SRS_SIM928, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)
        
        # GPIB identity string of the instrument
        #self.id_string = "Agilent Technologies,33220A,MY44036372,2.02-2.02-22-2"
        
        self.manufacturer = 'Stanford Research Systems'
        self.model_number = 'SIM928'
        self.description  = 'Isolated Voltage Source'
        
        self.port = port
        
        #self.compare_identity()
        
        self.vmax = 10.0
        self.vmin = 10.0

    def simWrite(self, port, cmd):
        '''Write a command to one of the SIM ports.'''
        
        commandstring = 'SNDT ' + str(port) + ', "' + cmd + '"'
        self.write(commandstring)
        
    def simWriteRead(self, port, cmd, max_bytes=80):
        
        commandstring = 'SNDT ' + str(port) +', "' + cmd + '"'
        self.write(commandstring)
        sleep(0.03)
        recievestring = 'GETN? '+ str(port) + ', ' + str(max_bytes)
        result = self.ask(recievestring)

        return result

    def simPortInputBytes(self):
        
        recievestring = 'NINP? '+ str(self.port)
        result = self.ask(recievestring)
        
        return result   
    
    def simPortOutputBytes(self, port):
        
        recievestring = 'NOUT? '+ str(self.port)
        result = self.ask(recievestring)
        
        return result     

    def setOutputOn(self):
        '''Set the voltage'''
            
        cmd = 'OPON'
        self.simWrite(self.port, cmd)

    def setOutputOff(self):
        '''Set the voltage'''
            
        cmd = 'OPOF'
        self.simWrite(self.port, cmd)
        
    def setVoltage(self, voltage):
        '''Set the voltage'''
            
        cmd = 'VOLT ' + str(voltage)
        self.simWrite(self.port, cmd)
        
    def setvolt(self,voltage):
        '''Wrapper for SetVoltage. '''
        
        self.setVoltage(voltage)

    def getVoltage(self):
        '''Get the current offset voltage'''
        
        cmd = 'VOLT?'
        result = self.simWriteRead(self.port, cmd)
        float_answer = float(result[5:])
        
        return float_answer