from waferscreen.scripts import sweep_to_find_resonances
from waferscreen.analyze.find_and_fit import ResFit


sweep_file = sweep_to_find_resonances(project='so', wafer="7", trace_number=0,
                                      fcenter_GHz=4.10, fspan_MHz=200, num_freq_points=100001, sweeptype='lin',
                                      if_bw_Hz=1000,
                                      ifbw_track=False, port_power_dBm=-40, vna_avg=1,)
res_fit = ResFit(file=sweep_file,
                 group_delay=31.839, verbose=True, freq_units="GHz", auto_process=True)
sweep_file = sweep_to_find_resonances(project='so', wafer="6", trace_number=2,
                                      fcenter_GHz=4.350, fspan_MHz=200, num_freq_points=100001, sweeptype='lin',
                                      if_bw_Hz=1000,
                                      ifbw_track=False, port_power_dBm=-40, vna_avg=1,)
res_fit = ResFit(file=sweep_file, group_delay=31.839, verbose=True, freq_units="GHz", auto_process=True)
