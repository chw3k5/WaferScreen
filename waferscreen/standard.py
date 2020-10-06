from waferscreen.plot.s21 import plot_21
from waferscreen.scripts import check_out, band_sweeps, acquire_tiny_sweeps
from waferscreen.analyze.tiny_sweeps import TinySweeps
from ref import today_str

"""
User Input Variables
"""
# for multiple scripts
temperature_K =0.095
wafer = 8
band_list = [1]
port_power_list = [-20, -50, -70]  # dBm

# for check_out script
check_out_coax_path = "InputB_1coldAmp_2warm"

# for band_sweeps script
lower_extra_span_fraction = 0.5
upper_extra_span_fraction = 0.0

# for tiny_sweeps scripts
run_number = 4

# for plot_plot_tiny_sweeps
redo_lambda = True

"""
Toggle Script Variables
"""
do_check_out = False
do_band_sweeps = False
do_tiny_sweeps = False
do_analyze_tiny_sweeps = True
plot_tiny_sweeps = True

"""
The Scripts
"""
if __name__ == '__main__':
    if do_check_out:
        check_out_file = check_out(coax_path=check_out_coax_path, temperature=temperature_K, fcenter_GHz=5, fspan_MHz=10000,
                                   num_freq_points=100001, sweeptype='lin', if_bw_Hz=30, ifbw_track=False,
                                   port_power_dBm=port_power_list[0], vna_avg=1, preset_vna=False, verbose=False)


    if do_band_sweeps:
        band_sweeps(wafer=wafer, project='so', power_list=port_power_list[0], band_list=band_list,
                    if_bw_Hz=100, num_freq_points=10001,
                    lower_extra_span_fraction=lower_extra_span_fraction,
                    upper_extra_span_fraction=upper_extra_span_fraction, temperature_K=temperature_K,
                    show_sweep_plot=True)

    for port_power in port_power_list:
        for band in band_list:
            if do_tiny_sweeps:
                acquire_tiny_sweeps(wafer=wafer, band_number=band, run_number=run_number, temperature_K=temperature_K,
                                    port_pwer_dBm=port_power)

            if any((do_analyze_tiny_sweeps, plot_tiny_sweeps)):
                ts = TinySweeps(wafer=wafer, band_number=band, date_str='2020-10-04', run_number=run_number,
                                auto_run=False, verbose=True)
                if do_analyze_tiny_sweeps:
                    ts.eager_analyze()
                if plot_tiny_sweeps:
                    ts.plot(redo_lambda=redo_lambda)
