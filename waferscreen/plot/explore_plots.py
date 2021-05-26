# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import os
import ref
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import matplotlib.colors as colors
import matplotlib.cm as cm
from scipy.stats import chisquare
from waferscreen.data_io.explore_io import flagged_data, wafer_str_to_num, res_num_to_str, band_num_to_str,\
    chip_id_str_to_chip_id_tuple
from waferscreen.data_io.s21_io import read_s21, ri_to_magphase
from waferscreen.analyze.lambfit import f0_of_I
from waferscreen.data_io.explore_io import CalcMetadataAtNeg95dbm, CalcMetadataAtNeg75dbm


report_markers = ["*", "v", "s", "<", "X",
                  "p", "^", "D", ">", "P"]
report_colors = ["seagreen", "crimson", "darkgoldenrod", "deepskyblue", "mediumblue", "rebeccapurple"]


def criteria_flagged_summary(flag_table_info, criteria_name, res_numbers, too_low=True):
    for res_label in res_numbers:
        summary_str = F"Criteria Flag: {criteria_name}"
        if too_low:
            summary_str += " too low."
        else:
            summary_str += " too high."
        # if the resonator was flagged already for another reason we need to add a new line to the summary.
        if res_label in flag_table_info:
            flag_table_info[res_label] += "\n" + summary_str
        else:
            flag_table_info[res_label] = summary_str
    return flag_table_info


def chi_squared_plot(ax, f_ghz_mean, chi_squared_for_resonators, res_nums_int, color, markersize, alpha,
                     x_label, y_label, x_ticks_on, max_chi_squared=None):
    # calculate when the values are outside of the acceptance range
    if max_chi_squared is None:
        upper_bound = float("inf")
    else:
        upper_bound = float(max_chi_squared)
    res_nums_too_high_chi_squared = set()
    # turn on/off tick marks
    if not x_ticks_on:
        ax.tick_params(axis="x", labelbottom=False)
    # loop to plot data one point at a time (add a identifying marker for each data point)
    counter = 0
    for f_ghz, chi_squared in zip(f_ghz_mean, chi_squared_for_resonators):

        res_num = res_nums_int[counter]
        marker = report_markers[res_num % len(report_markers)]
        ax.plot(f_ghz, chi_squared.statistic, color=color, ls='None', marker=marker, markersize=markersize, alpha=alpha)
        if upper_bound < chi_squared.statistic:
            res_nums_too_high_chi_squared.add(res_num_to_str(res_num))
            ax.plot(f_ghz, chi_squared.statistic, color="black", ls='None', marker="x", markersize=markersize + 2, alpha=1.0)
        counter += 1
    # boundary and average lines
    if max_chi_squared is not None:
        ax.axhline(y=max_chi_squared, xmin=0, xmax=1, color='red', linestyle='dashdot')
    # tick marks and axis labels
    if x_label is None:
        if x_ticks_on:
            ax.set_xlabel("Average Resonator Center Frequency (GHz)")
    else:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)
    # grid on major tick marks
    ax.grid(b=True)
    ax.set_yscale("log")
    return ax, res_nums_too_high_chi_squared


def error_bar_report_plot(ax, xdata, ydata, yerr, res_nums_int, color="black", ls='None', markersize=10, alpha=0.7,
                          x_label=None, y_label=None, x_ticks_on=True,
                          min_y=None, max_y=None, average_y=None):
    # calculate when the values are outside of the acceptance range
    if min_y is None:
        lower_bound = float("-inf")
    else:
        lower_bound = float(min_y)
    if max_y is None:
        upper_bound = float("inf")
    else:
        upper_bound = float(max_y)
    res_nums_too_low = set()
    res_nums_too_high = set()
    # turn on/off tick marks
    if not x_ticks_on:
        ax.tick_params(axis="x", labelbottom=False)
    # loop to plot data one point at a time (add a identifying marker for each data point)
    counter = 0
    for x_datum, y_datum, y_datum_err in zip(xdata, ydata, yerr):
        res_num = res_nums_int[counter]
        marker = report_markers[res_num % len(report_markers)]
        ax.errorbar(x_datum, y_datum, yerr=y_datum_err,
                    color=color, ls=ls, marker=marker, markersize=markersize, alpha=alpha)
        if y_datum < lower_bound:
            res_nums_too_low.add(res_num_to_str(res_num))
            ax.plot(x_datum, y_datum, color="black", ls=ls, marker="x", markersize=markersize + 2, alpha=1.0)
        elif upper_bound < y_datum:
            res_nums_too_high.add(res_num_to_str(res_num))
            ax.plot(x_datum, y_datum, color="black", ls=ls, marker="x", markersize=markersize + 2, alpha=1.0)
        counter += 1
    # boundary and average lines
    if min_y is not None:
        ax.axhline(y=min_y, xmin=0, xmax=1, color='red', linestyle='dashed')
    if average_y is not None:
        ax.axhline(y=average_y, xmin=0, xmax=1, color='green', linestyle='dotted')
    if max_y is not None:
        ax.axhline(y=max_y, xmin=0, xmax=1, color='red', linestyle='dashdot')
    # tick marks and axis labels
    if x_label is None:
        if x_ticks_on:
            ax.set_xlabel("Average Resonator Center Frequency (GHz)")
    else:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)
    # grid on major tick marks
    ax.grid(b=True)
    return ax, res_nums_too_low, res_nums_too_high


def hist_report_plot(ax, data, bins=10, color="blue", x_label=None, y_label=None, alpha=0.5):
    ax.tick_params(axis="y", labelleft=False)
    ax.tick_params(axis="x", labelbottom=False)
    ax.hist(data, bins=bins, color=color, orientation='horizontal', alpha=alpha)
    if x_label is not None:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)
    ax.tick_params(axis='x',  # changes apply to the x-axis
                   which='both',  # both major and minor ticks are affected
                   bottom=False,  # ticks along the bottom edge are off
                   top=False,  # ticks along the top edge are off
                   labelbottom=False)
    return ax


def rug_plot(ax, xdata, y_min, y_max, color="blue",
             f_ghz_residuals_for_res_plot_shifted=None, ua_arrays_for_resonators=None):

    # Lambda fit Residuals zen plot (the lines are reminiscent of the waves in a zen rock garden)
    if f_ghz_residuals_for_res_plot_shifted is not None:
        norm = colors.Normalize(vmin=0.0, vmax=0.01)
        cmap = plt.get_cmap('gist_ncar_r')
        scalar_map = cm.ScalarMappable(norm=norm, cmap=cmap)
        y_span = y_max - y_min
        # # the background color of the plot is an indicator that this feature is triggered.
        # ax.set_facecolor("black")
        # get the x axis limits prior to this plot
        x_min, x_max = ax.get_xlim()
        for f_ghz_plot_residuals, ua_array in zip(f_ghz_residuals_for_res_plot_shifted, ua_arrays_for_resonators):
            ua_min = np.min(ua_array)
            ua_max = np.max(ua_array)
            ua_span = ua_max - ua_min
            ua_array_normalized_for_plot = (((ua_array - ua_min) / ua_span) * y_span) + y_min
            f_ghz_residuals_span = np.max(f_ghz_plot_residuals) - np.min(f_ghz_plot_residuals)
            color_val = scalar_map.to_rgba(f_ghz_residuals_span)
            ax.plot(f_ghz_plot_residuals, ua_array_normalized_for_plot, color=color_val, linewidth=0.5)
        # reset the x limits, do not let the residuals dictate the x limits of this plot
        ax.set_xlim((x_min, x_max))

    # 'threads' of the rug plot
    ax.tick_params(axis="y", labelleft=False)
    for f_centers in xdata:
        f_len = len(f_centers)
        alpha = min(25.0 / f_len, 1.0)
        for f_center in list(f_centers):
            ax.plot((f_center, f_center), (y_min, y_max), ls='solid', linewidth=0.1, color=color, alpha=alpha)
    ax.set_ylim(bottom=0, top=1)
    ax.tick_params(axis='y',  # changes apply to the x-axis
                   which='both',  # both major and minor ticks are affected
                   left=False,  # ticks along the bottom edge are off
                   right=False,  # ticks along the top edge are off
                   labelleft=False)
    ax.tick_params(axis='x',  # changes apply to the x-axis
                   which='both',  # both major and minor ticks are affected
                   bottom=False,  # ticks along the bottom edge are off
                   top=True,  # ticks along the top edge are off
                   labelbottom=False,
                   labeltop=True)
    ax.xaxis.tick_top()
    ax.set_xlabel('X LABEL')
    ax.set_xlabel(F"Frequency (GHz)")
    ax.xaxis.set_label_position('top')
    return ax


def band_plot(ax, f_ghz, mag_dbm, f_centers_ghz_all, res_nums, band_str):
    # data math
    mag_dbm_mean = np.mean(mag_dbm)
    plot_s21_mag = mag_dbm - mag_dbm_mean
    plot_mag_min = np.min(plot_s21_mag)
    plot_mag_max = np.max(plot_s21_mag)
    ave_f_centers = [np.mean(f_centers) for f_centers in f_centers_ghz_all]
    # band boundary calculations
    band_dict = ref.band_params[band_str]
    trans = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
    in_band = [band_dict['min_GHz'] <= one_f <= band_dict['max_GHz'] for one_f in f_ghz]
    left_of_band = [one_f < band_dict['min_GHz'] for one_f in f_ghz]
    right_of_band = [band_dict['max_GHz'] < one_f for one_f in f_ghz]
    ax.fill_between((band_dict['min_GHz'], band_dict['max_GHz']), 0, 1,
                    facecolor='cornflowerblue', alpha=0.5, transform=trans)
    # the smurf keep out zones
    for keepout_min, keepout_max in ref.smurf_keepout_zones_ghz:
        ax.fill_between((keepout_min, keepout_max), 0, 1, facecolor='black', alpha=0.5, transform=trans)

    # the spectrum part of the plot
    ax.plot(f_ghz[in_band], plot_s21_mag[in_band], color="darkorchid", linewidth=1)
    ax.plot(f_ghz[left_of_band], plot_s21_mag[left_of_band], color="black", linewidth=1)
    ax.plot(f_ghz[right_of_band], plot_s21_mag[right_of_band], color="black", linewidth=1)

    # Key markers and labels
    res_labels = [res_num.replace("Res", "     ") for res_num in res_nums]
    res_nums_int = [int(res_num.replace("Res", "")) for res_num in res_nums]
    counter_f_ghz = 0
    counter_ave_centers = 0
    while counter_ave_centers < len(ave_f_centers) and counter_f_ghz < len(f_ghz):
        single_f_ghz = f_ghz[counter_f_ghz]
        single_f_center = ave_f_centers[counter_ave_centers]
        if single_f_center < single_f_ghz:
            # the point is trigger to plot the when the above is true
            marker = report_markers[res_nums_int[counter_ave_centers] % len(report_markers)]
            ax.plot(single_f_center, 0.0, color='black', alpha=0.5, marker=marker, markersize=10)
            ax.text(single_f_center, plot_mag_min, res_labels[counter_ave_centers], color='black', rotation=300,
                    horizontalalignment='center', verticalalignment='bottom', fontsize=8)
            counter_ave_centers += 1
        else:
            counter_f_ghz += 1
    # plot details
    ax.tick_params(axis="x", labelbottom=False)
    ax.set_ylabel("dB")
    ax.tick_params(axis='x',  # changes apply to the x-axis
                   which='both',  # both major and minor ticks are affected
                   bottom=False,  # ticks along the bottom edge are off
                   top=False,  # ticks along the top edge are off
                   labelbottom=False)
    ax.set_ylim(bottom=None, top=plot_mag_max)
    return ax


def report_key(ax, leglines, leglabels, summary_info, res_flags=None):
    ax.tick_params(axis='x',  # changes apply to the x-axis
                   which='both',  # both major and minor ticks are affected
                   bottom=False,  # ticks along the bottom edge are off
                   top=False,  # ticks along the top edge are off
                   labelbottom=False)
    ax.tick_params(axis='y',  # changes apply to the x-axis
                   which='both',  # both major and minor ticks are affected
                   left=False,  # ticks along the bottom edge are off
                   right=False,  # ticks along the top edge are off
                   labelleft=False)
    ax.text(0.5, 1, summary_info, color='black',
            horizontalalignment='center', verticalalignment='top', multialignment='left', fontsize=10)
    ax.set_xlim(left=0, right=1)
    ax.set_ylim(bottom=0, top=1)
    # ax.set_title("KEY")
    ax.legend(leglines, leglabels, loc=8, numpoints=5, handlelength=3, fontsize=10)
    if res_flags is not None:
        omitted_res = []
        for res_flag in res_flags:
            omitted_res.append([res_num_to_str(res_flag.seed_res_num), res_flag.type])
        ax.table(omitted_res, loc='center', fontsize=10)
    return ax


def report_plot_init(num_of_scatter_hist_x=3, num_of_scatter_hist_y=2):
    """
    Three Major Regions
      1) Top: Frequency Rug Plot 2) Middle: Resonator Spectrum  3) Bottom: Scatter plots with side histograms
          definitions for the axes

    :param num_of_scatter_hist_x: int
    :param num_of_scatter_hist_y: int
    :return:
    """
    left = 0.05
    bottom = 0.05
    right = 0.99
    top = 0.95

    major12_region_spacing = 0.000
    major32_region_spacing = 0.001

    major_regions_y = (0.50, top - 0.15)

    key_margin_x = 0.85
    key_space = 0.003

    scatter_hist_little_space = 0.005
    scatter_hist_bigger_vspace = 0.005
    scatter_hist_bigger_hspace = 0.060
    scatter_to_hist_ratio = 1.6
    # 0) A plot used as a Key
    key_top = top
    key_bottom = major_regions_y[0] + major32_region_spacing
    key_height = key_top - key_bottom
    key_left = key_margin_x + key_space
    key_right = right
    key_width = key_right - key_left
    key_cood = [key_left, key_bottom, key_width, key_height]

    # 1) Top: Frequency Rug Plot
    rug_top = top
    rug_bottom = major_regions_y[1] + major12_region_spacing
    rug_height = rug_top - rug_bottom
    rug_left = left
    rug_right = key_margin_x - key_space
    rug_width = rug_right - rug_left
    rug_cood = [rug_left, rug_bottom, rug_width, rug_height]

    # 2) Middle: Resonator Spectrum
    res_spec_top = major_regions_y[1] - major12_region_spacing
    res_spec_bottom = major_regions_y[0] + major32_region_spacing
    res_spec_height = res_spec_top - res_spec_bottom
    res_spec_left = left
    res_spec_right = key_margin_x - key_space
    res_spec_width = res_spec_right - res_spec_left
    res_spec_cood = [res_spec_left, res_spec_bottom, res_spec_width, res_spec_height]

    # 3) Bottom:Scatter plots with side histograms
    shist_top = major_regions_y[0] - major32_region_spacing

    available_plot_y_per_histogram = (((shist_top - bottom) - ((num_of_scatter_hist_y - 1) * scatter_hist_bigger_vspace))
                                      / num_of_scatter_hist_y)
    available_plot_x_per_histogram = (((right - left) - ((num_of_scatter_hist_x - 1) * scatter_hist_bigger_hspace))
                                      / num_of_scatter_hist_x) - scatter_hist_little_space
    scat_width = available_plot_x_per_histogram * scatter_to_hist_ratio / (scatter_to_hist_ratio + 1.0)
    hist_width = available_plot_x_per_histogram - scat_width
    hist_coords = []
    scatter_coords = []
    for yhist_index in range(num_of_scatter_hist_y):
        shist_bottom = shist_top - available_plot_y_per_histogram
        shist_height = shist_top - shist_bottom
        scat_left = left
        for xhist_index in range(num_of_scatter_hist_x):
            hist_left = scat_left + scat_width + scatter_hist_little_space
            scatter_coords.append([scat_left, shist_bottom, scat_width, shist_height])
            hist_coords.append([hist_left, shist_bottom, hist_width, shist_height])
            scat_left = hist_left + hist_width + scatter_hist_bigger_hspace
        shist_top = shist_bottom - scatter_hist_bigger_vspace

    # initialize the plot
    fig = plt.figure(figsize=(25, 10))
    ax_key = fig.add_axes(key_cood, frameon=False)
    ax_res_spec = fig.add_axes(res_spec_cood, frameon=False)
    ax_rug = fig.add_axes(rug_cood, sharex=ax_res_spec, frameon=False)
    axes_scatter = [fig.add_axes(scatter_cood, sharex=ax_res_spec, frameon=False) for scatter_cood in scatter_coords]
    axes_hist = [fig.add_axes(hist_coord, sharey=ax_scatter, frameon=False)
                 for hist_coord, ax_scatter in zip(hist_coords, axes_scatter)]
    axes_shist = [(ax_scatter, ax_hist) for ax_scatter, ax_hist in zip(axes_scatter, axes_hist)]
    return fig, ax_key, ax_res_spec, ax_rug, axes_shist


def f_ghz_from_lambda_fit(lambda_fit, ua_array):
    def lamb_fit_these_params(ua):
        f_ghz = f0_of_I(ramp_current_amps=ua * 1.0e-6, ramp_current_amps_0=lambda_fit.i0fit,
                        m=lambda_fit.mfit, f2=lambda_fit.f2fit, P=lambda_fit.pfit, lamb=lambda_fit.lambfit)
        return f_ghz
    return np.fromiter(map(lamb_fit_these_params, ua_array), dtype=float)


def single_lamb_to_report_plot(axes, res_set, color, leglines, leglabels, band_str, flag_table_info, ordered_res_strs,
                               markersize=8, alpha=0.5):
    summary_info = {}
    # check to make sure we have date for all the requested resonator numbers
    for res_str in list(ordered_res_strs):
        if not hasattr(res_set, res_str):
            ordered_res_strs.remove(res_str)
            if "lost_res_nums" in summary_info.keys():
                summary_info["lost_res_nums"].add(res_str)
            else:
                summary_info["lost_res_nums"] = {res_str}

    # do some data analysis
    lamb_values = np.array([res_set.__getattribute__(res_str).lamb_fit.lambfit for res_str in ordered_res_strs])
    lamb_value_errs = np.array([res_set.__getattribute__(res_str).lamb_fit.lambfit_err
                                for res_str in ordered_res_strs])
    flux_ramp_pp_khz = np.array([res_set.__getattribute__(res_str).lamb_fit.pfit * 1.0e6
                                 for res_str in ordered_res_strs])
    flux_ramp_pp_khz_errs = np.array([res_set.__getattribute__(res_str).lamb_fit.pfit_err * 1.0e6
                                      for res_str in ordered_res_strs])
    conversion_factor = (ref.phi_0 / (2.0 * np.pi)) * 1.0e12
    fr_squid_mi_pH = np.array([res_set.__getattribute__(res_str).lamb_fit.mfit * conversion_factor
                               for res_str in ordered_res_strs])
    fr_squid_mi_pH_err = np.array([res_set.__getattribute__(res_str).lamb_fit.mfit_err * conversion_factor
                                   for res_str in ordered_res_strs])
    port_powers_dbm = np.array([res_set.__getattribute__(res_str).metadata["port_power_dbm"]
                                for res_str in ordered_res_strs])
    # This should be a real calibration not this hacky one size fits all subtraction, I hate that I wrote this
    at_res_power_dbm = []
    for res_str, port_power_dbm in zip(ordered_res_strs, port_powers_dbm):
        wafer_num = res_set.__getattribute__(res_str).metadata["wafer"]
        if wafer_num < 12.5:
            # with warm 20 dBm attenuator that make the VNA output unleveled
            at_res_power_dbm.append(port_power_dbm - 75.0)
        else:
            # no warm 20 dBm attenuator on the input
            at_res_power_dbm.append(port_power_dbm - 55.0)
    at_res_power_dbm_mean = np.mean(at_res_power_dbm)

    # initialize some useful parameters
    f_centers_ghz_all = []
    f_centers_ghz_mean = []
    f_centers_ghz_std = []
    q_i_mean = []
    q_i_std = []
    q_c_mean = []
    q_c_std = []
    impedance_ratio_mean = []
    impedance_ratio_std = []
    non_linear_mean = []
    non_linear_std = []
    for res_str in ordered_res_strs:
        single_lamb = res_set.__getattribute__(res_str)
        f_centers_this_lamb = np.array([res_params.fcenter_ghz for res_params in single_lamb.res_fits])
        f_centers_ghz_all.append(f_centers_this_lamb)
        f_centers_ghz_mean.append(np.mean(f_centers_this_lamb))
        f_centers_ghz_std.append(np.std(f_centers_this_lamb))

        q_is_this_lamb = np.array([res_params.q_i for res_params in single_lamb.res_fits])
        q_i_mean.append(np.mean(q_is_this_lamb))
        q_i_std.append(np.std(q_is_this_lamb))

        q_cs_this_lamb = np.array([res_params.q_c for res_params in single_lamb.res_fits])
        q_c_mean.append(np.mean(q_cs_this_lamb))
        q_c_std.append(np.std(q_cs_this_lamb))

        impedance_ratios_this_lamb = np.array([res_params.impedance_ratio for res_params in single_lamb.res_fits])
        impedance_ratio_mean.append(np.mean(impedance_ratios_this_lamb))
        impedance_ratio_std.append(np.std(impedance_ratios_this_lamb))

        non_linear_this_lamb = np.array([res_params.base_amplitude_slope for res_params in single_lamb.res_fits])
        non_linear_mean.append(np.mean(non_linear_this_lamb))
        non_linear_std.append(np.std(non_linear_this_lamb))

    f_centers_ghz_mean = np.array(f_centers_ghz_mean)
    f_centers_ghz_std = np.array(f_centers_ghz_std)
    q_i_mean = np.array(q_i_mean)
    q_i_std = np.array(q_i_std)
    q_c_mean = np.array(q_c_mean)
    q_c_std = np.array(q_c_std)
    impedance_ratio_mean = np.array(impedance_ratio_mean)
    impedance_ratio_std = np.array(impedance_ratio_std)
    f_spacings_ghz = f_centers_ghz_mean[1:] - f_centers_ghz_mean[:-1]
    res_nums_int = [int(res_str.replace("Res", "")) for res_str in ordered_res_strs]
    # lambda dfpp is the "delta frequency peak to peak", it is identical to "flux ramp span".
    lambda_corrected_dfpp_khz = flux_ramp_pp_khz * (1.0 - lamb_values**2.0)
    lambda_corrected_dfpp_khz_errs = lambda_corrected_dfpp_khz * ((flux_ramp_pp_khz_errs/flux_ramp_pp_khz) +
                                                                  ((lamb_value_errs/lamb_values)**2.0))

    # Lambda fit residuals
    # if -78.0 <= at_res_power_dbm_mean <= -72.0:
    lambda_fits_for_resonators = [res_set.__getattribute__(res_str).lamb_fit for res_str in ordered_res_strs]
    ua_arrays_for_resonators = []
    f_ghz_arrays_for_resonators = []
    for res_str in ordered_res_strs:
        res_fits_per_resonator_number = res_set.__getattribute__(res_str).res_fits
        ua_arrays_for_resonators.append(np.array([single_res_params.flux_ramp_current_ua
                                                  for single_res_params in res_fits_per_resonator_number]))
        f_ghz_arrays_for_resonators.append(np.array([single_res_params.fcenter_ghz
                                                     for single_res_params in res_fits_per_resonator_number]))
    f_ghz_fit_arrays_for_resonators = list(map(f_ghz_from_lambda_fit, lambda_fits_for_resonators,
                                               ua_arrays_for_resonators))
    f_ghz_residuals_for_resonators = [f_ghz - f_ghz_fits for f_ghz, f_ghz_fits
                                      in zip(f_ghz_arrays_for_resonators, f_ghz_fit_arrays_for_resonators)]

    # chi squared
    chi_squared_for_resonators = [chisquare(f_obs=f_ghz, f_exp=f_ghz_fits) for f_ghz, f_ghz_fits
                                  in zip(f_ghz_arrays_for_resonators, f_ghz_fit_arrays_for_resonators)]
    # get ready to export some of the calculations to update metadata for these resonators.
    series_calc_metadata = {}
    # test if the resonators are in the requested export ranges
    if -78.0 <= at_res_power_dbm_mean <= -72.0:
        for res_index, res_str in list(enumerate(ordered_res_strs)):
            series_calc_metadata[res_str] = CalcMetadataAtNeg75dbm(lamb=lamb_values[res_index],
                                                                   lamb_err=lamb_value_errs[res_index],
                                                                   flux_ramp_pp_khz=flux_ramp_pp_khz[res_index],
                                                                   flux_ramp_pp_khz_err=flux_ramp_pp_khz_errs[
                                                                       res_index],
                                                                   fr_squid_mi_pH=fr_squid_mi_pH[res_index],
                                                                   fr_squid_mi_pH_err=fr_squid_mi_pH_err[res_index],
                                                                   chi_squared=chi_squared_for_resonators[res_index][0],
                                                                   q_i_mean=q_i_mean[res_index],
                                                                   q_i_std=q_i_std[res_index],
                                                                   q_c_mean=q_c_mean[res_index],
                                                                   q_c_std=q_c_std[res_index],
                                                                   impedance_ratio_mean=impedance_ratio_mean[res_index])
    elif -98.0 <= at_res_power_dbm_mean <= -92.0:
        for res_index, res_str in list(enumerate(ordered_res_strs)):
            series_calc_metadata[res_str] = CalcMetadataAtNeg95dbm(lamb=lamb_values[res_index],
                                                                   lamb_err=lamb_value_errs[res_index],
                                                                   flux_ramp_pp_khz=flux_ramp_pp_khz[res_index],
                                                                   flux_ramp_pp_khz_err=flux_ramp_pp_khz_errs[
                                                                       res_index],
                                                                   fr_squid_mi_pH=fr_squid_mi_pH[res_index],
                                                                   fr_squid_mi_pH_err=fr_squid_mi_pH_err[res_index],
                                                                   chi_squared=chi_squared_for_resonators[res_index][0],
                                                                   q_i_mean=q_i_mean[res_index],
                                                                   q_i_std=q_i_std[res_index],
                                                                   q_c_mean=q_c_mean[res_index],
                                                                   q_c_std=q_c_std[res_index],
                                                                   impedance_ratio_mean=impedance_ratio_mean[res_index])

    """ 
    The residuals should be near zero by definition (for good fits). For display purposes we will want to shift 
    them so the that their average value is the f_ghz_mean for a given resonator instead of around zero. 
    """
    f_ghz_residuals_for_res_plot_shifted = [f_center_ghz - (1.0e3 * f_ghz_residuals)
                                            for f_center_ghz,  f_ghz_residuals
                                            in zip(f_centers_ghz_mean, f_ghz_residuals_for_resonators)]
    # else:
    #     f_ghz_residuals_for_res_plot_shifted = None
    #     ua_arrays_for_resonators = None

    # Qi
    q_i_label = F"Qi (Quality Factor)"
    ax_scatter_q_i, ax_hist_q_i = axes[0]
    if -78.0 <= at_res_power_dbm_mean <= -72.0:
        ax_scatter_q_i, res_nums_too_low_q_i,  res_nums_too_high_q_i = \
            error_bar_report_plot(ax=ax_scatter_q_i, xdata=f_centers_ghz_mean, ydata=q_i_mean, yerr=q_i_std,
                                  res_nums_int=res_nums_int,
                                  color=color, ls='None', markersize=markersize, alpha=alpha,
                                  x_label=None, y_label=q_i_label, x_ticks_on=False,
                                  min_y=ref.min_q_i, max_y=None, average_y=None)
    else:
        ax_scatter_q_i, res_nums_too_low_q_i, res_nums_too_high_q_i = \
            error_bar_report_plot(ax=ax_scatter_q_i, xdata=f_centers_ghz_mean, ydata=q_i_mean, yerr=q_i_std,
                                  res_nums_int=res_nums_int,
                                  color=color, ls='None', markersize=markersize, alpha=alpha,
                                  x_label=None, y_label=q_i_label, x_ticks_on=False,
                                  min_y=None, max_y=None, average_y=None)

    hist_report_plot(ax=ax_hist_q_i, data=q_i_mean, bins=10, color=color, x_label=None, y_label=None, alpha=alpha)
    ax_scatter_q_i.tick_params(axis='x',  # changes apply to the x-axis
                               which='both',  # both major and minor ticks are affected
                               bottom=False,  # ticks along the bottom edge are off
                               top=False)

    # Qc
    q_c_label = F"Qc (Quality Factor)"
    ax_scatter_q_c, ax_hist_q_c = axes[1]
    ax_scatter_q_c, res_nums_too_low_q_c,  res_nums_too_high_q_c = \
        error_bar_report_plot(ax=ax_scatter_q_c, xdata=f_centers_ghz_mean, ydata=q_c_mean, yerr=q_c_std,
                              res_nums_int=res_nums_int,
                              color=color, ls='None', markersize=markersize, alpha=alpha,
                              x_label=None, y_label=q_c_label, x_ticks_on=False)
    hist_report_plot(ax=ax_hist_q_c, data=q_c_mean, bins=10, color=color, x_label=None, y_label=None, alpha=alpha)
    ax_scatter_q_c.tick_params(axis='x',  # changes apply to the x-axis
                               which='both',  # both major and minor ticks are affected
                               bottom=False,  # ticks along the bottom edge are off
                               top=False)  # ticks along the top edge are off

    # Impedance Ratio (Z ratio)
    zratio_label = F"Impedance Ratio (Z ratio)"
    ax_scatter_zratio, ax_hist_zratio = axes[2]
    ax_scatter_zratio, res_nums_too_low_zratio, res_nums_too_high_zratio = \
        error_bar_report_plot(ax=ax_scatter_zratio, xdata=f_centers_ghz_mean,
                              ydata=impedance_ratio_mean, yerr=impedance_ratio_std, res_nums_int=res_nums_int,
                              color=color, ls='None', markersize=markersize, alpha=alpha,
                              x_label=None, y_label=zratio_label, x_ticks_on=False)
    hist_report_plot(ax=ax_hist_zratio, data=impedance_ratio_mean, bins=10, color=color,
                     x_label=None, y_label=None, alpha=alpha)
    ax_scatter_zratio.tick_params(axis='x',  # changes apply to the x-axis
                                  which='both',  # both major and minor ticks are affected
                                  bottom=False,  # ticks along the bottom edge are off
                                  top=False)

    # Lambda (SQUID parameter lambda)
    lamb_label = F"SQUID parameter lambda"
    ax_scatter_lamb, ax_hist_lamb = axes[3]
    if -98.0 <= at_res_power_dbm_mean <= -92.0:
        ax_scatter_lamb, res_nums_too_low_lamb, res_nums_too_high_lamb = \
            error_bar_report_plot(ax=ax_scatter_lamb, xdata=f_centers_ghz_mean,
                                  ydata=lamb_values, yerr=lamb_value_errs, res_nums_int=res_nums_int,
                                  color=color, ls='None', markersize=markersize, alpha=alpha,
                                  x_label=None, y_label=lamb_label, x_ticks_on=False,
                                  min_y=ref.min_lambda, max_y=ref.max_lambda, average_y=ref.average_lambda)
    else:
        ax_scatter_lamb, res_nums_too_low_lamb, res_nums_too_high_lamb = \
            error_bar_report_plot(ax=ax_scatter_lamb, xdata=f_centers_ghz_mean,
                                  ydata=lamb_values, yerr=lamb_value_errs, res_nums_int=res_nums_int,
                                  color=color, ls='None', markersize=markersize, alpha=alpha,
                                  x_label=None, y_label=lamb_label, x_ticks_on=True,
                                  min_y=None, max_y=None, average_y=None)
    hist_report_plot(ax=ax_hist_lamb, data=lamb_values, bins=10, color=color, x_label=None, y_label=None, alpha=alpha)

    # Flux Ramp Span (peak-to-peak fit parameter)
    flux_ramp_label = F"d_fpp - Flux Ramp Span (kHz)"
    ax_scatter_flux_ramp, ax_hist_flux_ramp = axes[4]
    if -78.0 <= at_res_power_dbm_mean <= -72.0:
        ax_scatter_flux_ramp, res_nums_too_low_flux_ramp, res_nums_too_high_flux_ramp = \
            error_bar_report_plot(ax=ax_scatter_flux_ramp, xdata=f_centers_ghz_mean,
                                  ydata=flux_ramp_pp_khz, yerr=flux_ramp_pp_khz_errs, res_nums_int=res_nums_int,
                                  color=color, ls='None', markersize=markersize, alpha=alpha,
                                  x_label=None, y_label=flux_ramp_label, x_ticks_on=True,
                                  min_y=ref.peak_to_peak_shift_hz, max_y=None, average_y=None)
    else:
        ax_scatter_flux_ramp, res_nums_too_low_flux_ramp, res_nums_too_high_flux_ramp = \
            error_bar_report_plot(ax=ax_scatter_flux_ramp, xdata=f_centers_ghz_mean,
                                  ydata=flux_ramp_pp_khz, yerr=flux_ramp_pp_khz_errs, res_nums_int=res_nums_int,
                                  color=color, ls='None', markersize=markersize, alpha=alpha,
                                  x_label=None, y_label=flux_ramp_label, x_ticks_on=True)
    hist_report_plot(ax=ax_hist_flux_ramp, data=flux_ramp_pp_khz, bins=10, color=color,
                     x_label=None, y_label=None, alpha=alpha)

    # fr_squid_mi_pH
    fr_squid_mi_pH_label = F"FR - SQUID Mutual Inductance (pH)"
    ax_scatter_fr_squid, ax_hist_fr_squid = axes[5]
    ax_scatter_fr_squid, res_nums_too_low_fr_squid, res_nums_too_high_fr_squid = \
        error_bar_report_plot(ax=ax_scatter_fr_squid, xdata=f_centers_ghz_mean,
                              ydata=fr_squid_mi_pH, yerr=fr_squid_mi_pH_err, res_nums_int=res_nums_int,
                              color=color, ls='None', markersize=markersize, alpha=alpha,
                              x_label=None, y_label=fr_squid_mi_pH_label, x_ticks_on=True)
    hist_report_plot(ax=ax_hist_fr_squid, data=fr_squid_mi_pH, bins=10, color=color,
                     x_label=None, y_label=None, alpha=alpha)

    lambda_corrected_dfpp_label = F"lambda Corrected d_fpp (kHz)"
    ax_scatter_lambda_corrected_dfpp, ax_hist_lambda_corrected_dfpp = axes[6]
    ax_scatter_lambda_corrected_dfpp, res_nums_too_low_lambda_corrected_dfpp, \
        res_nums_too_high_lambda_corrected_dfpp = \
        error_bar_report_plot(ax=ax_scatter_lambda_corrected_dfpp, xdata=f_centers_ghz_mean,
                              ydata=lambda_corrected_dfpp_khz, yerr=lambda_corrected_dfpp_khz_errs,
                              res_nums_int=res_nums_int,
                              color=color, ls='None', markersize=markersize, alpha=alpha,
                              x_label=None, y_label=lambda_corrected_dfpp_label, x_ticks_on=True)
    hist_report_plot(ax=ax_hist_lambda_corrected_dfpp, data=lambda_corrected_dfpp_khz, bins=10, color=color,
                     x_label=None, y_label=None, alpha=alpha)

    # chi Squared
    chi_squared_label = F"chi squared"
    ax_scatter_chi_squared, ax_hist_chi_squared = axes[7]
    ax_scatter_chi_squared, res_nums_too_high_chi_squared = \
        chi_squared_plot(ax=ax_scatter_chi_squared, f_ghz_mean=f_centers_ghz_mean,
                         chi_squared_for_resonators=chi_squared_for_resonators,  res_nums_int=res_nums_int,
                         color=color, markersize=markersize, alpha=alpha,
                         x_label=None, y_label=chi_squared_label, x_ticks_on=True, max_chi_squared=None)

    hist_report_plot(ax=ax_hist_chi_squared,
                     data=[chi_squared_result.statistic for chi_squared_result in chi_squared_for_resonators],
                     bins=10, color=color, x_label=None, y_label=None, alpha=alpha)

    # legend and Yield calculations
    summary_info["f_spacings_ghz"] = list(f_spacings_ghz)

    # in-band calculations (not counted against yield)
    band_min_ghz = ref.band_params[band_str]['min_GHz']
    band_max_ghz = ref.band_params[band_str]['max_GHz']
    summary_info["res_nums_in_band"] = {res_num_str for f_center, res_num_str
                                        in zip(f_centers_ghz_mean, ordered_res_strs)
                                        if band_min_ghz <= f_center <= band_max_ghz}
    # resonators in the smurf keepout zones (counts against yield)
    res_nums_in_keepout_zones = set()
    for keepout_min, keepout_max in ref.smurf_keepout_zones_ghz:
        [res_nums_in_keepout_zones.add(res_num_str)
         for f_center, res_num_str in zip(f_centers_ghz_mean, ordered_res_strs)
         if keepout_min <= f_center <= keepout_max]
    summary_info["res_nums_in_keepout_zones"] = res_nums_in_keepout_zones

    # Screening Criteria Flags (counts against yield)
    for res_nums_too_low, res_nums_too_high, criteria_name in [(res_nums_too_low_q_i, res_nums_too_high_q_i, "Qi"),
                                                               (res_nums_too_low_q_c, res_nums_too_high_q_c, "Qc"),
                                                               (res_nums_too_low_zratio, res_nums_too_high_zratio, "Z ratio"),
                                                               (res_nums_too_low_lamb, res_nums_too_high_lamb, "Lambda"),
                                                               (res_nums_too_low_flux_ramp, res_nums_too_high_flux_ramp, "peak-to-peak"),
                                                               (res_nums_too_low_fr_squid, res_nums_too_high_fr_squid, "FR squid"),
                                                               (res_nums_too_low_lambda_corrected_dfpp, res_nums_too_high_lambda_corrected_dfpp, "A")]:
        flag_table_info = criteria_flagged_summary(flag_table_info=flag_table_info, criteria_name=criteria_name,
                                                   res_numbers=res_nums_too_low, too_low=True)
        flag_table_info = criteria_flagged_summary(flag_table_info=flag_table_info, criteria_name=criteria_name,
                                                   res_numbers=res_nums_too_high, too_low=False)
    # Combined criteria for yield calculation
    summary_info["criteria_flagged_resonator_numbers"] = res_nums_too_low_q_i | res_nums_too_high_q_i | \
                                                         res_nums_too_low_q_c | res_nums_too_high_q_c | \
                                                         res_nums_too_low_zratio | res_nums_too_high_zratio | \
                                                         res_nums_too_low_lamb | res_nums_too_high_lamb | \
                                                         res_nums_too_low_flux_ramp | res_nums_too_high_flux_ramp | \
                                                         res_nums_too_low_fr_squid | res_nums_too_high_fr_squid | \
                                                         res_nums_too_low_lambda_corrected_dfpp | res_nums_too_high_lambda_corrected_dfpp | \
                                                         res_nums_too_high_chi_squared
    # legend lines and label
    leglines.append(plt.Line2D(range(12), range(12), color=color, ls='None',
                               marker='o', markersize=markersize, markerfacecolor=color, alpha=alpha))
    power = res_set.series_key.port_power_dbm
    leglabels.append(F"{'%4i' % at_res_power_dbm_mean} est., {'%4i' % power} port (dBm)")
    return axes, leglines, leglabels, f_centers_ghz_all, ordered_res_strs, summary_info, flag_table_info, \
        f_ghz_residuals_for_res_plot_shifted, ua_arrays_for_resonators, series_calc_metadata


def report_plot(series_res_sets, sorted_series_handles, wafer_str, chip_id_str, seed_scan_path, report_dir,
                markersize=8, alpha=0.5,
                show=False, omit_flagged=False, save=True, return_fig=False):
    fig, ax_key, ax_res_spec, ax_rug, axes_shist = report_plot_init(num_of_scatter_hist_x=4, num_of_scatter_hist_y=2)
    band_num, x_pos, y_pos = chip_id_str_to_chip_id_tuple(chip_id_str)
    # one of Hannes' design element requests that differs slightly from the more general
    # string formatting of chip_id designed for robust for comparison and sorting.
    if x_pos is None or y_pos is None:
        hannes_formatted_chip_id = F"{band_num_to_str(band_num)}"
    else:
        hannes_formatted_chip_id = F"{band_num_to_str(band_num)} ({'%i' % x_pos},{'%i' % y_pos})"
    fig.suptitle(F"{wafer_str} {hannes_formatted_chip_id} report:", y=0.995, x=0.98, horizontalalignment='right')
    leglines = []
    leglabels = []
    counter = 0
    rug_y_increment = 1.0 / len(sorted_series_handles)

    f_centers_ghz_all = []
    res_nums = []
    wafer_num = wafer_str_to_num(wafer_str)

    band_str = band_num_to_str(band_num)
    if omit_flagged and wafer_num in flagged_data.wafer_band_flags.keys() \
            and band_num in flagged_data.wafer_band_flags[wafer_num].keys():
        res_flags = flagged_data.wafer_band_flags[wafer_num][band_num]
        res_nums_user_flagged = {res_flag.seed_res_num for res_flag in res_flags}
    else:
        res_flags = None
        res_nums_user_flagged = None

    # total resonators identified
    available_res_nums = set()
    for series_handle in sorted_series_handles:
        available_res_nums.update(series_res_sets[series_handle].available_res_nums)
    # load the user flagged data
    if res_nums_user_flagged is None:
        res_nums_user_flagged = set()
    else:
        res_nums_user_flagged = {res_num_to_str(res_num) for res_num in res_nums_user_flagged}

    # error bar plots and histograms with dynamic criteria flagging
    flag_table_info = {}
    total_summary_info = {}
    calc_metadata = {}
    for series_handle in sorted_series_handles:
        res_set = series_res_sets[series_handle]
        color = report_colors[counter % len(report_colors)]
        axes_shist, leglines, leglabels, f_centers_ghz_all, res_nums, summary_info, flag_table_info, \
            f_ghz_residuals_for_res_plot_shifted, ua_arrays_for_resonators, series_calc_metadata \
            = single_lamb_to_report_plot(axes=axes_shist, res_set=res_set, color=color, band_str=band_str,
                                         leglines=leglines, leglabels=leglabels, flag_table_info=flag_table_info,
                                         ordered_res_strs=sorted(available_res_nums - res_nums_user_flagged),
                                         markersize=markersize, alpha=alpha)
        calc_metadata[series_handle] = series_calc_metadata
        # rug plot
        y_max = 1.0 - (rug_y_increment * counter)
        counter += 1
        y_min = 1.0 - (rug_y_increment * counter)
        ax_rug = rug_plot(ax=ax_rug, xdata=f_centers_ghz_all, y_min=y_min, y_max=y_max, color=color,
                          f_ghz_residuals_for_res_plot_shifted=f_ghz_residuals_for_res_plot_shifted,
                          ua_arrays_for_resonators=ua_arrays_for_resonators)
        for summary_key in summary_info.keys():
            if summary_key in total_summary_info.keys():
                if summary_key in {"f_spacings_ghz"}:
                    total_summary_info[summary_key].extend(summary_info[summary_key])
                else:
                    total_summary_info[summary_key].update(summary_info[summary_key])
            else:
                total_summary_info[summary_key] = summary_info[summary_key]
    # Flag table update
    for res_str in total_summary_info['res_nums_in_keepout_zones']:
        if res_str in flag_table_info.keys():
            flag_table_info[res_str] += "\nIn keepout zone."
        else:
            flag_table_info[res_str] = "In keepout zone."
    # Raw S21 Scan data
    x_min, x_max = ax_rug.get_xlim()
    formatted_s21_dict, metadata = read_s21(path=seed_scan_path)
    f_ghz = formatted_s21_dict["freq_ghz"]
    s21_mag, _s21_phase = ri_to_magphase(r=formatted_s21_dict["real"], i=formatted_s21_dict["imag"])
    indexes_to_plot = np.where((f_ghz >= x_min) & (f_ghz <= x_max))
    ax_res_spec = band_plot(ax=ax_res_spec, f_ghz=f_ghz[indexes_to_plot], mag_dbm=s21_mag[indexes_to_plot],
                            f_centers_ghz_all=f_centers_ghz_all, res_nums=res_nums, band_str=band_str)
    ax_res_spec.set_xlim(left=x_min, right=x_max)

    # Plot KEY
    # add the out-of-bounds legend key
    # Total Yield calculations
    res_nums_flagged = res_nums_user_flagged | total_summary_info["res_nums_in_keepout_zones"] | \
                       total_summary_info["criteria_flagged_resonator_numbers"]
    res_nums_passed = available_res_nums - res_nums_flagged
    num_usable = len(res_nums_passed)

    # build the strings for the report summary
    if res_nums_user_flagged is None:
        num_expected = 65
        yield_str = ""
    else:
        num_expected = 64
        yield_percent = 100.0 * num_usable / num_expected
        yield_str = F"Yield:{'%5.1f' % yield_percent}% "
    yield_str = F"{yield_str}{num_usable}/{num_expected} accepted"
    found_str = F"{len(available_res_nums)} identified, {len(res_nums_user_flagged)} user flagged"
    in_band_str = F"{len(total_summary_info['res_nums_in_band'])} in-band"
    in_keepout = F"{len(total_summary_info['res_nums_in_keepout_zones'])} in SMURF Keepout"
    f_spacings_mhz_median = np.median(np.array(total_summary_info["f_spacings_ghz"])) * 1.0e3
    spacing = F"{'%5.3f' % f_spacings_mhz_median} MHz median spacing"
    yield_criteria_flagged = F"{len(total_summary_info['criteria_flagged_resonator_numbers'])} outside yield criteria"
    summary_paragraph = F"{yield_str}\n{found_str}\n{in_band_str}, {in_keepout}\n{spacing}\n{yield_criteria_flagged}"
    # legend lines and labels
    leglabels.append("Criteria Flag")
    leglines.append(plt.Line2D(range(10), range(10), color="black", ls='None',
                               marker='x', markersize=markersize - 2, markerfacecolor="black", alpha=1.0))
    # add the boundary and average lines to the legend
    leglabels.append("Maximum")
    leglines.append(plt.Line2D(range(10), range(10), color='red', ls='dashdot'))
    leglabels.append("Target")
    leglines.append(plt.Line2D(range(10), range(10), color='green', ls='dotted'))
    leglabels.append("Minimum")
    leglines.append(plt.Line2D(range(10), range(10), color='red', ls='dashed'))
    ax_key = report_key(ax=ax_key, leglines=leglines, leglabels=leglabels,
                        summary_info=summary_paragraph, res_flags=res_flags)
    # Display
    # another special case of string formatting for Hannes.
    hannes_formatted_chip_id = hannes_formatted_chip_id.replace(" ", "_")
    if res_nums_user_flagged is None:
        scatter_plot_basename = F"ScatterHist_{hannes_formatted_chip_id}_{wafer_str}"
    else:
        scatter_plot_basename = F"ScatterHist_{hannes_formatted_chip_id}_{wafer_str}_curated"
    scatter_plot_path = os.path.join(report_dir, scatter_plot_basename)
    plt.draw()
    if show:
        plt.show(block=True)
    if save:
        for extension in [".pdf", ".png"]:
            plt.savefig(scatter_plot_path + extension)
        print("Saved Plot to:", scatter_plot_path)
    if return_fig:
        return fig, flag_table_info, calc_metadata
    else:
        plt.close(fig=fig)
        return None, flag_table_info, calc_metadata


if __name__ == "__main__":
    report_plot_init(num_of_scatter_hist_x=3, num_of_scatter_hist_y=2)
    plt.show()
