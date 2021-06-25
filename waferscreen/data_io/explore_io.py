# Copyright (C) 2018 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.
import numpy as np
from waferscreen.data_io.flags import Flagger
from typing import NamedTuple, Optional


def wafer_num_to_str(wafer_num):
    return F"Wafer{'%03i' % wafer_num}"


def wafer_str_to_num(wafer_str):
    return int(wafer_str.lower().replace("wafer", ""))


def res_num_to_str(res_num):
    return F"Res{'%04i' % res_num}"


def band_str_to_num(band_str):
    return int(band_str.lower().replace('band', ''))


def band_num_to_str(band_num):
    return F"Band{'%02i' % band_num}"


def pos_str_to_nums(pos_str):
    if ',' in pos_str:
        delimiter = ','
    elif '&' in pos_str:
        delimiter = '&'
    else:
        raise KeyError(F"delimiter not recognized in: {pos_str}")
    x_pos_str, y_pos_str = pos_str.replace("(", "").replace(")", "").replace(" ", "").split(delimiter)
    return float(x_pos_str), float(y_pos_str)


def chip_id_str_to_chip_id_tuple(chip_id_str):
    if "_(" in chip_id_str:
        band_str, pos_str = chip_id_str.split("_", 1)
        band_num = band_str_to_num(band_str=band_str)
        x_pos, y_pos = pos_str_to_nums(pos_str=pos_str)
        return band_num, x_pos, y_pos
    else:
        # just a band
        return band_str_to_num(band_str=chip_id_str), None, None


def chip_id_tuple_to_chip_id_str(chip_id_tuple):
    band_num = chip_id_tuple[0]
    x_pos = chip_id_tuple[1]
    y_pos = chip_id_tuple[2]
    if band_num is None:
        chip_id_str = ""
    else:
        chip_id_str = band_num_to_str(band_num=band_num)
    if x_pos is None or y_pos is None:
        pass
    else:
        chip_id_str += F"_({'%1.3f' % x_pos},{'%1.3f' % y_pos})"
    if chip_id_str == "":
        raise TypeError("chip_id must be identified by a band_num and/or x_position and y_position," + \
                        " all are 'None' in this instance")
    return chip_id_str


def chip_id_handle_chip_id_str(chip_id_handle):
    if "_" in chip_id_handle:
        band_str, pos_handle_str = chip_id_handle.split("_")
        pos_str = pos_handle_str.replace("neg", "-").replace("and", ",")
        return F"{band_str}_({pos_str})"
    else:
        # this handle is only a band_str
        return chip_id_handle


def chip_id_str_to_chip_id_handle(chip_id_str):
    if "_(" in chip_id_str:
        chip_id_handle = chip_id_str.replace(",", 'and').replace("(", "").replace(")", "").replace("-", "neg")
        return chip_id_handle
    else:
        # this chip id is only a band number
        return chip_id_str


def seed_name_to_handle(seed_base):
    return seed_base.replace("-", "_").replace(".", "point")


def power_to_power_str(power_dbm):
    return F"{int(np.round(power_dbm))}dbm"


def power_str_and_column_name_to_metadata_str(power_str, column_name):
    return F"{column_name}_at{power_str}".replace('-', '_minus')


id_frequency_report_entry_header = ['record_id', "device_id", "group_id", 'wafer_and_chip_id']
required_frequency_report_entry_header = ['lambda_path', 'f_ghz', 'so_band', 'is_in_band', 'is_in_keepout']
optional_frequency_report_entry_header = ['res_num', 'designed_f_ghz', 'x_pos_mm_on_chip', 'y_pos_mm_on_chip',
                                          'resonator_height_um', 'wiggles', 'sliders', 'slider_delta_um',
                                          'resonator_impedance_ohms', 'coupling_capacitance_f',
                                          'coupling_inductance_h', 'adr_fiftymk_k',
                                          'group_num', 'flags']

frequency_report_entry_header = []
[frequency_report_entry_header.extend(column_names) for column_names in [id_frequency_report_entry_header,
                                                                         required_frequency_report_entry_header,
                                                                         optional_frequency_report_entry_header]]
frequency_report_columns = set(frequency_report_entry_header)


class FrequencyReportEntry(NamedTuple):
    f_ghz: float
    so_band: int
    is_in_band: bool
    is_in_keepout: bool
    lambda_path: str
    res_num: Optional[int] = None
    designed_f_ghz: Optional[float] = None
    x_pos_mm_on_chip: Optional[float] = None
    y_pos_mm_on_chip: Optional[float] = None
    group_num: Optional[int] = None
    flags: Optional[str] = None
    record_id: Optional[str] = None
    device_id: Optional[str] = None
    group_id: Optional[str] = None
    wafer_and_chip_id: Optional[str] = None
    resonator_height_um: Optional[float] = None
    wiggles: Optional[float] = None
    sliders: Optional[float] = None
    slider_delta_um: Optional[float] = None
    resonator_impedance_ohms: Optional[float] = None
    coupling_capacitance_f: Optional[float] = None
    coupling_inductance_h: Optional[float] = None
    adr_fiftymk_k: Optional[float] = None

    def __str__(self):
        return_str = ""
        for var_name in frequency_report_entry_header:
            return_str += F"{self.__getattribute__(var_name)},"
        # get rid of the last comma ","
        return return_str[:-1]


calc_metadata_header = ['lamb', 'lamb_err', 'flux_ramp_pp_khz', 'flux_ramp_pp_khz_err',
                        'fr_squid_mi_pH', 'fr_squid_mi_pH_err',
                        'chi_squared', 'q_i_mean', 'q_i_std', 'q_c_mean', 'q_c_std', 'impedance_ratio_mean']


class CalcMetadata(NamedTuple):
    lamb: Optional[float] = None
    lamb_err: Optional[float] = None
    flux_ramp_pp_khz: Optional[float] = None
    flux_ramp_pp_khz_err: Optional[float] = None
    fr_squid_mi_pH: Optional[float] = None
    fr_squid_mi_pH_err: Optional[float] = None
    chi_squared: Optional[float] = None
    q_i_mean: Optional[float] = None
    q_i_std: Optional[float] = None
    q_c_mean: Optional[float] = None
    q_c_std: Optional[float] = None
    impedance_ratio_mean: Optional[float] = None

    def __str__(self):
        return_str = ""
        for var_name in calc_metadata_header:
            return_str += F"{self.__getattribute__(var_name)},"
        # get rid of the last comma ","
        return return_str[:-1]


class CalcMetadataAtNeg95dbm(CalcMetadata):
    est_device_power_dbm = -95.0


class CalcMetadataAtNeg75dbm(CalcMetadata):
    est_device_power_dbm = -75.0


power_ints_and_mata_data_classes = [(-95, CalcMetadataAtNeg95dbm), (-75, CalcMetadataAtNeg75dbm)]

power_strs = [power_to_power_str(power_int) for power_int, CalcMetadataAt in power_ints_and_mata_data_classes]
calc_metadata_header_full = []
for power_str in power_strs:
    for column_name in calc_metadata_header:
        calc_metadata_header_full.append(power_str_and_column_name_to_metadata_str(power_str=power_str,
                                                                                   column_name=column_name))


class PhysicalChipData:
    records_column_names = list(frequency_report_entry_header)
    records_column_names.extend(['wafer', 'chip_id'])
    records_column_names.extend(calc_metadata_header_full)
    records_header = ''
    for column in records_column_names:
        records_header += F"{column},"
    records_header = records_header[:-1] + '\n'
    stats_columns = ['group_id', 'wafer_and_chip_id', 'wafer', 'chip_id']
    stats_header = "group_id,wafer_and_chip_id,wafer,chip_id\n"
    spacing_acceptance_column_names = []

    def __init__(self, wafer_and_chip_id, group_id, rank_data,
                 frequency_records_ordered=None, stats_dict=None,
                 frequency_spacing_acceptance=None,
                 calc_metadata_all_res=None):
        # record data
        self.frequency_records_ordered = frequency_records_ordered
        self.stats_dict = stats_dict
        self.frequency_spacing_acceptance = frequency_spacing_acceptance
        # calculated metadata at specific powers, reshape to one dict per resonator
        if calc_metadata_all_res is None:
            self.calc_metadata_all_res = None
        else:
            self.calc_metadata_all_res = []
            for per_power_calc_metadata_this_res in calc_metadata_all_res:
                calc_metadata_this_res = {}
                for power_str, calc_metadata_at_power in per_power_calc_metadata_this_res:
                    for column_name in calc_metadata_header:
                        md_str = power_str_and_column_name_to_metadata_str(power_str=power_str, column_name=column_name)
                        calc_metadata_this_res[md_str] = calc_metadata_at_power.__getattribute__(column_name)
                self.calc_metadata_all_res.append(calc_metadata_this_res)
        # for quick reference and sorting
        self.wafer_and_chip_id = wafer_and_chip_id
        if self.frequency_records_ordered is None:
            self.group_num = None
        else:
            self.group_num = self.frequency_records_ordered[0].group_num
        if wafer_and_chip_id is None:
            self.wafer_num = None
            self.chip_id_str = None
        else:
            wafer_str, self.chip_id_str = wafer_and_chip_id.split("|")
            self.wafer_num = wafer_str_to_num(wafer_str=wafer_str)
        if self.chip_id_str is None:
            self.so_band = None
        else:
            self.so_band, *_chip_pos = chip_id_str_to_chip_id_tuple(self.chip_id_str)
        self.group_id = group_id
        self.rank_data = rank_data

        # organization
        if stats_dict is None:
            self.stats_dict = {}
        self.stats_dict['group_id'] = self.group_id
        self.stats_dict['wafer_and_chip_id'] = self.wafer_and_chip_id
        self.stats_dict['wafer'] = self.wafer_num
        self.stats_dict['chip_id'] = self.chip_id_str

    def update_header(self, spacing_acceptance=None, stats=None):
        if spacing_acceptance is not None:
            self.spacing_acceptance_column_names.extend(list(spacing_acceptance))
            new_records_header = self.records_header.rstrip("\n")
            for item in spacing_acceptance:
                new_records_header += F",{item}"
                self.records_column_names.append(str(item))
            self.records_header = F"{new_records_header}\n"
        if stats is not None:
            new_stats_header = self.stats_header.rstrip("\n")
            for item in stats:
                new_stats_header += F",{item}"
                self.stats_columns.append(str(item))
            self.stats_header = F"{new_stats_header}\n"

    def records_str(self, records_column_names=None):
        if records_column_names is None:
            records_column_names = self.records_column_names
        output_str = ''
        for f_record, spacing_acceptance, calc_metadata in zip(self.frequency_records_ordered,
                                                               self.frequency_spacing_acceptance,
                                                               self.calc_metadata_all_res):
            combined_data_dict = {'wafer': self.wafer_num, 'chip_id': self.chip_id_str}
            for f_record_column in frequency_report_entry_header:
                combined_data_dict[f_record_column] = f_record.__getattribute__(f_record_column)
            for spacing_column in self.spacing_acceptance_column_names:
                combined_data_dict[spacing_column] = spacing_acceptance[spacing_column]
            for calc_metadata_column in calc_metadata_header_full:
                combined_data_dict[calc_metadata_column] = calc_metadata[calc_metadata_column]
            for column_name in records_column_names:
                output_str += F"{combined_data_dict[column_name]},"
            output_str = output_str[:-1] + '\n'
        return output_str

    def stats_str(self, stats_columns=None):
        if stats_columns is None:
            stats_columns = self.stats_columns
        output_str = ''
        for column_name in stats_columns:
            output_str += F"{self.stats_dict[column_name]},"
        return output_str[:-1] + '\n'


flagged_data = Flagger()
flagged_data.read()
flagged_data.organize()
