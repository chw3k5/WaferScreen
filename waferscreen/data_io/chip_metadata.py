import os
from typing import NamedTuple
from operator import itemgetter
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from waferscreen.data_io.s21_metadata import MetaDataDict, num_format
from ref import chip_per_band_metadata, wafer_pos_metadata, layout_dir


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
    group_colors = {1: 'dodgerblue', 2: 'firebrick', 3: 'darkgoldenrod'}

    def __init__(self):
        self.path = wafer_pos_metadata
        self.wafer_range_to_layout = None
        self.default_layout_range = None
        self.read()

    def read(self):
        self.wafer_range_to_layout = {}
        with open(self.path, 'r') as f:
            raw_rows = [row.strip() for row in f.readlines()]
        header = raw_rows[0].split(',')
        wafer_range = (None, None)
        for row_data in raw_rows[1:]:
            # let different wafers have different layouts.
            if 'wafers:' in row_data.lower():
                wafer_str_min, wafer_str_max = row_data.lower().replace('wafers:', '').replace(' ', '').split('to')
                if wafer_str_max == 'max':
                    wafer_range = (float(wafer_str_min), float('inf'))
                    self.default_layout_range = wafer_range
                else:
                    wafer_range = (float(wafer_str_min), float(wafer_str_max))
                self.wafer_range_to_layout[wafer_range] = {'from_wafer_pos': {}, 'from_band_and_group': {}}
            else:
                # parse the rows of layout data.
                data_dict = {column: num_format(value) for column, value in zip(header, row_data.split(','))}
                x_pos = data_dict['x_pos']
                y_pos = data_dict['y_pos']
                so_band_num = data_dict['so_band_num']
                group_num = data_dict['group_num']
                self.wafer_range_to_layout[wafer_range]['from_wafer_pos'][(x_pos, y_pos)] = data_dict
                self.wafer_range_to_layout[wafer_range]['from_band_and_group'][(so_band_num, group_num)] = data_dict

    def get_range_from_wafer_num(self, wafer_num):
        for wafer_num_min, wafer_num_max in self.wafer_range_to_layout.keys():
            if wafer_num_min <= wafer_num <= wafer_num_max:
                return wafer_num_min, wafer_num_max
        else:
            raise KeyError(F"Wafer_num: {wafer_num}, is not with in the available layout ranges: {self.wafer_range_to_layout.keys()}.")

    def get_from_wafer_pos(self, x_pos, y_pos, wafer_num=None):
        if x_pos is None or y_pos is None:
            return None
        if wafer_num is None:
            wafer_layout_range = self.default_layout_range
        else:
            wafer_layout_range = self.get_range_from_wafer_num(wafer_num=wafer_num)
        layout_data = self.wafer_range_to_layout[wafer_layout_range]
        from_wafer_pos = layout_data['from_wafer_pos']
        pos_key = (int(x_pos), int(y_pos))
        if pos_key in from_wafer_pos.keys():
            return from_wafer_pos[pos_key]
        else:
            return None

    def from_pos_to_group_num(self, x_pos, y_pos, wafer_num=None):
        data_dict = self.get_from_wafer_pos(x_pos=x_pos, y_pos=y_pos, wafer_num=wafer_num)
        if data_dict is None:
            return None
        else:
            return data_dict['group_num']

    def get_from_band_and_group(self, so_band_num, group_num, wafer_num=None):
        if wafer_num is None:
            wafer_layout_range = self.default_layout_range
        else:
            wafer_layout_range = self.get_range_from_wafer_num(wafer_num=wafer_num)
        layout_data = self.wafer_range_to_layout[wafer_layout_range]
        from_band_and_group = layout_data['from_band_and_group']
        band_and_group_key = (int(so_band_num), int(group_num))
        if band_and_group_key in from_band_and_group.keys():
            return from_band_and_group[band_and_group_key]
        else:
            return None

    def plot(self, show=False):
        for wafer_num_min, wafer_num_max in sorted(self.wafer_range_to_layout.keys()):
            layout_data = self.wafer_range_to_layout[(wafer_num_min, wafer_num_max)]
            from_wafer_pos = layout_data['from_wafer_pos']
            if wafer_num_max == float('inf'):
                wafer_max_str = 'MAX'
            else:
                wafer_max_str = F"{'%i' % wafer_num_max}"
            plot_filename = F"ChipLayout_Wafers{'%i' % wafer_num_min}thru{wafer_max_str}.png"
            plot_path = os.path.join(layout_dir, plot_filename)
            fig = plt.figure(figsize=(8, 8))
            ax = fig.add_axes([0.05, 0.05, 0.9, 0.9], frame_on=False)
            for x_position, y_position in sorted(from_wafer_pos.keys()):
                layout_data_this_chip = from_wafer_pos[(x_position, y_position)]
                so_band_num = layout_data_this_chip['so_band_num']
                group_num = layout_data_this_chip['group_num']
                color = self.group_colors[group_num]
                ax.add_patch(Rectangle(xy=(x_position - 0.45, y_position - 0.45), width=0.9, height=0.9,
                                       facecolor=color))
                patch_text = F"({'%i' % x_position}, {'%i' % y_position}) Band{'%02i' % so_band_num} Group-{group_num}"
                ax.text(x=x_position, y=y_position, s=patch_text, color='black', ha='center', va='center')
            ax.set_xlim((-1.5, 1.5))
            ax.set_ylim((-7.5, 7.5))
            if show:
                plt.show(block=True)
            plt.savefig(plot_path)
            plt.close(fig=fig)


chip_metadata = ChipMetaData()
wafer_pos_to_band_and_group = WaferPosToBandAndGroup()
if __name__ == '__main__':
    wafer_pos_to_band_and_group.plot(show=True)
