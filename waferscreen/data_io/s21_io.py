import os
import numpy as np
import matplotlib.pyplot as plt
from waferscreen.data_io.s21_metadata import MetaDataDict, num_format
from waferscreen.data_io.res_io import res_params_header, ResParams
from waferscreen.data_io.lamb_io import lambda_header, LambdaParams
from waferscreen.tools.band_calc import find_band_edges, find_center_band
from waferscreen.plot.quick_plots import ls, len_ls

s21_header = "# Header:freq_ghz,real,imag"
default_header = ["freq_ghz", "real", "imag"]


def write_s21(output_file, freqs_ghz=None, s21_complex=None, metadata=None,
              fitted_resonators_parameters=None, lamb_params_fits=None):
    with open(output_file, 'w') as f:
        if metadata is not None:
            f.write(F"{metadata}\n")
        if fitted_resonators_parameters is not None:
            f.write(F"{res_params_header}\n")
            for res_param in fitted_resonators_parameters:
                f.write(F"{res_param}\n")
        if lamb_params_fits is not None:
            f.write(F"{lambda_header}\n")
            for lamb_params_fit in lamb_params_fits:
                f.write(F"{lamb_params_fit}\n")
        if freqs_ghz is not None and s21_complex is not None:
            f.write(F"{s21_header}\n")
            for freq, s21_value in list(zip(freqs_ghz, s21_complex)):
                real = s21_value.real
                imag = s21_value.imag
                f.write(F"{freq},{real},{imag}\n")


def read_s21(path, return_res_params=False, return_lamb_params=False):
    with open(path, "r") as f:
        raw_lines = f.readlines()
    metadata = MetaDataDict()
    header = default_header  # this is only used if a the expected header is absent
    # get the metadata and header and other ancillary data types
    line_index = 0
    res_fits_trigger = False
    res_fits_header = None
    res_fits = None
    lamb_fits_trigger = False
    lamb_fits_header = None
    lamb_fits = None
    found_s21_header_data = False
    for line_index, raw_line in list(enumerate(raw_lines)):
        if raw_lines[line_index][0] == "#":
            try:
                context_type, context_data = raw_lines[line_index].replace("#", "", 1).lstrip().split(":", 1)
            except ValueError:
                pass
            else:
                context_type = context_type.rstrip().lower()
                if context_type == "header":
                    header = [column_name.strip().lower() for column_name in context_data.split(",")]
                    found_s21_header_data = True
                    # the rest of the data is columns of S21 data
                    break
                elif context_type == "metadata":
                    for key_value_pair in context_data.split(","):
                        raw_key, raw_value = key_value_pair.split("|")
                        metadata[raw_key] = num_format(raw_value.strip())
                    res_fits_trigger = False
                elif context_type == "resfits":
                    res_fits_trigger = True
                    lamb_fits_trigger = False
                    res_fits = []
                    res_fits_header = [column_name.strip().lower() for column_name in context_data.split(",")]
                elif context_type == "lambda":
                    lamb_fits_trigger = True
                    res_fits_trigger = False
                    lamb_fits = []
                    lamb_fits_header = [column_name.strip().lower() for column_name in context_data.split(",")]
        elif res_fits_trigger:
            res_fits_dict = {column_name: num_format(row_value)
                             for column_name, row_value in zip(res_fits_header, raw_line.split(","))}
            res_fits.append(ResParams(**res_fits_dict))
        elif lamb_fits_trigger:
            lamb_fits_dict = {column_name: num_format(row_value)
                              for column_name, row_value in zip(lamb_fits_header, raw_line.split(","))}
            lamb_fits.append(LambdaParams(**lamb_fits_dict))
    # Process the S21 data
    if found_s21_header_data:
        s21_data = raw_lines[line_index + 1:]
        s21_assembly_dict = {column_name: [] for column_name in header}
        for raw_s21_line in s21_data:
            [s21_assembly_dict[column_name].append(float(raw_cell_value))
             for column_name, raw_cell_value in zip(header, raw_s21_line.split(","))]
        formatted_s21_dict = {column_name: np.array(s21_assembly_dict[column_name])
                              for column_name in s21_assembly_dict.keys()}
    else:
        formatted_s21_dict = None
    if return_res_params and return_lamb_params:
        return formatted_s21_dict, metadata, res_fits, lamb_fits
    elif return_res_params:
        return formatted_s21_dict, metadata, res_fits
    elif return_lamb_params:
        return formatted_s21_dict, metadata, lamb_fits
    else:
        return formatted_s21_dict, metadata


def dirname_create(output_basedir, location, wafer, date_str, is_raw=True, sweep_type="scan", res_id=None):
    dir_build_list = [str(location), str(wafer), str(date_str)]
    if is_raw:
        dir_build_list.append("raw")
    else:
        dir_build_list.append("pro")
    if sweep_type == "scan":
        dir_build_list.append("scans")
    else:
        dir_build_list.append(str(res_id))
    path_str = output_basedir
    for dir_name in dir_build_list:
        path_str = os.path.join(path_str, dir_name)
        if not os.path.isdir(path_str):
            os.mkdir(path_str)
    return path_str


def generate_output_filename(processing_steps, basename_prefix, dirname, file_extension):
    output_prefix = str(basename_prefix)
    for process_step in processing_steps:
        output_prefix += F"_{process_step.lower().strip()}"
    outputfile_basename_prefix = os.path.join(dirname, output_prefix)
    plot_filename = outputfile_basename_prefix + ".pdf"
    data_filename = outputfile_basename_prefix + "." + file_extension
    return data_filename, plot_filename


def parse_output_file(path):
    dirname, basename = os.path.split(path)
    basename_prefix, extension = basename.rsplit(".", 1)
    return dirname, basename_prefix, extension


def input_to_output_filename(processing_steps, input_path):
    dirname, basename_prefix, extension = parse_output_file(path=input_path)
    return generate_output_filename(processing_steps=processing_steps, basename_prefix=basename_prefix,
                                    dirname=dirname, file_extension=extension)


def ri_to_magphase(r, i):
    s21_mag = 20.0 * np.log10(np.sqrt((r ** 2.0) + (i ** 2.0)))
    s21_phase = np.arctan2(i, r)
    return s21_mag, s21_phase


def magphase_to_realimag(mag, phase):
    linear_mag = 10.0**(mag / 20.0)
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


def mx_plus_b(x, m, b):
    return (x * m) + b
