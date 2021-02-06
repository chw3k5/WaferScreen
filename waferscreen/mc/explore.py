import datetime
import numpy as np
import matplotlib.pyplot as plt
from waferscreen.analyze.lambfit import phi_0
from waferscreen.data_io.s21_io import read_s21
from waferscreen.data_io.lamb_io import remove_processing_tags
from waferscreen.mc.data import get_all_lamb_files


def error_bar_report_plot(ax, xdata, ydata, yerr, color="black", ls='None', marker="o", alpha=0.7,
                          x_label=None, y_label=None):
    ax.errorbar(xdata, ydata, yerr=yerr,
                color=color, ls=ls, marker=marker, alpha=alpha)
    if x_label is None:
        ax.set_xlabel("Average Resonator Center Frequency (GHz)")
    else:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)
    return ax


def hist_report_plot(ax, data, bins=10, color="blue", x_label=None, y_label=None):
    ax.hist(data, bins=bins, color=color)
    if x_label is not None:
        ax.set_xlabel(x_label)
    if y_label is None:
        ax.set_ylabel("Resonators per Bin")
    else:
        ax.set_ylabel(y_label)
    ax.grid(True)
    return ax


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
        ordered_res_strs = sorted(self.available_res_nums)
        lamb_values = np.array([self.__getattribute__(res_str).lamb_fit.lambfit for res_str in ordered_res_strs])
        lamb_value_errs = np.array([self.__getattribute__(res_str).lamb_fit.lambfit_err
                                    for res_str in ordered_res_strs])
        flux_ramp_pp_khz = np.array([self.__getattribute__(res_str).lamb_fit.pfit * 1.0e6
                                     for res_str in ordered_res_strs])
        flux_ramp_pp_khz_errs = np.array([self.__getattribute__(res_str).lamb_fit.pfit_err * 1.0e6
                                          for res_str in ordered_res_strs])
        conversion_factor = (phi_0 / (2.0 * np.pi)) * 1.0e12
        fr_squid_mi_pH = np.array([self.__getattribute__(res_str).lamb_fit.mfit * conversion_factor
                                   for res_str in ordered_res_strs])
        fr_squid_mi_pH_err = np.array([self.__getattribute__(res_str).lamb_fit.mfit_err * conversion_factor
                                       for res_str in ordered_res_strs])
        f_centers_ghz_mean = []
        f_centers_ghz_std = []
        q_i_mean = []
        q_i_std = []
        q_c_mean = []
        q_c_std = []
        impedance_ratio_mean = []
        impedance_ratio_std = []
        for res_str in ordered_res_strs:
            single_lamb = self.__getattribute__(res_str)
            f_centers_this_lamb = np.array([res_params.fcenter_ghz for res_params in single_lamb.res_fits])
            f_centers_ghz_mean.append(np.mean(f_centers_this_lamb))
            f_centers_ghz_std.append(np.std(f_centers_this_lamb))

            q_is_this_lamb = np.array([res_params.q_i for res_params in single_lamb.res_fits])
            q_i_mean.append(np.mean(q_is_this_lamb))
            q_i_std.append(np.std(q_is_this_lamb))

            q_cs_this_lamb = np.array([res_params.q_c for res_params in single_lamb.res_fits])
            q_c_mean.append(np.mean(q_cs_this_lamb))
            q_c_std.append(np.std(q_cs_this_lamb))

            impedance_ratios_this_lamb = np.array([res_params.impedance_ratio for res_params in single_lamb.res_fits])
            impedance_ratio_mean.append(np.mean(impedance_ratios_this_lamb))
            impedance_ratio_std.append(np.std(impedance_ratios_this_lamb))
        f_centers_ghz_mean = np.array(f_centers_ghz_mean)
        f_centers_ghz_std = np.array(f_centers_ghz_std)
        q_i_mean = np.array(q_i_mean)
        q_i_std = np.array(q_i_std)
        q_c_mean = np.array(q_c_mean)
        q_c_std = np.array(q_c_std)
        impedance_ratio_mean = np.array(impedance_ratio_mean)
        impedance_ratio_std = np.array(impedance_ratio_std)
        f_spacings_ghz = f_centers_ghz_mean[1:] - f_centers_ghz_mean[:-1]
        f_spacings_mhz_mean = np.mean(f_spacings_ghz) * 1.0e3
        f_spacings_mhz_std = np.std(f_spacings_ghz) * 1.0e3

        # initialize the plot stuff
        fig, axes = plt.subplots(nrows=6, ncols=2, figsize=(10, 15))
        fig.subplots_adjust(left=0.125, bottom=0.02, right=0.9, top=0.98, wspace=0.25, hspace=0.25)
        fig.suptitle(F"{wafer_num_to_str(single_lamb.wafer)}, {single_lamb.band} reprot: " +
                     F"{len(f_centers_ghz_mean)}/65 resonators found. " +
                     F"Mean spacing: {'%6.3f' % f_spacings_mhz_mean} MHz, STD: {'%6.3f' % f_spacings_mhz_std} MHz",
                     y=0.995)
        # Qi
        q_i_label = F"Qi (Quality Factor)"
        error_bar_report_plot(ax=axes[0, 0], xdata=f_centers_ghz_mean, ydata=q_i_mean, yerr=q_i_std,
                              color="black", ls='None', marker="o", alpha=0.7,
                              x_label=None, y_label=q_i_label)
        hist_report_plot(ax=axes[0, 1], data=q_i_mean, bins=10, color="blue", x_label=q_i_label, y_label=None)

        # Qc
        q_c_label = F"Qc (Quality Factor)"
        error_bar_report_plot(ax=axes[1, 0], xdata=f_centers_ghz_mean, ydata=q_c_mean, yerr=q_c_std,
                              color="black", ls='None', marker="o", alpha=0.7,
                              x_label=None, y_label=q_c_label)
        hist_report_plot(ax=axes[1, 1], data=q_c_mean, bins=10, color="blue", x_label=q_c_label, y_label=None)

        # Impedance Ratio (Z ratio)
        zratio_label = F"Impedance Ratio (Z ratio)"
        error_bar_report_plot(ax=axes[2, 0], xdata=f_centers_ghz_mean,
                              ydata=impedance_ratio_mean, yerr=impedance_ratio_std,
                              color="black", ls='None', marker="o", alpha=0.7,
                              x_label=None, y_label=zratio_label)
        hist_report_plot(ax=axes[2, 1], data=impedance_ratio_mean, bins=10, color="blue",
                         x_label=zratio_label, y_label=None)

        # Lambda (SQUID parameter lambda)
        lamb_label = F"SQUID parameter lambda"
        error_bar_report_plot(ax=axes[3, 0], xdata=f_centers_ghz_mean,
                              ydata=lamb_values, yerr=lamb_value_errs,
                              color="black", ls='None', marker="o", alpha=0.7,
                              x_label=None, y_label=lamb_label)
        hist_report_plot(ax=axes[3, 1], data=lamb_values, bins=10, color="blue",
                         x_label=lamb_label, y_label=None)

        # Flux Ramp Span (peak-to-peak fit parameter)
        flux_ramp_label = F"Flux Ramp Span (kHz)"
        error_bar_report_plot(ax=axes[4, 0], xdata=f_centers_ghz_mean,
                              ydata=flux_ramp_pp_khz, yerr=flux_ramp_pp_khz_errs,
                              color="black", ls='None', marker="o", alpha=0.7,
                              x_label=None, y_label=flux_ramp_label)
        hist_report_plot(ax=axes[4, 1], data=flux_ramp_pp_khz, bins=10, color="blue",
                         x_label=flux_ramp_label, y_label=None)

        # fr_squid_mi_pH
        fr_squid_mi_pH_label = F"FR - SQUID Mutual Inductance (pH)"
        error_bar_report_plot(ax=axes[5, 0], xdata=f_centers_ghz_mean,
                              ydata=fr_squid_mi_pH, yerr=fr_squid_mi_pH_err,
                              color="black", ls='None', marker="o", alpha=0.7,
                              x_label=None, y_label=fr_squid_mi_pH_label)
        hist_report_plot(ax=axes[5, 1], data=fr_squid_mi_pH, bins=10, color="blue",
                         x_label=fr_squid_mi_pH_label, y_label=None)

        fig.show()

        print("temp test point")


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

    def band_swbr_reports(self):
        for seed_handle in self.available_seed_handles:
            if seed_handle in self.__dict__.keys():
                seed_name_swbr = self.__getattribute__(seed_handle)
                for wafer_str in self.available_wafers:
                    if wafer_str in seed_name_swbr.__dict__.keys():
                        wafer_swbr = seed_name_swbr.__getattribute__(wafer_str)
                        for band_str in self.available_bands:
                            if band_str in wafer_swbr.__dict__.keys():
                                band_swbr = wafer_swbr.__getattribute__(band_str)
                                band_swbr.report()


if __name__ == "__main__":
    lamb_explore = LambExplore(auto_load=True)
    lamb_explore.organize(structure_key="swb")
    lamb_explore.organize(structure_key="wbs")
    lamb_explore.band_swbr_reports()

