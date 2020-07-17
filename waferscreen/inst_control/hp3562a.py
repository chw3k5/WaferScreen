'''
HP3562A Dynamic Signal Analyzer
Created on Mar 11, 2009
@author: bennett based on Gene's Code
'''

import gpib_instrument
import struct
import numpy
import time
from scipy import logspace
from scipy import log10
from lookup import Lookup

class Hp3562a(gpib_instrument.Gpib_Instrument):
    '''
    HP3562A Dnamic Signal Analyzer GPIB Communication
    '''


    def __init__(self, pad, board_number = 0, name = '', sad = 0, timeout = 13, send_eoi = 1, eos_mode = 0):
        '''
        Must provide the pad (primary GPIB address) - older instrument so some standard commands do not apply
        '''
        super(Hp3562a, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)
        
        # GPIB identity string of the instrument
        self.id_string = "LSCI,MODEL370,370447,09272005"
        
        self.manufacturer = 'HP'
        self.model_number = '3562A'
        self.description  = 'Dynamic Signal Analyzer'
        
        #self.compare_identity()

        self.numpts=801  # fixed  by the instrument
        self.freq=numpy.zeros(self.numpts,dtype=numpy.float)
        self.realspectrum=numpy.zeros(self.numpts,dtype=numpy.float)
        self.complexspectrum=numpy.zeros(self.numpts,dtype=numpy.complex)

        self.function_enum=('No data','Frequency Response','Power Spectrum 1',
                  'Power Spectrum 2', 'Coherence','Cross Spectrum','Input time 1',
                  'Input time 2', 'Input linear spectrum1', 'Input linear spectrum 2',
                  'Impulse Response', 'Cross Correlation', 'Auto correlation 1', 
                  'Auto correlation 2', 'Histogram 1', 'Histogram 2')
        self.channel_enum=('Channel 1', 'Channel 2', 'Channels 1 and 2','No channel')
        self.domain_enum=('Time','Frequency','Voltage (amplitude)')
        self.peak_enum=('Peak','RMS','Volts (indicates peak only)')
        self.amplitude_enum=('Volts', 'Volts^2','V^2/Hz', 'V^2s/Hz', 'V/sqrtHz','No units',
            'Unit volts','Units volts^^2')
        self.xaxis_enum=('No Units','Hz','RPM','Orders','Seconds','Revs','Degrees','dB','dBV',
                  'Volts','V/sqrtHz','Hertz/second','Volts/EU','Vrms','V^2/Hz','Percent','Points','Records',
                  'Ohms','Hz/octave','Pulse/rev','Decades','Minutes','V^2s/Hz','Octave','Seconds/Decade',
                  'Seconds/Octace','Hz/point','Points/Sweep','Points/Decade','V/Vrms','V^2','EU','EU','EU')
        self.measmode_enum=('Linear Resolution','Log Resolution','Swept Sine','Time Capture',
                  'Linear Resolution Throughput')
        self.sweepmode_enum=('Linear Sweep','Log Sweep')
        self.demod_enum=('AM','FM','PM')
        self.average_enum=('No data','Not averaged','Averaged')
        self.window_enum=('N/A','Hanning','Flat Top','Uniform','Exponential','Force','Force1 Exp2',
                  'Exp1 Force2','User')

        self.control_mode_switch = Lookup({
            'closed' : '1',
            'zone' : '2',
            'open' : '3',
            'off' : '4'
        })

        self.on_off_switch = Lookup({
            'off' : '0',
            'on' : '1'
        })


    def Clear(self): # Does not work - find replacement

        self.clear

    def StartMeasurement(self):
        '''
        Start the measurement
        '''

        self.write('STRT')

    def GetData(self):  # for opensource gpib 
        '''
        Get Binary data dump from HP3562A
        '''

        self.write('DDAN') #data dump ansi floats
        time.sleep(1)
        test=self.rawread(2) # should get "#A"
        data = struct.unpack('!h',self.rawread(2))
        dumplength = data[0]
        dumped_data = self.rawread(dumplength)
        time.sleep(1)
        self.write('LCL') # go back to local
        headerlength = 66*8 # 
        if dumplength < headerlength:
            print "something is wrong with data size\n"
            sys.exit()

        headerdata=dumped_data[0:headerlength]
        data=dumped_data[headerlength:]
      
        header_doubles =  struct.unpack('!66d',headerdata)
        header={}
        header['display_function']=self.function_enum[int(header_doubles[0])]
        header['number_elements']=int(header_doubles[1])
        if header['number_elements'] !=self.numpts:
            print "something is wrong with data size\n"
            sys.exit()
        header['displayed_elements']=int(header_doubles[2])
        header['number_averages']=int(header_doubles[3])
        header['channels']=self.channel_enum[int(header_doubles[4])]
        header['overflow_status']=self.channel_enum[int(header_doubles[5])]
        header['overlap_pct']=int(header_doubles[6])
        header['domain']=self.domain_enum[int(header_doubles[7])]
        header['volts_pk_rms']=self.peak_enum[int(header_doubles[8])]
        header['amplitude_units']=self.amplitude_enum[int(header_doubles[9])]
        header['xaxis_units']=self.xaxis_enum[int(header_doubles[10])]
        header['float_integer']=int(header_doubles[35])
        header['complex_real']=int(header_doubles[36])
        header['log_linear']=int(header_doubles[40])
        header['meas_mode']=self.measmode_enum[int(header_doubles[43])]
        header['delta_x']=header_doubles[55]
        header['start_frequency']=header_doubles[64]
        header['start_data']=header_doubles[65] 
        self.header=header
        self.complexdata=header['complex_real']

        if self.complexdata == 0: #real data only - noise spectrum
            if len(data) != self.numpts*8:
                print "something is wrong with data size\n"
                sys.exit()       
            datavals=struct.unpack('!%dd'%(self.numpts),data)
            for i in range(self.numpts):
                self.freq[i]=i*header['delta_x']+header['start_frequency']
                self.realspectrum[i]=datavals[i]
            f = numpy.copy(self.freq)
            p = numpy.copy(self.realspectrum)
            return(f,p)

        else: # complex data - complex impedence data
            if len(data) != self.numpts*8*2:
                print "something is wrong with data size\n"
                sys.exit()      
            datavals=struct.unpack('!%dd'%(2*header['number_elements']),data)
            self.GetInstrumentState()
            for i in range(header['number_elements']):
                self.freq[i]=i*header['delta_x']+header['start_frequency']
                # negative sign fixes our data to look like nasas
                # no negative is what JNU assures me is sensible
                self.complexspectrum[i]=datavals[2*i]+datavals[2*i+1]*(0+1j)
            if self.istate['sweep_mode'] == 'Log Sweep':
                start = self.istate['sweep_start']
                stop = self.istate['sweep_end']
                self.freq=logspace(log10(start),log10(stop),self.numpts)
            f = numpy.copy(self.freq)
            p = numpy.copy(self.complexspectrum)
            return (f,p)

    def GetInstrumentState(self):  # for opensource gpib 
        '''
        Get Instrument State - Some information saved to istate
        '''

        self.write('DSAN') #instrument state dump ansi floats
        time.sleep(1)
        test=self.rawread(2) # should get "#A"
        data = struct.unpack('!h',self.rawread(2))
        dumplength = data[0]
        dumped_data = self.rawread(dumplength)
        time.sleep(1)
        self.write('LCL') # go back to local
        statelength = 96*8 # 
        if dumplength != statelength:
          print "something is wrong with data size\n"
          sys.exit()
      
        header_doubles =  struct.unpack('!96d',dumped_data)
        header={}
        header['sweep_mode']=self.sweepmode_enum[int(header_doubles[24])-39]
        header['source_level']=float(header_doubles[72])
        header['frequency_span']=float(header_doubles[79])
        header['start_freq']=float(header_doubles[91])
        header['sweep_start']=float(header_doubles[93])
        header['sweep_end']=float(header_doubles[94])
        self.istate=header


    def GetComment(self):
        '''
        Uses info from GetData to create header for output file - must call GetData first
        '''

        header=self.header
        a="# %s\n"% (time.asctime(time.localtime(time.time()))) 
        a=a+'# hp3562a data dump.  function = %s\n'%(header['display_function'])
        a=a+'# number = %d   averages= %d    channels = %s    overflow = %s\n'%(header['number_elements'],header['number_averages'],
        header['channels'],header['overflow_status'])
        a=a+'# volts pk/rms = %s   amplitude units = %s   xaxis units = %s   log-linear = %s\n'%(header['volts_pk_rms'], header['amplitude_units'], 
        header['xaxis_units'],header['log_linear'])
        a=a+'# delta x = %g   start freq = %g   start data = %g\n' % (header['delta_x'],header['start_frequency'],header['start_data'])
        return a

    def CheckMeasure(self):
        '''
        Return true if measurement is done (light is off)
        '''

        self.write('SMSD')
        result = self.rawread()
        if result[0] == '1':return True
        return False

   
    def writesleep(self,command,sleeptime=2):
        '''
        Add a sleep to the write to give time for the ancient instrument
        '''

        time.sleep(sleeptime)
        self.write(command)

    def SetNoise(self):
        '''
        Setup HP3562A to get noise spectra
        '''

#        stolen gratuitously from nathan

        self.writesleep('AUTO 0')                # autocal off 
        self.writesleep('A')                        # Selecting A
        self.writesleep('SNGL')                # Single window
        self.writesleep('CORD MGLG')                # Log magnitude
        self.writesleep('LOGX')                # Log X scale.
        self.writesleep('LNRS')                # Linear resolution
        self.writesleep('PSPC')                # Power spectrum
        self.writesleep('CH2')                # Ch2 Input
        self.writesleep('SROF')                # Source off
        self.writesleep('MDSP;FRQR')                # Measurement display, frequency
        self.writesleep('HZS')                # Units Hzs
        self.writesleep('PSUN;VHZ')                # Power spectrum units, V/rt(Hz)
        self.writesleep('PSP1')                # Measurements display, power spec1
        self.writesleep('AU1')                # Ch1 Auto range, Up & down
        self.writesleep('AU2')                # Ch2 Auto range, Up & down
        self.writesleep('AVOF')                # Averaging off
        self.writesleep('OVRJ1')                # Overload rejection ON
        self.writesleep('FSAV1')                # Fast averaging ON   
        self.writesleep('STBL')                # Stable mean
        self.writesleep('PROF')                # Preview off
        self.writesleep('ZST')                # Zero frequency start        
        self.writesleep('GND2')                # Ch1 ground   
        self.writesleep('C2AC1')                # Ch1 AC coupling  
        self.writesleep('GND1')                # Ch2 ground   
        self.writesleep('C1AC1')                # Ch2 AC coupling   
        self.writesleep('UNIF')                     # Uniform (no) window

    def SetNoiseVar(self,freqres='2 KHZ',navg=5):
        '''
        Set # of avrages and frequency span for HP3562A to get noise spectra
        '''

        self.writesleep('XASC')                # X-auto scale
        self.writesleep('YASC')                # Y-auto scale
        self.writesleep('NAVG %d'%navg)        # Number of averages
        self.writesleep('FRS %s'%freqres)        # Frequency Resolution 2 KHz
        self.writesleep('STRT')                # Start


    def SetComplexZ(self,freqres='2 KHZ',navg=5,):
        '''
        Setup HP3562A to get complex Z data
        '''

        self.writesleep('AUTO 0')         # Auto calibration off.
        self.writesleep('SSIN')           # Swept sine mode.
        self.writesleep('LGSW')           # Log swept sine mode.
        self.writesleep('FRSP')           # Frequency response measurment
#        self.writesleep('CH12')           # Ch1 and Ch2 active
#        self.writesleep('UNIF')           # Uniform window
        self.writesleep('C1AC1')          # Ch1 AC coupling 1=ac 2=dc
        self.writesleep('C2AC1')          # Ch2 AC coupling 1=ac 2=dc
#        self.writesleep('PROF')          # Demodulation Preview Off (not relevent in swept sine)      
#        self.writesleep('ZST')              # Set Zero start frequency (not relevent in swept sine)  
        self.writesleep('GND1')           # Ground CH1 (Sets shield to 200 ohm to groound)
        self.writesleep('GND2')              # Ground CH2 (Sets shield to 200 ohm to groound)
        self.writesleep('UPLO')           # Sets display to turn on two display (upper and lower)
#        self.writesleep('OVRJ1')         # Overload rejection ON (not relevent in swept sine)
#        self.writesleep('FSAV1')         # Fast averaging ON (not relevent in swept sine)
#        self.writesleep('STBL')          # Stable Mean (not relevent in swept sine)
#        self.writesleep('RND')           # Random Noise (not relevent in swept sine)
        self.writesleep('SRLV20mV')       # Source level, 20mV
        self.writesleep('DCOF0mV')        # dc offset, 0
        self.writesleep('SF1HZ')          # start freq, 1 HZ
#        self.writesleep('SWDN100KHZ')    # sweep down  ? 100KHZ (bad syntax) should have been SPF stop frequency
        self.writesleep('SWRT20S/Dc')     # sweep rate, 20 seconds per Decade        
        self.writesleep('SRON')           # source ON
        self.writesleep('AU1')            # Allow Ch1 to autorange up and down
        self.writesleep('AU2')            # Allow Ch2 to autorange up and down

## Setting A channel
        self.writesleep('A')                   
        self.writesleep('MDSP FRQR')      # Measurment Display Frequency Response
        self.writesleep('REAL')           # Display the real portion of measured value
        self.writesleep('HZS')            # Selescts Hz for time domain display
        self.writesleep('LOGX')           # Sets xazis to log scale 
        self.writesleep('XASC')           # Auto scale display x axis
        self.writesleep('YASC')           # Auto scale display y axis

## Setting B Channel
        self.writesleep('B')            
        self.writesleep('MDSP FRQR')      # Measurment Display Frequency Response
        self.writesleep('IMAG')           # Display the imaginary portion of measured value
        self.writesleep('HZS')            # Selescts Hz for time domain display
        self.writesleep('LOGX')           # Sets xazis to log scale 
        self.writesleep('XASC')           # Auto scale display x axis
        self.writesleep('YASC')           # Auto scale display y axis

    def SetComplexZVar(self,freqres='100 KHZ',navg=5,signal_level=20):
        '''
        Setup frequency span, signal level and # of avgs of HP3562A to get complex Z data
        '''

        self.writesleep('FRS %s'%freqres)      # Frequency Span
        self.writesleep('SRLV %s'%signal_level)    # Source level
        self.writesleep('NAVG %d'%navg)  # Number of averages
        self.writesleep('STRT')      # Start mesurement
    
    def Autocal(self):
        # seems messed up - return is odd 
        self.write('AUTO 0')        # autocal off
        time.sleep(2)
        self.write('RST')        # reset
        time.sleep(10)
        self.write('SNGC')        # run single autocalibration
        time.sleep(80)
 
    def AutoCalOff(self):
        '''
        Turn auto calibration off
        '''

        self.write('AUTO 0')



