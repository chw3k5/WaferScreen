from waferscreen.scripts import sweep_to_find_resonances, check_out, band_sweeps, acquire_tiny_sweeps


# for db in [-30, -20, -15, -10, 0, -40, -50]:
#     check_out(coax_path="Thru1_wZX60", temperature=300, port_power_dBm=db)

temperture_K = 0.140
wafer = 7
project = 'so'
# band_sweeps(wafer=wafer, project=project, power_list=[-30], band_list=1,
#             lower_extra_span_fraction=0.2, upper_extra_span_fraction=0.5, temperature_K=temperture_K)

acquire_tiny_sweeps(wafer=wafer, band_number=1, run_number=5, temperature_K=temperture_K, port_pwer_dBm=-30)
