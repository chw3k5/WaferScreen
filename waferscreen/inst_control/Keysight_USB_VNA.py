import visa
import math
import numpy as np
import time


class USBVNA():
    """ Keysight USB VNA instrument class. """

    def __init__(self, address="GPIB::16"):
        self.ResourceManager = visa.ResourceManager()
        self.ctrl = self.ResourceManager.open_resource("%s" % address, write_termination='\n')
        self.ctrl.timeout = 1000000
        self.ctrl.vna_id = self.ctrl.query("*IDN?").rstrip()
        print("Connected to : " + self.ctrl.vna_id)

    def close(self):
        """ closes the VISA instance """
        self.ctrl.write("INIT:CONT ON")
        self.ctrl.close()
        print("VNA control closed")

    def preset(self):
        """presets PNA"""
        self.ctrl.write("SYST:FPR")
        self.ctrl.write("*CLS")
        # print(self.ctrl.query("*STB?"))
        # print(self.ctrl.query("*SRE?"))
        print("VNA Preset")

    def wait(self):
        self.ctrl.write("*WAI")

    def setup2port(self):
        """sets up 2 port measurement"""
        time.sleep(0.1)
        self.ctrl.meas_type = "FULL"
        self.ctrl.write("DISP:Window1:STATE ON")
        # self.ctrl.write("DISP:Window2:STATE ON")
        self.ctrl.write("CALC:PAR:DEL:ALL")
        self.ctrl.write("CALC:PAR:DEF:EXT 'Meas11','S11'")
        self.ctrl.write("CALC:PAR:DEF:EXT 'Meas12','S12'")
        self.ctrl.write("CALC:PAR:DEF:EXT 'Meas21','S21'")
        self.ctrl.write("CALC:PAR:DEF:EXT 'Meas22','S22'")
        self.ctrl.write("DISP:Window1:Trace1:FEED 'Meas11'")
        self.ctrl.write("DISP:Window1:Trace2:FEED 'Meas12'")
        self.ctrl.write("DISP:Window1:Trace3:FEED 'Meas21'")
        self.ctrl.write("DISP:Window1:Trace4:FEED 'Meas22'")
        # self.ctrl.write("CONT:CHAN:INT:CONT 1")
        self.ctrl.write("INIT:CONT OFF")  # turn off continuous triggering
        self.ctrl.write("TRIG:SOUR MAN")  # set trigger to manual
        self.ctrl.write("TRIG:SCOP ALL")  # trigger all channels sequentially
        self.ctrl.write("SENS:SWE:MODE CONT")  # allow channels to trigger repeatedly
        self.ctrl.write("*WAI")
        self.reset_sweep()
        self.avg_inquire()
        self.sweep_inquire()
        self.freqs_inquire()
        self.ifbw_inquire()
        self.power_inquire()
        print("2 Port Measurement Set up")

    def setup_thru(self):
        """sets up a simple S21 measurement"""
        time.sleep(0.1)
        self.ctrl.meas_type = "THRU"
        self.ctrl.write("DISP:Window1:STATE ON")
        self.ctrl.write("CALC:PAR:DEL:ALL")
        self.ctrl.write("CALC:PAR:DEF:EXT 'Meas21','S21'")
        # define display format for this measurement? ... CALC:FORM MLOG or MLIN
        self.ctrl.write("DISP:Window1:Trace1:FEED 'Meas21'")
        # self.ctrl.write("CONT:CHAN:INT:CONT 1")
        self.ctrl.write("INIT:CONT OFF")
        self.ctrl.write("TRIG:SOUR MAN")
        self.ctrl.write("*WAI")
        self.reset_sweep()
        self.avg_inquire()
        self.sweep_inquire()
        self.freqs_inquire()
        self.ifbw_inquire()
        self.power_inquire()
        print("Thru Measurement Set Up")

    def set_cal(self, calset="ArbitraryCalSet", calstate='OFF'):
        if calstate == 'ON':
            self.ctrl.write("SENS:CORR:CSET:ACT \"%s\",1" % calset)
            self.ctrl.write("*WAI")
            time.sleep(0.1)
            self.avg_inquire()
            self.sweep_inquire()
            self.freqs_inquire()
            self.ifbw_inquire()
            self.power_inquire()
            print("Using Cal Set: " + calset)
            print("PNA State post Cal Set Application: ")
            if self.ctrl.avestate == 1:
                print("Averaging ON with " + str(int(self.ctrl.avecount)) + " points")
            else:
                print("Averaging OFF")
            if self.ctrl.sweeptype == "LIN":
                print("Linear Freq. Sweep with " + str(int(self.ctrl.sweeppoints)) + " points")
            elif self.ctrl.sweeptype == "LOG":
                print("Logarithmic Freq. Sweep with " + str(int(self.ctrl.sweeppoints)) + " points")
            else:
                print("Unrecognized Sweep Type")
            print("Sweep time: " + str(self.ctrl.sweeptime) + " seconds")
            print("IF Bandwidth: " + str(self.ctrl.ifbw) + "Hz")
            print("Measurement from " + str(self.ctrl.freqstart / 1e9) + "GHz to " + str(
                float(self.ctrl.freqstop) / 1e9) + "GHz")
            print("Source 1 Power: %.2f dBm" % self.ctrl.powersource1)
            print("Source 2 Power: %.2f dBm" % self.ctrl.powersource2)
            self.reset_sweep()
        elif calstate == 'OFF':
            self.ctrl.write("SENS:CORR OFF")
            print("Taking Un-Calibrated Data")

    def set_sweep(self, numpoints, type="lin"):
        self.ctrl.write("SENS:SWE:POIN %d" % numpoints)
        if type == "lin":
            self.ctrl.write("SENS:SWE:TYPE LIN")
        if type == "log":
            self.ctrl.write("SENS:SWE:TYPE LOG")
        self.sweep_inquire()
        print("Sweep type   = " + self.ctrl.sweeptype)
        print("Sweep points = " + str(self.ctrl.sweeppoints))
        self.reset_sweep()

    def sweep_inquire(self):
        self.ctrl.write("*WAI")
        self.ctrl.sweeptype = self.ctrl.query("SENS:SWE:TYPE?").rstrip()
        self.ctrl.write("*WAI")
        self.ctrl.sweeppoints = int(self.ctrl.query("SENS:SWE:POIN?"))
        self.ctrl.write("*WAI")
        self.ctrl.sweeptime = float(self.ctrl.query("SENS:SWE:TIME?"))  # in milliseconds
        self.ctrl.write("*WAI")

    def set_freq_limits(self, start=0.01, stop=50.0):
        self.ctrl.write("SENS:FREQ:STAR %fghz " % start)
        self.ctrl.write("SENS:FREQ:STOP %fghz" % stop)
        self.freqs_inquire()
        print("Freq Start = " + str(1e-9 * self.ctrl.freqstart) + "GHz")
        print("Freq Stop  = " + str(1e-9 * self.ctrl.freqstop) + "GHz")
        self.sweep_inquire()
        self.reset_sweep()

    def set_freq_center(self, center=21.755, span=43.49):
        self.ctrl.write("SENS:FREQ:CENT %fghz " % center)
        self.ctrl.write("SENS:FREQ:SPAN %fghz " % span)
        self.freqs_inquire()
        print("Freq Center = " + str(1e-9 * self.ctrl.freqcent) + "GHz")
        print("Span        = " + str(1e-9 * self.ctrl.freqspan) + "GHz")
        self.sweep_inquire()
        self.reset_sweep()

    def freqs_inquire(self):
        self.ctrl.write("*WAI")
        self.ctrl.freqstart = float(self.ctrl.query("SENS:FREQ:STAR?"))
        self.ctrl.write("*WAI")
        self.ctrl.freqstop = float(self.ctrl.query("SENS:FREQ:STOP?"))
        self.ctrl.write("*WAI")
        self.ctrl.freqcent = float(self.ctrl.query("SENS:FREQ:CENT?"))
        self.ctrl.write("*WAI")
        self.ctrl.freqspan = float(self.ctrl.query("SENS:FREQ:SPAN?"))
        self.ctrl.write("*WAI")

    def set_avg(self, count=1, mode="sweep"):
        if count > 1:
            self.ctrl.write("SENS:AVER ON")
            self.ctrl.write("SENS:AVER:COUN %d" % count)
            self.ctrl.write("SENS:AVER:MODE %s" % mode)
        else:
            self.ctrl.write("SENS:AVER OFF")
        self.avg_inquire()
        if self.ctrl.avestate == 1:
            print("Averaging ON")
            print("Averaging COUNT = " + str(self.ctrl.avecount))
            print("Averaging  MODE = " + self.ctrl.avemode.rstrip())
        elif self.ctrl.avestate == 0:
            print("Averaging OFF")
        self.sweep_inquire()
        self.reset_sweep()

    def avg_inquire(self):
        self.ctrl.write("*WAI")
        self.ctrl.avestate = int(self.ctrl.query("SENS:AVER:STAT?"))
        self.ctrl.write("*WAI")
        if self.ctrl.avestate == 1:
            self.ctrl.avemode = self.ctrl.query("SENS:AVER:MODE?")
            self.ctrl.write("*WAI")
            self.ctrl.avecount = int(self.ctrl.query("SENS:AVER:COUN?"))

    def avg_clear(self):
        self.ctrl.write("SENS:AVER:CLE")

    def set_ifbw(self, ifbw=100, track=False):
        self.ctrl.write("SENS:BWID:RES %d " % ifbw)
        self.ctrl.write("*WAI")
        # print("IF Bandwidth set to :" + str(ifbw) + "Hz")
        if track == True:
            self.ctrl.write("SENS:BWID:TRAC ON")
        elif track == False:
            self.ctrl.write("SENS:BWID:TRAC OFF")
        self.ctrl.write("*WAI")
        self.ifbw_inquire()
        print('IF Bandwidth set to: %.1fHz' % self.ctrl.ifbw)
        if self.ctrl.ifbwtrack == 1:
            print("IF Bandwidth Tracking ON")
        elif self.ctrl.ifbwtrack == 0:
            print("IF Bandwidth Tracking OFF")
        self.sweep_inquire()
        self.reset_sweep()

    def ifbw_inquire(self):
        self.ctrl.write("*WAI")
        self.ctrl.ifbw = float(self.ctrl.query("SENS:BWID:RES?"))
        self.ctrl.write("*WAI")
        self.ctrl.ifbwtrack = int(self.ctrl.query("SENS:BWID:TRAC?"))
        self.ctrl.write("*WAI")

    def set_power(self, port=1, level=-5, state='ON'):
        if state == 'ON':
            if port == 1:
                self.ctrl.write("SOUR:POW1:LEV %f " % level)
                # self.ctrl.write("SOUR:POW1:MODE ON")
            if port == 2:
                self.ctrl.write("SOUR:POW2:LEV %f " % level)
                # self.ctrl.write("SOUR:POW2:MODE ON")
        elif state == 'OFF':
            if port == 1:
                self.ctrl.write("SOUR:POW1:MODE OFF")
            if port == 2:
                self.ctrl.write("SOUR:POW2:MODE OFF")
        else:
            print("Port " + str(port) + " power state not recognized")
        self.power_inquire()
        print("Port 1 Power set to: %.2fdBm" % self.ctrl.powersource1)
        print("Port 2 Power set to: %.2fdBm" % self.ctrl.powersource2)
        self.sweep_inquire()
        self.reset_sweep()

    def power_inquire(self):
        self.ctrl.write("*WAI")
        self.ctrl.powersource1 = float(self.ctrl.query("SOUR:POW1:LEV?"))
        self.ctrl.write("*WAI")
        self.ctrl.powersource2 = float(self.ctrl.query("SOUR:POW2:LEV?"))
        self.ctrl.write("*WAI")

    def trig_sweep(self):
        self.sweep_inquire()
        print("")
        print("Sweep time is %.2f seconds" % float(self.ctrl.sweeptime))
        if self.ctrl.avestate == 1:  # averaging ON
            self.avg_clear()
            # use stat oper cond ave to check that averaging is done
            for i in range(0, self.ctrl.avecount):
                self.ctrl.write("INIT:IMM")
                self.ctrl.write("*WAI")
                self.ctrl.query("*OPC?")
                print("Sweep %d/%d finished" % (i + 1, self.ctrl.avecount))
            self.ctrl.trig1 = True
        else:  # averaging OFF
            if self.ctrl.trig1 == False:
                print("Triggering VNA Sweep")
                self.ctrl.write("INIT:IMM")
                self.ctrl.write("*WAI")
                self.ctrl.query("*OPC?")
                self.ctrl.trig1 = True
            print("Sweep finished")

    def get_trace(self, trace=1, format="LM"):
        if trace == 1:
            self.ctrl.write("CALC:PAR:SEL \'Meas11\'")
        elif trace == 2:
            self.ctrl.write("CALC:PAR:SEL \'Meas12\'")
        elif trace == 3:
            self.ctrl.write("CALC:PAR:SEL \'Meas21\'")
        elif trace == 4:
            self.ctrl.write("CALC:PAR:SEL \'Meas22\'")
        else:
            print("Not a recognized trace")
            return 0
        # print("Triggering VNA Sweep")
        # self.trig_sweep()
        self.ctrl.write("*WAI")
        self.ctrl.write("CALC:DATA? SDATA")
        rawtrace = self.ctrl.read()
        self.ctrl.write("*WAI")
        tracesplit = rawtrace.split(",")
        if format == "LM":
            traceLM = []
            tracePH = []
            for i in range(0, len(tracesplit)):
                if i % 2 == 1:
                    traceLM.append(10 * math.log10(float(tracesplit[i - 1]) ** 2 + float(tracesplit[i]) ** 2))
                    tracePH.append(180 / math.pi * math.atan2(float(tracesplit[i]), float(tracesplit[i - 1])))
            return (traceLM, tracePH)
        elif format == "RI":
            traceR = []
            traceI = []
            for i in range(0, len(tracesplit)):
                if i % 2 == 1:
                    traceR.append(float(tracesplit[i - 1]))
                    traceI.append(float(tracesplit[i]))
            traceR = np.array(traceR)
            traceI = np.array(traceI)
            return (traceR, traceI)
        elif format == "COM":
            tracecom = []
            for i in range(0, len(tracesplit)):
                if i % 2 == 1:
                    tracecom.append(tracesplit[i - 1] + 1j * tracesplit[i])
            return tracecom
        else:
            print("Data Format not recognized")
            return 0

    def get_S21(self, format='LM'):
        self.ctrl.write("CALC:PAR:SEL \'Meas21\'")
        # print("Triggering VNA Sweep")
        # self.trig_sweep()
        self.ctrl.write("*WAI")
        self.ctrl.write("CALC:DATA? SDATA")
        rawtrace = self.ctrl.read()
        self.ctrl.write("*WAI")
        tracesplit = rawtrace.split(",")
        if format == 'LM':
            traceLM = []
            tracePH = []
            for i in range(0, len(tracesplit)):
                if i % 2 == 1:
                    traceLM.append(10.0 * math.log10(float(tracesplit[i - 1]) ** 2 + float(tracesplit[i]) ** 2))
                    tracePH.append(180.0 / math.pi * math.atan2(float(tracesplit[i]), float(tracesplit[i - 1])))
            traceLM = np.array(traceLM)
            tracePH = np.array(tracePH)
            return (traceLM, tracePH)
        elif format == 'RI':
            traceR = []
            traceI = []
            for i in range(0, len(tracesplit)):
                if i % 2 == 1:
                    traceR.append(float(tracesplit[i - 1]))
                    traceI.append(float(tracesplit[i]))
            traceR = np.array(traceR)
            traceI = np.array(traceI)
            return traceR, traceI
        else:
            print('Format not recognized!')
            return 0

    def get_S12(self, format='LM'):
        self.ctrl.write("CALC:PAR:SEL \'Meas12\'")
        # print("Triggering VNA Sweep")
        # self.trig_sweep()
        self.ctrl.write("*WAI")
        self.ctrl.write("CALC:DATA? SDATA")
        rawtrace = self.ctrl.read()
        self.ctrl.write("*WAI")
        tracesplit = rawtrace.split(",")
        if format == 'LM':
            traceLM = []
            tracePH = []
            for i in range(0, len(tracesplit)):
                if i % 2 == 1:
                    traceLM.append(10.0 * math.log10(float(tracesplit[i - 1]) ** 2 + float(tracesplit[i]) ** 2))
                    tracePH.append(180.0 / math.pi * math.atan2(float(tracesplit[i]), float(tracesplit[i - 1])))
            traceLM = np.array(traceLM)
            tracePH = np.array(tracePH)
            return (traceLM, tracePH)
        elif format == 'RI':
            traceR = []
            traceI = []
            for i in range(0, len(tracesplit)):
                if i % 2 == 1:
                    traceR.append(float(tracesplit[i - 1]))
                    traceI.append(float(tracesplit[i]))
            traceR = np.array(traceR)
            traceI = np.array(traceI)
            return (traceR, traceI)
        else:
            print('Format not recognized!')
            return 0

    def reset_sweep(self):
        self.ctrl.trig1 = False
        self.ctrl.trig2 = False