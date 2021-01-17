import numpy as np
from scipy.signal import savgol_filter
from waferscreen.analyze.s21_inductor import read_s21, write_s21
from waferscreen.analyze.s21_metadata import MetaDataDict


class ResPipe:
    def __init__(self, s21_path, verbose=True):
        self.path = s21_path
        self.verbose = True
        self.unprocessed_freq_GHz, self.unprocessed_reals21, self.unprocessed_imags21 = None, None, None
        self.meta_data = None

    def read(self):
        data_dict, self.meta_data = read_s21(path=self.path)
        self.unprocessed_freq_GHz = data_dict["freq_ghz"]
        self.unprocessed_reals21, self.unprocessed_imags21 = data_dict["real"],  data_dict["imag"]

    def gain_correct(self):
        pass

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