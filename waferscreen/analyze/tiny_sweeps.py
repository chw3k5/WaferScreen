import numpy as np
import math
import time
import os
from ref import output_dir, today_str, vna_address, volt_source_address, volt_source_port
from waferscreen.inst_control import Keysight_USB_VNA
from waferscreen.inst_control import srs_sim928
from waferscreen.analyze.find_and_fit import ResParams
from waferscreen.measure.res_sweep import VnaMeas

###
#  This code takes a single flux ramp sweep at one RF read power over a number of resonators
###


class TinySweeps:
    def __init__(self, wafer, band_number, run_number, port_power_dBm=-40, temperature_K=300, date_str=None, auto_run=False, verbose=True):
        self.verbose = verbose
        self.wafer = wafer
        self.band_number = band_number
        self.run_number = run_number
        if date_str is None:
            self.date_str = today_str
        else:
            self.date_str = date_str

        self.temperature_K = temperature_K

        self.data_output_folder = os.path.join(output_dir, '../s21', F"{self.wafer}", F'Band{self.band_number}',
                                               self.date_str, "flux_ramp")
        if not os.path.isdir(self.data_output_folder):
            os.mkdir(self.data_output_folder)
        self.file_delimiter = ","

        # resonator frequencies file
        self.freqs_filename = os.path.join(output_dir, '../s21', F"{wafer}", F'Band{self.band_number}', self.date_str,
                                           F"{self.wafer}_Trace{str(self.band_number)}_{self.date_str}" +
                                           F"_run{self.run_number}_fit.csv")
        self.res_freq_units = "GHz"
        self.res_num_limits = [1, -1]  # set to -1 to ignore limits

        # instrument addresses
        self.vna_address = vna_address  # go into Keysight GUI, enable HiSlip Interface, find address in SCPI Parser I/O
        self.volt_source_address = volt_source_address
        self.volt_source_port = volt_source_port

        # frequency sweep options
        self.meas_span = 1000  # kHz
        self.num_pts_per_sweep = 501  # 1601 for Aly8722ES, 100001 for P5002A
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
        self.current_steps = 251
        self.currents = np.linspace(self.current_min, self.current_max, self.current_steps)
        self.volts = np.linspace(self.current_min * self.rseries * 1e-6, self.current_max * self.rseries * 1e-6, self.current_steps)  # volts

        # make sure volts are in integer # of mV so SRS doesn't freak out
        for i in range(0, len(self.volts)):
            millivolts = int(round(self.volts[i] * 1000))
            self.volts[i] = millivolts / 1000
        if self.verbose:
            print("Currents to measure at:")
            print(self.currents)
            print("Voltages to measure at:")
            print(self.volts)

        ### group delay removal (best to get correct within 180 degrees over dataset) ####
        self.remove_group_delay = True
        self.group_delay = 27.292  # nanoseconds

        # uninitialized parameters for other methods in this class
        self.res_params = None
        self.res_freqs = None
        self.freq_bounds = None
        self.freq_bounds_array = None
        self.vna_meas = None

        if auto_run:
            self.load_res_freqs()
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
        print("")
        total_est_time = (self.current_steps * len(self.res_freqs) * (0.5 + self.num_pts_per_sweep / self.if_bw)) / 3600.0
        print("Total time to do FR sweep: " + str(total_est_time) + " hours")
        self.vna_meas = VnaMeas(fcenter_GHz=self.res_freqs[0], fspan_MHz=self.meas_span * 1e-6,
                                num_freq_points=self.num_pts_per_sweep, sweeptype="lin", if_bw_Hz=self.if_bw,
                                ifbw_track=self.ifbw_track, port_power_dBm=self.port_power, vna_avg=1, preset_vna=False,
                                output_filename=None, auto_init=True, temperature_K=self.temperature_K, verbose=self.verbose)

        print("")

        # connect to SIM928
        voltsource = srs_sim928.SRS_SIM928(address=volt_source_address, port=volt_source_port)
        voltsource.setvolt(self.volts[0])
        voltsource.output_on()

        print("")

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
                print("There is an error in this code....")

            if mask_res:

                # set frequency limits
                if self.keep_away_collisions:
                    self.vna_meas.set_sweep_range_min_max(fmin_GHz=self.freq_bounds[j][0], fmax_GHz=self.freq_bounds[j][1])
                    freqs = np.linspace(self.freq_bounds[j, 0], self.freq_bounds[j, 1], self.num_pts_per_sweep)
                else:
                    self.vna_meas.set_sweep_range_center_span(fcenter_GHz=self.res_freqs[j], fspan_MHz=self.meas_span * 1e-6)
                    freqs = np.linspace(self.res_freqs[j] - self.meas_span * 1e-6 / 2.0, self.res_freqs[j] +
                                        self.meas_span * 1e-6 / 2.0, self.num_pts_per_sweep)

                self.vna_meas.freqs = freqs
                for single_voltage, single_current in zip(self.volts, self.currents):
                    # set voltage source
                    cur_volt = voltsource.getvolt()
                    while abs(cur_volt - single_voltage) > 0.001:
                        voltsource.setvolt(single_voltage)
                        time.sleep(0.1)
                        cur_volt = voltsource.getvolt()
                    time.sleep(0.1)

                    print("Measuring resonator # " + str(j + 1) + "/" + str(len(self.res_freqs)) +
                          " at flux bias current " + str(single_current) + "uA")

                    # trigger a sweep to be done
                    self.vna_meas.vna_tiny_sweeps(single_current, res_number=j)

        # close connection to instruments
        self.vna_meas.vna_close()

        print("Connection to Instruments Closed")
