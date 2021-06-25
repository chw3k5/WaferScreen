# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import os
import sys
import datetime
"""
This is not PEP8 formatting, breaking up the import statements. I will explain:

The working direction for this project should always be ~/WaferScreen/
if you are in the python terminal then you should cd to this directory and start python and ui.py as follows
    $ cd your_path/WaferScreen/
    $ python
    >>> exec(open(waferscreen/mc/ui.py).read())

People can not remember this. So I have this code below that figures out where the WaferScreen project is on
the local computer and then manually add that to sys.path so that all the other modules of this project 
import properly. My hope is that this reduces the number of emails I get from people who refuse to use 
PyCharm and think project is something other than pure Python.

If you are no long making changes to this project, consider making a distribution from the setup.py file.
This way you can import WaferScreen like any other Python module.
"""
ref_file_path = os.path.dirname(os.path.realpath(__file__))
parent_dir, _ = ref_file_path.rsplit("WaferScreen", 1)
sys.path.append(os.path.join(parent_dir, 'WaferScreen'))
"""
These are modules that have been written specifically for the WaferScreen project.
"""
from waferscreen.analyze.s21_inductor import InductS21
from waferscreen.data_io.ui_io import dm_if_none
from waferscreen.data_io.data_pro import get_raw_scan_files_between_dates, get_raw_res_dirs_between_dates, \
    get_pro_res_dirs_between_dates
from waferscreen.mc.explore import full_analysis, LambExplore
from waferscreen.mc.device_summary import standard_summary_plots
from waferscreen.mc.device_stats import DeviceStats
from waferscreen.mc.wafer_plots import ParameterSurveys
from ref import device_summaries_dir


# edit these to look at existing measurements
start_date = datetime.date(year=2021, month=1, day=1)
end_date = datetime.date(year=2021, month=6, day=30)
# option to run the analysis apps
do_model_fit_processing = False  # takes a very long time
do_fit_exploration = True  # much less time
do_device_summaries = do_fit_exploration  # very fast
do_device_stats = do_fit_exploration  # very fast
do_wafer_coord_visualization = do_fit_exploration  # fast

# model fit processing in data_pro and s21_inductor
do_quick_look = False
do_scan = False
do_res_sweeps = not do_scan

# explore.py definition options, exploring the model fits
get_temperatures = True
redo_get_temps = False


# this statement is true if this file is run direct, it is false if this file imported from another file.
# multithreading requires this statement to avoid infinite thread recursion.
if __name__ == "__main__":
    # model based processing of raw s21 data
    if do_model_fit_processing or do_quick_look:
        # get the directors and file paths for the model fit data
        scan_files = get_raw_scan_files_between_dates(start_date=start_date, end_date=end_date)
        raw_res_dirs = get_raw_res_dirs_between_dates(start_date=start_date, end_date=end_date)
        pro_dirs = get_pro_res_dirs_between_dates(start_date=start_date, end_date=end_date)
        if do_quick_look:
            # set these to False for a quick look, do_quick_look only does quick looks
            do_scan = False
            do_res_sweeps = False
            do_fit_exploration = False
            # look at the latest scans first
            for test_scan_file in reversed(scan_files):
                # standard data induction workflow, but with 'save' False and 'show' True
                induct_s21 = InductS21(path=test_scan_file)
                induct_s21.induct()
                induct_s21.remove_group_delay()
                induct_s21.plot(show=True, save=False)
        # a data manager class for model fit processes
        dm = None
        if do_scan:
            # start the instance of the DataManger class if it is None
            dm = dm_if_none(dm=dm)
            # do all the 'scan' type data processing
            dm.full_loop_scans(scan_paths=scan_files, cosine_filter=False, window_pad_factor=3, fitter_pad_factor=7,
                               show_filter_plots=False,
                               do_interactive_plot=True, save_res_plots=True,
                               make_band_seeds=False, make_single_res_seeds=True)
        if do_res_sweeps:
            # start the instance of the DataManger class if it is None
            dm = dm_if_none(dm=dm)
            # do all the 'single_res' type data processing
            dm.full_loop_single_res(raw_res_dirs=raw_res_dirs, do_raw=False, save_phase_plot=True,
                                    pro_res_dirs=pro_dirs, do_pro=True, save_res_plots=True, reprocess_res=False,
                                    do_lamb=True, lamb_plots=True)  # lamb_plots is not properly toggling the plots
    # processing, linking, and analysis of model results explore.py
    example_lamb_explore = None
    if do_fit_exploration:
        # this function is a catch all for the analysis and processing in explore.py
        full_analysis(start_date=start_date, end_date=end_date, lamb_explore=example_lamb_explore,
                      get_temperatures=get_temperatures, redo_get_temps=redo_get_temps,
                      do_device_scale=True, do_measurement_scale=True)
    # analysis of the per-device data in device_summary.csv
    if do_device_summaries:
        standard_summary_plots(device_records_cvs_path=LambExplore.device_records_cvs_path,
                               output_dir=device_summaries_dir, hist_columns=None, hist_num_of_bins=20, hist_alpha=0.4)
    # analysis of the per-device statistics data in device_stats.csv
    if do_device_stats:
        device_stats = DeviceStats()
        device_stats.wafer_yield_study()
    # see per-device results presented as a function of wafer position
    if do_wafer_coord_visualization:
        requested_params = ['lamb_at_minus95dbm', 'flux_ramp_pp_khz_at_minus75dbm', 'q_i_mean_at_minus75dbm']
        # Data displayed by resonator position on wafer. Makes single file for each parameter that is 1 wafers per page.
        example_per_wafer_dsd = ParameterSurveys(device_summary_path=LambExplore.device_records_cvs_path,
                                                 params=requested_params,
                                                 output_dir=device_summaries_dir,
                                                 show_d_shift_in_x=False, show_f_design_shift_in_y=True)
