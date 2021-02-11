import os
from waferscreen.mc.data import DataManager
from waferscreen.analyze.s21_inductor import InductS21
import ref

# edit these to look at existing measurements
location = "nist"
wafer = str(11)
date_str = "2021-02-11"

raw_dir = os.path.join(ref.working_dir, location, wafer, date_str, "raw")
raw_scans_dir = os.path.join(raw_dir, "scans")
raw_single_res_dir = os.path.join(raw_dir, "single_res")

seed_name = "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"
test_scan_files = [os.path.join(raw_scans_dir, F"{seed_name}.csv")]
test_raw_res_dirs = [raw_single_res_dir]

pro_dir = os.path.join(ref.working_dir, location, wafer, date_str, "pro")
test_pro_res_dirs = [pro_dir]


if __name__ == "__main__":
    do_quick_look = False
    do_scan = False
    do_res_sweeps = not do_scan

    if do_quick_look:
        do_scan = True
        do_res_sweeps = False


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
                           make_band_seeds=False, make_single_res_seeds=True)
    if do_res_sweeps:
        dm.full_loop_single_res(raw_res_dirs=test_raw_res_dirs, do_raw=False,
                                pro_res_dirs=test_pro_res_dirs, do_pro=True,
                                do_lamb=False,
                                save_res_plots=True, reprocess_res=True, lamb_plots=True)
