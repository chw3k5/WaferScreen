import visa
import numpy as np
import cmath
import pickle
import pylab
import math

'''
aly8722ES
Created on Jan, 2015
@author: hubmayr
updated to python 3 and pyvisa, Jake 30 July 2020
'''


class aly8722ES():
    """ Agilent 8722ES VNA """

    def __init__(self, address="GPIB1::19::INSTR"):
        self.ResourceManager = visa.ResourceManager()
        self.ctrl = self.ResourceManager.open_resource("%s" % address, write_termination='\n')
        self.ctrl.timeout = 10000
        self.ctrl.device_id = self.ctrl.query("*IDN?")
        print("Connected to : " + self.ctrl.device_id)

        self.ctrl.allowedpts = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]  # allowed number of x-axis bins for VNA

    def close(self):
        self.ctrl.close()
        print("VNA control closed")

    # Helper functions ---------------------------------------------------------------------------------

    def convertToPhase(self, z, f, tau, zc):
        ''' convert response to phase assuming info from circle fit
            input: 
            z: raw complex input array
            f: resonance frequency (MHz)
            tau: cable delay (ns)
            zc: center of circle in IQ mixer plane

            output:
            phase
        '''
        z = z * np.e ** (2j * np.pi * f * tau * 1e-3)  # remove cable delay
        z = (zc - z) * np.e ** (-1j * cmath.phase(zc))  # center circle
        phi = np.unwrap(np.arctan2(np.imag(z), np.real(z)))  # compute phase
        return phi

    def savePickle(self, data, filename):
        ''' save python data 'd' to a picklefile with filename 'filename.pkl' '''
        filename = filename + '.pkl'
        print('writing data to file: ' + str(filename))
        f = open(filename, 'w')
        pickle.dump(data, f)
        f.close()

    def s21mag(self, a_real, a_imag):
        return 20 * np.log10(np.sqrt(a_real ** 2 + a_imag ** 2))

    def makeFrequencyArray(self, fi, numpts, span):
        ''' return the frequency array given start frequency fi, 
            the number of points (numpts), and the frequency span
        '''
        return fi + np.arange(numpts) * span / float(numpts - 1)

    def makeTimeArray(self, numpts, sweeptime):
        return np.arange(numpts) * sweeptime / float(numpts - 1)

    def findClosestNpts(self, N):
        ''' Number of points per window can only take discrete values self.allowedpts.  Find 
            closest number greater than N within self.allowedpts
        '''
        if N > 1602:
            print('Warning Npts max = 1601. returning N=1601.')
            Npts = 1601
        else:
            XX = np.array(self.allowedpts) - N
            dex = np.argmin(np.abs(XX))
            if XX[dex] < 0:
                Npts = self.allowedpts[dex + 1]
            else:
                Npts = self.allowedpts[dex]
        return Npts

    def removeCableDelay(self, f, z, tau):
        return z * np.e ** (2j * np.pi * f * tau)

    def convertArrayToComplex(self, z_r, z_i):
        return z_r + 1j * z_i

    # Get functions -----------------------------------------------------------------------------------

    def getIFbw(self):
        return float(self.ctrl.query('IFBW?'))

    def getFrequencyArray(self):
        """ returns the current frequency array (in MHz) by asking the VNA for the sweep parameters """
        return self.makeFrequencyArray(fi=self.getStartFrequency(), numpts=self.getPoints(), span=self.getSpan()) / 1.e6

    def getPower(self):
        return float(self.ctrl.query('POWE?'))

    def getSpan(self):
        """gets the frequency span in Hz"""
        F = float(self.ctrl.query('SPAN?'))
        return F

    def getMarkerVal(self):
        """returns freq (Hz) and Power (dB) of marker"""
        str = self.ctrl.query('OUTPMARK')
        str.split(',')
        [dB, f] = [float(str.split(',')[0]), float(str.split(',')[2])]
        return [dB, f]

    def getCWfreq(self):
        """gets the center frequency (in MHz) in continuous wave mode"""
        F = float(self.ctrl.query('CWFREQ?')) / 1.e6
        return F

    def getPoints(self):
        """get the number of points in the trace"""
        N = float(self.ctrl.query('POIN?'))
        return int(N)

    def getStartFrequency(self):
        return float(self.ctrl.query('STAR?'))

    def getFrequencySweepParameters(self):
        print('To be written!!')
        return False

    def getSweepTime(self):
        return float(self.ctrl.query('SWET?'))

    def getSweepTimeArray(self):
        N = self.getPoints()
        st = self.getSweepTime()
        return self.makeTimeArray(N, st)

    def getMeasurement(self, D=100000):
        self.ctrl.write('SING')
        return self.getComplexTrace(D)

    def getTrace(self):
        """ transfer the current trace to the computer using the ascii protocol
            output: N x 2 numpy array, 0th column is real, 1st column is imaginary
        """
        Npts = self.getPoints()
        self.ctrl.write('FORM4')
        self.ctrl.write('OUTPDATA')
        res = self.ctrl.read()  # (Npts*50) # form4 (ascii) takes 50 bytes per frequency bin
        res = res.split('\n')[:-1]  # this will only work if D is longer than the real data!
        N = len(res)
        if N != Npts:
            print('WARNING: number of output points does not match the current number of frequency bins!')
        result = np.zeros((N, 2))
        for n in range(N):
            XX = res[n].split(',')
            result[n, 0] = float(XX[0])
            result[n, 1] = float(XX[1])
        return result

    def get3DTrace(self, savefile=''):
        ''' get 2D trace plus time vector'''
        d = self.getTrace()
        t = self.getSweepTimeArray()
        result = np.zeros((len(t), 3))
        result[:, 0] = t
        result[:, 1] = d[:, 0]
        result[:, 2] = d[:, 1]
        if savefile:
            f = open(savefile, 'w')
            pickle.dump(result, f)
            f.close()
        return result

    def getComplexTrace(self, D=100000, savedata=False, filename='foo'):
        # 'sets xfer format to float'
        # 'D should be appropriately sized for the number of points in the trace'
        print('getComplexTrace is depricated.  Consider using getTrace.')
        self.ctrl.write('FORM4')
        self.ctrl.write('OUTPDATA')
        res = self.ctrl.read(D)
        split_array = res.split('\x00')
        raw_data_array = split_array[0].split('\n')
        print(len(raw_data_array))
        raw_data_array.pop  # clip inevitable garbage element
        # 'list with form r,i \n'
        N = len(raw_data_array)
        result = np.zeros((N - 1, 1), 'complex')
        for n in range(N - 1):
            # 'breaks into nx2 matrix with r,i'
            result[n] = float(raw_data_array[n].split(',')[0]) + 1j * float(raw_data_array[n].split(',')[1])
        if savedata:
            f = open(filename + '.pkl', 'w')
            pylab.plot(np.real(result))
            pickle.dump(result, f)
        return result

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
    def setSweepTime(self, t):
        self.ctrl.write('SWET%.1f' % t)

    def setCWfreq(self, F):
        'set the frequency for CW mode'
        self.ctrl.write('CWFREQ%.3fMHz' % (F))

    def setLinearFrequencySweep(self):
        self.ctrl.write('LINFREQ')

    def setLogFrequencySweep(self):
        self.ctrl.write("LOGFREQ")

    def setPowerSwitch(self, P):
        if P == 'on' or P == 1 or P == 'ON':
            power = 'ON'
        else:
            power = 'OFF'
        self.ctrl.write('SOUP' + power)

    def setPower(self, P):
        self.ctrl.write('POWE %.3fDB' % (P))

    def setIFbandwidth(self, ifbw):
        ''' set the intermediate frequency bandwidth (in Hz) '''
        allowedvals = {10, 30, 100, 300, 1000, 3000, 3700, 6000}
        if ifbw in allowedvals:
            self.ctrl.write('IFBW%d' % ifbw)
        else:
            raise KeyError('The IF bandwidth can only take the following discrete values:' + str(allowedvals))

    def set_center_freq(self, center_freq_Hz):
        self.ctrl.write(F"CENT {center_freq_Hz}")

    def set_ave_factor(self, ave_factor):
        if isinstance(ave_factor, int):
            self.ctrl.write(F"AVERFACT {ave_factor}")

    def turn_ave_on(self):
        self.ctrl.write(F"AVERO ON")

    def turn_ave_off(self):
        self.ctrl.write(F"AVERO OFF")

    def setupFrequencySweep(self, fi=100, ff=200, power=-45, mtype='S21', displaytype='LOGM', numpts=1601, ifbw=1000):
        """ set instrument for a frequency sweep """
        self.setIFbandwidth(ifbw)
        self.setLinearFrequencySweep()
        self.ctrl.write('CHAN1;AUTO;AUXCOFF;')
        self.ctrl.write(mtype + ';' + displaytype)
        self.ctrl.write('STAR %.3f MHZ;STOP %.3f MHz' % (fi, ff))
        self.setPower(power)
        self.setPoints(numpts)
        self.setPowerSwitch('ON')
        self.ctrl.write('AUTO')

    def setupTDtrace(self, fc, numpts=1601, ifbw=1000, power=-45, mtype='S21', sweeptime=0):
        ''' set up instrument to take a time domain trace, monitoring a single tone '''
        self.setCWfreq(fc)
        self.setPoints(numpts)
        self.setIFbandwidth(ifbw)
        self.setPower(power)
        self.ctrl.write(mtype)
        self.setSweepTime(sweeptime)
        self.ctrl.write('AUTO')

    def setPoints(self, N):
        'sets the number of points in a trace'
        if N not in self.ctrl.allowedpts:
            print('WARNING: ' + str(N) + ' points not allowed.  N must be in ' + str(self.ctrl.allowedpts))
            self.ctrl.write('POIN %.3f' % (N))
            print('Number of points set to: ' + str(self.getPoints()))
        else:
            self.ctrl.write('POIN %.3f' % (N))

    def setSpan(self, N):
        'sets the frequency span in Hz'
        self.ctrl.write('SPAN %.3f' % (N))

    def setMarkerOn(self, N):
        'turns on numbered marker'
        self.ctrl.write('MARK%.3f' % (N))

    def setMarkerMax(self):
        'sets marker to max point on trace'
        self.ctrl.write('SEAMAX')

    def setMarkerMin(self):
        'sets marker to min point on trace'
        self.ctrl.write('SEAMIN')

    def setMarkerCenter(self):
        'sets the center frequency to the marker'
        self.ctrl.write('MARKCENT')

    def get_sweep(self, show_plot=False):
        self.ctrl.write('OPC?;SING')  # take single frequency sweep
        print('taking snapshot')
        complete = self.ctrl.read().rstrip()
        print(complete)
        print('Done.')
        self.ctrl.write('AUTO')
        if complete == '1':
            pass
        else:
            raise TimeoutError('The frequency sweep did not complete before pulling the data.')
        d = self.getTrace()
        N, M = np.shape(d)
        f = self.getFrequencyArray()
        freqs = f
        real = d[:, 0]
        imag = d[:, 1]
        if show_plot:
            print('plotting the data')
            pylab.plot(freqs, real, imag, 'b-')
            pylab.xlabel('Frequency (MHz)')
            pylab.ylabel('Response (dB)')
        return freqs, real, imag

    # higher level data acquisition functions --------------------------------------------------------------
    def alySnapShot(self, fi=100, ff=200, power=-45, ifbw=1000, mtype='S21', displaytype='LOGM', numpts=1601,
                    show_plot=False, savedata=False, filename='foo', dataformat=0):
        """ measure a frequency sweep in one frame of the network analyzer (1601 pts max)

            input:
            fi = start frequency (MHz)
            ff = stop frequency (MHz)
            power = (dBm) microwave power
            mtype = 'S21' or 'S11'
            displaytype = 'LOGM', 'PHAS', etc.  What will be displayed on the instrument
            numpts = number of points in scan (max = 1601)
            dataformat: how the data is returned as described below


            output:

            DEFAULT:
            numpts x 3 array
            1st column: frequency (MHz)
            2nd column: real part of response
            3rd column: imaginary part of response

            if dataformat = 1
            return farray and separately the complex array Z_real +1jZ_imag
        """
        self.setupFrequencySweep(fi, ff, power, mtype, displaytype, numpts)
        self.setIFbandwidth(ifbw)
        self.ctrl.write('OPC?;SING')  # take single frequency sweep
        print('taking snapshot')
        complete = self.ctrl.read().rstrip()
        print(complete)
        print('Done.')
        self.ctrl.write('AUTO')
        if complete == '1':
            pass
        else:
            print('WARNING: the frequency sweep did not complete before pulling the data.')
        d = self.getTrace()
        N, M = np.shape(d)
        f = self.getFrequencyArray()
        dd = np.zeros((N, 3))
        dd[:, 0] = f
        dd[:, 1] = d[:, 0]
        dd[:, 2] = d[:, 1]
        if show_plot:
            print('plotting the data')
            pylab.plot(dd[:, 0], self.s21mag(dd[:, 1], dd[:, 2]), 'b-')
            pylab.xlabel('Frequency (MHz)')
            pylab.ylabel('Response (dB)')
        if savedata:
            self.savePickle(dd, filename)
        if dataformat == 1:
            return f, dd[:, 1] + 1j * dd[:, 2]
        else:
            return dd

    def measureSurvey(self, fi=500, ff=1000, fres=1, power=-45, mtype='S21', displaytype='LOGM', showplot=False,
                      dataformat=0, savedata=False, filename='foo'):
        ''' take a frequency survey 

            input: fi, start frequency (MHz)
                   ff, stop frequency (MHz)
                   fres, frequency resolution (MHz), note this is an upper limit (not exact) because Npoints can only take discrete values
                   power, (dBm)
                   mtype, measurement type (S21 or S11, etc)
                   displaytype, what is shown on the VNA (log mag, real, imag, phase, etc)
                   showplot, if true the results are plotted to screen
                   savedata, if true save the data as a pickle file with filename 'filename.pkl' (.pkl) added
                   dataformat: how the data is returned as described below

            output: 

            DEFAULT: 
            numpts x 3 array
            1st column: frequency (MHz)
            2nd column: real part of response
            3rd column: imaginary part of response

            if dataformat = 1
            return farray and separately the complex array Z_real +1jZ_imag

        '''
        span = ff - fi
        Npts = int(span / float(fres))
        if Npts < 1602:  # if total Npts less than 1601, just take one window
            N = self.findClosestNpts(Npts)
            DD = self.alySnapShot(fi, ff, power=power, mtype=mtype, displaytype=displaytype, numpts=N,
                                  showplot=showplot)
        else:  # if greater than one window, do multiple using N=1601
            Nwindows = int(math.ceil((
                                                 Npts / 1601.0)))  # number of alysnapshots to take, ensure round up to achieve at least higher resolution that fres
            Npts = Nwindows * 1601
            farray = np.linspace(fi, ff, Npts)
            DD = np.zeros((Npts, 3))  # initialize return array
            for ii in range(Nwindows):
                fstart = farray[ii * 1601]
                fstop = farray[(ii + 1) * 1601 - 1]
                print(str(fstart) + "," + str(fstop))
                dd = self.alySnapShot(fi=fstart, ff=fstop, power=power, mtype=mtype, displaytype=displaytype,
                                      numpts=1601, showplot=showplot)
                DD[ii * 1601:1601 * (ii + 1), :] = dd
        if savedata:
            self.savePickle(DD, filename)
        if dataformat == 1:
            return DD[:, 0], DD[:, 1] + 1j * DD[:, 2]
        else:
            return DD

    def measureTDtrace(self, fc, numpts, ifbw, sweeptime=10, power=-40, mtype='S21', doSetup=True, showplot=False,
                       dataformat=0, savedata=False, filename='foo'):
        ''' grab a time domain trace 

            input:
            fc = probe frequency
            numpts = number of points in the TD trace
            ifbw = intermediate frequency bandwidth, can only be discrete values (see setIFbandwidth above)
                   larger ifbw decreases the length of the scan for a fixed number of points

            output: numpts x 3 array
            1st column: time
            2nd column: real part of response
            3rd column: imaginary part of response

        '''

        if doSetup:
            self.setupTDtrace(fc, numpts, ifbw, power, mtype, sweeptime)

        self.ctrl.write('OPC?;SING;AUTO')
        d = self.getTrace()
        t = self.getSweepTimeArray()
        N, M = np.shape(d)
        dd = np.zeros((N, 3))
        dd[:, 0] = t
        dd[:, 1] = d[:, 0]
        dd[:, 2] = d[:, 1]
        if showplot:
            pylab.figure(1)
            pylab.plot(dd[:, 0], self.s21mag(dd[:, 1], dd[:, 2]))
            pylab.xlabel('Time (s)')
            pylab.ylabel('Response (dB)')
            pylab.figure(2)
            phi = self.convertToPhase(dd[:, 1] + 1j * dd[:, 2], f=1008.367, tau=30.5, zc=-.3894 - .2580j)
            pylab.plot(dd[:, 0], np.unwrap(phi))
            pylab.xlabel('Time (s)')
            pylab.ylabel('Phase (rad)')
        if dataformat == 1:
            return t, dd[:, 1] + 1j * dd[:, 2]
        if savedata:
            self.savePickle(dd, filename)
        else:
            return dd
