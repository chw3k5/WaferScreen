import numpy as np
from matplotlib import pyplot as plt
from ref import today_str
from waferscreen.plot.quick_plots import ls, len_ls
from waferscreen.tools.band_calc import find_band_edges, find_center_band
from waferscreen.analyze.s21_io import read_s21, write_s21, dirname_create, ri_to_magphase, plot_bands


def s21_subplot(ax, plot_data, x_data_str, y_data_str, y_label_str="", x_label_str="", leg_label_str="", title_str='',
                color="black", ls="solid", show_bands=False):
    legend_dict = {}
    ax.plot(plot_data[x_data_str], plot_data[y_data_str], color=color, ls=ls)
    ax.set_ylabel(y_label_str)
    ax.set_xlabel(x_label_str)
    legend_dict['leg_lines'] = [plt.Line2D(range(10), range(10), color=color, ls=ls)]
    legend_dict['leg_labels'] = [leg_label_str]
    if show_bands:
        center_band_str = plot_bands(ax, plot_data, legend_dict)
        if title_str == "":
            ax.title.set_text(center_band_str)
    else:
        ax.title.set_text(title_str)
    ax.legend(legend_dict['leg_lines'], legend_dict['leg_labels'], loc=1, numpoints=3, handlelength=5, fontsize=12)
    return


def plot_s21(file=None, freqs_GHz=None, s21_complex=None, show_ri=False,
             meta_data=None, save=True, show=False, show_bands=True):
    legend_dict = {}
    data_dict = {}
    if file is not None and s21_complex is None and freqs_GHz is None and meta_data is None:
        s21_dict, meta_data = read_s21(path=file)
        data_dict['freq'] = s21_dict["freq_ghz"]
        data_dict["real"], data_dict["imag"] = s21_dict["real"], s21_dict["imag"]
    else:
        data_dict["freq"] = freqs_GHz
        data_dict["real"], data_dict["imag"] = s21_complex.real, s21_complex.imag
    # Math
    data_dict["mag"], data_dict["phase"] = ri_to_magphase(r=data_dict["real"], i=data_dict["phase"])

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


def plot_filter(freqs_GHz, original_s21, lowpass_s21, highpass_s21, output_filename=None):
    # Organization and Math
    plot_data = {"freq_ghz": freqs_GHz,
                 "original_real": np.real(original_s21), "original_imag": np.imag(original_s21),
                 "lowpass_real": np.real(lowpass_s21), "lowpass_imag": np.imag(lowpass_s21),
                 "highpass_real": np.real(highpass_s21), "highpass_imag": np.imag(highpass_s21)}
    plot_data["original_mag"], plot_data["original_phase"] = ri_to_magphase(r=plot_data["original_real"], i=plot_data["original_imag"])
    plot_data["lowpass_mag"], plot_data["lowpass_phase"] = ri_to_magphase(r=plot_data["lowpass_real"],
                                                                          i=plot_data["lowpass_imag"])
    plot_data["highpass_mag"], plot_data["highpass_phase"] = ri_to_magphase(r=plot_data["highpass_real"],
                                                                            i=plot_data["highpass_imag"])
    # frequency
    plot_data["min_freq"] = np.min(plot_data['freq_ghz'])
    plot_data["max_freq"] = np.max(plot_data['freq_ghz'])
    plot_data["center_freq"] = (plot_data["max_freq"] + plot_data["min_freq"]) / 2.0

    # Whole Plot
    x_inches = 15.0
    yx_ratio = 11.0 / 8.5
    fig = plt.figure(figsize=(x_inches, x_inches * yx_ratio))
    fig.suptitle('Filtered data  ' + today_str, size='xx-large')
    ax_mags = fig.add_subplot(211)
    ax_phases = fig.add_subplot(234)
    ax_reals = fig.add_subplot(235)
    ax_imags = fig.add_subplot(236)

    # Plot Loops
    ls = "solid"
    for ax_handle, short_name, y_label in [(ax_mags, "mag", "Magnitude (dBm)"), (ax_phases, "phase", "Phase (radians)"), (ax_reals, "real", "Real"), (ax_imags, "imag", "Imaginary")]:
        legend_dict = {}
        legend_dict['leg_lines'] = []
        legend_dict['leg_labels'] = []
        for data_type, color, linew in [("original", "black", 3),  ("highpass", "dodgerblue", 1), ("lowpass", "chartreuse", 1)]:
            ax_handle.plot(freqs_GHz, plot_data[F"{data_type}_{short_name}"], color=color, ls=ls, linewidth=linew)
            legend_dict['leg_lines'].append(plt.Line2D(range(10), range(10), color=color, ls=ls, linewidth=linew))
            legend_dict['leg_labels'].append(F"{data_type}")
        ax_handle.set_ylabel(F"S21 {y_label}")
        ax_handle.set_xlabel("Frequency (GHz)")
        ax_handle.legend(legend_dict['leg_lines'], legend_dict['leg_labels'], loc=0, numpoints=3, handlelength=5, fontsize=16)

    # Display
    if output_filename is not None:
        plt.draw()
        plt.savefig(output_filename)
        print("Saved Plot to:", output_filename)
    else:
        plt.show()


if __name__ == "__main__":
    # file = os.path.join(s21_dir, "so", "7_Band01_2020-09-08_run9.csv")
    # file = os.path.join(output_dir, "s21", "8", "Band03", "2020-09-28", "8_Band03_2020-09-28_run4.csv")
    # file = os.path.join("D:\\", 'waferscreen', 's21', 'check_out', 'Input1_Trace0.15K_2020-09-01_run14.csv')
    plot_s21(file="D:\\waferscreen\\s21\\check_out\\InputB_1coldAmp_2warm_Trace300K_2020-10-09_run2.csv", show=True, save=True, show_bands=True)

    # make_s21_folder(os.path.join("D:\\", 'waferscreen', 's21', 'check_out'))

