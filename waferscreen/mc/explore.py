# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import os
import datetime
from operator import itemgetter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from waferscreen.data_io.data_pro import get_all_lamb_files, get_lamb_files_between_dates
from waferscreen.data_io.lamb_io import remove_processing_tags
from waferscreen.data_io.s21_io import read_s21
from waferscreen.data_io.series_io import SeriesKey, series_key_header
from waferscreen.data_io.explore_io import wafer_num_to_str, res_num_to_str, seed_name_to_handle, \
    chip_id_str_to_chip_id_handle, chip_id_handle_chip_id_str, chip_id_tuple_to_chip_id_str, \
    chip_id_str_to_chip_id_tuple, band_str_to_num
from waferscreen.plot.explore_plots import report_plot
from ref import too_long_did_not_read_dir


# Pure magic, https://stackoverflow.com/questions/2641484/class-dict-self-init-args
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

        self.wafer = self.so_band = self.chip_id_str = self.chip_position = self.meas_time = self.seed_name = None
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
            self.so_band = self.metadata.so_band
        if "x_position" in self.metadata.keys() and "y_position" in self.metadata.keys():
            self.chip_position = (self.metadata["x_position"], self.metadata["y_position"])
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

        # make a unique-within-a-wafer chip ID
        if self.chip_position is None:
            self.chip_id_str = chip_id_tuple_to_chip_id_str(chip_id_tuple=(band_str_to_num(self.so_band),
                                                                           None, None))
        else:
            self.chip_id_str = chip_id_tuple_to_chip_id_str(chip_id_tuple=(band_str_to_num(self.so_band),
                                                                           self.chip_position[0],
                                                                           self.chip_position[1]))


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
        self.chip_id_str = self.wafer = self.report_dir = self.seed_scan_path = None
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
        self.chip_id_str = set_if(thing=self.chip_id_str, other_thing=single_lamb.chip_id_str,
                                  type_of_thing='chip_id_str')
        self.report_dir = set_if(thing=self.report_dir, other_thing=single_lamb.report_dir, type_of_thing='report_dir')
        self.seed_scan_path = set_if(thing=self.seed_scan_path, other_thing=single_lamb.seed_scan_path,
                                     type_of_thing='seed_scan_path')

    def report(self, show=False, omit_flagged=True, save=True, return_fig=False):
        wafer_str = wafer_num_to_str(self.wafer)
        chip_id_str = self.chip_id_str
        handle_list = list(self.available_series_handles)
        series_keys = [self.series_handle_to_key[handle] for handle in handle_list]
        sorted_series_handles, *ordered_series_values = zip(*sorted([(handle, *series_key)
                                                                     for handle, series_key
                                                                     in zip(handle_list, series_keys)],
                                                                    key=itemgetter(1, 2), reverse=True))
        series_res_sets = {series_handle: self.__getattribute__(series_handle) for series_handle in
                           sorted_series_handles}
        seed_scan_path = self.seed_scan_path
        report_dir = self.report_dir
        report_fig = report_plot(series_res_sets, sorted_series_handles, wafer_str,
                                 chip_id_str, seed_scan_path, report_dir,
                                 show=show, omit_flagged=omit_flagged, save=save, return_fig=return_fig)
        return report_fig


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


class ChipIDsSWB:
    def __init__(self, single_lamb):
        self.chip_id_str = self.wafer = None
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        chip_id_handle = chip_id_str_to_chip_id_handle(single_lamb.chip_id_str)
        if chip_id_handle in self.__dict__.keys():
            self.__getattribute__(chip_id_handle).add(single_lamb=single_lamb)
        else:
            self.__setattr__(chip_id_handle, SeriesLamb(single_lamb=single_lamb))
        if self.wafer is None:
            self.wafer = single_lamb.wafer
        elif self.wafer != single_lamb.wafer:
            raise KeyError("Setting the wafer a second time is not allowed")


class ChipIDsWBS:
    def __init__(self, single_lamb):
        self.chip_id_str = self.wafer = None
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        chip_id_handle = chip_id_str_to_chip_id_handle(single_lamb.chip_id_str)
        if chip_id_handle in self.__dict__.keys():
            self.__getattribute__(chip_id_handle).add(single_lamb=single_lamb)
        else:
            self.__setattr__(chip_id_handle, SeedsWBS(single_lamb=single_lamb))
        if self.wafer is None:
            self.wafer = single_lamb.wafer
        elif self.wafer != single_lamb.wafer:
            raise KeyError("Setting the wafer a second time is not allowed")


class WafersSWB:
    def __init__(self, single_lamb):
        self.chip_id_str = self.wafer = None
        if single_lamb is not None:
            self.add(single_lamb=single_lamb)

    def add(self, single_lamb):
        wafer_handle = wafer_num_to_str(single_lamb.wafer)
        if wafer_handle in self.__dict__.keys():
            self.__getattribute__(wafer_handle).add(single_lamb=single_lamb)
        else:
            self.__setattr__(wafer_handle, ChipIDsSWB(single_lamb=single_lamb))


class LambExplore:
    def __init__(self, start_date=None, end_date=None):
        """
        :param start_date: expecting the class datetime.date, as in start_date=datetime.date(year=2020, month=4, day=25)
                           or None. None will set the minimum date for data retrieval to be 0001-01-01
        :param end_date: expecting the class datetime.date, as in start_date=datetime.date(year=2020, month=4, day=25)
                         or None. None will set the maximum date for data to be retrieved as 9999-12-31
        """
        if start_date is None:
            self.start_date = datetime.date.min
        else:
            self.start_date = start_date
        if end_date is None:
            self.end_date = datetime.date.max
        else:
            self.end_date = end_date
        self.lamb_params_data = None
        self.available_seed_handles = set()
        self.available_chip_id_strs = set()
        self.available_wafers = set()
        if start_date is None and end_date is None:
            self.readall()
        else:
            self.read_between_dates()

    def readall(self):
        self.lamb_params_data = {lamb_path: SingleLamb(path=lamb_path, auto_load=True)
                                 for lamb_path in get_all_lamb_files()}

    def read_between_dates(self):
        self.lamb_params_data = {lamb_path: SingleLamb(path=lamb_path, auto_load=True)
                                 for lamb_path in get_lamb_files_between_dates(start_date=self.start_date,
                                                                               end_date=self.end_date)}

    def update_loops_vars(self, single_lamb):
        self.available_seed_handles.add(seed_name_to_handle(single_lamb.seed_name))
        self.available_chip_id_strs.add(single_lamb.chip_id_str)
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
                    self.__setattr__(wafer_str, ChipIDsWBS(single_lamb=single_lamb))
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

    def summary_reports(self, multi_page_summary=False, show=False):
        figure_dict = {}
        for seed_handle in self.available_seed_handles:
            if seed_handle in self.__dict__.keys():
                wafers_per_seed = self.__getattribute__(seed_handle)
                for wafer_str in self.available_wafers:
                    if wafer_str in wafers_per_seed.__dict__.keys():
                        if wafer_str not in figure_dict.keys():
                            figure_dict[wafer_str] = {}
                        chip_id_strs_per_wafer = wafers_per_seed.__getattribute__(wafer_str)
                        for chip_id_str in self.available_chip_id_strs:
                            chip_id_handle = chip_id_str_to_chip_id_handle(chip_id_str)
                            if chip_id_handle in chip_id_strs_per_wafer.__dict__.keys():
                                single_chip = chip_id_strs_per_wafer.__getattribute__(chip_id_handle)
                                # individually saved report plots per umux chip scale
                                report_fig = single_chip.report(save=True, show=show, return_fig=multi_page_summary)
                                # Later we will save this figure in a multi-page pdf we will use this tuple to sort
                                band_num, x_pos, y_pos = chip_id_str_to_chip_id_tuple(chip_id_str=single_chip.chip_id_str)
                                if band_num is None:
                                    band_num = float("-inf")
                                if x_pos is None:
                                    x_pos = float("-inf")
                                if y_pos is None:
                                    y_pos = float("-inf")
                                # the chip count is to handle when the same chip was measured across multiple seeds
                                chip_count = 0
                                figure_id_tup = (band_num, x_pos, y_pos, chip_count)
                                while figure_id_tup in figure_dict[wafer_str].keys():
                                    chip_count += 1
                                    figure_id_tup = (band_num, x_pos, y_pos, chip_count)
                                figure_dict[wafer_str][figure_id_tup] = report_fig
        for wafer_str in figure_dict.keys():
            per_wafer_figure_dict = figure_dict[wafer_str]
            # order the chip_id_tuples
            ordered_chip_id_tuples = sorted(per_wafer_figure_dict.keys())
            # multi-page PDF is made on a per-wafer basis
            multi_page_pdf_path = os.path.join(too_long_did_not_read_dir, F"{wafer_str}.pdf")
            if multi_page_summary:
                with PdfPages(multi_page_pdf_path) as pdf_pages:
                    for chip_id_tuple in ordered_chip_id_tuples:
                        fig_this_id = per_wafer_figure_dict[chip_id_tuple]
                        pdf_pages.savefig(fig_this_id)
                        # close all the figures and free up the resources
                        plt.close(fig=fig_this_id)
                print(F"Multipage PDF summary saved at:{multi_page_pdf_path}")


if __name__ == "__main__":
    lamb_explore = LambExplore(start_date=datetime.date(year=2021, month=1, day=1),
                               end_date=datetime.date(year=2021, month=4, day=23))
    lamb_explore.organize(structure_key="swb")
    lamb_explore.organize(structure_key="wbs")
    lamb_explore.summary_reports(multi_page_summary=True, show=False)
