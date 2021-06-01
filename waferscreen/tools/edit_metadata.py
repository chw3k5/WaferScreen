import os
import ref
from ref import working_dir, parent_dir
from waferscreen.data_io.s21_io import read_s21, write_s21
from waferscreen.data_io.s21_metadata import MetaDataDict
from waferscreen.analyze.res_pipeline_config import processing_metadata_to_remove_from_seeds
from waferscreen.data_io.table_read import row_dict
from waferscreen.data_io.explore_io import chip_id_str_to_chip_id_tuple, chip_id_tuple_to_chip_id_str, band_str_to_num


def list_files(filepath, filetype):
    paths = []
    for root, dirs, files in os.walk(filepath):
        for file in files:
            if file.lower().endswith(filetype.lower()):
                paths.append(os.path.join(root, file))
    return paths


def read_single_res_seed(parent_folder, res_num):
    res_dir = os.path.join(parent_folder, F"{'%04i' % res_num}")
    path_for_seed = os.path.join(res_dir, "seed.csv")
    return read_s21(path=path_for_seed, return_res_params=True)


def read_single_res_non_seed_files(parent_folder, res_num):
    res_dir = os.path.join(parent_folder, F"{'%04i' % res_num}")
    paths_this_res = [os.path.join(res_dir, res_file) for res_file in os.listdir(res_dir)
                      if res_file != "seed.csv"]
    return [read_s21(path=res_path, return_res_params=True, return_lamb_params=True) for res_path in paths_this_res]


def edit_raw_metadata_from_seed_metadata(parent_folder, res_nums):
    for res_num in res_nums:
        read_single_res_seed(parent_folder, res_num)
        _formatted_s21_dict, seed_metadata, _res_fits = read_single_res_seed(parent_folder=parent_folder,
                                                                         res_num=res_num)
        res_dir = os.path.join(parent_folder, F"{'%04i' % res_num}")
        non_seed_paths_this_res = [os.path.join(res_dir, res_file) for res_file in os.listdir(res_dir)
                                   if res_file != "seed.csv"]
        for non_seed_path in non_seed_paths_this_res:
            formatted_s21_dict, old_metadata, res_fits, lamb_fits = read_s21(path=non_seed_path, return_res_params=True,
                                                                             return_lamb_params=True)
            new_metadata_dict = MetaDataDict(old_metadata)
            # do the replacement
            keys_to_update = set(seed_metadata.keys()) - processing_metadata_to_remove_from_seeds - set(old_metadata.keys())
            for seed_key in keys_to_update:
                new_metadata_dict[seed_key] = seed_metadata[seed_key]
            if formatted_s21_dict is None:
                s21_complex = None
                freqs_ghz = None
            else:
                s21_complex = formatted_s21_dict['real'] + (1j * formatted_s21_dict['imag'])
                freqs_ghz = formatted_s21_dict['freq_ghz']
            write_s21(output_file=non_seed_path, freqs_ghz=freqs_ghz,
                      s21_complex=s21_complex, metadata=new_metadata_dict,
                      fitted_resonators_parameters=res_fits, lamb_params_fits=lamb_fits)

    return


def single_edit(path, replace_key, replace_value):
    mutable_dict = {}
    new_metadata_dict = MetaDataDict()
    formatted_s21_dict, old_metadata, res_fits, lamb_fits = read_s21(path=path, return_res_params=True,
                                                                     return_lamb_params=True)
    mutable_dict.update(old_metadata)
    mutable_dict[replace_key] = replace_value
    new_metadata_dict.update(mutable_dict)
    if formatted_s21_dict is None:
        s21_complex = None
        freqs_ghz = None
    else:
        s21_complex = formatted_s21_dict['real'] + (1j * formatted_s21_dict['imag'])
        freqs_ghz = formatted_s21_dict['freq_ghz']
    write_s21(output_file=path, freqs_ghz=freqs_ghz,
              s21_complex=s21_complex, metadata=new_metadata_dict,
              fitted_resonators_parameters=res_fits, lamb_params_fits=lamb_fits)


def edit_raw_single_res(parent_folder, res_nums, replace_key, replace_value):
    for res_num in res_nums:
        res_dir = os.path.join(parent_folder, F"{'%04i' % res_num}")
        paths_this_res = [os.path.join(res_dir, res_file) for res_file in os.listdir(res_dir)]
        for res_path in paths_this_res:
            single_edit(path=res_path, replace_key=replace_key, replace_value=replace_value)


def edit_all_csv_files(dir_name, replace_key, replace_value):
    file_paths = list_files(filepath=dir_name, filetype='.csv')
    # act on each file
    for path in file_paths:
        try:
            single_edit(path=path, replace_key=replace_key, replace_value=replace_value)
        except:
            print(path)
            raise


class ChipIDCorrections:
    def __init__(self):
        self.path = os.path.join(parent_dir, "WaferScreen", "waferscreen", 'metadata_correction_may2021.csv')
        self.all_csv_paths = []
        [self.all_csv_paths.extend(list_files(filepath=output_dir, filetype='.csv')) for output_dir in ref.output_dirs]
        self.row_dicts = row_dict(self.path)

        self.by_wafer = {}
        for data_row in self.row_dicts:
            wafer = int(data_row['wafer'])
            chip_id = chip_id_str_to_chip_id_tuple(data_row['current_chip_id'])
            new_x_pos = data_row['new_pos_x']
            new_y_pos = data_row['new_pos_y']
            if wafer not in self.by_wafer.keys():
                self.by_wafer[wafer] = {}
            if chip_id not in self.by_wafer[wafer].keys():
                self.by_wafer[wafer][chip_id] = (new_x_pos, new_y_pos)

    def run(self):
        replacement_count = 0
        for csv_path in self.all_csv_paths:
            formatted_s21_dict, old_metadata, res_fits, lamb_fits = read_s21(path=csv_path, return_res_params=True,
                                                                             return_lamb_params=True)
            # do the replacement
            # get the metadata in this csv file
            if 'wafer' in old_metadata.keys() and 'so_band' in old_metadata.keys():
                wafer = int(old_metadata['wafer'])
                so_band = band_str_to_num(old_metadata['so_band'])
                if "x_position" in old_metadata.keys():
                    x_pos_old = float(old_metadata["x_position"])
                else:
                    x_pos_old = None
                if "y_position" in old_metadata.keys():
                    y_pos_old = float(old_metadata["y_position"])
                else:
                    y_pos_old = None
                chip_id_tuple = (so_band, x_pos_old, y_pos_old)
                if wafer in self.by_wafer.keys():
                    if chip_id_tuple in self.by_wafer[wafer].keys():
                        new_metadata_dict = MetaDataDict({key: old_metadata[key] for key in old_metadata.keys()
                                                          if key not in {'x_position', 'y_position'}})
                        new_metadata_dict['x_position'], new_metadata_dict['y_position'] = self.by_wafer[wafer][chip_id_tuple]
                        if formatted_s21_dict is None:
                            s21_complex = None
                            freqs_ghz = None
                        else:
                            s21_complex = formatted_s21_dict['real'] + (1j * formatted_s21_dict['imag'])
                            freqs_ghz = formatted_s21_dict['freq_ghz']
                        write_s21(output_file=csv_path, freqs_ghz=freqs_ghz,
                                  s21_complex=s21_complex, metadata=new_metadata_dict,
                                  fitted_resonators_parameters=res_fits, lamb_params_fits=lamb_fits)
                        replacement_count += 1
                        if replacement_count % 100 == 0:
                            print(F"{'%8s' % replacement_count} csv files updated with new chip id coordinates.")
        print(F"{'%5s' % replacement_count} csv files updated with new chip id coordinates.")


if __name__ == "__main__":
    # dirname = os.path.join(working_dir, "nist", "16")
    # edit_raw_metadata_from_seed_metadata(parent_folder=dirname, res_nums=list(range(1, 457)))
    # edit_all_csv_files(dir_name=dirname, replace_key='wafer', replace_value=16)
    read_chip_corrections = ChipIDCorrections()
    read_chip_corrections.run()
