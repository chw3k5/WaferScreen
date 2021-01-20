import os
import numpy as np
from typing import NamedTuple, Optional
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


def get_pro_s21(process_type, export_type="scan", extensions={"txt", "csv"}):
    len_pro_type = len(process_type)
    len_export_type = len(export_type)
    pro_data_folders = []
    [pro_data_folders.extend(get_subdirs(rootdir=rootdir, matching_str='pro')) for rootdir in output_dirs]
    files_to_return = []
    for pro_data_folder in pro_data_folders:
        for basename in os.listdir(pro_data_folder):
            filename, extension = basename.rsplit(".", 1)
            if max(len_pro_type, len_export_type) < len(filename):
                if filename[-len_pro_type:] == process_type and filename[:len_export_type] == export_type and \
                        extension.lower() in extensions:
                    files_to_return.append(os.path.join(pro_data_folder, basename))
    return files_to_return


class DataManager:
    def __init__(self, user_input_group_delay=None, verbose=True):
        self.user_input_group_delay = user_input_group_delay
        self.verbose = verbose
        self.raw_search_dirs = output_dirs
        self.raw_scan_files = []
        self.phase_corrected_scan_files = []

    def from_scratch(self):
        self.raw_process_all()

    def raw_process_all(self):
        for rootdir in output_dirs:
            raw_dirs = get_subdirs(rootdir=rootdir, matching_str='raw')
            for raw_dir in raw_dirs:
                self.raw_scan_files.extend([os.path.join(raw_dir, path) for path in os.listdir(raw_dir)
                                            if path[:4] == 'scan'])
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
        self.phase_corrected_scan_files = get_pro_s21(process_type="phase", export_type="scan")
        for scan_file in self.phase_corrected_scan_files:
            res_pipe = ResPipe(s21_path=scan_file, verbose=self.verbose)
            res_pipe.read()
            res_pipe.baseline_subtraction()


if __name__ == "__main__":
    dm = DataManager(user_input_group_delay=None)
    # dm.raw_process_all()
    dm.find_scans_resonators()
