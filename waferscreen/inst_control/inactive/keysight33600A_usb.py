import time
import array
import usbtmc
import time

'''
I figured out how to talk to the usbtmc0 device from this blob on github:
https://github.com/duke-87/tekusbtmc/blob/master/tekusbtmc.py - D.Becker
Update: (December 26th, 2017) D.Bennett
(The usbtmc device does not appear to behave the same way on macs)
An alternative option that seems to work better on macs is the the python
package for usbtmc. After the import a device can be assigned like
instr =  usbtmc.Instrument("USB0::2391::19207::INSTR")
Where the argument is the unique instrument identifier.
This _usb version is modified to work with the python package. It might be
possible to merge them in the future if that make sense.

The device string doens't work for all of the models, it turns out they changed the 
numbers when they made true new keysight hardware not rebranded Agilent hardware
with a sticker. --JG
'''

class Keysight33600A_usb():
    '''Class to communicate with the Keysight336xx function generators based on python package for usbtmc.'''
    def __init__(self, device='USB0::2391::19207::INSTR'):
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

# Function used by Dan for complexZ

    def setupComplexZ(self, source):
        self.write("source%d:function sin" % source)
        self.setOffset(source, 0.0)
        self.write("outp%d on" % source)

    def setAmplitude(self, source, voltage):
        self.write("source%d:voltage %e" % (source, voltage))

    def setFrequency(self, source, freq):
        self.write("source%d:frequency %e" % (source, freq))

    def setOffset(self, source, offset):
        self.write("source%d:voltage:offset %e" % (source, offset))

    def setEdgeTimes(self, source, time):
        self.write("source%d:FUNC:PULS:TRAN:BOTH %e" % (source, time))

# New methods added by D.Bennett compatible for firmware testing

    def setAmplitude(self, voltage, ch_num):

        self.write("source%d:voltage %e" % (ch_num, voltage))

    def setOutputState(self, output_state, ch_num):

        if ch_num == 1:
            if output_state == 'ON':
                self.write('OUTPut1 ON')
            elif output_state == 'OFF':
                self.write('OUTPut1 OFF')
            else:
                print('Invlaid state, must be either OFF or ON')
        elif ch_num == 2:
            if output_state == 'ON':
                self.write('OUTPut2 ON')
            elif output_state == 'OFF':
                self.write('OUTPut2 OFF')
            else:
                print('Invlaid state, must be either OFF or ON')
        else:
            print('Invlaid channel number.')


    def setFunction(self, wavform_function, ch_num = 1):
        '''Sets the waveform for the specfied channel.
        wavform_functions {SIN|SQU|TRI|RAMP|PULS|PRBS|NOIS|ARB|DC}.
        ch_num is either 1 or 2.'''

        if ch_num == 1:
            if wavform_function == 'SIN':
                self.write('SOURce1:FUNCtion SIN')
            elif wavform_function == 'SQU':
                self.write('SOURce1:FUNCtion SQU')
            elif wavform_function == 'TRI':
                self.write('SOURce1:FUNCtion TRI')
            elif wavform_function == 'RAMP':
                self.write('SOURce1:FUNCtion RAMP')
            elif wavform_function == 'PULS':
                self.write('SOURce1:FUNCtion PULS')
            elif wavform_function == 'PRBS':
                self.write('SOURce1:FUNCtion PRBS')
            elif wavform_function == 'NOIS':
                self.write('SOURce1:FUNCtion NOIS')
            elif wavform_function == 'ARB':
                self.write('SOURce1:FUNCtion ARB')
            elif wavform_function == 'DC':
                self.write('SOURce1:FUNCtion DC')
            else:
                print('Invalid Waveform')
        elif  ch_num == 2:
            if wavform_function == 'SIN':
                self.write('SOURce2:FUNCtion SIN')
            elif wavform_function == 'SQU':
                self.write('SOURce2:FUNCtion SQU')
            elif wavform_function == 'TRI':
                self.write('SOURce2:FUNCtion TRI')
            elif wavform_function == 'RAMP':
                self.write('SOURce2:FUNCtion RAMP')
            elif wavform_function == 'PULS':
                self.write('SOURce2:FUNCtion PULS')
            elif wavform_function == 'PRBS':
                self.write('SOURce2:FUNCtion PRBS')
            elif wavform_function == 'NOIS':
                self.write('SOURce2:FUNCtion NOIS')
            elif wavform_function == 'ARB':
                self.write('SOURce2:FUNCtion ARB')
            elif wavform_function == 'DC':
                self.write('SOURce2:FUNCtion DC')
            else:
                print('Invalid Waveform')
        else:
            print('Invalid Channel Number.')

    def setByteOrder(self, swap_bytes=True):

        if swap_bytes is True:
            self.write('FORMat:BORDer SWAP')
        elif swap_bytes is False:
            self.write('FORMat:BORDer NORM')
        else:
            print('Error: swap_bytes shoulkd br true or false')

    def getByteOrder(self):

        response = self.ask('FORMat:BORDer?')

        if response == 'SWAP':
            swap_bytes = True
        elif response == 'NORM':
            swap_bytes = False
        else:
            print('Did not understand the reponse:')
            print(response)
        return swap_bytes

    def clearVolatileMem(self, ch_num = 1):

        if ch_num == 1:
            self.write('SOURce1:DATA:VOLatile:CLEar')
        elif ch_num == 2:
            self.write('SOURce2:DATA:VOLatile:CLEar')
        else:
            print('Channl number invalid')

    def setArbSampleRate(self, sample_rate, ch_num = 1):

        #The max sample rate depends on the filter settings
        # Range asppeas to be 1 uSa/s to 1 GSa/s (33600 Series), default 40 kSa/s
        #For 33600 series the sample rate is limited to 250 MSa/s with the filer off

        if (sample_rate < 1.0e9) and (sample_rate > 1.0e-6):
            rate_string = str(sample_rate)
            if ch_num == 1:
                send_string = 'SOURce1:FUNCtion:ARBitrary:SRATe ' + rate_string
                self.write(send_string)
            elif ch_num == 2:
                send_string = 'SOURce2:FUNCtion:ARBitrary:SRATe ' + rate_string
                self.write(send_string)
            else:
                print('Invalid channel numnber.')
        else:
            print('Invalid sample rate.')
            print('Sample rate must be between 1 uSa/s to 1 GSa/s .')

    def setArbFilter(self, ch_num = 1, filter_state = 'STEP'):

        if ch_num == 1:
            if filter_state == 'STEP':
                self.write('SOURce1:FUNCtion:ARBitrary:FILTer STEP')
            elif filter_state == 'NORM':
                self.write('SOURce1:FUNCtion:ARBitrary:FILTer NORM')
            elif filter_state == 'OFF':
                self.write('SOURce1:FUNCtion:ARBitrary:FILTer OFF')
            else:
                print('Invalid filter state.')
        elif ch_num == 2:
            if filter_state == 'STEP':
                self.write('SOURce2:FUNCtion:ARBitrary:FILTer STEP')
            elif filter_state == 'NORM':
                self.write('SOURce2:FUNCtion:ARBitrary:FILTer NORM')
            elif filter_state == 'OFF':
                self.write('SOURce2:FUNCtion:ARBitrary:FILTer OFF')
            else:
                print('Invalid filter state.')
        else:
            print('Invalid channal number.')


    def syncArbWavforms(self):

        self.write('FUNC:ARB:SYNC')

    def setArbFile(self, arb_name, ch_num = 1):

        if ch_num == 1:
            send_string = 'SOURce1:FUNCtion:ARBitrary ' + arb_name
            self.write(send_string)
        elif  ch_num == 2:
            send_string = 'SOURce2:FUNCtion:ARBitrary ' + arb_name
            self.write(send_string)
        else:
            print('Ivalid channel number.')


    def sendArbFloat(self, data, ch_num, arb_name='myArb', swap_bytes = True, clear_mem = True):

        #clear memmory to avoid conflicts space or name conflicts
        if clear_mem is True:
            print('Clearing volatile memory.')
            self.clearVolatileMem(ch_num)

        #check byte order
        #We expect 'SWAP' to be correctg but instrument defaults to 'NORM'.
        current_byte_order = self.getByteOrder()
        if current_byte_order != swap_bytes:
            print('Byte order swap appears to:')
            print(current_byte_order)
            print('Setting byte order swap to:')
            print(swap_bytes)
            if swap_bytes == False:
                self.setByteOrder(swap_bytes=False)
            if swap_bytes == True:
                self.setByteOrder(swap_bytes=True)
            else:
                print('byte_order is not a valid option. Setting to SWAP.')
                self.setByteOrder(swap_bytes=True)


        formated_array = array.array('f', data)
        packed_string = formated_array.tostring()
        print 'length packed string: ', len(packed_string)
        send_string1 = 'SOURce' + str(ch_num) + ':DATA:ARB '
        send_string2 =  arb_name + ', #' + str(len(str(len(packed_string)))) + str(len(packed_string))
        send_string = send_string1 + send_string2 + packed_string + '\n'
        self.instr.write_raw(send_string)

# Convience functions for autmated setup

    def setupDualChannelArb(self, datai, dataq, sample_rate, voltage):

        arb_name_1 = 'ft1i'
        arb_name_2 = 'ft1q'

        #send data to instrument channels
        self.sendArbFloat(datai, ch_num=1, arb_name=arb_name_1, swap_bytes=True, clear_mem=True)
        self.sendArbFloat(dataq, ch_num=2, arb_name=arb_name_2, swap_bytes=True, clear_mem=True)

        #setup instrument
        #set FG channels to Arb
        print('set FG channels to Arb')
        self.setFunction(wavform_function='ARB', ch_num=1)
        self.setFunction(wavform_function='ARB', ch_num=2)
        #choose arb waveform from memory
        print('choose arb waveform from memory')
        self.setArbFile(arb_name_1, ch_num=1)
        self.setArbFile(arb_name_2, ch_num=2)
        #set filter to steps
        print('set filter to steps')
        self.setArbFilter(ch_num=1, filter_state='STEP')
        self.setArbFilter(ch_num=2, filter_state='STEP')
        #set sample rates
        print('set sample rates')
        self.setArbSampleRate(sample_rate, ch_num=1)
        self.setArbSampleRate(sample_rate, ch_num=2)
        #set amplitudes
        print('set amplitudes')
        self.setAmplitude(voltage, ch_num=1)
        self.setAmplitude(voltage, ch_num=2)
        #turn outputs on
        print('set output state on')
        self.setOutputState(output_state='ON', ch_num=1)
        self.setOutputState(output_state='ON', ch_num=2)
        #syncronize arbs
        print('syncronize arbs')
        time.sleep(2)
        self.syncArbWavforms()


