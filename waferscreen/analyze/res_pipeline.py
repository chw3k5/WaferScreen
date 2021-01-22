import numpy as np
from scipy.signal import savgol_filter
from scipy.interpolate import interp1d
from waferscreen.analyze.s21_io import read_s21, write_s21, ri_to_magphase, magphase_to_realimag
from waferscreen.plot.s21_plots import plot_filter, plot_res_fit

import waferscreen.analyze.res_pipeline_config as rpc
from waferscreen.analyze.res_io import ResParams
from waferscreen.analyze.res_fit_jake import wrap_simple_res_gain_slope_complex, package_res_results, jake_res_finder
from submm_python_routines.KIDs import find_resonances_interactive as fr_interactive
import copy


halfway_in_log_mag = 10.0 * np.log10(0.5)  # when 3 dB is not accurate enough

def fwhm(goal_depth, f_Hz_single_res, s21_mag_singe_res):
    f_fwhm_Hz_now = f_fwhm_Hz_last = f_fwhm_mag_now = f_fwhm_mag_last = None
    for single_f_Hz, single_linear_mag in zip(f_Hz_single_res, s21_mag_singe_res):
        if single_linear_mag < goal_depth:
            f_fwhm_Hz_now = single_f_Hz
            f_fwhm_mag_now = single_linear_mag
            break
        else:
            f_fwhm_Hz_last = single_f_Hz
            f_fwhm_mag_last = single_linear_mag
    else:
        if any([f_fwhm_Hz_now is None, f_fwhm_Hz_last is None, f_fwhm_mag_now is None, f_fwhm_mag_last is None]):
            raise UnboundLocalError(F"the FWHM function needs a keast two data point, to not error,\n" +
                                    F"but it needs a lot more to work well.\n")
    slope = (f_fwhm_Hz_now - f_fwhm_Hz_last) / (f_fwhm_mag_now - f_fwhm_mag_last)
    f_fwhm_Hz = ((goal_depth - f_fwhm_mag_last) * slope) + f_fwhm_Hz_last
    return f_fwhm_Hz


class ResPipe:
    def __init__(self, s21_path, verbose=True):
        self.path = s21_path
        self.verbose = True
        self.meta_data = None
        self.unprocessed_freq_GHz, self.unprocessed_reals21, self.unprocessed_imags21 = None, None, None
        self.unprocessed_freq_Hz = None
        self.unprocessed_mags21, self.unprocessed_phases21 = None, None
        self.lowpass_filter_reals21, self.lowpass_filter_imags21 = None, None
        self.highpass_filter_reals21, self.highpass_filter_imags21 = None, None
        self.highpass_filter_mags21, self.lowpass_filter_mags21 = None, None
        self.highpass_linear_mag, self.not_smoothed_mag, self.synthetic_baseline_smoothed = None, None, None
        self.highpass_phase = None  # phase does not really change with the current processing
        self.minima_as_windows = None
        self.fitted_resonators_parameters = None

    def read(self):
        data_dict, self.meta_data = read_s21(path=self.path)
        self.unprocessed_freq_GHz = data_dict["freq_ghz"]
        self.unprocessed_freq_Hz = self.unprocessed_freq_GHz * 1.0e9
        self.unprocessed_reals21, self.unprocessed_imags21 = data_dict["real"],  data_dict["imag"]
        self.unprocessed_mags21, self.unprocessed_phases21 = ri_to_magphase(r=self.unprocessed_reals21,
                                                                            i=self.unprocessed_imags21)

    def savgol_filter_mag(self, reals21=None, imags21=None, window_length=31, polyorder=2, plot=False):
        self.filter_reset()
        mag, phase = ri_to_magphase(r=reals21, i=imags21)
        if window_length % 2 == 0:
            # window length needs to be an odd int
            window_length += 1
        self.filter_update_mag(mag=mag, phase=phase,
                               lowpass_filter_mags21=savgol_filter(x=mag, window_length=window_length, polyorder=polyorder),
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
                                          tau=(self.unprocessed_freq_GHz[1] - self.unprocessed_freq_GHz[0]) * 1.0e9,
                                          f_3db=1.0 / smoothing_scale,
                                          width=0.1 * (1.0 / smoothing_scale),
                                          padd_data=True)
        # this filter needs odd lengths of data
        mag = mag[:len(self.lowpass_filter_mags21)]
        phase = phase[:len(self.lowpass_filter_mags21)]
        self.unprocessed_freq_GHz = self.unprocessed_freq_GHz[:len(self.lowpass_filter_mags21)]
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
        plot_filter(freqs_GHz=self.unprocessed_freq_GHz,
                    original_s21=self.unprocessed_reals21 + 1j * self.unprocessed_imags21,
                    lowpass_s21=self.lowpass_filter_reals21 + 1j * self.lowpass_filter_imags21,
                    highpass_s21=self.highpass_filter_reals21 + 1j * self.highpass_filter_imags21)

    def find_window(self, cosine_filter=False, window_pad_factor=3, fitter_pad_factor=5, show_filter_plots=False,
                    debug_mode=False):
        # initial filtering in magnitude space
        f_step_GHz = self.unprocessed_freq_GHz[1] - self.unprocessed_freq_GHz[0]
        window_length = int(np.round(rpc.baseline_smoothing_window_GHz / f_step_GHz))
        if cosine_filter:
            mag, phase = self.cosine_filter_mag(reals21=self.unprocessed_reals21, imags21=self.unprocessed_imags21,
                                                smoothing_scale=rpc.baseline_smoothing_window_GHz * 1.0e9,
                                                plot=show_filter_plots)
        else:
            mag, phase = self.savgol_filter_mag(reals21=self.unprocessed_reals21, imags21=self.unprocessed_imags21,
                                                window_length=window_length, polyorder=2, plot=show_filter_plots)
        # interaction threshold plotting, return local minima and window information about size of the resonators
        i_thresh = fr_interactive.InteractiveThresholdPlot(f_Hz=self.unprocessed_freq_GHz * 1.0e9,
                                                           s21_mag=self.highpass_filter_mags21,
                                                           peak_threshold_dB=0.5,
                                                           spacing_threshold_Hz=rpc.resonator_spacing_threshold_Hz,
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
        synthetic_baseline = f(range(len(self.unprocessed_freq_GHz)))
        self.filter_update_mag(mag=mag, phase=phase,
                               lowpass_filter_mags21=synthetic_baseline,
                               plot=show_filter_plots)

        self.not_smoothed_mag = copy.copy(self.highpass_filter_mags21)
        self.synthetic_baseline_smoothed = savgol_filter(x=synthetic_baseline,
                                                         window_length=window_length + 1, polyorder=3)
        self.filter_update_mag(mag=mag, phase=phase,
                               lowpass_filter_mags21=self.synthetic_baseline_smoothed,
                               plot=show_filter_plots)
        self.highpass_phase = phase
        self.highpass_linear_mag = np.sqrt((self.highpass_filter_reals21 ** 2.0) + (self.highpass_filter_imags21 ** 2.0))

        self.minima_as_windows = i_thresh.minima_as_windows

    def analyze_resonators(self):
        self.fitted_resonators_parameters = []
        for single_window in self.minima_as_windows:
            # get slices of data ready
            fitter_slice = slice(single_window.left_fitter_pad, single_window.right_fitter_pad)
            left_baseline_slice = slice(single_window.left_fitter_pad, single_window.left_window)
            right_baseline_slice = slice(single_window.right_window, single_window.right_fitter_pad)
            f_GHz_single_res = self.unprocessed_freq_GHz[fitter_slice]
            f_Hz_single_res = self.unprocessed_freq_Hz[fitter_slice]
            s21_mag_single_res = self.unprocessed_mags21[fitter_slice]
            s21_phase_single_res = self.highpass_phase[fitter_slice]
            s21_mag_single_res_highpass = self.highpass_filter_mags21[fitter_slice]
            s21_mag_single_res_highpass_linear = self.highpass_linear_mag[fitter_slice]
            s21_real_single_res_highpass = self.highpass_filter_reals21[fitter_slice]
            s21_imag_single_res_highpass = self.highpass_filter_imags21[fitter_slice]
            s21_complex_single_res_highpass = s21_real_single_res_highpass + 1j * s21_imag_single_res_highpass
            minima_mag_single_res_highpass_linear = self.highpass_linear_mag[single_window.minima]
            minima_mag_single_res_highpass = self.highpass_filter_mags21[single_window.minima]
            # Guess the initial fit parameters


            fcenter_guess_GHz = self.unprocessed_freq_GHz[single_window.minima]
            fcenter_guess_Hz = self.unprocessed_freq_Hz[single_window.minima]
            base_amplitude_abs_guess = 1.0  # This the expected value for a highpass in magnitude space
            # a_phase_rad_guess = np.mean(np.concatenate((phase[left_baseline_slice], phase[right_baseline_slice])))
            a_phase_rad_guess = np.mean(self.highpass_phase[fitter_slice])

            # find the fullwidth half maximum
            goal_depth = halfway_in_log_mag  # basically 3 dB down from the baseline
            f_fwhm_left_Hz = fwhm(goal_depth, f_Hz_single_res, s21_mag_single_res_highpass)
            f_fwhm_right_Hz = fwhm(goal_depth, reversed(f_Hz_single_res), reversed(s21_mag_single_res_highpass))

            # Quality factors
            Q_guess_Hz = f_fwhm_right_Hz - f_fwhm_left_Hz
            Q_guess = fcenter_guess_Hz / Q_guess_Hz
            Qi_guess = Q_guess * np.sqrt(0 - minima_mag_single_res_highpass)
            Qc_guess = Qi_guess * Q_guess / (Qi_guess - Q_guess)

            # tau_ns
            delta_freq_GHz = f_GHz_single_res[-1] - f_GHz_single_res[0]
            group_delay_slope, group_delay_offset = \
                np.polyfit(f_Hz_single_res * 2.0 * np.pi, np.unwrap(s21_phase_single_res, discont=np.pi), deg=1)
            tau_ns_guess = group_delay_slope * 1.0e9 / (2.0 * np.pi)

            # base amplitude slope
            base_amplitude_slope_guess = (np.mean(self.highpass_linear_mag[single_window.left_fitter_pad])
                            - np.mean(self.highpass_linear_mag[single_window.right_fitter_pad])) \
                                         / (delta_freq_GHz * 2.0 * np.pi)
            params_guess = ResParams(base_amplitude_abs=base_amplitude_abs_guess, a_phase_rad=a_phase_rad_guess,
                                     base_amplitude_slope=base_amplitude_slope_guess, tau_ns=tau_ns_guess,
                                     f0=fcenter_guess_GHz, Qi=Qi_guess, Qc=Qc_guess, Zratio=0)

            popt, pcov = wrap_simple_res_gain_slope_complex(freqs_GHz=f_GHz_single_res,
                                                            s21_complex=s21_complex_single_res_highpass,
                                                            s21_linear_mag=s21_mag_single_res_highpass_linear,
                                                            base_amplitude_abs_guess=params_guess.base_amplitude_abs,
                                                            a_phase_rad_guess=params_guess.a_phase_rad,
                                                            f0_guess=params_guess.f0,
                                                            Qi_guess=params_guess.Qi,
                                                            Qc_guess=params_guess.Qc,
                                                            base_amplitude_slope_guess=params_guess.base_amplitude_slope,
                                                            tau_ns_guess=params_guess.tau_ns,
                                                            Zratio_guess=params_guess.Zratio)
            params_fit = package_res_results(popt=popt, pcov=pcov, verbose=self.verbose)
            self.fitted_resonators_parameters.append(params_fit)

            plot_res_fit(f_GHz_single_res=f_GHz_single_res,
                         s21_mag_single_res=s21_mag_single_res,
                         not_smoothed_mag_single_res=self.not_smoothed_mag[fitter_slice],
                         s21_mag_single_res_highpass=s21_mag_single_res_highpass,
                         params_guess=params_guess, params_fit=params_fit,
                         minima_pair=(self.unprocessed_freq_GHz[single_window.minima],
                                      self.highpass_filter_mags21[single_window.minima]),
                         fwhm_pair=((f_fwhm_left_Hz * 1.0e-9, f_fwhm_right_Hz * 1.0e-9), (goal_depth, goal_depth)),
                         window_pair=((self.unprocessed_freq_GHz[single_window.left_window],
                                       self.unprocessed_freq_GHz[single_window.right_window]),
                                      (self.highpass_filter_mags21[single_window.left_window],
                                       self.highpass_filter_mags21[single_window.right_window])),
                         fitter_pair=((self.unprocessed_freq_GHz[single_window.left_pad],
                                       self.unprocessed_freq_GHz[single_window.right_pad]),
                                      (self.highpass_filter_mags21[single_window.left_pad],
                                       self.highpass_filter_mags21[single_window.right_pad])),
                         output_filename=None)

    def fit_resonators_jake(self):
        frs = jake_res_finder(unprocessed_freq_GHz=self.unprocessed_freq_GHz,
                              unprocessed_reals21=self.unprocessed_reals21,
                              unprocessed_imags21=self.unprocessed_reals21,
                              edge_search_depth=50,
                              smoothing_scale_kHz=25,
                              smoothing_order=5,
                              cutoff_rate=500,
                              minimum_spacing_kHz=100.0,
                              remove_baseline_ripple=True,
                              baseline_scale_kHz=3000,
                              baseline_order=3,
                              verbose=self.verbose)
        return frs
