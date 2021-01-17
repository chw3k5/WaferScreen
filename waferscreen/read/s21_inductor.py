import os
import time
import copy
import pathlib
import numpy as np
import datetime
from matplotlib import pyplot as plt
from waferscreen.plot.quick_plots import ls, len_ls
from waferscreen.tools.band_calc import find_band_edges, find_center_band
from waferscreen.read.table_read import num_format
from waferscreen.read.s21_metadata import MetaDataDict
from waferscreen.tools.rename import get_all_file_paths
from waferscreen.tools.band_calc import band_center_to_band_number
from ref import today_str, working_dir


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


def s21_subplot(ax, plot_data, x_data_str, y_data_str, y_label_str="", x_label_str="", leg_label_str="", title_str='',
                color="black", ls="solid", show_bands=False):
    legend_dict = {}
    ax.plot(plot_data[x_data_str], plot_data[y_data_str], color=color, ls=ls)
    ax.set_ylabel(y_label_str)
    ax.set_xlabel(x_label_str)
    legend_dict['leg_lines'] = [plt.Line2D(range(10), range(10), color=color, ls=ls)]
    legend_dict['leg_labels'] = [leg_label_str]
    if show_bands:
        center_band_str = plot_bands(ax, plot_data, legend_dict)
        if title_str == "":
            ax.title.set_text(center_band_str)
    else:
        ax.title.set_text(title_str)
    ax.legend(legend_dict['leg_lines'], legend_dict['leg_labels'], loc=1, numpoints=3, handlelength=5, fontsize=12)
    return


class InductS21:
    def __init__(self, path, verbose=True):
        self.path = path
        self.local_dirname, self.basename = os.path.split(self.path)
        self.parent_dirname, self.process_level_dirname = os.path.split(self.local_dirname)

        self.verbose = verbose

        self.group_delay_removed = False
        # Initialized variables used in methods
        self.freqs_GHz = None
        self.radians_per_second = None
        self.s21_complex_raw = None
        self.s21_complex_raw = None
        self.s21_mag_raw = None
        self.s21_phase_raw = None
        self.s21_phase_unwrapped = None
        self.s21_complex = None
        self.s21_mag = None
        self.s21_phase = None
        self.s21_phase_raw_unwrapped = None
        self.metadata = None
        self.group_delay = None
        self.phase_offset = None
        self.group_delay_slope = None
        self.group_delay_offset = None
        self.output_file = None
        self.plot_file = None
        self.freq_step = None
        self.max_delay = None

    def simple_induct(self, metadata_dict=None):
        self.remove_group_delay()
        if metadata_dict is not None:
            self.add_metadata(**metadata_dict)
        self.calc_metadata()
        self.write()
        self.plot()

    def induct(self):
        """
        open and read in 3 column S21 files.
        Converts to standard format of frequency in GHz,
        and S21 in as a real and imaginary column.
        """
        s21_dict, self.metadata = read_s21(path=self.path)
        self.freqs_GHz = s21_dict["freq_ghz"]
        real, imag = s21_dict["real"], s21_dict["imag"]
        self.radians_per_second = self.freqs_GHz * 1.0e9 * 2.0 * np.pi
        self.s21_complex_raw = real + (1j * imag)
        self.s21_complex = copy.deepcopy(self.s21_complex_raw)
        self.freq_step = np.mean(self.freqs_GHz[1:] - self.freqs_GHz[:-1]) * 1.0e9
        self.max_delay = 1.0 / (2.0 * np.sqrt(2.0) * self.freq_step)

    def get_mag_phase(self, and_raw=False):
        if self.s21_complex is None:
            self.induct()
        self.s21_mag, self.s21_phase = ri_to_magphase(r=self.s21_complex.real,
                                                      i=self.s21_complex.imag)
        self.s21_phase_unwrapped = np.unwrap(self.s21_phase, discont=np.pi)
        if and_raw:
            self.s21_mag_raw, self.s21_phase_raw = ri_to_magphase(r=self.s21_complex_raw.real,
                                                                  i=self.s21_complex_raw.imag)
            self.s21_phase_raw_unwrapped = np.unwrap(self.s21_phase_raw, discont=np.pi)
        return self.s21_mag, self.s21_phase

    def add_metadata(self, **kwargs):
        if kwargs is None:
            pass
        else:
            self.metadata.update(kwargs)

    def calc_metadata(self):

        # self.metadata['band'] = band_center_to_band_number(self.metadata["freq_center_GHz"])

        self.prepare_output_file()
        self.metadata['raw_path'] = self.metadata['path']

        self.metadata['plot_path'] = self.plot_file
        self.metadata['path'] = self.output_file

    def calc_group_delay(self):
        self.get_mag_phase()
        self.group_delay_slope, self.group_delay_offset = \
            np.polyfit(self.radians_per_second, self.s21_phase_unwrapped, deg=1)
        group_delay = self.group_delay_slope * -1.0
        if group_delay < self.max_delay:
            self.group_delay = group_delay
            self.phase_offset = ((self.group_delay_offset + np.pi) % (2.0 * np.pi)) - np.pi
        else:
            self.phase_offset = self.group_delay = float("nan")
        if self.verbose:
            print_str = F"{'%3.3f' % (self.group_delay * 1.0e9)} ns of cable delay, " + \
                        F"{'%3.3f' % (self.max_delay * 1.0e9)} ns is the maximum group delay measurable."

            print(print_str)

    def remove_group_delay(self, user_input_group_delay=None):
        if "group_delay_removed" not in self.metadata.keys():
            # get the calculate the group delay if no user input
            if user_input_group_delay is None:
                if self.group_delay is None:
                    self.calc_group_delay()
                if self.group_delay == float("nan"):
                    raise ValueError("Calculated group delay was greater than the allowed resolution.\n" +\
                                     "If the group delay " +
                                     "is known, input it thought the 'user_input_group_delay' variable.")
                group_delay = self.group_delay
            else:
                group_delay = user_input_group_delay
            # remove group delay
            phase_factors = np.exp(1j * (2.0 * np.pi * self.freqs_GHz * 1.0e9 * group_delay - self.phase_offset))
            self.s21_complex = self.s21_complex * phase_factors
            self.group_delay_removed = True
            self.metadata["group_delay_removed"] = F"utc:{datetime.datetime.utcnow()}"

    def prepare_output_filenames(self):
        output_dir = os.path.join(self.parent_dirname, "pro")
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        prefix, _extension = self.basename.rsplit(".", 1)
        self.output_file = os.path.join(output_dir, prefix + "_phase.csv")
        self.plot_file = os.path.join(output_dir, prefix + "_phase.pdf")

    def write(self):
        if not self.group_delay_removed:
            self.remove_group_delay()
        # write the output S21 file
        self.prepare_output_filenames()
        write_s21(output_file=self.output_file, freqs_ghz=self.freqs_GHz, 
                  s21_complex=self.s21_complex, metadata=self.metadata)

    def plot(self, save=True, show=False, show_bands=False):
        self.get_mag_phase(and_raw=True)
        # Organization and Math
        # frequency
        plot_data = {"freq_ghz": self.freqs_GHz, "rad_per_sec": self.radians_per_second}
        plot_data["min_freq"] = np.min(plot_data['freq_ghz'])
        plot_data["max_freq"] = np.max(plot_data['freq_ghz'])
        plot_data["center_freq"] = (plot_data["max_freq"] + plot_data["min_freq"]) / 2.0
        # raw
        plot_data["raw_real"], plot_data["raw_imag"] = self.s21_complex_raw.real, self.s21_complex_raw.imag
        plot_data["raw_mag"], plot_data['raw_phase'], plot_data[
            'raw_phase_unwrapped'] = self.s21_mag_raw, self.s21_phase_raw, self.s21_phase_raw_unwrapped
        plot_data["lin_fit"] = plot_data["rad_per_sec"] * self.group_delay_slope + self.group_delay_offset
        # processed
        plot_data["pro_real"], plot_data["pro_imag"] = self.s21_complex.real, self.s21_complex.imag
        plot_data["pro_mag"], plot_data['pro_phase'], plot_data[
            'pro_phase_unwrapped'] = self.s21_mag, self.s21_phase, self.s21_phase_unwrapped

        # Whole Plot
        x_inches = 15.0
        yx_ratio = 11.0 / 8.5
        fig = plt.figure(figsize=(x_inches, x_inches * yx_ratio))
        fig.suptitle('Data Inductor  ' + today_str, size='xx-large')
        ax_mag = fig.add_subplot(311)
        ax_raw_phase = fig.add_subplot(323)
        ax_raw_ri = fig.add_subplot(324)
        ax_pro_phase = fig.add_subplot(325)
        ax_pro_ri = fig.add_subplot(326)

        # Magnitude
        legend_dict = {}
        mag_x_data_str = "freq_ghz"
        mag_x_label_str = "Frequency (GHz)"
        mag_y_label_str = "Magnitude S21 (dBm)"
        mag_title_str = "S21 Magnitude"
        mag_ls = "solid"
        ax_mag.plot(plot_data[mag_x_data_str], plot_data["raw_mag"], color="black", ls=mag_ls, linewidth=3)
        legend_dict['leg_lines'] = [plt.Line2D(range(10), range(10), color="black", ls=mag_ls, linewidth=3)]
        legend_dict['leg_labels'] = ["Raw"]
        ax_mag.plot(plot_data[mag_x_data_str], plot_data["raw_mag"], color="chartreuse", ls=mag_ls, linewidth=1)
        legend_dict['leg_lines'].append(plt.Line2D(range(10), range(10), color="chartreuse", ls=mag_ls, linewidth=1))
        legend_dict['leg_labels'].append("Processed")

        ax_mag.set_ylabel(mag_y_label_str)
        ax_mag.set_xlabel(mag_x_label_str)

        if show_bands:
            center_band_str = plot_bands(ax_mag, plot_data, legend_dict)
            if mag_title_str == "":
                ax_mag.title.set_text(center_band_str)
        else:
            ax_mag.title.set_text(mag_title_str)
        ax_mag.legend(legend_dict['leg_lines'], legend_dict['leg_labels'],
                      loc=1, numpoints=3, handlelength=5, fontsize=12)

        # Raw Phase
        legend_dict = {}
        raw_phase_x_data_str = "rad_per_sec"
        raw_phase_x_label_str = "Frequency (radians / second)"
        raw_phase_y_label_str = "Phase (radians)"
        raw_phase_title_str = "Raw Unwrapped S21 Phase"
        ax_raw_phase.plot(plot_data[raw_phase_x_data_str], plot_data['raw_phase_unwrapped'],
                          color="firebrick", ls="solid", linewidth=6)
        legend_dict['leg_lines'] = [plt.Line2D(range(10), range(10), color="firebrick", ls="solid", linewidth=6)]
        legend_dict['leg_labels'] = ["Raw Unwrapped S21 Phase"]

        ax_raw_phase.plot(plot_data[raw_phase_x_data_str], plot_data["lin_fit"],
                          color="black", ls="dashed", linewidth=11)
        legend_dict['leg_lines'].append(plt.Line2D(range(10), range(10), color="black", ls="dashed", linewidth=11))
        legend_dict['leg_labels'].append(F"Fit group delay {'%2.2f' % (self.group_delay * 1.0e9)} ns,  offset {'%2.2f' % self.phase_offset} radians")

        ax_raw_phase.set_ylabel(raw_phase_y_label_str)
        ax_raw_phase.set_xlabel(raw_phase_x_label_str)
        ax_raw_phase.legend(legend_dict['leg_lines'], legend_dict['leg_labels'],
                            loc=1, numpoints=3, handlelength=5, fontsize=12)

        # Raw Real Imaginary Plot
        s21_subplot(ax_raw_ri, plot_data,
                    x_data_str="raw_real", y_data_str='raw_imag',
                    x_label_str="Real S21", y_label_str="Imaginary S21",
                    leg_label_str="Raw Real-Imag S21", title_str="Raw Real(freq) vs Imaginary(freq) S21",
                    color="firebrick", ls="solid", show_bands=False)

        # Processed Phase residuals  Plot
        s21_subplot(ax_pro_phase, plot_data,
                    x_data_str="rad_per_sec", y_data_str='pro_phase_unwrapped',
                    x_label_str="Frequency (radians / second)", y_label_str="Phase (radians)",
                    leg_label_str="Phase S21", title_str="Processed S21 Phase Residuals",
                    color="dodgerblue", ls="solid", show_bands=False)

        # Processed Real Imaginary Plot
        s21_subplot(ax_pro_ri, plot_data,
                    x_data_str="pro_real", y_data_str='pro_imag',
                    x_label_str="Real S21", y_label_str="Imaginary S21",
                    leg_label_str="Real-Imag S21", title_str="Processed Real(freq) vs Imaginary(freq) S21",
                    color="dodgerblue", ls="solid", show_bands=False)

        # Display
        if save:
            if self.output_file is None:
                self.prepare_output_filenames()
            plt.draw()
            plt.savefig(self.plot_file)
            print("Saved Plot to:", self.plot_file)
        if show:
            plt.show()
        plt.clf()
        return


def induct_princeton(verbose=True):
    base = os.path.join(working_dir, "princeton", "SMBK_wafer8")
    metadata_path = os.path.join(base, "metadata.txt")
    m21 = S21MetadataPrinceton()
    m21.meta_from_file(metadata_path)
    paths = get_all_file_paths(base)
    s21by_path = {}
    for path in paths:
        _, extension = path.rsplit('.', 1)
        if extension.lower() == "csv":
            this_loop_s21 = InductS21(path=path, columns=("freq_Hz", 'real', "imag"), verbose=verbose)
            this_loop_s21.simple_induct(metadata_dict=m21.file_to_meta[path])
            s21by_path[path] = this_loop_s21
    return s21by_path


def induct_dirs(search_dirs=None, columns=None, verbose=True):
    s21by_path = {}
    if search_dirs is None:
        search_dirs = [working_dir]
    if columns is None:
        columns = ("freq_Hz", 'real', "imag")
    for path in crawl_raw_s21(search_dirs=search_dirs):
        s21by_path[path] = InductS21(path=path, columns=columns, verbose=verbose)
        s21by_path[path].simple_induct(metadata_dict=None)
    return s21by_path



if __name__ == "__main__":
    s21by_path = induct_all()
    for path in s21by_path.keys():
        s21by_path[path].plot()

