import time
from datetime import datetime
import os
import numpy as np
from matplotlib import pyplot as plt
from waferscreen.inst_control import Keysight_USB_VNA
from waferscreen.inst_control.aly8722ES import aly8722ES
from waferscreen.plot import pySmith
from ref import file_extension_to_delimiter, usbvna_address, agilent8722es_address, pro_data_dir





def ramp_name_parse(basename):
    res_num_str, current_uA_and_power_str = basename.rstrip('dBm.csv').lstrip("sdata_res_").split('_cur_')
    current_str, power_str = current_uA_and_power_str.split("uA_")
    if "m" == current_str[0]:
        current_uA = -1.0 * float(current_str[1:])
    else:
        current_uA = float(current_str)
    power_dBm = float(power_str)
    res_num = int(res_num_str)
    return power_dBm, current_uA, res_num


def ramp_name_create(power_dBm, current_uA, res_num):
    if current_uA >= 0:
        ind_filename = F"sdata_res_{res_num}_cur_{int(round(current_uA))}uA_{power_dBm}dBm.csv"
    else:
        ind_filename = F"sdata_res_{res_num}_cur_m{int(round(-1 * current_uA))}uA_{power_dBm}dBm.csv"
    return ind_filename


class VnaMeas:
    """
    Code which will take an S21 measurement with a Keysight USB VNA (P937XA) and plot it LM and in a Smith Chart
    And then write the data to a file with (freq, s21A, s21B) where A and B are determined by the data_format
    """
    def __init__(self, fcenter_GHz=4.15, fspan_MHz=300, num_freq_points=20001, sweeptype='lin', if_bw_Hz=100,
                 ifbw_track=False, port_power_dBm=-20, vna_avg=1, preset_vna=False,
                 output_filename=None, auto_init=True, temperature_K=None, use_exact_num_of_points=False, verbose=True):
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
        self.params_file = os.path.join(pro_data_dir, "sweep_params.txt")

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
        self.use_exact_num_of_points = use_exact_num_of_points
        self.sweeptype = sweeptype  # lin or log in freq space
        self.if_bw_Hz = if_bw_Hz
        self.ifbw_track = ifbw_track  # ifbw tracking, reduces IFBW at low freq to overcome 1/f noise
        self.port_power_dBm = port_power_dBm
        self.vna_avg = vna_avg  # number of averages. if one, set to off
        self.preset_vna = preset_vna  # preset the VNA? Do if you don't know the state of the VNA ahead of time
        self.temperature_K = temperature_K
        # requested output parameters
        self.output_params = ['output_filename', 'group_delay', "fcenter_GHz", "fspan_MHz",
                              'num_freq_points', "sweeptype",
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
        self.freqs_GHz = None
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
            self.freqs_GHz = np.linspace(self.fmin, self.fmax, self.num_freq_points)
        elif self.sweeptype == 'log':
            logfmin = np.log10(self.fmin)
            logfmax = np.log10(self.fmax)
            logfreqs = np.linspace(logfmin, logfmax, self.num_freq_points)
            self.freqs_GHz = 10.0 ** logfreqs

    def vna_init(self, vna='8722es'):
        vna = vna.lower()
        if vna == 'usbvna':
            self.vna_address = usbvna_address
            self.max_frequency_points = 100001
            # Set up Network Analyzer
            self.vna = Keysight_USB_VNA.USBVNA(address=self.vna_address)
            if self.preset_vna:
                self.vna.preset()
            self.vna.setup_thru()
            self.vna.set_cal(calstate='OFF')  # get raw S21 data
        elif vna == '8722es':
            self.vna_address = agilent8722es_address
            self.max_frequency_points = 1601
            multiple_of_max_points = 0
            if not self.use_exact_num_of_points:
                # only a few values of points are allowed for this VNA,
                # change the requested number of points to be a multiple of an allowed value, the max points
                while self.num_freq_points > multiple_of_max_points:
                    multiple_of_max_points += self.max_frequency_points
                self.num_freq_points = multiple_of_max_points
            self.calulations()
            self.vna = aly8722ES(address=self.vna_address)
            self.vna.set_measure_type(measure_type='S21')
        else:
            raise KeyError("VNA: " + str(vna) + " if not a recognized")
        self.set_sweep_range_center_span()
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
            self.vna.setPower(P=(power))
            self.vna.setPowerSwitch(P='ON')
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

    def set_freq_points(self, num_freq_points=None):
        if num_freq_points is None:
            num_freq_points = self.num_freq_points
        if self.vna_address == usbvna_address:
            self.vna.set_sweep(num_freq_points, type=self.sweeptype)
        elif self.vna_address == agilent8722es_address:
            self.vna.setPoints(N=num_freq_points)
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

    def set_sweep_range_min_max(self, fmin_GHz=None, fmax_GHz=None):
        if fmin_GHz is not None:
            self.fmin = fmin_GHz
        if fmax_GHz is not None:
            self.fmax = fmax_GHz
        self.fcenter_GHz = (fmin_GHz + fmax_GHz) * 0.5
        self.fspan_MHz = (fmax_GHz - fmin_GHz) * 1000.0
        self.set_freq_center()

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
        # count how many loops we need to get all the data for this sweep.
        loops_required = 0
        points_acquired_after_n_loops = 0
        while points_acquired_after_n_loops < self.num_freq_points:
            loops_required += 1
            points_acquired_after_n_loops += self.max_frequency_points
        points_needed_last_loop = self.max_frequency_points - (points_acquired_after_n_loops - self.num_freq_points)
        # initialized the data variables
        self.s21R = np.zeros(self.num_freq_points)
        self.s21I = np.zeros(self.num_freq_points)
        self.s21LM = np.zeros(self.num_freq_points)
        self.s21PH = np.zeros(self.num_freq_points)
        # do the loops to get the VNA data
        points_last_loop = -1
        start_index = 0
        end_index = self.max_frequency_points
        for loop_index in range(loops_required):
            # determine if this is the last loop
            if loop_index + 1 == loops_required:
                # thing to do on the last loop
                points_this_loop = points_needed_last_loop
                freqs_this_loop = self.freqs_GHz[start_index:]
                end_index = self.num_freq_points
            else:
                points_this_loop = self.max_frequency_points
                freqs_this_loop = self.freqs_GHz[start_index:end_index]
            fmin = freqs_this_loop[0]
            fmax = freqs_this_loop[-1]
            # change the number of frequency points if needed
            if points_last_loop != points_this_loop:
                self.set_freq_points(num_freq_points=points_this_loop)
            # change the frequency
            self.set_sweep_range_min_max(fmin_GHz=fmin, fmax_GHz=fmax)
            # process the data into other formats and add the option phase delay
            if self.verbose:
                fmax_str = '%1.4f' % fmax
                fmin_str = '%1.4f' % fmin
                if fmax_str == fmin_str:
                    fmax_str = '%1.6f' % fmax
                    fmin_str = '%1.6f' % fmin
                print(F"Loop {'%02i' % (loop_index + 1)} of {'%02i' % loops_required}  " +
                      F"{fmin_str} GHz to {fmax_str}")
            s21Au, s21Bu = self.get_sweep()
            s21R, s21I, s21LM, s21PH = data_format_and_phase_delay(s21Au=s21Au, s21Bu=s21Bu, freqs=freqs_this_loop,
                                                                   group_delay=self.group_delay)
            # Store the data in the varables for this class
            self.s21R[start_index: end_index] = s21R
            self.s21I[start_index: end_index] = s21I
            self.s21LM[start_index: end_index] = s21LM
            self.s21PH[start_index: end_index] = s21PH
            # things to reset for the next loop
            points_last_loop = points_this_loop
            start_index = int(end_index)
            end_index += self.max_frequency_points

    def vna_tiny_sweeps(self, single_current, res_number):

        self.vna_sweep()
        ind_filename = ramp_name_create(power_dBm=self.port_power_dBm, current_uA=single_current, res_num=res_number)
        self.output_filename = os.path.join(self.dirname, ind_filename)
        self.basename = os.path.basename(self.output_filename)
        self.dirname = os.path.dirname(self.output_filename)
        # write out sdata
        with open(self.output_filename, 'w') as f:
            for i in range(len(self.freqs_GHz)):
                f.write(str(self.freqs_GHz[i]) + "," + str(self.s21R[i]) + "," + str(self.s21I[i]) + "\n")
        self.record_params()

    def vna_close(self):
        self.vna.close()

    def write_sweep(self, file_extension='csv'):
        file_extension = file_extension.lower().strip().replace(".", "")
        delimiter = file_extension_to_delimiter[file_extension]
        if self.data_format == 'LM':
            header = "freq,LM,PH"
            body = [str(freq) + delimiter + str(lm) + delimiter + str(ph)
                    for freq, lm, ph in zip(self.freqs_GHz, self.s21LM, self.s21PH)]
        elif self.data_format == 'RI':
            header = "freq,real,imag"
            body = [str(freq) + delimiter + str(real) + delimiter + str(imag)
                    for freq, real, imag in zip(self.freqs_GHz, self.s21R, self.s21I)]
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
        for i in range(0, len(self.freqs_GHz)):
            plot_freqs.append(self.freqs_GHz[i])
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
