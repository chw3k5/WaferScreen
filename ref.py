# Copyright (C) 2018 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import os
import sys
import getpass
import matplotlib as mpl
from datetime import datetime
# To change the backend for matplotlib we must change it before matplotlib.pyplot is imported.
mpl.use(backend="TkAgg")

# Instrument addresses
usbvna_address = "TCPIP0::687UWAVE-TEST::hislip_PXI10_CHASSIS1_SLOT1_INDEX0,4880::INSTR"
agilent8722es_address = "GPIB1::19::INSTR"
flux_ramp_address = "GPIB0::17::INSTR"
volt_source_port = 1

# Debug mode
debug_mode = False
# multiprocessing
current_user = getpass.getuser()
if debug_mode:
    multiprocessing_threads = None
    mpl.use(backend='module://backend_interagg')
elif current_user == "chw3k5":
    multiprocessing_threads = 4  # Caleb's other computers
elif current_user in "cwheeler":
    multiprocessing_threads = 16  # Mac Pro 8-core intel core i9 processor 16 threads
elif current_user == "uvwave":
    multiprocessing_threads = 8  # The Nist computer has an Intel Xeon W-2123, 8 threads on 4 cores.
elif current_user == "bjd":
    multiprocessing_threads = 10  # 4 core machine
else:
    # this will do standard linear processing.
    multiprocessing_threads = None

# References used in the WaferScreen Catalog
now = datetime.now()
today_str = F"{'%4i' % now.year}-{'%02i' % now.month}-{'%02i' % now.day}"

# for initializations that are dependent on the machine and user
nist_users = ["uvwave", 'chw3k5']

# directory tree used by WaferScreen Database, including folder creation for things in .gitignore
ref_file_path = os.path.dirname(os.path.realpath(__file__))
parent_dir, _ = ref_file_path.rsplit("WaferScreen", 1)
if getpass.getuser() == 'uvwave':
    working_dir = os.path.join("D:\\", "waferscreen")
else:
    working_dir = os.path.join(parent_dir, "WaferScreen", "waferscreen")

output_dirs = [os.path.join(working_dir, output_folder) for output_folder in ["nist"]]


# reference file locations
s21_metadata_nist = os.path.join(working_dir, "ref_data", "s21_metadata_nist.txt")
runtime_log = os.path.join(working_dir, "runtime_log_waferscreeen.txt")
processing_log = os.path.join(working_dir, "processing_log_waferscreeen.txt")
flag_file_path = os.path.join(parent_dir, "WaferScreen", "waferscreen", "res_flags.csv")
umux_screener_assembly_path = os.path.join(parent_dir, "WaferScreen", "waferscreen", "umux_screener_assembly.csv")
too_long_did_not_read_dir = os.path.join(parent_dir, "WaferScreen", "waferscreen", "tldr")
if not os.path.isdir(too_long_did_not_read_dir):
    os.mkdir(too_long_did_not_read_dir)
starcryo_logs_dir = os.path.join("C:\\Users\\chw3k5\\Downloads", "DataLogs")
chip_per_band_metadata = os.path.join(parent_dir, "WaferScreen", "waferscreen", "umux100k_v321_banddef_summary.csv")
wafer_pos_metadata = os.path.join(parent_dir, "WaferScreen", "waferscreen", "wafer_pos_metadata.csv")

if current_user == 'uvwave':
    if not os.path.isfile(runtime_log):
        f = open(runtime_log, 'w')
        f.close()
    with open(runtime_log, "a") as f:
        f.write(F"RunStart(utc):{str(datetime.utcnow())}\n")

# data types
file_extension_to_delimiter = {'csv': ",", 'psv': "|", 'txt': " ", "tsv": '\t'}
s21_file_extensions = {"txt", "csv"}

# Constants used in WaferScreen
h = 6.6260755E-34  # Js
c = 299792458.0  # m/s
k = 1.380658E-23  # J/K
phi_0 = 2.068e-15  # magnetic flux quantum


# processing types
s21_processing_types = {"phase", "windowbaselinesmoothedremoved"}


# Simons Observatory Frequency Band definitions
band_names = ["Band00", "Band01", "Band02", "Band03", "Band04", "Band05", "Band06",
              "Band07", "Band08", "Band09", "Band10", "Band11", "Band12", "Band13"]
band_params = {"Band00": {"min_GHz": 4.019, "max_GHz": 4.147},
               "Band01": {"min_GHz": 4.152, "max_GHz": 4.280},
               "Band02": {"min_GHz": 4.285, "max_GHz": 4.414},
               "Band03": {"min_GHz": 4.419, "max_GHz": 4.581},
               "Band04": {"min_GHz": 4.584, "max_GHz": 4.714},
               "Band05": {"min_GHz": 4.718, "max_GHz": 4.848},
               "Band06": {"min_GHz": 4.852, "max_GHz": 4.981},
               "Band07": {"min_GHz": 5.019, "max_GHz": 5.147},
               "Band08": {"min_GHz": 5.152, "max_GHz": 5.280},
               "Band09": {"min_GHz": 5.286, "max_GHz": 5.413},
               "Band10": {"min_GHz": 5.421, "max_GHz": 5.581},
               "Band11": {"min_GHz": 5.585, "max_GHz": 5.714},
               "Band12": {"min_GHz": 5.718, "max_GHz": 5.848},
               "Band13": {"min_GHz": 5.851, "max_GHz": 5.981},
               }

for band in band_params.keys():
    params_dict = band_params[band]
    params_dict["span_GHz"] = params_dict["max_GHz"] - params_dict["min_GHz"]
    params_dict["center_GHz"] = (params_dict["max_GHz"] + params_dict["min_GHz"]) * 0.5
    params_dict["band_num"] = int(band.lower().replace("band", ""))


def get_band_name(f_ghz):
    for band_name in band_names:
        band_dict = band_params[band_name]
        if band_dict["min_GHz"] <= f_ghz <= band_dict['max_GHz']:
            return band_name
    return None

# smurf (FPGA readout) definitions
smurf_keepout_zones_ghz = [(3.981 + 0.5 * zone_number, 4.019 + 0.5 * zone_number) for zone_number in range(5)]


def in_smurf_keepout(f_ghz):
    for keep_out_min, keep_out_max in smurf_keepout_zones_ghz:
        if keep_out_min < f_ghz < keep_out_max:
            return True
    return False


def in_band(band_str, f_ghz):
    if band_params[band_str]['min_GHz'] <= f_ghz <= band_params[band_str]['max_GHz']:
        return True
    else:
        return False


"""wafer acceptance criteria"""
# Qi Quality Factor
min_q_i = 1.2e5

# Lambda
min_lambda = 0.2
max_lambda = 0.6
average_lambda = 0.3

# Peak-to-peak shift (Flux Ramp Span) in Hertz (Hz)
peak_to_peak_shift_hz = 60.0
