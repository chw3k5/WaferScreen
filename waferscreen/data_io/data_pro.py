# Copyright (C) 2018 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import os
import ref
import logging
import datetime
from multiprocessing import Pool
from waferscreen.analyze.s21_inductor import InductS21
from waferscreen.analyze.res_pipeline import ResPipe
from waferscreen.analyze.lambcalc import LambCalc
from waferscreen.data_io.s21_io import input_to_output_filename
from waferscreen.data_io.exceptions import ResProcessingError, LambdaProcessingError
from concurrent.futures.process import ProcessPoolExecutor

# initialize resonator processing log settings
logging.basicConfig(filename=ref.processing_log, level=logging.INFO)


def get_subdirs(rootdir, matching_str):
    folder_list = []
    for root, subdirs, files in os.walk(rootdir):
        for subdir in subdirs:
            if subdir == matching_str:
                folder_list.append(os.path.join(root, subdir))
    return folder_list


def get_all_subdirs(rootdir):
    folder_list = []
    for root, subdirs, files in os.walk(rootdir):
        for subdir in subdirs:
            folder_list.append(os.path.join(root, subdir))
    return folder_list


def get_pro_data_dirs():
    pro_data_dirs = []
    [pro_data_dirs.extend(get_subdirs(rootdir=rootdir, matching_str="pro")) for rootdir in ref.output_dirs]
    return pro_data_dirs


def get_report_dirs():
    report_data_dirs = []
    [report_data_dirs.extend(get_subdirs(rootdir=rootdir, matching_str="report")) for rootdir in ref.output_dirs]
    return report_data_dirs


def get_lamb_dirs():
    lamb_data_dirs = []
    [lamb_data_dirs.extend(get_subdirs(rootdir=rootdir, matching_str="lambda")) for rootdir in ref.output_dirs]
    return lamb_data_dirs


def get_dirs_between_dates(start_date, end_date):
    """
    At the "date" level of directory hierarchy (the folder names ar in the format (YYYY-MM-DD)
    Get all the directory names between the date arguments

    :param start_date: use datetime.date()
    :param end_date: use datetime.date()
    :return: list - empty or elements that are the full paths (str) for 'date'
                    directories (YYYY-MM-DD) between the date arguments
    """
    date_dirs_in_range = []
    for location_dir in ref.output_dirs:
        # get all the wafer-number directories
        wafer_number_dirs = []
        for wafer_number_dir_name in os.listdir(location_dir):
            wafer_number_dir_test = os.path.join(location_dir, wafer_number_dir_name)
            if os.path.isdir(wafer_number_dir_test):
                # wafer number directory name can be converted to and integer, ignore calibration directories and others
                try:
                    int(wafer_number_dir_name)
                except ValueError:
                    pass
                else:
                    wafer_number_dirs.append(wafer_number_dir_test)
        # get all the date name directory directories between the start and end dates
        for wafer_number_dir in wafer_number_dirs:
            for date_string_dir in os.listdir(wafer_number_dir):
                # move on if the directory is not in date format (like hidden directories i.e. .DS_Store)
                try:
                    dt_this_dir = datetime.datetime.strptime(date_string_dir, "%Y-%m-%d").date()
                except ValueError:
                    pass
                else:
                    if start_date <= dt_this_dir <= end_date:
                        date_dirs_in_range.append(os.path.join(wafer_number_dir, date_string_dir))
    return date_dirs_in_range


def get_lamb_dirs_between_dates(start_date, end_date):
    """
    Get all the directory names where processed Lambda parameter data is stored between
    the date arguments.

    :param start_date: use datetime.date()
    :param end_date: use datetime.date()
    :return: list - empty or elements that are the full paths (str) for Lambda data directories
                    between the date arguments.
    """
    lamb_data_dirs = []
    #  within the available date dirs, get the lambda dirs
    [lamb_data_dirs.extend(get_subdirs(rootdir=date_dir, matching_str="lambda"))
     for date_dir in get_dirs_between_dates(start_date, end_date)]
    return lamb_data_dirs


def get_raw_scan_dirs_between_dates(start_date, end_date):
    """
    Between the date arguments, get all the full paths for the directories for raw scan files.

    A seed filename is taken from 'scan' type files, where resonators are
    initially identified. This can be used to find all 'scan' and 'resonator' data,
    both raw and processed,

    :param start_date: use datetime.date()
    :param end_date: use datetime.date()
    :return: list - empty or elements are the full paths (str) for raw scan (seed) data
                    directories between the date arguments.
    """
    return [os.path.join(date_dir, "raw", "scans")
            for date_dir in get_dirs_between_dates(start_date, end_date)]


def get_raw_scan_files_between_dates(start_date, end_date):
    raw_scan_files = []
    for scan_dir in get_raw_scan_dirs_between_dates(start_date, end_date):
        for test_scan_file in os.listdir(scan_dir):
            full_path = os.path.join(scan_dir, test_scan_file)
            if os.path.isfile(full_path) and test_scan_file[0:4] == "scan":
                raw_scan_files.append(full_path)
    return raw_scan_files


def get_raw_res_dirs_between_dates(start_date, end_date):
    """
    Between the date arguments, get all the full paths for the directories for raw
    single resonator directories.


    :param start_date: use datetime.date()
    :param end_date: use datetime.date()
    :return: list - empty or elements are the full paths (str) for raw single_res data
                    directories between the date arguments.
    """
    return [os.path.join(date_dir, "raw", "single_res")
            for date_dir in get_dirs_between_dates(start_date, end_date)]


def get_pro_res_dirs_between_dates(start_date, end_date):
    """
    Between the date arguments, get all the full paths for the directories for pro (processed)
    data directories.

    :param start_date: use datetime.date()
    :param end_date: use datetime.date()
    :return: list - empty or elements are the full paths (str) for pro (processed) data
                    directories between the date arguments.
    """
    return [os.path.join(date_dir, "pro")
            for date_dir in get_dirs_between_dates(start_date, end_date)]


def get_pro_s21_scans(process_type):
    pro_data_dirs = get_pro_data_dirs()
    scan_dirs = []
    [scan_dirs.extend(get_all_subdirs(rootdir=pro_data_dir)) for pro_data_dir in pro_data_dirs]
    len_pro_type = len(process_type)
    scan_files = []
    for pro_data_folder in scan_dirs:
        for basename in os.listdir(pro_data_folder):
            if os.path.isfile(os.path.join(pro_data_folder, basename)):
                filename, extension = basename.rsplit(".", 1)
                if len_pro_type < len(filename):
                    if filename[-len_pro_type:] == process_type and extension.lower() in ref.s21_file_extensions:
                        test_name = os.path.join(pro_data_folder, basename)
                        if os.path.isfile(test_name):
                            scan_files.append(test_name)
    return scan_files


def get_all_lamb_files():
    lamb_files = []
    for lamb_data_dir in get_lamb_dirs():
        for basename in os.listdir(lamb_data_dir):
            if "." in basename:
                test_basename_prefix, extension = basename.rsplit(".", 1)
                if extension in ref.s21_file_extensions and "lambda_" == test_basename_prefix[:7]:
                    lamb_files.append(os.path.join(lamb_data_dir, basename))
    return lamb_files


def get_lamb_files_between_dates(start_date, end_date):
    lamb_files = []
    for lamb_data_dir in get_lamb_dirs_between_dates(start_date=start_date, end_date=end_date):
        for basename in os.listdir(lamb_data_dir):
            if "." in basename:
                test_basename_prefix, extension = basename.rsplit(".", 1)
                if extension in ref.s21_file_extensions and "lambda_" == test_basename_prefix[:7]:
                    lamb_files.append(os.path.join(lamb_data_dir, basename))
    return lamb_files


def get_pro_res_dirs():
    pro_res_dirs = []
    [pro_res_dirs.extend([os.path.join(pro_data_dir, test_dir) for test_dir in os.listdir(pro_data_dir)
                          if os.path.isdir(os.path.join(pro_data_dir, test_dir)) and test_dir[:3] == "res"])
     for pro_data_dir in get_pro_data_dirs()]
    return pro_res_dirs


def get_pro_res_dirs_from_sin_res(single_res_parent_dirs):
    if single_res_parent_dirs is None:
        # by default, get all the processed resonator directories.
        pro_res_dirs = get_pro_res_dirs()
    else:
        pro_res_dirs = []
        [pro_res_dirs.extend([os.path.join(pro_data_dir, test_dir) for test_dir in os.listdir(pro_data_dir)
                              if os.path.isdir(os.path.join(pro_data_dir, test_dir)) and test_dir[:3] == "res"])
         for pro_data_dir in single_res_parent_dirs]
    return pro_res_dirs


def get_single_res_parent_dirs(pro_dirs):
    single_res_parent_dirs = []
    for pro_dir in pro_dirs:
        for test_dir in os.listdir(pro_dir):
            test_path = os.path.join(pro_dir, test_dir)
            if os.path.isdir(test_path) and test_dir[:3] == "res":
                single_res_parent_dirs.append(test_path)
    return single_res_parent_dirs


def single_res_pro(single_res_file, verbose, reprocess, save_res_plots):
    res_pipe = ResPipe(s21_path=single_res_file, verbose=verbose)
    res_pipe.read()
    if reprocess or res_pipe.fitted_resonators_parameters is None:
        try:
            res_pipe.analyze_single_res(save_res_plots=save_res_plots)
        except ResProcessingError:
            logging.exception(F'File: {single_res_file} | Proceeding Exception: {ResProcessingError}')


phase_corrected_scan_files = []


def raw_process(path, save_phase_plot=True, user_input_group_delay=None):
    inducts21 = InductS21(path)
    inducts21.induct()
    inducts21.remove_group_delay(user_input_group_delay=user_input_group_delay)
    inducts21.write()
    if inducts21.metadata["export_type"] == "scan":
        phase_corrected_scan_files.append(inducts21.output_file)
    if save_phase_plot:
        inducts21.plot()


def lamb_process(lamb_dir, lamb_plots=True):
    single_lamb_calc = LambCalc(lamb_dir=lamb_dir, auto_fit=False, plot=lamb_plots)
    single_lamb_calc.read_input()
    try:
        single_lamb_calc.sort_by_type()
    except LambdaProcessingError:
        logging.exception(F'File: {lamb_dir} | Proceeding Exception: {LambdaProcessingError}')


class DataManager:
    def __init__(self, user_input_group_delay=None, verbose=True):
        self.user_input_group_delay = user_input_group_delay
        self.verbose = verbose
        self.raw_search_dirs = ref.output_dirs

        self.raw_scan_files = []
        self.phase_corrected_scan_files = []

        self.raw_bands_files = []
        self.phase_corrected_bands_files = []

        self.raw_single_res_files = []
        self.phase_corrected_single_res_files = []

        self.windowbaselinesmoothedremoved_scan_files = []

    def from_scratch(self):
        self.raw_process_all()

    def get_all_scan_files(self):
        for rootdir in ref.output_dirs:
            raw_dirs = get_subdirs(rootdir=rootdir, matching_str='raw')

            # scans
            scans_dirs = []
            [scans_dirs.extend(get_subdirs(rootdir=raw_dir, matching_str='scans')) for raw_dir in raw_dirs]
            [self.raw_scan_files.extend([os.path.join(scans_dir, path) for path in os.listdir(scans_dir)])
             for scans_dir in scans_dirs]

    def get_band_or_res_from_dir(self, file_type, bands_or_res_dirs):
        parent_scan_dirs = []
        number_dirs = []
        output_var = []
        [parent_scan_dirs.extend(get_all_subdirs(rootdir=bands_or_res_dir))
         for bands_or_res_dir in bands_or_res_dirs]
        [number_dirs.extend(get_all_subdirs(rootdir=parent_scan_dir)) for parent_scan_dir in parent_scan_dirs]
        for number_dir in number_dirs:
            for basename in os.listdir(number_dir):
                if "." in basename:
                    basename_prefix, _extension = basename.rsplit(".", 1)
                    if basename_prefix != "seed":
                        full_path = os.path.join(number_dir, basename)
                        output_var.append(full_path)
        if file_type == "bands":
            self.raw_bands_files = output_var
        elif file_type == "single_res":
            self.raw_single_res_files = output_var
        else:
            raise KeyError

    def get_all_single_res_or_bands_files(self, file_type="bands"):
        for rootdir in ref.output_dirs:
            raw_dirs = get_subdirs(rootdir=rootdir, matching_str='raw')
            matching_str = file_type
            bands_or_res_dirs = []
            [bands_or_res_dirs.extend(get_subdirs(rootdir=raw_dir, matching_str=matching_str)) for raw_dir in raw_dirs]
            self.get_band_or_res_from_dir(file_type=file_type, bands_or_res_dirs=bands_or_res_dirs)

    def raw_process_all(self):
        self.raw_process_all_scans()
        self.raw_process_all_bands()
        self.raw_process_all_single_res()

    def raw_process_all_scans(self):
        self.get_all_scan_files()
        for raw_scan_path in self.raw_scan_files:
            raw_process(path=raw_scan_path, save_phase_plot=True)
            self.phase_corrected_scan_files = phase_corrected_scan_files

    def raw_process_all_bands(self):
        self.get_all_single_res_or_bands_files(file_type="bands")
        for raw_band_path in self.raw_bands_files:
            _dirname, basename = os.path.split(raw_band_path)
            basename_prefix, _extension = basename.rsplit(".", 1)
            if basename_prefix != "seed":
                raw_process(path=raw_band_path, save_phase_plot=True)

    def raw_process_all_single_res(self):
        self.get_all_single_res_or_bands_files(file_type="single_res")
        for raw_single_res_path in self.raw_single_res_files:
            _dirname, basename = os.path.split(raw_single_res_path)
            basename_prefix, _extension = basename.rsplit(".", 1)
            if basename_prefix != "seed":
                raw_process(path=raw_single_res_path, save_phase_plot=True, user_input_group_delay=False)

    def analyze_resonator_files(self, s21_files, cosine_filter=False,
                                window_pad_factor=3, fitter_pad_factor=6,
                                show_filter_plots=False, skip_interactive_plot=False,
                                save_res_plots=False):
        for s21_file in s21_files:
            res_pipe = ResPipe(s21_path=s21_file, verbose=self.verbose)
            res_pipe.read()
            res_pipe.find_window(cosine_filter=cosine_filter,
                                 window_pad_factor=window_pad_factor, fitter_pad_factor=fitter_pad_factor,
                                 show_filter_plots=show_filter_plots,
                                 debug_mode=skip_interactive_plot)
            res_pipe.analyze_resonators(save_res_plots=save_res_plots)
            data_filename, plot_filename = input_to_output_filename(processing_steps=["windowBaselineSmoothedRemoved"],
                                                                    input_path=s21_file)
            self.windowbaselinesmoothedremoved_scan_files.append(data_filename)

    def analyze_scans_resonators(self, scan_paths=None, cosine_filter=False,
                                 window_pad_factor=3, fitter_pad_factor=6,
                                 show_filter_plots=False, skip_interactive_plot=False,
                                 save_res_plots=False):
        if scan_paths is None:
            # by default, get all the scans files
            self.phase_corrected_scan_files = get_pro_s21_scans(process_type="phase")
            phase_corrected_scan_files = self.phase_corrected_scan_files
        self.analyze_resonator_files(s21_files=scan_paths, cosine_filter=cosine_filter,
                                     window_pad_factor=window_pad_factor, fitter_pad_factor=fitter_pad_factor,
                                     show_filter_plots=show_filter_plots, skip_interactive_plot=skip_interactive_plot,
                                     save_res_plots=save_res_plots)

    def analyze_single_res(self, single_res_parent_dirs=None, save_res_plots=True, reprocess=False):
        for single_res_folder in get_pro_res_dirs_from_sin_res(single_res_parent_dirs):
            single_res_files_this_folder = []
            for test_file in os.listdir(single_res_folder):
                test_path = os.path.join(single_res_folder, test_file)
                if os.path.isfile(test_path):
                    _test_file_prefix, extension = test_file.rsplit(".", 1)
                    if extension in ref.s21_file_extensions:
                        single_res_files_this_folder.append(test_path)
            if single_res_files_this_folder:
                # reset the plots folder
                temp_res_pipe = ResPipe(s21_path=single_res_files_this_folder[0])
                temp_res_pipe.prepare_res_pot_dir()
            # Start optional multiprocessing
            if ref.multiprocessing_threads is None:
                for single_res_file in single_res_files_this_folder:
                    single_res_pro(single_res_file=single_res_file, verbose=self.verbose, reprocess=reprocess,
                                   save_res_plots=save_res_plots)
            else:
                single_res_pro_args = zip(single_res_files_this_folder,
                                          [self.verbose] * len(single_res_files_this_folder),
                                          [reprocess] * len(single_res_files_this_folder),
                                          [save_res_plots] * len(single_res_files_this_folder))
                with Pool(ref.multiprocessing_threads) as p:
                    p.starmap(single_res_pro, single_res_pro_args)

    def calc_lamb(self, single_res_parent_dirs=None, lamb_plots=True):
        lamb_dirs = get_pro_res_dirs_from_sin_res(single_res_parent_dirs)
        if ref.multiprocessing_threads is None:
            [lamb_process(lamb_dir=lamb_dir, lamb_plots=lamb_plots) for lamb_dir in lamb_dirs]
        else:
            lamb_process_args = zip(lamb_dirs, [lamb_plots] * len(lamb_dirs))
            with Pool(ref.multiprocessing_threads) as p:
                p.starmap(lamb_process, lamb_process_args)

    def scans_to_seeds(self, pro_scan_paths=None, make_band_seeds=False, make_single_res_seeds=False):
        if pro_scan_paths is None:
            # by default, get all the windowbaselinesmoothedremoved files
            self.windowbaselinesmoothedremoved_scan_files = \
                get_pro_s21_scans(process_type="windowbaselinesmoothedremoved")
            windowbaselinesmoothedremoved_scan_files = self.windowbaselinesmoothedremoved_scan_files
        else:
            windowbaselinesmoothedremoved_scan_files = pro_scan_paths
        for scan_file in windowbaselinesmoothedremoved_scan_files:
            res_pipe = ResPipe(s21_path=scan_file, verbose=self.verbose)
            res_pipe.read()
            res_pipe.scan_to_band()
            res_pipe.report_scan_of_bands()
            if make_band_seeds:
                res_pipe.make_band_seeds()
            if make_single_res_seeds:
                res_pipe.make_res_seeds()

    def full_loop_scans(self, scan_paths=None, cosine_filter=False, window_pad_factor=3, fitter_pad_factor=6,
                        show_filter_plots=False,
                        do_interactive_plot=True, save_res_plots=True,
                        make_band_seeds=False, make_single_res_seeds=True):
        if scan_paths is None:
            self.raw_process_all_scans()
        else:
            [raw_process(path=scan_path) for scan_path in scan_paths]
        self.analyze_scans_resonators(scan_paths=phase_corrected_scan_files, cosine_filter=cosine_filter,
                                      window_pad_factor=window_pad_factor, fitter_pad_factor=fitter_pad_factor,
                                      show_filter_plots=show_filter_plots,
                                      skip_interactive_plot=not do_interactive_plot,
                                      save_res_plots=save_res_plots)
        self.scans_to_seeds(pro_scan_paths=self.windowbaselinesmoothedremoved_scan_files,
                            make_band_seeds=make_band_seeds, make_single_res_seeds=make_single_res_seeds)

    def full_loop_single_res(self, raw_res_dirs=None, do_raw=False, save_phase_plot=True,
                             pro_res_dirs=None, do_pro=False, save_res_plots=True, reprocess_res=True,
                             do_lamb=False, lamb_plots=True):

        if do_raw:
            self.get_band_or_res_from_dir(file_type="single_res", bands_or_res_dirs=raw_res_dirs)
            if ref.multiprocessing_threads is None:
                [raw_process(path=raw_single_res, save_phase_plot=save_phase_plot)
                 for raw_single_res in self.raw_single_res_files]
            else:
                raw_process_args = zip(self.raw_single_res_files,
                                       [save_phase_plot] * len(self.raw_single_res_files))
                with Pool(ref.multiprocessing_threads) as p:
                    p.starmap(raw_process, raw_process_args)
        if do_pro:
            self.analyze_single_res(single_res_parent_dirs=pro_res_dirs,
                                    save_res_plots=save_res_plots, reprocess=reprocess_res)
        if do_lamb:
            self.calc_lamb(single_res_parent_dirs=pro_res_dirs, lamb_plots=lamb_plots)
