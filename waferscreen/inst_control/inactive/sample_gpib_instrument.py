'''
Created on Mar 11, 2009

@author: schimaf
'''

import gpib_instrument

class MyGpibInstrument(gpib_instrument.Gpib_Instrument):
    '''
    classdocs
    '''


    def __init__(self, pad, board_number = 0, name = '', sad = 0, timeout = 13, send_eoi = 1, eos_mode = 0):
        '''
        Constructor
        '''
        super(MyGpibInstrument, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)
        
        # GPIB identity string of the instrument
        self.id_string = "????"
        
        self.manufacturer = 'HP'
        self.model_number = '1234'
        self.description  = ''
        
        self.compare_identity()
        
    def mag_up(self):
        
        self.write('*ABC')
