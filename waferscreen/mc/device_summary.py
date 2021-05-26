import os
import numpy as np
import pandas
pandas.options.mode.chained_assignment = None  # default='warn'
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from ref import device_summaries_dir
from waferscreen.mc.explore import LambExplore


wafer_num_to_color_dict = {9: "seagreen", 11: "crimson", 12: "darkgoldenrod", 13: "deepskyblue", 14: "mediumblue",
                           15: "rebeccapurple", 16: "DarkOrange"}
column_name_to_axis_label = {'lamb_at_minus95dbm': "Lambda (-95dBm est. at devices)",
                             'flux_ramp_pp_khz_at_minus95dbm': 'Flux Ramp peak-to-peak (kHz) (-95dBm est. at devices)',
                             'q_i_mean_at_minus75dbm': 'Qi (-75dBm est. at devices)'}
column_name_to_range = {'flux_ramp_pp_khz_at_minus95dbm': (30, 0, 250),
                        'lamb_at_minus95dbm': (60, 0, 0.7)}
hatches = ['/', '*', '|', '\\', 'x', 'o', '-', '.', '0', '+']
len_hatches = len(hatches)


def wafer_num_to_color(wafer_num):
    wafer_num = int(wafer_num)
    if wafer_num in wafer_num_to_color_dict.keys():
        return wafer_num_to_color_dict[wafer_num]
    return 'black'


def delta_f_plot(device_records, show=True, output_dir=None, markersize=30, fontsize=18):
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
        plt.savefig(os.path.join(output_dir, "delta_f_per_wafer.pdf"))
    # show the plot
    if show:
        plt.show(block=True)
    # close the plot and let the memory be free
    plt.close(fig=fig)


def user_hist(x, num_of_bins=50):
    hist, bins = np.histogram(x, bins=num_of_bins)
    width = np.diff(bins)
    centers = (bins[:-1] + bins[1:]) / 2
    return hist, bins, width, centers


def histogram_per_wafer(device_records, column_name="lamb_at_minus95dbm", show=True, output_dir=None, num_of_bins=50,
                        alpha=0.5, linewidth=3, fontsize=24):
    sub_dataframe = device_records[["f_ghz", "designed_f_ghz", "wafer", column_name]]

    fig = plt.figure(figsize=(25, 10))
    coor = [0.05, 0.10, 0.9, 0.9]
    ax = fig.add_axes(coor, frameon=False)
    legend_data = []
    legend_keys = []
    for wafer_num in sorted(wafer_num_to_color_dict.keys()):
        sub_dataframe_per_wafer = sub_dataframe.loc[sub_dataframe['wafer'] == wafer_num]
        data_this_wafer = sub_dataframe_per_wafer[column_name][sub_dataframe_per_wafer[column_name].notnull()]
        hatch = hatches[wafer_num % len_hatches]
        color = wafer_num_to_color_dict[wafer_num]
        if column_name in column_name_to_range.keys():
            num_of_bins, *hist_range = column_name_to_range[column_name]
        else:
            hist_range = None
        line = ax.hist(x=data_this_wafer, range=hist_range, color=color,
                       bins=num_of_bins, density=True, histtype='step', linewidth=linewidth)
        filled = ax.hist(x=data_this_wafer, range=hist_range, color=color,
                         bins=num_of_bins, density=True, histtype='stepfilled', alpha=alpha,
                         hatch=hatch)
        legend_data.append(mpatches.Patch(facecolor=color, label=F"Wafer{'%03i' % wafer_num}",
                                          hatch=hatch))
        legend_keys.append((line[2], filled[2]))
    ax.legend(handles=legend_data, loc=0, numpoints=5, handlelength=3, fontsize=fontsize)
    ax.set_ylabel('Density', size=fontsize)
    if column_name in column_name_to_axis_label.keys():
        ax.set_xlabel(column_name_to_axis_label[column_name], size=fontsize)
    else:
        ax.set_xlabel(column_name, size=fontsize)
    if output_dir is not None:
        plt.savefig(os.path.join(output_dir, F"{column_name}_per_wafer.pdf"))
    if show:
        plt.show(block=True)
    plt.close(fig=fig)


if __name__ == '__main__':
    device_records_cvs_path = LambExplore.device_records_cvs_path

    device_records = pandas.read_csv(filepath_or_buffer=device_records_cvs_path, index_col=0)
    delta_f_plot(device_records=device_records, show=False, output_dir=device_summaries_dir)
    for column_name in ['lamb_at_minus95dbm', 'flux_ramp_pp_khz_at_minus95dbm', 'q_i_mean_at_minus75dbm']:
        histogram_per_wafer(device_records=device_records, column_name=column_name,
                            show=False, output_dir=device_summaries_dir, num_of_bins=20, alpha=0.4)
