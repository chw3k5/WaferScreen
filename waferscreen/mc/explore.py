import os
import ref
import datetime
import numpy as np
from operator import itemgetter
from waferscreen.data_io.s21_io import read_s21, ri_to_magphase
from waferscreen.mc.data import get_all_lamb_files
from waferscreen.data_io.lamb_io import remove_processing_tags
from waferscreen.data_io.series_io import SeriesKey, series_key_header
from waferscreen.plot.explore_plots import single_lamp_to_report_plot, report_plot_init, rug_plot, band_plot, report_key
import matplotlib.pyplot as plt


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
        self.lamb_dir, self.basename = os.path.split(self.path)
        self.report_dir, _lamb_foldername = os.path.split(self.lamb_dir)
        self.pro_scan_dir, _rportt_foldername = os.path.split(self.report_dir)
        self.pro_dir, _scan_foldername = os.path.split(self.pro_scan_dir)
        self.date_str_dir, _pro_foldername = os.path.split(self.pro_dir)
        self.seed_scan_path = None

        self.metadata = None
        self.res_fits = None
        self.lamb_fit = None
        self.res_number = None
        self.location = None
        self.series_key = None

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
            self.seed_scan_path = os.path.join(self.date_str_dir, 'raw', 'scans', F"{self.seed_name}.csv")
        if 'location' in self.metadata.keys():
            self.location = self.metadata.location
        if all([header_key in self.metadata.keys() for header_key in series_key_header]):
            self.series_key = SeriesKey(port_power_dbm=self.metadata.port_power_dbm,
                                        if_bw_hz=self.metadata.if_bw_hz)
        self.res_number = self.lamb_fit.res_num


def set_if(thing, other_thing, type_of_thing='unknown'):
    if thing is None:
        return other_thing
    elif thing != other_thing:
        raise KeyError(F"Setting the {type_of_thing} a second time is not allowed")
    return thing


class ResLamb:
    def __init__(self, single_lamb=None):
        self.series_key = None
        self.available_res_nums = set()
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        res_str = res_num_to_str(single_lamb.res_number)
        self.__setattr__(res_str, single_lamb)
        self.available_res_nums.add(res_str)
        if self.series_key is None:
            self.series_key = single_lamb.series_key
        elif self.series_key != single_lamb.series_key:
            raise KeyError("Setting the series_key a second time is not allowed")


class SeriesLamb:
    def __init__(self, single_lamb=None):
        self.plot_colors = ["seagreen", "crimson", "darkgoldenrod", "deepskyblue", "mediumblue", "rebeccapurple"]
        self.band = self.wafer = self.report_dir = self.seed_scan_path = None
        self.available_series_handles = set()
        self.series_handle_to_key = {}
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        series_handle = str(single_lamb.series_key)
        if series_handle in self.__dict__.keys():
            self.__getattribute__(series_handle).add(single_lamb=single_lamb)
        else:
            self.__setattr__(series_handle, ResLamb(single_lamb=single_lamb))
        self.available_series_handles.add(series_handle)
        self.series_handle_to_key[series_handle] = single_lamb.series_key
        self.wafer = set_if(thing=self.wafer, other_thing=single_lamb.wafer, type_of_thing='wafer')
        self.band = set_if(thing=self.band, other_thing=single_lamb.band, type_of_thing='band')
        self.report_dir = set_if(thing=self.report_dir, other_thing=single_lamb.report_dir, type_of_thing='report_dir')
        self.seed_scan_path = set_if(thing=self.seed_scan_path, other_thing=single_lamb.seed_scan_path,
                                     type_of_thing='seed_scan_path')

    def report(self):
        fig, ax_key, ax_res_spec, ax_rug, axes_shist = report_plot_init(num_of_scatter_hist_x=3,
                                                                        num_of_scatter_hist_y=2)
        wafer_str = wafer_num_to_str(self.wafer)
        fig.suptitle(F"{wafer_str}, {self.band} report:", y=0.995, x=0.98, horizontalalignment='right')
        leglines = []
        leglabels = []
        counter = 0
        rug_y_increment = 1.0 / len(self.available_series_handles)
        handle_list = list(self.available_series_handles)
        series_keys = [self.series_handle_to_key[handle] for handle in handle_list]
        sorted_series_handles, *ordered_series_values = zip(*sorted([(handle, *series_key)
                                                                     for handle, series_key
                                                                     in zip(handle_list, series_keys)],
                                                            key=itemgetter(1, 2), reverse=True))
        f_centers_ghz_all = []
        res_nums = []
        for series_handle in sorted_series_handles:
            res_set = self.__getattribute__(series_handle)
            color = self.plot_colors[counter % len(self.plot_colors)]
            axes_shist, leglines, leglabels, f_centers_ghz_all, res_nums, summary_info \
                = single_lamp_to_report_plot(axes=axes_shist, res_set=res_set, color=color, band_str=self.band,
                                             leglines=leglines, leglabels=leglabels)
            y_max = 1.0 - (rug_y_increment * counter)
            counter += 1
            y_min = 1.0 - (rug_y_increment * counter)
            ax_rug = rug_plot(ax=ax_rug, xdata=f_centers_ghz_all, y_min=y_min, y_max=y_max, color=color)

        # Raw S21 Scan data
        x_min, x_max = ax_rug.get_xlim()
        formatted_s21_dict, metadata = read_s21(path=self.seed_scan_path)
        f_ghz = formatted_s21_dict["freq_ghz"]
        s21_mag, _s21_phase = ri_to_magphase(r=formatted_s21_dict["real"], i=formatted_s21_dict["imag"])
        indexes_to_plot = np.where((f_ghz >= x_min) & (f_ghz <= x_max))
        ax_res_spec = band_plot(ax=ax_res_spec, f_ghz=f_ghz[indexes_to_plot], mag_dbm=s21_mag[indexes_to_plot],
                                f_centers_ghz_all=f_centers_ghz_all, res_nums=res_nums, band_str=self.band)
        ax_res_spec.set_xlim(left=x_min, right=x_max)

        # Plot KEY
        ax_key = report_key(ax=ax_key, leglines=leglines, leglabels=leglabels, summary_info=summary_info)

        # Display
        scatter_plot_basename = F"ScatterHist_{self.band}_{wafer_str}.pdf"
        scatter_plot_path = os.path.join(self.report_dir, scatter_plot_basename)
        plt.draw()
        plt.savefig(scatter_plot_path)
        print("Saved Plot to:", scatter_plot_path)
        plt.show(block=True)
        plt.close(fig=fig)


class SeedsWBS:
    def __init__(self, single_lamb):
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        seed_handle = seed_name_to_handle(single_lamb.seed_name)
        if seed_handle in self.__dict__.keys():
            self.__getattribute__(seed_handle).add(single_lamb=single_lamb)
        else:
            self.__setattr__(seed_handle, SeriesLamb(single_lamb=single_lamb))

    def report(self):
        # loop here to to get reports across seeds and series
        pass


class BandsSWB:
    def __init__(self, single_lamb):
        self.band = self.wafer = None
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        band_handle = str(single_lamb.band)
        if band_handle in self.__dict__.keys():
            self.__getattribute__(band_handle).add(single_lamb=single_lamb)
        else:
            self.__setattr__(band_handle, SeriesLamb(single_lamb=single_lamb))
        if self.wafer is None:
            self.wafer = single_lamb.wafer
        elif self.wafer != single_lamb.wafer:
            raise KeyError("Setting the wafer a second time is not allowed")


class BandsWBS:
    def __init__(self, single_lamb):
        self.band = self.wafer = None
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        band_handle = str(single_lamb.band)
        if band_handle in self.__dict__.keys():
            self.__getattribute__(band_handle).add(single_lamb=single_lamb)
        else:
            self.__setattr__(band_handle, SeedsWBS(single_lamb=single_lamb))
        if self.wafer is None:
            self.wafer = single_lamb.wafer
        elif self.wafer != single_lamb.wafer:
            raise KeyError("Setting the wafer a second time is not allowed")


class WafersSWB:
    def __init__(self, single_lamb):
        self.band = self.wafer = None
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        wafer_handle = wafer_num_to_str(single_lamb.wafer)
        if wafer_handle in self.__dict__.keys():
            self.__getattribute__(wafer_handle).add(single_lamb=single_lamb)
        else:
            self.__setattr__(wafer_handle, BandsSWB(single_lamb=single_lamb))


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
                    self.__setattr__(wafer_str, BandsWBS(single_lamb=single_lamb))
                self.update_loops_vars(single_lamb=single_lamb)

        elif structure_key == "swb":
            for lamb_path in sorted(self.lamb_params_data.keys()):
                single_lamb = self.lamb_params_data[lamb_path]
                seed_handle = seed_name_to_handle(single_lamb.seed_name)
                if seed_handle in self.__dict__.keys():
                    self.__getattribute__(seed_handle).add(single_lamb=single_lamb)
                else:
                    self.__setattr__(seed_handle, WafersSWB(single_lamb=single_lamb))
                self.update_loops_vars(single_lamb=single_lamb)

    def band_swbr_reports(self):
        for seed_handle in self.available_seed_handles:
            if seed_handle in self.__dict__.keys():
                wafers_per_seed = self.__getattribute__(seed_handle)
                for wafer_str in self.available_wafers:
                    if wafer_str in wafers_per_seed.__dict__.keys():
                        bands_per_wafer = wafers_per_seed.__getattribute__(wafer_str)
                        for band_str in self.available_bands:
                            if band_str in bands_per_wafer.__dict__.keys():
                                single_band = bands_per_wafer.__getattribute__(band_str)
                                single_band.report()


if __name__ == "__main__":
    lamb_explore = LambExplore(auto_load=True)
    lamb_explore.organize(structure_key="swb")
    lamb_explore.organize(structure_key="wbs")
    lamb_explore.band_swbr_reports()
