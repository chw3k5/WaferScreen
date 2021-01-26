import numpy as np
from matplotlib import pyplot as plt
from ref import today_str
from waferscreen.plot.quick_plots import ls, len_ls, colors
from waferscreen.tools.band_calc import find_band_edges, find_center_band
from waferscreen.analyze.s21_io import read_s21, ri_to_magphase, plot_bands
from waferscreen.analyze.resfit import fit_simple_res_gain_slope_complex
from ref import band_params


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
        plt.show(block=True)
    if save and file is not None:
        plt.draw()
        plot_file_name, _ = file.rsplit(".", 1)
        plot_file_name += '.pdf'
        plt.savefig(plot_file_name)
        print("Saved Plot to:", plot_file_name)
    plt.close(fig)
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
        plt.show(block=True)
    plt.clf()
    plt.close(fig)


def plot_res_fit(f_GHz_single_res, s21_mag_single_res=None, not_smoothed_mag_single_res=None,
                 s21_mag_single_res_highpass=None,
                 params_guess=None, params_fit=None,
                 minima_pair=None, fwhm_pair=None, window_pair=None, fitter_pair=None, output_filename=None):
    fig = plt.figure(figsize=(8, 8))
    leglines = []
    leglabels = []

    # unprocessed (yet still phase corrected, group delay removed, data)
    if s21_mag_single_res is not None:
        unprocessed_color = "black"
        unprocessed_linewidth = 5
        plt.plot(f_GHz_single_res, s21_mag_single_res - s21_mag_single_res[0], color="black",
                 linewidth=unprocessed_linewidth)
        leglines.append(plt.Line2D(range(10), range(10), color=unprocessed_color, ls="-",
                                   linewidth=unprocessed_linewidth))
        leglabels.append(F"unprocessed")

    # window baseline subtraction
    if not_smoothed_mag_single_res is not None:
        window_bl_color = "dodgerblue"
        window_bl_linewidth = 4
        plt.plot(f_GHz_single_res, not_smoothed_mag_single_res, color=window_bl_color,
                 linewidth=window_bl_linewidth)
        leglines.append(plt.Line2D(range(10), range(10), color=window_bl_color, ls="-",
                                   linewidth=window_bl_linewidth))
        leglabels.append(F"Highpass Window")

    # window baseline substraction and smooth
    if s21_mag_single_res_highpass is not None:
        window_bl_smooth_color = "chartreuse"
        window_bl_smooth_linewidth = 3
        plt.plot(f_GHz_single_res, s21_mag_single_res_highpass, color=window_bl_smooth_color,
                 linewidth=window_bl_smooth_linewidth)
        leglines.append(plt.Line2D(range(10), range(10), color=window_bl_smooth_color, ls="-",
                                   linewidth=window_bl_smooth_linewidth))
        leglabels.append(F"Highpass Window Smoothed")

    # guess mag-phase
    if params_guess is not None:
        guess_fit_out = fit_simple_res_gain_slope_complex(f_GHz_single_res, params_guess.base_amplitude_abs,
                                                          params_guess.a_phase_rad, params_guess.base_amplitude_slope,
                                                          params_guess.tau_ns, params_guess.fcenter_ghz,
                                                          params_guess.q_i, params_guess.q_c,
                                                          params_guess.impedance_ratio)
        guess_complex = np.array([guess_fit_out[2 * n] + 1j * guess_fit_out[(2 * n) + 1]
                                  for n in range(len(f_GHz_single_res))])
        guess_mag, guess_phase = ri_to_magphase(r=guess_complex.real, i=guess_complex.imag)
        guess_mag_color = "firebrick"
        guess_mag_linewidth = 2
        plt.plot(f_GHz_single_res, guess_mag, color=guess_mag_color,
                 linewidth=guess_mag_linewidth)
        leglines.append(plt.Line2D(range(10), range(10), color=guess_mag_color, ls="-",
                                   linewidth=guess_mag_linewidth))
        leglabels.append(F"Initial Fit")

    # Final Fit mag-phase
    if params_fit is not None:
        final_fit_out = fit_simple_res_gain_slope_complex(f_GHz_single_res, params_fit.base_amplitude_abs,
                                                          params_fit.a_phase_rad, params_fit.base_amplitude_slope,
                                                          params_fit.tau_ns, params_fit.fcenter_ghz,
                                                          params_fit.q_i, params_fit.q_c, params_fit.impedance_ratio)
        final_complex = np.array([final_fit_out[2 * n] + 1j * final_fit_out[(2 * n) + 1]
                                  for n in range(len(f_GHz_single_res))])
        final_mag, final_phase = ri_to_magphase(r=final_complex.real, i=final_complex.imag)
        final_mag_color = "black"
        final_mag_linewidth = 5
        final_mag_ls = 'dotted'
        plt.plot(f_GHz_single_res, final_mag, color=final_mag_color,
                 linewidth=final_mag_linewidth, ls=final_mag_ls)
        leglines.append(plt.Line2D(range(10), range(10), color=final_mag_color, ls=final_mag_ls,
                                   linewidth=final_mag_linewidth))
        leglabels.append(F"Final Fit")

    # Zero Line for reference
    zero_line_color = "darkgoldenrod"
    zero_line_smooth_linewidth = 1
    zero_line_ls = "dashed"
    plt.plot((f_GHz_single_res[0], f_GHz_single_res[-1]), (0, 0), color=zero_line_color,
             linewidth=zero_line_smooth_linewidth, ls=zero_line_ls)
    leglines.append(plt.Line2D(range(10), range(10), color=zero_line_color, ls=zero_line_ls,
                               linewidth=zero_line_smooth_linewidth))
    leglabels.append(F"Zero dB line")

    # show minima
    if minima_pair is not None:
        f_GHz_min = minima_pair[0]
        mag_min = minima_pair[1]
        window_bound_color \
            = "darkorchid"
        window_bound_linewidth = 1
        window_bound_ls = "None"
        window_bound_alpha = 0.65
        window_bound_marker = 'o'
        window_bound_markersize = 10
        plt.plot(f_GHz_min, mag_min,
                 color=window_bound_color,
                 linewidth=window_bound_linewidth, ls=window_bound_ls, marker=window_bound_marker,
                 markersize=window_bound_markersize, markerfacecolor=window_bound_color, alpha=window_bound_alpha)
        leglines.append(plt.Line2D(range(10), range(10), color=window_bound_color, ls=window_bound_ls,
                                   linewidth=window_bound_linewidth, marker=window_bound_marker,
                                   markersize=window_bound_markersize,
                                   markerfacecolor=window_bound_color, alpha=window_bound_alpha))
        leglabels.append(F"Found Minima")

    # show the calculated FWHM
    if fwhm_pair is not None:
        f_GHz_fwhm = fwhm_pair[0]
        mag_fwhm = fwhm_pair[1]
        fwhm_color = "forestgreen"
        fwhm_linewidth = 1
        fwhm_ls = "None"
        fwhm_alpha = 0.8
        fwhm_marker = 'D'
        fwhm_markersize = 10
        plt.plot(f_GHz_fwhm, mag_fwhm,
                 color=fwhm_color, linewidth=fwhm_linewidth, ls=fwhm_ls, marker=fwhm_marker,
                 markersize=fwhm_markersize, markerfacecolor=fwhm_color, alpha=fwhm_alpha)
        leglines.append(plt.Line2D(range(10), range(10), color=fwhm_color, ls=fwhm_ls,
                                   linewidth=fwhm_linewidth, marker=fwhm_marker,
                                   markersize=fwhm_markersize,
                                   markerfacecolor=fwhm_color, alpha=fwhm_alpha))
        leglabels.append(F"FWHM")

    # show the calculated windows from the thresholding
    if window_pair is not None:
        f_GHz_window_pair = window_pair[0]
        mag_window_pair = window_pair[1]
        window_bound_color = "firebrick"
        window_bound_linewidth = 1
        window_bound_ls = "None"
        window_bound_alpha = 0.8
        window_bound_marker = '*'
        window_bound_markersize = 10
        plt.plot(f_GHz_window_pair, mag_window_pair,
                 color=window_bound_color,
                 linewidth=window_bound_linewidth, ls=window_bound_ls, marker=window_bound_marker,
                 markersize=window_bound_markersize,
                 markerfacecolor=window_bound_color, alpha=window_bound_alpha)
        leglines.append(plt.Line2D(range(10), range(10), color=window_bound_color, ls=window_bound_ls,
                                   linewidth=window_bound_linewidth, marker=window_bound_marker,
                                   markersize=window_bound_markersize,
                                   markerfacecolor=window_bound_color, alpha=window_bound_alpha))
        leglabels.append(F"Window from Threshold")

    # show the calculated fitter boundaries
    if fitter_pair is not None:
        f_GHz_fitter = fitter_pair[0]
        mag_fitter = fitter_pair[1]
        fitter_bound_color = "Navy"
        fitter_bound_linewidth = 1
        fitter_bound_ls = "None"
        fitter_bound_alpha = 1.0
        fitter_bound_marker = 'x'
        fitter_bound_markersize = 10
        plt.plot(f_GHz_fitter, mag_fitter,
                 color=fitter_bound_color, linewidth=fitter_bound_linewidth,
                 ls=fitter_bound_ls, marker=fitter_bound_marker,
                 markersize=fitter_bound_markersize,markerfacecolor=fitter_bound_color, alpha=fitter_bound_alpha)
        leglines.append(plt.Line2D(range(10), range(10), color=fitter_bound_color, ls=fitter_bound_ls,
                                   linewidth=fitter_bound_linewidth, marker=fitter_bound_marker,
                                   markersize=fitter_bound_markersize,
                                   markerfacecolor=fitter_bound_color, alpha=fitter_bound_alpha))
        leglabels.append(F"Baseline Bounds")

    # Whole plot options:
    plt.xlabel(F"Frequency (GHz)")
    plt.ylabel(F"dB")
    format_str = '%i'
    if params_fit is not None:
        title_str = F"Qi: {format_str % params_fit.q_i}({format_str % params_fit.q_i_error})   "
        title_str += F"Qc: {format_str % params_fit.q_c}({format_str % params_fit.q_c_error})"
        plt.title(title_str)
    plt.legend(leglines,
               leglabels, loc=0,
               numpoints=3, handlelength=5,
               fontsize=8)
    # Display
    if output_filename is not None:
        plt.draw()
        plt.savefig(output_filename)
        print("Saved Plot to:", output_filename)
    else:
        plt.show(block=True)
    plt.clf()
    plt.close(fig)


def band_plot(freqs_GHz, mags, fitted_resonators_parameters_by_band, output_filename=None):


    fig = plt.figure(figsize=(20, 8))
    ax1 = fig.add_subplot(111)
    ax1.plot(freqs_GHz, mags, color="black", ls='solid', linewidth=1)
    # found resonators
    color_count = 0
    for band_name in fitted_resonators_parameters_by_band:
        color = colors[color_count]
        band_dict = band_params[band_name]
        min_GHz = band_dict["min_GHz"]
        max_GHz = band_dict["max_GHz"]
        boolean_array = np.logical_and(min_GHz <= freqs_GHz, freqs_GHz <= max_GHz)
        ax1.plot(freqs_GHz[boolean_array], mags[boolean_array], color=color, ls='solid', linewidth=2)
        color_count += 1

    ymin, ymax = ax1.get_ylim()
    text_y = (0.2 * (ymax - ymin)) + ymin
    color_count = 0
    # band bounds
    for band_name in fitted_resonators_parameters_by_band:
        color = colors[color_count]
        band_dict = band_params[band_name]
        fitted_params_this_band = fitted_resonators_parameters_by_band[band_name]
        in_band_res = [res_param for res_param in fitted_params_this_band
                       if band_dict["max_GHz"] >= res_param.fcenter_ghz >= band_dict["min_GHz"]]

        ax1.plot((band_dict["min_GHz"], band_dict["min_GHz"]), (ymin, ymax), color="black", ls="dotted")
        ax1.plot((band_dict["max_GHz"], band_dict["max_GHz"]), (ymin, ymax), color="black", ls="dashed")
        text_x = (0.1 * (band_dict["max_GHz"] - band_dict["min_GHz"])) + band_dict["min_GHz"]
        ax1.text(text_x, text_y, F'{band_name}\n {len(fitted_params_this_band)} found,\n {len(in_band_res)} inband',
                 color='black', bbox={'facecolor': color, 'alpha': 0.5, 'pad': 10})
        color_count += 1

    # Whole plot details
    ax1.set_xlabel('Frequency (GHz)')
    ax1.set_ylabel("S21 (dB)")

    # Display
    if output_filename is not None:
        plt.draw()
        plt.savefig(output_filename)
        print("Saved Plot to:", output_filename)
    else:
        plt.show(block=True)
    plt.clf()
    plt.close()


