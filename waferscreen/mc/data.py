import os
import numpy as np
from typing import NamedTuple, Optional
from ref import output_dirs
from waferscreen.analyze.s21_inductor import InductS21
from waferscreen.analyze.res_pipeline import ResPipe


def read_res_params(path):
    # open resonant frequencies file
    with open(path, 'r') as f:
        lines = f.readlines()
    header = lines[0].strip().split(",")
    res_params = []
    for line in lines[1:]:
        datavec = line.split(",")
        res_params.append(ResParams(**{column_name: float(value) for column_name, value in zip(header, datavec)}))
    return res_params


primary_res_params = ["Amag", "Aphase", "Aslope", "tau", "f0", "Qi", "Qc", "Zratio"]
res_params_header = ""
for param_type in primary_res_params:
    res_params_header += param_type + "," + param_type + "_error,"
res_params_header = res_params_header[:-1]


class ResParams(NamedTuple):
    Amag: float
    Aphase: float
    Aslope: float
    tau: float
    f0: float
    Qi: float
    Qc: float
    Zratio: float
    Amag_error: Optional[float] = None
    Aphase_error: Optional[float] = None
    Aslope_error: Optional[float] = None
    tau_error: Optional[float] = None
    f0_error: Optional[float] = None
    Qi_error: Optional[float] = None
    Qc_error: Optional[float] = None
    Zratio_error: Optional[float] = None

    def __str__(self):
        output_string = ""
        for attr in primary_res_params:
            error_value = str(self.__getattribute__(attr + "_error"))
            if error_value is None:
                error_str = ""
            else:
                error_str = str(error_value)
            output_string += str(self.__getattribute__(attr)) + "," + error_str + ","
        return output_string[:-1]


class ProS21(NamedTuple):
    freq_Ghz: np.array
    s21_complex: np.array
    meta_data: dict


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
