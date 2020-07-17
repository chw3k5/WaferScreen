'''
Created on Jan 12, 2010

@author: schimaf
'''

import gpib_instrument
from time import sleep

class AgilentE3631A(gpib_instrument.Gpib_Instrument):
    '''
    Agililent E3631A control class
    '''

    def __init__(self, pad, board_number = 0, name = '', sad = 0, timeout = 13, send_eoi = 1, eos_mode = 0):
        '''Constructor - The PAD (Primary GPIB Address) is the only required parameter '''

        super(AgilentE3631A, self).__init__(board_number, name, pad, sad, timeout, send_eoi, eos_mode)
        
        # GPIB identity string of the instrument
        self.id_string = "HEWLETT-PACKARD,E3631A,0,2.1-5.0-1.0"
        self.manufacturer = 'Agilent'
        self.model_number = 'E3631A'
        self.description  = 'DC Power Supply'

        self.allowed_outputs = ["P6V", "P25V", "N25V"]
        
        self.voltage = None
        self.powered = False

    def powerOff(self):
        '''
        shutOff() = Shut off the power
        '''
        self.write("OUTP OFF")
        self.displayText("--OFF--")
        self.powered = False

    def powerOn(self):
        '''
        turnOn() = Turn on the power
        '''
        self.reset()
        self.write("OUTP ON")
        # Allow time to stabilize
        self.powered = True
        sleep(1)

    def displayText(self, text_string):
        
        self.write('DISP:TEXT "%s"' % text_string )

    def setCurrentLimit(self, output, voltage, amps_limit):
        '''
        Set Current Limit
        '''
        voltage_string = "%8.6f" %( voltage ) # V setting
        amps_limit_string = "%8.6f" %( amps_limit )
        self.write("APPL " + output + "," + voltage_string + "," + amps_limit_string)

    def measureCurrent(self, output):
        '''
        result = measureCurrent(output)
        output = "P6V" or "P25V" or "N25V"
        P6V  =  +6V output
        P25V = +25V output
        N25V = -25V output
        Measure one of the currents from the specified output
        '''
        the_result = self.askFloat("MEAS:CURR:DC? " + output)
        return the_result

    def measureVoltage(self, output):
        '''
        result = measureVoltage(output)
        output = "P6V" or "P25V" or "N25V"
        P6V  =  +6V output
        P25V = +25V output
        N25V = -25V output
        Measure one of the voltages from the specified output
        '''
        the_result = self.askFloat("MEAS:VOLT:DC? " + output)
        return the_result
