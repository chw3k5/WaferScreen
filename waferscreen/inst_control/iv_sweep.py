import os
import time
import datetime
import numpy as np
from ref import working_dir
from waferscreen.inst_control.keithley2450 import Keithley2450


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

        self.output_file_name = None
        self.start_ua = None
        self.end_ua = None
        self.num_points = None
        self.step_ua = None
        self.sweep_array_ua = None
        self.sweeps_array_v = None
        self.meas_utc = None

    def sweep(self, start_ua, end_ua, num_points=100):
        self.start_ua = start_ua
        self.end_ua = end_ua
        if self.start_ua > self.end_ua:
            self.start_ua, self.end_ua = self.end_ua, self.start_ua
        self.num_points = num_points
        self.step_ua = (end_ua - start_ua) / (num_points - 1)
        self.sweep_array_ua = np.arange(self.start_ua, self.end_ua + (self.step_ua / 2.0), self.step_ua)
        self.sweeps_array_v = np.zeros(shape=len(self.sweep_array_ua))
        if True:  # with self.source:
            # Here were start send commands to the Keithley 2450, or whatever source meter you have
            self.source.__enter__()
            self.source.init_junction_sweep()
            for current_index, current_ua in list(enumerate(self.sweep_array_ua)):
                self.source.set_current(current_ua * 1.0E-6)
                self.sweeps_array_v[current_index] = self.source.get_volt()

        self.meas_utc = datetime.datetime.utcnow()
            
    def write(self):
        self.output_file_name = gen_output_path(wafer=self.wafer, wafer_coord=self.wafer_coord, 
                                                structure_name=self.test_structure, utc=self.meas_utc)
        with open(self.output_file_name, 'w') as f:
            f.write("current_ua,voltage_v\n")
            for current_ua, voltage_v in zip(self.sweep_array_ua, self.sweeps_array_v):
                f.write(F"{current_ua},{voltage_v}\n")
        

if __name__ == "__main__":
    iv = IVSweep(wafer=11, wafer_coord=(0, 0), structure_name='warm res 130ohms', connection_type='lan', verbose=True)
    iv.sweep(start_ua=0, end_ua=100, num_points=200)
    iv.write()
