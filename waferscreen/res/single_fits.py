#!/usr/bin/python
import os
import numpy as np
import math
import cmath
import scipy.special as specfunc
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from ref import pro_data_dir


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


def renormalize_smat(smat, z0, z0_new):
    # renormalizes 2port s matrices from z0 to z0_new, assuming both port impedances are the same in both cases
    emat = np.array([[1, 0], [0, 1]])
    ref = (z0_new - z0) / (z0_new + z0)
    rmat = np.array([[ref, 0], [0, ref]])
    amp = np.sqrt(z0_new / z0) * 1.0 / (z0_new + z0)
    amat = np.array([[amp, 0], [0, amp]])
    smat_new = np.dot(np.linalg.inv(amat),
                      np.dot((smat - rmat), np.dot(np.linalg.inv(emat - np.dot(rmat, smat)), amat)))
    return smat_new


def fit_resonator(freqs, s21data, data_format='RI', model='simple_res', error_est='prop', throw_out=0,
                  make_plot=True, plot_dir=pro_data_dir, file_prefix="", show_plot=False):
    """
    Function which returns fit parameters to a resonator model
    freqs are the measured frequencies, s21data is the S21 data
    model selects which function to fit to
    error_est chooses your error estimation method, prop, const, etc...
    throw out tosses out the first and last N points
    """

    # trim down freqs and data so that only the part you want to fit is used
    fit_freqs = []
    fit_params = []
    for i in range(0, len(freqs)):
        if (i >= throw_out) and (
                i < len(freqs) - throw_out):  # if not within throw_out points of the edges of the measurement
            fit_freqs.append(freqs[i])
            if data_format == 'RI':  # real and imaginary
                fit_params.append(np.array([s21data[i, 0], s21data[i, 1]]))
            elif data_format == 'LM':  # log magnitude (dB) and phase (deg)
                s21R = 10 ** (s21data[i, 0] / 20.0) * math.cos(math.pi / 180.0 * s21data[i, 1])
                s21I = 10 ** (s21data[i, 0] / 20.0) * math.sin(math.pi / 180.0 * s21data[i, 1])
                fit_params.append(np.array([s21R, s21I]))
            elif data_format == 'COM':  # complex
                fit_params.append(np.array([s21data[i].real, s21data[i].imag]))
            else:
                raise KeyError('Data Format not recognized.')
    fit_freqs = np.array(fit_freqs)
    fit_params = np.array(fit_params)

    # guess Amag and Aphase by looking at ends of data
    est_A_range = 10  # number of data points on each end used to estimate A
    A_low_guess = 0
    A_high_guess = 0
    for i in range(0, est_A_range):
        A_low_guess = A_low_guess + (fit_params[i, 0] + 1j * fit_params[i, 1]) / est_A_range
        A_high_guess = A_high_guess + (
                    fit_params[len(fit_freqs) - i - 1, 0] + 1j * fit_params[len(fit_freqs) - i - 1, 1]) / est_A_range
    Aave = 0.5 * (A_low_guess + A_high_guess)
    Amag_guess = np.abs(Aave)  # average of low and high magnitudes
    Aphase_guess = 180.0 / math.pi * np.arctan2(Aave.imag, Aave.real)  # average of high and low phases

    # guess Aslope and tau by looking at difference in A_high and A_low
    delta_guess_index = int(round(est_A_range / 2.0))
    delta_freq = fit_freqs[len(fit_freqs) - delta_guess_index] - fit_freqs[delta_guess_index]
    Aslope_guess = (np.abs(A_high_guess) - np.abs(A_low_guess)) / delta_freq

    phase_high_guess = np.arctan2(A_high_guess.imag, A_high_guess.real)  # in radians
    phase_low_guess = np.arctan2(A_low_guess.imag, A_low_guess.real)  # in radians
    tau_guess = (phase_low_guess - phase_high_guess) / (2.0 * math.pi * delta_freq)

    print('Fit Guesses')
    print('Amag   : %.4f' % Amag_guess)
    print('Aphase : %.2f Deg' % Aphase_guess)
    print('Aslope : %.3f /GHz' % Aslope_guess)
    print('Tau    : %.3f ns' % tau_guess)

    # now make array of |s21|^2, remove baseline gain and slope
    guess_s21 = []
    f_mid = (fit_freqs[len(fit_freqs) - 1] + fit_freqs[0]) / 2.0
    for i in range(0, len(fit_freqs)):
        raw_s21 = fit_params[i, 0] ** 2 + fit_params[i, 1] ** 2
        guess_s21.append(raw_s21 / ((Amag_guess + Aslope_guess * (
                    fit_freqs[i] - f_mid)) ** 2))  # normalize |s21|^2 using guesses for Amag and Aslope

    # smooth s21 trace
    window_size, poly_order = 25, 3
    guess_s21_filt = savgol_filter(guess_s21, window_size, poly_order)

    # guess f0
    s21_min = 1e15
    f0_guess = -1
    for i in range(0, len(fit_freqs)):  # find freq of minimum transmission
        fit_vec = fit_params[i]
        if guess_s21_filt[i] < s21_min:
            s21_min = guess_s21_filt[i]
            f0_guess = fit_freqs[i]
    if f0_guess == -1:  # if this somehow fails, choose f_mid
        f0_guess = f_mid

    print('f0     : %.4f GHz' % f0_guess)

    # guess Qi and Qc by looking for FWHM (effective)
    s21_search = 0.5 * (1 + s21_min)  # = |s21|^2 at (1-(f/f0)^2) == Qt^-1
    # now find first point to have |S21|^2 < s21_search
    i = 0
    while guess_s21_filt[i] > s21_search and i < len(fit_freqs) - 1:
        i += 1
    f_lower = fit_freqs[i]
    # now find first point to have |S21|^2 < 0.5 * |A|^2 from above
    i = len(fit_freqs) - 1
    while guess_s21_filt[i] > s21_search and i >= 0:
        i -= 1
    f_upper = fit_freqs[i]
    if f_lower < f0_guess and f_upper > f0_guess:
        Qt_lower = 1.0 / (1 - (f_lower / f0_guess) ** 2)
        Qt_upper = -1.0 / (1 - (f_upper / f0_guess) ** 2)
        Qt = 0.5 * (Qt_lower + Qt_upper)
    elif f_lower < f_upper:
        f_mid_guess = 0.5 * (f_upper + f_lower)
        Qt_lower = 1.0 / (1 - (f_lower / f_mid_guess) ** 2)
        Qt_upper = -1.0 / (1 - (f_upper / f_mid_guess) ** 2)
        Qt = 0.5 * (Qt_lower + Qt_upper)
    else:  # guess
        Qt = f0_guess / (fit_freqs[len(fit_freqs) - 1] - fit_freqs[0])
        print("Error in Estimating Qtotal")
    if Qt < 1:
        Qt = 1
    if math.isnan(Qt):
        Qt = f0_guess / (fit_freqs[len(fit_freqs) - 1] - fit_freqs[0])
    Qi_guess = Qt / np.sqrt(s21_min)
    Qc_guess = 1.0 / (1.0 / Qt - 1.0 / Qi_guess)
    if math.isnan(Qi_guess):
        Qi_guess = f0_guess / (fit_freqs[len(fit_freqs) - 1] - fit_freqs[0])
        Qc_guess = f0_guess / (fit_freqs[len(fit_freqs) - 1] - fit_freqs[0])

    print('Qi     : %.0f' % Qi_guess)
    print('Qc     : %.0f' % Qc_guess)

    if make_plot:
        fig0 = plt.figure(0)
        ax0 = fig0.add_subplot(111)
        ax0.plot(fit_freqs, guess_s21)
        ax0.plot(fit_freqs, guess_s21_filt)
        ax0.plot([fit_freqs[0], fit_freqs[len(fit_freqs) - 1]], [1, 1], c='k', linestyle='--')
        ax0.plot([fit_freqs[0], fit_freqs[len(fit_freqs) - 1]], [s21_min, s21_min], c='k', linestyle='--')
        ax0.plot([fit_freqs[0], fit_freqs[len(fit_freqs) - 1]], [s21_search, s21_search], c='k', linestyle='--')
        ax0.plot([f_lower, f_lower], [s21_min, 1], c='r', linestyle='--')
        ax0.plot([f_upper, f_upper], [s21_min, 1], c='r', linestyle='--')
        ax0.plot([f0_guess, f0_guess], [s21_min, 1], c='b', linestyle='--')
        if show_plot:
            plt.show()
        fig0.savefig(os.path.join(plot_dir, file_prefix + str("%1.5f" % f0_guess) + "_GHz_resonator_fit.pdf"))
        fig0.clf()

    # use curve fit to for these params
    popt, pcov = single_res_fit(model=model, fit_freqs=fit_freqs,
                                fit_params=fit_params, error_est=error_est,
                                Amag_guess=Amag_guess, Aphase_guess=Aphase_guess,
                                f0_guess=f0_guess, Qi_guess=Qi_guess, Qc_guess=Qc_guess,
                                Aslope_guess=Aslope_guess, tau_guess=tau_guess)
    return popt, pcov


def est_error(fit_freqs, fit_params, error_est='prop'):
    # estimate errors according to method est_errors
    error_params = []
    if error_est == 'prop':  # estimate errors are proportional to |S| or |Y|
        print('Using Proportional Errors')
        e11_min = 0.0
        for i in range(0, len(fit_freqs)):
            fit_vec = fit_params[i]
            e1 = np.sqrt(fit_vec[0] ** 2 + fit_vec[1] ** 2) + e11_min
            error_vec = np.array([e1, e1])
            error_params.append(error_vec)
    elif error_est == 'flat':  # estimate errors are constant
        print('Using Flat Errors')
        for i in range(0, len(fit_freqs)):
            error_vec = np.array([1.0, 1.0])
            error_params.append(error_vec)
    else:
        raise KeyError('Error estimation method not recognized')
    return np.array(error_params)


def single_res_fit(model, fit_freqs, fit_params, error_est,
                   Amag_guess, Aphase_guess, f0_guess, Qi_guess, Qc_guess,
                   Aslope_guess=None, tau_guess=None):
    # use curve fit to for these params
    error_params = est_error(fit_freqs, fit_params, error_est=error_est)
    # unravel fit parameters and errors to 1D vector
    error_params = np.array(error_params)
    fit_params = fit_params.ravel()
    error_params = error_params.ravel()
    # perform fit using optimize.curve_fit
    if model == 'simple_res':  # (Amag, Aphase, tau, f0, Qi, Qc)
        starting_vals = [Amag_guess, Aphase_guess, 0, f0_guess, Qi_guess, Qc_guess]
        bounds = ((0, -360.0, -10, fit_freqs[0], 0, 0), (np.inf, 360.0, 10, fit_freqs[-1], np.inf, np.inf))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res, fit_freqs, fit_params, p0=starting_vals, sigma=error_params,
                               bounds=bounds)  # , max_nfev = 10000)
    elif model == 'simple_res_gain_slope':  # (Amag, Aphase, Aslope, tau, f0, Qi, Qc)
        starting_vals = [Amag_guess, Aphase_guess, 0, 0, f0_guess, Qi_guess, Qc_guess]
        bounds = ((0, -360.0, -10, -10, fit_freqs[0], 0, 0), (np.inf, 360.0, 10, 10, fit_freqs[-1], np.inf, np.inf))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res_gain_slope, fit_freqs, fit_params, p0=starting_vals, sigma=error_params,
                               bounds=bounds)  # , max_nfev = 10000)
    elif model == 'simple_res_nonlinear_phase':  # (Amag, Aphase, Pphase, tau, f0, Qi, Qc)
        starting_vals = [Amag_guess, Aphase_guess, 0, 0, f0_guess, Qi_guess, Qc_guess]
        bounds = ((0, -360.0, -10, -10, fit_freqs[0], 0, 0), (np.inf, 360.0, 10, 10, fit_freqs[-1], np.inf, np.inf))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res_nonlinear_phase, fit_freqs, fit_params, p0=starting_vals,
                               sigma=error_params, bounds=bounds)  # , max_nfev = 10000)
    elif model == 'simple_res_nonlinear_phase_gain_slope':  # (Amag, Aphase, Aslope, Pphase, tau, f0, Qi, Qc)
        starting_vals = [Amag_guess, Aphase_guess, 0, 0, 0, f0_guess, Qi_guess, Qc_guess]
        bounds = ((0, -360.0, -100, -10, -10, fit_freqs[0], 0, 0),
                  (np.inf, 360.0, 100, 10, 10, fit_freqs[-1], np.inf, np.inf))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res_nonlinear_phase_gain_slope, fit_freqs, fit_params, p0=starting_vals,
                               sigma=error_params, bounds=bounds)  # , max_nfev = 10000)
    elif model == 'tline_res':  # (Amag, Aphase, tau, f0, Qi, Qc, Z0ratio)
        starting_vals = [Amag_guess, Aphase_guess, 0, f0_guess, Qi_guess, Qc_guess, 1]
        bounds = (
        (0, -360.0, -10, fit_freqs[0], 0, 0, 0.99), (np.inf, 360.0, 10, fit_freqs[-1], np.inf, np.inf, 1.01))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_tline_res, fit_freqs, fit_params, p0=starting_vals, sigma=error_params,
                               bounds=bounds)  # , max_nfev = 10000)
    elif model == 'tline_res_gain_slope':  # (Amag, Aphase, Aslope, tau, f0, Qi, Qc, Z0ratio)
        starting_vals = [Amag_guess, Aphase_guess, 0, 0, f0_guess, Qi_guess, Qc_guess, 1]
        bounds = ((0, -360.0, -10, -10, fit_freqs[0], 0, 0, 0.99),
                  (np.inf, 360.0, 10, 10, fit_freqs[-1], np.inf, np.inf, 1.01))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_tline_res_gain_slope, fit_freqs, fit_params, p0=starting_vals, sigma=error_params,
                               bounds=bounds)  # , max_nfev = 10000)
    elif model == 'simple_res_gain_slope_renorm':  # (Amag, Aphase, Aslope, tau, f0, Qi, Qc, Z0new_real, Z0new_imag)
        starting_vals = [Amag_guess, Aphase_guess, Aslope_guess, tau_guess, f0_guess, Qi_guess, Qc_guess, 50, 0]
        bounds = ((0, -360.0, -100, -100, fit_freqs[0], 0, 0, 0, -np.inf),
                  (np.inf, 360.0, 100, 100, fit_freqs[-1], np.inf, np.inf, np.inf, np.inf))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res_gain_slope_renorm, fit_freqs, fit_params, p0=starting_vals,
                               sigma=error_params, bounds=bounds)  # , max_nfev = 10000)
    elif model == 'simple_res_gain_slope_complex':  # (Amag, Aphase, Aslope, tau, f0, Qi, Qc, Zratio)
        starting_vals = [Amag_guess, Aphase_guess, Aslope_guess, tau_guess, f0_guess, Qi_guess, Qc_guess, 0]
        bounds = (
        (0, -360.0, -1000, -100, fit_freqs.min(), 0, 0, -5.0), (np.inf, 360.0, 1000, 100, fit_freqs.max(), np.inf, np.inf, 5.0))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res_gain_slope_complex, fit_freqs, fit_params, p0=starting_vals,
                               sigma=error_params, bounds=bounds)  # , max_nfev = 10000)
    else:
        raise KeyError('Fit model : ' + str(model) + ' not recognized')
    return popt, pcov


def fit_simple_res(freqs, Amag, Aphase, tau, f0, Qi, Qc):
    """Simple Lorentzian Resonator"""
    s21data = []
    for freq in freqs:
        s21 = simple_res_model(freq, Amag, Aphase, tau, f0, Qi, Qc)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_model(freq, Amag, Aphase, tau, f0, Qi, Qc):
    A = Amag * (math.cos(math.pi * Aphase / 180.0) + 1j * math.sin(math.pi * Aphase / 180.0))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq - f0) * 2.0 * math.pi * tau)  # tau in ns, freq in GHz
    s21 = A * phase_delay * (1 - (freq / f0) ** 2 + 1j / Qi) / (1 - (freq / f0) ** 2 + 1j / Qi + 1j / Qc)
    return s21


def fit_simple_res_gain_slope(freqs, Amag, Aphase, Aslope, tau, f0, Qi, Qc):
    """Lorentzian Resonator w/ gain slope"""
    s21data = []
    for freq in freqs:
        s21 = simple_res_gain_slope_model(freq, Amag, Aphase, Aslope, tau, f0, Qi, Qc)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_gain_slope_model(freq, Amag, Aphase, Aslope, tau, f0, Qi, Qc):
    A = Amag * (1 + Aslope * (freq - f0)) * (
                math.cos(math.pi * Aphase / 180.0) + 1j * math.sin(math.pi * Aphase / 180.0))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq - f0) * 2.0 * math.pi * tau)  # tau in ns, freq in GHz
    s21 = A * phase_delay * (1 - (freq / f0) ** 2 + 1j / Qi) / (1 - (freq / f0) ** 2 + 1j / Qi + 1j / Qc)
    return s21


def fit_simple_res_nonlinear_phase(freqs, Amag, Aphase, Pphase, tau, f0, Qi, Qc):
    """Lorentzian Resonator w/ Non-linear Phase Response"""
    s21data = []
    for freq in freqs:
        s21 = simple_res_nonlinear_phase_model(freq, Amag, Aphase, Pphase, tau, f0, Qi, Qc)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_nonlinear_phase_model(freq, Amag, Aphase, Pphase, tau, f0, Qi, Qc):
    A = Amag * (math.cos(math.pi * Aphase / 180.0) + 1j * math.sin(math.pi * Aphase / 180.0))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq - f0) * 2.0 * math.pi * tau)  # tau in ns, freq in GHz
    s21 = A * phase_delay * (1 - (freq / f0) ** 2 + 1j / Qi) / (1 - (freq / f0) ** 2 + 1j / Qi + 1j / Qc)
    # additional phase delay due to power
    power_delay = np.exp(-1j * np.abs(s21) ** 2 / (Amag ** 2) * Pphase * math.pi / 180.0)
    return s21 * power_delay


def fit_simple_res_nonlinear_phase_gain_slope(freqs, Amag, Aphase, Aslope, Pphase, tau, f0, Qi, Qc):
    """Lorentzian Resonator w/ Gain Slope and Non-linear Phase Response """
    s21data = []
    for freq in freqs:
        s21 = simple_res_nonlinear_phase_gain_slope_model(freq, Amag, Aphase, Aslope, Pphase, tau, f0, Qi, Qc)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_nonlinear_phase_gain_slope_model(freq, Amag, Aphase, Aslope, Pphase, tau, f0, Qi, Qc):
    A = Amag * (1 + Aslope * (freq - f0)) * (
                math.cos(math.pi * Aphase / 180.0) + 1j * math.sin(math.pi * Aphase / 180.0))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq - f0) * 2.0 * math.pi * tau)  # tau in ns, freq in GHz
    s21 = A * phase_delay * (1 - (freq / f0) ** 2 + 1j / Qi) / (1 - (freq / f0) ** 2 + 1j / Qi + 1j / Qc)
    # additional phase delay due to power
    power_delay = np.exp(-1j * np.abs(s21) ** 2 / (Amag ** 2) * Pphase * math.pi / 180.0)
    return s21 * power_delay


def fit_tline_res(freqs, Amag, Aphase, tau, f0, Qi, Qc, Z0ratio):
    """Transmission line Resonator"""
    s21data = []
    for freq in freqs:
        s21 = tline_res_model(freq, Amag, Aphase, tau, f0, Qi, Qc, Z0ratio)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def tline_res_model(freq, Amag, Aphase, tau, f0, Qi, Qc, Z0ratio):
    A = Amag * (math.cos(math.pi * Aphase / 180.0) + 1j * math.sin(math.pi * Aphase / 180.0))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq - f0) * 2.0 * math.pi * tau)  # tau in ns, freq in GHz
    tan_mult_term = freq / f0 * np.sqrt((1.0 / Qc) * cmath.pi / 2 * Z0ratio * (1.0 - 1j * f0 / (freq * Qi)))
    tan_term = cmath.tan(freq / f0 * cmath.pi / 2 * np.sqrt(1.0 - 1j * f0 / (freq * Qi)))
    Qc_term = 0.5 * 1j * freq / f0 * np.sqrt(cmath.pi / (2 * Qc * Z0ratio))
    s21raw = (1.0 - tan_mult_term * tan_term) / (1.0 - tan_mult_term * tan_term + Qc_term)
    s21 = A * phase_delay * s21raw
    return s21


def fit_tline_res_gain_slope(freqs, Amag, Aphase, Aslope, tau, f0, Qi, Qc, Z0ratio):
    """Transmission line Resonator w/ gain slope """
    s21data = []
    Z0ratio = 1
    for freq in freqs:
        s21 = tline_res_gain_slope_model(freq, Amag, Aphase, Aslope, tau, f0, Qi, Qc, Z0ratio)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def tline_res_gain_slope_model(freq, Amag, Aphase, Aslope, tau, f0, Qi, Qc, Z0ratio):
    A = Amag * (1 + Aslope * (freq - f0)) * (
                math.cos(math.pi * Aphase / 180.0) + 1j * math.sin(math.pi * Aphase / 180.0))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq - f0) * 2.0 * math.pi * tau)  # tau in ns, freq in GHz
    tan_mult_term = freq / f0 * np.sqrt((1.0 / Qc) * cmath.pi / 2 * Z0ratio * (1.0 - 1j * f0 / (freq * Qi)))
    tan_term = cmath.tan(freq / f0 * cmath.pi / 2 * np.sqrt(1.0 - 1j * f0 / (freq * Qi)))
    Qc_term = 0.5 * 1j * freq / f0 * np.sqrt(cmath.pi / (2 * Qc * Z0ratio))
    s21raw = (1.0 - tan_mult_term * tan_term) / (1.0 - tan_mult_term * tan_term + Qc_term)
    s21 = A * phase_delay * s21raw
    return s21


def fit_simple_res_gain_slope_renorm(freqs, Amag, Aphase, Aslope, tau, f0, Qi, Qc, Z0new_real, Z0new_imag):
    """Lorentzian Resonator w/ gain slope and impedance renormalization"""
    s21data = []
    for freq in freqs:
        s21 = simple_res_gain_slope_renorm_model(freq, Amag, Aphase, Aslope, tau, f0, Qi, Qc, Z0new_real, Z0new_imag)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_gain_slope_renorm_model(freq, Amag, Aphase, Aslope, tau, f0, Qi, Qc, Z0new_real, Z0new_imag):
    A = Amag * (1 + Aslope * (freq - f0)) * (
                math.cos(math.pi * Aphase / 180.0) + 1j * math.sin(math.pi * Aphase / 180.0))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq - f0) * 2.0 * math.pi * tau)  # tau in ns, freq in GHz
    # shunt resonator model
    s11_temp = (-1j / Qc) / (1 - (freq / f0) ** 2 + 1j / Qi + 1j / Qc)
    s21_temp = (1 - (freq / f0) ** 2 + 1j / Qi) / (1 - (freq / f0) ** 2 + 1j / Qi + 1j / Qc)
    smat = [[s11_temp, s21_temp], [s21_temp, s11_temp]]
    new_smat = renormalize_smat(smat, 50, Z0new_real + 1j * Z0new_imag)
    s21 = A * phase_delay * new_smat[1, 0]
    return s21


def fit_simple_res_gain_slope_complex(freqs, Amag, Aphase, Aslope, tau, f0, Qi, Qc, Zratio):
    """Lorentzian Resonator w/ gain slope and complex feedline impedance"""
    s21data = []
    for freq in freqs:
        s21 = simple_res_gain_slope_complex_model(freq, Amag, Aphase, Aslope, tau, f0, Qi, Qc, Zratio)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_gain_slope_complex_model(freq, Amag, Aphase, Aslope, tau, f0, Qi, Qc, Zratio):
    A = Amag * (1 + Aslope * (freq - f0)) * (
                math.cos(math.pi * Aphase / 180.0) + 1j * math.sin(math.pi * Aphase / 180.0))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq - f0) * 2.0 * math.pi * tau)  # tau in ns, freq in GHz
    # shunt resonator model
    s11_temp = (Zratio / Qc - 1j / Qc) / (1 - (freq / f0) ** 2 + 1j / Qi + 1j / Qc)
    s21_temp = (1 - (freq / f0) ** 2 + 1j / Qi) / (1 - (freq / f0) ** 2 - Zratio / Qc + 1j / Qi + 1j / Qc)
    s21 = A * phase_delay * s21_temp
    return s21


def fit_resonator_mb_tls(temps, f0s, f0errors, Qi, Qierrors, temp_range=[0, np.inf]):
    """
    Code which takes fit results from temperature sweep data, and fits those results to a MB + TLS model
    for now just fit TLS to deltaFr
    """
    fit_temps = []
    fit_params = []
    error_params = []
    for i in range(0, len(temps)):
        if temps[i] >= temp_range[0] and temps[i] <= temp_range[1]:
            fit_temps.append(temps[i])
            fit_params.append(f0s[i])
            error_params.append(f0errors[i])
    fit_temps = np.array(fit_temps)
    fit_params = np.array(fit_params)
    error_params = np.array(error_params)

    starting_vals = [f0s[0], 1e-6]  # f0(T=0), FdeltaTLS
    print("F0 Guess:      " + str(f0s[0]))
    print("FtanD Guess  : " + str(1e-6))
    bounds = ((0, 0), (np.inf, np.inf))
    starting_vals = rebound_starting_vals(bounds, starting_vals)
    popt, pcov = curve_fit(fit_mb_tls, fit_temps, fit_params, p0=starting_vals, sigma=error_params, bounds=bounds,
                           absolute_sigma=True)

    return popt, pcov


def fit_mb_tls(temps, f0, FdeltaTLS):  # , delta, alphaK):
    """function which returns raveled array of fR(T) and Qi(T) for fitting purposes"""
    fRT = []
    for temp in temps:
        fR, Qi = mb_tls_model(temp, f0, FdeltaTLS)
        fRT.append(fR)  # , delta, alphaK))
    return np.array(fRT)


def mb_tls_model(temp, f0, FdeltaTLS):  # , delta, alphaK):
    """
    Mattis-Bardeen + TLS model for quarter wave resonators
    """
    hbar = 1.0545718e-34
    kB = 1.38064852e-23
    # for now just fit f0 to TLS, so only useful at low temp
    fR = f0 * (1.0 + (FdeltaTLS / math.pi) * (
                specfunc.digamma(0.5 - hbar * f0 * 1.0e9 / (1j * kB * temp * 0.001)).real - math.log(
            hbar * f0 * 1.0e9 / (kB * temp * 0.001))))  # TLS dominated f_resonance
    Qi_TLS = 1.0 / (
                FdeltaTLS * np.tanh(hbar * 2.0 * math.pi * f0 * 1.0e9 / (2.0 * kB * temp * 0.001)))  # TLS limited Qi
    return fR, Qi_TLS

# def fit_resonator_lambda(currents, f0s, f0errors):
#
# def fit_lambda(currents,
