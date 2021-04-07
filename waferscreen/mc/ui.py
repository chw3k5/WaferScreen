import os
import ref
import sys
# Add the top level repositories to sys.path so that waferscreen, gluerobot, and submm_python_routines modules are found
ref_file_path = os.path.dirname(os.path.realpath(__file__))
parent_dir, _ = ref_file_path.rsplit("WaferScreen", 1)
sys.path.append(os.path.join(parent_dir, 'WaferScreen'))
# these are modules that have been written specifically for the wafer screen project.
from waferscreen.mc.data import DataManager
from waferscreen.analyze.s21_inductor import InductS21


def to_raw_path(seed_name):
    return F"{seed_name}.csv"


# edit these to look at existing measurements
location = "nist"
wafer = "14"  # str(8)
date_str = "2021-04-06"  # ref.today_str # "2021-02-11"

raw_dir = os.path.join(ref.working_dir, location, wafer, date_str, "raw")
raw_scans_dir = os.path.join(raw_dir, "scans")
raw_single_res_dir = os.path.join(raw_dir, "single_res")

# seed_names = ["scan4.000GHz-4.500GHz_2021-02-12 05-48-00.492736",  # "scan3.900GHz-4.500GHz_2021-02-10 19-04-56.938380"
#               "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"]

seed_names = ["scan4.030GHz-4.190GHz_2021-04-06 22-12-09.099966"]

test_scan_files = [os.path.join(raw_scans_dir, to_raw_path(seed_name)) for seed_name in seed_names]
test_raw_res_dirs = [raw_single_res_dir]

pro_dir = os.path.join(ref.working_dir, location, wafer, date_str, "pro")
test_pro_res_dirs = [pro_dir]


if __name__ == "__main__":
    do_quick_look = False
    do_scan = True
    do_res_sweeps = not do_scan

    if do_quick_look:
        do_scan = False
        do_res_sweeps = False

    # this statement is true if this file is run direct, it is false if this file imported from another file.
    # multithreading requires this statement to avoid infinite thread recursion.
    if do_quick_look:
        for test_scan_file in test_scan_files:
            induct_s21 = InductS21(path=test_scan_file)
            induct_s21.induct()
            induct_s21.remove_group_delay()
            induct_s21.plot(show=True, save=False)

    dm = DataManager(user_input_group_delay=None)
    if do_scan:
        dm.full_loop_scans(scan_paths=test_scan_files, cosine_filter=False, window_pad_factor=3, fitter_pad_factor=7,
                           show_filter_plots=False,
                           do_interactive_plot=True, save_res_plots=True,
                           make_band_seeds=False, make_single_res_seeds=True)
    if do_res_sweeps:
        dm.full_loop_single_res(raw_res_dirs=test_raw_res_dirs, do_raw=True, save_phase_plot=True,
                                pro_res_dirs=test_pro_res_dirs, do_pro=True, save_res_plots=True, reprocess_res=True,
                                do_lamb=True, lamb_plots=True)
