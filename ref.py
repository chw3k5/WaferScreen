import os
import sys
import getpass
import matplotlib as mpl
from datetime import datetime
# To change the backend for matplotlib we must change it before matplotlib.pyplot is imported.
if sys.platform == "win32":
    mpl.use(backend="TkAgg")
elif sys.platform == 'darwin':
    mpl.use(backend="MacOSX")
import matplotlib as mpl
from datetime import datetime
# To change the backend for matplotlib we must change it before matplotlib.pyplot is imported.
if sys.platform == "win32":
    mpl.use(backend="TkAgg")
elif sys.platform == 'darwin':
    mpl.use(backend="MacOSX")
# Debug mode
debug_mode = False

# Instrument addresses
usbvna_address = "TCPIP0::687UWAVE-TEST::hislip_PXI10_CHASSIS1_SLOT1_INDEX0,4880::INSTR"
agilent8722es_address = "GPIB1::19::INSTR"
flux_ramp_address = "GPIB0::17::INSTR"
volt_source_port = 1

# multiprocessing
current_user = getpass.getuser()
if debug_mode:
    multiprocessing_threads = None
elif current_user == "chw3k5":
    multiprocessing_threads = 4  # Caleb's other computers
elif current_user in "cwheeler":
    multiprocessing_threads = 8  # Mac Pro 8-core intel core i9 processor 16 threads
elif current_user == "uvwave":
    multiprocessing_threads = 2  # The Nist computer has an Intel Xeon W-2123, 8 threads on 4 cores.
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
flag_file_path = os.path.join(working_dir, "res_flags.csv")

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

s21_processing_types = {"phase", "windowbaselinesmoothedremoved"}

google_drive_api_key = "AIzaSyAJBe0g27WNUhsjSBLoLSNlT4WIdDgUJ_U"