import os
import numpy as np
from scipy.signal import savgol_filter
from ref import raw_data_dir, today_str, check_out_dir, band_params
from waferscreen.plot.s21_plots import plot_21
from waferscreen.measure.res_sweep import VnaMeas
from waferscreen.res.finder import ResFinder
from waferscreen.tiny_sweeps import TinySweeps
from waferscreen.tools.band_calc import calc_band_edges


def sweep_to_find_resonances(project, wafer, temperature_K=300,
                             fcenter_GHz=None, fspan_GHz=None, num_freq_points=20001, sweeptype='lin', if_bw_Hz=100,
                             ifbw_track=False, port_power_dBm=-30, vna_avg=1, preset_vna=False,
                             band=None, lower_extra_span_fraction=0.1, upper_extra_span_fraction=0.1,
                             show_plot=False, verbose=True):
    if band is not None:
        if isinstance(band, int):
            band = F"Band{'%02i' % band}"
        fspan_GHz, fcenter_GHz = calc_band_edges(min_GHz=band_params[band]["min_GHz"], max_GHz=band_params[band]["max_GHz"],
                                                 center_GHz=band_params[band]["center_GHz"],
                                                 lower_extra_span_fraction=lower_extra_span_fraction,
                                                 upper_extra_span_fraction=upper_extra_span_fraction,
                                                 return_span_center=True)
        # keep the number of frequency points in-band constant, no matter how much the extra_span_fraction
        num_freq_points = int(np.round(num_freq_points * (
                    1.0 + (lower_extra_span_fraction + upper_extra_span_fraction) * 0.5)))
    else:
        band = "BandNone"

    sweep_dir = os.path.join(raw_data_dir, project.lower())
    if not os.path.isdir(sweep_dir):
        os.mkdir(sweep_dir)

    sweep_base_name = F"{wafer}_{band}_{today_str}_run"
    run_number = 1
    while os.path.isfile(os.path.join(sweep_dir, sweep_base_name + str(run_number) + '.csv')):
        run_number += 1
    vna_meas = VnaMeas(fcenter_GHz=fcenter_GHz, fspan_MHz=fspan_GHz * 1000.0, num_freq_points=num_freq_points,
                       sweeptype=sweeptype, if_bw_Hz=if_bw_Hz,
                       ifbw_track=ifbw_track, port_power_dBm=port_power_dBm, vna_avg=vna_avg, preset_vna=preset_vna,
                       output_filename=os.path.join(sweep_dir, sweep_base_name + str(run_number)),
                       auto_init=True,
                       verbose=verbose, temperature_K=temperature_K)
    vna_meas.vna_sweep()
    vna_meas.write_sweep(file_extension='csv')
    if show_plot:
        vna_meas.plot_sweep()
    return vna_meas.last_output_file


def check_out(coax_path, temperature=300, fcenter_GHz=10, fspan_MHz=20000, num_freq_points=100001, sweeptype='lin',
              if_bw_Hz=1000, ifbw_track=False, port_power_dBm=-30, vna_avg=1, preset_vna=False, verbose=False):

    sweep_base_name = F"{coax_path}_Trace{str(temperature)}K_{today_str}_run"
    run_number = 1
    while os.path.isfile(os.path.join(check_out_dir, sweep_base_name + str(run_number) + '.csv')):
        run_number += 1
    vna_meas = VnaMeas(fcenter_GHz=fcenter_GHz, fspan_MHz=fspan_MHz, num_freq_points=num_freq_points,
                       sweeptype=sweeptype, if_bw_Hz=if_bw_Hz,
                       ifbw_track=ifbw_track, port_power_dBm=port_power_dBm, vna_avg=vna_avg, preset_vna=preset_vna,
                       output_filename=os.path.join(check_out_dir, sweep_base_name + str(run_number)),
                       auto_init=True,
                       verbose=verbose)
    vna_meas.vna_sweep()
    vna_meas.write_sweep(file_extension='csv')
    return vna_meas.last_output_file


def band_sweeps(wafer, project="so", power_list=-30, band_list=None, num_freq_points=100001, if_bw_Hz=100,
                lower_extra_span_fraction=0.1, upper_extra_span_fraction=0.1, temperature_K=300,
                show_sweep_plot=False):
    if band_list is None:
        band_list = ["BandNone"]
    elif isinstance(band_list, (int, float, str)):
        band_list = [band_list]
    if isinstance(power_list, (int, float, str)):
        power_list = [power_list]
    sweeps_params = []
    for band in list(band_list):
        for power in list(power_list):
            sweeps_params.append((power, band))
    res_fits = []
    for port_power_dBm, band in sweeps_params:
        sweep_file = sweep_to_find_resonances(project=project, wafer=wafer,
                                              fcenter_GHz=None, fspan_GHz=None, num_freq_points=num_freq_points,
                                              sweeptype='lin', if_bw_Hz=if_bw_Hz,
                                              band=band, lower_extra_span_fraction=lower_extra_span_fraction,
                                              upper_extra_span_fraction=upper_extra_span_fraction,
                                              ifbw_track=False, port_power_dBm=port_power_dBm, vna_avg=1,
                                              temperature_K=temperature_K, show_plot=show_sweep_plot)

        res_fit = ResFinder(file=sweep_file,
                            group_delay=31.839, verbose=True, freq_units="GHz", auto_process=True)
        plot_21(file=sweep_file, save=True, show=False, res_fit=res_fit)
        res_fits.append(res_fit)
    return res_fits


def acquire_tiny_sweeps(wafer, band_number=None, run_number=1, port_pwer_dBm=-40, temperature_K=300):
    if band_number is None:
        band_number = "BandNone"
    TinySweeps(wafer=wafer, band_number=band_number, run_number=run_number, port_power_dBm=port_pwer_dBm,
               temperature_K=temperature_K, auto_run=True, verbose=True)
    return


def analyze_tiny_sweeps(wafer, band_number=None):
    ts = TinySweeps(wafer=wafer, band_number=band_number, run_number=-1, auto_run=False, verbose=True)
    ts.analyze_all()
    return


def jakes_prep(freqs, sdata, group_delay_ns, edge_search_depth, remove_baseline_ripple,
               baseline_scale_kHz, smoothing_scale_kHz, baseline_order, smoothing_order, verbose=False):
    # now remove given group delay and make sure sdata is array
    phase_factors = np.exp(-1j * 2.0 * np.pi * freqs * group_delay_ns)  # e^(-j*w*t)
    sdata = np.array(sdata) / phase_factors

    if verbose:
        print("Removed Group Delay")

    # figure out complex gain and gain slope
    ave_left_gain = 0
    ave_right_gain = 0
    for j in range(0, edge_search_depth):
        ave_left_gain = ave_left_gain + sdata[j] / edge_search_depth
        ave_right_gain = ave_right_gain + sdata[len(sdata) - 1 - j] / edge_search_depth
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
    sdata = sdata / gains

    if verbose:
        print("Removed Group Delay and Gain")
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
        baseline_real = savgol_filter(np.real(sdata), baseline_scale, baseline_order)
        baseline_imag = savgol_filter(np.imag(sdata), baseline_scale, baseline_order)
        baseline = np.array(baseline_real + 1j * baseline_imag)
        pre_baseline_removal_sdata = np.copy(sdata)
        sdata = sdata / baseline

    # figure out freq spacing, convert smoothing_scale_kHz to smoothing_scale (must be an odd number)
    freq_spacing = (freqs[1] - freqs[0]) * 1e6  # GHz -> kHz
    smoothing_scale = int(round(smoothing_scale_kHz / freq_spacing))
    if smoothing_scale % 2 == 0:  # if even
        smoothing_scale = smoothing_scale + 1  # make it odd
    if smoothing_scale >= smoothing_order:
        smoothing_order = smoothing_scale - 1
    if verbose:
        print("Freq Spacing is " + str(freq_spacing) + "kHz")
        print("Requested smoothing scale is " + str(smoothing_scale_kHz) + "kHz")
        print("Number of points to smooth over is " + str(smoothing_scale))
    # smooth s21 trace in both real and imaginary to do peak finding
    sdata_smooth_real = savgol_filter(np.real(sdata), smoothing_scale, smoothing_order)
    sdata_smooth_imag = savgol_filter(np.imag(sdata), smoothing_scale, smoothing_order)
    sdata_smooth = np.array(sdata_smooth_real + 1j * sdata_smooth_imag)
    return sdata_smooth
