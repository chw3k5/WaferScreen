from pathlib import Path
import numpy as np
from typing import NamedTuple, Optional
from waferscreen.read.s21_inductor import read_s21
from waferscreen.read.table_read import num_format
from waferscreen.read.s21_metadata import MetaDataDict



def crawl_raw(pro_data_dir):
    return [str(path) for path in Path(pro_data_dir).rglob('*s21.csv')]


def crawl_s21(pro_data_dir):
    return [str(path) for path in Path(pro_data_dir).rglob('*s21.csv')]


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


if __name__ == "__main__":
    s21_files = crawl_s21()
    freq, s21_complex, meta_data = read_s21(path=s21_files[0])
