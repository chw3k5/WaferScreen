from pathlib import Path
import numpy as np
from typing import NamedTuple
from ref import pro_data_dir
from waferscreen.read.table_read import num_format


def crawl_s21():
    return [str(path) for path in Path(pro_data_dir).rglob('*s21.csv')]


def read_pro_s21(path):
    with open(path, "r") as f:
        raw_lines = f.readlines()
    freq_GHz = []
    s21_complex = []
    meta_data = {}
    header = ["freq_ghz", "real", "imag"]
    for raw_line in raw_lines:
        stripped_raw_line = raw_line.strip()
        if stripped_raw_line[0] == "%":
            meta_data_line = stripped_raw_line[1:].lstrip()
            if meta_data_line != "":
                data_type, data_info = meta_data_line.split(":", 1)
                data_type = data_type.rstrip().lower()
                if data_type == "meta_data":
                    for key_value_pair in list(data_info.split("|")):
                        key, value = key_value_pair.split(",")
                        meta_data[key.strip()] = num_format(value.strip())
                elif data_type == 'header':
                    match_header = [column.strip() for column in list(data_info.split(","))]
                    if match_header != header:
                        raise KeyError("Unexpected Header")
        elif stripped_raw_line != '':
            freq_str, real_str, imag_str = stripped_raw_line.split(",")
            freq_GHz.append(num_format(freq_str.strip()))
            real = num_format(real_str.strip())
            imag = num_format(imag_str.strip())
            s21_complex.append(np.complex(real, imag))
    return np.array(freq_GHz), np.array(s21_complex), meta_data


class ProS21(NamedTuple):
    freq_Ghz: np.array
    s21_complex: np.array
    meta_data: dict


if __name__ == "__main__":
    s21_files = crawl_s21()
    freq, s21_complex, meta_data = read_pro_s21(path=s21_files[0])
