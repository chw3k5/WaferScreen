from waferscreen.scripts import sweep_to_find_resonances, check_out, band_sweeps
from waferscreen.scripts import acquire_tiny_sweeps, analyze_tiny_sweeps
from waferscreen.analyze.tiny_sweeps import TinySweeps


# for db in [-30, -20, -15, -10, 0, -40, -50]:
#     check_out(coax_path="Thru1_wZX60", temperature=300, port_power_dBm=db)

temperture_K = 1.8
wafer = 7
project = 'so'
band_list = [1]
do_band_sweeps = False
do_tiny_sweeps = True
do_analyze_tiny_sweeps = False


if do_band_sweeps:
    band_sweeps(wafer=wafer, project=project, power_list=[-30], band_list=band_list,
                if_bw_Hz=300, num_freq_points=10001,
                lower_extra_span_fraction=0.0, upper_extra_span_fraction=0.3, temperature_K=temperture_K,
                show_sweep_plot=True)

if do_tiny_sweeps:
    for band in band_list:
        acquire_tiny_sweeps(wafer=wafer, band_number=band, run_number=8, temperature_K=temperture_K, port_pwer_dBm=-30)

if do_analyze_tiny_sweeps:
    ts = TinySweeps(wafer=7, band_number=1, date_str="2020-09-08", run_number=-1, auto_run=False, verbose=True)
    ts.plot()