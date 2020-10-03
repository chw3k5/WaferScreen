import numpy as np
from matplotlib import pyplot as plt
from operator import itemgetter
import bisect
import os
from ref import band_params, output_dir
from waferscreen.read.table_read import floats_table
from waferscreen.plot.quick_plots import ls, len_ls


band_edges = []
band_centers = []
for band in band_params.keys():
    band_edges.append((band_params[band]["min_GHz"], F"Start {band}"))
    band_edges.append((band_params[band]["max_GHz"], F"End {band}"))
    band_centers.append((band_params[band]["center_GHz"], F"{band}  Center at {'%1.3f' % band_params[band]['center_GHz']} GHz"))
ordered_band_edges = sorted(band_edges, key=itemgetter(0))
ordered_band_list = [band_tuple[0] for band_tuple in ordered_band_edges]
ordered_band_centers = sorted(band_centers, key=itemgetter(0))


def find_band_edges(min_freq, max_freq, extened=False):
    start_index = bisect.bisect(ordered_band_list, min_freq)
    end_index = bisect.bisect_left(ordered_band_list, max_freq)
    if extened:
        if start_index != 0:
            start_index -= 1
        if end_index != len(ordered_band_list):
            end_index += 1
    return ordered_band_edges[start_index: end_index]


def find_center_band(center_GHz):
    min_diff = float('inf')
    nearest_band_center_index = -1
    count = 0
    for freq, _ in ordered_band_centers:
        diff = np.abs(center_GHz - freq)
        if diff < min_diff:
            min_diff = diff
            nearest_band_center_index = count
        count += 1
    return ordered_band_centers[nearest_band_center_index]


def plot_21(file, save=True, show=False, show_bands=True, res_fit=None):
    legend_dict = {}
    data_dict = floats_table(file, delimiter=",")
    if isinstance(data_dict, list):
        data_dict = {'freq': data_dict[0], 'real': data_dict[1], 'imag': data_dict[2]}
    data_dict["mag"] = 20.0 * np.log10(np.sqrt(np.square(data_dict['real']) + np.square(data_dict['imag'])))
    data_dict['phase'] = np.arctan2(data_dict['imag'], data_dict['real'])

    plt.figure(figsize=(20, 8))
    plt.plot(data_dict["freq"], data_dict['mag'], color='firebrick', ls='solid')
    legend_dict['leg_lines'] = [plt.Line2D(range(10), range(10), color='firebrick', ls='solid')]
    legend_dict['leg_labels'] = ['S21']

    min_freq = np.min(data_dict['freq'])
    max_freq = np.max(data_dict['freq'])
    center_freq = (max_freq + min_freq) / 2.0
    axes = plt.gca()
    ymin, ymax = axes.get_ylim()
    if show_bands:
        counter = 1
        color = "black"
        for freq, label_str in find_band_edges(min_freq=min_freq, max_freq=max_freq):
            line_style = ls[counter % len_ls]
            plt.plot([freq, freq], [ymin, ymax], color=color, ls=line_style)
            legend_dict['leg_lines'].append(plt.Line2D(range(10), range(10), color=color, ls=line_style))
            legend_dict['leg_labels'].append(label_str)
            counter += 1
        center_band_freq, center_band_str = find_center_band(center_GHz=center_freq)
        plt.title(center_band_str)
    else:
        plt.title(file)
    plt.xlabel('Frequency (GHz)')
    plt.ylabel("S21 Transmission (dB)")
    plt.legend(legend_dict['leg_lines'], legend_dict['leg_labels'], loc=0, numpoints=3, handlelength=5, fontsize=16)
    plt.ylim((ymin, ymax))
    if show:
        plt.show()
    if save:
        plot_file_name, _ = file.rsplit(".", 1)
        plot_file_name += '.pdf'
        plt.savefig(plot_file_name)
        print("Saved Plot to:", plot_file_name)
    return


def make_s21_folder(folder):
    for file in [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]:
        plot_21(file=file, save=True, show_bands=False, show=False)


if __name__ == "__main__":
    # file = os.path.join(s21_dir, "so", "7_Band01_2020-09-08_run9.csv")
    # file = os.path.join(output_dir, "s21", "8", "Band03", "2020-09-28", "8_Band03_2020-09-28_run4.csv")
    # file = os.path.join("D:\\", 'waferscreen', 's21', 'check_out', 'Input1_Trace0.15K_2020-09-01_run14.csv')
    plot_21(file='D:\\waferscreen\\output\\s21\\8\\Band03\\2020-09-29\\flux_ramp\\sdata_res_18_cur_0uA.csv', show=True, save=False, show_bands=False)

    # make_s21_folder(os.path.join("D:\\", 'waferscreen', 's21', 'check_out'))

