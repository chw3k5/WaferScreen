import os
import numpy as np
from ref import s21_dir, today_str, check_out_dir, band_params
from waferscreen.plot.s21 import plot_21
from waferscreen.measure.res_sweep import VnaMeas
from waferscreen.analyze.find_and_fit import ResFit
from waferscreen.analyze.tiny_sweeps import TinySweeps


def calc_band_edges(min_GHz, max_GHz, center_GHz,
                    lower_extra_span_fraction=0.1, upper_extra_span_fraction=0.1, return_span_center=False):
    lower_edge = center_GHz - ((center_GHz - min_GHz) * (1.0 + lower_extra_span_fraction))
    upper_edge = center_GHz + ((max_GHz - center_GHz) * (1.0 + upper_extra_span_fraction))
    if return_span_center:
        return (upper_edge - lower_edge), ((upper_edge + lower_edge) * 0.5)
    else:
        return lower_edge, upper_edge


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

    sweep_dir = os.path.join(s21_dir, project.lower())
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

        res_fit = ResFit(file=sweep_file,
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
