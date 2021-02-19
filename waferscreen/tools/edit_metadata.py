import os
from ref import working_dir
from waferscreen.data_io.s21_io import read_s21, write_s21
from waferscreen.data_io.s21_metadata import MetaDataDict


def edit_raw_single_single_res(parent_folder, res_nums, replace_key, replace_value):
    for res_num in res_nums:
        res_dir = os.path.join(parent_folder, F"{'%04i' % res_num}")
        paths_this_res = [os.path.join(res_dir, res_file) for res_file in  os.listdir(res_dir)]
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
    dirname = os.path.join(working_dir, "nist", "11", "2021-02-11", "raw", "single_res",
                           "scan4.000GHz-4.500GHz_2021-02-12 05-48-00.492736_phase_windowbaselinesmoothedremoved")
    edit_raw_single_single_res(parent_folder=dirname, res_nums=range(66, 131),
                               replace_key='so_band', replace_value='Band02')
