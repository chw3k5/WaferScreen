import os
from waferscreen.mc.data import DataManager
from waferscreen.analyze.s21_inductor import InductS21
import ref

# edit these to look at existing measurements
location = "nist"
wafer = str(9)
date_str = "2021-02-09"

raw_dir = os.path.join(ref.working_dir, location, wafer, date_str, "raw")
raw_scans_dir = os.path.join(raw_dir, "scans")
raw_single_res_dir = os.path.join(raw_dir, "single_res")

basename = "scan3.800GHz-6.600GHz_2021-02-10 01-01-10.284327.csv"
test_scan_files = [os.path.join(raw_scans_dir, basename)]
test_res_dirs = [raw_single_res_dir]


if __name__ == "__main__":
    do_quick_look = False
    do_scan = True
    do_res_sweeps = not do_scan

    # this statement is true if this file is run direct, it is false if this file imported from another file.
    # multithreading requires this statement to avoid infinite thread recursion, which is very bad.
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
                           skip_interactive_plot=False, save_res_plots=True,
                           make_band_seeds=False, make_single_res_seeds=False)
    if do_res_sweeps:
        dm.full_loop_single_res(res_dirs=test_res_dirs, save_res_plots=True, reprocess_res=True, lamb_plots=True)
