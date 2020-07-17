'''
Created on Mar 3, 2009

@author: schimaf
@version: 1.0.0
'''

#import time

import instrument
from gpibinter import ibdev, ibfind, ibonl, ibcmd, ibcmda, ibclr, ibwrt, ibwrta, ibrd, ibln, ibwait, ibsta
import numpy

# Constants
RQS = (1<<11)
SRQ = (1<<12)
TIMO = (1<<14)

class Gpib_Instrument(instrument.Instrument):
    '''
    Base class for GPIB controlled instrument
    '''

    def __init__(self, board_number = 0, name = '', pad = None, sad = 0, timeout = 13, send_eoi = 1, eos_mode = 0):
        super(Gpib_Instrument, self).__init__()
        
        self._own = False
        self.id_string = ""
        self.res = ""
        
        self.board_number = board_number
        self.name = name
        self.pad = pad
        self.sad = sad
        self.timeout = timeout
        self.send_eoi = send_eoi
        self.eos_mode = eos_mode
        
        if len(name) > 0:
            self.id = ibfind(name)
            self._own = True
#        elif pad is None:
#            self.id = name
        else:
            self.id = ibdev(board_number, pad, sad, timeout, send_eoi, eos_mode)
            self._own = True
    
    # automatically close descriptor when instance is deleted
    def __del__(self):
        if self._own:
            ibonl(self.id, 0)
            
    def __repr__(self):
        return "%s(%d)" % (self.__class__.__name__, self.id)

    def command(self, string):
        ibcmd(self.id, string)
    
    def command_async(self, string):
        ibcmda(self.id, string)
    
    def interface_clear(self):
        ibclr(self.id)
    
    def online(self, boolean):
        if boolean == True:
            ibonl(self.id, 1)
        else:
            ibonl(self.id, 0)
    
    def write(self, string):
        ibwrt(self.id, string)

    def write_async(self, string):
        ibwrta(self.id, string)
    
    def read(self, strlen=512):
        self.res = str(ibrd(self.id, strlen))
        # Cut of the junk characters by looking for a carriage return or line feed. 
        split_array = self.res.replace('\n', '\r').split('\r')
        return split_array[0]
    
    def rawread(self, strlen=512):
        self.res = str(ibrd(self.id, strlen))
        return self.res

    def ask(self, x):
        self.write(x)
        result = self.read()
        return result

    def askFloat(self, string):
        '''
        send a command and get a float in return. Has error handling for empty returns.
        '''
        self.write(string)
        result = self.read()
        float_result = numpy.nan
        if len(result) > 0:
            float_result = float(result)
        
        return float_result

    def listener(self, pad, sad=0):
        self.res = ibln(self.id, pad, sad)
        return self.res

    def clear(self):
        ibclr(self.id)
        
    def wait(self, mask):
        ibwait(self.id,mask)
    
    def ibsta(self):
        self.res = ibsta()
        return self.res

    def reset(self):
        self.write('*RST')
        
    def identify(self):
        self.write('*IDN?')
        self.res = self.read()
        return self.res
        
    def clear_status(self):
        self.write('*CLS')
        
    def compare_identity(self, maxlen = -1):
        
        string = self.identify()
        if maxlen == -1:
            length = len(string)
        else:
            length = maxlen
        if string[:length] != self.id_string[:length]:
            print "This is not a %s %s" % (self.manufacturer, self.model_number)
