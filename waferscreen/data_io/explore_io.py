# Copyright (C) 2018 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

from waferscreen.data_io.flags import Flagger
from typing import NamedTuple


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
    x_pos_str, y_pos_str = pos_str.replace("(", "").replace(")", "").replace(" ", "").split(",")
    return float(x_pos_str), float(y_pos_str)


def chip_id_str_to_chip_id_tuple(chip_id_str):
    if "_(" in chip_id_str:
        band_str, pos_str = chip_id_str.split("_", 1)
        band_num = band_str_to_num(band_str=band_str)
        x_pos, y_pos = pos_str_to_nums(pos_str=pos_str)
        return band_num, x_pos, y_pos
    else:
        # just a band_str
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


frequency_report_entry_header = ['f_ghz', 'so_band', 'is_in_band', 'is_in_keepout']


class FrequencyReportEntry(NamedTuple):
    f_ghz: float
    so_band: int
    is_in_band: bool
    is_in_keepout: bool

    def __str__(self):
        return F"{self.f_ghz},{self.so_band},{self.is_in_band},{self.is_in_keepout}"


flagged_data = Flagger()
flagged_data.read()
flagged_data.organize()
