from waferscreen.scripts import sweep_to_find_resonances, check_out, band_sweeps


# for db in [-30, -20, -15, -10, 0, -40, -50]:
#     check_out(coax_path="Thru1_wZX60", temperature=300, port_power_dBm=db)


band_sweeps(wafer=7, project="so", power_list=[-30, -20], band_list=1,
            lower_extra_span_fraction=0.2, upper_extra_span_fraction=0.5)

# acquire_tiny_sweeps(wafer=7, band_number=1, run_number=1, port_pwer_dBm=-30)