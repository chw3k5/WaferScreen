import datetime
import matplotlib.pyplot as plt
from waferscreen.data_io.s21_io import read_s21
from waferscreen.data_io.lamb_io import remove_processing_tags
from waferscreen.mc.data import get_all_lamb_files


def wafer_num_to_str(wafer_num):
    return F"Wafer{'%03i' % wafer_num}"


def wafer_str_to_num(wafer_str):
    return int(wafer_str.lower().replace("wafer", ""))


def res_num_to_str(res_num):
    return F"Res{'%04i' % res_num}"


def seed_name_to_handle(seed_base):
    return seed_base.replace("-", "_").replace(".", "point")


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class SingleLamb:
    def __init__(self, path, auto_load=True):
        self.path = path
        self.metadata = None
        self.res_fits = None
        self.lamb_fit = None
        self.res_number = None

        self.wafer = self.band = self.meas_time = self.seed_name = None
        if auto_load:
            self.read(lamb_path=self.path)

    def read(self, lamb_path):
        _s21, metadata, self.res_fits, lamb_fits = read_s21(path=lamb_path, return_res_params=True,
                                                            return_lamb_params=True)
        self.metadata = AttrDict(**metadata)

        self.lamb_fit = lamb_fits[0]
        if "wafer" in self.metadata.keys():
            self.wafer = self.metadata.wafer
        if "so_band" in self.metadata.keys():
            self.band = self.metadata.so_band
        if 'seed_base' in self.metadata.keys():
            self.seed_name = remove_processing_tags(self.metadata.seed_base)
            scan_freqs, meas_utc = self.seed_name.split("_")
            year_month_day, hour_min_sec = meas_utc.split(" ")
            datetime_str = F"{year_month_day} {hour_min_sec.replace('-', ':')}+00:00"
            self.meas_time = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S.%f%z')
        self.res_number = self.lamb_fit.res_num


class ResWBRS:
    def __init__(self, single_lamb):
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        seed_handle = seed_name_to_handle(single_lamb.seed_name)
        self.__setattr__(seed_handle, single_lamb)


class BandWBRS:
    def __init__(self, single_lamb):
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        res_str = res_num_to_str(single_lamb.res_number)
        if res_str in self.__dict__.keys():
            self.__getattribute__(res_str).add(single_lamb=single_lamb)
        else:
            self.__setattr__(res_str, ResWBRS(single_lamb=single_lamb))


class WaferWBRS:
    def __init__(self, single_lamb):
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        if single_lamb.band in self.__dict__.keys():
            self.__getattribute__(single_lamb.band).add(single_lamb=single_lamb)
        else:
            self.__setattr__(single_lamb.band, BandWBRS(single_lamb=single_lamb))


class BandSWBR:
    def __init__(self, single_lamb):
        self.available_res_nums = set()
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        res_str = res_num_to_str(single_lamb.res_number)
        self.__setattr__(res_str, single_lamb)
        self.available_res_nums.add(res_str)

    def report(self):
        # do some data analysis
        f_center_ghz_last = None
        f_spacings_ghz = []
        f_centers_ghz = []
        q_i_mean = []
        q_i_std = []
        q_c_mean = []
        q_c_std = []
        z_ratio_mean = []
        z_ratio_std = []
        lamb_values = []
        flux_ramp_pp = []
        frs = []
        for res_str in sorted(self.available_res_nums):
            single_lamb = self.__getattribute__(res_str)

        # initialize the plot stuff
        fig = plt.figure(figsize=(10, 25))
        ax1 = fig.add_subplot(241)






class WaferSWBR:
    def __init__(self, single_lamb):
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        if single_lamb.band in self.__dict__.keys():
            self.__getattribute__(single_lamb.band).add(single_lamb)
        else:
            self.__setattr__(single_lamb.band, BandSWBR(single_lamb))


class SeedNameSWBR:
    def __init__(self, single_lamb):
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        wafer_str = wafer_num_to_str(single_lamb.wafer)
        if wafer_str in self.__dict__.keys():
            self.__getattribute__(wafer_str).add(single_lamb=single_lamb)
        else:
            self.__setattr__(wafer_str, WaferSWBR(single_lamb=single_lamb))


class LambExplore:
    def __init__(self, auto_load=True):
        self.lamb_params_data = None
        self.available_seed_handles = set()
        self.available_bands = set()
        self.available_wafers = set()
        if auto_load:
            self.readall()

    def readall(self):
        self.lamb_params_data = {lamb_path: SingleLamb(path=lamb_path, auto_load=True)
                                 for lamb_path in get_all_lamb_files()}

    def update_loops_vars(self, single_lamb):
        self.available_seed_handles.add(seed_name_to_handle(single_lamb.seed_name))
        self.available_bands.add(single_lamb.band)
        self.available_wafers.add(wafer_num_to_str(single_lamb.wafer))

    def organize(self, structure_key=None):
        structure_key = structure_key.lower().strip()
        # make a data attribute structure
        if structure_key == "wbs" or structure_key is None:
            for lamb_path in sorted(self.lamb_params_data.keys()):
                single_lamb = self.lamb_params_data[lamb_path]
                wafer_str = wafer_num_to_str(single_lamb.wafer)
                if wafer_str in self.__dict__.keys():
                    self.__getattribute__(wafer_str).add(single_lamb=single_lamb)
                else:
                    self.__setattr__(wafer_str, WaferWBRS(single_lamb=single_lamb))
                self.update_loops_vars(single_lamb=single_lamb)

        elif structure_key == "swb":
            for lamb_path in sorted(self.lamb_params_data.keys()):
                single_lamb = self.lamb_params_data[lamb_path]
                seed_handle = seed_name_to_handle(single_lamb.seed_name)
                if seed_handle in self.__dict__.keys():
                    self.__getattribute__(seed_handle).add(single_lamb=single_lamb)
                else:
                    self.__setattr__(seed_handle, SeedNameSWBR(single_lamb=single_lamb))
                self.update_loops_vars(single_lamb=single_lamb)


if __name__ == "__main__":
    lamb_explore = LambExplore(auto_load=True)
    lamb_explore.organize(structure_key="swb")
    lamb_explore.organize(structure_key="wbs")

