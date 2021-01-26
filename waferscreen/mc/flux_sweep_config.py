import numpy as np
import os

# Output Base Directory
output_base_dir = os.path.join("D:\\", "waferscreen")

# Test Information
wafer = 9
location = 'nist'

# VNA Configuration
probe_power_dBm = -20
power_sweep_dBm = [-20]  # dBm
span_scale_factor = 400.0  # span_GHz = f_center_GHz / span_scale_factor
num_freq_points = 401
sweeptype = 'lin'
if_bw_Hz = 300
vna_avg = None

# Scan configuration (A Scan searches the entire RF band)
scan_f_min_GHz = 3.8
scan_f_max_GHz = 6.2
scan_stepsize_kHz = 10


# Flux Ramp parameters
ramp_rseries = 10000  # ohms
ramp_uA_min = -125  # uA
ramp_uA_max = 125  # uA
ramp_uA_steps = 26
ramp_span_as_multiple_of_quality_factor = 5.0
ramp_sweep_points = 200
ramp_uA = np.linspace(ramp_uA_min, ramp_uA_max, ramp_uA_steps)
ramp_volts = np.linspace(ramp_uA_min * ramp_rseries * 1e-6, 
                         ramp_uA_max * ramp_rseries * 1e-6,
                         ramp_uA_steps)
ramp_volt_to_uA = {volt: uA for volt, uA in zip(ramp_volts, ramp_uA)}
