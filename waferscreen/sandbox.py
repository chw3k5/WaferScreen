from waferscreen.scripts import sweep_to_find_resonances, check_out, band_sweeps
from waferscreen.scripts import acquire_tiny_sweeps, analyze_tiny_sweeps
from waferscreen.analyze.tiny_sweeps import TinySweeps
from ref import today_str


# for db in [-30, -20, -15, -10, 0, -40, -50]:
#     check_out(coax_path="Thru1_wZX60", temperature=300, port_power_dBm=db)

temperture_K = 0.093
wafer = 7
project = 'so'
band_list = [1]
run_number = 4
port_power = -30  # dBm

do_check_out = False
do_band_sweeps = False
do_tiny_sweeps = False
do_analyze_tiny_sweeps = True


if do_check_out:
    check_out_file = check_out(coax_path="loopA", temperature=temperture_K, fcenter_GHz=5, fspan_MHz=10000,
                               num_freq_points=20001, sweeptype='lin', if_bw_Hz=100, ifbw_track=False,
                               port_power_dBm=port_power, vna_avg=1, preset_vna=False, verbose=False)

if do_band_sweeps:
    band_sweeps(wafer=wafer, project=project, power_list=[port_power], band_list=band_list,
                if_bw_Hz=300, num_freq_points=10001,
                lower_extra_span_fraction=0.1, upper_extra_span_fraction=0.4, temperature_K=temperture_K,
                show_sweep_plot=True)

for band in band_list:
    if do_tiny_sweeps:
        acquire_tiny_sweeps(wafer=wafer, band_number=band, run_number=run_number, temperature_K=temperture_K,
                            port_pwer_dBm=port_power)

    if do_analyze_tiny_sweeps:
        ts = TinySweeps(wafer=7, band_number=band, date_str=today_str, run_number=run_number, auto_run=False, verbose=True)
        ts.eager_analyze()
        ts.plot()
