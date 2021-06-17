# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import os
import datetime
import itertools
from operator import itemgetter
from multiprocessing import Pool
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from waferscreen.data_io.data_pro import get_all_lamb_files, get_lamb_files_between_dates
from waferscreen.data_io.lamb_io import remove_processing_tags
from waferscreen.data_io.s21_io import read_s21, write_s21
from waferscreen.data_io.series_io import SeriesKey, series_key_header
from waferscreen.data_io.chip_metadata import chip_metadata, wafer_pos_to_band_and_group
from waferscreen.data_io.explore_io import wafer_num_to_str, wafer_str_to_num, res_num_to_str, seed_name_to_handle, \
    chip_id_str_to_chip_id_handle, chip_id_tuple_to_chip_id_str, chip_id_str_to_chip_id_tuple, band_str_to_num, \
    FrequencyReportEntry, frequency_report_entry_header, calc_metadata_header, PhysicalChipData, \
    power_ints_and_mata_data_classes, power_str_and_column_name_to_metadata_str, power_to_power_str
from waferscreen.plot.explore_plots import report_plot
from waferscreen.plot.explore_frequency import frequencies_plot
from waferscreen.inst_control.starcryo_monitor import StarCryoData
from ref import too_long_did_not_read_dir, in_smurf_keepout, in_band, min_spacings_khz, project_starcryo_logs_dir, \
    starcryo_logs_dir, multiprocessing_threads


# Pure magic, https://stackoverflow.com/questions/2641484/class-dict-self-init-args
class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


# star cryo data
starcryo = StarCryoData(logs_dir=starcryo_logs_dir)


class SingleLamb:
    def __init__(self, path, auto_load=True, get_temperatures=False):
        self.path = path
        self.get_temperatures = get_temperatures
        self.lamb_dir, self.basename = os.path.split(self.path)
        self.report_dir, _lamb_foldername = os.path.split(self.lamb_dir)
        self.pro_scan_dir, _rportt_foldername = os.path.split(self.report_dir)
        self.pro_dir, _scan_foldername = os.path.split(self.pro_scan_dir)
        self.date_str_dir, _pro_foldername = os.path.split(self.pro_dir)

        self.flags = set()

        self.seed_scan_path = None

        self.metadata = None
        self.res_fits = None
        self.res_fit_to_starcryo_record = None
        self.lamb_fit = None
        self.res_number = None
        self.location = None
        self.series_key = None

        self.wafer = self.so_band = self.chip_id_str = self.chip_position = self.meas_time = self.seed_name = None
        self.port_power_dbm = self.group_num = self.adr_50mk = None
        if auto_load:
            self.read(lamb_path=self.path)

    def read(self, lamb_path):
        s21, metadata, self.res_fits, lamb_fits = read_s21(path=lamb_path, return_res_params=True,
                                                           return_lamb_params=True)
        self.metadata = AttrDict(**metadata)

        self.lamb_fit = lamb_fits[0]
        if "wafer" in self.metadata.keys():
            self.wafer = self.metadata.wafer
        if "so_band" in self.metadata.keys():
            self.so_band = self.metadata.so_band
        if "x_position" in self.metadata.keys() and "y_position" in self.metadata.keys():
            x_pos = self.metadata["x_position"]
            y_pos = self.metadata["y_position"]
            self.chip_position = (x_pos, y_pos)
            wafer_layout_dict = wafer_pos_to_band_and_group.get_from_wafer_pos(x_pos=x_pos, y_pos=y_pos,
                                                                               wafer_num=self.wafer)
            if wafer_layout_dict is None:
                self.group_num = None
            else:
                self.group_num = wafer_layout_dict['group_num']
                meas_band_num = band_str_to_num(self.so_band)
                if meas_band_num != wafer_layout_dict['so_band_num']:
                    err_msg = F"Band are different between the measured chip band: {meas_band_num},\n" + \
                              F"   and the band from positional metadata: {wafer_layout_dict['so_band_num']}"
                    print(err_msg)
                    raise KeyError(err_msg)
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
        if 'port_power_dbm' in self.metadata.keys():
            self.port_power_dbm = self.metadata["port_power_dbm"]
        if 'adr_50mk' in self.metadata.keys():
            self.adr_50mk = self.metadata['adr_50mk']
        self.res_number = self.lamb_fit.res_num

        # make a unique-within-a-wafer chip ID
        if self.chip_position is None:
            self.chip_id_str = chip_id_tuple_to_chip_id_str(chip_id_tuple=(band_str_to_num(self.so_band),
                                                                           None, None))
        else:
            self.chip_id_str = chip_id_tuple_to_chip_id_str(chip_id_tuple=(band_str_to_num(self.so_band),
                                                                           self.chip_position[0],
                                                                           self.chip_position[1]))

        # get the starcryo data records for these measurements
        if self.get_temperatures and self.adr_50mk is None:
            if self.res_fits is not None:
                self.res_fit_to_starcryo_record = {}
                for res_record in self.res_fits:
                    utc_this_record = res_record.utc
                    if utc_this_record is not None:
                        starcryo_record = starcryo.get_record(utc=utc_this_record)
                        if starcryo_record is not None:
                            self.res_fit_to_starcryo_record[res_record] = starcryo_record
                if self.res_fit_to_starcryo_record == {}:
                    self.res_fit_to_starcryo_record = None

            # calculate an average temperature
            if self.res_fit_to_starcryo_record is not None:
                temperature_array = np.array([self.res_fit_to_starcryo_record[res_record].adr_50mk
                                              for res_record in self.res_fit_to_starcryo_record.keys()])
                self.adr_50mk = np.mean(temperature_array)
                # save this result
                metadata['adr_50mk'] = self.adr_50mk
                if s21 is None:
                    s21_complex = None
                    freqs_ghz = None
                else:
                    s21_complex = s21['real'] + (1j * s21['imag'])
                    freqs_ghz = s21['freq_ghz']
                write_s21(output_file=lamb_path, freqs_ghz=freqs_ghz,
                          s21_complex=s21_complex, metadata=metadata,
                          fitted_resonators_parameters=self.res_fits, lamb_params_fits=lamb_fits)


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
        report_fig, flag_table_info, calc_metadata = report_plot(series_res_sets, sorted_series_handles, wafer_str,
                                                                 chip_id_str, seed_scan_path, report_dir,
                                                                 show=show, omit_flagged=omit_flagged, save=save,
                                                                 return_fig=return_fig)
        # update metadata with flag info
        calc_metadata_per_res_num = {}
        for series_handle in self.available_series_handles:
            for res_num_str in flag_table_info.keys():
                if res_num_str in self.__getattribute__(series_handle).__dict__.keys():
                    single_lamb = self.__getattribute__(series_handle).__getattribute__(res_num_str)
                    [single_lamb.flags.add(flag_str) for flag_str in flag_table_info[res_num_str].split("\n")]
            for res_num_str in calc_metadata[series_handle].keys():
                calc_metadata_this_res = calc_metadata[series_handle][res_num_str]
                power_str = power_to_power_str(calc_metadata_this_res.est_device_power_dbm)
                calc_metadata_this_series = {power_str_and_column_name_to_metadata_str(power_str, column_name):
                                             calc_metadata_this_res.__getattribute__(column_name)
                                             for column_name in calc_metadata_header}
                if res_num_str not in calc_metadata_per_res_num.keys():
                    calc_metadata_per_res_num[res_num_str] = {}
                calc_metadata_per_res_num[res_num_str].update(calc_metadata_this_series)
        for series_handle in self.available_series_handles:
            for res_num_str in calc_metadata[series_handle].keys():
                single_lamb = self.__getattribute__(series_handle).__getattribute__(res_num_str)
                combined_calc_metadata_dict = calc_metadata_per_res_num[res_num_str]
                single_lamb.metadata.update(combined_calc_metadata_dict)
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


def single_lamb_pro(lamb_path, auto_load, get_temperatures):
    return SingleLamb(path=lamb_path, auto_load=auto_load, get_temperatures=get_temperatures)


class LambExplore:
    measurement_stats_cvs_path = os.path.join(too_long_did_not_read_dir, "measurement_stats.csv")
    measurement_records_cvs_path = os.path.join(too_long_did_not_read_dir, "measurement_summary.csv")
    measurement_plot_path = os.path.join(too_long_did_not_read_dir, "measurement_frequencies_plot.pdf")
    device_stats_cvs_path = os.path.join(too_long_did_not_read_dir, "device_stats.csv")
    device_records_cvs_path = os.path.join(too_long_did_not_read_dir, "device_summary.csv")
    device_plot_path = os.path.join(too_long_did_not_read_dir, "device_frequencies_plot.pdf")

    def __init__(self, start_date=None, end_date=None, lambda_params_data=None, get_temperatures=False, verbose=True):
        """
        :param start_date: expecting the class datetime.date, as in start_date=datetime.date(year=2020, month=4, day=25)
                           or None. None will set the minimum date for data retrieval to be 0001-01-01
        :param end_date: expecting the class datetime.date, as in start_date=datetime.date(year=2020, month=4, day=25)
                         or None. None will set the maximum date for data to be retrieved as 9999-12-31
        """
        self.verbose = verbose
        if start_date is None:
            self.start_date = datetime.date.min
        else:
            self.start_date = start_date
        if end_date is None:
            self.end_date = datetime.date.max
        else:
            self.end_date = end_date
        self.get_temperatures = get_temperatures
        self.lamb_params_data = None
        self.available_seed_handles = set()
        self.available_chip_id_strs = set()
        self.available_wafers = set()
        self.records_column_names = None
        self.stats_columns = None
        # data structures
        self.device_records = None
        self.measurement_records = None
        self.measurement_records_stats_dict_keys = None
        self.spacing_dict_keys = None
        # there are two ways to initiate this class
        if lambda_params_data is None:
            self.lamb_params_data = {}
            # 1) A a read-in from the lambda csv files
            lamb_paths = get_lamb_files_between_dates(start_date=self.start_date, end_date=self.end_date)
            if multiprocessing_threads is None or multiprocessing_threads < 2:
                len_path = len(lamb_paths)
                print_interval = 1  # max(int(np.round(len_path * 0.01)), 1)
                for lamb_index, lamb_path in list(enumerate(lamb_paths)):
                    self.lamb_params_data[lamb_path] = SingleLamb(path=lamb_path, auto_load=True,
                                                                  get_temperatures=self.get_temperatures)
                    if self.verbose and lamb_index % print_interval == 0:
                        index_plus_one = lamb_index + 1
                        percent_value = 100.0 * float(index_plus_one) / len_path
                        print(F"{'%6.2f' % percent_value}% of explore.py Lambda files read: " +
                              F"{'%6i' % index_plus_one} of {len_path} files")
            else:
                single_lamb_pro_args = [(lamb_path, True, get_temps) for lamb_path, get_temps
                                        in zip(lamb_paths, [self.get_temperatures] * len(lamb_paths))]
                with Pool(multiprocessing_threads) as p:
                    single_lambs = p.starmap(single_lamb_pro, single_lamb_pro_args)
                    self.lamb_params_data = {lamb_path: single_lamb for lamb_path, single_lamb
                                             in zip(lamb_paths, single_lambs)}
        else:
            # 2) A lambda_params_data from a prior read-in
            self.lamb_params_data = lambda_params_data

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

    def filtered_output(self, wafer_numbers=None, utc_after=None, utc_before=None):
        # populate section criteria that are None
        if wafer_numbers is None:
            wafer_numbers = {wafer_str_to_num(wafer_str=wafer_str) for wafer_str in self.available_wafers}
        if utc_after is None:
            utc_after = datetime.datetime.min
        if utc_before is None:
            utc_before = datetime.datetime.max
        # loop though all the lambda_data and select what meets the various filter criteria
        output_lambda_params_data = {}
        for lambda_path in self.lamb_params_data.keys():
            lambda_data_this_lap = self.lamb_params_data[lambda_path]
            # the criteria selection statements
            if lambda_data_this_lap.wafer in wafer_numbers:
                if utc_after <= lambda_data_this_lap.meas_time <= utc_before:
                    output_lambda_params_data[lambda_path] = lambda_data_this_lap
        # check to make sure there was data in from the results of the filter
        if output_lambda_params_data == {}:
            raise ValueError("The filtered_out did not return any data after the criteria matching.")
        return LambExplore(lambda_params_data=output_lambda_params_data)

    def do_frequencies_analysis(self):
        wafer_scale_frequencies_data = {}
        # loop over all available data in this class and organize the relevant information.
        for lambda_path in self.lamb_params_data.keys():
            lambda_data_this_lap = self.lamb_params_data[lambda_path]
            wafer_num = lambda_data_this_lap.wafer
            group_num = lambda_data_this_lap.group_num
            # add this wafer number to the wafer_scale_frequencies_plot_data
            if wafer_num not in wafer_scale_frequencies_data.keys():
                wafer_scale_frequencies_data[wafer_num] = {}
            # get the so_band number
            so_band_num = band_str_to_num(lambda_data_this_lap.so_band)
            # get the chip_id
            chip_id_str = lambda_data_this_lap.chip_id_str
            # make a new data container set for this chip_id is none exists
            if chip_id_str not in wafer_scale_frequencies_data[wafer_num].keys():
                wafer_scale_frequencies_data[wafer_num][chip_id_str] = {}
            # get the seed name
            seed_name = lambda_data_this_lap.seed_name
            # make a new data container for seed_name
            if seed_name not in wafer_scale_frequencies_data[wafer_num][chip_id_str].keys():
                wafer_scale_frequencies_data[wafer_num][chip_id_str][seed_name] = {}
            # get the port_power_dbm
            port_power_dbm = lambda_data_this_lap.port_power_dbm
            # make a new data container for port_power_dbm
            if port_power_dbm not in wafer_scale_frequencies_data[wafer_num][chip_id_str][seed_name].keys():
                wafer_scale_frequencies_data[wafer_num][chip_id_str][seed_name][port_power_dbm] = set()
            # take the average of the resonator fit
            f_ghz = float(np.mean(np.array([res_fit.fcenter_ghz for res_fit in lambda_data_this_lap.res_fits])))
            # collect the data record information
            is_in_band = in_band(band_str=lambda_data_this_lap.so_band, f_ghz=f_ghz)
            is_in_keepout = in_smurf_keepout(f_ghz=f_ghz)
            flags_str = ""
            for single_flag in sorted(lambda_data_this_lap.flags):
                flags_str += F"{single_flag}|"
            if flags_str == "":
                flags_str = None
            else:
                flags_str = flags_str[:-1]
            # make the data record
            frequency_report_entry = FrequencyReportEntry(f_ghz=f_ghz, so_band=so_band_num,
                                                          is_in_band=is_in_band, is_in_keepout=is_in_keepout,
                                                          lambda_path=lambda_path, group_num=group_num,
                                                          flags=flags_str)
            # add the data record
            wafer_scale_frequencies_data[wafer_num][chip_id_str][seed_name][port_power_dbm].add(frequency_report_entry)
        # With all the data collected we do some statistics and order the data
        device_records = {}
        self.measurement_records = []
        self.measurement_records_stats_dict_keys = []
        spacing_dict_types = set()
        for wafer_num in sorted(wafer_scale_frequencies_data.keys()):
            single_wafer_frequencies = wafer_scale_frequencies_data[wafer_num]
            for chip_id_str in sorted(single_wafer_frequencies.keys()):
                so_band_num, *_xy_pos = chip_id_str_to_chip_id_tuple(chip_id_str=chip_id_str)
                single_chip_frequencies = single_wafer_frequencies[chip_id_str]
                wafer_and_chip_id = F"Wafer{'%03i' % wafer_num}|{chip_id_str.replace(',', '&').replace(' ', '')}"
                for seed_name in sorted(single_chip_frequencies.keys()):
                    single_seed_frequencies = single_chip_frequencies[seed_name]
                    for port_power_dbm in sorted(single_seed_frequencies.keys()):
                        group_id = F"{wafer_and_chip_id}|{seed_name}|{port_power_dbm}"
                        # this is currently the base level for this data structure
                        single_power_frequency_records = single_seed_frequencies[port_power_dbm]
                        # order the data records
                        frequency_records_ordered = sorted(single_power_frequency_records, key=itemgetter(0))
                        # make and array for doing stats
                        frequencies_array = np.array([frequency_report_entry.f_ghz
                                                      for frequency_report_entry in frequency_records_ordered])
                        # get spacing data
                        delta_f_khz_array = (frequencies_array[1:] - frequencies_array[:-1]) * 1.0e6
                        left_spacing_list_khz = list(itertools.chain([float('inf')], list(delta_f_khz_array)))
                        right_spacing_list_khz = list(itertools.chain(list(delta_f_khz_array), [float('inf')]))
                        # import chip level metadata and make a new frequency data record
                        order_updated_records = []
                        acceptance_list = []
                        for res_num, f_record in list(enumerate(frequency_records_ordered)):
                            record_id = F"{group_id}|{res_num_to_str(res_num)}"
                            device_id = F"{wafer_and_chip_id}|{res_num_to_str(res_num)}"
                            left_spacing_khz = left_spacing_list_khz[res_num]
                            right_spacing_khz = right_spacing_list_khz[res_num]
                            # deal with spacing acceptance
                            updated_flags = f_record.flags
                            acceptance_dict = {}
                            for min_spacing_khz in min_spacings_khz:
                                spacing_str = F"{np.round(min_spacing_khz)}_khz"
                                left_str = F"left_neighbor_within_{spacing_str}"
                                right_str = F"right_neighbor_within_{spacing_str}"
                                spacing_dict_types.add(left_str)
                                spacing_dict_types.add(right_str)
                                if left_spacing_khz > min_spacing_khz:
                                    acceptance_dict[left_str] = False
                                else:
                                    acceptance_dict[left_str] = True
                                    if updated_flags is None:
                                        updated_flags = left_str.replace("_", " ")
                                    else:
                                        updated_flags += F"|{left_str.replace('_', ' ')}"
                                if right_spacing_khz > min_spacing_khz:
                                    acceptance_dict[right_str] = False
                                else:
                                    acceptance_dict[right_str] = True
                                    if updated_flags is None:
                                        updated_flags = right_str.replace("_", " ")
                                    else:
                                        updated_flags += F"|{right_str.replace('_', ' ')}"
                            acceptance_list.append(acceptance_dict)
                            # get the existing record data
                            updated_record_data = {var_name: f_record.__getattribute__(var_name)
                                                   for var_name in frequency_report_entry_header}
                            # update some values here
                            update_f_record = {'record_id': record_id, 'device_id': device_id,
                                               'group_id': group_id, "wafer_and_chip_id": wafer_and_chip_id,
                                               'res_num': res_num, 'flags': updated_flags}
                            # get design metadata
                            res_num_metadata = chip_metadata.return_res_metadata(so_band_num=so_band_num,
                                                                                 res_num=res_num)
                            if res_num_metadata is not None:
                                # add the some of the selected meta
                                update_f_record.update({'designed_f_ghz': res_num_metadata['freq_hz'] * 1.0e-9,
                                                        'x_pos_mm_on_chip': res_num_metadata['x_pos_mm'],
                                                        'y_pos_mm_on_chip': res_num_metadata['y_pos_mm'],
                                                        'resonator_height_um': res_num_metadata['resonator_height_um'],
                                                        'wiggles': res_num_metadata['wiggles'],
                                                        'sliders': res_num_metadata['sliders'],
                                                        'slider_delta_um': res_num_metadata['slider_delta_um'],
                                                        'resonator_impedance_ohms': res_num_metadata['resonator_impedance_ohms'],
                                                        'coupling_capacitance_f': res_num_metadata['coupling_capacitance_f'],
                                                        'coupling_inductance_h': res_num_metadata['coupling_inductance_h']})

                                for chip_metadata_column in ['resonator_height_um', 'wiggles', 'sliders',
                                                             'slider_delta_um', 'resonator_impedance_ohms',
                                                             'coupling_capacitance_f', 'coupling_inductance_h']:
                                    update_f_record[chip_metadata_column] = res_num_metadata[chip_metadata_column]
                                lambda_path = updated_record_data['lambda_path']
                                # the lambda file from which this associated metadata belongs
                                self.lamb_params_data[lambda_path].metadata.update(update_f_record)

                            updated_record_data.update(update_f_record)
                            # update the explore.py class metadata
                            order_updated_records.append(FrequencyReportEntry(**updated_record_data))
                        # do stats
                        f_ghz_min = np.min(frequencies_array)
                        f_ghz_max = np.max(frequencies_array)
                        f_ghz_median = np.median(frequencies_array)
                        f_ghz_mean = np.mean(frequencies_array)
                        f_ghz_std = np.std(frequencies_array)
                        # do spacing stats
                        delta_f_khz_min = np.min(delta_f_khz_array)
                        delta_f_khz_max = np.max(delta_f_khz_array)
                        delta_f_khz_median = np.median(delta_f_khz_array)
                        delta_f_khz_mean = np.mean(delta_f_khz_array)
                        delta_f_khz_std = np.std(delta_f_khz_array)
                        # count collision zones
                        spacing_counting_dict = {}
                        flag_counting_dict = {}
                        for min_spacing_khz in min_spacings_khz:
                            spacing_str = F"{np.round(min_spacing_khz)}_khz"
                            left_str = F"left_neighbor_within_{spacing_str}"
                            right_str = F"right_neighbor_within_{spacing_str}"
                            spacing_counting_dict[min_spacing_khz] = {'left':  0, 'right':  0, 'both':  0, 'none':  0}
                            flag_counting_dict[min_spacing_khz] = {'criteria': 0, 'both': 0, 'spacing': 0, 'none': 0}
                            for acceptance_dict, frequency_record in zip(acceptance_list, order_updated_records):
                                # get stats on the types of collisions
                                left_is_within = acceptance_dict[left_str]
                                right_is_within = acceptance_dict[right_str]
                                spacing_flag = True
                                if left_is_within and right_is_within:
                                    spacing_counting_dict[min_spacing_khz]['both'] += 1
                                elif left_is_within:
                                    spacing_counting_dict[min_spacing_khz]['left'] += 1
                                elif right_is_within:
                                    spacing_counting_dict[min_spacing_khz]['right'] += 1
                                else:
                                    spacing_counting_dict[min_spacing_khz]['none'] += 1
                                    spacing_flag = False
                                # get some stats on the total number and type of flags
                                if frequency_record.flags is None:
                                    criteria_flags = set()
                                else:
                                    flag_strs = set(frequency_record.flags.split('|'))
                                    spacing_flags = {flag_str for flag_str in flag_strs if 'neighbor within' in flag_str}
                                    criteria_flags = flag_strs - spacing_flags
                                if criteria_flags != set() and spacing_flag:
                                    flag_counting_dict[min_spacing_khz]['both'] += 1
                                elif spacing_flag:
                                    flag_counting_dict[min_spacing_khz]['spacing'] += 1
                                elif criteria_flags != set():
                                    flag_counting_dict[min_spacing_khz]['criteria'] += 1
                                else:
                                    flag_counting_dict[min_spacing_khz]['none'] += 1
                        # makes a dictionary to store the stats
                        stats_dict = {"f_ghz_min": f_ghz_min, 'f_ghz_max': f_ghz_max, 'f_ghz_median': f_ghz_median,
                                      'f_ghz_mean': f_ghz_mean, 'f_ghz_std': f_ghz_std,
                                      "delta_f_khz_min": delta_f_khz_min, 'delta_f_khz_max': delta_f_khz_max,
                                      'delta_f_khz_median': delta_f_khz_median, 'delta_f_khz_mean': delta_f_khz_mean,
                                      'delta_f_khz_std': delta_f_khz_std}
                        keys = None
                        if not self.measurement_records_stats_dict_keys:
                            keys = sorted(stats_dict.keys(), reverse=True)
                        for min_spacing_khz in sorted(spacing_counting_dict.keys()):
                            spacing_str = F"{np.round(min_spacing_khz)}_khz"
                            for collision_type in sorted(spacing_counting_dict[min_spacing_khz].keys()):
                                stats_key = F"{spacing_str}_{collision_type}_count"
                                stats_dict[stats_key] = spacing_counting_dict[min_spacing_khz][collision_type]
                                if keys is not None:
                                    keys.append(stats_key)
                            for flag_type in sorted(flag_counting_dict[min_spacing_khz].keys()):
                                flags_key = F"{spacing_str}_{flag_type}_flags_count"
                                stats_dict[flags_key] = flag_counting_dict[min_spacing_khz][flag_type]
                                if keys is not None:
                                    keys.append(flags_key)
                        if keys is not None:
                            self.measurement_records_stats_dict_keys = keys
                        # harvest some metadata
                        # the calculated metadata
                        calc_metadata_all_res = []
                        for f_record in frequency_records_ordered:
                            lambda_path = f_record.lambda_path
                            lambda_data_this_lap = self.lamb_params_data[lambda_path]
                            power_int_and_metadata = []
                            for power_int_dbm, CalcMetadataAtNeg in power_ints_and_mata_data_classes:
                                power_str = power_to_power_str(power_int_dbm)
                                metadata_strs = [power_str_and_column_name_to_metadata_str(power_str, column_name)
                                                 for column_name in calc_metadata_header]
                                calc_meta_data_dict = {column_name: lambda_data_this_lap.metadata[metadata_str]
                                                       for metadata_str, column_name
                                                       in zip(metadata_strs, calc_metadata_header)
                                                       if metadata_str in lambda_data_this_lap.metadata.keys()}
                                power_int_and_metadata.append((power_str, CalcMetadataAtNeg(**calc_meta_data_dict)))

                            calc_metadata_all_res.append(power_int_and_metadata)
                        # get all the chip together in a chip level class
                        rank_data = (port_power_dbm, seed_name)
                        chip_data = PhysicalChipData(wafer_and_chip_id=wafer_and_chip_id, group_id=group_id,
                                                     rank_data=rank_data,
                                                     frequency_records_ordered=order_updated_records,
                                                     stats_dict=stats_dict,
                                                     frequency_spacing_acceptance=acceptance_list,
                                                     calc_metadata_all_res=calc_metadata_all_res)
                        # save this data record for output
                        self.measurement_records.append(chip_data)
                        # get a per device data object
                        if wafer_and_chip_id not in device_records.keys() \
                                or device_records[wafer_and_chip_id].rank_data < rank_data:
                            device_records[wafer_and_chip_id] = chip_data
        self.spacing_dict_keys = sorted(spacing_dict_types)
        # order the chip records
        self.device_records = []
        for wafer_and_chip_id in sorted(device_records.keys()):
            self.device_records.append(device_records[wafer_and_chip_id])

    def write_csv(self, do_device_scale=True, do_measurement_scale=True):
        output_lists = []
        summary_file_names = []
        stats_filenames = []
        if do_device_scale:
            output_lists.append(self.device_records)
            summary_file_names.append(self.device_records_cvs_path)
            stats_filenames.append(self.device_stats_cvs_path)
        if do_measurement_scale:
            output_lists.append(self.measurement_records)
            summary_file_names.append(self.measurement_records_cvs_path)
            stats_filenames.append(self.measurement_stats_cvs_path)
        # outer loop to write all file types
        if self.records_column_names is None:
            header_pcd = PhysicalChipData(wafer_and_chip_id=None, group_id=None, rank_data=None)
            header_pcd.update_header(spacing_acceptance=self.spacing_dict_keys,
                                     stats=self.measurement_records_stats_dict_keys)

            self.records_column_names = header_pcd.records_column_names
            self.stats_columns = header_pcd.stats_columns
        # here is a place to edit the columns before they are written out

        # make the header
        stats_header = ""
        for stats_column in self.stats_columns:
            stats_header += F"{stats_column},"
        stats_header = stats_header[:-1] + '\n'
        records_header = ''
        for records_column in self.records_column_names:
            records_header += F"{records_column},"
        records_header = records_header[:-1] + '\n'
        # Write the file
        for output_list, summary_path, stats_path in zip(output_lists, summary_file_names, stats_filenames):
            with open(stats_path, 'w') as f_stats, open(summary_path, 'w') as f_csv:
                # write out the header lines
                f_stats.write(stats_header)
                f_csv.write(records_header)
                for physical_chip_data in output_list:
                    # write the stats line
                    f_stats.write(physical_chip_data.stats_str(stats_columns=self.stats_columns).replace('None', 'null'))
                    # write all the lines for each resonators in this group
                    f_csv.write(physical_chip_data.records_str(records_column_names=self.records_column_names)
                                .replace('None', 'null'))

    def frequency_report(self, do_device_scale=True, do_measurement_scale=True):
        self.do_frequencies_analysis()
        self.write_csv(do_device_scale=do_device_scale, do_measurement_scale=do_measurement_scale)
        if do_device_scale:
            frequencies_plot(self.device_records, plot_path=self.device_plot_path)
        if do_measurement_scale:
            frequencies_plot(self.measurement_records, plot_path=self.measurement_plot_path)


def standard_summary_report_plots(start_date=None, end_date=None, lamb_explore=None, get_temperatures=False):
    if lamb_explore is None:
        lamb_explore = LambExplore(start_date=start_date, end_date=end_date, get_temperatures=get_temperatures)
    lamb_explore.organize(structure_key="swb")
    lamb_explore.organize(structure_key="wbs")
    lamb_explore.summary_reports(multi_page_summary=True, show=False)
    return lamb_explore


def frequency_report_plot(start_date=None, end_date=None, lamb_explore=None):
    if lamb_explore is None:
        lamb_explore = LambExplore(start_date=start_date, end_date=end_date)
    lamb_explore.frequency_report()
    lamb_explore.organize(structure_key="swb")
    lamb_explore.organize(structure_key="wbs")
    return lamb_explore


def full_analysis(start_date=None, end_date=None, lamb_explore=None,
                  do_device_scale=True, do_measurement_scale=True):
    if lamb_explore is None:
        lamb_explore = LambExplore(start_date=start_date, end_date=end_date)
    # lamb_explore.do_frequencies_analysis()
    lamb_explore.frequency_report(do_device_scale=do_device_scale, do_measurement_scale=do_measurement_scale)
    lamb_explore.organize(structure_key="swb")
    lamb_explore.organize(structure_key="wbs")
    lamb_explore.summary_reports(multi_page_summary=True, show=False)
    lamb_explore.do_frequencies_analysis()
    lamb_explore.write_csv(do_device_scale=do_device_scale, do_measurement_scale=do_measurement_scale)
    return lamb_explore


if __name__ == "__main__":
    do_summary_report_plots = False
    do_frequency_report_plot = False

    example_start_date = datetime.date(year=2020, month=5, day=1)
    example_end_date = datetime.date(year=2022, month=5, day=30)

    example_lamb_explore = None
    if do_summary_report_plots:
        example_lamb_explore = standard_summary_report_plots(start_date=example_start_date, end_date=example_end_date,
                                                             lamb_explore=example_lamb_explore, get_temperatures=False)

    if do_frequency_report_plot:
        example_lamb_explore = frequency_report_plot(start_date=example_start_date, end_date=example_end_date,
                                                     lamb_explore=example_lamb_explore)

    if all([not do_summary_report_plots, not do_frequency_report_plot]):
        full_analysis(start_date=example_start_date, end_date=example_end_date, lamb_explore=example_lamb_explore,
                      do_device_scale=True, do_measurement_scale=True)
