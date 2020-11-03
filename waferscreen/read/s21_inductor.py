import os
import numpy as np
from matplotlib import pyplot as plt
from waferscreen.read.table_read import num_format
from ref import pro_data_dir


def lin_equation(x, m, b):
    y = (m * x) + b
    return y

class InductS21:
    def __init__(self, path, columns=None, meas_dict=None, first_data_line=0, auto_process=True):
        self.path = path
        self.meas_dict = meas_dict
        self.first_data_line = first_data_line
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

        # Initialized variables used in methods
        self.freqs_GHz = None
        self.s21_complex = None
        self.s21_mag = None
        self.s21_phase = None
        self.meta_data = {}
        self.group_delay = None
        self.output_file = None

        if auto_process:
            self.induct()

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

    def get_mag_phase(self):
        if self.s21_complex is None:
            self.induct()
        if self.s21_mag is None or self.s21_phase:
            real = np.real(self.s21_complex)
            imag = np.imag(self.s21_complex)
            self.s21_mag = 20 * np.log10(np.sqrt((real ** 2.0) + (imag ** 2.0)))
            self.s21_phase = np.arctan2(imag, real)
        return self.s21_mag, self.s21_phase

    def add_meta_data(self, **kwargs):
        if kwargs is None:
            pass
        else:
            self.meta_data.update(kwargs)

    def calc_group_delay(self, plot=False):
        _s21_mag, s21_phase = self.get_mag_phase()
        radians_per_second = self.freqs_GHz * 1.0e9 * 2.0 * np.pi
        self.group_delay, offset = np.polyfit(radians_per_second, s21_phase, deg=1)
        if plot:
            def group_fit(x):
                return lin_equation(x, self.group_delay, offset)
            plt.plot(radians_per_second, s21_phase)
            plt.plot(radians_per_second, group_fit(radians_per_second))
            plt.show()


    def write(self):
        basename = os.path.basename(self.path)
        if "location" in self.meta_data.keys():
            location = self.meta_data["location"]
        else:
            location = "null"
        self.output_file = os.path.join(pro_data_dir)


if __name__ == "__main__":
    base = "C:\\Users\\chw3k5\\PycharmProjects\\WaferScreen\\waferscreen\\raw\\princeton\\SMBK_wafer8"
    filename = "1603928373.66-F_4.00_TO_5.00-BW_1000.0-ATTEN_20.0-VOLTS_0.000.CSV"
    i21 = InductS21(path=os.path.join(base, filename), columns=("freq_Hz", 'real', "imag"), meas_dict={},
                    first_data_line=3)
    meta_data = {"ctime": 1603928373.66, "freq_min_GHz": 4.0, "freq_max_GHz": 5.0, "IF_band_Hz": 1000,
                 "atten": 20, "volts": 0.0, "location": "princeton", "wafer": 8}
    i21.add_meta_data(**meta_data)
    i21.calc_group_delay(plot=True)



