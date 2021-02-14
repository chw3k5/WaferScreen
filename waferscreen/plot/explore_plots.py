import numpy as np
from waferscreen.analyze.lambfit import phi_0
import matplotlib.pyplot as plt


def error_bar_report_plot(ax, xdata, ydata, yerr, color="black", ls='None', marker="o", markersize=10, alpha=0.7,
                          x_label=None, y_label=None, x_ticks_on=True):
    if not x_ticks_on:
        ax.tick_params(axis="x", labelbottom=False)
    ax.errorbar(xdata, ydata, yerr=yerr,
                color=color, ls=ls, marker=marker, markersize=markersize, alpha=alpha)
    if x_label is None:
        if x_ticks_on:
            ax.set_xlabel("Average Resonator Center Frequency (GHz)")
    else:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)
    return ax


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


def rug_plot(ax, xdata, y_min, y_max, color="blue"):
    ax.tick_params(axis="y", labelleft=False)
    for f_centers in xdata:
        f_len = len(f_centers)
        alpha = 1.5 / f_len
        for f_center in list(f_centers):
            ax.plot((f_center, f_center), (y_min, y_max), ls='solid', linewidth=0.1, color=color, alpha=alpha)
    ax.set_ylim(bottom=0, top=1)
    ax.set_xlabel(F"Frequency (GHz)")
    ax.tick_params(axis='y',  # changes apply to the x-axis
                   which='both',  # both major and minor ticks are affected
                   left=False,  # ticks along the bottom edge are off
                   right=False,  # ticks along the top edge are off
                   labelleft=False)
    return ax


def band_plot(ax, f_ghz, mag_dbm):
    ax.tick_params(axis="x", labelbottom=False)
    ax.plot(f_ghz, mag_dbm, color="darkorchid", linewidth=1)
    ax.set_ylabel("dB")
    ax.tick_params(axis='x',  # changes apply to the x-axis
                   which='both',  # both major and minor ticks are affected
                   bottom=False,  # ticks along the bottom edge are off
                   top=False,  # ticks along the top edge are off
                   labelbottom=False)
    return ax


def report_key(ax, leglines, leglabels):
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
    ax.set_xlim(left=0, right=1)
    ax.set_ylim(bottom=0, top=1)
    ax.set_title("KEY")
    ax.legend(leglines, leglabels, loc=0, numpoints=2, handlelength=3, fontsize=7)
    return ax


def report_plot_init(num_of_scatter_hist_x=3, num_of_scatter_hist_y=2):
    """
    Three Major Regions
      1) Top Third:Resonator Spectrum 2) Middle:Frequency Rug Plot 3) Bottom:Scatter plots with side histograms
          definitions for the axes

    :param num_of_scatter_hist:
    :return:
    """
    left = 0.05
    bottom = 0.05
    right = 0.99
    top = 0.95

    major12_region_spacing = 0.001
    major32_region_spacing = 0.028

    major_regions_y = (0.60, 0.70)

    key_margin_x = 0.85
    key_space = 0.003

    scatter_hist_little_space = 0.005
    scatter_hist_bigger_vspace = 0.010
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

    # 1) Top Third:Resonator Spectrum
    res_spec_top = top
    res_spec_bottom = major_regions_y[1] + major12_region_spacing
    res_spec_height = res_spec_top - res_spec_bottom
    res_spec_left = left
    res_spec_right = key_margin_x - key_space
    res_spec_width = res_spec_right - res_spec_left
    res_spec_cood = [res_spec_left, res_spec_bottom, res_spec_width, res_spec_height]

    # 2) Middle:Frequency Rug Plot
    rug_top = major_regions_y[1] - major12_region_spacing
    rug_bottom = major_regions_y[0] + major32_region_spacing
    rug_height = rug_top - rug_bottom
    rug_left = left
    rug_right = key_margin_x - key_space
    rug_width = rug_right - rug_left
    rug_cood = [rug_left, rug_bottom, rug_width, rug_height]

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
    fig = plt.figure(figsize=(17, 10))
    ax_key = fig.add_axes(key_cood, frameon=False)
    ax_res_spec = fig.add_axes(res_spec_cood, frameon=False)
    ax_rug = fig.add_axes(rug_cood, sharex=ax_res_spec, frameon=False)
    axes_scatter = [fig.add_axes(scatter_cood, sharex=ax_res_spec) for scatter_cood in scatter_coords]
    axes_hist = [fig.add_axes(hist_coord, sharey=ax_scatter)
                 for hist_coord, ax_scatter in zip(hist_coords, axes_scatter)]
    axes_shist = [(ax_scatter, ax_hist) for ax_scatter, ax_hist in zip(axes_scatter, axes_hist)]
    return fig, ax_key, ax_res_spec, ax_rug, axes_shist


def single_lamp_to_report_plot(axes, res_set, color, leglines, leglabels, markersize=8, alpha=0.5):
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
    f_centers_ghz_all = []
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
    ax_scatter_q_i, ax_hist_q_i = axes[0]
    error_bar_report_plot(ax=ax_scatter_q_i, xdata=f_centers_ghz_mean, ydata=q_i_mean, yerr=q_i_std,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=q_i_label, x_ticks_on=False)
    hist_report_plot(ax=ax_hist_q_i, data=q_i_mean, bins=10, color=color, x_label=None, y_label=None, alpha=alpha)

    # Qc
    q_c_label = F"Qc (Quality Factor)"
    ax_scatter_q_c, ax_hist_q_c = axes[1]
    error_bar_report_plot(ax=ax_scatter_q_c, xdata=f_centers_ghz_mean, ydata=q_c_mean, yerr=q_c_std,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=q_c_label, x_ticks_on=False)
    hist_report_plot(ax=ax_hist_q_c, data=q_c_mean, bins=10, color=color, x_label=None, y_label=None, alpha=alpha)

    # Impedance Ratio (Z ratio)
    zratio_label = F"Impedance Ratio (Z ratio)"
    ax_scatter_zratio, ax_hist_zratio = axes[2]
    error_bar_report_plot(ax=ax_scatter_zratio, xdata=f_centers_ghz_mean,
                          ydata=impedance_ratio_mean, yerr=impedance_ratio_std,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=zratio_label, x_ticks_on=False)
    hist_report_plot(ax=ax_hist_zratio, data=impedance_ratio_mean, bins=10, color=color,
                     x_label=None, y_label=None, alpha=alpha)

    # Lambda (SQUID parameter lambda)
    lamb_label = F"SQUID parameter lambda"
    ax_scatter_lamb, ax_hist_lamb = axes[3]
    error_bar_report_plot(ax=ax_scatter_lamb, xdata=f_centers_ghz_mean,
                          ydata=lamb_values, yerr=lamb_value_errs,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=lamb_label, x_ticks_on=True)
    hist_report_plot(ax=ax_hist_lamb, data=lamb_values, bins=10, color=color, x_label=None, y_label=None, alpha=alpha)

    # Flux Ramp Span (peak-to-peak fit parameter)
    flux_ramp_label = F"Flux Ramp Span (kHz)"
    ax_scatter_flux_ramp, ax_hist_flux_ramp = axes[4]
    error_bar_report_plot(ax=ax_scatter_flux_ramp, xdata=f_centers_ghz_mean,
                          ydata=flux_ramp_pp_khz, yerr=flux_ramp_pp_khz_errs,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=flux_ramp_label, x_ticks_on=True)
    hist_report_plot(ax=ax_hist_flux_ramp, data=flux_ramp_pp_khz, bins=10, color=color,
                     x_label=None, y_label=None, alpha=alpha)

    # fr_squid_mi_pH
    fr_squid_mi_pH_label = F"FR - SQUID Mutual Inductance (pH)"
    ax_scatter_fr_squid, ax_hist_fr_squid = axes[5]
    error_bar_report_plot(ax=ax_scatter_fr_squid, xdata=f_centers_ghz_mean,
                          ydata=fr_squid_mi_pH, yerr=fr_squid_mi_pH_err,
                          color=color, ls='None', marker="o", markersize=markersize, alpha=alpha,
                          x_label=None, y_label=fr_squid_mi_pH_label, x_ticks_on=True)
    hist_report_plot(ax=ax_hist_fr_squid, data=fr_squid_mi_pH, bins=10, color=color,
                     x_label=None, y_label=None, alpha=alpha)

    # legend
    num_found = F"{len(f_centers_ghz_mean)}/65"
    spacing = F"Spacing{'%6.3f' % f_spacings_mhz_mean} MHz"
    leglines.append(plt.Line2D(range(10), range(10), color=color, ls='None',
                               marker='o', markersize=markersize, markerfacecolor=color, alpha=alpha))
    power = res_set.series_key.port_power_dbm

    leglabels.append(F"{'%3i' % power}dBm|{num_found}|{spacing}")
    return axes, leglines, leglabels, f_centers_ghz_all


if __name__ == "__main__":
    report_plot_init(num_of_scatter_hist_x=3, num_of_scatter_hist_y=2)
    plt.show()
