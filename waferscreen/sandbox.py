from waferscreen.scripts import sweep_to_find_resonances, check_out, band_sweeps
from waferscreen.scripts import acquire_tiny_sweeps, analyze_tiny_sweeps


# for db in [-30, -20, -15, -10, 0, -40, -50]:
#     check_out(coax_path="Thru1_wZX60", temperature=300, port_power_dBm=db)

temperture_K = 0.205
wafer = 7
project = 'so'
band_list = [2]
do_band_sweeps = False
do_tiny_sweeps = True


if do_band_sweeps:
    band_sweeps(wafer=wafer, project=project, power_list=[-30], band_list=band_list,
                lower_extra_span_fraction=0.0, upper_extra_span_fraction=0.3, temperature_K=temperture_K)

if do_tiny_sweeps:
    for band in band_list:
        acquire_tiny_sweeps(wafer=wafer, band_number=band, run_number=2, temperature_K=temperture_K, port_pwer_dBm=-30)
