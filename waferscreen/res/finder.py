import os
import shutil
from typing import NamedTuple, Optional
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from ref import raw_data_dir, pro_data_dir, s21_file_extensions
import waferscreen.res.single_fits as fit_res
from waferscreen.read.prodata import read_pro_s21, ResParams, res_params_header


"""
Written by Jake Connors 24 Jan 2020, v2 10 March 2020
Diced up and with scope changes for a new control flow on November 5, 2020 Caleb Wheeler
Consumes an array of complex s21 transmission data
Removes absolute gain, gain slope
Smooths data using a savitsky-golay filter to reduce noise in derivatives
Optionally removes baseline ripple using a wider savitsky-golay filter
Takes complex 1st derivative of s21 data w.r.t. frequency
Finds component of 1st derivative in the amplitude and phase directions given s21 position
Searches for maxima of Qt~f/2*ds21/df*theta-hat above a given threshold and minimum spacing to identify resonances
Returns a list of resonant frequencies and optionally writes this to a text file
"""


def package_res_results(popt, pcov, verbose=False):
    fit_Amag = popt[0]
    fit_Aphase = popt[1]
    fit_Aslope = popt[2]
    fit_tau = popt[3]
    fit_f0 = popt[4]
    fit_Qi = popt[5]
    fit_Qc = popt[6]
    fit_Zratio = popt[7]

    error_Amag = np.sqrt(pcov[0, 0])
    error_Aphase = np.sqrt(pcov[1, 1])
    error_Aslope = np.sqrt(pcov[2, 2])
    error_tau = np.sqrt(pcov[3, 3])
    error_f0 = np.sqrt(pcov[4, 4])
    error_Qi = np.sqrt(pcov[5, 5])
    error_Qc = np.sqrt(pcov[6, 6])
    error_Zratio = np.sqrt(pcov[7, 7])

    if verbose:
        print('Fit Result')
        print('Amag          : %.4f +/- %.6f' % (fit_Amag, error_Amag))
        print('Aphase        : %.2f +/- %.4f Deg' % (fit_Aphase, error_Aphase))
        print('Aslope        : %.3f +/- %.3f /GHz' % (fit_Aslope, error_Aslope))
        print('Tau           : %.3f +/- %.3f ns' % (fit_tau, error_tau))
        print('f0            : %.6f +/- %.8f GHz' % (fit_f0, error_f0))
        print('Qi            : %.0f +/- %.0f' % (fit_Qi, error_Qi))
        print('Qc            : %.0f +/- %.0f' % (fit_Qc, error_Qc))
        print('Im(Z0)/Re(Z0) : %.2f +/- %.3f' % (fit_Zratio, error_Zratio))
        print('')

    single_res_params = ResParams(Amag=fit_Amag, Amag_error=error_Amag,
                                  Aphase=fit_Aphase, Aphase_error=error_Aphase,
                                  Aslope=fit_Aslope, Aslope_error=error_Aslope,
                                  tau=fit_tau, tau_error=error_tau,
                                  f0=fit_f0, f0_error=error_f0,
                                  Qi=fit_Qi, Qi_error=error_Qi,
                                  Qc=fit_Qc, Qc_error=error_Qc,
                                  Zratio=fit_Zratio, Zratio_error=error_Zratio)
    return single_res_params


class ResFinder:
    def __init__(self, file, remove_baseline_ripple=False, verbose=True, auto_process=True):
        self.filename = file
        file_basename = os.path.basename(file)
        base_handle, _extension = file_basename.rsplit(".", 1)
        self.wafer_name, self.trace_number, self.data_str, *self.run_details = base_handle.split("_", 3)
        self.plot_prefix = ""
        if self.run_details:
            for an_item in self.run_details:
                self.plot_prefix += an_item
            self.plot_prefix += "_"

        self.verbose = verbose
        self.freq_units = "ghz"
    
        """resonance finding parameters """
        self.edge_search_depth = 50                  # how many frequency points inward from edges to average in removing gain, phase and gain slope offsets
        self.smoothing_scale_kHz = 75                # smoothing scale in savitsky-golay procedure
        self.smoothing_order = 5                     # smoothing order in savitsky-golay procedure
        self.cutoff_rate = 5000                      # cutoff in Qt^2/Qc to find resonances
        self.minimum_spacing_kHz = 100.0             # minimum spacing between resonances
        self.remove_baseline_ripple_find_res = remove_baseline_ripple  # uses a wider savitsky-golay procedure to remove baseline ripple during resonance finding
        self.baseline_scale_kHz_find_res = 3000      # smoothing scale for baseline ripple removal, should be ~30x smoothing_scale_kHz
        self.baseline_order_find_res = 3             # smoothing order for baseline ripple removal
        self.make_plots_find_res = True              # make plots during resonance finding

        """resonator fitting options"""
        self.fitting_range_kHz = 500.0  # kHz, range around each resonance to use to fit
        self.throw_out = 0  # doesnt use N points on the edge of each sweep
        self.fit_model = 'simple_res_gain_slope_complex'  # name of model to fit to resonance
        self.error_est = 'prop'  # 'prop' or 'flat', proportional or constant errors
        self.fit_guess_plots = True  # make plots of each fit guess

        """File name a directory determinations"""
        output_folder = pro_data_dir
        for dir_name in ['s21', self.wafer_name, self.trace_number, self.data_str]:
            output_folder = os.path.join(output_folder, dir_name)
            if not os.path.isdir(output_folder):
                os.mkdir(output_folder)
        self.output_folder = output_folder
        self.resonator_output_folder = os.path.join(self.output_folder, 'resonators')
        if not os.path.isdir(self.resonator_output_folder):
            os.mkdir(self.resonator_output_folder)
        if self.filename != os.path.join(self.output_folder, file_basename):
            shutil.copyfile(self.filename, os.path.join(self.output_folder, file_basename))
        self.fit_filename = os.path.join(self.output_folder, base_handle + "_fit.csv")

        """Data containers populated by the methods of this class"""
        self.freqs = None
        self.s21 = None
        self.s21_meta_data = None
        self.res_freqs = None
        self.res_params = None

        if auto_process:
            self.open()
            self.find_resonances()
            self.extract_params()

    def open(self):
        self.freqs, self.s21, self.s21_meta_data = read_pro_s21(path=self.filename)

    def find_resonances(self, show_plot=False):
        # pass this s21 sweep to find_resonances_fast
        self.res_freqs = find_resonances(self.freqs, self.s21, edge_search_depth=self.edge_search_depth,
                                         smoothing_scale_kHz=self.smoothing_scale_kHz,
                                         smoothing_order=self.smoothing_order, cutoff_rate=self.cutoff_rate,
                                         minimum_spacing_kHz=self.minimum_spacing_kHz,
                                         remove_baseline_ripple=self.remove_baseline_ripple_find_res,
                                         baseline_scale_kHz=self.baseline_scale_kHz_find_res,
                                         baseline_order=self.baseline_order_find_res,
                                         verbose=self.verbose,
                                         make_plots=self.make_plots_find_res,
                                         plot_dir=self.output_folder,
                                         file_prefix=self.plot_prefix,
                                         show_plot=show_plot)
        
    def extract_params(self, show_plot=False):
        # loop over found resonators and fit to a model to extract Qt, Qc, Qi, f0, Fano etc
        self.res_params = []
        delta_f = (self.freqs[1] - self.freqs[0]) * 1e6
        float_samples = self.fitting_range_kHz / delta_f
        n_samples = np.floor(float_samples) + 1  # only need to take data this far around a given resonance
        if self.verbose:
            print("Data frequency spacing is " + str(delta_f) + "kHz")
            print("Fitting range is +/- " + str(self.fitting_range_kHz) + "kHz")
            print("Need to fit +/-" + str(n_samples) + " samples around each resonance center")
        prev_res_index = 0
        for i in range(0, len(self.res_freqs)):
            if self.verbose:
                print("Fitting found resonance #" + str(i+1) + "/" + str(len(self.res_freqs)))
            # only pass section of data that's within range of the resonance
            res_index = prev_res_index
            res_found = False
            while not res_found and res_index < len(self.freqs):
                if self.freqs[res_index] > self.res_freqs[i]:
                    res_found = True
                    prev_res_index = res_index
                else:
                    res_index = res_index + 1
            # now res_index is the index of the freq that's half a bin above the marked fr
            fit_freqs = self.freqs[int(max(res_index - n_samples - 1, 0)):
                                   int(min(res_index + n_samples + 1, len(self.freqs) - 1))]
            fit_s21data = self.s21[int(max(res_index - n_samples - 1, 0)):
                                   int(min(res_index + n_samples + 1, len(self.s21) - 1))]
            # now fit the resonance
            popt, pcov = fit_res.fit_resonator(fit_freqs, fit_s21data, data_format='COM', model=self.fit_model,
                                               error_est=self.error_est, throw_out=self.throw_out,
                                               make_plot=self.fit_guess_plots, plot_dir=self.resonator_output_folder,
                                               file_prefix=self.plot_prefix, show_plot=show_plot)

            self.res_params.append(package_res_results(popt=popt, pcov=pcov, verbose=self.verbose))
        self.write_results()

    def write_results(self):
        with open(self.fit_filename, 'w') as f:
            f.write(res_params_header + "\n")
            for single_res_params in self.res_params:
                f.write(str(single_res_params) + "\n")


def process_all(s21_data_dir):
    all_files = [os.path.join(s21_data_dir, f) for f in os.listdir(s21_data_dir)
                 if os.path.isfile(os.path.join(s21_data_dir, f))]
    s21_files = []
    for single_file in all_files:
        _, file_extension = single_file.rsplit(".", 1)
        if file_extension in s21_file_extensions:
            s21_files.append(single_file)
    return {single_file: ResFinder(file=single_file, verbose=True, freq_units="MHz", auto_process=True) for single_file in s21_files}


def find_resonances(freqs,
                    s21_complex,
                    edge_search_depth=50,
                    smoothing_scale_kHz=25,
                    smoothing_order=5,
                    cutoff_rate=500,
                    minimum_spacing_kHz=100.0,
                    remove_baseline_ripple=True,
                    baseline_scale_kHz=3000,
                    baseline_order=3,
                    input_freq_units="GHz",
                    write_out_freqs=False,
                    freqs_filename="D:\\Data\\uMux\\scratch\\test_freq_output.txt",
                    verbose=False,
                    make_plots=False,
                    plot_dir=pro_data_dir,
                    file_prefix="",
                    show_plot=False):

    # start by converting frequencies to GHz and making sure it is in array form
    if input_freq_units == "Hz":
        freqs = np.array(freqs) * 1e-9  # convert to GHz from Hz
    elif input_freq_units == "kHz":
        freqs = np.array(freqs) * 1e-6  # convert to GHz from kHz
    elif input_freq_units == "MHz":
        freqs = np.array(freqs) * 1e-3  # convert to GHz from MHz
    elif input_freq_units == "GHz":
        freqs = np.array(freqs)  # no need to convert

    if verbose:
        print("Taken in Data")

    # figure out complex gain and gain slope
    ave_left_gain = 0
    ave_right_gain = 0
    for j in range(0, edge_search_depth):
        ave_left_gain = ave_left_gain + s21_complex[j] / edge_search_depth
        ave_right_gain = ave_right_gain + s21_complex[len(s21_complex) - 1 - j] / edge_search_depth
    left_freq = freqs[int(edge_search_depth / 2.0)]
    right_freq = freqs[len(freqs) - 1 - int(edge_search_depth / 2.0)]
    gain_slope = (ave_right_gain - ave_left_gain) / (right_freq - left_freq)
    if verbose:
        # calculate extra group delay and abs gain slope removed for printing out purposes
        left_phase = np.arctan2(np.imag(ave_left_gain), np.real(ave_left_gain))
        right_phase = np.arctan2(np.imag(ave_right_gain), np.real(ave_right_gain))
        excess_tau = (left_phase - right_phase) / (2.0 * np.pi * (right_freq - left_freq))
        abs_gain = np.absolute(0.5 * ave_right_gain + 0.5 * ave_left_gain)
        abs_gain_slope = (np.absolute(ave_right_gain) - np.absolute(ave_left_gain)) / (right_freq - left_freq)
        print("Removing an excess group delay of " + str(excess_tau) + "ns from data")
        print("Removing a gain of " + str(abs_gain) + " and slope of " + str(abs_gain_slope) + "/GHz from data")
    gains = ave_left_gain + (freqs - left_freq) * gain_slope
    s21_complex = s21_complex / gains

    if verbose:
        print("Removed gain and excess group delay")

    # remove baseline ripple if desired
    if remove_baseline_ripple:
        freq_spacing = (freqs[1] - freqs[0]) * 1.0e6  # GHz -> kHz
        baseline_scale = int(round(baseline_scale_kHz / freq_spacing))
        if baseline_scale % 2 == 0:  # if even
            baseline_scale = baseline_scale + 1  # make it odd
        if verbose:
            print("Freq Spacing is " + str(freq_spacing) + "kHz")
            print("Requested baseline smoothing scale is " + str(baseline_scale_kHz) + "kHz")
            print("Number of points to smooth over is " + str(baseline_scale))
        # smooth s21 trace in both real and imaginary to do peak finding
        baseline_real = savgol_filter(np.real(s21_complex), baseline_scale, baseline_order)
        baseline_imag = savgol_filter(np.imag(s21_complex), baseline_scale, baseline_order)
        baseline = np.array(baseline_real + 1j * baseline_imag)
        pre_baseline_removal_s21_complex = np.copy(s21_complex)
        s21_complex = s21_complex / baseline

    # figure out freq spacing, convert smoothing_scale_kHz to smoothing_scale (must be an odd number)
    freq_spacing = (freqs[1] - freqs[0]) * 1e6  # GHz -> kHz
    smoothing_scale = int(round(smoothing_scale_kHz / freq_spacing))
    if smoothing_scale % 2 == 0:  # if even
        smoothing_scale = smoothing_scale + 1  # make it odd
    if smoothing_scale >= smoothing_order:
        smoothing_order = smoothing_scale - 1
    if smoothing_scale <= smoothing_order:
        print(F"For smoothing scale of {smoothing_scale_kHz}kHz is too find, soothing skipped.")
        s21_complex_smooth = s21_complex
    else:
        if verbose:
            print("Freq Spacing is " + str(freq_spacing) + "kHz")
            print("Requested smoothing scale is " + str(smoothing_scale_kHz) + "kHz")
            print("Number of points to smooth over is " + str(smoothing_scale))
        # smooth s21 trace in both real and imaginary to do peak finding
        s21_complex_smooth_real = savgol_filter(np.real(s21_complex), smoothing_scale, smoothing_order)
        s21_complex_smooth_imag = savgol_filter(np.imag(s21_complex), smoothing_scale, smoothing_order)
        s21_complex_smooth = np.array(s21_complex_smooth_real + 1j * s21_complex_smooth_imag)

    if verbose:
        print("Smoothed Data")

    # take derivative of data (optional) and smoothed data
    first_deriv_smooth = []
    first_deriv_freqs = []
    for j in range(0, len(s21_complex_smooth) - 1):
        if freqs[j + 1] - freqs[j] < 1e-7:
            print(freqs[j])
            print(freqs[j + 1])
        first_deriv_smooth.append((s21_complex_smooth[j + 1] - s21_complex_smooth[j]) / (freqs[j + 1] - freqs[j]))
        first_deriv_freqs.append((freqs[j + 1] + freqs[j]) / 2.0)
    first_deriv_smooth = np.array(first_deriv_smooth)
    first_deriv_freqs = np.array(first_deriv_freqs)

    if verbose:
        print("Derivative Taken")

    # rotate first deriv into r-hat vs. theta-hat coordinates using original position of s21
    first_deriv_rot_smooth = []
    for j in range(0, len(first_deriv_smooth)):
        s21_complex_pt_smooth = (s21_complex_smooth[j] + s21_complex_smooth[j + 1]) / 2.0
        theta_smooth = np.arctan2(np.imag(s21_complex_pt_smooth), np.real(s21_complex_pt_smooth))
        first_deriv_rot_smooth.append([(np.real(first_deriv_smooth[j]) * np.cos(theta_smooth) + np.imag(
            first_deriv_smooth[j]) * np.sin(theta_smooth)), (-1.0 * np.real(first_deriv_smooth[j]) * np.sin(
            theta_smooth) + np.imag(first_deriv_smooth[j]) * np.cos(theta_smooth))])
    first_deriv_rot_smooth = np.array(first_deriv_rot_smooth)

    if verbose:
        print("Derivative Rotated")

    # use smoothed rotated first derivatives to find resonances
    frs = []
    Qts = []
    # figure out spacing between freqs
    delta_f = first_deriv_freqs[1] - first_deriv_freqs[0]
    float_samples = minimum_spacing_kHz / (delta_f * 1e6)
    n_samples = int(np.floor(float_samples) + 1)  # only need to look this far around a given point above cutoff
    if verbose:
        print("Data spacing is " + str(delta_f * 1e6) + "kHz")
        print("Prescribed minimum resonator spacing is " + str(minimum_spacing_kHz) + "kHz")
        print("Need to look +/-" + str(n_samples) + " samples around each point above cutoff")
    for j in range(len(first_deriv_rot_smooth)):
        if first_deriv_rot_smooth[j, 1] * (first_deriv_freqs[j] / 2.0) > cutoff_rate:
            another_higher = False
            k = max(0, j - n_samples)  # start looking at k = j - n_samples
            while not another_higher and k < len(first_deriv_rot_smooth) and k < j + n_samples + 1:
                if abs(first_deriv_freqs[j] - first_deriv_freqs[k]) < minimum_spacing_kHz * 1e-6 and j != k:
                    # freq is within range
                    if first_deriv_rot_smooth[k, 1] * (first_deriv_freqs[k] / 2.0) > first_deriv_rot_smooth[j, 1] * (
                            first_deriv_freqs[j] / 2.0):  # found one with larger derivative
                        another_higher = True
                # increment k, check if next point is higher
                k = k + 1
            if not another_higher:  # confirmed, this is the highest point within +/- minimum spacing
                frs.append(first_deriv_freqs[j])
                Qts.append(first_deriv_rot_smooth[j, 1] * (first_deriv_freqs[j] / 2.0))
                if verbose:
                    print("Added " + str(first_deriv_freqs[j]) + "GHz")
    frs = np.array(frs)

    if verbose:
        print("Found " + str(len(frs)) + " Resonators")

    if write_out_freqs:
        # write out resonant frequencies to files (one for each input file)
        fout = open(freqs_filename, "w")
        for j in range(0, len(frs)):
            fout.write(str(frs[j]) + "\n")
        fout.close()
        if verbose:
            print("Files Written Out")

    if make_plots:
        if remove_baseline_ripple:
            # plot baseline removal data
            fig5 = plt.figure(5)
            ax51 = fig5.add_subplot(121)
            ax51.plot(freqs, 20.0 * np.log10(np.absolute(pre_baseline_removal_s21_complex)), c='b', label='Raw')
            ax51.plot(freqs, 20.0 * np.log10(np.absolute(s21_complex)), c='r', label='Baseline Removed')
            ax51.plot(freqs, 20.0 * np.log10(np.absolute(baseline)), c='g', label='Baseline')
            ax51.set_ylim([-15, 2.5])
            ax51.set_xlabel("Freq. (GHz)")
            ax51.set_ylabel(r"$\left| S_{21} \right|^2$ (dB)")
            ax51.legend(loc='upper right')

            ax52 = fig5.add_subplot(122)
            ax52.plot(freqs, 180.0 / np.pi * np.arctan2(np.imag(pre_baseline_removal_s21_complex),
                                                          np.real(pre_baseline_removal_s21_complex)), c='b', label='Raw')
            ax52.plot(freqs, 180.0 / np.pi * np.arctan2(np.imag(s21_complex), np.real(s21_complex)), c='r',
                      label='Baseline Removed')
            ax52.plot(freqs, 180.0 / np.pi * np.arctan2(np.imag(baseline), np.real(baseline)), c='g',
                      label='Baseline')
            ax52.set_xlabel("Freq. (GHz)")
            ax52.set_ylabel(r"$\angle S_{21}$ (Deg)")
            ax52.legend(loc='upper right')
            fig5.savefig(os.path.join(plot_dir, file_prefix + "fig5_baseline_ripple.pdf"))
        if show_plot:
            plt.show()
        if remove_baseline_ripple:
            fig5.clf()
    return frs


if __name__ == "__main__":
    data_dir = os.path.join(raw_data_dir, 'umux', "s4data")
    example_file = os.path.join(data_dir, "WaferName_TraceNumber_2020-07-13.csv")
    group_delay = 31.839
    # res_fit = ResFit(file=file, group_delay=group_delay, verbose=True, freq_units="MHz", auto_process=True)
    fits_dict = process_all(s21_data_dir=data_dir)
