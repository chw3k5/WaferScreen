import os
from waferscreen.mc.data import DataManager
import ref

# edit these to look at existing measurements
location = "nist"
wafer = str(9)
date_str = "2021-01-26"

raw_dir = os.path.join(ref.working_dir, location, wafer, date_str, "raw")
raw_scans_dir = os.path.join(raw_dir, "scans")
raw_single_res_dir = os.path.join(raw_dir, "single_res")


test_scan_files = [os.path.join(raw_scans_dir, "scan3.800GHz-6.200GHz_2021-01-26 22-35-20.055941.csv")]
test_res_dirs = [raw_single_res_dir]


if __name__ == "__main__":
    do_scan = True
    do_res_sweeps = True

    # this statement is true if this file is run direct, it is false if this file imported from another file.
    # multithreading requires this statement to avoid infinite thread recursion, which is very bad.
    dm = DataManager(user_input_group_delay=None)
    if do_scan:
        dm.full_loop_scans(scan_paths=test_scan_files, cosine_filter=False, window_pad_factor=3, fitter_pad_factor=7,
                           show_filter_plots=False,
                           skip_interactive_plot=False, save_res_plots=True,
                           make_band_seeds=False, make_single_res_seeds=False)
    if do_res_sweeps:
        dm.full_loop_single_res(res_dirs=test_res_dirs, save_res_plots=True, reprocess_res=True, lamb_plots=True)
