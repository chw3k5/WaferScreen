import os
from ref import output_dirs
from waferscreen.analyze.s21_inductor import InductS21
from waferscreen.analyze.res_pipeline import ResPipe


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


def get_pro_s21_scans(process_type, extensions={"txt", "csv"}):
    pro_data_dirs = []
    [pro_data_dirs.extend(get_subdirs(rootdir=rootdir, matching_str="pro")) for rootdir in output_dirs]
    scan_dirs = []
    [scan_dirs.extend(get_all_subdirs(rootdir=pro_data_dir)) for pro_data_dir in pro_data_dirs]
    len_pro_type = len(process_type)
    scan_files = []
    for pro_data_folder in scan_dirs:
        for basename in os.listdir(pro_data_folder):
            if os.path.isfile(os.path.join(pro_data_folder, basename)):
                filename, extension = basename.rsplit(".", 1)
            if len_pro_type < len(filename):
                if filename[-len_pro_type:] == process_type and extension.lower() in extensions:
                    test_name = os.path.join(pro_data_folder, basename)
                    if os.path.isfile(test_name):
                        scan_files.append(test_name)
    return scan_files


class DataManager:
    def __init__(self, user_input_group_delay=None, verbose=True):
        self.user_input_group_delay = user_input_group_delay
        self.verbose = verbose
        self.raw_search_dirs = output_dirs
        self.raw_scan_files = []
        self.phase_corrected_scan_files = []
        self.windowbaselinesmoothedremoved_scan_files = []

    def from_scratch(self):
        self.raw_process_all()

    def raw_process_all(self):
        for rootdir in output_dirs:
            raw_dirs = get_subdirs(rootdir=rootdir, matching_str='raw')
            scans_dirs = []
            [scans_dirs.extend(get_subdirs(rootdir=raw_dir, matching_str='scans')) for raw_dir in raw_dirs]
            [self.raw_scan_files.extend([os.path.join(scans_dir, path) for path in os.listdir(scans_dir)])
             for scans_dir in scans_dirs]

        for raw_scan_path in self.raw_scan_files:
            self.raw_process(path=raw_scan_path)

    def raw_process(self, path):
        inducts21 = InductS21(path, verbose=self.verbose)
        inducts21.induct()
        inducts21.remove_group_delay(user_input_group_delay=self.user_input_group_delay)
        inducts21.write()
        if inducts21.metadata["export_type"] == "scan":
            self.phase_corrected_scan_files.append(inducts21.output_file)
        inducts21.plot()

    def find_scans_resonators(self):
        self.phase_corrected_scan_files = get_pro_s21_scans(process_type="phase")
        for scan_file in self.phase_corrected_scan_files:
            res_pipe = ResPipe(s21_path=scan_file, verbose=self.verbose)
            res_pipe.read()
            res_pipe.find_window(cosine_filter=False,
                                 window_pad_factor=3, fitter_pad_factor=6, show_filter_plots=False, debug_mode=True)
            res_pipe.analyze_resonators(save_res_plots=False)

    def load_scans_resonators(self):
        self.windowbaselinesmoothedremoved_scan_files = get_pro_s21_scans(process_type="windowbaselinesmoothedremoved")
        for scan_file in self.windowbaselinesmoothedremoved_scan_files:
            res_pipe = ResPipe(s21_path=scan_file, verbose=self.verbose)
            res_pipe.read()
            res_pipe.scan_to_band()
            res_pipe.report_scan_of_bands()
            res_pipe.make_res_seeds()
            # res_pipe.make_band_seeds()


if __name__ == "__main__":
    dm = DataManager(user_input_group_delay=None)
    # dm.raw_process_all()
    # dm.find_scans_resonators()
    dm.load_scans_resonators()
