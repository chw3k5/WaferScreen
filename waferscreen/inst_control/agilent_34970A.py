import serial

class Agilent34970A:
    def __init__(self):
        self.timeout = 10
        self.baudrate = 4800
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        xonxoff = True
        self.s = serial.Serial(port='/dev/ttyUSB3', timeout=self.timeout, baudrate=self.baudrate,
                               bytesize=self.bytesize, parity=self.parity, stopbits=self.stopbits, xonxoff=True)

    def reset(self):
        self.s.write('*RST\n')

    def closeSwitch(self, board, switch):
        self.s.write('ROUT:CLOS (@' + str(board) + str(switch).zfill(2) + ')\n')

    def checkClosed(self, board, switch):
        self.s.write('ROUT:CLOS? (@' + str(board) + str(switch).zfill(2) + ')\n')
        sto = self.s.readline()

        if int(sto) == 0:
            print 'Switch open'
        elif int(sto) == 1:
            print 'Switch closed'

    def measureResistance(self, board, switch, Range="AUTO", Resolution="AUTO"):
        if Resolution == "AUTO":
            self.s.write(
                'MEAS:RES? ' + str(Range) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')
        else:
            self.s.write(
                'MEAS:RES? ' + str(Range) + ',' + str(Resolution) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')

        return float(self.s.readline())

    def measureFrequency(self, board, switch, Range="AUTO", Resolution="AUTO"):
        if Resolution == "AUTO":
            self.s.write(
                'MEAS:FREQ? ' + str(Range) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')
        else:
            self.s.write(
                'MEAS:FREQ? ' + str(Range) + ',' + str(Resolution) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')

        return float(self.s.readline())

    def measurePeriod(self, board, switch, Range="AUTO", Resolution="AUTO"):
        if Resolution == "AUTO":
            self.s.write(
                'MEAS:PER? ' + str(Range) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')
        else:
            self.s.write(
                'MEAS:PER? ' + str(Range) + ',' + str(Resolution) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')

        return float(self.s.readline())

    def measureACCurrent(self, board, switch, Range="AUTO", Resolution="AUTO"):
        if Resolution == "AUTO":
            self.s.write(
                'MEAS:CURR:AC? ' + str(Range) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')
        else:
            self.s.write(
                'MEAS:CURR:AC? ' +
                str(Range) + ',' + str(Resolution) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')

        return float(self.s.readline())

    def measureDCCurrent(self, board, switch, Range="AUTO", Resolution="AUTO"):
        if Resolution == "AUTO":
            self.s.write(
                'MEAS:CURR:DC? ' + str(Range) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')
        else:
            self.s.write(
                'MEAS:CURR:DC? ' +
                str(Range) + ',' + str(Resolution) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')

        return float(self.s.readline())

    def measureACVoltage(self, board, switch, Range="AUTO", Resolution="AUTO"):
        if Resolution == "AUTO":
            self.s.write(
                'MEAS:VOLT:AC? ' + str(Range) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')
        else:
            self.s.write(
                'MEAS:VOLT:AC? ' +
                str(Range) + ',' + str(Resolution) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')

        return float(self.s.readline())

    def measureDCVoltage(self, board, switch, Range="AUTO", Resolution="AUTO"):
        if Resolution == "AUTO":
            self.s.write(
                'MEAS:VOLT:DC? ' + str(Range) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')
        else:
            self.s.write(
                'MEAS:VOLT:DC? ' +
                str(Range) + ',' + str(Resolution) + ',(@' + str(board) + str(switch).zfill(2) + ')\n')

        return float(self.s.readline())
