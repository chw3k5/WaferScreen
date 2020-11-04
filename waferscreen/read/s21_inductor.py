import os
import time
import numpy as np
from matplotlib import pyplot as plt
from waferscreen.read.table_read import num_format
from waferscreen.tools.rename import get_all_file_paths
from waferscreen.tools.band_calc import band_center_to_band_number
from ref import pro_data_dir, raw_data_dir


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


class InductS21:
    def __init__(self, path, columns=None, auto_process=True, verbose=True):
        self.path = path
        self.verbose = verbose
        if columns is None:
            self.columns = ("freq_GHz", 'real', "imag")
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
        self.s21_complex = None
        self.s21_mag = None
        self.s21_phase = None
        self.meta_data = {}
        self.group_delay = None
        self.output_file = None
        self.freq_step = None
        self.max_delay = None

        if auto_process:
            self.induct()
            self.remove_group_delay()

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
        real = data_matrix[:, 1]
        imag = data_matrix[:, 2]
        self.s21_complex = real + (1j * imag)
        self.freq_step = np.mean(self.freqs_GHz[1:] - self.freqs_GHz[:-1]) * 1.0e9
        self.max_delay = 1.0 / (2.0 * np.sqrt(2.0) * self.freq_step)

    def get_mag_phase(self):
        if self.s21_complex is None:
            self.induct()
        if self.s21_mag is None or self.s21_phase is None:
            real = np.real(self.s21_complex)
            imag = np.imag(self.s21_complex)
            self.s21_mag = 20 * np.log10(np.sqrt((real ** 2.0) + (imag ** 2.0)))
            self.s21_phase = np.arctan(imag, real)
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
        _s21_mag, s21_phase = self.get_mag_phase()
        radians_per_second = self.freqs_GHz * 1.0e9 * 2.0 * np.pi
        s21_phase_zones = []
        was_increasing = None
        last_phase = s21_phase[0]
        index_count = 1
        for a_phase in s21_phase[1:]:
            phase_diff = a_phase - last_phase
            if phase_diff == 0.0:
                is_increasing = None
            elif phase_diff < 0.0:
                is_increasing = False
            else:
                is_increasing = True
            if is_increasing is not None:
                if was_increasing is None:
                    s21_phase_zones.append([(radians_per_second[index_count - 1], last_phase),
                                            (radians_per_second[index_count], a_phase)])
                elif was_increasing == is_increasing:
                    s21_phase_zones[-1].append((radians_per_second[index_count], a_phase))
                else:
                    is_increasing = None
            # updates for the next loop
            was_increasing = is_increasing
            last_phase = a_phase
            index_count += 1

        group_delay_per_zone = []
        for zone in s21_phase_zones:
            s21_rads_per_second = [omega for omega, phase in zone]
            s21_phase_zone = [phase for omega, phase in zone]
            group_delay_this_zone, _offset = np.polyfit(s21_rads_per_second, s21_phase_zone, deg=1)
            group_delay_per_zone.append(np.abs(group_delay_this_zone))
        group_delay = np.average(group_delay_per_zone, weights=[len(zone) - 1 for zone in s21_phase_zones])
        if group_delay < self.max_delay:
            self.group_delay = group_delay
        else:
            self.group_delay = float("nan")
        if self.verbose:
            print_str = F"{'%3.3f' % (self.group_delay * 1.0e9)} ns of cable delay, " + \
                        F"{'%3.3f' % (self.max_delay * 1.0e9)} ns is the maximum group delay measurable."

            print(print_str)

    def remove_group_delay(self, user_input_group_delay=None):
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
        phase_factors = np.exp(-1j * 2.0 * np.pi * self.freqs_GHz * 1.0e9 * group_delay)
        self.s21_complex = self.s21_complex / phase_factors
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
            self.output_file = os.path.join(self.output_file, basename)


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
            raw_data[path] = InductS21(path=path, columns=("freq_Hz", 'real', "imag"))
            raw_data[path].add_meta_data(**m21.file_to_meta[path])
            raw_data[path].calc_meta_data()
            raw_data[path].write()


