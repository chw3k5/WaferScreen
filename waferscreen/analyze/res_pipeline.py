# Copyright (C) 2018 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import os
import copy
from shutil import rmtree
import numpy as np
from scipy.signal import savgol_filter
from scipy.interpolate import interp1d
from waferscreen.data_io.s21_io import read_s21, write_s21, ri_to_magphase, magphase_to_realimag, \
    generate_output_filename
from waferscreen.plot.s21_plots import plot_filter, plot_res_fit, band_plot
from waferscreen.data_io.series_io import SeriesKey, series_key_header
import waferscreen.analyze.res_pipeline_config as rpc
from waferscreen.data_io.res_io import ResParams
from waferscreen.analyze.resfit import wrap_simple_res_gain_slope_complex, package_res_results
from waferscreen.data_io.jobs_io import JobOrganizer
from waferscreen.data_io.exceptions import ResMinIsLeftMost, ResMinIsRightMost
from submm_python_routines.KIDs import find_resonances_interactive as fr_interactive
import ref


def fwhm_old(goal_depth, f_hz_single_res, s21_mag_singe_res):
    f_fwhm_hz_now = f_fwhm_hz_last = f_fwhm_mag_now = f_fwhm_mag_last = None
    for single_f_hz, single_linear_mag in zip(f_hz_single_res, s21_mag_singe_res):
        if single_linear_mag < goal_depth:
            f_fwhm_hz_now = single_f_hz
            f_fwhm_mag_now = single_linear_mag
            break
        else:
            f_fwhm_hz_last = single_f_hz
            f_fwhm_mag_last = single_linear_mag
    if any([f_fwhm_hz_now is None, f_fwhm_hz_last is None, f_fwhm_mag_now is None, f_fwhm_mag_last is None]):
        if f_fwhm_hz_now is not None and f_fwhm_mag_now is not None:
            return f_fwhm_hz_now
        raise UnboundLocalError(F"the FWHM function needs at least one data point to not error,\n" +
                                F"but it needs a lot more to work well.\n")
    slope = (f_fwhm_hz_now - f_fwhm_hz_last) / (f_fwhm_mag_now - f_fwhm_mag_last)
    f_fwhm_hz = ((goal_depth - f_fwhm_mag_last) * slope) + f_fwhm_hz_last
    return f_fwhm_hz


def fwhm(frequency_array, s21_linear_mag, minima_index, left_goal_depth, right_goal_depth):
    # find the left full-width-half-maximum (FWHM)
    if minima_index == 0:
        # this is what happens if there is nothing to the left of the minima, i.e. the minima is the left most point
        f_fwhm_left = frequency_array[minima_index]
    else:
        f_fwhm_mag_now_left = s21_linear_mag[minima_index]
        f_fwhm_now_left = frequency_array[minima_index]
        f_fwhm_last_left = None
        f_fwhm_mag_last_left = None
        # start from the minima and go to the left to find the fwhm
        for single_f_left, single_linear_mag_left in \
                zip(reversed(frequency_array[:minima_index]), reversed(s21_linear_mag[:minima_index])):
            f_fwhm_last_left = f_fwhm_now_left
            f_fwhm_mag_last_left = f_fwhm_mag_now_left
            f_fwhm_now_left = single_f_left
            f_fwhm_mag_now_left = single_linear_mag_left
            if f_fwhm_mag_now_left > left_goal_depth:
                break
        if f_fwhm_last_left is None:
            # this happens when the minima of the trace is the left most point
            raise ResMinIsLeftMost
        else:
            slope = (f_fwhm_now_left - f_fwhm_last_left) / (f_fwhm_mag_now_left - f_fwhm_mag_last_left)
            f_fwhm_left = ((left_goal_depth - f_fwhm_mag_last_left) * slope) + f_fwhm_last_left
    # do the same thing for the right side, a lot of repeated code
    if minima_index == len(s21_linear_mag):
        # this is what happens if there is nothing to the right of the minima, i.e. the minima is the right most point
        f_fwhm_right = frequency_array[minima_index]
    else:
        # at least on frequency point to the right of the minima
        f_fwhm_mag_now_right = s21_linear_mag[minima_index]
        f_fwhm_now_right = frequency_array[minima_index]
        f_fwhm_last_right = None
        f_fwhm_mag_last_right = None
        # start from the minima and go to the left to find the fwhm
        for single_f_right, single_linear_mag_right in \
                zip(frequency_array[minima_index + 1:], s21_linear_mag[minima_index + 1:]):
            f_fwhm_last_right = f_fwhm_now_right
            f_fwhm_mag_last_right = f_fwhm_mag_now_right
            f_fwhm_now_right = single_f_right
            f_fwhm_mag_now_right = single_linear_mag_right
            if f_fwhm_mag_now_right > right_goal_depth:
                break
        if f_fwhm_last_right is None:
            # this happens when the minima of the trace is the right most point
            raise ResMinIsRightMost
        else:
            slope = (f_fwhm_now_right - f_fwhm_last_right) / (f_fwhm_mag_now_right - f_fwhm_mag_last_right)
            f_fwhm_right = ((right_goal_depth - f_fwhm_mag_last_right) * slope) + f_fwhm_last_right
    return f_fwhm_left, f_fwhm_right


def guess_res_params(freq_ghz, s21_mag_db, s21_phase_rad, left_margin=None, right_margin=None, margin_fraction=0.1):
    # most of the calculation needs to be in linear magnitude space for clarity.
    s21_linear_mag = 10.0 ** (s21_mag_db / 20.0)
    # determine an approximate baseline margin on each side of the resonator, estimate if None are provided
    if left_margin is None or right_margin is None:
        data_len = len(s21_mag_db)
        margin_len = int(np.round(data_len * margin_fraction))
        if left_margin is None:
            left_margin = margin_len
        if right_margin is None:
            right_margin = data_len - margin_len
    left_lin_mag_s21 = np.mean(s21_linear_mag[0:left_margin + 1])
    right_lin_mag_s21 = np.mean(s21_linear_mag[right_margin:])
    # frequency calculations
    delta_freq_ghz = freq_ghz[-1] - freq_ghz[0]
    # minima calculations
    minima_index = np.argmin(s21_mag_db)
    minima_mag = s21_mag_db[minima_index]
    minima_mag_lin = s21_linear_mag[minima_index]
    # find the fullwidth half maximum basically 3 dB down from the baseline
    left_goal_depth = left_lin_mag_s21 + (0.5 * (minima_mag_lin - left_lin_mag_s21))
    right_goal_depth = right_lin_mag_s21 + (0.5 * (minima_mag_lin - right_lin_mag_s21))
    f_fwhm_left_ghz, f_fwhm_right_ghz = fwhm(frequency_array=freq_ghz, s21_linear_mag=s21_linear_mag,
                                             minima_index=minima_index, left_goal_depth=left_goal_depth,
                                             right_goal_depth=right_goal_depth)
    # fcenter
    fcenter_guess_ghz = freq_ghz[minima_index]
    # base amplitude
    base_amplitude_lin_mag = (left_lin_mag_s21 + right_lin_mag_s21) / 2.0
    # base amplitude slope
    base_amplitude_slope_guess = (left_lin_mag_s21 - right_lin_mag_s21) / (delta_freq_ghz * 2.0 * np.pi)
    # base phase
    a_phase_rad_guess = float(np.mean(s21_phase_rad))
    # Quality factors
    q_guess_ghz = f_fwhm_right_ghz - f_fwhm_left_ghz
    q_guess = fcenter_guess_ghz / q_guess_ghz
    base_amplitude_mag = 20.0 * np.log10(base_amplitude_lin_mag)
    q_i_guess = q_guess * np.sqrt(base_amplitude_mag - minima_mag)
    q_c_guess = q_i_guess * q_guess / (q_i_guess - q_guess)
    # phase slope?, this removed by s21_inductor...
    tau_ns_guess = 0.0
    # package the resonator parameters
    params_guess = ResParams(base_amplitude_abs=base_amplitude_lin_mag, a_phase_rad=a_phase_rad_guess,
                             base_amplitude_slope=base_amplitude_slope_guess, tau_ns=tau_ns_guess,
                             fcenter_ghz=fcenter_guess_ghz, q_i=q_i_guess, q_c=q_c_guess, impedance_ratio=0)
    plot_data = {"f_fwhm_left_ghz": f_fwhm_left_ghz, "f_fwhm_right_ghz": f_fwhm_right_ghz,
                 "left_goal_depth": left_goal_depth, "right_goal_depth": right_goal_depth,
                 "minima_mag": minima_mag, "left_margin": left_margin, "right_margin": right_margin}
    return params_guess, plot_data


class ResPipe:
    def __init__(self, s21_path, verbose=True):
        self.path = s21_path
        self.dirname, self.basename = os.path.split(self.path)
        self.basename_prefix, self.file_extension = self.basename.rsplit(".", 1)

        self.res_plot_dir = os.path.join(self.dirname, F"resonator_plots")
        self.report_dir = os.path.join(self.dirname, F"report")

        self.job_organizer = JobOrganizer(check_for_old_jobs=False)

        self.verbose = verbose
        self.metadata = None
        self.unprocessed_freq_ghz, self.unprocessed_reals21, self.unprocessed_imags21 = None, None, None
        self.unprocessed_freq_hz = None
        self.unprocessed_mags21, self.unprocessed_phases21 = None, None
        self.lowpass_filter_reals21, self.lowpass_filter_imags21 = None, None
        self.highpass_filter_reals21, self.highpass_filter_imags21 = None, None
        self.highpass_filter_mags21, self.lowpass_filter_mags21 = None, None
        self.highpass_linear_mag, self.not_smoothed_mag, self.synthetic_baseline_smoothed = None, None, None
        self.highpass_phase = None  # phase does not really change with the current processing
        self.minima_as_windows = None
        self.fitted_resonators_parameters = None

        self.is_even_bands = None
        self.fitted_resonators_parameters_by_band = None

    def read(self):
        data_dict, self.metadata, self.fitted_resonators_parameters = read_s21(path=self.path, return_res_params=True)
        self.unprocessed_freq_ghz = data_dict["freq_ghz"]
        self.unprocessed_freq_hz = self.unprocessed_freq_ghz * 1.0e9
        self.unprocessed_reals21, self.unprocessed_imags21 = data_dict["real"], data_dict["imag"]
        self.unprocessed_mags21, self.unprocessed_phases21 = ri_to_magphase(r=self.unprocessed_reals21,
                                                                            i=self.unprocessed_imags21)

    def write(self, output_file, freqs_ghz, s21_complex):
        write_s21(output_file, freqs_ghz, s21_complex, metadata=self.metadata,
                  fitted_resonators_parameters=self.fitted_resonators_parameters)

    def generate_output_filename(self, processing_steps):
        return generate_output_filename(processing_steps=processing_steps,
                                        basename_prefix=self.basename_prefix,
                                        dirname=self.dirname, file_extension=self.file_extension)

    def savgol_filter_mag(self, reals21=None, imags21=None, window_length=31, polyorder=2, plot=False):
        self.filter_reset()
        mag, phase = ri_to_magphase(r=reals21, i=imags21)
        if window_length % 2 == 0:
            # window length needs to be an odd int
            window_length += 1
        self.filter_update_mag(mag=mag, phase=phase,
                               lowpass_filter_mags21=savgol_filter(x=mag, window_length=window_length,
                                                                   polyorder=polyorder),
                               plot=plot)
        return mag, phase

    def filter_reset(self):
        self.lowpass_filter_reals21, self.lowpass_filter_imags21 = None, None
        self.highpass_filter_reals21, self.highpass_filter_imags21 = None, None
        self.highpass_filter_mags21, self.lowpass_filter_mags21 = None, None

    def filter_update_mag(self, mag, phase, lowpass_filter_mags21, plot=False):
        self.lowpass_filter_mags21 = lowpass_filter_mags21
        self.highpass_filter_mags21 = mag - self.lowpass_filter_mags21
        self.lowpass_filter_reals21, self.lowpass_filter_imags21 = \
            magphase_to_realimag(mag=self.lowpass_filter_mags21, phase=phase)
        self.highpass_filter_reals21, self.highpass_filter_imags21 = \
            magphase_to_realimag(mag=self.highpass_filter_mags21, phase=phase)
        if plot:
            self.plot_filter()

    def savgol_filter_ri(self, reals21=None, imags21=None, window_length=31, polyorder=2, plot=False):
        self.filter_reset()
        if reals21 is None or imags21 is None:
            reals21, imags21 = self.unprocessed_reals21, self.unprocessed_imags21
        if window_length % 2 == 0:
            # window length needs to be an odd int
            window_length += 1
        self.lowpass_filter_reals21 = savgol_filter(x=reals21, window_length=window_length, polyorder=polyorder)
        self.lowpass_filter_imags21 = savgol_filter(x=imags21, window_length=window_length, polyorder=polyorder)
        self.highpass_filter_reals21 = reals21 - self.lowpass_filter_reals21
        self.highpass_filter_imags21 = imags21 - self.lowpass_filter_imags21
        if plot:
            self.plot_filter()

    def cosine_filter_mag(self, reals21=None, imags21=None, smoothing_scale=5.0e6, plot=False):
        self.filter_reset()
        mag, phase = ri_to_magphase(r=reals21, i=imags21)
        self.lowpass_filter_mags21 = \
            fr_interactive.lowpass_cosine(y=mag,
                                          tau=(self.unprocessed_freq_ghz[1] - self.unprocessed_freq_ghz[0]) * 1.0e9,
                                          f_3db=1.0 / smoothing_scale,
                                          width=0.1 * (1.0 / smoothing_scale),
                                          padd_data=True)
        # this filter needs odd lengths of data
        mag = mag[:len(self.lowpass_filter_mags21)]
        phase = phase[:len(self.lowpass_filter_mags21)]
        self.unprocessed_freq_ghz = self.unprocessed_freq_ghz[:len(self.lowpass_filter_mags21)]
        self.unprocessed_reals21 = self.unprocessed_reals21[:len(self.lowpass_filter_mags21)]
        self.unprocessed_imags21 = self.unprocessed_imags21[:len(self.lowpass_filter_mags21)]
        self.highpass_filter_mags21 = mag - self.lowpass_filter_mags21
        self.lowpass_filter_reals21, self.lowpass_filter_imags21 = \
            magphase_to_realimag(mag=self.lowpass_filter_mags21, phase=phase)
        self.highpass_filter_reals21, self.highpass_filter_imags21 = \
            magphase_to_realimag(mag=self.highpass_filter_mags21, phase=phase)
        if plot:
            self.plot_filter()
        return mag, phase

    def plot_filter(self):
        plot_filter(freqs_GHz=self.unprocessed_freq_ghz,
                    original_s21=self.unprocessed_reals21 + 1j * self.unprocessed_imags21,
                    lowpass_s21=self.lowpass_filter_reals21 + 1j * self.lowpass_filter_imags21,
                    highpass_s21=self.highpass_filter_reals21 + 1j * self.highpass_filter_imags21)

    def find_window(self, cosine_filter=None, window_pad_factor=3, fitter_pad_factor=5, show_filter_plots=False,
                    debug_mode=False):
        # initial filtering in magnitude space
        f_step_ghz = self.unprocessed_freq_ghz[1] - self.unprocessed_freq_ghz[0]
        window_length = int(np.round(rpc.baseline_smoothing_window_ghz / f_step_ghz))
        if cosine_filter is not None:
            if cosine_filter:
                mag, phase = self.cosine_filter_mag(reals21=self.unprocessed_reals21, imags21=self.unprocessed_imags21,
                                                    smoothing_scale=rpc.baseline_smoothing_window_ghz * 1.0e9,
                                                    plot=show_filter_plots)
            else:
                mag, phase = self.savgol_filter_mag(reals21=self.unprocessed_reals21, imags21=self.unprocessed_imags21,
                                                    window_length=window_length, polyorder=2, plot=show_filter_plots)
        # interaction threshold plotting, return local minima and window information about size of the resonators
        i_thresh = fr_interactive.InteractiveThresholdPlot(f_Hz=self.unprocessed_freq_ghz * 1.0e9,
                                                           s21_mag=self.highpass_filter_mags21,
                                                           peak_threshold_dB=2.0,
                                                           spacing_threshold_Hz=rpc.resonator_spacing_threshold_hz,
                                                           window_pad_factor=window_pad_factor,
                                                           fitter_pad_factor=fitter_pad_factor,
                                                           debug_mode=debug_mode)
        self.highpass_filter_mags21[self.highpass_filter_mags21 > -1.0 * i_thresh.peak_threshold_dB] = 0
        res_indexes = []
        baseline_indexes = []
        for minima_index, data_index_minima in list(enumerate(i_thresh.local_minima)):
            single_window = i_thresh.minima_as_windows[minima_index]
            baseline_indexes.extend(list(range(single_window.left_max, single_window.left_pad)))
            res_indexes.extend(list(range(single_window.left_pad, single_window.right_pad)))
            baseline_indexes.extend(list(range(single_window.right_pad, single_window.right_max)))

        baseline_mag_values = mag[baseline_indexes]
        f = interp1d(x=baseline_indexes, y=baseline_mag_values, kind='cubic')
        synthetic_baseline = f(range(len(self.unprocessed_freq_ghz)))
        self.filter_update_mag(mag=mag, phase=phase,
                               lowpass_filter_mags21=synthetic_baseline,
                               plot=show_filter_plots)

        self.not_smoothed_mag = copy.copy(self.highpass_filter_mags21)
        if window_length % 2 == 0:
            window_length += 1
        self.synthetic_baseline_smoothed = savgol_filter(x=synthetic_baseline,
                                                         window_length=window_length, polyorder=3)
        self.filter_update_mag(mag=mag, phase=phase,
                               lowpass_filter_mags21=self.synthetic_baseline_smoothed,
                               plot=show_filter_plots)
        self.highpass_phase = phase
        self.highpass_linear_mag = np.sqrt(
            (self.highpass_filter_reals21 ** 2.0) + (self.highpass_filter_imags21 ** 2.0))

        self.minima_as_windows = i_thresh.minima_as_windows
        self.metadata["window_pad_factor"] = window_pad_factor
        self.metadata["fitter_pad_factor"] = fitter_pad_factor
        self.metadata["peak_threshold_db"] = i_thresh.peak_threshold_dB

    def prepare_res_pot_dir(self):
        if os.path.exists(self.res_plot_dir):
            rmtree(self.res_plot_dir)
        os.mkdir(self.res_plot_dir)

    def analyze_resonators(self, save_res_plots=False):
        if save_res_plots:
            self.prepare_res_pot_dir()
        self.fitted_resonators_parameters = []
        for res_number, single_window in zip(range(1, len(self.minima_as_windows) + 1), self.minima_as_windows):
            # get slices of data ready
            fitter_slice = slice(single_window.left_fitter_pad, single_window.right_fitter_pad)
            f_ghz_single_res = self.unprocessed_freq_ghz[fitter_slice]
            s21_mag_single_res = self.unprocessed_mags21[fitter_slice]
            s21_phase_single_res = self.highpass_phase[fitter_slice]
            s21_mag_single_res_highpass = self.highpass_filter_mags21[fitter_slice]
            s21_mag_single_res_highpass_linear = self.highpass_linear_mag[fitter_slice]
            s21_real_single_res_highpass = self.highpass_filter_reals21[fitter_slice]
            s21_imag_single_res_highpass = self.highpass_filter_imags21[fitter_slice]
            s21_complex_single_res_highpass = s21_real_single_res_highpass + 1j * s21_imag_single_res_highpass

            left_margin = single_window.left_window - single_window.left_fitter_pad
            right_margin = single_window.right_fitter_pad - single_window.right_window

            params_guess, plot_data = guess_res_params(freq_ghz=f_ghz_single_res,
                                                       s21_mag_db=s21_mag_single_res_highpass,
                                                       s21_phase_rad=s21_phase_single_res,
                                                       left_margin=left_margin, right_margin=right_margin)

            popt, pcov = wrap_simple_res_gain_slope_complex(freqs_GHz=f_ghz_single_res,
                                                            s21_complex=s21_complex_single_res_highpass,
                                                            s21_linear_mag=s21_mag_single_res_highpass_linear,
                                                            base_amplitude_abs_guess=params_guess.base_amplitude_abs,
                                                            a_phase_rad_guess=params_guess.a_phase_rad,
                                                            fcenter_GHz_guess=params_guess.fcenter_ghz,
                                                            q_i_guess=params_guess.q_i,
                                                            q_c_guess=params_guess.q_c,
                                                            base_amplitude_slope_guess=params_guess.base_amplitude_slope,
                                                            tau_ns_guess=params_guess.tau_ns,
                                                            impedance_ratio_guess=params_guess.impedance_ratio)
            params_fit = package_res_results(popt=popt, pcov=pcov, res_number=res_number,
                                             flux_ramp_current_ua=self.metadata["flux_current_ua"],
                                             parent_file=self.path, verbose=self.verbose)
            self.fitted_resonators_parameters.append(params_fit)
            if save_res_plots:
                plot_res_fit(f_GHz_single_res=f_ghz_single_res,
                             s21_mag_single_res=s21_mag_single_res - s21_mag_single_res[0],
                             not_smoothed_mag_single_res=self.not_smoothed_mag[fitter_slice],
                             s21_mag_single_res_highpass=s21_mag_single_res_highpass,
                             params_guess=params_guess, params_fit=params_fit,
                             minima_pair=(self.unprocessed_freq_ghz[single_window.minima],
                                          self.highpass_filter_mags21[single_window.minima]),
                             fwhm_pair=((plot_data["f_fwhm_left_ghz"], plot_data["f_fwhm_right_ghz"]),
                                        (plot_data["left_goal_depth"], plot_data["right_goal_depth"])),
                             window_pair=((self.unprocessed_freq_ghz[single_window.left_window],
                                           self.unprocessed_freq_ghz[single_window.right_window]),
                                          (self.highpass_filter_mags21[single_window.left_window],
                                           self.highpass_filter_mags21[single_window.right_window])),
                             fitter_pair=((self.unprocessed_freq_ghz[single_window.left_pad],
                                           self.unprocessed_freq_ghz[single_window.right_pad]),
                                          (self.highpass_filter_mags21[single_window.left_pad],
                                           self.highpass_filter_mags21[single_window.right_pad])),
                             zero_line=True,
                             output_filename=os.path.join(self.res_plot_dir, F"{'%04i' % res_number}.png"))
        self.metadata["baseline_removed"] = True
        self.metadata["baseline_technique"] = "windows function based on the a threshold then smoothed"
        self.metadata["smoothing_scale_ghz"] = rpc.baseline_smoothing_window_ghz
        self.metadata["resonator_spacing_threshold_hz"] = rpc.resonator_spacing_threshold_hz
        data_filename, plot_filename = self.generate_output_filename(processing_steps=["windowBaselineSmoothedRemoved"])
        output_s21complex = self.highpass_filter_reals21 + 1j * self.highpass_filter_imags21
        self.write(output_file=data_filename, freqs_ghz=self.unprocessed_freq_ghz,
                   s21_complex=output_s21complex)

    def analyze_single_res(self, save_res_plots=True):
        s21_complex = self.unprocessed_reals21 + 1j * self.unprocessed_imags21
        s21_linear_mag = np.sqrt((self.unprocessed_reals21 ** 2.0) + (self.unprocessed_imags21 ** 2.0))
        params_guess, plot_data = guess_res_params(freq_ghz=self.unprocessed_freq_ghz,
                                                   s21_mag_db=self.unprocessed_mags21,
                                                   s21_phase_rad=self.unprocessed_phases21)
        file_prefix = ""
        try:
            popt, pcov = wrap_simple_res_gain_slope_complex(freqs_GHz=self.unprocessed_freq_ghz,
                                                            s21_complex=s21_complex,
                                                            s21_linear_mag=s21_linear_mag,
                                                            base_amplitude_abs_guess=params_guess.base_amplitude_abs,
                                                            a_phase_rad_guess=params_guess.a_phase_rad,
                                                            fcenter_GHz_guess=params_guess.fcenter_ghz,
                                                            q_i_guess=params_guess.q_i,
                                                            q_c_guess=params_guess.q_c,
                                                            base_amplitude_slope_guess=params_guess.base_amplitude_slope,
                                                            tau_ns_guess=params_guess.tau_ns,
                                                            impedance_ratio_guess=params_guess.impedance_ratio)
        except RuntimeError:
            file_prefix += "FAIL_"
            save_res_plots = True
            params_fit = None
            print(F"\nFAILED FIT: {self.path}\n")
        else:
            params_fit = package_res_results(popt=popt, pcov=pcov, res_number=self.metadata["res_num"],
                                             flux_ramp_current_ua=self.metadata["flux_current_ua"],
                                             parent_file=self.path, verbose=self.verbose)
            self.fitted_resonators_parameters = [params_fit]
            self.write(output_file=self.path, freqs_ghz=self.unprocessed_freq_ghz, s21_complex=s21_complex)

        if save_res_plots:
            # file name handling
            basename = F"{file_prefix}{'%04i' % self.metadata['res_num']}_cur{'%6.3f' % self.metadata['flux_current_ua']}uA.png"
            series_name = F"{SeriesKey(port_power_dbm=self.metadata['port_power_dbm'], if_bw_hz=self.metadata['if_bw_hz'])}"
            subplot_path = os.path.join(self.res_plot_dir, series_name)
            if not os.path.isdir(subplot_path):
                # multiprocessing can cause this to happen multiple times in parallel
                try:
                    os.mkdir(subplot_path)
                except FileExistsError:
                    pass
            single_res_plot_path = os.path.join(subplot_path, basename)
            plot_res_fit(f_GHz_single_res=self.unprocessed_freq_ghz,
                         s21_mag_single_res=self.unprocessed_mags21,
                         not_smoothed_mag_single_res=None,
                         s21_mag_single_res_highpass=None,
                         params_guess=params_guess, params_fit=params_fit,
                         minima_pair=(params_guess.fcenter_ghz, plot_data["minima_mag"]),
                         fwhm_pair=((plot_data["f_fwhm_left_ghz"], plot_data["f_fwhm_right_ghz"]),
                                    (plot_data["left_goal_depth"], plot_data["right_goal_depth"])),
                         window_pair=None,
                         fitter_pair=((self.unprocessed_freq_ghz[plot_data["left_margin"]],
                                       self.unprocessed_freq_ghz[plot_data["right_margin"]]),
                                      (self.unprocessed_mags21[plot_data["left_margin"]],
                                       self.unprocessed_mags21[plot_data["right_margin"]])),
                         zero_line=False,
                         output_filename=single_res_plot_path)

    def scan_to_band(self, connected_group_threshold_ghz=0.07):
        f_centers_ghz = np.array([fit_params.fcenter_ghz for fit_params in self.fitted_resonators_parameters])
        res_nums = np.array([fit_params.res_number for fit_params in self.fitted_resonators_parameters])
        # find the connected groups
        connected_groups = []
        current_group = [self.fitted_resonators_parameters[0]]
        for f_index in range(len(f_centers_ghz) - 1):
            f_left_ghz = f_centers_ghz[f_index]
            f_right_ghz = f_centers_ghz[f_index + 1]
            if connected_group_threshold_ghz < f_right_ghz - f_left_ghz:
                connected_groups.append(current_group)
                current_group = []
            current_group.append(self.fitted_resonators_parameters[f_index + 1])
        else:
            if current_group:
                connected_groups.append(current_group)

        # make bins based on the band limits
        res_nums_per_band = {}
        for band_name_str in ref.band_names:
            min_ghz = ref.band_params[band_name_str]["min_GHz"]
            max_ghz = ref.band_params[band_name_str]["max_GHz"]
            # there is a dead space between bands, resonators in that space are not counted
            res_nums_over_min = set(res_nums[min_ghz <= f_centers_ghz])
            res_nums_below_max = set(res_nums[f_centers_ghz <= max_ghz])
            res_nums_per_band[band_name_str] = res_nums_over_min & res_nums_below_max

        # Expecting every other band to be mostly populated
        even_res_nums = set()
        even_band_nums = []
        even_band_names = []
        odd_res_nums = set()
        odd_band_nums = []
        odd_band_names = []
        for band_number, band_name_str in list(enumerate(ref.band_names)):
            if band_number % 2 == 0:
                [even_res_nums.add(res_num) for res_num in res_nums_per_band[band_name_str]]
                even_band_names.append(band_name_str)
                even_band_nums.append(band_number)
            else:
                [odd_res_nums.add(res_num) for res_num in res_nums_per_band[band_name_str]]
                odd_band_names.append(band_name_str)
                odd_band_nums.append(band_number)
        if len(odd_res_nums) < len(even_res_nums):
            self.is_even_bands = True
            band_names = even_band_names
            band_nums = even_band_nums
        else:
            self.is_even_bands = False
            band_names = odd_band_names
            band_nums = odd_band_nums

        # find the overlap between the connected groups of resonators and the resonators that are in known bands.
        self.fitted_resonators_parameters_by_band = {}
        for resonator_group in connected_groups:
            res_nums_this_group = set([fit_params.res_number for fit_params in resonator_group])
            for band_name, band_num in zip(band_names, band_nums):
                res_nums_this_band = res_nums_per_band[band_name]
                if res_nums_this_band & res_nums_this_group:
                    if band_name not in self.fitted_resonators_parameters_by_band.keys():
                        self.fitted_resonators_parameters_by_band[band_name] = []
                    self.fitted_resonators_parameters_by_band[band_name].extend(resonator_group)
                    break

    def report_scan_of_bands(self):
        if not os.path.exists(self.report_dir):
            os.mkdir(self.report_dir)
        band_plot(freqs_GHz=self.unprocessed_freq_ghz, mags=self.unprocessed_mags21,
                  fitted_resonators_parameters_by_band=self.fitted_resonators_parameters_by_band,
                  output_filename=os.path.join(self.report_dir, "band_report.pdf"))

    def prep_seed_dirs(self, seed_type):
        if "pro" in self.dirname:
            split_on = "pro"
        else:
            split_on = 'raw'
        date_str_path, _ = self.dirname.rsplit(split_on, 1)
        single_res_dir = os.path.join(date_str_path, 'raw', seed_type)
        if not os.path.exists(single_res_dir):
            os.mkdir(single_res_dir)
        scan_basename_dir = os.path.join(single_res_dir, self.basename_prefix)
        if not os.path.exists(scan_basename_dir):
            os.mkdir(scan_basename_dir)
        job_file_name = self.job_organizer.get_new_job_name(rf_chain_letter=self.metadata['rf_chain'])
        return scan_basename_dir, job_file_name

    def make_res_seeds(self):
        job_type = 'single_res'
        scan_basename_dir, job_file_name = self.prep_seed_dirs(seed_type=job_type)
        with open(job_file_name, 'w') as f:
            f.write(F"{job_type}\n")
            for band_str in sorted(self.fitted_resonators_parameters_by_band.keys()):
                for res_fit in self.fitted_resonators_parameters_by_band[band_str]:
                    seed_metadata = copy.deepcopy(self.metadata)
                    seed_metadata["so_band"] = band_str
                    seed_metadata["seed_base"] = self.basename_prefix
                    seed_metadata["seed_base_path"] = self.path
                    seed_metadata["res_number"] = res_fit.res_number
                    # make the correct output file in the 'raw' directory
                    res_dir = os.path.join(scan_basename_dir, F"{'%04i' % res_fit.res_number}")
                    if not os.path.exists(res_dir):
                        os.mkdir(res_dir)
                    seed_filename = os.path.join(res_dir, "seed.csv")
                    write_s21(output_file=seed_filename, metadata=seed_metadata,
                              fitted_resonators_parameters=[res_fit])
                    f.write(F"{seed_filename}\n")

    def make_band_seeds(self):
        scan_basename_dir, job_file_name = self.prep_seed_dirs(seed_type='bands')
        with open(job_file_name, 'w') as f:
            f.write('band\n')
            for band_str in sorted(self.fitted_resonators_parameters_by_band.keys()):
                seed_metadata = copy.deepcopy(self.metadata)
                seed_metadata["so_band"] = band_str
                seed_metadata["seed_base"] = self.basename_prefix
                seed_metadata["seed_base_path"] = self.path
                # make the correct output file in the 'raw' directory
                band_dir = os.path.join(scan_basename_dir, band_str)
                if not os.path.exists(band_dir):
                    os.mkdir(band_dir)
                seed_filename = os.path.join(band_dir, "seed.csv")
                write_s21(output_file=seed_filename, metadata=seed_metadata,
                          fitted_resonators_parameters=self.fitted_resonators_parameters_by_band[band_str])
                f.write(F"{seed_filename}\n")
