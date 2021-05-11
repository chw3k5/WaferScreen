from typing import NamedTuple
from operator import itemgetter
from waferscreen.data_io.s21_metadata import MetaDataDict, num_format
from ref import chip_per_band_metadata, wafer_pos_metadata


class ChipMetaDataID(NamedTuple):
    so_band: int
    res_num_per_chip: int


class ChipMetaData:
    def __init__(self, path=None):
        # set the path for reading the raw data
        if path is None:
            path = chip_per_band_metadata
        self.path = path
        # initialized values
        self.by_band_res_num = None
        self.by_band = None
        # read the data from file
        self.read()

    def read(self):
        self.by_band_res_num = {}
        self.by_band = {}
        with open(self.path, 'r') as f:
            raw_lines = [a_line.strip() for a_line in f.readlines()]
        header = raw_lines[0].split(",")
        rows_of_values = raw_lines[1:]
        for a_row in rows_of_values:
            # format the data
            row_dict = MetaDataDict({column_name: num_format(value)
                                     for column_name, value in zip(header, a_row.split(","))})
            # this is reused often
            so_band_num = row_dict['so_band']
            # for the so_band, resonator number id dictionary.
            chip_metadata_id = ChipMetaDataID(so_band=so_band_num, res_num_per_chip=row_dict['res_num_per_chip'])
            self.by_band_res_num[chip_metadata_id] = row_dict
            # for the by_band dictionary
            if so_band_num not in self.by_band.keys():
                self.by_band[so_band_num] = []
            self.by_band[so_band_num].append(row_dict)
        # order the the by_band lists by resonator number
        for so_band_num in self.by_band.keys():
            res_data_by_band = self.by_band[so_band_num]
            self.by_band[so_band_num] = sorted(res_data_by_band, key=itemgetter("res_num_per_chip"))

    def return_res_metadata(self, so_band_num, res_num):
        chip_metadata_id = ChipMetaDataID(so_band=int(so_band_num), res_num_per_chip=int(res_num))
        if chip_metadata_id in self.by_band_res_num.keys():
            return self.by_band_res_num[chip_metadata_id]
        else:
            return None

    def return_band_metadata(self, so_band_num):
        so_band_num = int(so_band_num)
        if so_band_num in self.by_band.keys():
            return self.by_band[so_band_num]
        else:
            return None


class WaferPosToBandAndGroup:
    def __init__(self):
        self.path = wafer_pos_metadata
        self.from_wafer_pos = None
        self.from_band_and_group = None
        self.read()

    def read(self):
        self.from_wafer_pos = {}
        self.from_band_and_group = {}
        with open(self.path, 'r') as f:
            raw_rows = [row.strip() for row in f.readlines()]
        header = raw_rows[0].split(',')
        for row_data in raw_rows[1:]:
            data_dict = {column: num_format(value) for column, value in zip(header, row_data.split(','))}
            x_pos = data_dict['x_pos']
            y_pos = data_dict['y_pos']
            so_band_num = data_dict['so_band_num']
            group_num = data_dict['group_num']
            self.from_wafer_pos[(x_pos, y_pos)] = data_dict
            self.from_band_and_group[(so_band_num, group_num)] = data_dict

    def get_from_wafer_pos(self, x_pos, y_pos):
        if x_pos is None or y_pos is None:
            return None
        pos_key = (int(x_pos), int(y_pos))
        if pos_key in self.from_wafer_pos.keys():
            return self.from_wafer_pos[pos_key]
        else:
            return None

    def form_pos_to_group_num(self, x_pos, y_pos):
        data_dict = self.get_from_wafer_pos(x_pos=x_pos, y_pos=y_pos)
        if data_dict is None:
            return None
        else:
            return data_dict['group_num']

    def get_from_band_and_group(self, so_band_num, group_num):
        band_and_group_key = (int(so_band_num), int(group_num))
        if band_and_group_key in self.from_band_and_group.keys():
            return self.from_band_and_group[band_and_group_key]
        else:
            return None


chip_metadata = ChipMetaData()
wafer_pos_to_band_and_group = WaferPosToBandAndGroup()
