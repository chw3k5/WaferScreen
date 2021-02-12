import numpy as np
from waferscreen.analyze.lambfit import phi_0
import matplotlib.pyplot as plt


def error_bar_report_plot(ax, xdata, ydata, yerr, color="black", ls='None', marker="o", markersize=10, alpha=0.7,
                          x_label=None, y_label=None):
    ax.errorbar(xdata, ydata, yerr=yerr,
                color=color, ls=ls, marker=marker, markersize=markersize, alpha=alpha)
    if x_label is None:
        ax.set_xlabel("Average Resonator Center Frequency (GHz)")
    else:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)
    return ax


def hist_report_plot(ax, data, bins=10, color="blue", x_label=None, y_label=None):
    ax.hist(data, bins=bins, color=color)
    if x_label is not None:
        ax.set_xlabel(x_label)
    if y_label is None:
        ax.set_ylabel("Resonators per Bin")
    else:
        ax.set_ylabel(y_label)
    ax.grid(True)
    return ax


def single_lamp_to_report_plot(axes, res_set, color, leglines, leglabels, markersize=8, alpha=0.7):
    available_res_nums = res_set.available_res_nums
    # do some data analysis
    ordered_res_strs = sorted(available_res_nums)
    lamb_values = np.array([res_set.__getattribute__(res_str).lamb_fit.lambfit for res_str in ordered_res_strs])
    lamb_value_errs = np.array([res_set.__getattribute__(res_str).lamb_fit.lambfit_err
                                for res_str in ordered_res_strs])
    flux_ramp_pp_khz = np.array([res_set.__getattribute__(res_str).lamb_fit.pfit * 1.0e6
                                 for res_str in ordered_res_strs])
    flux_ramp_pp_khz_errs = np.array([res_set.__getattribute__(res_str).lamb_fit.pfit_err * 1.0e6
                                      for res_str in ordered_res_strs])
    conversion_factor = (phi_0 / (2.0 * np.pi)) * 1.0e12
    fr_squid_mi_pH = np.array([res_set.__getattribute__(res_str).lamb_fit.mfit * conversion_factor
                               for res_str in ordered_res_strs])
    fr_squid_mi_pH_err = np.array([res_set.__getattribute__(res_str).lamb_fit.mfit_err * conversion_factor
                                   for res_str in ordered_res_strs])
    # initialize some useful parameters
    f_centers_ghz_mean = []
    f_centers_ghz_std = []
    q_i_mean = []
    q_i_std = []
    q_c_mean = []
    q_c_std = []
    impedance_ratio_mean = []
    impedance_ratio_std = []
    for res_str in ordered_res_strs:
        single_lamb = res_set.__getattribute__(res_str)
        f_centers_this_lamb = np.array([res_params.fcenter_ghz for res_params in single_lamb.res_fits])
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
    f_centers_ghz_mean = np.array(f_centers_ghz_mean)
    f_centers_ghz_std = np.array(f_centers_ghz_std)
    q_i_mean = np.array(q_i_mean)
    q_i_std = np.array(q_i_std)
    q_c_mean = np.array(q_c_mean)
    q_c_std = np.array(q_c_std)
    impedance_ratio_mean = np.array(impedance_ratio_mean)
    impedance_ratio_std = np.array(impedance_ratio_std)
    f_spacings_ghz = f_centers_ghz_mean[1:] - f_centers_ghz_mean[:-1]
    f_spacings_mhz_mean = np.mean(f_spacings_ghz) * 1.0e3
    f_spacings_mhz_std = np.std(f_spacings_ghz) * 1.0e3


    # Qi
    q_i_label = F"Qi (Quality Factor)"
    error_bar_report_plot(ax=axes[0, 0], xdata=f_centers_ghz_mean, ydata=q_i_mean, yerr=q_i_std,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=q_i_label)
    hist_report_plot(ax=axes[0, 1], data=q_i_mean, bins=10, color=color, x_label=q_i_label, y_label=None)

    # Qc
    q_c_label = F"Qc (Quality Factor)"
    error_bar_report_plot(ax=axes[1, 0], xdata=f_centers_ghz_mean, ydata=q_c_mean, yerr=q_c_std,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=q_c_label)
    hist_report_plot(ax=axes[1, 1], data=q_c_mean, bins=10, color=color, x_label=q_c_label, y_label=None)

    # Impedance Ratio (Z ratio)
    zratio_label = F"Impedance Ratio (Z ratio)"
    error_bar_report_plot(ax=axes[2, 0], xdata=f_centers_ghz_mean,
                          ydata=impedance_ratio_mean, yerr=impedance_ratio_std,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=zratio_label)
    hist_report_plot(ax=axes[2, 1], data=impedance_ratio_mean, bins=10, color=color,
                     x_label=zratio_label, y_label=None)

    # Lambda (SQUID parameter lambda)
    lamb_label = F"SQUID parameter lambda"
    error_bar_report_plot(ax=axes[3, 0], xdata=f_centers_ghz_mean,
                          ydata=lamb_values, yerr=lamb_value_errs,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=lamb_label)
    hist_report_plot(ax=axes[3, 1], data=lamb_values, bins=10, color=color,
                     x_label=lamb_label, y_label=None)

    # Flux Ramp Span (peak-to-peak fit parameter)
    flux_ramp_label = F"Flux Ramp Span (kHz)"
    error_bar_report_plot(ax=axes[4, 0], xdata=f_centers_ghz_mean,
                          ydata=flux_ramp_pp_khz, yerr=flux_ramp_pp_khz_errs,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=flux_ramp_label)
    hist_report_plot(ax=axes[4, 1], data=flux_ramp_pp_khz, bins=10, color=color,
                     x_label=flux_ramp_label, y_label=None)

    # fr_squid_mi_pH
    fr_squid_mi_pH_label = F"FR - SQUID Mutual Inductance (pH)"
    error_bar_report_plot(ax=axes[5, 0], xdata=f_centers_ghz_mean,
                          ydata=fr_squid_mi_pH, yerr=fr_squid_mi_pH_err,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=fr_squid_mi_pH_label)
    hist_report_plot(ax=axes[5, 1], data=fr_squid_mi_pH, bins=10, color=color,
                     x_label=fr_squid_mi_pH_label, y_label=None)

    # legend
    num_found = F"{len(f_centers_ghz_mean)}/65"
    spacing = F"Spacing{'%6.3f' % f_spacings_mhz_mean} MHz"
    leglines.append(plt.Line2D(range(10), range(10), color=color, ls='None',
                               marker='o', markersize=markersize, markerfacecolor=color, alpha=alpha))
    power = res_set.series_key.port_power_dbm

    leglabels.append(F"{'%3i' % power}dBm|{num_found}|{spacing}")
    return axes, leglines, leglabels
