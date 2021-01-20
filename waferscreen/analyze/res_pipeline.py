import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from scipy.interpolate import interp1d
from waferscreen.analyze.s21_io import read_s21, write_s21, ri_to_magphase, magphase_to_realimag
from waferscreen.plot.s21_plots import plot_filter
import waferscreen.analyze.res_pipeline_config as rpc
from waferscreen.analyze.mariscotti import mariscotti
from submm_python_routines.KIDs import find_resonances_interactive as fr_interactive


class ResPipe:
    def __init__(self, s21_path, verbose=True):
        self.path = s21_path
        self.verbose = True
        self.meta_data = None
        self.unprocessed_freq_GHz, self.unprocessed_reals21, self.unprocessed_imags21 = None, None, None
        self.lowpass_filter_reals21, self.lowpass_filter_imags21 = None, None
        self.highpass_filter_reals21, self.highpass_filter_imags21 = None, None
        self.highpass_filter_mags21, self.lowpass_filter_mags21 = None, None

    def read(self):
        data_dict, self.meta_data = read_s21(path=self.path)
        self.unprocessed_freq_GHz = data_dict["freq_ghz"]
        self.unprocessed_reals21, self.unprocessed_imags21 = data_dict["real"],  data_dict["imag"]

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

    def baseline_subtraction(self, cosine_filter=False, window_padding=3):
        # initial filtering in magnitude space
        f_step_GHz = self.unprocessed_freq_GHz[1] - self.unprocessed_freq_GHz[0]
        window_length = int(np.round(rpc.baseline_smoothing_window_GHz / f_step_GHz))
        if cosine_filter:
            mag, phase = self.cosine_filter_mag(reals21=self.unprocessed_reals21, imags21=self.unprocessed_imags21,
                                                smoothing_scale=rpc.baseline_smoothing_window_GHz * 1.0e9, plot=False)
        else:
            mag, phase = self.savgol_filter_mag(reals21=self.unprocessed_reals21, imags21=self.unprocessed_imags21,
                                                window_length=window_length, polyorder=2, plot=True)
        # interaction threshold plotting, return local minima and window information about size of the resonators
        i_thresh = fr_interactive.interactive_threshold_plot(f_Hz=self.unprocessed_freq_GHz * 1.0e9,
                                                             s21_mag=self.highpass_filter_mags21,
                                                             peak_threshold_dB=0.5,
                                                             spacing_threshold_Hz=rpc.resonator_spacing_threshold_Hz,
                                                             window_padding=window_padding)
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
                               plot=True)
        synthetic_baseline_smoothed = savgol_filter(x=synthetic_baseline,
                                                    window_length=window_length + 1, polyorder=3)
        self.filter_update_mag(mag=mag, phase=phase,
                               lowpass_filter_mags21=synthetic_baseline_smoothed,
                               plot=True)
        print()






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
            excess_tau = (left_phase - right_phase) / (2.0 * np.pi * (right_freq - left_freq))
            abs_gain = np.absolute(0.5 * ave_right_gain + 0.5 * ave_left_gain)
            abs_gain_slope = (np.absolute(ave_right_gain) - np.absolute(ave_left_gain)) / (right_freq - left_freq)
            print("Removing an excess group delay of " + str(excess_tau) + "ns from data")
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