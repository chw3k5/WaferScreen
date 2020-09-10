import time
from datetime import datetime
import math
import os
import numpy as np
from matplotlib import pyplot as plt
from waferscreen.inst_control import Keysight_USB_VNA
from waferscreen.inst_control.aly8722ES import aly8722ES
from waferscreen.plot import pySmith
from ref import file_extension_to_delimiter, usbvna_address, agilent8722es_address, output_dir


class VnaMeas:
    """
    Code which will take an S21 measurement with a Keysight USB VNA (P937XA) and plot it LM and in a Smith Chart
    And then write the data to a file with (freq, s21A, s21B) where A and B are determined by the data_format
    """
    def __init__(self, fcenter_GHz=4.15, fspan_MHz=300, num_freq_points=20001, sweeptype='lin', if_bw_Hz=100,
                 ifbw_track=False, port_power_dBm=-20, vna_avg=1, preset_vna=False,
                 output_filename=None, auto_init=True, temperature_K=None, verbose=True):
        """
        Configuration and Option Settings
        """
        self.verbose = verbose
        if output_filename is None:
            self.output_filename = "C:\\Users\\uvwave\\Desktop\\Jake_VNA\\Data\\12Aug2020\\test_s21_500mK"  # leave extension off, added according to file type
        else:
            self.output_filename = output_filename
        self.basename = os.path.basename(self.output_filename)
        self.dirname = os.path.dirname(self.output_filename)
        self.params_file = os.path.join(output_dir, "sweep_params.txt")

        # group delay removal settings
        self.group_delay = 2.787  # nanoseconds

        # output format settings
        self.data_format = 'RI'  # 'LM' or 'RI' # records this data type in file
        self.plot_phase = True

        # User VNA settings
        self.vna_address = None  # set later
        self.max_frequency_points = None  # set later
        self.fcenter_GHz = fcenter_GHz
        self.fspan_MHz = fspan_MHz
        self.num_freq_points = num_freq_points  # number of frequency points measured
        self.sweeptype = sweeptype  # lin or log in freq space
        self.if_bw_Hz = if_bw_Hz
        self.ifbw_track = ifbw_track  # ifbw tracking, reduces IFBW at low freq to overcome 1/f noise
        self.port_power_dBm = port_power_dBm
        self.vna_avg = vna_avg  # number of averages. if one, set to off
        self.preset_vna = preset_vna  # preset the VNA? Do if you don't know the state of the VNA ahead of time
        self.temperature_K = temperature_K
        # requested output parameters
        self.output_params = ['basename', 'group_delay', "fcenter_GHz", "fspan_MHz", 'num_freq_points', "sweeptype",
                              'if_bw_Hz', 'ifbw_track', 'ifbw_track', 'vna_avg', "temperature_K"]

        # setting and tools for this class
        self.last_output_file = None

        """
        Initialized Data Storage
        """
        self.s21R = self.s21I = self.s21LM = self.s21PH = None
        """
        Calculations        
        """
        self.fmin = None
        self.fmax = None
        self.freqs = None
        self.calulations()
        """ 
        Auto Initialization 
        """
        if auto_init:
            self.vna_init()
        else:
            self.vna = None

    def calulations(self, freq_only=False):
        if not freq_only:
            # Figure out frequency points for recording
            freq_radius_GHz = self.fspan_MHz / 2000.0
            self.fmin = self.fcenter_GHz - freq_radius_GHz
            self.fmax = self.fcenter_GHz + freq_radius_GHz
        if self.sweeptype == "lin":
            self.freqs = np.linspace(self.fmin, self.fmax, self.num_freq_points)
        elif self.sweeptype == 'log':
            logfmin = np.log10(self.fmin)
            logfmax = np.log10(self.fmax)
            logfreqs = np.linspace(logfmin, logfmax, self.num_freq_points)
            self.freqs = 10.0 ** logfreqs

    def vna_init(self, vna='8822es'):
        vna = vna.lower()
        if vna == 'usbvna':
            self.vna_address = usbvna_address
            self.max_frequency_points = 100001
            # Set up Network Analyzer
            self.vna = Keysight_USB_VNA.USBVNA(address=self.vna_address)  # "PXI10::0-0.0::INSTR") #"PXI10::CHASSIS1::SLOT1::FUNC0::INSTR"
            if self.preset_vna:
                self.vna.preset()
            self.vna.setup_thru()
            self.vna.set_cal(calstate='OFF')  # get raw S21 data
        elif vna == '8822es':
            self.vna_address = usbvna_address
            self.max_frequency_points = 1601
            self.vna = aly8722ES(address=self.vna_address)
        else:
            raise KeyError("VNA: " + str(vna) + " if not a recognized")
        self.set_sweep_range_center_span()
        self.set_freq_points()
        self.set_avg()
        self.set_ifbw()
        self.set_power()

    def set_power(self, power=None):
        if power is None:
            power = self.port_power_dBm
        else:
            self.port_power_dBm = power
        if self.vna_address == usbvna_address:
            self.vna.set_power(port=1, level=power, state="ON")
        elif self.vna_address == agilent8722es_address:
            self.vna.setPower(P=(power - 30.0))
            self.vna.self.setPowerSwitch(P='ON')
        time.sleep(1.0)  # sleep for a second in case we've just over-powered the resonators

    def power_off(self):
        if self.vna_address == usbvna_address:
            self.vna.set_power(port=1, level=self.port_power_dBm, state="OFF")
        elif self.vna_address == agilent8722es_address:
            self.vna.self.setPowerSwitch(P='OFF')

    def set_ifbw(self):
        if self.vna_address == usbvna_address:
            self.vna.set_ifbw(self.if_bw_Hz, track=self.ifbw_track)
        elif self.vna_address == agilent8722es_address:
            self.vna.setIFbandwidth(ifbw=self.if_bw_Hz)

    def set_freq_points(self):
        if self.vna_address == usbvna_address:
            self.vna.set_sweep(self.num_freq_points, type=self.sweeptype)
        elif self.vna_address == agilent8722es_address:
            self.vna.setPoints(N=self.num_freq_points)
            if self.sweeptype == 'log':
                self.vna.setLogFrequencySweep()
            else:
                self.vna.setLinearFrequencySweep()

    def set_avg(self):
        if self.vna_address == usbvna_address:
            self.vna.set_avg(count=self.vna_avg)
        else:
            if self.vna_avg < 2:
                self.vna.turn_ave_off()
            else:
                self.vna.turn_ave_on()
                self.vna.set_ave_factor(self.vna_avg)

    def set_freq_center(self):
        if self.vna_address == usbvna_address:
            self.vna.set_freq_center(center=self.fcenter_GHz, span=self.fspan_MHz / 1000.0)
        elif self.vna_address == agilent8722es_address:
            self.vna.set_center_freq(center_freq_Hz=self.fcenter_GHz * 1.0e9)
            self.vna.setSpan(N=self.fspan_MHz * 1.0e6)

    def set_sweep_range_center_span(self, fcenter_GHz=None, fspan_MHz=None):
        if fcenter_GHz is not None:
            self.fcenter_GHz = fcenter_GHz
        if fspan_MHz is not None:
            self.fspan_MHz = fspan_MHz
        self.set_freq_center()
        self.calulations()

    def set_sweep_range_min_max(self, fmin_GHz=None, fmax_GHz=None):
        if fmin_GHz is not None:
            self.fmin = fmin_GHz
        if fmax_GHz is not None:
            self.fmax = fmax_GHz
        self.vna.set_freq_limits(start=self.fmin, stop=self.fmax)
        self.fcenter_GHz = (fmin_GHz + fmax_GHz) * 0.5
        self.fspan_MHz = (fmax_GHz - fmin_GHz) * 1000.0
        self.calulations(freq_only=True)

    def get_sweep(self):
        if self.vna_address == usbvna_address:
            self.vna.reset_sweep()
            self.vna.trig_sweep()
            # collect data according to data_format LM or RI
            s21Au, s21Bu = self.vna.get_S21(format='RI')
        elif self.vna_address == agilent8722es_address:
            freqs, s21Au, s21Bu = self.vna.get_sweep()
        if self.verbose:
            print("Trace Acquired")
        return s21Au, s21Bu

    def vna_sweep(self):
        s21Au, s21Bu = self.get_sweep()
        # put uncalibrated data in complex format
        s21data = np.array(s21Au) + 1j * np.array(s21Bu)

        # remove group delay if desired
        if self.group_delay is None:
            self.group_delay = 0.0
        phase_delays = np.exp(-1j * self.freqs * 2.0 * math.pi * self.group_delay)

        # calculate the 'calibrated' S21 data by dividing by phase delay
        cal_s21data = s21data / phase_delays
        self.s21R = np.real(cal_s21data)
        self.s21I = np.imag(cal_s21data)

        # convert data from data_format to both LM for plotting
        self.s21LM = 10 * np.log10(self.s21R ** 2 + self.s21I ** 2)
        self.s21PH = 180.0 / np.pi * np.arctan2(self.s21I, self.s21R)

    def vna_tiny_sweeps(self, single_current, res_number):
        # trigger a sweep to be done
        self.vna.reset_sweep()
        self.vna.trig_sweep()

        # collect data according to data_format LM or RI
        (s21Au, s21Bu) = self.vna.get_S21(format='RI')
        print("Trace Acquired")

        # put uncalibrated data in complex format
        s21 = []
        for i in range(0, len(self.freqs)):
            s21.append(s21Au[i] + 1j * s21Bu[i])
        s21 = np.array(s21)

        # remove group delay
        if self.group_delay is not None:
            phase_factors = np.exp(-1j * 2.0 * math.pi * self.freqs * self.group_delay)
            s21 = s21 / phase_factors

        if single_current >= 0:
            ind_filename = F"sdata_res_{res_number}_cur_" + str(int(round(single_current))) + "uA.csv"
        else:
            ind_filename = F"sdata_res_{res_number}_cur_m" + str(int(round(-1 * single_current))) + "uA.csv"

        # write out sdata
        f = open(os.path.join(self.dirname, ind_filename), 'w')
        for i in range(0, len(self.freqs)):
            f.write(str(self.freqs[i]) + "," + str(s21[i].real) + "," + str(s21[i].imag) + "\n")
        f.close()

    def vna_close(self):
        self.vna.close()

    def write_sweep(self, file_extension='csv'):
        file_extension = file_extension.lower().strip().replace(".", "")
        delimiter = file_extension_to_delimiter[file_extension]
        if self.data_format == 'LM':
            header = "freq,LM,PH"
            body = [str(freq) + delimiter + str(lm) + delimiter + str(ph)
                    for freq, lm, ph in zip(self.freqs, self.s21LM, self.s21PH)]
        elif self.data_format == 'RI':
            header = "freq,real,imag"
            body = [str(freq) + delimiter + str(real) + delimiter + str(imag)
                    for freq, real, imag in zip(self.freqs, self.s21R, self.s21I)]
        else:
            raise KeyError(F"Data format: '{self.data_format}' not recognized!")
        output_filename = self.output_filename + "." + file_extension
        with open(output_filename, 'w') as f:
            f.write(header + "\n")
            [f.write(line + "\n") for line in body]
        if self.verbose:
            print(file_extension.upper(), 'file written')
        self.last_output_file = output_filename
        self.record_params()

    def record_params(self):
        if os.path.isfile(self.params_file):
            write_mode = 'a'
        else:
            write_mode = 'w'
        params_line = ""
        for param in self.output_params:
            params_line += param + "=" + str(self.__getattribute__(param)) + ","
        params_line += 'utc=' + str(datetime.utcnow()) + "\n"
        with open(self.params_file, write_mode) as f:
            f.write(params_line)

    def plot_sweep(self):
        plot_freqs = []
        for i in range(0, len(self.freqs)):
            plot_freqs.append(self.freqs[i])
        plot_freqs = np.array(plot_freqs)

        fig1 = plt.figure(1)
        ax11 = fig1.add_subplot(121)
        ax11.set_xlabel("Freq. (GHz)")
        if self.sweeptype == 'log':
            ax11.set_xscale('log')
        ax11.set_ylabel("S21 (dB)")
        if self.plot_phase:
            ax11t = ax11.twinx()
            ax11t.set_ylabel("S21 (deg)")
        ax12 = pySmith.get_smith(fig1, 122)

        # plot Log Magnitude and possibly Phase data
        ax11.plot(plot_freqs, self.s21LM)
        if self.plot_phase:
            ax11t.plot(plot_freqs, self.s21PH, c='r')

        # plot Smith Chart data
        ax12.plot(self.s21R, self.s21I)

        # show maximized plot
        fig_manager = plt.get_current_fig_manager()
        # fig_manager.window.showMaximized()
        plt.show()
