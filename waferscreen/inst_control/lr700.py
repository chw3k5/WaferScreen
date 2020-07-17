'''
LR700 
Created on Augest 15, 2009
@author: bennett
'''

import gpib_instrument
from lookup import Lookup
from time import sleep

class LR700(gpib_instrument.Gpib_Instrument):
    '''
    The LR700 AC Bridge GPIB communication class (Incomplete)
    '''


    def __init__(self, pad, board_number = 0, name = '', sad = 0, timeout = 17, send_eoi = 1, eos_mode = 0):
        '''
        Constructor  The PAD (Primary GPIB Address) is the only required parameter
        '''

        super(LR700, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)
        
        # GPIB identity string of the instrument
        self.id_string = "Needtolookup"
        
        self.manufacturer = 'Linear Research'
        self.model_number = '700'
        self.description  = 'AC Resistance Bridge'
        
        #self.compare_identity()

        
    def GetResistance(self):
        '''
        Get resistance from a given channel as a float
        '''
        
        commandstring = 'GET 0'
        result = self.ask(commandstring)


        valuestrings = result.split()
	#print valuestrings
        if valuestrings[2] is not 'R':
            print 'Error in read - Did not retuen a R'
        value = float(valuestrings[0])
        units = valuestrings[1]

        if units == 'KOHM':
            multiplier = 1e3
        elif units == 'OHM':
            multiplier = 1
        elif units == 'MOHM':
            multiplier = 1e-3
        elif units == 'UOHM':
            multiplier = 1e-6
        else:
            multiplier = 1
            print 'Error - No Matching Units'

        resistance = value * multiplier
        
        return resistance


