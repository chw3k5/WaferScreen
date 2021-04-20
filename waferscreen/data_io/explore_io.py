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


def seed_name_to_handle(seed_base):
    return seed_base.replace("-", "_").replace(".", "point")


flagged_data = Flagger()
flagged_data.read()
flagged_data.organize()
