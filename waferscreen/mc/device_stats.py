import os
import numpy as np
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from ref import device_summaries_dir
from waferscreen.mc.explore import LambExplore
from waferscreen.data_io.table_read import row_dict


def yield_fraction_bars(f_khz, **kwargs):
    pass


class DeviceStats:
    # these toggle different behavior when squashing data by wafer or chip
    id_match_strs = {'id', 'wafer'}
    float_match_strs = {'f_'}
    count_match_strs = {'count'}

    def __init__(self):
        # Reads the csv file data into a dictionary with each row of data paired with a unique group_id.
        # Each row of data is a dictionary with column names paired with the data values
        self.device_stats, self.data_columns = row_dict(filename=LambExplore.device_stats_cvs_path, key='group_id',
                                                        delimiter=",", null_value=None, inner_key_remove=False,
                                                        return_keys=True)
        # sort the different types of data id columns
        self.id_columns = {column_name for column_name in self.data_columns
                           if any([match in column_name for match in self.id_match_strs])}
        self.float_columns = {column_name for column_name in self.data_columns
                              if any([match in column_name for match in self.float_match_strs])}
        self.count_columns = {column_name for column_name in self.data_columns
                              if any([match in column_name for match in self.count_match_strs])}
        # sort the data by wafer
        self.device_stats_by_wafer = {}
        for group_id in self.device_stats.keys():
            chip_row = self.device_stats[group_id]
            wafer_num = chip_row['wafer']
            if wafer_num not in self.device_stats_by_wafer.keys():
                self.device_stats_by_wafer[wafer_num] = {}
            self.device_stats_by_wafer[wafer_num][group_id] = chip_row
    #


if __name__ == '__main__':
    device_stats = DeviceStats()
