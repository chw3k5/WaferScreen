import os
import getpass
from getpass import getuser
from datetime import datetime

# Instrument addresses
usbvna_address = "TCPIP0::687UWAVE-TEST::hislip_PXI10_CHASSIS1_SLOT1_INDEX0,4880::INSTR"
agilent8722es_address = "GPIB1::19::INSTR"
flux_ramp_address = "GPIB0::17::INSTR"
volt_source_port = 1

# multiprocessing
multiprocessing_threads = 1  # The Nist computer has an Intel Xeon W-2123, 8 threads on 4 cores.

# References used in the WaferScreen Catalog
now = datetime.now()
today_str = F"{'%4i' % now.year}-{'%02i' % now.month}-{'%02i' % now.day}"

# for initializations that are dependent on the machine and user
nist_users = ["uvwave", 'chw3k5']

# directory tree used by WaferScreen Database, including folder creation for things in .gitignore
ref_file_path = os.path.dirname(os.path.realpath(__file__))
parent_dir, _ = ref_file_path.rsplit("WaferScreen", 1)
if getuser() == 'uvwave':
    working_dir = os.path.join("D:\\", "waferscreen")
else:
    working_dir = os.path.join(parent_dir, "WaferScreen", "waferscreen")


# reference file locations
s21_metadata_nist = os.path.join(working_dir, "ref_data", "s21_metadata_nist.txt")
runtime_log = os.path.join(working_dir, "runtime_log_waferscreeen.txt")
if not os.path.isfile(runtime_log):
    f = open(runtime_log, 'w')
    f.close()

# data types
file_extension_to_delimiter = {'csv': ",", 'psv': "|", 'txt': " ", "tsv": '\t'}

# Constants used in WaferScreen
h = 6.6260755E-34  # Js
c = 299792458.0  # m/s
k = 1.380658E-23  # J/K

# Simons Observatory Frequency Band definitions
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
