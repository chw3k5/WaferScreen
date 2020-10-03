import numpy as np
import os
import time
from matplotlib import pyplot as plt
from typing import NamedTuple, Optional
from multiprocessing import Pool
from ref import output_dir, today_str, volt_source_address, volt_source_port, agilent8722es_address
from waferscreen.inst_control import srs_sim928
from waferscreen.analyze.resonator_fitter import single_res_fit, fit_resonator
from waferscreen.analyze.find_and_fit import ResParams, res_params_header, ResFit, package_res_results
from waferscreen.measure.res_sweep import VnaMeas
from waferscreen.analyze.lamb_fit import lambdafit, Phi0
from waferscreen.read.table_read import ClassyReader, floats_table


def ramp_name_parse(basename):
    res_num, current_uA_str = basename.rstrip('uA.csv').lstrip("sdata_res_").split('_cur_')
    return current_uA_str, res_num


class TinySweeps:
    def __init__(self, wafer, band_number, run_number, port_power_dBm=-40, temperature_K=300, date_str=None,
                 fit_number=1, remove_baseline_ripple=False, vna_address=agilent8722es_address,
                 auto_run=False, verbose=True):
        self.verbose = verbose
        self.wafer = wafer
        self.band_number = band_number
        self.run_number = run_number
        self.fit_number = fit_number
        self.remove_baseline_ripple = remove_baseline_ripple
        if date_str is None:
            self.date_str = today_str
        else:
            self.date_str = date_str

        self.temperature_K = temperature_K

        band_str = F"Band{'%02i' % self.band_number}"
        self.parent_dir = os.path.join(output_dir, 's21', F"{self.wafer}", band_str, self.date_str)
        self.lambda_filename = os.path.join(self.parent_dir, 'lambda_fits.csv')
        self.plot_filename = os.path.join(self.parent_dir, F"{self.wafer}_{band_str}_{self.date_str}_flux_ramp.pdf")
        self.data_output_folder =  os.path.join(self.parent_dir, "flux_ramp")
        if not os.path.isdir(self.data_output_folder):
            os.mkdir(self.data_output_folder)
        self.res_out_dir = os.path.join(self.data_output_folder, 'res_fits')
        if not os.path.isdir(self.res_out_dir):
            os.mkdir(self.res_out_dir)
        self.file_delimiter = ","

        # resonator frequencies file
        self.freqs_filename = os.path.join(output_dir, 's21', F"{wafer}", band_str, self.date_str,
                                           F"{self.wafer}_{band_str}_{self.date_str}" +
                                           F"_run{self.run_number}_fit.csv")
        self.res_freq_units = "GHz"
        self.res_num_limits = [1, -1]  # set to -1 to ignore limits

        # instrument addresses
        self.vna_address = vna_address  # go into Keysight GUI, enable HiSlip Interface, find address in SCPI Parser I/O
        self.volt_source_address = volt_source_address
        self.volt_source_port = volt_source_port

        # frequency sweep options
        self.meas_span = 1000  # kHz
        self.num_pts_per_sweep = 401  # 1601 for Aly8722ES, 100001 for P5002A
        self.port_power = port_power_dBm  # dBm
        self.if_bw = 300  # Hz
        self.ifbw_track = False  # ifbw tracking, reduces IFBW at low freq to overcome 1/f noise
        self.vna_avg = 1  # number of averages. if one, set to off
        self.preset_vna = False  # preset the VNA? Do if you don't know the state of the VNA ahead of time
        self.keep_away_collisions = True  # option to modify frequency boundaries of s21 measurement so that we can fit better

        # flux ramp options
        self.rseries = 10000  # ohms
        self.current_min = -125  # uA
        self.current_max = 125  # uA
        self.current_steps = 51
        self.currents = np.linspace(self.current_min, self.current_max, self.current_steps)
        self.volts = np.linspace(self.current_min * self.rseries * 1e-6, self.current_max * self.rseries * 1e-6, self.current_steps) # volts

        # fitting options
        self.fit_model = 'simple_res_gain_slope_complex'
        self.error_est = 'prop'  # 'flat' or 'prop'
        self.eager_analyze_retry_time = 20  # in seconds

        # make sure volts are in integer # of mV so SRS doesn't freak out
        for i in range(0, len(self.volts)):
            millivolts = int(round(self.volts[i] * 1000))
            self.volts[i] = millivolts / 1000

        # group delay removal (best to get correct within 180 degrees over dataset)
        self.remove_group_delay = True
        self.group_delay = 27.292  # nanoseconds

        # uninitialized parameters for other methods in this class
        self.res_params = None
        self.res_freqs = None
        self.freq_bounds = None
        self.freq_bounds_array = None
        self.vna_meas = None
        self.res_num_dict = None
        self.lambda_params = None

        # load the data from the initial course S21 sweep over the band
        self.load_res_freqs()

        # take data
        if auto_run:
            self.take_sweep()

    def load_res_freqs(self):
        # open resonant frequencies file
        with open(self.freqs_filename, 'r') as f:
            lines = f.readlines()
        header = lines[0].strip().split(",")
        self.res_params = []
        for line in lines[1:]:
            datavec = line.split(",")
            self.res_params.append(ResParams(**{column_name: float(value) for column_name, value in zip(header, datavec)}))
        self.res_freqs = np.array([res_param.f0 for res_param in self.res_params])

        # figure out boundaries between resonators so we don't measure a neighbor
        self.freq_bounds = []
        approach_factor = 0.65  # fraction of distance between resonators to draw boundary, should be between 0.5 and 1
        for i, freq in list(enumerate(self.res_freqs)):
            if i == 0:
                lower_bound = freq - self.meas_span * 1e-6 / 2.0
                if (self.res_freqs[i + 1] - self.res_freqs[i]) * approach_factor < self.meas_span * 1e-6 / 2.0:
                    upper_bound = self.res_freqs[i] + (self.res_freqs[i + 1] - self.res_freqs[i]) * approach_factor
                else:
                    upper_bound = self.res_freqs[i] + self.meas_span * 1e-6 / 2.0
            elif i == len(self.res_freqs) - 1:
                upper_bound = self.res_freqs[i] + self.meas_span * 1e-6 / 2.0
                if (self.res_freqs[i] - self.res_freqs[i - 1]) * approach_factor < self.meas_span * 1e-6 / 2.0:
                    lower_bound = self.res_freqs[i] - (self.res_freqs[i] - self.res_freqs[i - 1]) * approach_factor
                else:
                    lower_bound = self.res_freqs[i] - self.meas_span * 1e-6 / 2.0
            else:
                if (self.res_freqs[i] - self.res_freqs[i - 1]) * approach_factor < self.meas_span * 1e-6 / 2.0:
                    lower_bound = self.res_freqs[i] - (self.res_freqs[i] - self.res_freqs[i - 1]) * approach_factor
                else:
                    lower_bound = self.res_freqs[i] - self.meas_span * 1e-6 / 2.0
                if (self.res_freqs[i + 1] - self.res_freqs[i]) * approach_factor < self.meas_span * 1e-6 / 2.0:
                    upper_bound = self.res_freqs[i] + (self.res_freqs[i + 1] - self.res_freqs[i]) * approach_factor
                else:
                    upper_bound = self.res_freqs[i] + self.meas_span * 1e-6 / 2.0
            self.freq_bounds.append((lower_bound, upper_bound))
        self.freq_bounds_array = np.array(self.freq_bounds)

    def take_sweep(self):
        if self.verbose:
            print("Currents to measure at:")
            print(self.currents)
            print("Voltages to measure at:")
            print(self.volts)
            print("")
            total_est_time = (self.current_steps * len(self.res_freqs) * (0.5 + self.num_pts_per_sweep / self.if_bw)) / 3600.0
            print("Total time to do FR sweep: " + str(total_est_time) + " hours")
        self.vna_meas = VnaMeas(fcenter_GHz=self.res_freqs[0], fspan_MHz=self.meas_span * 1e-6,
                                num_freq_points=self.num_pts_per_sweep, sweeptype="lin", if_bw_Hz=self.if_bw,
                                ifbw_track=self.ifbw_track, port_power_dBm=self.port_power, vna_avg=1, preset_vna=False,
                                output_filename=os.path.join(self.data_output_folder, "file_name_place_holder.fake"),
                                auto_init=True, temperature_K=self.temperature_K, use_exact_num_of_points=True,
                                verbose=self.verbose)
        # connect to SIM928
        voltsource = srs_sim928.SRS_SIM928(com_num=5, address=volt_source_address, port=volt_source_port)
        voltsource.setvolt(self.volts[0])
        voltsource.output_on()
        for j in range(len(self.res_freqs)):
            # only fit resonators we want to fit...
            mask_res = False
            if self.res_num_limits[0] != -1 and self.res_num_limits[1] != -1:
                if j >= self.res_num_limits[0] and j <= self.res_num_limits[1]:
                    mask_res = True
            elif self.res_num_limits[0] == -1 and self.res_num_limits[1] != -1:
                if j <= self.res_num_limits[1]:
                    mask_res = True
            elif self.res_num_limits[0] != -1 and self.res_num_limits[1] == -1:
                if j >= self.res_num_limits[0]:
                    mask_res = True
            elif self.res_num_limits[0] == -1 and self.res_num_limits[1] == -1:
                mask_res = True
            else:
                raise KeyError("There is an error in this code....")

            if mask_res:
                # set frequency limits
                if self.keep_away_collisions:
                    self.vna_meas.set_sweep_range_min_max(fmin_GHz=self.freq_bounds[j][0],
                                                          fmax_GHz=self.freq_bounds[j][1])
                    self.vna_meas.freqs = np.linspace(self.freq_bounds[j][0], self.freq_bounds[j][1],
                                                      self.num_pts_per_sweep)
                else:
                    self.vna_meas.set_sweep_range_center_span(fcenter_GHz=self.res_freqs[j],
                                                              fspan_MHz=self.meas_span * 1e-6)
                    self.vna_meas.freqs = np.linspace(self.res_freqs[j] - self.meas_span * 1e-6 / 2.0, self.res_freqs[j]
                                                      + self.meas_span * 1e-6 / 2.0, self.num_pts_per_sweep)

                for single_voltage, single_current in zip(self.volts, self.currents):
                    # set voltage source
                    voltsource.setvolt(single_voltage)
                    cur_volt = voltsource.getvolt()
                    if abs(cur_volt - single_voltage) > 0.001:
                        raise IOError("Voltage failed to set for SIM928")
                    if self.verbose:
                        print("Measuring resonator # " + str(j + 1) + "/" + str(len(self.res_freqs)) +
                              " at flux bias current " + str(single_current) + "uA")

                    # trigger a sweep to be done
                    self.vna_meas.vna_tiny_sweeps(single_current, res_number=j)

        # close connection to instruments
        self.vna_meas.vna_close()
        if self.verbose:
            print("Connection to Instruments Closed")

    def make_res_fit_file(self, res_num):
        return os.path.join(self.res_out_dir, F"sdata_res_{res_num}_fit_{self.fit_number}.csv")

    def analyze_sweep(self, file):
        # open the sweep file with the resonator
        with open(file=file, mode='r') as f:
            raw_sweep = f.readlines()
        split_sweep = [tuple(raw_line.rstrip().split(',')) for raw_line in raw_sweep]
        # there is a legacy file type without a header, we test for that here
        try:
            float(split_sweep[0][0])
        except ValueError:
            header = split_sweep[0]
            split_sweep.pop(0)
        else:
            header = ['freq', 'real', "imag"]
        by_column_data = list(zip(*split_sweep))
        sweep_dict = {header_value: np.array(column_values, dtype=float)
                      for header_value, column_values in zip(header, by_column_data)}

        # get the current and resonator number information
        basename = os.path.basename(file)
        current_uA_str, res_num = ramp_name_parse(basename)
        if "m" == current_uA_str[0]:
            current_uA = -1.0 * float(current_uA_str[1:])
        else:
            current_uA = float(current_uA_str)
        output_filename = self.make_res_fit_file(res_num=res_num)
        # if making a new file, make the header now
        if not os.path.isfile(output_filename):
            with open(output_filename, "w") as f:
                f.write("ramp_current_uA,res_num," + res_params_header + "\n")
        # fit the resonator
        popt, pcov = fit_resonator(freqs=sweep_dict['freq'],
                                   s21data=np.array(list(zip(sweep_dict['real'], sweep_dict['imag']))),
                                   data_format='RI', model=self.fit_model,
                                   error_est=self.error_est, throw_out=0,
                                   make_plot=False, plot_dir=output_dir,
                                   file_prefix="",
                                   show_plot=False)
        single_res_params = package_res_results(popt=popt, pcov=pcov, verbose=self.verbose)
        # res_fit = ResFit(file=file, group_delay=0, verbose=self.verbose, freq_units=self.res_freq_units,
        #                  remove_baseline_ripple=self.remove_baseline_ripple,
        #                  auto_process=True)
        with open(output_filename, 'a') as f:
            f.write(str(current_uA) + "," + res_num + "," + str(single_res_params) + "\n")

    def analyze_unprocessed(self):
        # get all the resonators sweeps that are available
        available_resonator_currents = set()
        current_tuple_to_filename = {}
        list_of_available_files = [os.path.join(self.data_output_folder, f) for f in os.listdir(self.data_output_folder)
                                   if os.path.isfile(os.path.join(self.data_output_folder, f))]
        for available_filename in list_of_available_files:
            current_uA_str, res_num = ramp_name_parse(os.path.basename(available_filename))
            if current_uA_str[0] == "m":
                current_uA_str = "-" + current_uA_str[1:]
            current_tuple = (float(current_uA_str), float(res_num))
            available_resonator_currents.add(current_tuple)
            current_tuple_to_filename[current_tuple] = available_filename
        # find the resonators that have been processed
        res_fit_dir = os.path.join(self.data_output_folder, "res_fits")
        processed_resonator_currents = set()
        if os.path.isdir(res_fit_dir):
            processed_resonator_files = [os.path.join(res_fit_dir, f) for f in os.listdir(res_fit_dir)
                                         if os.path.isfile(os.path.join(res_fit_dir, f))]
            for resonator_file in processed_resonator_files:
                res_data = ClassyReader(filename=resonator_file, delimiter=',')
                processed_resonator_currents.update({(ramp_current_uA, res_num)
                                                     for ramp_current_uA, res_num
                                                     in zip(res_data.ramp_current_uA, res_data.res_num)})
        # these are the resonators that are a available but have not been processed, process them now
        unprocessed_currents = available_resonator_currents - processed_resonator_currents
        files_to_analyze = [current_tuple_to_filename[current_tuple]
                            for current_tuple in available_resonator_currents - processed_resonator_currents]
        # [self.analyze_sweep(a_file) for a_file in files_to_analyze]
        with Pool(processes=4) as pool:
            pool.map(func=self.analyze_sweep, iterable=files_to_analyze)
        if unprocessed_currents == set():
            return True
        else:
            return False

    def eager_analyze(self):
        """
        Keep analysing unprocessed data until it is found that there was no additional data to process after 2 tries.
        """
        complete_status1 = False
        complete_status2 = False
        while not (complete_status1 and complete_status2):
            complete_status2 = complete_status1
            complete_status1 = self.analyze_unprocessed()
            if not (complete_status2 and complete_status1):
                time.sleep(self.eager_analyze_retry_time)
        if self.verbose:
            print(F"No new data for {self.eager_analyze_retry_time} seconds, " +
                  "eager_analyze() is complete")

    def analyze_all(self):
        list_of_files = [os.path.join(self.data_output_folder, f) for f in os.listdir(self.data_output_folder)
                         if os.path.isfile(os.path.join(self.data_output_folder, f))]
        for file_name in sorted(list_of_files):
            self.analyze_sweep(file=file_name)

    def load_flux_ramp_res_data(self):
        list_of_res_fit_files = [os.path.join(self.res_out_dir, f) for f in os.listdir(self.res_out_dir)
                                 if os.path.isfile(os.path.join(self.res_out_dir, f))]
        self.res_num_dict = {}
        for res_file in list_of_res_fit_files:
            res_num, run_num = os.path.basename(res_file).rstrip(".csv").lstrip("sdata_res_").split('_fit_')
            with open(res_file, 'r') as f:
                res_file_lines = f.readlines()
            header = res_file_lines[0].strip().split(',')
            current_dict = {}
            for res_data in res_file_lines[1:]:
                res_dict = {header_name: float(row_value)
                            for header_name, row_value in zip(header, res_data.strip().split(','))}
                current_dict[res_dict['ramp_current_uA']] = ResParams(**{column_name: res_dict[column_name]
                                                                         for column_name
                                                                         in res_params_header.split(',')})
            self.res_num_dict[int(res_num)] = current_dict

    def calc_lambda(self):
        # get the data
        self.load_flux_ramp_res_data()
        # arrange the data
        self.lambda_params = []
        for res_num in sorted(self.res_num_dict.keys()):
            res_calc = {}
            currents_uA, res_params = zip(*[(current, self.res_num_dict[res_num][current])
                                          for current in sorted(self.res_num_dict[res_num].keys())])
            try:
                I0fit, mfit, f2fit, Pfit, lambfit = lambdafit(I=np.array(currents_uA) * 1.0e-6,
                                                              f0=np.array([res_param.f0 for res_param in res_params]))
            except RuntimeError:
                I0fit = mfit = f2fit = Pfit = lambfit = np.nan
            self.lambda_params.append(LambdaParams(I0fit=I0fit, mfit=mfit, f2fit=f2fit, Pfit=Pfit, lambfit=lambfit,
                                                   res_num=res_num))

        with open(file=self.lambda_filename, mode='w') as f:
            f.write(lambda_header + "\n")
            res_params_to_lambda_params = {int(lamb_param.res_num): lamb_param for lamb_param in self.lambda_params}
            for res_num in sorted(res_params_to_lambda_params.keys()):
                single_lambda = res_params_to_lambda_params[res_num]
                f.write(str(single_lambda) + "\n")

    def read_lambda(self):
        lambda_data = floats_table(file=self.lambda_filename)
        self.lambda_params = []
        for I0fit, mfit, f2fit, Pfit, lambfit, res_num in list(zip(lambda_data["I0fit"], lambda_data["mfit"],
                                                                   lambda_data["f2fit"], lambda_data["Pfit"],
                                                                   lambda_data["lambfit"], lambda_data["res_num"])):
            self.lambda_params.append(LambdaParams(I0fit=I0fit, mfit=mfit, f2fit=f2fit, Pfit=Pfit, lambfit=lambfit,
                                                   res_num=res_num))

    def plot(self, show=False):
        self.load_flux_ramp_res_data()
        if os.path.isfile(self.lambda_filename):
            self.read_lambda()
        else:
            self.calc_lambda()
        res_params_to_lambda_params = {int(lamb_param.res_num): lamb_param for lamb_param in self.lambda_params}
        plot_dict = {}
        sorted_res_nums = sorted(res_params_to_lambda_params.keys())
        for res_num in list(sorted_res_nums):
            res_calc = {}
            currents_uA, res_params = zip(*[(current, self.res_num_dict[res_num][current])
                                          for current in sorted(self.res_num_dict[res_num].keys())])
            average_res_freq = np.mean([param.f0 for param in res_params])
            res_calc['average_res_qc'] = np.mean([param.Qc for param in res_params])
            res_calc['average_res_qi'] = np.mean([param.Qi for param in res_params])
            res_calc['average_res_zratio'] = np.mean([param.Zratio for param in res_params])

            lambda_params = res_params_to_lambda_params[int(res_num)]
            res_calc['lambfit'] = lambda_params.lambfit
            res_calc['flux_ramp_shift_kHz'] = lambda_params.Pfit * 1.0e6
            res_calc['fr_squid_mi_pH'] = (lambda_params.mfit * Phi0 / (2.0 * np.pi)) * 1.0e12  # converting to pico Henries
            plot_dict[average_res_freq] = res_calc

        # making the plots
        fig1 = plt.figure(1, figsize=(16, 9))
        # set up figures
        fig1.suptitle(F"{len(self.res_num_dict.keys())} resonators Band{'%02i' % self.band_number} Wafer{'%02i' % self.wafer} {self.date_str}")
        fig1.subplots_adjust(top=0.95, bottom=0.075, left=0.07, right=0.965, hspace=0.21, wspace=0.18)
        ax11 = fig1.add_subplot(231)
        ax12 = fig1.add_subplot(232)
        ax13 = fig1.add_subplot(233)
        ax14 = fig1.add_subplot(234)
        ax15 = fig1.add_subplot(235)
        ax16 = fig1.add_subplot(236)
        sorted_freq_list = sorted(plot_dict.keys())
        ax11.plot(sorted_freq_list, [plot_dict[res_freq]['average_res_qi'] for res_freq in sorted_freq_list],
                  color='firebrick', ls='None', marker='x')
        ax12.plot(sorted_freq_list, [plot_dict[res_freq]['average_res_qc'] for res_freq in sorted_freq_list],
                  color='dodgerblue', ls='None', marker='x')
        ax13.plot(sorted_freq_list, [plot_dict[res_freq]['average_res_zratio'] for res_freq in sorted_freq_list],
                  color='darkorchid', ls='None', marker='x')
        ax14.plot(sorted_freq_list, [plot_dict[res_freq]['lambfit'] for res_freq in sorted_freq_list],
                  color='darkgoldenrod', ls='None', marker='x')
        ax15.plot(sorted_freq_list, [plot_dict[res_freq]['flux_ramp_shift_kHz'] for res_freq in sorted_freq_list],
                  color='forestgreen', ls='None', marker='x')
        ax16.plot(sorted_freq_list, [plot_dict[res_freq]['fr_squid_mi_pH'] for res_freq in sorted_freq_list],
                  color='saddlebrown', ls='None', marker='x')

        # make the figure look nice
        ax11.grid(True)
        ax12.grid(True)
        ax13.grid(True)
        ax14.grid(True)
        ax15.grid(True)
        ax16.grid(True)
        ax11.legend(loc='upper right')
        ax12.legend(loc='upper right')
        ax13.legend(loc='upper right')
        ax14.legend(loc='upper right')
        ax11.set_xlabel("Frequency (GHz)")
        ax11.set_ylabel(r"Mean $Q_i$")
        ax12.set_xlabel("Frequency (GHz)")
        ax12.set_ylabel(r"Mean $Q_c$")
        ax13.set_xlabel("Frequency (GHz)")
        ax13.set_ylabel(r"$Z_{ratio}$")
        ax14.set_xlabel("Frequency (GHz)")
        ax14.set_ylabel("SQUID Lambda")
        ax14.set_xlabel("Frequency (GHz)")
        ax14.set_ylabel("SQUID Lambda")
        ax15.set_xlabel("Frequency (GHz)")
        ax15.set_ylabel("Flux Ramp Span kHz")
        ax16.set_xlabel("Frequency (GHz)")
        ax16.set_ylabel("FR - SQUID Mutual Inductance (pH)")
        plt.savefig(self.plot_filename)
        if show:
            plt.show()


lambda_header = "I0fit,mfit,f2fit,Pfit,lambfit,res_num"


class LambdaParams(NamedTuple):
    I0fit: float
    mfit: float
    f2fit: float
    Pfit: float
    lambfit: float
    res_num: Optional[int] = None

    def __str__(self):
        output_string = ""
        for attr in lambda_header.split(','):
            output_string += str(self.__getattribute__(attr)) + ","
        return output_string[:-1]


if __name__ == "__main__":
    ts = TinySweeps(wafer=7, band_number=1, date_str="2020-09-08", run_number=9, auto_run=False, verbose=True)
    ts.eager_analyze()
    # ts.plot()
