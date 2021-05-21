import pandas
import ref
import matplotlib.pyplot as plt
from matplotlib import cm
from waferscreen.mc.explore import LambExplore


device_records_cvs_path = LambExplore.device_records_cvs_path
device_stats_cvs_path = LambExplore.device_stats_cvs_path

device_records = pandas.read_csv(filepath_or_buffer=device_records_cvs_path, index_col=0)
designed_f_ghz = device_records.designed_f_ghz
measured_f_ghz = device_records.f_ghz
wafer_numbers = device_records.wafer

fig = plt.figure(figsize=(25, 10))
wafer_num_to_color = {9: "seagreen", 11: "crimson", 12: "darkgoldenrod", 13: "deepskyblue", 14: "mediumblue",
                      15: "rebeccapurple"}
coor = [0.05, 0.05, 0.9, 0.9]
ax = fig.add_axes(coor, frameon=False)
design_offset_mhz = []
design_values = []
wafer_numbers_plot = []
for m_f_ghz, d_f_ghz, wafer_num in zip(measured_f_ghz, designed_f_ghz, wafer_numbers):
    try:
        d_f_ghz = float(d_f_ghz)
    except ValueError:
        pass
    else:
        design_offset_mhz.append((m_f_ghz - d_f_ghz) * 1.0e3)
        design_values.append(d_f_ghz)
        wafer_numbers_plot.append(wafer_num_to_color[wafer_num])
ax.scatter(design_values, design_offset_mhz, c=wafer_numbers_plot)
leglabels = []
leglines = []
for wafer_num in sorted(wafer_num_to_color.keys()):
    leglabels.append(F"Wafer{'%03i' % wafer_num}")
    leglines.append(plt.Line2D(range(10), range(10), color=wafer_num_to_color[wafer_num], ls='None',
                               marker='o', markersize=10, markerfacecolor=wafer_num_to_color[wafer_num], alpha=1.0))
ax.legend(leglines, leglabels, loc=0, numpoints=5, handlelength=3, fontsize=10)
ax.set_ylabel('Measured - Designed (MHz)')
ax.set_xlabel('Designed Frequency (GHz)')
plt.show(block=True)
