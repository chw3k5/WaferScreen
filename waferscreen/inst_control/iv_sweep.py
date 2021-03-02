import os
import time
import datetime
import numpy as np
from ref import working_dir
from waferscreen.inst_control.keithley2450 import Keithley2450
import matplotlib.pyplot as plt


location = 'nist'
location_dir = os.path.join(working_dir, location)
if not os.path.isdir(location_dir):
    os.mkdir(location_dir)
iv_output_dir = os.path.join(location_dir, 'iv')
if not os.path.isdir(iv_output_dir):
    os.mkdir(iv_output_dir)


def gen_output_path(wafer, wafer_coord, structure_name, utc):
    utc_str = str(utc).replace(":", "-")
    basename = F"wafer{wafer}_coord{wafer_coord[0]}_{wafer_coord[1]}_{structure_name}_utc{utc_str}.csv"
    return os.path.join(iv_output_dir, basename)


class IVSweep:
    def __init__(self, wafer, wafer_coord, structure_name, connection_type='lan', verbose=True):
        self.wafer = wafer
        self.wafer_coord = wafer_coord
        self.test_structure = structure_name
        self.connection_type = connection_type
        self.verbose = verbose

        self.source = Keithley2450(connection_type=self.connection_type, verbose=self.verbose)
        self.source.startup()
        self.source.set_source_type(v_range=b"2", i_range=b"100e-6")

        self.output_file_name = None
        self.start_ua = None
        self.end_ua = None
        self.num_points = None
        self.step_ua = None
        self.sweep_array_ua = None
        self.sweeps_array_v = None
        self.meas_utc = None

    def sweep(self, start_ua, end_ua, num_points=101, v_gain=1.0):
        self.start_ua = start_ua
        self.end_ua = end_ua
        if self.start_ua > self.end_ua:
            self.start_ua, self.end_ua = self.end_ua, self.start_ua
        self.num_points = num_points

        output_data = self.source.sweep(start_curr=start_ua * 1.0e-6, stop_curr=end_ua * 1.0e-6, num_points=num_points, delay_s=0.1)
        self.sweep_array_ua = np.array([1.0e6 * a_tup[1] for a_tup in output_data])
        self.sweeps_array_v = np.array([a_tup[2] for a_tup in output_data]) / v_gain
        self.meas_utc = datetime.datetime.utcnow()
            
    def write(self):
        self.output_file_name = gen_output_path(wafer=self.wafer, wafer_coord=self.wafer_coord, 
                                                structure_name=self.test_structure, utc=self.meas_utc)
        with open(self.output_file_name, 'w') as f:
            f.write("current_ua,voltage_v\n")
            for current_ua, voltage_v in zip(self.sweep_array_ua, self.sweeps_array_v):
                f.write(F"{current_ua},{voltage_v}\n")

    def close(self):
        self.source.shutdown()

    def plot(self):
        a_array = self.sweep_array_ua * 1.0e-6
        mv_array = self.sweeps_array_v * 1.0e3
        res, v_offset = np.polyfit(a_array, self.sweeps_array_v, deg=1)
        fit_mv_array = ((self.sweep_array_ua * 1.0e-6 * res) + v_offset) * 1.0e3
        plt.plot(fit_mv_array, self.sweep_array_ua, ls='solid', color="firebrick", linewidth=5)
        plt.plot(mv_array, self.sweep_array_ua, ls='solid', linewidth=1, color='black',
                 marker="o", alpha=0.5, markerfacecolor="dodgerblue")

        plt.ylabel("Current (uA)")
        plt.xlabel("Voltage (mV)")
        plt.title(F"Resistance: {'%2.3f'% res} Ohms")
        plt.show(block=True)


class VVSweep:
    def __init__(self):
        self.sweeps_array_mv = None
        self.sweeps_array_uv = None

        self.source = Keithley2450(connection_type='lan', verbose=True)
        self.source.startup()
        self.source.set_source_type(source_type='voltage', sense_type='voltage', v_range=b'2')

    def sweep(self, start_uv=-10000, end_uv=10000, num_points=101):
        output_data = self.source.sweep(start_curr=start_uv * 1.0e-6, stop_curr=end_uv * 1.0e-6, num_points=num_points,
                                        delay_s=0.1)
        self.sweeps_array_uv = np.array([1.0e6 * a_tup[1] for a_tup in output_data])
        self.sweeps_array_mv = np.array([1.0e3 * a_tup[2] for a_tup in output_data])

    def plot(self):
        xv_array = self.sweeps_array_uv * 1.0e-6
        yv_array = self.sweeps_array_mv * 1.0e-3
        gain, v_offset = np.polyfit(xv_array, yv_array, deg=1)
        # plt.plot(self.sweeps_array_uv, (self.sweeps_array_uv * gain) + (v_offset * 1.0e3), ls='solid',
        #          color="firebrick", linewidth=5)
        plt.plot(self.sweeps_array_uv, self.sweeps_array_mv, ls='solid', linewidth=1, color='black',
                 marker="o", alpha=0.5, markerfacecolor="dodgerblue")

        plt.ylabel("Current (mV)")
        plt.xlabel("Voltage (uV)")
        plt.title(F"PreAmp Gain: {'%2.3f'% gain} V/V")
        plt.show(block=True)

    def close(self):
        self.source.shutdown()


def sweeper(start_ua, end_ua, num_points, wafer, wafer_coord, structure_name, plot=True, verbose=True, close=True):
    iv = IVSweep(wafer=wafer, wafer_coord=wafer_coord, structure_name=structure_name, connection_type='lan',
                 verbose=verbose)
    iv.sweep(start_ua=start_ua, end_ua=end_ua, num_points=num_points, v_gain=96.0)
    if close:
        iv.close()
    iv.write()
    if plot:
        iv.plot()
    return iv


def warm_squid_sweep(wafer, wafer_coord, structure_name=None):
    if structure_name is None:
        structure_name = "warm sweep"
    return sweeper(start_ua=-20, end_ua=20, num_points=100, wafer=wafer, wafer_coord=wafer_coord,
                   structure_name=structure_name, plot=True, verbose=True, close=True)


def is_alive_squid_sleep(wafer, wafer_coord, structure_name=None):
    if structure_name is None:
        structure_name = "warm is_alive"
    return sweeper(start_ua=-1, end_ua=1, num_points=10, wafer=wafer, wafer_coord=wafer_coord,
                   structure_name=structure_name, plot=True, verbose=True, close=True)


def test_preamp_gain():
    vv = VVSweep()
    vv.sweep()
    vv.plot()
    vv.close()
    return vv


if __name__ == "__main__":
    preamp_gain_test = False
    is_alive_test = True
    warm_squid_test = False
    wafer = 'null'
    wafer_coord = (0, 0)
    structure_name = 'warm res 130ohms'

    if preamp_gain_test:
        vv = test_preamp_gain()
    if is_alive_test:
        iv = is_alive_squid_sleep(wafer=wafer, wafer_coord=wafer_coord, structure_name=structure_name)
    if warm_squid_test:
        iv = warm_squid_sweep(wafer=wafer, wafer_coord=wafer_coord, structure_name=structure_name)

