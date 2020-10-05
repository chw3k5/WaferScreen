from waferscreen.scripts import sweep_to_find_resonances, check_out, band_sweeps, ResFit
from waferscreen.scripts import acquire_tiny_sweeps, analyze_tiny_sweeps
from waferscreen.analyze.tiny_sweeps import TinySweeps
from ref import today_str
from waferscreen.plot.s21 import plot_21


sweep_file = "D:\\waferscreen\\output\\s21\\8\\Band01\\2020-10-04\\8_Band01_2020-10-04_run1.csv"
res_fit = ResFit(file=sweep_file, group_delay=31.839, verbose=True, freq_units="GHz", auto_process=True)
plot_21(file=sweep_file, save=True, show=False, res_fit=res_fit)
