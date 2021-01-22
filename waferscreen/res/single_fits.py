import numpy as np
import math
import cmath
import scipy.special as specfunc
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter


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


def fit_resonator(freq_GHz, s21_complex, model='simple_res', error_est='prop'):
    """
    Function which returns fit parameters to a resonator model
    freq_GHzs are the measured freq_GHzuencies, s21data is the S21 data
    model selects which function to fit to
    error_est chooses your error estimation method, prop, const, etc...
    throw out tosses out the first and last N points
    """

    # guess base_amplitude_abs and a_phase_rad by looking at ends of data
    # number of data points on each end used to estimate A
    s21_complex = np.array([s21_complex, s21_complex])
    amplitude_est_range = np.min((10, int(np.round(len(freq_GHz * 0.5)))))
    amplitude_ave_low = np.mean(s21_complex)
    amplitude_ave_high = np.mean(s21_complex[-amplitude_est_range:, 0] + 1j * s21_complex[-amplitude_est_range, 1])

    Aave = 0.5 * (amplitude_ave_low + amplitude_ave_high)
    base_amplitude_abs_guess = np.abs(Aave)  # average of low and high magnitudes
    a_phase_rad_guess = np.arctan2(Aave[1], Aave[0])  # average of high and low phases

    # guess base_amplitude_slope and tau_ns by looking at difference in A_high and A_low
    delta_guess_index = int(round(amplitude_est_range / 2.0))
    delta_freq_GHz = freq_GHz[len(freq_GHz) - delta_guess_index] - freq_GHz[delta_guess_index]
    base_amplitude_slope_guess = (np.abs(amplitude_ave_high) - np.abs(amplitude_ave_low)) / delta_freq_GHz

    phase_high_guess = np.arctan2(amplitude_ave_high.imag, amplitude_ave_high.real)  # in radians
    phase_low_guess = np.arctan2(amplitude_ave_low.imag, amplitude_ave_low.real)  # in radians
    tau_ns_guess = (phase_low_guess - phase_high_guess) / (2.0 * math.pi * delta_freq_GHz)

    print('Fit Guesses')
    print('base_amplitude_abs   : %.4f' % base_amplitude_abs_guess)
    print('a_phase_rad : %.2f Deg' % a_phase_rad_guess)
    print('base_amplitude_slope : %.3f /GHz' % base_amplitude_slope_guess)
    print('tau_ns    : %.3f ns' % tau_ns_guess)

    # now make array of |s21|^2, remove baseline gain and slope
    guess_s21 = []
    f_mid = (freq_GHz[len(freq_GHz) - 1] + freq_GHz[0]) / 2.0
    for i in range(0, len(freq_GHz)):
        raw_s21 = s21_complex[i, 0] ** 2 + s21_complex[i, 1] ** 2
        guess_s21.append(raw_s21 / ((base_amplitude_abs_guess + base_amplitude_slope_guess * (
                    freq_GHz[i] - f_mid)) ** 2))  # normalize |s21|^2 using guesses for base_amplitude_abs and base_amplitude_slope

    # smooth s21 trace
    window_size, poly_order = 25, 3
    while len(guess_s21) < window_size:
        window_size -= 2
    guess_s21_filt = savgol_filter(guess_s21, window_size, poly_order)

    # guess f0
    s21_min = 1e15
    f0_guess = -1
    for i in range(0, len(freq_GHz)):  # find freq_GHz of minimum transmission
        fit_vec = s21_complex[i]
        if guess_s21_filt[i] < s21_min:
            s21_min = guess_s21_filt[i]
            f0_guess = freq_GHz[i]
    if f0_guess == -1:  # if this somehow fails, choose f_mid
        f0_guess = f_mid

    print('f0     : %.4f GHz' % f0_guess)

    # guess Qi and Qc by looking for FWHM (effective)
    s21_search = 0.5 * (1 + s21_min)  # = |s21|^2 at (1-(f/f0)^2) == Qt^-1
    # now find first point to have |S21|^2 < s21_search
    i = 0
    while guess_s21_filt[i] > s21_search and i < len(freq_GHz) - 1:
        i += 1
    f_lower = freq_GHz[i]
    # now find first point to have |S21|^2 < 0.5 * |A|^2 from above
    i = len(freq_GHz) - 1
    while guess_s21_filt[i] > s21_search and i >= 0:
        i -= 1
    f_upper = freq_GHz[i]
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
        Qt = f0_guess / (freq_GHz[len(freq_GHz) - 1] - freq_GHz[0])
        print("Error in Estimating Qtotal")
    if Qt < 1:
        Qt = 1
    if math.isnan(Qt):
        Qt = f0_guess / (freq_GHz[len(freq_GHz) - 1] - freq_GHz[0])
    Qi_guess = Qt / np.sqrt(s21_min)
    Qc_guess = 1.0 / (1.0 / Qt - 1.0 / Qi_guess)
    if math.isnan(Qi_guess):
        Qi_guess = f0_guess / (freq_GHz[len(freq_GHz) - 1] - freq_GHz[0])
        Qc_guess = f0_guess / (freq_GHz[len(freq_GHz) - 1] - freq_GHz[0])

    print('Qi     : %.0f' % Qi_guess)
    print('Qc     : %.0f' % Qc_guess)

    # use curve fit to for these params
    popt, pcov = single_res_fit(model=model, freq_GHz=freq_GHz,
                                s21_complex=s21_complex, error_est=error_est,
                                base_amplitude_abs_guess=base_amplitude_abs_guess, a_phase_rad_guess=a_phase_rad_guess,
                                f0_guess=f0_guess, Qi_guess=Qi_guess, Qc_guess=Qc_guess,
                                base_amplitude_slope_guess=base_amplitude_slope_guess, tau_ns_guess=tau_ns_guess)
    return popt, pcov


def est_error(freq_GHz, s21_complex, error_est='prop'):
    # estimate errors according to method est_errors
    error_params = []
    if error_est == 'prop':  # estimate errors are proportional to |S| or |Y|
        print('Using Proportional Errors')
        e11_min = 0.0
        for i in range(0, len(freq_GHz)):
            fit_vec = s21_complex[i]
            e1 = np.sqrt(fit_vec[0] ** 2 + fit_vec[1] ** 2) + e11_min
            error_vec = np.array([e1, e1])
            error_params.append(error_vec)
    elif error_est == 'flat':  # estimate errors are constant
        print('Using Flat Errors')
        for i in range(0, len(freq_GHz)):
            error_vec = np.array([1.0, 1.0])
            error_params.append(error_vec)
    else:
        raise KeyError('Error estimation method not recognized')
    return np.array(error_params)


def single_res_fit(model, freq_GHz, s21_complex, s21_linear_mag,
                   base_amplitude_abs_guess, a_phase_rad_guess, f0_guess, Qi_guess, Qc_guess,
                   base_amplitude_slope_guess=None, tau_ns_guess=None):
    y_data = (s21_complex.real, s21_complex.imag)
    # perform fit using optimize.curve_fit
    if model == 'simple_res':  # (base_amplitude_abs, a_phase_rad, tau_ns, f0, Qi, Qc)
        starting_vals = [base_amplitude_abs_guess, a_phase_rad_guess, 0, f0_guess, Qi_guess, Qc_guess]
        bounds = ((0, -360.0, -10, freq_GHz[0], 0, 0), (np.inf, 360.0, 10, freq_GHz[-1], np.inf, np.inf))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res, freq_GHz, y_data, p0=starting_vals, sigma=s21_linear_mag,
                               bounds=bounds)  # , max_nfev = 10000)
    elif model == 'simple_res_gain_slope':  # (base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc)
        starting_vals = [base_amplitude_abs_guess, a_phase_rad_guess, 0, 0, f0_guess, Qi_guess, Qc_guess]
        bounds = ((0, -360.0, -10, -10, freq_GHz[0], 0, 0), (np.inf, 360.0, 10, 10, freq_GHz[-1], np.inf, np.inf))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res_gain_slope, freq_GHz, y_data, p0=starting_vals, sigma=s21_linear_mag,
                               bounds=bounds)  # , max_nfev = 10000)
    elif model == 'simple_res_nonlinear_phase':  # (base_amplitude_abs, a_phase_rad, Pphase, tau_ns, f0, Qi, Qc)
        starting_vals = [base_amplitude_abs_guess, a_phase_rad_guess, 0, 0, f0_guess, Qi_guess, Qc_guess]
        bounds = ((0, -360.0, -10, -10, freq_GHz[0], 0, 0), (np.inf, 360.0, 10, 10, freq_GHz[-1], np.inf, np.inf))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res_nonlinear_phase, freq_GHz, y_data, p0=starting_vals,
                               sigma=s21_linear_mag, bounds=bounds)  # , max_nfev = 10000)
    elif model == 'simple_res_nonlinear_phase_gain_slope':  # (base_amplitude_abs, a_phase_rad, base_amplitude_slope, Pphase, tau_ns, f0, Qi, Qc)
        starting_vals = [base_amplitude_abs_guess, a_phase_rad_guess, 0, 0, 0, f0_guess, Qi_guess, Qc_guess]
        bounds = ((0, -360.0, -100, -10, -10, freq_GHz[0], 0, 0),
                  (np.inf, 360.0, 100, 10, 10, freq_GHz[-1], np.inf, np.inf))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res_nonlinear_phase_gain_slope, freq_GHz, y_data, p0=starting_vals,
                               sigma=s21_linear_mag, bounds=bounds)  # , max_nfev = 10000)
    elif model == 'tline_res':  # (base_amplitude_abs, a_phase_rad, tau_ns, f0, Qi, Qc, Z0ratio)
        starting_vals = [base_amplitude_abs_guess, a_phase_rad_guess, 0, f0_guess, Qi_guess, Qc_guess, 1]
        bounds = (
        (0, -360.0, -10, freq_GHz[0], 0, 0, 0.99), (np.inf, 360.0, 10, freq_GHz[-1], np.inf, np.inf, 1.01))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_tline_res, freq_GHz, y_data, p0=starting_vals, sigma=s21_linear_mag,
                               bounds=bounds)  # , max_nfev = 10000)
    elif model == 'tline_res_gain_slope':  # (base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Z0ratio)
        starting_vals = [base_amplitude_abs_guess, a_phase_rad_guess, 0, 0, f0_guess, Qi_guess, Qc_guess, 1]
        bounds = ((0, -360.0, -10, -10, freq_GHz[0], 0, 0, 0.99),
                  (np.inf, 360.0, 10, 10, freq_GHz[-1], np.inf, np.inf, 1.01))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_tline_res_gain_slope, freq_GHz, y_data, p0=starting_vals, sigma=s21_linear_mag,
                               bounds=bounds)  # , max_nfev = 10000)
    elif model == 'simple_res_gain_slope_renorm':  # (base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Z0new_real, Z0new_imag)
        starting_vals = [base_amplitude_abs_guess, a_phase_rad_guess, base_amplitude_slope_guess, tau_ns_guess, f0_guess, Qi_guess, Qc_guess, 50, 0]
        bounds = ((0, -360.0, -100, -100, freq_GHz[0], 0, 0, 0, -np.inf),
                  (np.inf, 360.0, 100, 100, freq_GHz[-1], np.inf, np.inf, np.inf, np.inf))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res_gain_slope_renorm, freq_GHz, y_data, p0=starting_vals,
                               sigma=s21_linear_mag, bounds=bounds)  # , max_nfev = 10000)
    elif model == 'simple_res_gain_slope_complex':  # (base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Zratio)
        starting_vals = [base_amplitude_abs_guess, a_phase_rad_guess, base_amplitude_slope_guess, tau_ns_guess, f0_guess, Qi_guess, Qc_guess, 0]
        bounds = ((0, -360.0, -1000, -100, freq_GHz.min(), 0, 0, -5.0),
                  (np.inf, 360.0, 1000, 100, freq_GHz.max(), np.inf, np.inf, 5.0))
        starting_vals = rebound_starting_vals(bounds, starting_vals)
        popt, pcov = curve_fit(fit_simple_res_gain_slope_complex, freq_GHz, y_data, p0=starting_vals,
                               sigma=s21_linear_mag, bounds=bounds)  # , max_nfev = 10000)
    else:
        raise KeyError('Fit model : ' + str(model) + ' not recognized')
    return popt, pcov


def fit_simple_res(freq_GHzs, base_amplitude_abs, a_phase_rad, tau_ns, f0, Qi, Qc):
    """Simple Lorentzian Resonator"""
    s21data = []
    for freq_GHz in freq_GHzs:
        s21 = simple_res_model(freq_GHz, base_amplitude_abs, a_phase_rad, tau_ns, f0, Qi, Qc)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_model(freq_GHz, base_amplitude_abs, a_phase_rad, tau_ns, f0, Qi, Qc):
    A = base_amplitude_abs * (math.cos(a_phase_rad) + 1j * math.sin(a_phase_rad))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq_GHz - f0) * 2.0 * math.pi * tau_ns)  # tau_ns in ns, freq_GHz in GHz
    s21 = A * phase_delay * (1 - (freq_GHz / f0) ** 2 + 1j / Qi) / (1 - (freq_GHz / f0) ** 2 + 1j / Qi + 1j / Qc)
    return s21


def fit_simple_res_gain_slope(freq_GHzs, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc):
    """Lorentzian Resonator w/ gain slope"""
    s21data = []
    for freq_GHz in freq_GHzs:
        s21 = simple_res_gain_slope_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_gain_slope_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc):
    A = base_amplitude_abs * (1 + base_amplitude_slope * (freq_GHz - f0)) * (
                math.cos(a_phase_rad) + 1j * math.sin(a_phase_rad))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq_GHz - f0) * 2.0 * math.pi * tau_ns)  # tau_ns in ns, freq_GHz in GHz
    s21 = A * phase_delay * (1 - (freq_GHz / f0) ** 2 + 1j / Qi) / (1 - (freq_GHz / f0) ** 2 + 1j / Qi + 1j / Qc)
    return s21


def fit_simple_res_nonlinear_phase(freq_GHzs, base_amplitude_abs, a_phase_rad, Pphase, tau_ns, f0, Qi, Qc):
    """Lorentzian Resonator w/ Non-linear Phase Response"""
    s21data = []
    for freq_GHz in freq_GHzs:
        s21 = simple_res_nonlinear_phase_model(freq_GHz, base_amplitude_abs, a_phase_rad, Pphase, tau_ns, f0, Qi, Qc)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_nonlinear_phase_model(freq_GHz, base_amplitude_abs, a_phase_rad, Pphase, tau_ns, f0, Qi, Qc):
    A = base_amplitude_abs * (math.cos(a_phase_rad) + 1j * math.sin(a_phase_rad))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq_GHz - f0) * 2.0 * math.pi * tau_ns)  # tau_ns in ns, freq_GHz in GHz
    s21 = A * phase_delay * (1 - (freq_GHz / f0) ** 2 + 1j / Qi) / (1 - (freq_GHz / f0) ** 2 + 1j / Qi + 1j / Qc)
    # additional phase delay due to power
    power_delay = np.exp(-1j * np.abs(s21) ** 2 / (base_amplitude_abs ** 2) * Pphase * math.pi / 180.0)
    return s21 * power_delay


def fit_simple_res_nonlinear_phase_gain_slope(freq_GHzs, base_amplitude_abs, a_phase_rad, base_amplitude_slope, Pphase, tau_ns, f0, Qi, Qc):
    """Lorentzian Resonator w/ Gain Slope and Non-linear Phase Response """
    s21data = []
    for freq_GHz in freq_GHzs:
        s21 = simple_res_nonlinear_phase_gain_slope_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, Pphase, tau_ns, f0, Qi, Qc)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_nonlinear_phase_gain_slope_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, Pphase, tau_ns, f0, Qi, Qc):
    A = base_amplitude_abs * (1 + base_amplitude_slope * (freq_GHz - f0)) * (
                math.cos(a_phase_rad) + 1j * math.sin(a_phase_rad))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq_GHz - f0) * 2.0 * math.pi * tau_ns)  # tau_ns in ns, freq_GHz in GHz
    s21 = A * phase_delay * (1 - (freq_GHz / f0) ** 2 + 1j / Qi) / (1 - (freq_GHz / f0) ** 2 + 1j / Qi + 1j / Qc)
    # additional phase delay due to power
    power_delay = np.exp(-1j * np.abs(s21) ** 2 / (base_amplitude_abs ** 2) * Pphase * math.pi / 180.0)
    return s21 * power_delay


def fit_tline_res(freq_GHzs, base_amplitude_abs, a_phase_rad, tau_ns, f0, Qi, Qc, Z0ratio):
    """Transmission line Resonator"""
    s21data = []
    for freq_GHz in freq_GHzs:
        s21 = tline_res_model(freq_GHz, base_amplitude_abs, a_phase_rad, tau_ns, f0, Qi, Qc, Z0ratio)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def tline_res_model(freq_GHz, base_amplitude_abs, a_phase_rad, tau_ns, f0, Qi, Qc, Z0ratio):
    A = base_amplitude_abs * (math.cos(a_phase_rad) + 1j * math.sin(a_phase_rad))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq_GHz - f0) * 2.0 * math.pi * tau_ns)  # tau_ns in ns, freq_GHz in GHz
    tan_mult_term = freq_GHz / f0 * np.sqrt((1.0 / Qc) * cmath.pi / 2 * Z0ratio * (1.0 - 1j * f0 / (freq_GHz * Qi)))
    tan_term = cmath.tan(freq_GHz / f0 * cmath.pi / 2 * np.sqrt(1.0 - 1j * f0 / (freq_GHz * Qi)))
    Qc_term = 0.5 * 1j * freq_GHz / f0 * np.sqrt(cmath.pi / (2 * Qc * Z0ratio))
    s21raw = (1.0 - tan_mult_term * tan_term) / (1.0 - tan_mult_term * tan_term + Qc_term)
    s21 = A * phase_delay * s21raw
    return s21


def fit_tline_res_gain_slope(freq_GHzs, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Z0ratio):
    """Transmission line Resonator w/ gain slope """
    s21data = []
    Z0ratio = 1
    for freq_GHz in freq_GHzs:
        s21 = tline_res_gain_slope_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Z0ratio)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def tline_res_gain_slope_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Z0ratio):
    A = base_amplitude_abs * (1 + base_amplitude_slope * (freq_GHz - f0)) * (
                math.cos(a_phase_rad) + 1j * math.sin(a_phase_rad))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq_GHz - f0) * 2.0 * math.pi * tau_ns)  # tau_ns in ns, freq_GHz in GHz
    tan_mult_term = freq_GHz / f0 * np.sqrt((1.0 / Qc) * cmath.pi / 2 * Z0ratio * (1.0 - 1j * f0 / (freq_GHz * Qi)))
    tan_term = cmath.tan(freq_GHz / f0 * cmath.pi / 2 * np.sqrt(1.0 - 1j * f0 / (freq_GHz * Qi)))
    Qc_term = 0.5 * 1j * freq_GHz / f0 * np.sqrt(cmath.pi / (2 * Qc * Z0ratio))
    s21raw = (1.0 - tan_mult_term * tan_term) / (1.0 - tan_mult_term * tan_term + Qc_term)
    s21 = A * phase_delay * s21raw
    return s21


def fit_simple_res_gain_slope_renorm(freq_GHzs, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Z0new_real, Z0new_imag):
    """Lorentzian Resonator w/ gain slope and impedance renormalization"""
    s21data = []
    for freq_GHz in freq_GHzs:
        s21 = simple_res_gain_slope_renorm_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Z0new_real, Z0new_imag)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data


def simple_res_gain_slope_renorm_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Z0new_real, Z0new_imag):
    A = base_amplitude_abs * (1 + base_amplitude_slope * (freq_GHz - f0)) * (
                math.cos(a_phase_rad) + 1j * math.sin(a_phase_rad))  # complex gain factor A
    phase_delay = np.exp(-1j * (freq_GHz - f0) * 2.0 * math.pi * tau_ns)  # tau_ns in ns, freq_GHz in GHz
    # shunt resonator model
    s11_temp = (-1j / Qc) / (1 - (freq_GHz / f0) ** 2 + 1j / Qi + 1j / Qc)
    s21_temp = (1 - (freq_GHz / f0) ** 2 + 1j / Qi) / (1 - (freq_GHz / f0) ** 2 + 1j / Qi + 1j / Qc)
    smat = [[s11_temp, s21_temp], [s21_temp, s11_temp]]
    new_smat = renormalize_smat(smat, 50, Z0new_real + 1j * Z0new_imag)
    s21 = A * phase_delay * new_smat[1, 0]
    return s21


def fit_simple_res_gain_slope_complex(freqs_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Zratio):
    """Lorentzian Resonator w/ gain slope and complex feedline impedance"""
    s21data = []
    for freq_GHz in freqs_GHz:
        s21 = simple_res_gain_slope_complex_model(freq_GHz, base_amplitude_abs, a_phase_rad, base_amplitude_slope, tau_ns, f0, Qi, Qc, Zratio)
        s21data.append(np.array([s21.real, s21.imag]))
    s21data = np.array(s21data).ravel()
    return s21data





def fit_resonator_mb_tls(temps, f0s, f0errors, Qi, Qierrors, temp_range=[0, np.inf]):
    """
    Code which takes fit results from temperature sweep data, and fits those results to a MB + TLS model
    for now just fit TLS to deltaFr
    """
    fit_temps = []
    s21_complex = []
    error_params = []
    for i in range(0, len(temps)):
        if temps[i] >= temp_range[0] and temps[i] <= temp_range[1]:
            fit_temps.append(temps[i])
            s21_complex.append(f0s[i])
            error_params.append(f0errors[i])
    fit_temps = np.array(fit_temps)
    s21_complex = np.array(s21_complex)
    error_params = np.array(error_params)

    starting_vals = [f0s[0], 1e-6]  # f0(T=0), FdeltaTLS
    print("F0 Guess:      " + str(f0s[0]))
    print("FtanD Guess  : " + str(1e-6))
    bounds = ((0, 0), (np.inf, np.inf))
    starting_vals = rebound_starting_vals(bounds, starting_vals)
    popt, pcov = curve_fit(fit_mb_tls, fit_temps, s21_complex, p0=starting_vals, sigma=error_params, bounds=bounds,
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
