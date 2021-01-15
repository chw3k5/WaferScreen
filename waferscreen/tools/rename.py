import os
from waferscreen.read.table_read import floats_table


def get_all_file_paths(directory):
    file_list = [os.path.join(directory, f) for f in os.listdir(directory)
                 if os.path.isfile(os.path.join(directory, f))]
    return file_list


def rename_data_column(file, old_column_name, new_column_name, delimiter=','):
    data_dict, old_header = floats_table(file=file, delimiter=delimiter, return_header=True)
    new_header = []
    for column_name in old_header:
        if column_name == old_column_name:
            new_header.append(new_column_name)
        else:
            new_header.append(column_name)
    with open(file, 'w') as f:
        header_str = ""
        for column_name in new_header:
            header_str += str(column_name) + ','
        f.write(header_str[:-1] + "\n")
        for row_index in range(len(data_dict[old_header[0]])):
            line_str = ""
            for column_name in old_header:
                line_str += str(data_dict[column_name][row_index]) + ","
            f.write(line_str[:-1] + '\n')


if __name__ == "__main__":
    pro_data_dir = ""
    for wafer_str, band_str, data_str in reversed([("7", "Band02", "2020-09-10"), ("7", "Band02", "2020-09-08"),
                                                   ("7", "Band01", "2020-09-10"),  ("7", "Band01", "2020-09-08")]):
        dir = os.path.join(pro_data_dir, "s21", wafer_str, band_str, data_str, "flux_ramp", "res_fits")
        for file in get_all_file_paths(directory=dir):
            rename_data_column(file=file, old_column_name='ramp_current_mA', new_column_name='ramp_current_uA')
