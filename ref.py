import os
from datetime import datetime

# Instrument addresses
# go into Keysight GUI, enable HiSlip Interface, find address in SCPI Parser I/O
usbvna_address = "TCPIP0::687UWAVE-TEST::hislip_PXI10_CHASSIS1_SLOT1_INDEX0,4880::INSTR"
agilent8722es_address = "GPIB1::19::INSTR"
volt_source_address = "GPIB0::16::INSTR"
volt_source_port = 1

# References used in the WaferScreen Catalog
now = datetime.now()
today_str = F"{'%4i' % now.year}-{'%02i' % now.month}-{'%02i' % now.day}"


# directory tree used by WaferScreen Database, including folder creation for things in .gitignore
ref_file_path = os.path.dirname(os.path.realpath(__file__))
parent_dir, _ = ref_file_path.rsplit("WaferScreen", 1)
working_dir = os.path.join(parent_dir, "WaferScreen", "waferscreen")
s21_dir = os.path.join(working_dir, 's21')
check_out_dir = os.path.join(s21_dir, "check_out")
output_dir = os.path.join(working_dir, "output")
resonances_dir = os.path.join(output_dir, 'resonances')
if not os.path.isdir(output_dir):
    os.mkdir(output_dir)
if not os.path.isdir(resonances_dir):
    os.mkdir(resonances_dir)
if not os.path.isdir(check_out_dir):
    os.mkdir(check_out_dir)

# data types
s21_file_extensions = {"txt", "csv"}
file_extension_to_delimiter = {'csv': ",", 'psv': "|", 'txt': " ", "tsv": '\t'}

# Constants used in WaferScreen
h = 6.6260755E-34  # Js
c = 299792458.0  # m/s
k = 1.380658E-23  # J/K

