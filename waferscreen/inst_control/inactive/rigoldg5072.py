'''
Rigol DG5072
Created on August 11, 2016
@author: cpappas
'''

import gpib_instrument


class Rigoldg5072(gpib_instrument.Gpib_Instrument):
    '''
    The Rigol DG 5072 GPIB communication class (Incomplete)
    '''


    def __init__(self, pad, board_number = 0, name = '', sad = 0, timeout = 17, send_eoi = 1, eos_mode = 0):
        '''
        Constructor  The PAD (Primary GPIB Address) is the only required parameter
	    '''

        super(Rigoldg5072, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)

        
    def SetFunction(self, type,channel,freq,amp,offset,phase):
        '''
        Set Output Sine Function on channel specified, with amp in Volts and freq in Hz
	enter type as 'USER' for arbitrary waveform, 'SINusoid' for sine wave
        '''
        print str(freq),str(amp),str(channel) 
        commandstring = ':SOURce'+str(channel)+':APPLy:'+str(type)+' '+str(freq)+','+str(amp)+','+str(offset)+','+str(phase)
        self.write(commandstring)
        
    def GetFunction(self,channel):
        '''Get the current function on channel specified'''
        
        commandstring = ':SOURce'+str(channel)+':APPLy?'
        result = self.ask(commandstring)
        return result

    def OutputIO(self,channel,command):
        '''Turns channel output on or off'''
        commandstring = 'OUTPut'+str(channel)+' '+str(command)
        self.write(commandstring) 
