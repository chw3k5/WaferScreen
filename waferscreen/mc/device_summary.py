import pandas
import ref
import matplotlib.pyplot as plt
from matplotlib import cm
from waferscreen.mc.explore import LambExplore

wafer_num_to_color_dict = {9: "seagreen", 11: "crimson", 12: "darkgoldenrod", 13: "deepskyblue", 14: "mediumblue",
                           15: "rebeccapurple"}


def wafer_num_to_color(wafer_num):
    wafer_num = int(wafer_num)
    if wafer_num in wafer_num_to_color_dict.keys():
        return wafer_num_to_color_dict[wafer_num]
    return 'black'


device_records_cvs_path = LambExplore.device_records_cvs_path
device_stats_cvs_path = LambExplore.device_stats_cvs_path

device_records = pandas.read_csv(filepath_or_buffer=device_records_cvs_path, index_col=0)
f_design_f_meas = device_records[["f_ghz", "designed_f_ghz", "wafer"]]
f_design_f_meas['delta_f_mhz'] = f_design_f_meas['f_ghz'].sub(f_design_f_meas['designed_f_ghz']).mul(1.0e3)
f_design_f_meas['wafer_color'] = f_design_f_meas['wafer'].map(wafer_num_to_color, na_action='ignore')

designed_f_ghz = device_records.designed_f_ghz
measured_f_ghz = device_records.f_ghz
wafer_numbers = device_records.wafer

fig = plt.figure(figsize=(25, 10))
coor = [0.05, 0.05, 0.9, 0.9]
ax = fig.add_axes(coor, frameon=False)
ax.scatter(f_design_f_meas['designed_f_ghz'], f_design_f_meas['delta_f_mhz'], c=f_design_f_meas['wafer_color'])
leglabels = []
leglines = []
for wafer_num in sorted(wafer_num_to_color_dict.keys()):
    leglabels.append(F"Wafer{'%03i' % wafer_num}")
    leglines.append(plt.Line2D(range(10), range(10), color=wafer_num_to_color_dict[wafer_num], ls='None',
                               marker='o', markersize=10, markerfacecolor=wafer_num_to_color_dict[wafer_num],
                               alpha=1.0))
ax.legend(leglines, leglabels, loc=0, numpoints=5, handlelength=3, fontsize=10)
ax.set_ylabel('Measured - Designed (MHz)')
ax.set_xlabel('Designed Frequency (GHz)')
plt.show(block=True)
