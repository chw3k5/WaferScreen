# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import os
import sys
import datetime
# Add the top level repositories to sys.path so that waferscreen, gluerobot, and submm_python_routines modules are found
ref_file_path = os.path.dirname(os.path.realpath(__file__))
parent_dir, _ = ref_file_path.rsplit("WaferScreen", 1)
sys.path.append(os.path.join(parent_dir, 'WaferScreen'))
# these are modules that have been written specifically for the wafer screen project.
from waferscreen.data_io.data_pro import DataManager, get_raw_scan_dirs_between_dates
from waferscreen.data_io.data_pro import get_raw_res_dirs_between_dates, get_pro_res_dirs_between_dates
from waferscreen.analyze.s21_inductor import InductS21


def to_raw_path(seed_name):
    return F"{seed_name}.csv"


# edit these to look at existing measurements
start_date = datetime.date(year=2021, month=4, day=7)
end_date = datetime.date(year=2021, month=4, day=7)

scan_files = get_raw_scan_dirs_between_dates(start_date=start_date, end_date=end_date)
raw_res_dirs = get_raw_res_dirs_between_dates(start_date=start_date, end_date=end_date)
pro_dirs = get_pro_res_dirs_between_dates(start_date=start_date, end_date=end_date)


if __name__ == "__main__":
    do_quick_look = False
    do_scan = False
    do_res_sweeps = not do_scan

    if do_quick_look:
        do_scan = False
        do_res_sweeps = False

    # this statement is true if this file is run direct, it is false if this file imported from another file.
    # multithreading requires this statement to avoid infinite thread recursion.
    if do_quick_look:
        for test_scan_file in scan_files:
            induct_s21 = InductS21(path=test_scan_file)
            induct_s21.induct()
            induct_s21.remove_group_delay()
            induct_s21.plot(show=True, save=False)

    dm = DataManager(user_input_group_delay=None)
    if do_scan:
        dm.full_loop_scans(scan_paths=scan_files, cosine_filter=False, window_pad_factor=3, fitter_pad_factor=7,
                           show_filter_plots=False,
                           do_interactive_plot=True, save_res_plots=True,
                           make_band_seeds=False, make_single_res_seeds=True)
    if do_res_sweeps:
        dm.full_loop_single_res(raw_res_dirs=raw_res_dirs, do_raw=False, save_phase_plot=False,
                                pro_res_dirs=pro_dirs, do_pro=True, save_res_plots=True, reprocess_res=False,
                                do_lamb=True, lamb_plots=True)
