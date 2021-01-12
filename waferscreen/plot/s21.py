import numpy as np
from matplotlib import pyplot as plt
import os
from waferscreen.plot.quick_plots import ls, len_ls
from waferscreen.tools.band_calc import find_band_edges, find_center_band
from waferscreen.read.prodata import read_pro_s21


def plot_s21(file=None, freqs_GHz=None, s21_complex=None, show_ri=False,
             meta_data=None, save=True, show=False, show_bands=True):
    legend_dict = {}
    data_dict = {}
    if file is not None and s21_complex is None and freqs_GHz is None and meta_data is None:
        data_dict["freq"], s21_complex, meta_data = read_pro_s21(path=file)
    else:
        data_dict["freq"] = freqs_GHz
    # Math
    data_dict["real"], data_dict["imag"] = s21_complex.real, s21_complex.imag
    data_dict["mag"] = 20.0 * np.log10(np.sqrt(np.square(data_dict['real']) + np.square(data_dict['imag'])))
    data_dict['phase'] = np.arctan2(data_dict['imag'], data_dict['real'])

    # Whole Plot
    fig = plt.figure(figsize=(20, 16))
    # Subplots
    if show_ri:
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)
    else:
        ax1 = fig.add_subplot(111)
    ax1.plot(data_dict["freq"], data_dict['mag'], color='firebrick', ls='solid')
    legend_dict['leg_lines'] = [plt.Line2D(range(10), range(10), color='firebrick', ls='solid')]
    legend_dict['leg_labels'] = ['S21']
    if show_ri:
        ax2.plot(data_dict["imag"], data_dict['real'], color='darkorchid', ls='solid')
        legend_dict['leg_lines'] = [plt.Line2D(range(10), range(10), color='darkorchid', ls='solid')]
        legend_dict['leg_labels'] = ['S21']
        ax2.set_xlabel('Real S21')
        ax2.set_ylabel("Imaginary S21")

    min_freq = np.min(data_dict['freq'])
    max_freq = np.max(data_dict['freq'])
    center_freq = (max_freq + min_freq) / 2.0
    ymin, ymax = ax1.get_ylim()
    if show_bands:
        counter = 1
        color = "black"
        for freq, label_str in find_band_edges(min_freq=min_freq, max_freq=max_freq):
            line_style = ls[counter % len_ls]
            ax1.plot([freq, freq], [ymin, ymax], color=color, ls=line_style)
            legend_dict['leg_lines'].append(plt.Line2D(range(10), range(10), color=color, ls=line_style))
            legend_dict['leg_labels'].append(label_str)
            counter += 1
        center_band_freq, center_band_str = find_center_band(center_GHz=center_freq)
        plt.title(center_band_str)
    else:
        plt.title(file)
    ax1.set_xlabel('Frequency (GHz)')
    ax1.set_ylabel("S21 Transmission (dB)")

    ax1.legend(legend_dict['leg_lines'], legend_dict['leg_labels'], loc=0, numpoints=3, handlelength=5, fontsize=16)
    ax1.set_ylim((ymin, ymax))
    if show:
        plt.show()
    if save and file is not None:
        plt.draw()
        plot_file_name, _ = file.rsplit(".", 1)
        plot_file_name += '.pdf'
        plt.savefig(plot_file_name)
        print("Saved Plot to:", plot_file_name)
    plt.clf()
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

