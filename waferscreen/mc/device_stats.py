import os
import numpy as np
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from ref import device_stats_dir, min_spacings_khz
from waferscreen.mc.explore import LambExplore
from waferscreen.data_io.table_read import row_dict

hatches = ['/', '*', '|', '\\', 'x', 'o', '-', '.', '0', '+']
len_hatches = len(hatches)
series_plot_order = ['none', 'left', 'both', 'right']
series_plot_colors = ['Chartreuse', 'darkorchid', 'firebrick', 'dodgerblue']
all_flags_plot_order = ['none', 'criteria', 'both', 'spacing']
all_flags_plot_colors = ['green', 'yellow', 'red', 'blue']


def yield_fraction_bars(ax, series_flags, series_of_all_flags):
    bar_width = 0.4
    number_of_bars = 2.0
    # sort the data for stacked and multi-line bar graph
    series_plot_data = []
    series_plot_data_labels = []
    all_flags_plot_data = []
    all_flags_plot_data_labels = []
    labels = []
    for series_key in sorted(series_flags.keys(), reverse=True):
        # collect series data
        labels.append(F"{int(np.round(series_key))} kHz")
        total_flag_counts = []
        running_sums_flag_counts = []
        running_sum = 0
        flag_counts = series_flags[series_key]
        for key in series_plot_order:
            count_datum = flag_counts[key]
            total_flag_counts.append(count_datum)
            running_sum += count_datum
            running_sums_flag_counts.append(running_sum)
        series_plot_data_labels.append(total_flag_counts)
        series_plot_data.append(running_sums_flag_counts)
        # all flags summary data
        total_summary_flag_counts = []
        running_sums_flags_summary_counts = []
        running_sum = 0
        flags_summary_counts = series_of_all_flags[series_key]
        for key in all_flags_plot_order:
            count_datum = flags_summary_counts[key]
            total_summary_flag_counts.append(count_datum)
            running_sum += count_datum
            running_sums_flags_summary_counts.append(running_sum)
        all_flags_plot_data_labels.append(total_summary_flag_counts)
        all_flags_plot_data.append(running_sums_flags_summary_counts)

    # plot the data
    bar_group_centers = np.arange(len(labels))
    # all flags summary
    bar_centers = bar_group_centers - (1.0 / number_of_bars) * bar_width - 0.02
    bottom_data = [0] * len(series_flags)
    for key_index, key in list(enumerate(all_flags_plot_order)):
        heights_this_layer = [all_flags_plot_data[series_index][key_index] for series_index in range(len(series_flags))]
        text_this_layer = [all_flags_plot_data_labels[series_index][key_index]
                           for series_index in range(len(series_flags))]
        if key == 'both':
            label = F"criteria and spacing"
        elif key == 'criteria':
            label = F"only criteria flags"
        elif key == 'spacing':
            label = F"only spacing flags"
        else:
            label = F"no flags"
        ax.bar(bar_centers, height=text_this_layer, width=bar_width, bottom=bottom_data,
               color=all_flags_plot_colors[key_index], label=label)
        for text, height, bar_center in zip(text_this_layer, heights_this_layer, bar_centers):
            ax.text(x=bar_center, y=height, s=F"{'%i' % text}", ha='center', va='top', color='white')
        bottom_data = heights_this_layer
    # spacing flags
    bar_centers = bar_group_centers + (1.0 / number_of_bars) * bar_width + 0.02
    bottom_data = [0] * len(series_flags)
    for key_index, key in list(enumerate(series_plot_order)):
        heights_this_layer = [series_plot_data[series_index][key_index] for series_index in range(len(series_flags))]
        text_this_layer = [series_plot_data_labels[series_index][key_index]
                           for series_index in range(len(series_flags))]
        if key == 'both':
            label = F"{key} neighbors too close"
        elif key == 'none':
            label = 'no spacing flags'
        else:
            label = F"{key} neighbor too close"
        ax.bar(bar_centers, height=text_this_layer, width=bar_width, bottom=bottom_data,
               color=series_plot_colors[key_index], hatch=hatches[key_index % len_hatches],
               label=label)
        for text, height, bar_center in zip(text_this_layer, heights_this_layer, bar_centers):
            if int(text) != 0:
                ax.text(x=bar_center, y=height, s=F"{'%i' % text}", ha='center', va='top', color='white')
        bottom_data = heights_this_layer

    # finishing plot and output
    ax.set_xticks(bar_group_centers)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Minimum Spacing Criteria")
    ax.set_ylabel("Measured Resonators")
    ax.legend(loc=4, numpoints=5, handlelength=3, fontsize=12)
    return ax


class DeviceStats:
    # these toggle different behavior when squashing data by wafer or chip
    id_match_strs = {'id', 'wafer'}
    float_match_strs = {'f_'}
    count_match_strs = {'count'}

    def __init__(self, plot_dir=None, min_spacings_khz_to_plot=None):
        if plot_dir is None:
            self.plot_dir = device_stats_dir
        else:
            self.plot_dir = plot_dir
        if min_spacings_khz_to_plot is None:
            self.min_spacings_khz = min_spacings_khz
        else:
            self.min_spacings_khz = min_spacings_khz_to_plot
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
        self.available_wafer_nums = set(self.device_stats_by_wafer.keys())
        # summarize the data by wafer
        self.wafer_stats = {}
        for wafer_num in sorted(self.available_wafer_nums):
            # initialize the summary data dictionary
            self.wafer_stats[wafer_num] = {}
            # id columns are sets
            for id_column in self.id_columns:
                self.wafer_stats[wafer_num][id_column] = set()
            # float_columns are means and get set at the end, for now collect data as list
            for float_column in self.float_columns:
                self.wafer_stats[wafer_num][float_column] = []
            # count columns need to be initialized at zero
            for count_column in self.count_columns:
                self.wafer_stats[wafer_num][count_column] = 0
            # get all the device stats for this wafer
            device_stats_this_wafer = self.device_stats_by_wafer[wafer_num]
            for group_id in device_stats_this_wafer.keys():
                device_stats_single_chip = device_stats_this_wafer[group_id]
                # add values to the sets for idea columns
                [self.wafer_stats[wafer_num][id_column].add(device_stats_single_chip[id_column])
                 for id_column in self.id_columns]
                # append to float_columns
                [self.wafer_stats[wafer_num][float_column].append(device_stats_single_chip[float_column])
                 for float_column in self.float_columns]
                # add count for the counts columns
                for count_column in self.count_columns:
                    self.wafer_stats[wafer_num][count_column] += device_stats_single_chip[count_column]
            # finish float columns  as simple means
            for float_column in self.float_columns:
                self.wafer_stats[wafer_num][float_column] = np.mean(self.wafer_stats[wafer_num][float_column])
        # sort the data by chip
        self.device_stats_by_chip = {}
        for group_id in self.device_stats.keys():
            chip_row = self.device_stats[group_id]
            chip_id = chip_row['chip_id']
            if chip_id not in self.device_stats_by_chip.keys():
                self.device_stats_by_chip[chip_id] = {}
            self.device_stats_by_chip[chip_id][group_id] = chip_row
        self.available_chip_ids = set(self.device_stats_by_chip.keys())

    def wafer_yield_study(self):
        """
        Make a single pdf of plot, one wafer per page, each page is a trade study of yield as a function of
        resonator spacing.
        :return:
        """
        # default figure settings
        figure_size = (12, 8)
        frameon = False
        left_ax_margin = 0.10
        right_ax_margin = 0.00
        bottom_ax_margin = 0.08
        top_ax_margin = 0.04
        width = 1.0 - left_ax_margin - right_ax_margin
        height = 1.0 - bottom_ax_margin - top_ax_margin
        axis_in_figure_coord = [left_ax_margin, bottom_ax_margin, width, height]
        # set the output plot's filename
        wafer_yield_study_path = os.path.join(self.plot_dir, 'by_wafer_yield_study.pdf')
        # open the context manager for pdf plots so it will close gracefully if there is an exception
        with PdfPages(wafer_yield_study_path) as pdf_pages:
            # start the wafer number loops
            for wafer_num in sorted(self.available_wafer_nums):
                # extract the wafer data
                wafer_summary = self.wafer_stats[wafer_num]
                flags_keys = {column for column in self.count_columns if '_flags_' in column}
                spacing_keys = self.count_columns - flags_keys
                flags = {flag_key.replace('_flags_count', ''): wafer_summary[flag_key] for flag_key in flags_keys}
                spacings = {spacing_key.replace('_count', ''): wafer_summary[spacing_key]
                            for spacing_key in spacing_keys}
                # 1-figure (page) per wafer, initialize
                fig_this_wafer = plt.figure(figsize=figure_size)
                ax_this_wafer = fig_this_wafer.add_axes(axis_in_figure_coord, frameon=frameon)
                series_of_all_flags = {}
                series_of_spacings = {}
                for spacing_khz in sorted(self.min_spacings_khz):
                    # get only the flag data that relates to this spacing,
                    # simplify the dictionary keys to remove repeated information
                    spacing_match_str = F"{'%1.1f' % spacing_khz}_khz_"
                    flags_this_spacing = {flag_key.replace(spacing_match_str, ''): flags[flag_key]
                                          for flag_key in flags.keys() if spacing_match_str in flag_key}
                    this_spacing = {spacing_key.replace(spacing_match_str, ''): spacings[spacing_key]
                                    for spacing_key in spacings.keys() if spacing_match_str in spacing_key}
                    series_of_all_flags[spacing_khz] = flags_this_spacing
                    series_of_spacings[spacing_khz] = this_spacing
                # send this data to the plot function
                ax_this_wafer = yield_fraction_bars(ax=ax_this_wafer, series_flags=series_of_spacings,
                                                    series_of_all_flags=series_of_all_flags)
                plt.suptitle(F"Wafer{'%03i' % wafer_num}")
                # save this figure (page) to the plot output
                pdf_pages.savefig(fig_this_wafer)
                # close all the figures and free up the resources
                plt.close(fig=fig_this_wafer)


if __name__ == '__main__':
    device_stats = DeviceStats()
    device_stats.wafer_yield_study()
