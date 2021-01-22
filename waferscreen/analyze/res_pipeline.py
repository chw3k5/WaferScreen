import numpy as np
import matplotlib.pyplot as plt
from typing import NamedTuple, Optional
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
from waferscreen.analyze.s21_io import read_s21, write_s21, ri_to_magphase, magphase_to_realimag
from waferscreen.plot.s21_plots import plot_filter
from waferscreen.res.single_fits import fit_simple_res_gain_slope_complex
import waferscreen.analyze.res_pipeline_config as rpc
from submm_python_routines.KIDs import find_resonances_interactive as fr_interactive
import copy


def rebound_starting_vals(bounds, starting_vals):
    # takes starting guess for resonator and makes sure it's within bounds
    new_starting_vals = []
    for i in range(0, len(starting_vals)):
        if (starting_vals[i] > bounds[0][i]) and (starting_vals[i] < bounds[1][i]):
            new_starting_vals.append(starting_vals[i])
        elif starting_vals[i] <= bounds[0][i]:
            new_starting_vals.append(bounds[0][i])
        elif starting_vals[i] >= bounds[1][i]:
            new_starting_vals.append(bounds[1][i])
    # new_starting_vals = np.array(new_starting_vals)
    return new_starting_vals


def package_res_results(popt, pcov, verbose=False):
    fit_base_amplitude_abs = popt[0]
    fit_a_phase_rad = popt[1]
    fit_base_amplitude_slope = popt[2]
    fit_tau_ns = popt[3]
    fit_f0 = popt[4]
    fit_Qi = popt[5]
    fit_Qc = popt[6]
    fit_Zratio = popt[7]

    error_base_amplitude_abs = np.sqrt(pcov[0, 0])
    error_a_phase_rad = np.sqrt(pcov[1, 1])
    error_base_amplitude_slope = np.sqrt(pcov[2, 2])
    error_tau_ns = np.sqrt(pcov[3, 3])
    error_f0 = np.sqrt(pcov[4, 4])
    error_Qi = np.sqrt(pcov[5, 5])
    error_Qc = np.sqrt(pcov[6, 6])
    error_Zratio = np.sqrt(pcov[7, 7])

    if verbose:
        print('Fit Result')
        print('base_amplitude_abs   : %.4f +/- %.6f' % (fit_base_amplitude_abs, error_base_amplitude_abs))
        print('a_phase_rad          : %.2f +/- %.4f Deg' % (fit_a_phase_rad, error_a_phase_rad))
        print('base_amplitude_slope : %.3f +/- %.3f /GHz' % (fit_base_amplitude_slope, error_base_amplitude_slope))
        print('tau_ns               : %.3f +/- %.3f ns' % (fit_tau_ns, error_tau_ns))
        print('fcenter              : %.6f +/- %.8f GHz' % (fit_f0, error_f0))
        print('Qi            : %.0f +/- %.0f' % (fit_Qi, error_Qi))
        print('Qc            : %.0f +/- %.0f' % (fit_Qc, error_Qc))
        print('Im(Z0)/Re(Z0) : %.2f +/- %.3f' % (fit_Zratio, error_Zratio))
        print('')

    single_res_params = ResParams(base_amplitude_abs=fit_base_amplitude_abs,
                                  base_amplitude_abs_error=error_base_amplitude_abs,
                                  a_phase_rad=fit_a_phase_rad, a_phase_rad_error=error_a_phase_rad,
                                  base_amplitude_slope=fit_base_amplitude_slope, 
                                  base_amplitude_slope_error=error_base_amplitude_slope,
                                  tau_ns=fit_tau_ns, tau_ns_error=error_tau_ns,
                                  f0=fit_f0, f0_error=error_f0,
                                  Qi=fit_Qi, Qi_error=error_Qi,
                                  Qc=fit_Qc, Qc_error=error_Qc,
                                  Zratio=fit_Zratio, Zratio_error=error_Zratio)
    return single_res_params


def wrap_simple_res_gain_slope_complex(freqs_GHz, s21_complex, s21_linear_mag,
                                       base_amplitude_abs_guess, a_phase_rad_guess, f0_guess, Qi_guess, Qc_guess,
                                       base_amplitude_slope_guess, tau_ns_guess,
                                       Zratio_guess):

    error_ravel = np.array([[a_s21_linear_mag, a_s21_linear_mag] for a_s21_linear_mag in s21_linear_mag]).ravel()
    s21data_ravel = np.array([[s21.real, s21.imag] for s21 in s21_complex]).ravel()
    starting_vals = [base_amplitude_abs_guess, a_phase_rad_guess, base_amplitude_slope_guess, tau_ns_guess,
                     f0_guess, Qi_guess, Qc_guess, Zratio_guess]
    bounds = ((0, -np.pi, -1000, 0, freqs_GHz.min(), 0, 0, -5.0),
              (np.inf, np.pi, 1000, 100, freqs_GHz.max(), np.inf, np.inf, 5.0))
    starting_vals = rebound_starting_vals(bounds, starting_vals)
    popt, pcov = curve_fit(f=fit_simple_res_gain_slope_complex, xdata=freqs_GHz, ydata=s21data_ravel, p0=starting_vals,
                           sigma=error_ravel, bounds=bounds)
    return popt, pcov


def read_res_params(path):
    # open resonant frequencies file
    with open(path, 'r') as f:
        lines = f.readlines()
    header = lines[0].strip().split(",")
    res_params = []
    for line in lines[1:]:
        datavec = line.split(",")
        res_params.append(ResParams(**{column_name: float(value) for column_name, value in zip(header, datavec)}))
    return res_params


primary_res_params = ["base_amplitude_abs", "a_phase_rad", "base_amplitude_slope", "tau_ns", "f0", "Qi", "Qc", "Zratio"]
res_params_header = ""
for param_type in primary_res_params:
    res_params_header += param_type + "," + param_type + "_error,"
res_params_header = res_params_header[:-1]


def fwhm(goal_depth, f_Hz_single_res, s21_mag_single_res_highpass_linear):
    for single_f_Hz, single_linear_mag in zip(f_Hz_single_res, s21_mag_single_res_highpass_linear):
        if single_linear_mag < goal_depth:
            f_fwhm_Hz_now = single_f_Hz
            f_fwhm_mag_now = single_linear_mag
            break
        else:
            f_fwhm_Hz_last = single_f_Hz
            f_fwhm_mag_last = single_linear_mag

    slope = (f_fwhm_Hz_now - f_fwhm_Hz_last) / (f_fwhm_mag_now - f_fwhm_mag_last)
    f_fwhm_Hz = ((goal_depth - f_fwhm_mag_last) * slope) + f_fwhm_Hz_last
    return f_fwhm_Hz


class ResParams(NamedTuple):
    base_amplitude_abs: float
    a_phase_rad: float
    base_amplitude_slope: float
    tau_ns: float
    f0: float
    Qi: float
    Qc: float
    Zratio: float
    base_amplitude_abs_error: Optional[float] = None
    a_phase_rad_error: Optional[float] = None
    base_amplitude_slope_error: Optional[float] = None
    tau_ns_error: Optional[float] = None
    f0_error: Optional[float] = None
    Qi_error: Optional[float] = None
    Qc_error: Optional[float] = None
    Zratio_error: Optional[float] = None

    def __str__(self):
        output_string = ""
        for attr in primary_res_params:
            error_value = str(self.__getattribute__(attr + "_error"))
            if error_value is None:
                error_str = ""
            else:
                error_str = str(error_value)
            output_string += str(self.__getattribute__(attr)) + "," + error_str + ","
        return output_string[:-1]


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
        self.found_res = None

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

    def baseline_subtraction(self, cosine_filter=False, window_pad_factor=3, fitter_pad_factor=5,
                             show_filter_plots=False):
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
                                                           debug_mode=True)
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
        not_smoothed_mag = copy.copy(self.highpass_filter_mags21)
        synthetic_baseline_smoothed = savgol_filter(x=synthetic_baseline,
                                                    window_length=window_length + 1, polyorder=3)
        self.filter_update_mag(mag=mag, phase=phase,
                               lowpass_filter_mags21=synthetic_baseline_smoothed,
                               plot=show_filter_plots)
        highpass_linear_mag = np.sqrt((self.highpass_filter_reals21 ** 2.0) + (self.highpass_filter_imags21 ** 2.0))

        self.found_res = []
        for single_window in i_thresh.minima_as_windows:
            # get slices of data ready
            fitter_slice = slice(single_window.left_fitter_pad, single_window.right_fitter_pad)
            left_baseline_slice = slice(single_window.left_fitter_pad, single_window.left_window)
            right_baseline_slice = slice(single_window.right_window, single_window.right_fitter_pad)
            f_GHz_single_res = self.unprocessed_freq_GHz[fitter_slice]
            f_Hz_single_res = self.unprocessed_freq_Hz[fitter_slice]
            s21_mag_single_res = self.unprocessed_mags21[fitter_slice]
            s21_phase_single_res = phase[fitter_slice]
            s21_mag_single_res_highpass = self.highpass_filter_mags21[fitter_slice]
            s21_mag_single_res_highpass_linear = highpass_linear_mag[fitter_slice]
            s21_real_single_res_highpass = self.highpass_filter_reals21[fitter_slice]
            s21_imag_single_res_highpass = self.highpass_filter_imags21[fitter_slice]
            s21_complex_single_res_highpass = s21_real_single_res_highpass + 1j * s21_imag_single_res_highpass
            minima_mag_single_res_highpass_linear = highpass_linear_mag[single_window.minima]
            minima_mag_single_res_highpass = self.highpass_filter_mags21[single_window.minima]
            # Guess the initial fit parameters


            fcenter_guess_GHz = self.unprocessed_freq_GHz[single_window.minima]
            fcenter_guess_Hz = self.unprocessed_freq_Hz[single_window.minima]
            base_amplitude_abs_guess = 1.0  # This the expected value for a highpass in magnitude space
            # a_phase_rad_guess = np.mean(np.concatenate((phase[left_baseline_slice], phase[right_baseline_slice])))
            a_phase_rad_guess = np.mean(phase[fitter_slice])

            # find the fullwidth half maximum
            # goal_depth = self.highpass_filter_mags21[single_window.minima] + 10.0 * np.log10(2.0)
            # goal_depth = (self.highpass_filter_mags21[single_window.minima]) * 0.5
            goal_depth = 10.0 * np.log10(0.5)
            f_fwhm_left_Hz = fwhm(goal_depth, f_Hz_single_res, s21_mag_single_res_highpass)
            f_fwhm_right_Hz = fwhm(goal_depth, reversed(f_Hz_single_res), reversed(s21_mag_single_res_highpass))

            # Quality factors
            Q_guess_Hz = f_fwhm_right_Hz - f_fwhm_left_Hz
            Q_guess = fcenter_guess_Hz / Q_guess_Hz


            # Qt_left = 1.0 / (1 - (f_fwhm_left_Hz / fcenter_guess_Hz) ** 2.0)
            # Qt_right = -1.0 / (1 - (f_fwhm_right_Hz / fcenter_guess_Hz) ** 2.0)
            # Qt = 0.5 * (Qt_left + Qt_right)

            Qi_guess = Q_guess * np.sqrt(0 - minima_mag_single_res_highpass)
            Qc_guess = Qi_guess * Q_guess / (Qi_guess - Q_guess)

            Qi_guess2 = 227000.
            Qc_guess2 = 46000.

            Q_guess2  = Qi_guess2 * Qc_guess2 / (Qi_guess2 + Qc_guess2)

            LOSTROOT = (Q_guess2/Qi_guess) ** 2.0

            # tau_ns
            delta_freq_GHz = f_GHz_single_res[-1] - f_GHz_single_res[0]

            # group_delay_slope, group_delay_offset = \
            #     np.polyfit(f_Hz_single_res * 2.0 * np.pi, np.unwrap(s21_phase_single_res, discont=np.pi), deg=1)
            # tau_ns_guess = group_delay_slope * 1.0e9

            tau_ns_guess = Q_guess / (np.pi * fcenter_guess_GHz)









            

            base_amplitude_slope_guess = (np.mean(highpass_linear_mag[single_window.left_fitter_pad])
                            - np.mean(highpass_linear_mag[single_window.right_fitter_pad])) \
                                         / (delta_freq_GHz * 2.0 * np.pi)
            params_guess = ResParams(base_amplitude_abs=base_amplitude_abs_guess, a_phase_rad=a_phase_rad_guess,
                                     base_amplitude_slope=base_amplitude_slope_guess, tau_ns=tau_ns_guess,
                                     f0=fcenter_guess_GHz, Qi=Qi_guess, Qc=Qc_guess, Zratio=0)
            Params_guess = params_guess


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
            Params_fit = params_fit


            QDIFF = Q_guess2 - Q_guess
            leglines = []
            leglabels = []

            # unprocessed
            unprocessed_color = "black"
            unprocessed_linewidth = 5
            plt.plot(f_GHz_single_res, s21_mag_single_res - s21_mag_single_res[0], color="black",
                     linewidth=unprocessed_linewidth)
            leglines.append(plt.Line2D(range(10), range(10), color=unprocessed_color, ls="-",
                                       linewidth=unprocessed_linewidth))
            leglabels.append(F"unprocessed")

            # window baseline substraction
            window_bl_color = "dodgerblue"
            window_bl_linewidth = 4
            plt.plot(f_GHz_single_res, not_smoothed_mag[fitter_slice], color=window_bl_color,
                     linewidth=window_bl_linewidth)
            leglines.append(plt.Line2D(range(10), range(10), color=window_bl_color, ls="-",
                                       linewidth=window_bl_linewidth))
            leglabels.append(F"Highpass Window")

            # window baseline substraction and smooth
            window_bl_smooth_color = "chartreuse"
            window_bl_smooth_linewidth = 3
            plt.plot(f_GHz_single_res, s21_mag_single_res_highpass, color=window_bl_smooth_color,
                     linewidth=window_bl_smooth_linewidth)
            leglines.append(plt.Line2D(range(10), range(10), color=window_bl_smooth_color, ls="-",
                                       linewidth=window_bl_smooth_linewidth))
            leglabels.append(F"Highpass Window Smoothed")


            # guess mag phase
            guess_fit_out = fit_simple_res_gain_slope_complex(f_GHz_single_res, params_guess.base_amplitude_abs,
                                                              params_guess.a_phase_rad, params_guess.base_amplitude_slope,
                                                              params_guess.tau_ns, params_guess.f0,
                                                              params_guess.Qi, params_guess.Qc, params_guess.Zratio)
            guess_complex = np.array([guess_fit_out[2 * n] + 1j * guess_fit_out[(2 * n) + 1]
                                     for n in range(len(f_GHz_single_res))])
            guess_mag, guess_phase = ri_to_magphase(r=guess_complex.real, i=guess_complex.imag)
            guess_mag_color = "firebrick"
            guess_mag_linewidth = 2
            plt.plot(f_GHz_single_res, guess_mag, color=guess_mag_color,
                     linewidth=guess_mag_linewidth)
            leglines.append(plt.Line2D(range(10), range(10), color=guess_mag_color, ls="-",
                                       linewidth=guess_mag_linewidth))
            leglabels.append(F"Initial Fit")

            # guess mag phase
            final_fit_out = fit_simple_res_gain_slope_complex(f_GHz_single_res, params_fit.base_amplitude_abs,
                                                              params_fit.a_phase_rad, params_fit.base_amplitude_slope,
                                                              params_fit.tau_ns, params_fit.f0,
                                                              params_fit.Qi, params_fit.Qc, params_fit.Zratio)
            final_complex = np.array([final_fit_out[2 * n] + 1j * final_fit_out[(2 * n) + 1]
                                     for n in range(len(f_GHz_single_res))])
            final_mag, final_phase = ri_to_magphase(r=final_complex.real, i=final_complex.imag)
            final_mag_color = "black"
            final_mag_linewidth = 5
            final_mag_ls = 'dotted'
            plt.plot(f_GHz_single_res, final_mag, color=final_mag_color,
                     linewidth=final_mag_linewidth, ls=final_mag_ls)
            leglines.append(plt.Line2D(range(10), range(10), color=final_mag_color, ls=final_mag_ls,
                                       linewidth=final_mag_linewidth))
            leglabels.append(F"Final Fit")

            # Zero Line for reference
            zero_line_color = "darkgoldenrod"
            zero_line_smooth_linewidth = 1
            zero_line_ls = "dashed"
            plt.plot((f_GHz_single_res[0], f_GHz_single_res[-1]), (0, 0), color=zero_line_color,
                     linewidth=zero_line_smooth_linewidth, ls=zero_line_ls)
            leglines.append(plt.Line2D(range(10), range(10), color=zero_line_color, ls=zero_line_ls,
                                       linewidth=zero_line_smooth_linewidth))
            leglabels.append(F"Zero dB line")

            # show minima
            window_bound_color = "darkorchid"
            window_bound_linewidth = 1
            window_bound_ls = "None"
            window_bound_alpha = 0.65
            window_bound_marker = 'o'
            window_bound_markersize = 10
            plt.plot(self.unprocessed_freq_GHz[single_window.minima],
                     self.highpass_filter_mags21[single_window.minima],
                     color=window_bound_color,
                     linewidth=window_bound_linewidth, ls=window_bound_ls, marker=window_bound_marker,
                     markersize=window_bound_markersize,
                     markerfacecolor=window_bound_color, alpha=window_bound_alpha)
            leglines.append(plt.Line2D(range(10), range(10), color=window_bound_color, ls=window_bound_ls,
                                       linewidth=window_bound_linewidth, marker=window_bound_marker,
                                       markersize=window_bound_markersize,
                                       markerfacecolor=window_bound_color, alpha=window_bound_alpha))
            leglabels.append(F"Found Minima")

            # show the calculated FWHM
            fwhm_color = "forestgreen"
            fwhm_linewidth = 1
            fwhm_ls = "None"
            fwhm_alpha = 0.8
            fwhm_marker = 'D'
            fwhm_markersize = 10
            plt.plot((f_fwhm_left_Hz * 1.0e-9, f_fwhm_right_Hz * 1.0e-9),
                     (goal_depth, goal_depth),
                     color=fwhm_color,
                     linewidth=fwhm_linewidth, ls=fwhm_ls, marker=fwhm_marker,
                     markersize=fwhm_markersize,
                     markerfacecolor=fwhm_color, alpha=fwhm_alpha)
            leglines.append(plt.Line2D(range(10), range(10), color=fwhm_color, ls=fwhm_ls,
                                       linewidth=fwhm_linewidth, marker=fwhm_marker,
                                       markersize=fwhm_markersize,
                                       markerfacecolor=fwhm_color, alpha=fwhm_alpha))
            leglabels.append(F"FWHM")

            # show the calculated window boundries
            window_bound_color = "firebrick"
            window_bound_linewidth = 1
            window_bound_ls = "None"
            window_bound_alpha = 0.8
            window_bound_marker = '*'
            window_bound_markersize = 10
            plt.plot((self.unprocessed_freq_GHz[single_window.left_window],
                      self.unprocessed_freq_GHz[single_window.right_window]),
                     (self.highpass_filter_mags21[single_window.left_window],
                      self.highpass_filter_mags21[single_window.right_window]),
                     color=window_bound_color,
                     linewidth=window_bound_linewidth, ls=window_bound_ls, marker=window_bound_marker,
                     markersize=window_bound_markersize,
                     markerfacecolor=window_bound_color, alpha=window_bound_alpha)
            leglines.append(plt.Line2D(range(10), range(10), color=window_bound_color, ls=window_bound_ls,
                                       linewidth=window_bound_linewidth, marker=window_bound_marker,
                                       markersize=window_bound_markersize,
                                       markerfacecolor=window_bound_color, alpha=window_bound_alpha))
            leglabels.append(F"Window from Threshold")

            # show the calculated window boundries
            window_bound_color = "Navy"
            window_bound_linewidth = 1
            window_bound_ls = "None"
            window_bound_alpha = 1.0
            window_bound_marker = 'x'
            window_bound_markersize = 10
            plt.plot((self.unprocessed_freq_GHz[single_window.left_pad],
                      self.unprocessed_freq_GHz[single_window.right_pad]),
                     (self.highpass_filter_mags21[single_window.left_pad],
                      self.highpass_filter_mags21[single_window.right_pad]),
                     color=window_bound_color,
                     linewidth=window_bound_linewidth, ls=window_bound_ls, marker=window_bound_marker,
                     markersize=window_bound_markersize,
                     markerfacecolor=window_bound_color, alpha=window_bound_alpha)
            leglines.append(plt.Line2D(range(10), range(10), color=window_bound_color, ls=window_bound_ls,
                                       linewidth=window_bound_linewidth, marker=window_bound_marker,
                                       markersize=window_bound_markersize,
                                       markerfacecolor=window_bound_color, alpha=window_bound_alpha))
            leglabels.append(F"Baseline Bounds")

            plt.xlabel(F"Frequency (GHz)")
            plt.ylabel(F"dB")
            plt.legend(leglines,
                       leglabels, loc=0,
                       numpoints=3, handlelength=5,
                       fontsize=8)
            plt.show()
            self.found_res.append("")


    def fit_resonators(self, model, f_GHz_single_res, s21_complex_single_res, error_est, guess_res_params):
        g = guess_res_params







    def jake_res_finder(self, edge_search_depth=50,
                              smoothing_scale_kHz=25,
                              smoothing_order=5,
                              cutoff_rate=500,
                              minimum_spacing_kHz=100.0,
                              remove_baseline_ripple=True,
                              baseline_scale_kHz=3000,
                              baseline_order=3):
        freq_GHz = self.unprocessed_freq_GHz
        s21_complex = self.unprocessed_reals21 + 1j * self.unprocessed_imags21
        # figure out complex gain and gain slope
        ave_left_gain = 0
        ave_right_gain = 0
        for j in range(0, edge_search_depth):
            ave_left_gain = ave_left_gain + s21_complex[j] / edge_search_depth
            ave_right_gain = ave_right_gain + s21_complex[len(s21_complex) - 1 - j] / edge_search_depth
        left_freq = freq_GHz[int(edge_search_depth / 2.0)]
        right_freq = freq_GHz[len(freq_GHz) - 1 - int(edge_search_depth / 2.0)]
        gain_slope = (ave_right_gain - ave_left_gain) / (right_freq - left_freq)
        if self.verbose:
            # calculate extra group delay and abs gain slope removed for printing out purposes
            left_phase = np.arctan2(np.imag(ave_left_gain), np.real(ave_left_gain))
            right_phase = np.arctan2(np.imag(ave_right_gain), np.real(ave_right_gain))
            excess_tau_ns = (left_phase - right_phase) / (2.0 * np.pi * (right_freq - left_freq))
            abs_gain = np.absolute(0.5 * ave_right_gain + 0.5 * ave_left_gain)
            abs_gain_slope = (np.absolute(ave_right_gain) - np.absolute(ave_left_gain)) / (right_freq - left_freq)
            print("Removing an excess group delay of " + str(excess_tau_ns) + "ns from data")
            print("Removing a gain of " + str(abs_gain) + " and slope of " + str(abs_gain_slope) + "/GHz from data")
        gains = ave_left_gain + (freq_GHz - left_freq) * gain_slope
        s21_complex = s21_complex / gains



        # remove baseline ripple if desired
        if remove_baseline_ripple:
            freq_spacing = (freq_GHz[1] - freq_GHz[0]) * 1.0e6  # GHz -> kHz
            baseline_scale = int(round(baseline_scale_kHz / freq_spacing))
            if baseline_scale % 2 == 0:  # if even
                baseline_scale = baseline_scale + 1  # make it odd
            # smooth s21 trace in both real and imaginary to do peak finding
            baseline_real = savgol_filter(np.real(s21_complex), baseline_scale, baseline_order)
            baseline_imag = savgol_filter(np.imag(s21_complex), baseline_scale, baseline_order)
            baseline = np.array(baseline_real + 1j * baseline_imag)
            pre_baseline_removal_s21_complex = np.copy(s21_complex)
            s21_complex = s21_complex / baseline

        # figure out freq spacing, convert smoothing_scale_kHz to smoothing_scale (must be an odd number)
        freq_spacing = (freq_GHz[1] - freq_GHz[0]) * 1e6  # GHz -> kHz
        smoothing_scale = int(round(smoothing_scale_kHz / freq_spacing))
        if smoothing_scale % 2 == 0:  # if even
            smoothing_scale = smoothing_scale + 1  # make it odd
        if smoothing_scale >= smoothing_order:
            smoothing_order = smoothing_scale - 1
        if smoothing_scale <= smoothing_order:
            print(F"For smoothing scale of {smoothing_scale_kHz}kHz is too find, soothing skipped.")
            s21_complex_smooth = s21_complex
        else:
            # smooth s21 trace in both real and imaginary to do peak finding
            s21_complex_smooth_real = savgol_filter(np.real(s21_complex), smoothing_scale, smoothing_order)
            s21_complex_smooth_imag = savgol_filter(np.imag(s21_complex), smoothing_scale, smoothing_order)
            s21_complex_smooth = np.array(s21_complex_smooth_real + 1j * s21_complex_smooth_imag)

        # take derivative of data (optional) and smoothed data
        first_deriv_smooth = []
        first_deriv_freq_GHz = []
        for j in range(0, len(s21_complex_smooth) - 1):
            if freq_GHz[j + 1] - freq_GHz[j] < 1e-7:
                print(freq_GHz[j])
                print(freq_GHz[j + 1])
            first_deriv_smooth.append(
                (s21_complex_smooth[j + 1] - s21_complex_smooth[j]) / (freq_GHz[j + 1] - freq_GHz[j]))
            first_deriv_freq_GHz.append((freq_GHz[j + 1] + freq_GHz[j]) / 2.0)
        first_deriv_smooth = np.array(first_deriv_smooth)
        first_deriv_freq_GHz = np.array(first_deriv_freq_GHz)


        # rotate first deriv into r-hat vs. theta-hat coordinates using original position of s21
        first_deriv_rot_smooth = []
        for j in range(0, len(first_deriv_smooth)):
            s21_complex_pt_smooth = (s21_complex_smooth[j] + s21_complex_smooth[j + 1]) / 2.0
            theta_smooth = np.arctan2(np.imag(s21_complex_pt_smooth), np.real(s21_complex_pt_smooth))
            first_deriv_rot_smooth.append([(np.real(first_deriv_smooth[j]) * np.cos(theta_smooth) + np.imag(
                first_deriv_smooth[j]) * np.sin(theta_smooth)), (-1.0 * np.real(first_deriv_smooth[j]) * np.sin(
                theta_smooth) + np.imag(first_deriv_smooth[j]) * np.cos(theta_smooth))])
        first_deriv_rot_smooth = np.array(first_deriv_rot_smooth)


        # use smoothed rotated first derivatives to find resonances
        frs = []
        Qts = []
        # figure out spacing between freq_GHz
        delta_f = first_deriv_freq_GHz[1] - first_deriv_freq_GHz[0]
        float_samples = minimum_spacing_kHz / (delta_f * 1e6)
        n_samples = int(np.floor(float_samples) + 1)  # only need to look this far around a given point above cutoff


        for j in range(len(first_deriv_rot_smooth)):
            if first_deriv_rot_smooth[j, 1] * (first_deriv_freq_GHz[j] / 2.0) > cutoff_rate:
                another_higher = False
                k = max(0, j - n_samples)  # start looking at k = j - n_samples
                while not another_higher and k < len(first_deriv_rot_smooth) and k < j + n_samples + 1:
                    if abs(first_deriv_freq_GHz[j] - first_deriv_freq_GHz[k]) < minimum_spacing_kHz * 1e-6 and j != k:
                        # freq is within range
                        if first_deriv_rot_smooth[k, 1] * (first_deriv_freq_GHz[k] / 2.0) > first_deriv_rot_smooth[
                            j, 1] * (
                                first_deriv_freq_GHz[j] / 2.0):  # found one with larger derivative
                            another_higher = True
                    # increment k, check if next point is higher
                    k = k + 1
                if not another_higher:  # confirmed, this is the highest point within +/- minimum spacing
                    frs.append(first_deriv_freq_GHz[j])
                    Qts.append(first_deriv_rot_smooth[j, 1] * (first_deriv_freq_GHz[j] / 2.0))
        frs = np.array(frs)
        if self.verbose:
            print("Found " + str(len(frs)) + " Resonators")
        return frs