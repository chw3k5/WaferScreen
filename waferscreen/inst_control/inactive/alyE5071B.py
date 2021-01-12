'''
alyE5071B
Created on Jun, 2015
@author: bmates1
'''

import gpib_instrument
import numpy as np
import pickle
import pylab
import math
import time

class alyE5071B(gpib_instrument.Gpib_Instrument):
    '''
    The network analyzer Agilent E5071B GPIB communication class
    '''


    def __init__(self, pad, board_number = 0, name = '', sad = 0, timeout = 13, send_eoi = 1, eos_mode = 0):
        '''Constructor  The PAD (Primary GPIB Address) is the only required parameter '''

        super(alyE5071B, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)
        
        # GPIB identity string of the instrument
        self.id_string = "HEWLETT PACKARD,E8071B"
        self.manufacturer = 'Agilent'
        self.model_number = 'E5071B'
        self.description  = 'Network Analyzer'
        self.allowedpts = [3,11,21,26,51,101,201,401,801,1601] # allowed number of x-axis bins for VNA
        self.voltage = None
        self.twait = 1.0
    
    # Helper functions ---------------------------------------------------------------------------------
    
    def savePickle(self,data,filename):
        ''' save python data 'd' to a picklefile with filename 'filename.pkl' '''
        filename=filename+'.pkl'
        print 'writing data to file: ',filename
        f=open(filename,'w')
        pickle.dump(data,f)
        f.close()
    
    def s21mag(self,a_real,a_imag):
        return 20*np.log10(np.sqrt(a_real**2+a_imag**2))
    
    def makeFrequencyArray(self,fi,numpts,span):
        ''' return the frequency array given start frequency fi, 
            the number of points (numpts), and the frequency span
        '''
        return fi+np.arange(numpts)*span/float(numpts-1)
    
    def makeTimeArray(self,numpts,sweeptime):
        return np.arange(numpts)*sweeptime/float(numpts-1)
    
    def findClosestNpts(self,N):
        ''' Number of points per window can only take discrete values self.allowedpts.  Find 
            closest number greater than N within self.allowedpts
        '''
        if N>1601:
            print 'Warning Npts max = 1601. returning N=1601.'
            Npts = 1601
        else:
            XX = np.array(self.allowedpts) - N
            dex = np.argmin(np.abs(XX))
            if XX[dex] < 0:
                Npts = self.allowedpts[dex+1]
            else:
                Npts = self.allowedpts[dex]
        return Npts
    
    # Get functions -----------------------------------------------------------------------------------
    
    def getFrequencyArray(self):
        ''' returns the current frequency array (in MHz) by asking the VNA for the sweep parameters '''
        return self.makeFrequencyArray(fi=self.getStartFrequency(),numpts=self.getPoints(),span=self.getSpan())/1.e6
        
    def getPower(self):
	ret_str = self.ask(':SOUR1:POW?')
	print ret_str
        return float(ret_str)
    
    def getSpan(self):
        'gets the frequency span in Hz'
        F=self.askFloat(':SENS1:FREQ:SPAN?')
        return F
    
    def getMarkerVal(self):
        'returns freq (Hz) and Power (dB) of marker'
        f = self.askFloat(':CALC1:MARK1:X?')
        dB = self.askFloat(':CALC1:MARK1:Y?')
        return [dB,f]
    
    def getCWfreq(self):
        'gets the center frequency (in MHz) in continuous wave mode'
        F=self.askFloat(':SENS1:FREQ?')/1.e6
        return F
    
    def getPoints(self):
        'get the number of points in the trace'
        N=self.askFloat(':SENS1:SWE:POIN?')
        return int(N)

    def getNumPoints(self):
        'get the number of points in the trace'
        N=self.askFloat(':SENS1:SWE:POIN?')
        return int(N)
    
    def getAverages(self):
        'get the number of traces being averaged'
        N=self.askFloat(':SENS1:AVER:COUN?')
        return int(N)
    
    def getStartFrequency(self):
        return float(self.ask(':SENS1:FREQ:STAR?'))

    def getCenterFrequency(self):
        return float(self.ask(':SENS1:FREQ:CENT?'))
    
    def getFrequencySweepParameters(self):
        print 'To be written!!'
        return False
    
    def getSweepTime(self):
        return float(self.ask(':SENS1:SWE:TIME?'))
    
    def getSweepTimeArray(self):
        N = self.getPoints()
        st = self.getSweepTime()
        return self.makeTimeArray(N,st)
 
#    def getMeasurement(self,D=100000):
#        self.write('SING')
#        return self.getComplexTrace(D)
    
    def getTrace(self):
        ''' transfer the current trace to the computer using the ascii protocol
            output: N x 2 numpy array, 0th column is real, 1st column is imaginary
        '''
        Npts = self.getPoints()
        twait = self.getAverages() * self.getSweepTime() * 1.01

        self.write(':ABOR')                         # Abort running measurements

        # Configure single-shot averaging operation
        self.write(':INIT1:CONT OFF')               # Suspend continuous operation
        self.write(':SENS1:AVER ON')                # Enable averaging (even if averfact = 1)
        self.write(':TRIG:AVER ON')                 # Lets the trigger start the average
        self.write(':INIT1:CONT ON')                # Restores continuous operation
        self.write(':TRIG:SOUR BUS')                # Waits for software trigger
        self.write(':TRIG:SING')                    # Sends software trigger

        # Take the data
        time.sleep(twait)                           # Pause for approximate duration of meaurement
        self.ask('*OPC?')                           # Wait until measurement is complete

        # Capture the data
        self.write(':FORM:DATA ASC')                # Set data to ASCII mode
        self.write(':CALC1:DATA:SDAT?')             # Ask for the acquired trace
        res = self.rawread(Npts*40)                 # Read trace data (40 bytes per frequency bin)

        # Process the data
        valuestrings = res.split(',')               # Split the data into frequency bins
        N = len(valuestrings)/2
        if N != Npts:                               # Check for the right number of frequency bins
            print 'WARNING: number of output points does not match the current number of frequency bins!'
        result = np.zeros((N,2))
        for n in range(N):                          # For each frequency bin
#            XX = res[n].split(',')                  # split the S-parameter into real and imaginary
            result[n,0]=float(valuestrings[2*n])
            result[n,1]=float(valuestrings[2*n + 1])

#        res = res.split('\n')[:-1]                  # Split the data into frequency bins
#        N = len(res)
#        if N != Npts:                               # Check for the right number of frequency bins
#            print 'WARNING: number of output points does not match the current number of frequency bins!'
#        result = np.zeros((N,2))
#        for n in range(N):                          # For each frequency bin
#            XX = res[n].split(',')                  # split the S-parameter into real and imaginary
#            result[n,0]=float(XX[0])
#            result[n,1]=float(XX[1])

        return result

    def getS21(self):
        data = self.getTrace()
        data_r = data[:,0]
        data_i = data[:,1]
        s21 = data_r + 1j*data_i
        return s21

#    def getComplexTrace(self,D=100000,savedata=False,filename='foo'):
#        'sets xfer format to float'
#        'D should be appropriately sized for the number of points in the trace'
#        print 'getComplexTrace is deprecated.  Consider using getTrace.'
#        self.write('FORM4')
#        self.write('OUTPDATA')
#        res = self.rawread(D)
#        split_array = res.split('\x00')
#        raw_data_array = split_array[0].split('\n')
#        print len(raw_data_array)
#        raw_data_array.pop #clip inevitable garbage element
#        'list with form r,i \n'
#        N = len(raw_data_array)
#        result = np.zeros((N-1,1),'complex')
#        for n in range(N-1): 
#            'breaks into nx2 matrix with r,i'
#            result[n]=float(raw_data_array[n].split(',')[0])+1j*float(raw_data_array[n].split(',')[1])
#        if savedata:
#            f = open(filename+'.pkl','w')
#            pylab.plot(np.real(result))
#            pickle.dump(result,f)
#        return result
    
#     def getTraceBinary(self):
#         ''' grab the data in the trace.  Should be twice as fast as getTrace.   '''
#         
#         # FORM3 is 64-bit floating point. 
#         # 8 bytes per data point.  There are two numbers per frequency bin (real and imag)
#         # thus a full 1601 bin trace has 1601 x 2 x 8 byte = 3216 bytes
#         # header is 4 bytes
#         print 'UNFINISHED!'
#         self.write('FORM3') 
#         self.write('OUTPDATA')
        
    
    # Set functions --------------------------------------------------------------------
    
    def setCWfreq(self,F):
        'set the frequency for CW mode'
        self.write(':SENS1:FREQ %.3fMHz'%(F))

    def setCenter(self,center):
        s = 'SENS:FREQ:CENT %f' % float(center)
        self.write(s)
    
    def setLinearFrequencySweep(self):
        self.write(':SENS1:SWE:TYPE LIN')
    
    def setPowerSwitch(self,P):
        if P=='on' or P==1 or P=='ON':
            power=' ON'
        else:
            power=' OFF'
        self.write('OUTP'+power)
    
    def setPower(self,P):
        self.write(':SOUR1:POW %.2f'%(P))
 
    def setIFbandwidth(self,ifbw):
        ''' set the intermediate frequency bandwidth (in Hz) '''
        allowedvals = [10,30,100,300,1000,3000,3700,6000]
        if ifbw in allowedvals:
            self.write(':SENS1:BWID %d'%ifbw)
        else:
            print 'The IF bandwidth can only take the following discrete values:',allowedvals

    def setIFBW(self,ifbw):
        self.setIFbandwidth(ifbw)
    
    def setupFrequencySweep(self,fi=100,ff=200,power=-45,mtype='S21',displaytype='MLOG',numpts=1601,averfact=1,ifbw=1000):
        ''' set instrument for a frequency sweep '''
        self.setIFbandwidth(ifbw)
        self.write(':SENS1:SWE:TIME:AUTO ON')

        self.write('SENS1:OFFS OFF')
        self.setLinearFrequencySweep()
        #self.write('CHAN1;AUTO;AUXCOFF;')

        self.write(':CALC1:PAR1:DEF '+mtype)
        self.write(':CALC1:PAR1:SEL')
        self.write(':CALC1:SEL:FORM '+displaytype)

        self.write(':SENS1:FREQ:STAR %.3fE6'%(fi))
        self.write(':SENS1:FREQ:STOP %.3fE6'%(ff))

        self.setPower(power)
        self.setPoints(numpts)
        self.setAverages(averfact)
        self.setPowerSwitch('ON')
    
#    def setupTDtrace(self,fc,numpts=1601,ifbw=1000,power=-45):
#        ''' set up instrument to take a time domain trace, monitoring a single tone '''
#        self.setCWfreq(fc)
#        self.setPoints(numpts)
#        self.setIFbandwidth(ifbw)
#        self.setPower(power)
#        self.write('AUTO')
       
    def setPoints(self,N):
        'sets the number of points in a trace'
        self.write(':SENS1:SWE:POIN %d'%(N))
        if N not in self.allowedpts:
            print 'WARNING: ', N, ' points not allowed.  N must be in ', self.allowedpts
            print 'Number of points set to: ', self.getPoints()

    def setNumPoints(self,N):
        self.setPoints(N)
    
    def setSpan(self,span):
        'sets the frequency span in Hz'
        self.write(':SENS1:FREQ:SPAN %.3f'%(span))
    
    def setAverages(self,averfact):
        'sets the number of traces to average'
        self.write(':SENS1:AVER:COUN %d'%(averfact))
        
    def setMarkerOn(self,N):
        'turns on numbered marker'
        self.write(':CALC1:MARK%d ON'%(N))
        
    def setMarkerMax(self):
        'sets marker to max point on trace'
        self.write(':CALC1:MARK1:FUNC:TYPE MAX')
        self.write(':CALC1:MARK1:FUNC:EXEC')
        
    def setMarkerMin(self):
        'sets marker to min point on trace'
        self.write(':CALC1:MARK1:FUNC:TYPE MIN')
        self.write(':CALC1:MARK1:FUNC:EXEC')
        
    def setMarkerCenter(self):
        'sets the center frequency to the marker'
        self.write(':CALC1:MARK1:SET CENT')
    
    # higher level data acquisition functions --------------------------------------------------------------
    
    def alySnapShot(self,fi=100,ff=200,power=-45,mtype='S21',displaytype='MLOG',numpts=1601,averfact=1,showplot=False,savedata=False,filename='foo'):
        ''' measure a frequency sweep in one frame of the network analyzer (1601 pts max) 
        
            input:
            fi = start frequency (MHz)
            ff = stop frequency (MHz)
            power = (dBm) microwave power
            mtype = 'S21' or 'S11'
            displaytype = 'LOGM', 'PHAS', etc.  What will be displayed on the instrument
            numpts = number of points in scan (max = 1601)
            
            output: numpts x 3 array
            1st column: frequency (MHz)
            2nd column: real part of response
            3rd column: imaginary part of response
        '''
        self.setupFrequencySweep(fi,ff, power, mtype, displaytype, numpts, averfact)
        #print 'taking snapshot'
        d = self.getTrace()
        N,M = np.shape(d)
        f = self.getFrequencyArray()
        dd = np.zeros((N,3))
        dd[:,0]=f
        dd[:,1]=d[:,0]
        dd[:,2]=d[:,1]
        if showplot:
            print 'plotting the data'
            pylab.plot(dd[:,0],self.s21mag(dd[:,1],dd[:,2]))
            pylab.xlabel('Frequency (MHz)')
            pylab.ylabel('Response (dB)')
        if savedata:
            self.savePickle(dd, filename)
        return dd
    
    
    
    def measureSurvey(self,fi=500,ff=1000,fres=1,power=-45,mtype='S21',displaytype='MLOG',averfact=10,showplot=False,savedata=False,filename='foo'):
        ''' take a frequency survey 
        
            input: fi, start frequency (MHz)
                   ff, stop frequency (MHz)
                   fres, frequency resolution (MHz), note this is an upper limit (not exact) because Npoints can only take discrete values
                   power, (dBm)
                   mtype, measurement type (S21 or S11, etc)
                   displaytype, what is shown on the VNA (log mag, real, imag, phase, etc)
                   showplot, if true the results are plotted to screen
                   savedata, if true save the data as a pickle file with filename 'filename.pkl' (.pkl) added
                   
            output: (N,3) numpy array
                    col 0: frequency
                    col 1: real
                    col 2: imag
        '''
        span = ff-fi
        Npts = int(span/float(fres))
        if Npts < 1602: # if total Npts less than 1601, just take one window
            N = self.findClosestNpts(Npts)
            dd = self.alySnapShot(fi,ff,power=power,mtype=mtype,displaytype=displaytype,numpts=N,averfact=averfact,showplot=showplot)
            if savedata:
                self.savePickle(dd, filename)
            return dd
        else: # if greater than one window, do multiple using N=1601
            Nwindows = int(math.ceil((Npts/1601.0))) # number of alysnapshots to take, ensure round up to achieve at least higher resolution that fres
            Npts = Nwindows*1601
            farray = np.linspace(fi,ff,Npts)
            DD = np.zeros((Npts,3)) # initialize return array
            for ii in range(Nwindows):
                fstart = farray[ii*1601]
                fstop = farray[(ii+1)*1601-1]
                print fstart,fstop
                dd = self.alySnapShot(fi=fstart,ff=fstop,power=power,mtype=mtype,displaytype=displaytype,numpts=1601,averfact=averfact,showplot=showplot)
                DD[ii*1601:1601*(ii+1),:] = dd
            if savedata:
                self.savePickle(DD, filename)
            return DD
                           
    
#    def measureTDtrace(self,fc,numpts,ifbw,doSetup=True,power=-40,showplot=False):
#        ''' grab a time domain trace 
#        
#            input:
#            fc = probe frequency
#            numpts = number of points in the TD trace
#            ifbw = intermediate frequency bandwidth, can only be discrete values (see setIFbandwidth above)
#                   larger ifbw decreases the length of the scan for a fixed number of points
#                   
#            output: numpts x 3 array
#            1st column: time
#            2nd column: real part of response
#            3rd column: imaginary part of response
#        
#        '''
#        
#        if doSetup:
#            self.setupTDtrace(fc, numpts, ifbw,power)
#        self.write('SING')
#        d = self.getTrace()
#        t = self.getSweepTimeArray()
#        N,M = np.shape(d)
#        dd = np.zeros((N,3))
#        dd[:,0]=t
#        dd[:,1]=d[:,0]
#        dd[:,2]=d[:,1]
#        if showplot:
#            pylab.plot(dd[:,0],self.s21mag(dd[:,1],dd[:,2]))
#            pylab.xlabel('Frequency (MHz)')
#            pylab.ylabel('Response (dB)')
#        return dd
        
            
        
        
        
