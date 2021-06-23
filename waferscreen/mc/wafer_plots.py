import os
from operator import itemgetter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
import matplotlib.colors as colors
import matplotlib.cm as cm
import matplotlib.colorbar
from waferscreen.data_io.table_read import row_dict
from waferscreen.data_io.explore_io import chip_id_str_to_chip_id_tuple
from waferscreen.data_io.chip_metadata import chip_metadata

column_name_to_range = {'flux_ramp_pp_khz_at_minus95dbm': (0, 250),  # (color_min, color_max)
                        'flux_ramp_pp_khz_at_minus75dbm': (0, 250),
                        'lamb_at_minus95dbm': (0.0, 0.7),
                        'adr_fiftymk_k': (0.0, 0.300)}

column_name_to_axis_label = {'lamb_at_minus95dbm': "Lambda (-95dBm est. at devices)",
                             'flux_ramp_pp_khz_at_minus95dbm': 'Flux Ramp peak-to-peak (kHz) (-95dBm est. at devices)',
                             'flux_ramp_pp_khz_at_minus75dbm': 'Flux Ramp peak-to-peak (kHz) (-75dBm est. at devices)',
                             'q_i_mean_at_minus75dbm': 'Qi (-75dBm est. at devices)',
                             'adr_fiftymk_k': 'Temperature (K) at ADR rod'}


def read_device_summaries(path):
    # read in raw data
    device_summaries_data = row_dict(filename=path, key='record_id', delimiter=',', null_value='null')
    # make the per wafer data dictionary
    per_wafer_dsd = {}
    for row_key in device_summaries_data.keys():
        row_data = device_summaries_data[row_key]
        wafer_num = row_data['wafer']
        if wafer_num not in per_wafer_dsd.keys():
            per_wafer_dsd[wafer_num] = {}
        per_wafer_dsd[wafer_num][row_key] = row_data
    return per_wafer_dsd


class ParameterSurveys:
    # plot options
    figure_size = (10, 10)
    frameon = False
    colormap = 'gist_rainbow'

    # spacing of the main plot axis
    left_ax_margin = 0.06
    right_ax_margin = 0.00
    bottom_ax_margin = 0.14
    top_ax_margin = 0.04
    width = 1.0 - left_ax_margin - right_ax_margin
    height = 1.0 - bottom_ax_margin - top_ax_margin
    axis_in_figure_coord = [left_ax_margin, bottom_ax_margin, width, height]

    # spacing for the color bar axis
    inter_axis_spacing = 0.07
    colorbar_bottom_ax_margin = 0.06
    colorbar_height = bottom_ax_margin - colorbar_bottom_ax_margin - inter_axis_spacing
    colorbar_x_pad = 0.02
    colorbar_left_ax_margin = colorbar_x_pad
    colorbar_width = 1.0 - (2.0 * colorbar_x_pad)
    colorbar_axis_in_figure_coord = [colorbar_left_ax_margin, colorbar_bottom_ax_margin,
                                     colorbar_width, colorbar_height]

    # chip level layout spacing and rules
    group_colors = {1: 'dodgerblue', 2: 'firebrick', 3: 'darkgoldenrod'}

    chip_zone_width = 0.95
    half_chip_zone_width = chip_zone_width * 0.5
    chip_zone_height = 0.9
    half_chip_zone_height = chip_zone_height * 0.5

    rug_left = -half_chip_zone_width + 0.01
    rug_right = half_chip_zone_width - 0.01
    rug_bottom = -half_chip_zone_height + 0.12
    rug_top = half_chip_zone_height - 0.20

    def __init__(self, device_summaries_path, params=None, output_dir=None):
        self.params = params
        self.device_summaries_path = device_summaries_path
        self.output_dir = output_dir
        self.per_wafer_dsd = read_device_summaries(path=device_summaries_path)
        if params is not None:
            # make per-parameter files the show one wafer's results per pages
            for parameter in params:
                self.single_parameter_survey(parameter=parameter)

    def single_wafer_single_parameter(self, wafer_num, parameter, this_wafer_parameter_data, cmap, norm, scalar_map):
        # 1-figure (page) per wafer, initialize the plot
        fig_this_wafer = plt.figure(figsize=self.figure_size)
        ax_this_wafer = fig_this_wafer.add_axes(self.axis_in_figure_coord, frameon=self.frameon)
        ax_colorbar = fig_this_wafer.add_axes(self.colorbar_axis_in_figure_coord, frameon=self.frameon)

        # loop over all the records and resort the data by chip id
        data_per_patch_ids = {}
        for record_id in sorted(this_wafer_parameter_data.keys()):
            device_plot_dict = this_wafer_parameter_data[record_id]
            x_chip_pos = device_plot_dict['x_chip_pos']
            y_chip_pos = device_plot_dict['y_chip_pos']
            group_num = device_plot_dict['group_num']
            so_band_num = device_plot_dict['so_band_num']
            patch_id = (x_chip_pos, y_chip_pos, group_num, so_band_num)
            if patch_id not in data_per_patch_ids.keys():
                data_per_patch_ids[patch_id] = []
            data_per_patch_ids[patch_id].append(device_plot_dict)
        # loop chips ids
        for patch_id in sorted(data_per_patch_ids.keys()):
            x_chip_pos, y_chip_pos, group_num, so_band_num = patch_id
            group_color = self.group_colors[group_num]
            # in plot coordinated
            rectangle_left = x_chip_pos - self.half_chip_zone_width
            rectangle_bottom = y_chip_pos - self.half_chip_zone_height
            rectangle_right = x_chip_pos + self.half_chip_zone_width
            rectangle_top = y_chip_pos + self.half_chip_zone_height
            # get the bound of the resonators threads (inside the rectangle)
            rug_left = self.rug_left + x_chip_pos
            rug_right = self.rug_right + x_chip_pos
            rug_bottom = self.rug_bottom + y_chip_pos
            rug_top = self.rug_top + y_chip_pos
            # plot the bounding boxed that indicate the chip and band information
            ax_this_wafer.add_patch(Rectangle(xy=(rectangle_left, rectangle_bottom),
                                              width=self.chip_zone_width, height=self.chip_zone_height,
                                              edgecolor=group_color, facecolor='white'))
            patch_text = F"({'%i' % x_chip_pos}, {'%i' % y_chip_pos}) Band{'%02i' % so_band_num} Group-{group_num}"
            chip_label_y_pos_center = (rectangle_top + rug_top) * 0.5
            ax_this_wafer.text(x=x_chip_pos, y=chip_label_y_pos_center, s=patch_text,
                               color=group_color, ha='center', va='center', fontsize=6)
            # sort the data to plot by 'x_pos_mm_on_chip'
            device_plot_dicts = sorted(data_per_patch_ids[patch_id], key=itemgetter('x_pos_mm_on_chip'))
            x_pos_mm_on_chip_min = device_plot_dicts[0]['x_pos_mm_on_chip']
            x_pos_mm_on_chip_max = device_plot_dicts[-1]['x_pos_mm_on_chip']
            # sort the data to plot by 'designed_f_ghz'
            device_plot_dicts_by_designed_f_ghz = sorted(data_per_patch_ids[patch_id], key=itemgetter('designed_f_ghz'))
            designed_f_ghz_min = device_plot_dicts_by_designed_f_ghz[0]['designed_f_ghz']
            designed_f_ghz_max = device_plot_dicts_by_designed_f_ghz[-1]['designed_f_ghz']
            designed_f_span_ghz = designed_f_ghz_max - designed_f_ghz_min

            plot_pos_chip_pos_slope = (rug_right - rug_left) / (x_pos_mm_on_chip_max - x_pos_mm_on_chip_min)

            def x_plot_pos(x_pos_mm_on_chip, designed_f_ghz, f_ghz):
                x_plot_coord = plot_pos_chip_pos_slope * (x_pos_mm_on_chip - x_pos_mm_on_chip_min) + rug_left
                return x_plot_coord

            for device_plot_dict in device_plot_dicts:
                parameter_value = device_plot_dict['parameter_value']
                x_pos_mm_on_chip = device_plot_dict['x_pos_mm_on_chip']
                # y_pos_mm_on_chip = device_plot_dict['y_pos_mm_on_chip']
                chip_id_str = device_plot_dict['chip_id_str']
                chip_id_so_band_num = device_plot_dict['chip_id_so_band_num']
                res_num = device_plot_dict['res_num']
                designed_f_ghz = device_plot_dict['designed_f_ghz']
                f_ghz = device_plot_dict['f_ghz']
                x_plot_coord = x_plot_pos(x_pos_mm_on_chip, designed_f_ghz, f_ghz)
                value_color = scalar_map.to_rgba(parameter_value)
                ax_this_wafer.plot((x_plot_coord, x_plot_coord), (rug_bottom, rug_top), color=value_color, linewidth=2)
                ax_this_wafer.text(x=x_plot_coord, y=rug_bottom, s=F"{'%02i' % res_num}  ",
                                   color='black', ha='center', va='top', fontsize=2, rotation=90.0)

        # colorbar
        cb1 = matplotlib.colorbar.ColorbarBase(ax=ax_colorbar, cmap=cmap, norm=norm, orientation='horizontal')
        if parameter in column_name_to_axis_label.keys():
            cb1.set_label(F'{column_name_to_axis_label[parameter]}')
        else:
            cb1.set_label(F'{parameter}')
        # wafer axis tick marks
        ax_this_wafer.set_xlim((-1.5, 1.5))
        ax_this_wafer.set_ylim((-7.5, 7.5))
        ax_this_wafer.set_xticks(ticks=[-1, 0, 1])
        ax_this_wafer.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=True)
        ax_this_wafer.set_yticks(ticks=[-7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7])
        ax_this_wafer.tick_params(axis='y', which='both', bottom=False, top=False, labelbottom=True)
        # axis labels
        ax_this_wafer.set_ylabel(F"Y Chip Position Label")
        ax_this_wafer.set_xlabel(F"X Chip Position Label")
        # legend
        legend_lines = []
        legend_labels = []
        for group_num in sorted(self.group_colors.keys()):
            color = self.group_colors[group_num]
            legend_lines.append(Rectangle(xy=(0, 0), width=1.0, height=1.0, edgecolor=color, facecolor='white'))
            legend_labels.append(F"Group{group_num}")
        ax_this_wafer.legend(legend_lines, legend_labels, loc=1, numpoints=5, handlelength=3, fontsize=12)
        # figure title (this page)
        plt.suptitle(F"{parameter} - Wafer{'%03i' % wafer_num}")
        return fig_this_wafer

    def single_parameter_survey(self, parameter):
        # collect and sort the relevant data for this parameters
        per_wafer_single_param = {}
        parameter_min = float('inf')
        parameter_max = float('-inf')
        for wafer_num in self.per_wafer_dsd.keys():
            all_data_this_wafer = self.per_wafer_dsd[wafer_num]
            for record_id in all_data_this_wafer.keys():
                device_record = all_data_this_wafer[record_id]
                if parameter in device_record.keys():
                    # only make a plot file if all the required data is available
                    try:
                        parameter_value = device_record[parameter]
                        so_band_num = device_record['so_band']
                        x_pos_mm_on_chip = device_record['x_pos_mm_on_chip']
                        y_pos_mm_on_chip = device_record['y_pos_mm_on_chip']
                        group_num = device_record['group_num']
                        chip_id_str = device_record['chip_id']
                        chip_id_so_band_num, x_chip_pos, y_chip_pos \
                            = chip_id_str_to_chip_id_tuple(chip_id_str=chip_id_str)
                        res_num = device_record['res_num']
                        designed_f_ghz = device_record['designed_f_ghz']
                        f_ghz = device_record['f_ghz']
                    except KeyError:
                        pass
                    else:
                        # finish the data organization if all the data was available
                        plot_dict = {'parameter_value': parameter_value, 'so_band_num': so_band_num,
                                     'x_pos_mm_on_chip': x_pos_mm_on_chip, 'y_pos_mm_on_chip': y_pos_mm_on_chip,
                                     'group_num': group_num, 'chip_id_str': chip_id_str,
                                     'chip_id_so_band_num': chip_id_so_band_num,
                                     'x_chip_pos': x_chip_pos, 'y_chip_pos': y_chip_pos, 'res_num': res_num,
                                     'designed_f_ghz': designed_f_ghz, 'f_ghz': f_ghz}
                        if wafer_num not in per_wafer_single_param.keys():
                            per_wafer_single_param[wafer_num] = {}
                        per_wafer_single_param[wafer_num][record_id] = plot_dict
                        if plot_dict['parameter_value'] < parameter_min:
                            parameter_min = plot_dict['parameter_value']
                        if parameter_max < plot_dict['parameter_value']:
                            parameter_max = plot_dict['parameter_value']
        # determine the color-axis
        if parameter in column_name_to_range.keys():
            parameter_min, parameter_max = column_name_to_range[parameter]
        norm = colors.Normalize(vmin=parameter_min, vmax=parameter_max)
        cmap = plt.get_cmap(self.colormap)
        scalar_map = cm.ScalarMappable(norm=norm, cmap=cmap)
        # open the context manager for pdf plots so it will close gracefully if there is an exception
        basename = F"{parameter}_wafer_series.pdf"
        full_plot_path = os.path.join(self.output_dir, basename)
        with PdfPages(full_plot_path) as pdf_pages:
            # run the wafer series for this parameter
            for wafer_num in sorted(per_wafer_single_param.keys()):
                this_wafer_parameter_data = per_wafer_single_param[wafer_num]
                # get the figure for this page of the single-parameter wafer-series file.
                fig_this_wafer = self.single_wafer_single_parameter(wafer_num=wafer_num, parameter=parameter,
                                                                    this_wafer_parameter_data=this_wafer_parameter_data,
                                                                    cmap=cmap, norm=norm, scalar_map=scalar_map)
                # save this figure (page) to the plot output
                pdf_pages.savefig(fig_this_wafer)
                # close the figure and free up the resources
                plt.close(fig=fig_this_wafer)
        print(F'Wafer Series plot saved for parameter ({parameter}): {full_plot_path}')


if __name__ == '__main__':
    from ref import device_summaries_dir
    # get the path of this python file
    ref_file_path = os.path.dirname(os.path.realpath(__file__))
    # find the path to the WaferScreen directory
    parent_dir, _ = ref_file_path.rsplit("WaferScreen", 1)
    # this is the standard path to device_summary.csv that is created by explore.py
    standard_device_summaries_path = os.path.join(parent_dir, "WaferScreen", "waferscreen", "tldr",
                                                  "device_summary.csv")
    # run the standard data summary plots
    example_per_wafer_dsd = ParameterSurveys(device_summaries_path=standard_device_summaries_path,
                                             params=['lamb_at_minus95dbm', 'flux_ramp_pp_khz_at_minus75dbm',
                                                     'q_i_mean_at_minus75dbm'],
                                             output_dir=device_summaries_dir)
