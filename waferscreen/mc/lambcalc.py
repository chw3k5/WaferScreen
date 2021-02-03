import os
from operator import attrgetter, itemgetter
from typing import NamedTuple, Optional
import numpy as np
from scipy.optimize import curve_fit
from waferscreen.analyze.s21_io import write_s21, read_s21
from waferscreen.analyze.lambfit import Phi0, f0_of_I, guess_lamb_fit_params
import ref

import matplotlib.pyplot as plt

lamb_params_prime_types = ["I0fit", "mfit", "f2fit", "Pfit", "lambfit"]
lambda_header_list = []
for prime_type in lamb_params_prime_types:
    lambda_header_list.append(prime_type)
    lambda_header_list.append(F"{prime_type}_err")
lambda_header = F"{lambda_header_list[0]}"
for header_item in lambda_header_list[1:]:
    lambda_header += F",{header_item}"


class LambdaParams(NamedTuple):
    I0fit: float
    mfit: float
    f2fit: float
    Pfit: float
    lambfit: float
    res_num: int
    parent_dir: str
    I0fit_err: Optional[float] = None
    mfit_err: Optional[float] = None
    f2fit_err: Optional[float] = None
    Pfit_err: Optional[float] = None
    lambfit_err: Optional[float] = None

    def __str__(self):
        output_string = ""
        for header_item in lambda_header_list:
            output_string += str(self.__getattribute__(header_item)) + ","
        return output_string[:-1]


class LambCalc:
    def __init__(self, lambda_dir, auto_fit=True):
        self.lambda_dir = lambda_dir
        self.input_paths = None
        self.res_fit_to_metadata = None
        self.resfits_and_metadata = None
        self.lamb_params_guess = None
        self.lamb_params_fit = None
        self.unified_metadata = None
        if auto_fit:
            self.read_input()
            self.fit()

    def read_input(self):
        self.input_paths = []
        for test_filename in os.listdir(self.lambda_dir):
            if "." in test_filename:
                _basename_prefix, extension = test_filename.rsplit(".", 1)
                if extension in ref.s21_file_extensions:
                    self.input_paths.append(os.path.join(self.lambda_dir, test_filename))
        self.res_fit_to_metadata = {}
        self.resfits_and_metadata = []
        for input_path in self.input_paths:
            _formatted_s21_dict, metadata_this_file, res_fits = read_s21(path=input_path, return_res_params=True)
            for res_fit in res_fits:
                self.res_fit_to_metadata[res_fit] = metadata_this_file
                self.resfits_and_metadata.append((metadata_this_file['flux_current_ua'], res_fit, metadata_this_file))
                # some of the metadata is the same across all resonators, that result is in self.unified_metadata
                if self.unified_metadata is None:
                    # this is the first metadata encountered
                    self.unified_metadata = {}
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
        self.resfits_and_metadata = sorted(self.resfits_and_metadata, key=itemgetter(0))

    def fit(self):
        currentuA = np.array([pair[0] for pair in self.resfits_and_metadata])
        freqGHz = np.array([pair[1].fcenter_ghz for pair in self.resfits_and_metadata])
        # guess for curve fit
        currentA = currentuA * 1.0e-6
        I0fit_guess, mfit_guess, f2fit_guess, Pfit_guess, lambfit_guess = guess_lamb_fit_params(currentA, freqGHz)
        self.lamb_params_guess = LambdaParams(I0fit=I0fit_guess, mfit=mfit_guess, f2fit=f2fit_guess, Pfit=Pfit_guess,
                                              lambfit=lambfit_guess, res_num=self.unified_metadata["res_num"],
                                              parent_dir=self.lambda_dir)

        popt, pcov = curve_fit(f0_of_I, currentA, freqGHz, (I0fit_guess, mfit_guess, f2fit_guess, Pfit_guess,
                                                            lambfit_guess))
        I0fit, mfit, f2fit, Pfit, lambfit = popt
        I0fit_err = pcov[0, 0]
        mfit_err = pcov[1, 1]
        f2fit_err = pcov[2, 2]
        Pfit_err = pcov[3, 3]
        lambfit_err = pcov[4, 4]
        self.lamb_params_fit = LambdaParams(I0fit=I0fit, mfit=mfit, f2fit=f2fit, Pfit=Pfit, lambfit=lambfit,
                                            res_num=self.unified_metadata["res_num"], parent_dir=self.lambda_dir,
                                            I0fit_err=I0fit_err, mfit_err=mfit_err, f2fit_err=f2fit_err,
                                            Pfit_err=Pfit_err, lambfit_err=lambfit_err)

        q_i_array = np.array([res_param.q_i for res_param in [a_tuple[1] for a_tuple in self.resfits_and_metadata]])
        q_i_mean = np.mean(q_i_array)
        q_i_std = np.std(q_i_array)
        q_c_array = np.array([res_param.q_c for res_param in [a_tuple[1] for a_tuple in self.resfits_and_metadata]])
        q_c_mean = np.mean(q_c_array)
        q_c_std = np.std(q_c_array)
        lamb_format_str = '%8.6f'
        q_format_str = "%i"
        title_str = F"Resonator Number: {self.lamb_params_fit.res_num},  "
        title_str += F"lambda: {lamb_format_str % self.lamb_params_fit.lambfit} "
        title_str += F"({lamb_format_str % self.lamb_params_fit.lambfit_err})  "
        title_str += F"mean Qi: {q_format_str % q_i_mean} "
        title_str += F"({q_format_str % q_i_std})  "
        title_str += F"mean Qc: {q_format_str % q_c_mean} "
        title_str += F"({q_format_str % q_c_std})"
        self.lamb_plot(input_data=(currentuA, freqGHz), lamb_params_guess=self.lamb_params_guess,
                       lamb_params_fit=self.lamb_params_fit, resfits_and_metadata=self.resfits_and_metadata,
                       title_str=title_str)
        
    @staticmethod
    def lamb_plot(input_data=None, lamb_params_guess=None, lamb_params_fit=None, resfits_and_metadata=None,
                  current_axis_num_of_points=1000, title_str=None, output_filename=None):
        fig = plt.figure(figsize=(14, 8))
        leglines = []
        leglabels = []
        f_min_GHz = None

        # define the current axis that the guess and fitter plots use
        if input_data is None:
            current_axis_uA = np.linspace(-125, 125, current_axis_num_of_points)
        else:
            currentuA, freqGHz = input_data
            current_axis_uA = np.linspace(np.min(currentuA), np.max(currentuA), current_axis_num_of_points)

        # This is final result of the parameters found using curve-fit
        if lamb_params_fit is not None:
            current_axis_A = current_axis_uA * 1.0e-6
            final_fit_out_GHz = f0_of_I(ramp_current_amps=current_axis_A,
                                        ramp_current_amps_0=lamb_params_fit.I0fit,
                                        m=lamb_params_fit.mfit, f2=lamb_params_fit.f2fit,
                                        P=lamb_params_fit.Pfit, lamb=lamb_params_fit.lambfit)
            if f_min_GHz is None:
                f_min_GHz = np.min(final_fit_out_GHz)
            final_fit_delta_f_kHz = (final_fit_out_GHz - f_min_GHz) * 1.0e6
            fit_color = "firebrick"
            fit_linewidth = 2

            plt.plot(current_axis_uA, final_fit_delta_f_kHz, color=fit_color,
                     linewidth=fit_linewidth)
            leglines.append(plt.Line2D(range(10), range(10), color=fit_color, ls="-",
                                       linewidth=fit_linewidth))
            leglabels.append(F"Fitted Parameters")

        # This is the guess of parameters that are used to initialize the curve-fit
        if lamb_params_guess is not None:
            current_axis_A = current_axis_uA * 1.0e-6
            guess_fit_out_GHz = f0_of_I(ramp_current_amps=current_axis_A, ramp_current_amps_0=lamb_params_guess.I0fit,
                                        m=lamb_params_guess.mfit, f2=lamb_params_guess.f2fit,
                                        P=lamb_params_guess.Pfit, lamb=lamb_params_guess.lambfit)
            if f_min_GHz is None:
                f_min_GHz = np.min(guess_fit_out_GHz)
            guess_fit_delta_f_kHz = (guess_fit_out_GHz - f_min_GHz) * 1.0e6
            guess_color = "dodgerblue"
            guess_linewidth = 1

            plt.plot(current_axis_uA, guess_fit_delta_f_kHz, color=guess_color,
                     linewidth=guess_linewidth)
            leglines.append(plt.Line2D(range(10), range(10), color=guess_color, ls="-",
                                       linewidth=guess_linewidth))
            leglabels.append(F"Initial Parameters Guess")

        # the raw data that is used as the basis for a fit/lambda parameter determination.
        if input_data is not None:
            currentuA, freqGHz = input_data
            if f_min_GHz is None:
                f_min_GHz = np.min(freqGHz)
            delta_f_kHz = (freqGHz - f_min_GHz) * 1.0e6
            input_data_color = "darkorchid"
            input_data_linewidth = 1
            input_data_ls = "none"
            input_data_alpha = 0.65
            input_data_marker = 'o'
            input_data_markersize = 10
            plt.plot(currentuA, delta_f_kHz,
                     color=input_data_color,
                     linewidth=input_data_linewidth, ls=input_data_ls, marker=input_data_marker,
                     markersize=input_data_markersize, markerfacecolor=input_data_color, alpha=input_data_alpha)
            leglines.append(plt.Line2D(range(10), range(10), color=input_data_color, ls=input_data_ls,
                                       linewidth=input_data_linewidth, marker=input_data_marker,
                                       markersize=input_data_markersize,
                                       markerfacecolor=input_data_color, alpha=input_data_alpha))
            leglabels.append(F"Fit Input Data")
            if resfits_and_metadata is not None:
                for single_uA, res_fit, single_metadata in resfits_and_metadata:
                    single_delta_f_kHz = (res_fit.fcenter_ghz - f_min_GHz) * 1.0e6
                    q_format_str = '%i'
                    text_str = F"{single_uA} uA\nQi: {q_format_str % res_fit.q_i}\nQc: {q_format_str % res_fit.q_c}"
                    plt.text(x=single_uA, y=single_delta_f_kHz, s=text_str, color="white", fontsize=6,
                             bbox={"facecolor": input_data_color, "alpha": 0.5})

        # Whole plot options:
        plt.xlabel(F"Flux Ramp Current (uA)")
        plt.ylabel(F"Relative Frequency Center (kHz)")
        if title_str is not None:
            plt.title(title_str)
        plt.legend(leglines, leglabels, loc=0, numpoints=3, handlelength=5, fontsize=10)
        # Display
        if output_filename is not None:
            plt.draw()
            plt.savefig(output_filename)
            print("Saved Plot to:", output_filename)
        else:
            plt.show(block=True)
        plt.close(fig=fig)


if __name__ == "__main__":
    test_folder = "C:\\Users\\chw3k5\\PycharmProjects\\WaferScreen\\waferscreen\\nist\\9\\2021-01-26\\pro\\" + \
                  "res76_scan3.800GHz-6.200GHz_2021-01-26 22-35-20.055941_phase_windowbaselinesmoothedremoved"
    lc = LambCalc(lambda_dir=test_folder, auto_fit=True)
