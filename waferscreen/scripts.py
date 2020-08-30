import os
from ref import s21_dir, today_str
from waferscreen.measure.res_sweep import VnaMeas


def sweep_to_find_resonances(project, wafer, trace_number,
                             fcenter_GHz=4.15, fspan_MHz=300, num_freq_points=20001, sweeptype='lin', if_bw_Hz=100,
                             ifbw_track=False, port_power_dBm=-30, vna_avg=1, preset_vna=False,
                             show_plot=True, verbose=False):
    sweep_dir = os.path.join(s21_dir, project.lower())
    if not os.path.isdir(sweep_dir):
        os.mkdir(sweep_dir)

    sweep_base_name = F"{wafer}_Trace{str(trace_number)}_{today_str}_run"
    run_number = 1
    while os.path.isfile(os.path.join(sweep_dir, sweep_base_name + str(run_number) + '.csv')):
        run_number += 1
    vna_meas = VnaMeas(fcenter_GHz=fcenter_GHz, fspan_MHz=fspan_MHz, num_freq_points=num_freq_points,
                       sweeptype=sweeptype, if_bw_Hz=if_bw_Hz,
                       ifbw_track=ifbw_track, port_power_dBm=port_power_dBm, vna_avg=vna_avg, preset_vna=preset_vna,
                       output_filename=os.path.join(sweep_dir, sweep_base_name + str(run_number)),
                       auto_init=True,
                       verbose=verbose)
    vna_meas.vna_sweep()
    vna_meas.write_sweep(file_extension='csv')
    if show_plot:
        vna_meas.plot_sweep()
    return vna_meas.last_output_file


def acquire_tiny_sweeps():

    return
