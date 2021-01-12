'''
Agilent 34401A
Created on Augest 15, 2009
@author: bennett, schimaf
'''

import gpib_instrument


class HP34401a(gpib_instrument.Gpib_Instrument):
    '''
    The Agilent 34401A Multimeter GPIB communication class (Incomplete)
    '''


    def __init__(self, pad, board_number = 0, name = '', sad = 0, timeout = 17, send_eoi = 1, eos_mode = 0):
        '''
        Constructor  The PAD (Primary GPIB Address) is the only required parameter
        '''

        super(HP34401a, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)
        
        # GPIB identity string of the instrument
        self.id_string = "HEWLETT-PACKARD,34401A,0,11-5-2"
        
        self.manufacturer = 'Agilent'
        self.model_number = '34401A'
        self.description  = '6.5 Digit Multimeter'
        
        #self.compare_identity()

        
    def GetVoltage(self):
        '''
        Get Voltage
        '''
        
        commandstring = 'MEAS:VOLT:DC?'
        result = self.ask(commandstring)

        voltage = float(result)
        
        return voltage


