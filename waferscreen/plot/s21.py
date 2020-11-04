import numpy as np
from matplotlib import pyplot as plt
import os
from waferscreen.read.table_read import floats_table
from waferscreen.plot.quick_plots import ls, len_ls
from waferscreen.tools.band_calc import find_band_edges, find_center_band


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
        plt.draw()
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
    plot_21(file="D:\\waferscreen\\s21\\check_out\\InputB_1coldAmp_2warm_Trace300K_2020-10-09_run2.csv", show=True, save=True, show_bands=True)

    # make_s21_folder(os.path.join("D:\\", 'waferscreen', 's21', 'check_out'))

