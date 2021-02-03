import os
from waferscreen.data_io.table_read import floats_table


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


def rename_dir(old_path, new_path=None):
    if new_path is None:
        parent_dir, local_dirname = os.path.split(old_path)
        new_path = os.path.join(parent_dir, F"res{local_dirname}")
    os.rename(old_path, new_path)


if __name__ == "__main__":
    parent_dir = "C:\\Users\\chw3k5\\PycharmProjects\\WaferScreen\\waferscreen\\nist\\9\\2021-01-26\\pro"
    all_dirs = [os.path.join(parent_dir, dirname) for dirname in os.listdir(parent_dir)
                if os.path.isdir(os.path.join(parent_dir, dirname)) and dirname[:4] != "scan"]
    for old_path in all_dirs:
        rename_dir(old_path=old_path)

