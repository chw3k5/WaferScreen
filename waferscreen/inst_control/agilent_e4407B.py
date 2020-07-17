'''
Created on April 16th, 2015

@author: bennettd
'''
import numpy
import pylab
import gpib_instrument
from time import sleep

class AgilentE4407B(gpib_instrument.Gpib_Instrument):
    '''
    Agililent E4407B control class
    '''

    def __init__(self, pad, board_number = 0, name = '', sad = 0, timeout = 13, send_eoi = 1, eos_mode = 0):
        '''Constructor - The PAD (Primary GPIB Address) is the only required parameter '''

        super(AgilentE4407B, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)
        
        # GPIB identity string of the instrument
        self.id_string = "Hewlett-Packard, E4407B, SG44210888, A.14.01"
        self.manufacturer = 'Agilent'
        self.model_number = 'E4407B'
        self.description  = 'Spectrum Analyzer'

    def identifyInstrument(self):
        '''Get the identiy string from instruement'''
        
        inst_idn = self.ask('*IDN?')
        print inst_idn

    def setCenterFrequency(self, frequency = 100):
        '''
        Set the center frequency in Hz
        '''
        frequencystring = str(frequency)
        commandstring = 'SENS:FREQ:CENT ' + frequencystring
        self.write(commandstring)

    def setSpanFrequency(self, frequency = 100):
        '''
        Set the span frequency in Hz
        '''
        frequencystring = str(frequency)
        commandstring = 'SENS:FREQ:SPAN ' + frequencystring
        self.write(commandstring)

    def getStartFrequency(self):
        '''
        Get the start frequency in Hz
        '''

        commandstring = 'SENS:FREQ:STAR?'
        result = self.ask(commandstring)
        value = float(result)
        
        return value

    def getStopFrequency(self):
        '''
        Get the stop frequency in Hz
        '''

        commandstring = 'SENS:FREQ:STOP?'
        result = self.ask(commandstring)
        value = float(result)
        
        return value

    def getTrace(self, trace=1):
        '''
        result = measureCurrent(output)
        output = "P6V" or "P25V" or "N25V"
        P6V  =  +6V output
        P25V = +25V output
        N25V = -25V output
        Measure one of the currents from the specified output
        '''
        
        if trace > 3 or trace < 1:
            print('Not a valid trace!')
            trace = 1
        
        commandstring = 'TRAC:DATA? TRACE' + str(int(trace))
        self.write(commandstring)
        result = self.read(20480)
        str_array = numpy.array(result.split(','))
        data_array = str_array.astype(numpy.float)
        
        return data_array
    
    def getSpectrum(self, trace=1):
        
        psd = self.getTrace(trace)
        start_freq = self.getStartFrequency()
        stop_freq = self.getStopFrequency()
        pnts = len(psd)
        freqs = numpy.linspace(start_freq, stop_freq, pnts)
        data_array = numpy.vstack((freqs,psd))
        return data_array
    
    def plotSpectrum(self, trace=1, file_name=None):
        
        data_array = self.getSpectrum(trace)
        if file_name is not None:
            numpy.savetxt(file_name, data_array.transpose())
        pylab.plot(data_array[0],data_array[1])
        pylab.xlabel('Frequency (Hz)')
        pylab.ylabel('Power (dB)')
        
        pylab.show()
        
