import time
from datetime import datetime
import numpy as np
from waferscreen.inst_control import Keysight_USB_VNA
from waferscreen.inst_control.aly8722ES import aly8722ES
from waferscreen.plot.s21_plots import plot_s21
from waferscreen.tools.timer import timer 
from ref import usbvna_address, agilent8722es_address


class AbstractVNA:
    """
    Control multiple VNAs though a single common interface.
    """
    def __init__(self, vna_address=agilent8722es_address, verbose=True):
        # Configuration and Optional Settings
        self.vna_address = vna_address
        self.verbose = verbose
        # VNA Specific Settings
        self.vna = None
        self.max_frequency_points = None
        # Initialized Data Storage
        self.s21real = self.s21imag = self.meta_data_for_export = None

        ''' Automated Settings '''
        # Sets for quick access and comparison for various automated processes
        self.programmable_settings = {"fcenter_GHz", "fspan_GHz", "num_freq_points", "sweeptype", "if_bw_Hz", "port_power_dBm", "vna_avg"}
        self.meta_data_types = self.programmable_settings | {"vna_address", "start_time", "end_time", "utc",
                                                             "fmin_GHz", "fmax_GHz"}
        self.auto_init_settings = {"fcenter_GHz", "fspan_GHz", "set_vna_avg", "if_bw_Hz", "port_power_dBm"}
        # meta data types (these attributes are here for notation, and have same names as the automated setting above.)
        self.fcenter_GHz = None
        self.fspan_GHz = None
        self.num_freq_points_per_sweep = None  # number of frequency points measured
        self.num_freq_points = None  # number of frequency points measured
        self.use_exact_num_of_points = None
        self.sweeptype = None  # lin or log in freq space
        self.if_bw_Hz = None
        self.port_power_dBm = None
        self.vna_avg = None  # number of averages. if one, set to off
        self.start_time = self.end_time = self.utc = None
        # Calculated Data
        self.fmin_GHz = None
        self.fmax_GHz = None
        self.freqs_GHz = None

    def update_settings(self, **kwargs):
        for key in kwargs.keys():
            if key in self.meta_data_types:
                self.__setattr__(key, kwargs[key])
                # some settings need to be send to the VNA here
                if key in self.programmable_settings:
                    self.__getattribute__("set_" + key)(kwargs[key])

            else:
                raise KeyError(F"{self.__name__} has no attribute named {key}\n" +
                               F"in the allowed types {self.meta_data_types}")

    def export_metadata(self):
        self.meta_data_for_export = {key: self.__getattribute__(key) for key in self.meta_data_types
                                     if self.__getattribute__(key) is not None}
        return self.meta_data_for_export

    def freq_calculations(self, freq_only=False):
        if not freq_only:
            # Figure out frequency points for recording
            freq_radius_GHz = self.fspan_GHz / 2.0
            self.fmin_GHz = self.fcenter_GHz - freq_radius_GHz
            self.fmax_GHz = self.fcenter_GHz + freq_radius_GHz
        if self.sweeptype == "log":
            logfmin = np.log10(self.fmin)
            logfmax = np.log10(self.fmax)
            logfreqs = np.linspace(logfmin, logfmax, self.num_freq_points)
            self.freqs_GHz = 10.0 ** logfreqs
        else:
            self.freqs_GHz = np.linspace(self.fmin_GHz, self.fmax_GHz, self.num_freq_points)

    def vna_init(self, is_on=False):
        if self.vna_address == usbvna_address:
            self.max_frequency_points = 100001
            # Set up Network Analyzer
            self.vna = Keysight_USB_VNA.USBVNA(address=self.vna_address)
            self.vna.setup_thru()
            self.vna.set_cal(calstate='OFF')  # get raw S21 data
        elif self.vna_address == agilent8722es_address:
            self.max_frequency_points = 1601
            self.vna = aly8722ES(address=self.vna_address)
            self.vna.set_measure_type(measure_type='S21')
        else:
            raise KeyError(F"VNA address: {self.vna_address} if not a recognized")
        if is_on:
            self.power_on()
        else:
            self.power_off()

    @timer
    def set_port_power_dBm(self, port_power_dBm):
        if self.vna_address == usbvna_address:
            self.vna.port_power_dBm(port_power_dBm=port_power_dBm, port=1)
        elif self.vna_address == agilent8722es_address:
            self.vna.setPower(P=(port_power_dBm))

    @timer
    def power_on(self):
        self.vna.set_power_on()

    @timer
    def power_off(self):
        self.vna.set_power_off()

    @timer
    def set_if_bw_Hz(self, if_bw_Hz):
        self.vna.set_if_bw_Hz(if_bw_Hz)

    @timer
    def set_sweeptype(self, sweeptype):
        self.vna.set_sweeptype(sweeptype)

    @timer
    def set_num_freq_points(self, num_freq_points):
        if self.max_frequency_points < num_freq_points:
            # need more points than the VNA can handle
            q, r = divmod(num_freq_points, self.max_frequency_points)
            if r != 0:
                q +=1
            self.num_freq_points = q * self.max_frequency_points
            self.num_freq_points_per_sweep = self.max_frequency_points

        else:
            # less than or exactly the number of point handled be the VNA
            self.num_freq_points_per_sweep = num_freq_points
        self.vna.set_num_freq_points(self.num_freq_points_per_sweep)

    @timer
    def set_vna_avg(self, vna_avg):
        if self.vna_address == usbvna_address:
            self.vna.set_avg(count=vna_avg)
        else:
            if vna_avg is None or vna_avg < 2:
                self.vna.turn_ave_off()
            else:
                self.vna.turn_ave_on()
                self.vna.set_ave_factor(vna_avg)

    @timer
    def set_fcenter_GHz(self, fcenter_GHz):
        if self.vna_address == usbvna_address:
            self.vna.set_center_freq_GHz(center_freq_GHz=fcenter_GHz)
        elif self.vna_address == agilent8722es_address:
            center_freq_Hz = int(np.round(fcenter_GHz * 1.0e9))
            self.vna.set_center_freq(center_freq_Hz=center_freq_Hz)

    @timer
    def set_fspan_GHz(self, fspan_GHz):
        if self.vna_address == usbvna_address:
            self.vna.set_span_GHz(span_GHz=fspan_GHz)
        elif self.vna_address == agilent8722es_address:
            self.vna.setSpan(N=self.fspan_GHz * 1.0e9)

    def set_sweep_range_center_span(self, fcenter_GHz=None, fspan_GHz=None):
        if fcenter_GHz is not None:
            self.fcenter_GHz = fcenter_GHz
            self.set_fcenter_GHz(fcenter_GHz=self.fcenter_GHz)
        if fspan_GHz is not None:
            self.fspan_GHz = fspan_GHz
            self.set_fspan_GHz(fspan_GHz=self.fspan_GHz)

    def set_sweep_range_min_max(self, fmin_GHz=None, fmax_GHz=None):
        if fmin_GHz is not None:
            self.fmin = fmin_GHz
        if fmax_GHz is not None:
            self.fmax = fmax_GHz
        self.fcenter_GHz = (fmin_GHz + fmax_GHz) * 0.5
        self.fspan_GHz = fmax_GHz - fmin_GHz
        self.set_fcenter_GHz(fcenter_GHz=self.fcenter_GHz)
        self.set_fspan_GHz(fspan_GHz=self.fspan_GHz)

    def get_sweep(self):
        if self.vna_address == usbvna_address:
            self.vna.reset_sweep()
            self.vna.trig_sweep()
            # collect data according to data_format LM or RI
            s21real, s21imag = self.vna.get_S21(format='RI')
            freqs = self.freqs_GHz
        elif self.vna_address == agilent8722es_address:
            freqs, s21real, s21imag = self.vna.get_sweep()
        else:
            raise KeyError(F"VNA address {self.vna_address} not recognized.")
        if self.verbose:
            print(F"{'%2.3f' % freqs[0]} GHz to {'%2.3f' % freqs[-1]} GHz Trace Acquired")
        return freqs, s21real, s21imag

    def sweep_stitcher(self, loops_required, points_acquired_after_n_loops):
        points_needed_last_loop = self.max_frequency_points - (points_acquired_after_n_loops - self.num_freq_points)
        # initialized the data variables
        self.s21real = np.zeros(self.num_freq_points)
        self.s21imag = np.zeros(self.num_freq_points)
        # do the loops to get the VNA data
        points_last_loop = None
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
                self.set_num_freq_points(points_this_loop)
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
                      F"{fmin_str} GHz to {fmax_str} GHz")
            freqs_this_loop, s21real_this_loop, s21imag_this_loop = self.get_sweep()
            # Store the data in the variables for this class
            self.s21real[start_index: end_index] = s21real_this_loop
            self.s21imag[start_index: end_index] = s21imag_this_loop

            # things to reset for the next loop
            points_last_loop = points_this_loop
            start_index = int(end_index)
            end_index += self.max_frequency_points


    @timer
    def vna_sweep(self):
        """
        Older VNAs can only send a limited amount of datapoints per sweep.
        This method addresses this issue by appending many smaller sweeps to
        make the requested sweep.
        
        VNAs that are newer and have no limits or large limits will complete 
        this method in a single 'for' loop
        
        :return: frequencies, S21_Real, S21_Imaginary
        """
        # count how many loops we need to get all the data for this sweep.
        self.start_time = time.time()
        self.freq_calculations()
        loops_required = 0
        points_acquired_after_n_loops = 0
        while points_acquired_after_n_loops < self.num_freq_points:
            loops_required += 1
            points_acquired_after_n_loops += self.max_frequency_points
        if loops_required == 1:
            fmin = self.freqs_GHz[0]
            fmax = self.freqs_GHz[-1]
            if self.verbose:
                fmax_str = '%1.4f' % fmax
                fmin_str = '%1.4f' % fmin
                if fmax_str == fmin_str:
                    fmax_str = '%1.6f' % fmax
                    fmin_str = '%1.6f' % fmin
                print(F"Single sweep ({self.num_freq_points} points)  " +
                      F"{fmin_str} GHz to {fmax_str} GHz")
            self.freqs_GHz, self.s21real, self.s21imag = self.get_sweep()
        else:
            self.sweep_stitcher(loops_required, points_acquired_after_n_loops)
        self.end_time = time.time()
        self.utc = str(datetime.utcnow())
        return self.freqs_GHz, self.s21real, self.s21imag, self.export_metadata()

    def close_connection(self):
        self.vna.close()

    def plot(self):
        plot_s21(file=None, freqs_GHz=self.freqs_GHz, s21_complex=self.s21real + 1j * self.s21imag,
                 show_ri=True,
                 meta_data=self.export_metadata(), save=False, show=True, show_bands=True)


if __name__ == "__main__":
    """
    This is a testing space. The code below only runs when this file is run directly,
    but not when this file is used in the import statements of other files that are being run.
    """
    avna = AbstractVNA(vna_address=agilent8722es_address, verbose=True)
    avna.vna_init(is_on=False)
    avna.update_settings(num_freq_points=3400, sweeptype='lin', if_bw_Hz=100, port_power_dBm=-20)

    vna_sweeps = []
    for f_center, f_span in [(4, 2), (8, 3)]:
        avna.update_settings(fcenter_GHz=f_center, fspan_GHz=f_span)
        freqs_GHz, s21real, s21imag, metadata = avna.vna_sweep()
        vna_sweeps.append((freqs_GHz, s21real, s21imag, metadata))
