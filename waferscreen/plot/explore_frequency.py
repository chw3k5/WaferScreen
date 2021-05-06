# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import matplotlib.patches as mpatch
from matplotlib.patches import FancyBboxPatch
import numpy as np
import ref
from waferscreen.plot.band_and_keepout import band_and_keepout_plot
from waferscreen.plot.band_and_keepout import colors as band_colors
from waferscreen.data_io.explore_io import chip_id_str_to_chip_id_tuple


def frequencies_plot(wafer_scale_frequencies_ordered, wafer_scale_frequencies_stats, plot_path=None, show=False):
    """
    A rug plot to display frequency placement data on a database scale. Each row of plot data is a different wafer.
    """
    # basic plot layout and calculations
    # plot element options
    thread_linewidth = 0.5
    thread_alpha = 0.5
    stats_text_rotation = 90
    stats_text_font_size = 8
    stat_text_color = 'black'
    stats_bbox_alpha = 0.3
    y_tick_label_fontsize = 18
    # plot frame size

    left, right, bottom, top = 0.05, 0.99, 0.06, 0.95
    width = right - left
    height = top - bottom
    fig = plt.figure(figsize=(16, 8))
    ax = fig.add_axes([left, bottom, width, height], frameon=False)
    # plot spacing vertical spacing for wafer data rows, y axis is in data coordinates
    thread_to_label_spacing_ratio = 1.0
    num_of_wafers = len(wafer_scale_frequencies_ordered)
    wafer_data_increment_size = 1.0 / num_of_wafers
    """
    l = y+x 
    r = y/x <=> y = rx
    <=> l = rx+x <=> l=x(r+1) <=> l/(r+1) = x
    """
    thread_increment_size = wafer_data_increment_size / (thread_to_label_spacing_ratio + 1.0)

    # band and keep out zone layout and display
    ax = band_and_keepout_plot(ax=ax, do_labels=False, y_ticks_off=False)
    # plot the data records
    y_ticks = []
    y_tick_labels = []
    left_margin = ref.smurf_keepout_zones_ghz[0][0]
    right_margin = ref.smurf_keepout_zones_ghz[-1][1]
    for wafer_count, wafer_num in list(enumerate(sorted(wafer_scale_frequencies_ordered.keys(), reverse=True))):
        y_ticks.append((wafer_data_increment_size * 0.5) + (wafer_data_increment_size * wafer_count))
        y_tick_labels.append(str(wafer_num))
        thread_region_start = wafer_count * wafer_data_increment_size
        thread_region_stop = thread_region_start + thread_increment_size
        label_region_start = thread_region_stop
        label_region_stop = (wafer_count + 1.0) * wafer_data_increment_size
        label_region_span = label_region_stop - label_region_start
        label_region_stop_margin = label_region_stop - (label_region_span * 0.1)
        for chip_id_str in sorted(wafer_scale_frequencies_ordered[wafer_num].keys()):
            so_band, *_xypos = chip_id_str_to_chip_id_tuple(chip_id_str)
            for seed_name in sorted(wafer_scale_frequencies_ordered[wafer_num][chip_id_str].keys()):
                for port_power_dbm in sorted(wafer_scale_frequencies_ordered[wafer_num][chip_id_str][seed_name].keys()):
                    frequency_records_ordered = \
                        wafer_scale_frequencies_ordered[wafer_num][chip_id_str][seed_name][port_power_dbm]
                    stats_dict = wafer_scale_frequencies_stats[wafer_num][chip_id_str][seed_name][port_power_dbm]
                    # ["f_ghz_min", 'f_ghz_max', 'f_ghz_median', 'f_ghz_mean', 'f_ghz_std']
                    # the minimum label
                    plt.text(y=label_region_start, x=stats_dict['f_ghz_min'], s=F"{'%1.3f' % stats_dict['f_ghz_min']}",
                             ha="left", va='bottom', size=stats_text_font_size, rotation=stats_text_rotation,
                             color=stat_text_color,
                             bbox=dict(boxstyle='square', fc=band_colors[so_band], alpha=stats_bbox_alpha))
                    # the maximum label
                    plt.text(y=label_region_start, x=stats_dict['f_ghz_max'], s=F"{'%1.3f' % stats_dict['f_ghz_max']}",
                             ha="right", va='bottom', size=stats_text_font_size, rotation=stats_text_rotation,
                             color=stat_text_color,
                             bbox=dict(boxstyle='square', fc=band_colors[so_band], alpha=stats_bbox_alpha))
                    # the median label
                    plt.text(y=label_region_start, x=stats_dict['f_ghz_median'],
                             s=F"{'%1.3f' % stats_dict['f_ghz_median']}",
                             ha="center", va='bottom', size=stats_text_font_size, rotation=stats_text_rotation,
                             color=stat_text_color,
                             bbox=dict(boxstyle='square', fc=band_colors[so_band], alpha=stats_bbox_alpha))
                    # the mean (std) label
                    plt.text(y=label_region_stop_margin, x=stats_dict['f_ghz_mean'],
                             s=F"{'%1.3f' % stats_dict['f_ghz_mean']} ({'%1.3f' % stats_dict['f_ghz_std']})",
                             ha="center", va='top', size=stats_text_font_size,
                             color=stat_text_color,
                             bbox=dict(boxstyle='square', fc=band_colors[so_band], alpha=stats_bbox_alpha))

                    # keep track tof the margin requirements
                    if stats_dict['f_ghz_min'] < left_margin:
                        left_margin = stats_dict['f_ghz_min']
                    if right_margin < stats_dict['f_ghz_max']:
                        right_margin = stats_dict['f_ghz_max']
                    # threads of the frequency lines
                    for f_ghz, so_band, is_in_band, is_in_keepout in frequency_records_ordered:
                        # plot the data
                        if is_in_band and not is_in_keepout:
                            plt.plot((f_ghz, f_ghz), (thread_region_start, thread_region_stop),
                                     color=band_colors[so_band], linewidth=thread_linewidth, alpha=thread_alpha)
                        else:
                            plt.plot((f_ghz, f_ghz), (thread_region_start, thread_region_stop),
                                     color="black", linewidth=thread_linewidth, alpha=thread_alpha)

    # add a black line to separate wafers
    for wafer_count in range(1, num_of_wafers):
        y_pos = wafer_count * wafer_data_increment_size
        ax.plot((left_margin, right_margin), (y_pos, y_pos), color='black', linewidth=2)
    # band labels
    band_label_centers = []
    band_label_names = []
    for band_num, band_string in list(enumerate(ref.band_names)):
        band_label_names.append(band_string)
        band_label_centers.append(ref.band_params[band_string]["center_GHz"])
        plt.text(x=ref.band_params[band_string]["center_GHz"], y=1.01, s=band_string,
                 horizontalalignment='center', verticalalignment='bottom', size=12,
                 bbox=dict(boxstyle='square', fc=band_colors[band_num]))
    # axis details
    ax.set_ylim([0, 1])
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_tick_labels, fontsize=y_tick_label_fontsize)
    ax.set_ylabel("Wafer", fontsize=12)
    ax.set_xlim([left_margin, right_margin])
    ax.set_xticks([x_tick for x_tick in np.arange(4.0, 6.01, 0.25)])
    ax.set_xlabel("Frequency (GHz)")
    if plot_path is not None:
        plt.savefig(plot_path)
        print("Saved Plot to:", plot_path)
    if show:
        plt.show(block=True)
    plt.close(fig)

