import os
import time
import copy
import numpy as np
from matplotlib import pyplot as plt
from waferscreen.plot.quick_plots import ls, len_ls
from waferscreen.tools.band_calc import find_band_edges, find_center_band
from waferscreen.read.prodata import read_pro_s21
from scipy.signal import savgol_filter
from waferscreen.read.table_read import num_format
from waferscreen.tools.rename import get_all_file_paths
from waferscreen.tools.band_calc import band_center_to_band_number
from ref import pro_data_dir, raw_data_dir, today_str


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


def jakes_prep(freqs, sdata, group_delay_ns, edge_search_depth, remove_baseline_ripple,
               baseline_scale_kHz, smoothing_scale_kHz, baseline_order, smoothing_order, verbose=False):
    # now remove given group delay and make sure sdata is array
    phase_factors = np.exp(-1j * 2.0 * np.pi * freqs * group_delay_ns)  # e^(-j*w*t)
    sdata = np.array(sdata) / phase_factors

    if verbose:
        print("Removed Group Delay")

    # figure out complex gain and gain slope
    ave_left_gain = 0
    ave_right_gain = 0
    for j in range(0, edge_search_depth):
        ave_left_gain = ave_left_gain + sdata[j] / edge_search_depth
        ave_right_gain = ave_right_gain + sdata[len(sdata) - 1 - j] / edge_search_depth
    left_freq = freqs[int(edge_search_depth / 2.0)]
    right_freq = freqs[len(freqs) - 1 - int(edge_search_depth / 2.0)]
    gain_slope = (ave_right_gain - ave_left_gain) / (right_freq - left_freq)
    if verbose:
        # calculate extra group delay and abs gain slope removed for printing out purposes
        left_phase = np.arctan2(np.imag(ave_left_gain), np.real(ave_left_gain))
        right_phase = np.arctan2(np.imag(ave_right_gain), np.real(ave_right_gain))
        excess_tau = (left_phase - right_phase) / (2.0 * np.pi * (right_freq - left_freq))
        abs_gain = np.absolute(0.5 * ave_right_gain + 0.5 * ave_left_gain)
        abs_gain_slope = (np.absolute(ave_right_gain) - np.absolute(ave_left_gain)) / (right_freq - left_freq)
        print("Removing an excess group delay of " + str(excess_tau) + "ns from data")
        print("Removing a gain of " + str(abs_gain) + " and slope of " + str(abs_gain_slope) + "/GHz from data")
    gains = ave_left_gain + (freqs - left_freq) * gain_slope
    sdata = sdata / gains

    if verbose:
        print("Removed Group Delay and Gain")
    # remove baseline ripple if desired
    if remove_baseline_ripple:
        freq_spacing = (freqs[1] - freqs[0]) * 1.0e6  # GHz -> kHz
        baseline_scale = int(round(baseline_scale_kHz / freq_spacing))
        if baseline_scale % 2 == 0:  # if even
            baseline_scale = baseline_scale + 1  # make it odd
        if verbose:
            print("Freq Spacing is " + str(freq_spacing) + "kHz")
            print("Requested baseline smoothing scale is " + str(baseline_scale_kHz) + "kHz")
            print("Number of points to smooth over is " + str(baseline_scale))
        # smooth s21 trace in both real and imaginary to do peak finding
        baseline_real = savgol_filter(np.real(sdata), baseline_scale, baseline_order)
        baseline_imag = savgol_filter(np.imag(sdata), baseline_scale, baseline_order)
        baseline = np.array(baseline_real + 1j * baseline_imag)
        pre_baseline_removal_sdata = np.copy(sdata)
        sdata = sdata / baseline

    # figure out freq spacing, convert smoothing_scale_kHz to smoothing_scale (must be an odd number)
    freq_spacing = (freqs[1] - freqs[0]) * 1e6  # GHz -> kHz
    smoothing_scale = int(round(smoothing_scale_kHz / freq_spacing))
    if smoothing_scale % 2 == 0:  # if even
        smoothing_scale = smoothing_scale + 1  # make it odd
    if smoothing_scale >= smoothing_order:
        smoothing_order = smoothing_scale - 1
    if verbose:
        print("Freq Spacing is " + str(freq_spacing) + "kHz")
        print("Requested smoothing scale is " + str(smoothing_scale_kHz) + "kHz")
        print("Number of points to smooth over is " + str(smoothing_scale))
    # smooth s21 trace in both real and imaginary to do peak finding
    sdata_smooth_real = savgol_filter(np.real(sdata), smoothing_scale, smoothing_order)
    sdata_smooth_imag = savgol_filter(np.imag(sdata), smoothing_scale, smoothing_order)
    sdata_smooth = np.array(sdata_smooth_real + 1j * sdata_smooth_imag)


class MetaS21:
    def __init__(self):
        self.file_to_meta = {}
        self.paths = []

    def meta_from_file(self, path):
        with open(path, mode='r') as f:
            raw_file = f.readlines()
        for raw_line in raw_file:
            meta_data_this_line = {}
            key_value_phrases = raw_line.split("|")
            for key_value_phrase in key_value_phrases:
                key_str, value_str = key_value_phrase.split(",")
                meta_data_this_line[key_str.strip()] = num_format(value_str.strip())
            else:
                if "path" in meta_data_this_line.keys():
                    local_test_path = os.path.join(os.path.dirname(path), meta_data_this_line["path"])
                    if os.path.isfile(local_test_path):
                        meta_data_this_line["path"] = local_test_path
                    self.file_to_meta[meta_data_this_line["path"]] = meta_data_this_line
                else:
                    raise KeyError("No path. All S21 meta data requires a unique path to the S21 file.")
        self.paths.append(path)


class InductS21:
    def __init__(self, path, columns=None, verbose=True):
        self.path = path
        self.verbose = verbose
        if columns is None:
            self.columns = ("freq_Hz", 'real', "imag")
        else:
            self.columns = columns
        _, self.freq_unit = self.columns[0].lower().split("_")
        if self.freq_unit == "ghz":
            self.convert_to_GHz = 1.0
        elif self.freq_unit == "mhz":
            self.convert_to_GHz = 1.0e-3
        elif self.freq_unit == "khz":
            self.convert_to_GHz = 1.0e-6
        elif self.freq_unit == "hz":
            self.convert_to_GHz = 1.0e-9
        elif self.freq_unit == "thz":
            self.convert_to_GHz = 1.0e+3
        else:
            raise KeyError("Frequency unit: " + str(self.freq_unit) + " not recognized.")

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
        self.meta_data = {}
        self.group_delay = None
        self.phase_offset = None
        self.group_delay_slope = None
        self.group_delay_offset = None
        self.output_file = None
        self.freq_step = None
        self.max_delay = None

    def induct(self):
        """
        open and read in 3 column S21 files.
        Converts to standard format of frequency in GHz,
        and S21 in as a real and imaginary column.
        """
        with open(self.path, 'r') as f:
            raw_data = f.readlines()

        split_data = [striped_line.split(",") for striped_line in [raw_line.strip() for raw_line in raw_data]
                      if striped_line != ""]
        data = [[num_format(single_number) for single_number in data_row] for data_row in split_data]
        # find the first row with a number the expected 2 column format
        for data_index, data_line in list(enumerate(data)):
            try:
                freq, s21_a, s21_b = data_line
                if all((isinstance(freq, float), isinstance(s21_a, float), isinstance(s21_b, float))):
                    s21_start_index = data_index
                    break
            except ValueError:
                pass
        else:
            raise KeyError("The file:" + str(self.path) + " does not have the S21 data in the expected 3 column format")
        s21_data = data[s21_start_index:]
        data_matrix = np.array(s21_data)
        self.freqs_GHz = data_matrix[:, 0] * self.convert_to_GHz
        self.radians_per_second = self.freqs_GHz * 1.0e9 * 2.0 * np.pi
        real = data_matrix[:, 1]
        imag = data_matrix[:, 2]
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

    def add_meta_data(self, **kwargs):
        if kwargs is None:
            pass
        else:
            self.meta_data.update(kwargs)

    def calc_meta_data(self):
        if self.freqs_GHz is not None:
            self.meta_data["freq_min_GHz"] = np.min(self.freqs_GHz)
            self.meta_data["freq_max_GHz"] = np.max(self.freqs_GHz)
            self.meta_data["freq_center_GHz"] = (self.meta_data["freq_max_GHz"] + self.meta_data["freq_min_GHz"]) / 2.0
            self.meta_data["freq_span_GHz"] = self.meta_data["freq_max_GHz"] - self.meta_data["freq_min_GHz"]
            self.meta_data["freq_step"] = self.freq_step
            self.meta_data['band'] = band_center_to_band_number(self.meta_data["freq_center_GHz"])
        if "time" in self.meta_data.keys():
            self.meta_data["datetime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.meta_data["time"]))
        self.prepare_output_file()
        self.meta_data['raw_path'] = self.meta_data['path']
        self.meta_data['path'] = self.output_file

    def calc_group_delay(self):
        self.get_mag_phase()
        self.group_delay_slope, self.group_delay_offset = np.polyfit(self.radians_per_second, self.s21_phase_unwrapped, deg=1)
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
        # get the calculate the group delay if no user input
        if user_input_group_delay is None:
            if self.group_delay is None:
                self.calc_group_delay()
            if self.group_delay == float("nan"):
                raise ValueError("Calculated group delay was greater than the allowed resolution. If the group delay " +
                                 "is known, input it thought the 'user_input_group_delay' variable.")
            group_delay = self.group_delay
        else:
            group_delay = user_input_group_delay
        # remove group delay
        phase_factors = np.exp(1j * (2.0 * np.pi * self.freqs_GHz * 1.0e9 * group_delay - self.phase_offset))
        self.s21_complex = self.s21_complex * phase_factors
        self.group_delay_removed = True

    def prepare_output_file(self):
        # output the file in the standard directory structure
        if "location" in self.meta_data.keys():
            location = self.meta_data["location"]
        else:
            location = "null"
        if "wafer" in self.meta_data.keys():
            wafer = str(self.meta_data["wafer"])
        else:
            wafer = "null"
        if "datetime" in self.meta_data.keys():
            day_str, _time_of_day_str = self.meta_data["datetime"].split(" ")
        else:
            day_str = "0000-00-00"
        if "band" in self.meta_data.keys():
            band = F"Band{'%02i' % (self.meta_data['band'])}"
        else:
            band = "null"
        self.output_file = pro_data_dir
        for directory in [location, wafer, band, day_str]:
            self.output_file = os.path.join(self.output_file, directory)
            if not os.path.exists(self.output_file):
                os.mkdir(self.output_file)
        else:
            basename = os.path.basename(self.path)
            prefix, _extension = basename.rsplit(".", 1)
            self.output_file = os.path.join(self.output_file, prefix + "_s21.csv")

    def write(self):
        if not self.group_delay_removed:
            self.remove_group_delay()

        # write the output S21 file
        with open(self.output_file, 'w') as f:
            meta_data_line = ""
            for key in sorted(self.meta_data.keys()):
                if key == "path":
                    meta_data_line = F"path,{self.meta_data['path']}|" + meta_data_line
                else:
                    meta_data_line += F"{key},{self.meta_data[key]}|"
            f.write("% MetaData :" + meta_data_line[:-1] + "\n")
            f.write("% Header :freq_ghz,real,imag\n")
            for freq, s21_value in list(zip(self.freqs_GHz, self.s21_complex)):
                real = s21_value.real
                imag = s21_value.imag
                f.write(F"{freq},{real},{imag}\n")

    def plot(self, save=True, show=False, show_bands=True):
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

        # Processed Data
        s21_subplot(ax_pro_phase, plot_data,
                    x_data_str="rad_per_sec", y_data_str='pro_phase_unwrapped',
                    x_label_str="Frequency (radians / second)", y_label_str="Phase (radians)",
                    leg_label_str="Phase S21", title_str="Processed S21 Phase Residuals",
                    color="dodgerblue", ls="solid", show_bands=False)

        s21_subplot(ax_pro_ri, plot_data,
                    x_data_str="pro_real", y_data_str='pro_imag',
                    x_label_str="Real S21", y_label_str="Imaginary S21",
                    leg_label_str="Real-Imag S21", title_str="Processed Real(freq) vs Imaginary(freq) S21",
                    color="dodgerblue", ls="solid", show_bands=False)

        # Display
        if show:
            plt.show()
        if save:
            if self.output_file is None:
                self.prepare_output_file()
            plt.draw()
            plot_file_name, _ = self.output_file.rsplit(".", 1)
            plot_file_name += '.pdf'
            plt.savefig(plot_file_name)
            print("Saved Plot to:", plot_file_name)
        plt.clf()
        return


if __name__ == "__main__":
    base = os.path.join(raw_data_dir, "princeton", "SMBK_wafer8")
    meta_data_path = os.path.join(base, "meta_data.txt")
    m21 = MetaS21()
    m21.meta_from_file(meta_data_path)
    paths = get_all_file_paths(base)
    raw_data = {}
    for path in paths:
        _, extension = path.rsplit('.', 1)
        if extension.lower() == "csv":
            this_loop_s21 = InductS21(path=path, columns=("freq_Hz", 'real', "imag"))
            this_loop_s21.remove_group_delay()
            this_loop_s21.add_meta_data(**m21.file_to_meta[path])
            this_loop_s21.calc_meta_data()
            this_loop_s21.write()
            this_loop_s21.plot()
            raw_data[path] = this_loop_s21



