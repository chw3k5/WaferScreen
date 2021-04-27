# Copyright (C) 2018 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

from waferscreen.data_io.flags import Flagger


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


def chip_id_str_to_band_and_pos(chip_id_str):
    if "_(" in chip_id_str:
        band_str, pos_str = chip_id_str.split("_", 1)
        band_num = band_str_to_num(band_str=band_str)
        x_pos, y_pos = pos_str_to_nums(pos_str=pos_str)
        return band_num, x_pos, y_pos
    else:
        # just a band_str
        return band_str_to_num(band_str=chip_id_str), None, None


def seed_name_to_handle(seed_base):
    return seed_base.replace("-", "_").replace(".", "point")


flagged_data = Flagger()
flagged_data.read()
flagged_data.organize()
