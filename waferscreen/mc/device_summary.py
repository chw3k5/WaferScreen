# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import os
import pandas
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
# only used to get input and output directory information
from ref import device_summaries_dir
from waferscreen.mc.explore import LambExplore


# A warning that we are changing and smaller version of a larger table
pandas.options.mode.chained_assignment = None  # default='warn'


# some optional customizable settings
# used in delta_f_plot() and histogram_per_wafer()
wafer_num_to_color_dict = {9: "seagreen", 11: "crimson", 12: "darkgoldenrod", 13: "deepskyblue", 14: "mediumblue",
                           15: "rebeccapurple", 16: "DarkOrange"}
# 'column_name': 'plot_label' for column names in device_summary.csv, used in histogram_per_wafer().
column_name_to_axis_label = {'lamb_at_minus95dbm': "Lambda (-95dBm est. at devices)",
                             'flux_ramp_pp_khz_at_minus95dbm': 'Flux Ramp peak-to-peak (kHz) (-95dBm est. at devices)',
                             'flux_ramp_pp_khz_at_minus75dbm': 'Flux Ramp peak-to-peak (kHz) (-75dBm est. at devices)',
                             'q_i_mean_at_minus75dbm': 'Qi (-75dBm est. at devices)',
                             'adr_fiftymk_k': 'Temperature (K) at ADR rod'}
# 'column_name': (num_histogram_bins, x_plot_min, x_plot_max) for column names in device_summary.csv,
#                                                             used in histogram_per_wafer().
column_name_to_range = {'flux_ramp_pp_khz_at_minus95dbm': (30, 0, 250),  # (num_histogram_bins, x_plot_min, x_plot_max)
                        'flux_ramp_pp_khz_at_minus75dbm': (30, 0, 250),
                        'lamb_at_minus95dbm': (60, 0.0, 0.7),
                        'adr_fiftymk_k': (50, 0.0, 0.300)}
hatches = ['/', '*', '|', '\\', 'x', 'o', '-', '.', '0', '+']
len_hatches = len(hatches)


def wafer_num_to_color(wafer_num):
    """
    A hack to make a color dictionary with a default value
    :param wafer_num: int
    :return: str - a matplotlib color
    """
    wafer_num = int(wafer_num)
    if wafer_num in wafer_num_to_color_dict.keys():
        return wafer_num_to_color_dict[wafer_num]
    return 'black'


def delta_f_plot(device_records, show=True, output_dir=None, markersize=30, fontsize=18):
    """
    A plot to show the difference in the designed frequency of a resonator from the resonator's measured frequency,
    or delta_f. The plot displays delta_f in MHz (y-axis) and as a function of designed frequency (x-axis).
    :param device_records: pandas.DataFrame - this data frame can be generated by importing the data in
                           device_summary.csv with the method pandas.read_csv() as follows:
                               pandas.read_csv(filepath_or_buffer='local_dir_path/device_summary.csv', index_col=0)
                           or on windows you need '\\':
                               pandas.read_csv(filepath_or_buffer='local_dir_path\\device_summary.csv', index_col=0)
    :param show: bool - show the plot in a pop-up window before exiting
    :param output_dir: str - the output path for the saved data plot.  None, the default, does not save a plot.
    :param markersize: float - the size of the data markers in the plot in points
    :param fontsize: float - the size of the label text in the plot in points
    :return: None
    """
    # get only the columns we are going to be working with
    subset_columns = device_records[["f_ghz", "designed_f_ghz", "wafer"]]
    # make a mask that reports true fro all rows of non-null data.
    not_null_row_mask = subset_columns.notnull().all(axis=1)
    # select all the data with no nulls in any of the rows
    delta_f = subset_columns[not_null_row_mask]
    # do a little math to make a new column the scatter plot
    delta_f['delta_f_mhz'] = delta_f['f_ghz'].sub(delta_f['designed_f_ghz']).mul(1.0e3)
    # map wafer number to color, also used in the scatter plot
    delta_f['wafer_color'] = delta_f['wafer'].map(wafer_num_to_color, na_action='ignore')
    # Figure init, figure width and height in inches
    fig = plt.figure(figsize=(25, 10))
    # figure coordinates for the the plot axis (ax) [left, bottom, width, height]
    coor = [0.04, 0.09, 0.94, 0.9]
    # init the scatter plot axis, I like to turn the plot frame off, gives the plots a modern look
    ax = fig.add_axes(coor, frameon=False)
    for wafer_num in sorted(wafer_num_to_color_dict.keys()):
        # get the subset of the data frame where the wafer_num is equal to the wafer value in the data
        sub_dataframe_per_wafer = delta_f.loc[delta_f['wafer'] == wafer_num]
        # plot the data
        ax.scatter(sub_dataframe_per_wafer['designed_f_ghz'], sub_dataframe_per_wafer['delta_f_mhz'],
                   c=wafer_num_to_color_dict[wafer_num], s=markersize,
                   label=F"Wafer{'%03i' % wafer_num}")
    # show the data legend
    ax.legend(loc=0, numpoints=5, handlelength=3, fontsize=fontsize)
    # set the axis labels
    ax.set_ylabel('Measured - Designed (MHz)', size=fontsize)
    ax.set_xlabel('Designed Frequency (GHz)', size=fontsize)
    # save the plot
    if output_dir is not None:
        plot_path = os.path.join(output_dir, "delta_f_per_wafer.pdf")
        plt.savefig(plot_path)
        print(F"  Plot saved: {plot_path}")
    # show the plot
    if show:
        plt.show(block=True)
    # close the plot and let the memory be free
    plt.close(fig=fig)


def user_hist(x, num_of_bins=50):
    """
    A custom histogram function. Returns data needed to make a histogram plot

    :param x: iterable - the data to sort and bin
    :param num_of_bins: int - the number of bins to use
    :return: hist, bins, width, centers
    """
    hist, bins = np.histogram(x, bins=num_of_bins)
    width = np.diff(bins)
    centers = (bins[:-1] + bins[1:]) / 2
    return hist, bins, width, centers


def histogram_per_wafer(device_records, column_name="lamb_at_minus95dbm", show=True, output_dir=None, num_of_bins=50,
                        alpha=0.5, linewidth=3, fontsize=24):
    """
    Make histograms as a function of wafer for any column of number data in device_summary.csv.

    See the optional settings after the import statements in this file to define custom axis labels and other
    plot configuration settings.

    :param device_records: pandas.DataFrame - this data frame can be generated by importing the data in
                           device_summary.csv with the method pandas.read_csv() as follows:
                               pandas.read_csv(filepath_or_buffer='local_dir_path/device_summary.csv', index_col=0)
                           or on windows you need '\\':
                               pandas.read_csv(filepath_or_buffer='local_dir_path\\device_summary.csv', index_col=0)
    :param column_name: str - the column in device_summary.csv
    :param show: bool - show the plot in a pop-up window before exiting
    :param output_dir: str - the output path for the saved data plot. None, the default, does not save a plot.
    :param num_of_bins: int - number of histograms bins, Note: this value is overridden if column_name is in
                              column_name_to_range.keys() as defined at the top of this file.
    :param alpha: float - 0.0 (invisible) to 1.0 (opaque) to control the transparency of the
                          bar graphs of the histograms.
    :param linewidth: float - the size of the boarder line the defines the outside of bars of the histograms.
                              This line is step plot in the matplotlib lexicon.
    :param fontsize: float - the size of the label text in the plot in points
    :return: None
    """
    # operate on only the data we need
    sub_dataframe = device_records[["f_ghz", "designed_f_ghz", "wafer", column_name]]
    # some hard coded figure options
    # plot size is defined here and is in inches
    fig = plt.figure(figsize=(25, 10))
    # figure coordinates for the the plot axis (ax) [left, bottom, width, height]
    coor = [0.05, 0.10, 0.9, 0.9]
    # I turn the axis frame off. I like my data to look free and run off the page.
    ax = fig.add_axes(coor, frameon=False)
    legend_data = []
    legend_keys = []
    # loop over each wafer number
    for wafer_num in sorted(wafer_num_to_color_dict.keys()):
        # get the date that belongs to this loop's wafer number.
        sub_dataframe_per_wafer = sub_dataframe.loc[sub_dataframe['wafer'] == wafer_num]
        # get the column of data values for the histogram for this wafer
        data_this_wafer = sub_dataframe_per_wafer[column_name][sub_dataframe_per_wafer[column_name].notnull()]
        # a few per-wafer settings
        hatch = hatches[wafer_num % len_hatches]
        color = wafer_num_to_color_dict[wafer_num]
        # check for and get data from the optional settings at the top of this file to get (num_of_bins, hist_range)
        if column_name in column_name_to_range.keys():
            num_of_bins, *hist_range = column_name_to_range[column_name]
        else:
            hist_range = None
        # draw the solid line that defines that boundary of the bar-graphs for this wafer, a step histogram
        line = ax.hist(x=data_this_wafer, range=hist_range, color=color,
                       bins=num_of_bins, density=True, histtype='step', linewidth=linewidth)
        # draw the semi-transparent filled bar-graph the defines this wafer's histogram
        filled = ax.hist(x=data_this_wafer, range=hist_range, color=color,
                         bins=num_of_bins, density=True, histtype='stepfilled', alpha=alpha,
                         hatch=hatch)
        # draw the legend label
        legend_data.append(mpatches.Patch(facecolor=color, label=F"Wafer{'%03i' % wafer_num}",
                                          hatch=hatch))
        # organize the legend information
        legend_keys.append((line[2], filled[2]))
    # legend settings
    ax.legend(handles=legend_data, loc=0, numpoints=5, handlelength=3, fontsize=fontsize)
    # y-axis label
    ax.set_ylabel('Density', size=fontsize)
    # check for and get data from the optional settings at the top of this file to set the x-axis label
    if column_name in column_name_to_axis_label.keys():
        ax.set_xlabel(column_name_to_axis_label[column_name], size=fontsize)
    else:
        ax.set_xlabel(column_name, size=fontsize)
    # save the plot if requested
    if output_dir is not None:
        plot_path = os.path.join(output_dir, F"{column_name}_per_wafer.png")
        plt.savefig(plot_path)
        print(F"  Plot saved: {plot_path}")
    # show the plot if requested
    if show:
        plt.show(block=True)
    # close the plot and free up memory
    plt.close(fig=fig)


def standard_summary_plots(device_records_cvs_path, output_dir=None, hist_columns=None,
                           hist_num_of_bins=20, hist_alpha=0.4, verbose=False):
    """
    A single definition to run all of the standard device_summaries plots at once. This can be used as a starting
    point or an example for someone making that own analysis and plots.

    This function automatically makes summary plots, and can be maintained to include additional plots for analysis.

    :param device_records_cvs_path: str - the path to device_summaries.csv. See the example path at the bottom of
                                          this file, device_summaries_path
    :param output_dir: str - the output path for the saved data plot. None, the default, does not save any plots.
    :param hist_columns: iterable of stings - each string is a column name in device_summary.csv
    :param hist_num_of_bins: int - number of histograms bins, Note: this value is overridden if column_name is in
                                   column_name_to_range.keys() as defined at the top of this file.
    :param hist_alpha: float - 0.0 (invisible) to 1.0 (opaque) to control the transparency of the
                               bar graphs of the histograms.
    :return: pandas.DataFrame - the pandas DataFrame for all the data in device_summaries.csv
    """
    if verbose:
        print('\nDoing standard_summary_plots() in device_summary.py')
    # set defaults
    if hist_columns is None:
        hist_columns = ['lamb_at_minus95dbm', 'flux_ramp_pp_khz_at_minus75dbm', 'q_i_mean_at_minus75dbm',
                        'adr_fiftymk_k']
    # import the all the data in in device_summary.csv
    device_records = pandas.read_csv(filepath_or_buffer=device_records_cvs_path, index_col=0)
    # plot and save the delta_f plot
    delta_f_plot(device_records=device_records, show=False, output_dir=output_dir)
    # plot and save the each histogram in hist_columns
    for column_name in hist_columns:
        histogram_per_wafer(device_records=device_records, column_name=column_name,
                            show=False, output_dir=output_dir, num_of_bins=hist_num_of_bins, alpha=hist_alpha)
    return device_records


if __name__ == '__main__':
    # get the path of this python file
    ref_file_path = os.path.dirname(os.path.realpath(__file__))
    # find the path to the WaferScreen directory
    parent_dir, _ = ref_file_path.rsplit("WaferScreen", 1)
    # this is the standard path to device_summary.csv that is created by explore.py
    device_summaries_path = os.path.join(parent_dir, "WaferScreen", "waferscreen", "tldr", "device_summary.csv")
    # run the standard data summary plots
    example_device_records = standard_summary_plots(device_records_cvs_path=device_summaries_path,
                                                    output_dir=None, hist_columns=None,
                                                    hist_num_of_bins=20, hist_alpha=0.4)
