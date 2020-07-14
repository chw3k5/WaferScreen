import os
from datetime import datetime

# References used in the WaferScreen Catalog
now = datetime.now()
today_str = F"{'%4i' % now.year}-{'%02i' % now.month}-{'%02i' % now.day}"


# directory tree used by WaferScreen Database, including folder creation for things in .gitignore
ref_file_path = os.path.dirname(os.path.realpath(__file__))
parent_dir, _ = ref_file_path.rsplit("WaferScreen", 1)
working_dir = os.path.join(parent_dir, "WaferScreen", "waferscreen")
s21_dir = os.path.join(working_dir, 's21')
output_dir = os.path.join(working_dir, "output")
if not os.path.isdir(output_dir):
    os.mkdir(output_dir)

# allow data type
s21_file_extensions = {"txt", "csv"}

# Constants used in WaferScreen
h = 6.6260755E-34  # Js
c = 299792458.0  # m/s
k = 1.380658E-23  # J/K

