from scipy.signal import savgol_filter
from scipy.optimize import curve_fit
import numpy as np
from waferscreen.res.single_fits import fit_simple_res_gain_slope_complex
from waferscreen.analyze.res_io import ResParams


def simple_res_gain_slope_complex_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope,
                                        tau_ns, f0, Qi, Qc, Zratio):
    A = base_amplitude_abs * (1 + base_amplitude_slope * (freq_GHz - f0)) * (
                np.cos(a_phase_rad) + 1j * np.sin(a_phase_rad))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq_GHz - f0) * 2.0 * np.pi * tau_ns)  # tau_ns in ns, freq_GHz in GHz
    # shunt resonator model
    # s11_temp = (Zratio / Qc - 1j / Qc) / (1 - (freq_GHz / f0) ** 2 + 1j / Qi + 1j / Qc)
    s21_temp = (1 - (freq_GHz / f0) ** 2 + 1j / Qi) / (1 - (freq_GHz / f0) ** 2 - Zratio / Qc + 1j / Qi + 1j / Qc)
    s21data = A * phase_delay * s21_temp
    return s21data


def fit_simple_res_gain_slope_complex(freqs_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope,
                                      tau_ns, f0, Qi, Qc, Zratio):
    """
    Lorentzian Resonator w/ gain slope and complex feedline impedance
    """
    s21data = []
    for freq_GHz in freqs_GHz:
        s21 = simple_res_gain_slope_complex_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Zratio)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def rebound_starting_vals(bounds, starting_vals):
    """
    Takes starting guess for resonator and makes sure it's within bounds
    """
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
        print('a_phase_rad          : %.4f +/- %.6f Radians' % (fit_a_phase_rad, error_a_phase_rad))
        print('base_amplitude_slope : %.3f +/- %.3f GHz' % (fit_base_amplitude_slope, error_base_amplitude_slope))
        print('tau_ns        : %.3f +/- %.3f ns' % (fit_tau_ns, error_tau_ns))
        print('fcenter       : %.6f +/- %.8f GHz' % (fit_f0, error_f0))
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


def jake_res_finder(unprocessed_freq_GHz,
                    unprocessed_reals21,
                    unprocessed_imags21,
                    edge_search_depth=50,
                    smoothing_scale_kHz=25,
                    smoothing_order=5,
                    cutoff_rate=500,
                    minimum_spacing_kHz=100.0,
                    remove_baseline_ripple=True,
                    baseline_scale_kHz=3000,
                    baseline_order=3,
                    verbose=True):
    freq_GHz = unprocessed_freq_GHz
    s21_complex = unprocessed_reals21 + 1j * unprocessed_imags21
    # figure out complex gain and gain slope
    ave_left_gain = 0
    ave_right_gain = 0
    for j in range(0, edge_search_depth):
        ave_left_gain = ave_left_gain + s21_complex[j] / edge_search_depth
        ave_right_gain = ave_right_gain + s21_complex[len(s21_complex) - 1 - j] / edge_search_depth
    left_freq = freq_GHz[int(edge_search_depth / 2.0)]
    right_freq = freq_GHz[len(freq_GHz) - 1 - int(edge_search_depth / 2.0)]
    gain_slope = (ave_right_gain - ave_left_gain) / (right_freq - left_freq)
    if verbose:
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
    if verbose:
        print("Found " + str(len(frs)) + " Resonators")
    return frs