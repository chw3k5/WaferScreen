'''
Agilent 33220A
Created on October 11, 2009
@author: bennett
'''

# Future functions GetLoad and SetLoad, GetUnits and SetUnits

import gpib_instrument
from lookup import Lookup
from time import sleep

class Agilent33220A(gpib_instrument.Gpib_Instrument):
    '''
    The Agilent 33220A Arbitrary Function Generator GPIB communication class (Incomplete)
    '''


    def __init__(self, pad, board_number = 0, name = '', sad = 0, timeout = 17, send_eoi = 1, eos_mode = 0):
        '''
        Constructor  The PAD (Primary GPIB Address) is the only required parameter
	    '''

        super(Agilent33220A, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)
        
        # GPIB identity string of the instrument
        self.id_string = "Agilent Technologies,33220A,MY44036372,2.02-2.02-22-2"
        
        self.manufacturer = 'Agilent'
        self.model_number = '33220A'
        self.description  = 'Arbitrary Function Generator'
        
        #self.compare_identity()
        
        self.vmax = 5.0 #assumes 50 Ohm load setting

        
    def SetFunction(self, function = 'sine'):
        '''
        Set Output Function Type
        '''
        
        if function == 'sine':
            functionstring = 'SINusoid'
        elif function == 'square':
            functionstring = 'SQUare'
        elif function == 'ramp':
            functionstring = 'RAMP'
        elif function == 'pulse':
            functionstring = 'PULSe'
        elif function == 'noise':
            functionstring = 'NOISe'
        elif function == 'dc':
            functionstring = 'DC'
        elif function == 'user':
            functionstring = 'USER'
        else:
            print 'Inva;if type of function'
            functionstring = ''

        commandstring = 'FUNCtion ' + functionstring
        self.write(commandstring)
        
    def GetFunction(self):
        '''Get the current function type'''
        
        commandstring = 'FUNCtion?'
        result = self.ask(commandstring)
        function = result
        
        return function

    def SetFrequency(self, frequency = 100):
        '''
        Set the output frequency in Hz
        '''

        function = self.GetFunction()

        if function == 'SIN': 
            if frequency > 20e6:
                print 'Greater then max frequency'
                frequency = 20e6
            if frequency < 1e-6:
                print 'Smaller then min frequency'
                frequency = 1e-6
        if function == 'SQU':
            if frequency > 20e6:
                print 'Greater then max frequency'
                frequency = 20e6
            if frequency < 1e-6:
                print 'Smaller then min frequency'
                frequency = 1e-6
        if function == 'RAMP':
            if frequency > 200e3:
                print 'Greater then max frequency'
                frequency = 200e3
            if frequency < 1e-6:
                print 'Smaller then min frequency'
                frequency = 1e-6
        if function == 'PULS':
            if frequency > 5e6:
                print 'Greater then max frequency'
                frequency = 5e6
            if frequency < 500e-6:
                print 'Smaller then min frequency'
                frequency = 500e-6
        if function == 'NOIS':
            print 'Frequency not applicable for Noise'
        if function == 'DC':
            print 'Frequency not applicable for DC'
        if function == 'USER':
            if frequency > 6e6:
                print 'Greater then max frequency'
                frequency = 6e6
            if frequency < 1e-6:
                print 'Smaller then min frequency'
                frequency = 1e-6

        frequencystring = str(frequency)
        commandstring = 'FREQuency ' + frequencystring
        self.write(commandstring)


    def GetFrequency(self):
        '''Get the current frequencye'''
        
        commandstring = 'FREQuency?'
        result = self.ask(commandstring)
        frequency = float(result)
        
        return frequency

    def SetAmplitude(self, amplitude = 0.1):
        '''
        Set the output amplitude in volts
        '''

        vmax = 5.0 #assumes 50 Ohm load setting
        offset = self.GetOffset()

        if amplitude < 0.010:
            print 'Amplitude is below minimum'
            amplitude = 0.010
            
        if amplitude > 5.0:
            print 'Amplitude greater than Max Voltage'
        elif amplitude/2.0+abs(offset) > vmax:
            print 'Combination of amplitude and offset greater than 5V. Offset will be modified.'

        amplitudestring = str(amplitude)
        commandstring = 'VOLTage ' + amplitudestring
        self.write(commandstring)

    def GetAmplitude(self):
        '''Get the current amplitude'''
        
        commandstring = 'VOLTage?'
        result = self.ask(commandstring)
        amplitude = float(result)
        
        return amplitude
        
    def SetOffset(self, offset):
        '''Set the offset voltage'''
    
        amplitude = self.GetAmplitude()
        
        if amplitude/2.0+abs(offset) > self.vmax:
            print 'Combination of amplitude and offset greater than 5V. Amplitude will be modified.'        
        
        offsetstring = str(offset)
        commandstring = 'VOLTage:OFFSet ' + offsetstring
        self.write(commandstring)        

    def GetOffset(self):
        '''Get the current offset voltage'''
        
        commandstring = 'VOLTage:OFFSet?'
        result = self.ask(commandstring)
        offset = float(result)
        
        return offset
             
    def SetVoltageHigh(self, vhigh):
        '''Set the high voltage'''
    
        vlow = self.GetVoltageLow()
        
        if vhigh > self.vmax:
            print 'Requested voltage is greater than vmax'
            vhigh = self.vmax
        if vhigh < vlow:
            print 'Requested voltage is less then low voltage'
        
        voltagestring = str(vhigh)
        commandstring = 'VOLTage:HIGH ' + voltagestring
        self.write(commandstring)        

    def GetVoltageHigh(self):
        '''Get the current high voltage'''
        
        commandstring = 'VOLTage:HIGH?'
        result = self.ask(commandstring)
        vhigh = float(result)
        
        return vhigh        
        
    def SetVoltageLow(self, vlow):
        '''Set the low voltage'''
    
        vhigh = self.GetVoltageHigh()
        
        if vlow < -1*self.vmax:
            print 'Requested voltage is less than vmin'
            vlow = -1*self.vmax
        if vlow > vhigh:
            print 'Requested voltage is greater then high voltage'
        
        voltagestring = str(vlow)
        commandstring = 'VOLTage:LOW ' + voltagestring
        self.write(commandstring)        

    def GetVoltageLow(self):
        '''Get the current low voltage'''
        
        commandstring = 'VOLTage:LOW?'
        result = self.ask(commandstring)
        vlow = float(result)
        
        return vlow       
        
    def SetOutput(self, outputstate):
        '''Set the state of the output 'off' or 'on' '''

        if outputstate != 'on' and outputstate != 'off':
            print 'Invalid output state, setting to off'
            outputstate = 'off'
            
        commandstring = 'OUTPut ' + outputstate
        self.write(commandstring)        

             
    def SetPulsePeriod(self, period):
        '''Set the pulse period'''
        
        periodstring = str(period)
        commandstring = 'PULSe:PERiod ' + periodstring
        self.write(commandstring)        

    def GetPulsePeriod(self):
        '''Get the pulse period'''
        
        commandstring = 'PULSe:PERiod?'
        result = self.ask(commandstring)
        period = float(result)
        
        return period        
            
    def SetPulseWidth(self, width):
        '''Set the pulse width'''
        
        widthstring = str(width)
        commandstring = 'FUNCtion:PULSe:WIDTh ' + widthstring
        self.write(commandstring)        

    def GetPulseWidth(self):
        '''Get the pulse width'''
        
        commandstring = 'FUNCtion:PULSe:WIDTh?'
        result = self.ask(commandstring)
        width = float(result)
        
        return width 

            
    def SetPulseEdgeTime(self, edgetime):
        '''Set the pulse edge time'''
        
        edgetimestring = str(edgetime)
        commandstring = 'FUNCtion:PULSe:TRANsition ' + edgetimestring
        self.write(commandstring)        

    def GetPulseEdgeTime(self):
        '''Get the pulse width'''
        
        commandstring = 'FUNCtion:PULSe:TRANsition?'
        result = self.ask(commandstring)
        edgetime = float(result)
        
        return edgetime 

    def GetOutput(self):
        '''Get the state of the output 'off' or 'on' '''
        
        commandstring = 'OUTPut?'
        result = self.ask(commandstring)
        if result == '0':
            state = 'off'
        elif result == '1':
            state = 'on'
        else:
            print 'Error querrying state'
            state = 'error'
        
        return state      

    def GetListOfArbWaveform(self):
        ''' Return a list of stings that are the names of the waveforms in memory'''
        
        commandstring = 'DATA:CATalog?'
        result = self.ask(commandstring)
         
        catalog = result.split(',')      # split into a list
        for k in range(len(catalog)):    # loop over list
            catalog[k]=catalog[k][1:-1]  # strip leading and trailing quotes
             
        return catalog    

        
    def SelectArbWaveform(self, waveform_name = 'VOLATILE'):
        '''Select the arbitrary waveform to output '''

        catalog = self.GetListOfArbWaveform()
        if waveform_name not in catalog:
            print 'Wavform does not exist. Setting to VOLATILE'
            waveform_name = 'VOLATILE'
            if waveform_name not in catalog:
                print 'VOLATILE does not exist. Setting to EXP_RISE'
                waveform_name = 'EXP_RISE'
            
        commandstring = 'FUNCtion:USER ' + waveform_name
        self.write(commandstring)        

    def GetSelectedArbWaveform(self):
        '''Get the currently selected abr waveform '''
        
        commandstring = 'FUNCtion:USER?'
        result = self.ask(commandstring)
        waveform_name = result
        
        return waveform_name 
        
    def SendArbWaveform(self, waveform):
        '''Send the arbitrary waeform to volatile memory '''

        waveliststring = str(list(waveform)) #turn array or whetever to a list and then string
        datastring = waveliststring[1:-1] # strip off the brackets on the end
            
        commandstring = 'DATA VOLATILE, ' + datastring
        self.write(commandstring)        
