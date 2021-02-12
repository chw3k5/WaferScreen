import os
import numpy as np
from operator import itemgetter
from scipy.optimize import curve_fit
from waferscreen.analyze.lambfit import f0_of_I, guess_lamb_fit_params
from waferscreen.data_io.s21_io import write_s21, read_s21
from waferscreen.data_io.lamb_io import remove_processing_tags, prep_lamb_dirs, LambdaParams
from waferscreen.data_io.s21_metadata import MetaDataDict
from waferscreen.data_io.series_io import SeriesKey, series_key_header
from waferscreen.plot.s21_plots import lamb_plot, multi_lamb_plot
import ref


class LambCalc:
    def __init__(self, lamb_dir, auto_fit=False, plot=True):
        self.lamb_dir = lamb_dir
        self.do_plot = plot
        self.input_paths = None
        self.res_fit_to_metadata = None
        self.resfits_and_metadata = None
        self.by_type_resfits_and_metadata = None

        self.lamb_params_guess = None
        self.lamb_params_fit = None
        self.lamb_type_key = None
        self.unified_metadata = None

        self.pro_data_dir, self.local_dirname = os.path.split(self.lamb_dir)
        self.report_parent_dir_str = None
        self.report_dir = None
        self.lamb_outputs_dir = None
        self.lamb_plots_dir = None
        self.lamb_output_path = None
        self.lamb_plot_path = None
        if auto_fit:
            self.read_input()
            self.fit()

    def update_unified_metadata(self, metadata_this_file):
        # some of the metadata is the same across all resonators, that result is in self.unified_metadata
        if self.unified_metadata is None:
            # this is the first metadata encountered
            self.unified_metadata = MetaDataDict()
            self.unified_metadata.update(metadata_this_file)
        else:
            # each subsequent loop removes keys from self.unified_metadata if values are found to be different
            # across files, only data the was the same across all file remains
            types_unified_meta_data = set(self.unified_metadata.keys())
            types_metadata_this_file = set(metadata_this_file)
            found_types_not_in_this_metadata = types_unified_meta_data - types_metadata_this_file
            for data_type in found_types_not_in_this_metadata:
                del self.unified_metadata[data_type]
            overlapping_types_to_check = types_unified_meta_data & types_metadata_this_file
            for data_type in overlapping_types_to_check:
                if self.unified_metadata[data_type] != metadata_this_file[data_type]:
                    del self.unified_metadata[data_type]

    def read_input(self):
        self.input_paths = []
        for test_filename in os.listdir(self.lamb_dir):
            if "." in test_filename:
                _basename_prefix, extension = test_filename.rsplit(".", 1)
                if extension in ref.s21_file_extensions:
                    self.input_paths.append(os.path.join(self.lamb_dir, test_filename))
        self.res_fit_to_metadata = {}
        self.resfits_and_metadata = []
        for input_path in self.input_paths:
            _formatted_s21_dict, metadata_this_file, res_fits = read_s21(path=input_path, return_res_params=True)
            self.update_unified_metadata(metadata_this_file=metadata_this_file)
            for res_fit in res_fits:
                self.res_fit_to_metadata[res_fit] = metadata_this_file
                self.resfits_and_metadata.append((metadata_this_file['flux_current_ua'], res_fit, metadata_this_file))
        self.set_input(resfits_and_metadata=self.resfits_and_metadata)

    def set_input(self, resfits_and_metadata):
        self.resfits_and_metadata = sorted(resfits_and_metadata, key=itemgetter(0))
        for flux_current_ua, res_fit, metadata_this_file in self.resfits_and_metadata:
            self.update_unified_metadata(metadata_this_file=metadata_this_file)
        self.report_parent_dir_str = remove_processing_tags(self.unified_metadata["seed_base"])
        self.report_dir, self.lamb_outputs_dir, self.lamb_plots_dir \
            = prep_lamb_dirs(pro_data_dir=self.pro_data_dir, report_parent_dir_str=self.report_parent_dir_str)

    def write(self):
        lamb_basename = F"lambda_res{'%04i' % self.lamb_params_fit.res_num}_{self.report_parent_dir_str}"
        if self.lamb_type_key is None:
            lamb_basename += ".csv"
        else:
            lamb_basename += F"_{self.lamb_type_key}.csv"
        self.lamb_output_path = os.path.join(self.lamb_outputs_dir, lamb_basename)
        res_fits = [a_tup[1] for a_tup in self.resfits_and_metadata]
        write_s21(output_file=self.lamb_output_path, metadata=self.unified_metadata,
                  fitted_resonators_parameters=res_fits, lamb_params_fits=[self.lamb_params_fit])

    def set_lamb_type_key(self):
        self.lamb_type_key = SeriesKey(port_power_dbm=self.unified_metadata["port_power_dbm"],
                                       if_bw_hz=self.unified_metadata["if_bw_hz"])

    def fit(self, currentuA=None, freqGHz=None, unified_metadata=None, lamb_plt_basename=None):
        if currentuA is None:
            currentuA = np.array([pair[0] for pair in self.resfits_and_metadata])
        if freqGHz is None:
            freqGHz = np.array([pair[1].fcenter_ghz for pair in self.resfits_and_metadata])
        if unified_metadata is None:
            unified_metadata = self.unified_metadata
        if lamb_plt_basename is None:
            if self.lamb_type_key:
                lamb_plt_basename = F"res{'%04i' % self.unified_metadata['res_num']}_{self.lamb_type_key}.png"
            else:
                lamb_plt_basename = F"res{'%04i' % self.unified_metadata['res_num']}.png"
        # guess for curve fit
        currentA = currentuA * 1.0e-6
        i0fit_guess, mfit_guess, f2fit_guess, pfit_guess, lambfit_guess = guess_lamb_fit_params(currentA, freqGHz)
        self.lamb_params_guess = LambdaParams(i0fit=i0fit_guess, mfit=mfit_guess, f2fit=f2fit_guess, pfit=pfit_guess,
                                              lambfit=lambfit_guess, res_num=unified_metadata["res_num"],
                                              parent_dir=self.lamb_dir)

        popt, pcov = curve_fit(f0_of_I, currentA, freqGHz, (i0fit_guess, mfit_guess, f2fit_guess, pfit_guess,
                                                            lambfit_guess))
        i0fit, mfit, f2fit, pfit, lambfit = popt
        i0fit_err = pcov[0, 0]
        mfit_err = pcov[1, 1]
        f2fit_err = pcov[2, 2]
        pfit_err = pcov[3, 3]
        lambfit_err = pcov[4, 4]
        self.lamb_params_fit = LambdaParams(i0fit=i0fit, mfit=mfit, f2fit=f2fit, pfit=pfit, lambfit=lambfit,
                                            res_num=unified_metadata["res_num"], parent_dir=self.lamb_dir,
                                            i0fit_err=i0fit_err, mfit_err=mfit_err, f2fit_err=f2fit_err,
                                            pfit_err=pfit_err, lambfit_err=lambfit_err)

        # output the fit data
        self.write()

        # make a showing the fit input and results.
        if self.do_plot:
            # calculations for the plot's title string
            q_i_array = np.array([res_param.q_i for res_param in [a_tuple[1] for a_tuple in self.resfits_and_metadata]])
            q_i_mean = np.mean(q_i_array)
            q_i_std = np.std(q_i_array)
            q_c_array = np.array([res_param.q_c for res_param in [a_tuple[1] for a_tuple in self.resfits_and_metadata]])
            q_c_mean = np.mean(q_c_array)
            q_c_std = np.std(q_c_array)
            lamb_format_str = '%8.6f'
            q_format_str = "%i"
            title_str = F"Resonator Number: {self.lamb_params_fit.res_num},  "
            title_str += F"{unified_metadata['so_band']},  "
            title_str += F"lambda: {lamb_format_str % self.lamb_params_fit.lambfit} "
            title_str += F"({lamb_format_str % self.lamb_params_fit.lambfit_err})  "
            title_str += F"mean Qi: {q_format_str % q_i_mean} "
            title_str += F"({q_format_str % q_i_std})  "
            title_str += F"mean Qc: {q_format_str % q_c_mean} "
            title_str += F"({q_format_str % q_c_std})"
            self.lamb_plot_path = os.path.join(self.lamb_plots_dir, lamb_plt_basename)
            lamb_plot(input_data=(currentuA, freqGHz), lamb_params_guess=self.lamb_params_guess,
                      lamb_params_fit=self.lamb_params_fit, resfits_and_metadata=self.resfits_and_metadata,
                      title_str=title_str, output_filename=self.lamb_plot_path)

    @classmethod
    def from_resfits_and_metadata(cls, resfits_and_metadata, lamb_dir, plot):
        a_lamb_calc = cls(lamb_dir, auto_fit=False, plot=plot)
        a_lamb_calc.set_input(resfits_and_metadata=resfits_and_metadata)
        return a_lamb_calc

    def sort_by_type(self):
        self.by_type_resfits_and_metadata = {}
        no_series_plots = True
        for metadata_type in series_key_header:
            type_dict = {}
            for flux_current_ua, res_fit, metadata_this_file in self.resfits_and_metadata:
                type_value = metadata_this_file[metadata_type]
                if type_value not in type_dict:
                    type_dict[type_value] = []
                type_dict[type_value].append((flux_current_ua, res_fit, metadata_this_file))
            type_values = type_dict.keys()
            self.by_type_resfits_and_metadata[metadata_type] = \
                {type_value: self.from_resfits_and_metadata(resfits_and_metadata=type_dict[type_value],
                                                            lamb_dir=self.lamb_dir, plot=self.do_plot)
                 for type_value in type_values}
            if len(type_values) > 1 and self.do_plot:
                no_series_plots = False
                values_dict = self.by_type_resfits_and_metadata[metadata_type]
                multi_resfits_and_metadata = [values_dict[type_value].resfits_and_metadata
                                              for type_value in type_values]
                multi_input_data = [(np.array([pair[0] for pair in resfits_and_metadata]),
                                     np.array([pair[1].fcenter_ghz for pair in resfits_and_metadata]))
                                    for resfits_and_metadata in multi_resfits_and_metadata]
                multi_labels = [F"{type_value}" for type_value in type_values]
                multi_lamb_params_fit = []
                for type_value in type_values:
                    values_dict[type_value].set_lamb_type_key()
                    values_dict[type_value].fit()

                    multi_lamb_params_fit.append(values_dict[type_value].lamb_params_fit)
                type_plot_basename = F"res{'%04i' % self.unified_metadata['res_num']}_SeriesType{metadata_type}.png"
                series_plot_dir = os.path.join(self.lamb_plots_dir, F"{metadata_type}")
                if not os.path.isdir(series_plot_dir):
                    os.mkdir(series_plot_dir)
                self.lamb_plot_path = os.path.join(series_plot_dir, type_plot_basename)
                multi_lamb_plot(multi_resfits_and_metadata=multi_resfits_and_metadata,
                                series_type=metadata_type,
                                res_num=self.unified_metadata['res_num'],
                                multi_input_data=multi_input_data,
                                multi_lamb_params_fit=multi_lamb_params_fit,
                                multi_labels=multi_labels,
                                current_axis_num_of_points=1000, show_text=False,
                                output_filename=self.lamb_plot_path)
        if no_series_plots and self.do_plot:
            self.fit()


if __name__ == "__main__":
    test_folder = "C:\\Users\\chw3k5\\PycharmProjects\\WaferScreen\\waferscreen\\nist\\12\\2021-02-10\\pro\\" + \
                  "res9_scan3.900GHz-4.500GHz_2021-02-10 19-04-56.938380_phase_windowbaselinesmoothedremoved"
    lamb_calc = LambCalc(lamb_dir=test_folder, auto_fit=False)
    lamb_calc.read_input()
    lamb_calc.sort_by_type()
