import time
import array
import usbtmc
import time
import numpy

'''
For communication to the 7000 series of agilent scopes using the python USBTMC class.
device='USB0::2391::5973::INSTR' for xxx
device='USB0::2391::5981::INSTR' for DSO7104B
'''

class AgilentMSO7104B_usb():
    '''Class to communicate with the Agilent 7000 series osciliscopes based on python package for usbtmc.'''
    def __init__(self, device='USB0::2391::5981::INSTR'):
        try: 
            self.instr =  usbtmc.Instrument(device)
        except:
            print('Instrument was likley not found?')
            #probably should find a way to list available instruments
            raise

# Helper communication functions to unify interface

    def write(self, cmd):
        self.instr.write(cmd)

    def write_raw(self, cmd):
        self.instr.write_raw(cmd)

    def readline(self):
        return self.instr.readline().strip()

    def ask(self, cmd):
        response = self.instr.ask(cmd)
        return response

# scope commands

    def getIDN(self):

        response = self.ask("*IDN?")
        return response

    def getWaveformSource(self):

        response = self.ask("WAVEform:SOURce?")
        return response

    def setWaveformSource(self, source='CHANnel1'):

        send_string = 'WAVEform:SOURce ' + source
        self.write(send_string)

    def getWaveformFormat(self):

        response = self.ask("WAVEform:FORMat?")
        return response

    def setWaveformForamt(self, format='ASCii'):

        send_string = 'WAVEform:FORMat ' + format
        self.write(send_string)

    def getWaveformFormat(self):

        response = self.ask("WAVEform:FORMat?")
        return response

    def getWavformPointsMode(self):

        response = self.ask('WAVeform:POINts:MODE?')
        return response


    def setWaveformPointsMode(self, mode='MAX'):

        if mode == 'MAX':
            self.write('WAVeform:POINts:MODE MAX')
        elif mode == 'NORM':
            self.write('WAVeform:POINts:MODE NORM')
        elif mode == 'RAW':
            self.write('WAVeform:POINts:MODE RAW')
        else:
            print('Mode is not recognized. No action taken!')


    def getWaveformNumPoints(self):

        response = self.ask("ACQuire:POINts?")
        value = int(response)
        return response

    def setWaveformNumPoints(self, num_points, max_pnts = False):
        '''Sets the number of waveform points to be transfered. The acquistion needs to be stopped
        in order to get the maximum. The number of points must be an even divsor of 1000 or be set
        to maximum.'''

        if max_pnts is True:
            send_string = 'WAVeform:POINts MAXimum'
        else:
            send_string = 'WAVeform:POINts ' + str(num_points)
        self.write(send_string)

    # When you use the block data format, the ASCII character string "#8<DD...D>"
    # is sent prior to sending the actual data. The 8 indicates how many Ds follow.
    # The Ds are ASCII numbers that indicate how many data bytes follow.

    def getWaveformData(self):

        response_str = self.ask('WAVeform:DATA?')
        header_n = int(response_str[1:2])
        data_bytes = int(response_str[2:header_n+2])
        data_str = response_str[header_n+3:]
        data_str_arr = data_str.split(',')
        data_str_np = numpy.array(data_str_arr)
        data = data_str_np.astype(numpy.float)

        return data

    def getWaveformPreamble(self):

        response_str = self.ask('WAVeform:PREAMBLE?')
        response_str_arr = response_str.split(',')
        # 0 for BYTE format, 1 for WORD format, 4 for ASCii format;
        # an integer in NR1 format (format set by :WAVeform:FORMat).
        data_mode = int(response_str_arr[0])
        # 2 for AVERage type, 0 for NORMal type, 1 for PEAK detect type;
        # an integer in NR1 format (type set by :ACQuire:TYPE).
        data_type = int(response_str_arr[1])
        data_pnts = int(response_str_arr[2]) # <points 32-bit NR1>
        # Average count or 1 if PEAK or NORMal; an integer in NR1 format (count set by :ACQuire:COUNt)
        count = int(response_str_arr[3])
        xincrement = float(response_str_arr[4]) #<xincrement 64-bit floating point NR3>
        xorigin = float(response_str_arr[5])    #<xorigin 64-bit floating point NR3>
        xref = float(response_str_arr[6])       #<xreference 32-bit NR1>
        yincrement = float(response_str_arr[7])    #<yincrement 32-bit floating point NR3>
        yorigin = float(response_str_arr[8])    #<yorigin 32-bit floating point NR3>
        yref = float(response_str_arr[9])    #<yreference 32-bit NR1>

        return data_pnts, xincrement, xorigin, xref, yincrement, yorigin, yref, data_mode, data_type

    # High level m,ethods

    def defaultSetup(self, num_pnts=1000):
        ''' Setup scope for ASCII transfer of the specifed numner of points.'''

        self.setWaveformForamt(format='ASCii')
        self.setWaveformNumPoints(num_pnts, False)
        self.setWaveformPointsMode(mode='MAX')


    def getTrace(self, channels = [1]):
        '''Grabs the channels requested in the channels list. Returns a 2d array where the first columns
        is time and the other colums are the channels in the same order as the list. Assumes scope is
        already setup for grabbing traces. Could give different number points then expected ifthe scope
        is not stopped!'''

        #should run a test the channels is valid 1, 2, 3,or 4
        # or on of the maths, etc..

        preamble = self.getWaveformPreamble()
        num_pnts = preamble[0]
        xincrement = preamble[1]

        if preamble[7] != 4:
            print('Data mode does not appear to be in ASCii mode!')

        time = numpy.linspace(0.0,num_pnts*xincrement,num_pnts)

        data = time

        for channel in channels:
            ch_string = 'CHANnel' + str(channel)
            self.setWaveformSource(ch_string)
            data_v = self.getWaveformData()
            data = numpy.vstack((data, data_v))

        return data