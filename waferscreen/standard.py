from waferscreen.plot.s21 import plot_21
from waferscreen.scripts import check_out, band_sweeps, acquire_tiny_sweeps
from waferscreen.analyze.tiny_sweeps import TinySweeps
from ref import today_str

"""
User Input Variables
"""
# for multiple scripts
temperature_K = 0.093
wafer = 7
band_list = [1]
port_power = -30  # dBm

# for check_out script
check_out_coax_path = "LoopA"

# for band_sweeps script
lower_extra_span_fraction = 0.1
upper_extra_span_fraction = 0.4

# for tiny_sweeps scripts
run_number = 4


"""
Toggle Script Variables
"""
do_check_out = True
do_band_sweeps = False
do_tiny_sweeps = False
do_analyze_tiny_sweeps = False

"""
The Scripts
"""
if do_check_out:
    check_out_file = check_out(coax_path=check_out_coax_path, temperature=temperature_K, fcenter_GHz=5, fspan_MHz=10000,
                               num_freq_points=20001, sweeptype='lin', if_bw_Hz=100, ifbw_track=False,
                               port_power_dBm=port_power, vna_avg=1, preset_vna=False, verbose=False)
    plot_21(file=check_out_file)


if do_band_sweeps:
    band_sweeps(wafer=wafer, project='so', power_list=[port_power], band_list=band_list,
                if_bw_Hz=300, num_freq_points=10001,
                lower_extra_span_fraction=lower_extra_span_fraction,
                upper_extra_span_fraction=upper_extra_span_fraction, temperature_K=temperature_K,
                show_sweep_plot=True)

for band in band_list:
    if do_tiny_sweeps:
        acquire_tiny_sweeps(wafer=wafer, band_number=band, run_number=run_number, temperature_K=temperature_K,
                            port_pwer_dBm=port_power)

    if do_analyze_tiny_sweeps:
        ts = TinySweeps(wafer=7, band_number=band, date_str=today_str, run_number=run_number, auto_run=False,
                        verbose=True)
        ts.eager_analyze()
        ts.plot()
