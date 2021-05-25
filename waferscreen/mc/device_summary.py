import os
import numpy as np
import pandas
import matplotlib.pyplot as plt
from ref import device_summaries_dir
from waferscreen.mc.explore import LambExplore


wafer_num_to_color_dict = {9: "seagreen", 11: "crimson", 12: "darkgoldenrod", 13: "deepskyblue", 14: "mediumblue",
                           15: "rebeccapurple", 16: "DarkOrange"}
column_name_to_axis_label = {'lamb_at_minus95dbm': "Lambda (-95dBm est. at devices)",
                             'flux_ramp_pp_khz_at_minus95dbm': 'Flux Ramp peak-to-peak (kHz) (-95dBm est. at devices)',
                             'q_i_mean_at_minus75dbm': 'Qi (-75dBm est. at devices)'}
column_name_to_range = {'flux_ramp_pp_khz_at_minus95dbm': (0, 250),
                        'lamb_at_minus95dbm': (0, 0.7)}
hatches = ['/', '*', '|', '\\', 'x', 'o', '-', '.', '0', '+']
len_hatches = len(hatches)


def wafer_num_to_color(wafer_num):
    wafer_num = int(wafer_num)
    if wafer_num in wafer_num_to_color_dict.keys():
        return wafer_num_to_color_dict[wafer_num]
    return 'black'


def delta_f_plot(device_records, show=True, output_dir=None):
    f_design_f_meas = device_records[["f_ghz", "designed_f_ghz", "wafer"]]
    f_design_f_meas['delta_f_mhz'] = f_design_f_meas['f_ghz'].sub(f_design_f_meas['designed_f_ghz']).mul(1.0e3)
    f_design_f_meas['wafer_color'] = f_design_f_meas['wafer'].map(wafer_num_to_color, na_action='ignore')

    fig = plt.figure(figsize=(25, 10))
    coor = [0.05, 0.05, 0.9, 0.9]
    ax = fig.add_axes(coor, frameon=False)
    leglabels = []
    leglines = []
    for wafer_num in sorted(wafer_num_to_color_dict.keys()):
        sub_dataframe_per_wafer = f_design_f_meas.loc[f_design_f_meas['wafer'] == wafer_num]
        ax.scatter(sub_dataframe_per_wafer['designed_f_ghz'], sub_dataframe_per_wafer['delta_f_mhz'],
                   c=wafer_num_to_color_dict[wafer_num])
        leglabels.append(F"Wafer{'%03i' % wafer_num}")
        leglines.append(plt.Line2D(range(10), range(10), color=wafer_num_to_color_dict[wafer_num], ls='None',
                                   marker='o', markersize=10, markerfacecolor=wafer_num_to_color_dict[wafer_num],
                                   alpha=1.0))
    ax.legend(leglines, leglabels, loc=0, numpoints=5, handlelength=3, fontsize=10)
    ax.set_ylabel('Measured - Designed (MHz)')
    ax.set_xlabel('Designed Frequency (GHz)')
    if output_dir is not None:
        plt.savefig(os.path.join(output_dir, "delta_f_per_wafer.pdf"))
    if show:
        plt.show(block=True)
    plt.close(fig=fig)


def user_hist(x, num_of_bins=50):
    hist, bins = np.histogram(x, bins=num_of_bins)
    width = np.diff(bins)
    centers = (bins[:-1] + bins[1:]) / 2
    return hist, bins, width, centers


def histogram_per_wafer(device_records, column_name="lamb_at_minus95dbm", show=True, output_dir=None, num_of_bins=50,
                        alpha=0.5):
    sub_dataframe = device_records[["f_ghz", "designed_f_ghz", "wafer", column_name]]

    fig = plt.figure(figsize=(25, 10))
    coor = [0.05, 0.05, 0.9, 0.9]
    ax = fig.add_axes(coor, frameon=False)

    for wafer_num in sorted(wafer_num_to_color_dict.keys()):
        sub_dataframe_per_wafer = sub_dataframe.loc[sub_dataframe['wafer'] == wafer_num]
        data_this_wafer = sub_dataframe_per_wafer[column_name][sub_dataframe_per_wafer[column_name].notnull()]
        hatch = hatches[wafer_num % len_hatches]
        if column_name in column_name_to_range.keys():
            hist_range = column_name_to_range[column_name]
        else:
            hist_range = None
        ax.hist(x=data_this_wafer, range=hist_range, color=wafer_num_to_color_dict[wafer_num],
                bins=num_of_bins, density=True, alpha=alpha,
                hatch=hatch,  label=F"Wafer{'%03i' % wafer_num}")
    ax.legend(loc=0, numpoints=5, handlelength=3, fontsize=24)
    ax.set_ylabel('Density')
    if column_name in column_name_to_axis_label.keys():
        ax.set_xlabel(column_name_to_axis_label[column_name])
    else:
        ax.set_xlabel(column_name)
    if output_dir is not None:
        plt.savefig(os.path.join(output_dir, F"{column_name}_per_wafer.pdf"))
    if show:
        plt.show(block=True)
    plt.close(fig=fig)


if __name__ == '__main__':
    device_records_cvs_path = LambExplore.device_records_cvs_path

    device_records = pandas.read_csv(filepath_or_buffer=device_records_cvs_path, index_col=0)
    # delta_f_plot(device_records=device_records, show=False, output_dir=device_summaries_dir)
    for column_name in ['lamb_at_minus95dbm', 'flux_ramp_pp_khz_at_minus95dbm', 'q_i_mean_at_minus75dbm']:
        histogram_per_wafer(device_records=device_records, column_name=column_name,
                            show=False, output_dir=device_summaries_dir, num_of_bins=20, alpha=0.4)
