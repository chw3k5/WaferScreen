'''
Created on Mar 11, 2009

@author: schimaf
'''

import gpib_instrument

class Keithley2700Multimeter(gpib_instrument.Gpib_Instrument):
    '''
    classdocs
    '''


    def __init__(self, pad, board_number = 0, name = '', sad = 0, timeout = 13, send_eoi = 1, eos_mode = 0):
        '''
        Constructor
        '''
        super(Keithley2700Multimeter, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)
        
        # GPIB identity string of the instrument
        self.id_string = "KEITHLEY INSTRUMENTS INC.,MODEL 2700,0822752,B02"
        
        self.manufacturer = 'Keithley'
        self.model_number = '2700'
        self.description  = 'Multimeter'
        
        self.compare_identity()
        
    def data(self):
        
        result = self.ask(':DATA?')
        print "result", result
        array = result.split(',')
        y = array[0]
        z = y[0:-3]
        voltage = float(z)
        
        return voltage