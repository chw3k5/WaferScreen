import os
import ref
from waferscreen.mc.s21_inductor import InductS21
from waferscreen.mc.res_pipeline import ResPipe
from waferscreen.analyze.s21_io import input_to_output_filename


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


def get_pro_s21_scans(process_type):
    pro_data_dirs = []
    [pro_data_dirs.extend(get_subdirs(rootdir=rootdir, matching_str="pro")) for rootdir in ref.output_dirs]
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
            self.raw_process(path=raw_scan_path)

    def raw_process_all_bands(self):
        self.get_all_single_res_or_bands_files(file_type="bands")
        for raw_band_path in self.raw_bands_files:
            _dirname, basename = os.path.split(raw_band_path)
            basename_prefix, _extension = basename.rsplit(".", 1)
            if basename_prefix != "seed":
                self.raw_process(path=raw_band_path)

    def raw_process_all_single_res(self):
        self.get_all_single_res_or_bands_files(file_type="single_res")
        for raw_single_res_path in self.raw_single_res_files:
            _dirname, basename = os.path.split(raw_single_res_path)
            basename_prefix, _extension = basename.rsplit(".", 1)
            if basename_prefix != "seed":
                self.raw_process(path=raw_single_res_path)

    def raw_process(self, path):
        inducts21 = InductS21(path, verbose=self.verbose)
        inducts21.induct()
        inducts21.remove_group_delay(user_input_group_delay=self.user_input_group_delay)
        inducts21.write()
        if inducts21.metadata["export_type"] == "scan":
            self.phase_corrected_scan_files.append(inducts21.output_file)
        inducts21.plot()

    def analyze_scans_resonators(self, scan_paths=None, cosine_filter=False,
                                 window_pad_factor=3, fitter_pad_factor=6,
                                 show_filter_plots=False, skip_interactive_plot=False,
                                 save_res_plots=False):
        if scan_paths is None:
            # by default, get all the scans files
            self.phase_corrected_scan_files = get_pro_s21_scans(process_type="phase")
            phase_corrected_scan_files = self.phase_corrected_scan_files
        else:
            phase_corrected_scan_files = scan_paths
        for scan_file in phase_corrected_scan_files:
            res_pipe = ResPipe(s21_path=scan_file, verbose=self.verbose)
            res_pipe.read()
            res_pipe.find_window(cosine_filter=cosine_filter,
                                 window_pad_factor=window_pad_factor, fitter_pad_factor=fitter_pad_factor,
                                 show_filter_plots=show_filter_plots,
                                 debug_mode=skip_interactive_plot)
            res_pipe.analyze_resonators(save_res_plots=save_res_plots)
            data_filename, plot_filename = input_to_output_filename(processing_steps=["windowBaselineSmoothedRemoved"],
                                                                    input_path=scan_file)
            self.windowbaselinesmoothedremoved_scan_files.append(data_filename)

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
                        skip_interactive_plot=False, save_res_plots=False,
                        make_band_seeds=False, make_single_res_seeds=False):
        if scan_paths is None:
            self.raw_process_all_scans()
        else:
            [self.raw_process(path=scan_path) for scan_path in scan_paths]
        self.analyze_scans_resonators(scan_paths=self.phase_corrected_scan_files, cosine_filter=cosine_filter,
                                      window_pad_factor=window_pad_factor, fitter_pad_factor=fitter_pad_factor,
                                      show_filter_plots=show_filter_plots, skip_interactive_plot=skip_interactive_plot,
                                      save_res_plots=save_res_plots)
        self.scans_to_seeds(pro_scan_paths=self.windowbaselinesmoothedremoved_scan_files,
                            make_band_seeds=make_band_seeds, make_single_res_seeds=make_single_res_seeds)

    def full_loop_single_res(self, res_dirs=None):
        self.get_band_or_res_from_dir(file_type="single_res", bands_or_res_dirs=res_dirs)
        [self.raw_process(path=raw_single_res) for raw_single_res in self.raw_single_res_files]

