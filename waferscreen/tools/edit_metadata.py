import os
from ref import working_dir
from waferscreen.data_io.s21_io import read_s21, write_s21
from waferscreen.data_io.s21_metadata import MetaDataDict
from waferscreen.analyze.res_pipeline_config import processing_metadata_to_remove_from_seeds


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

def edit_raw_single_res(parent_folder, res_nums, replace_key, replace_value):
    for res_num in res_nums:
        res_dir = os.path.join(parent_folder, F"{'%04i' % res_num}")
        paths_this_res = [os.path.join(res_dir, res_file) for res_file in os.listdir(res_dir)]
        for res_path in paths_this_res:
            mutable_dict = {}
            new_metadata_dict = MetaDataDict()
            formatted_s21_dict, old_metadata, res_fits, lamb_fits = read_s21(path=res_path, return_res_params=True,
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
            write_s21(output_file=res_path, freqs_ghz=freqs_ghz,
                      s21_complex=s21_complex, metadata=new_metadata_dict,
                      fitted_resonators_parameters=res_fits, lamb_params_fits=lamb_fits)


if __name__ == "__main__":
    dirname = os.path.join(working_dir, "nist", "14", "2021-04-22", "raw", "single_res",
                           "scan4.000GHz-6.000GHz_2021-04-23 01-48-31.782287_phase_windowbaselinesmoothedremoved")
    edit_raw_metadata_from_seed_metadata(parent_folder=dirname, res_nums=list(range(1, 457)))
