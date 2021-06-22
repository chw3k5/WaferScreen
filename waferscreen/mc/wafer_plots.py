import os
from waferscreen.data_io.table_read import row_dict
from waferscreen.data_io.explore_io import chip_id_str_to_chip_id_tuple


def single_wafer_single_parameter(wafer_num, parameter, this_wafer_parameter_data):
    for record_id in sorted(this_wafer_parameter_data.keys()):
        device_plot_dict = this_wafer_parameter_data[record_id]
        print('test point')

    return


def single_parameter_survey(parameter, per_wafer_dsd):
    # collect and sort the relevant data for this parameters
    per_wafer_single_param = {}
    for wafer_num in per_wafer_dsd.keys():
        all_data_this_wafer = per_wafer_dsd[wafer_num]
        for record_id in all_data_this_wafer.keys():
            device_record = all_data_this_wafer[record_id]
            if parameter in device_record.keys():
                try:
                    parameter_value = device_record[parameter]
                    so_band_num = device_record['so_band']
                    x_pos_mm_on_chip = device_record['x_pos_mm_on_chip']
                    y_pos_mm_on_chip = device_record['y_pos_mm_on_chip']
                    group_num = device_record['group_num']
                    chip_id_str = device_record['chip_id']
                    chip_id_so_band_num, x_chip_pos, y_chip_pos = chip_id_str_to_chip_id_tuple(chip_id_str=chip_id_str)
                    res_num = device_record['res_num']
                    plot_dict = {'parameter_value': parameter_value, 'so_band_num': so_band_num,
                                 'x_pos_mm_on_chip': x_pos_mm_on_chip, 'y_pos_mm_on_chip': y_pos_mm_on_chip,
                                 'group_num': group_num, 'chip_id_str': chip_id_str,
                                 'chip_id_so_band_num': chip_id_so_band_num,
                                 'x_chip_pos': x_chip_pos, 'y_chip_pos': y_chip_pos, 'res_num': res_num}
                except KeyError:
                    pass
                else:
                    if wafer_num not in per_wafer_single_param.keys():
                        per_wafer_single_param[wafer_num] = {}
                    per_wafer_single_param[wafer_num][record_id] = plot_dict
    # run the wafer series for this parameter
    for wafer_num in sorted(per_wafer_single_param.keys()):
        single_wafer_single_parameter(wafer_num=wafer_num, parameter=parameter,
                                      this_wafer_parameter_data=per_wafer_single_param[wafer_num])
    return


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


def standard_parameter_surveys(params, device_summaries_path):
    per_wafer_dsd = read_device_summaries(path=device_summaries_path)
    for parameter in params:
        single_parameter_survey(parameter=parameter, per_wafer_dsd=per_wafer_dsd)
    return per_wafer_dsd


if __name__ == '__main__':
    # get the path of this python file
    ref_file_path = os.path.dirname(os.path.realpath(__file__))
    # find the path to the WaferScreen directory
    parent_dir, _ = ref_file_path.rsplit("WaferScreen", 1)
    # this is the standard path to device_summary.csv that is created by explore.py
    standard_device_summaries_path = os.path.join(parent_dir, "WaferScreen", "waferscreen", "tldr",
                                                  "device_summary.csv")
    # run the standard data summary plots
    example_per_wafer_dsd = standard_parameter_surveys(params=['lamb_at_minus95dbm',
                                                               'flux_ramp_pp_khz_at_minus75dbm',
                                                               'q_i_mean_at_minus75dbm'],
                                                       device_summaries_path=standard_device_summaries_path)
