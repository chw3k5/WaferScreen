import numpy as np
import os
import matplotlib.pyplot as plt
from waferscreen.analyze.s21_metadata import MetaDataDict
from waferscreen.analyze.table_read import num_format
from waferscreen.tools.band_calc import find_band_edges, find_center_band
from waferscreen.plot.quick_plots import ls, len_ls

s21_header = "# Header:freq_ghz,real,imag"


def write_s21(output_file, freqs_ghz, s21_complex, metadata):
    with open(output_file, 'w') as f:
        f.write(F"{metadata}\n")
        f.write(F"{s21_header}\n")
        for freq, s21_value in list(zip(freqs_ghz, s21_complex)):
            real = s21_value.real
            imag = s21_value.imag
            f.write(F"{freq},{real},{imag}\n")


def read_s21(path):
    with open(path, "r") as f:
        raw_lines = f.readlines()
    metadata = MetaDataDict()
    header = ["freq_ghz", "real", "imag"]
    # get the metadata and header
    line_index = 0
    while raw_lines[line_index][0] == "#":
        try:
            context_type, context_data = raw_lines[line_index].replace("#", "", 1).lstrip().split(":", 1)
        except ValueError:
            pass
        else:
            context_type = context_type.rstrip().lower()
            if context_type == "header":
                header = [column_name.strip().lower() for column_name in context_data.split(",")]
            elif context_type == "metadata":
                for key_value_pair in context_data.split("|"):
                    raw_key, raw_value = key_value_pair.split(",")
                    metadata[raw_key] = num_format(raw_value.strip())
        line_index += 1
    else:
        s21_data = raw_lines[line_index:]
    s21_assembly_dict = {column_name: [] for column_name in header}
    for raw_s21_line in s21_data:
        [s21_assembly_dict[column_name].append(float(raw_cell_value))
         for column_name, raw_cell_value in zip(header, raw_s21_line.split(","))]
    return {column_name: np.array(s21_assembly_dict[column_name]) for column_name in s21_assembly_dict.keys()}, metadata


def dirname_create(output_basedir, location, wafer, date_str, sweep_type="scan", res_id=None):
    dir_build_list = [str(location), str(wafer), str(date_str)]
    if sweep_type == "scan":
        dir_build_list.append(str(sweep_type))
    else:
        dir_build_list.append(str(res_id))
    path_str = output_basedir
    for dir_name in dir_build_list:
        path_str = os.path.join(path_str, dir_name)
        if not os.path.isdir(path_str):
            os.mkdir(path_str)
    return path_str


def ri_to_magphase(r, i):
    s21_mag = 20 * np.log10(np.sqrt((r ** 2.0) + (i ** 2.0)))
    s21_phase = np.arctan2(i, r)
    return s21_mag, s21_phase


def magphase_to_realimag(mag, phase):
    linear_mag = 10.0**(mag / 20)
    s21_complex = linear_mag * np.exp(1j * phase)
    return np.real(s21_complex), np.imag(s21_complex)


def plot_bands(ax, plot_data, legend_dict):
    min_freq, max_freq = plot_data["min_freq"], plot_data["max_freq"]
    ymin, ymax = ax.get_ylim()
    counter = 1
    color = "black"
    for freq, label_str in find_band_edges(min_freq=min_freq, max_freq=max_freq):
        line_style = ls[counter % len_ls]
        ax.plot([freq, freq], [ymin, ymax], color=color, ls=line_style)
        legend_dict['leg_lines'].append(plt.Line2D(range(10), range(10), color=color, ls=line_style))
        legend_dict['leg_labels'].append(label_str)
        counter += 1
    center_band_freq, center_band_str = find_center_band(center_GHz=plot_data["center_freq"])
    return center_band_str
