"""
Look at long-term trends in screening parameters (i.e. temperature, RF power) and more interestingly
in the measured umux chip parameters

Assumes that all the high_level_data.pkl files from generate_wafer_report.py are in a single directory
Beware that, for example, wafer 16 required finnesse due to the number of chips that were screened.
Maybe easiest to get files if they already exist and copy them?  Ask John in any case

John Groh, January 2022
"""

import numpy as np
import matplotlib.pyplot as plt
import pickle as pkl
import glob
import os

# change these as appropriate depending on the machine you're running on
report_master_dir = "C:\\Users\\jcg12\\SO_screening\\wafer_reports\\"
summary_files = glob.glob(os.path.join(report_master_dir, "*\\high_level_data.pkl"))
plot_dir = "..\\plots\\fab_trends\\"

# first, just grab the list of wafers screened
wafers = []
for summary_file in summary_files:
    with open(summary_file, 'rb') as f:
        summary = pkl.load(f, encoding='latin1')
        wafers.append(summary['wafer'])
        
# make a plot of Qi trends over time
q25 = [] # 25th percentile
q50 = [] # median
q75 = [] # 75th percentile
for summary_file in summary_files:
    with open(summary_file, 'rb') as f:
        summary = pkl.load(f, encoding='latin1')
        q25.append(summary['quartiles']['Qi'][0])
        q50.append(summary['quartiles']['Qi'][1])
        q75.append(summary['quartiles']['Qi'][2])
fig, ax = plt.subplots(figsize=(10,6))
ax.plot(q50, 'k.-', label='median')
ax.fill_between(x=range(len(wafers)), y1=q25, y2=q75, color='k', alpha=0.5, label='interquartile range')
ax.set_ylabel('$Q_i$')
ax.set_xticks(range(len(wafers)))
ax.set_xticklabels([f"Wafer {w:02d}" for w in wafers], rotation=45, ha='right')
ax.legend()
fig.savefig(os.path.join(plot_dir, 'trend_Qi.png'))

# make a plot of lambda trends over time
q25 = [] # 25th percentile
q50 = [] # median
q75 = [] # 75th percentile
for summary_file in summary_files:
    with open(summary_file, 'rb') as f:
        summary = pkl.load(f, encoding='latin1')
        q25.append(summary['quartiles']['lambda'][0])
        q50.append(summary['quartiles']['lambda'][1])
        q75.append(summary['quartiles']['lambda'][2])
fig, ax = plt.subplots(figsize=(10,6))
ax.plot(q50, 'k.-', label='median')
ax.fill_between(x=range(len(wafers)), y1=q25, y2=q75, color='k', alpha=0.5, label='interquartile range')
ax.set_ylabel('$\lambda_{SQUID}$')
ax.set_xticks(range(len(wafers)))
ax.set_xticklabels([f"Wafer {w:02d}" for w in wafers], rotation=45, ha='right')
ax.legend()
fig.savefig(os.path.join(plot_dir, 'trend_lambda.png'))


# make a plot of dfpp trends over time
q25 = [] # 25th percentile
q50 = [] # median
q75 = [] # 75th percentile
for summary_file in summary_files:
    with open(summary_file, 'rb') as f:
        summary = pkl.load(f, encoding='latin1')
        q25.append(summary['quartiles']['dfpp'][0]*1.e6)
        q50.append(summary['quartiles']['dfpp'][1]*1.e6)
        q75.append(summary['quartiles']['dfpp'][2]*1.e6)
fig, ax = plt.subplots(figsize=(10,6))
ax.plot(q50, 'k.-', label='median')
ax.fill_between(x=range(len(wafers)), y1=q25, y2=q75, color='k', alpha=0.5, label='interquartile range')
ax.set_ylabel('$\Delta f_{p2p}$ [kHz]')
ax.set_xticks(range(len(wafers)))
ax.set_xticklabels([f"Wafer {w:02d}" for w in wafers], rotation=45, ha='right')
ax.legend()
fig.savefig(os.path.join(plot_dir, 'trend_dfpp.png'))

# make a plot of BW trends over time
q25 = [] # 25th percentile
q50 = [] # median
q75 = [] # 75th percentile
for summary_file in summary_files:
    with open(summary_file, 'rb') as f:
        summary = pkl.load(f, encoding='latin1')
        q25.append(summary['quartiles']['BW'][0]*1.e6)
        q50.append(summary['quartiles']['BW'][1]*1.e6)
        q75.append(summary['quartiles']['BW'][2]*1.e6)
fig, ax = plt.subplots(figsize=(10,6))
ax.plot(q50, 'k.-', label='median')
ax.fill_between(x=range(len(wafers)), y1=q25, y2=q75, color='k', alpha=0.5, label='interquartile range')
ax.set_ylabel('Resonator bandwidth [kHz]')
ax.set_xticks(range(len(wafers)))
ax.set_xticklabels([f"Wafer {w:02d}" for w in wafers], rotation=45, ha='right')
ax.legend()
fig.savefig(os.path.join(plot_dir, 'trend_BW.png'))

# make a plot of pairwise spacing trends over time
q25 = [] # 25th percentile
q50 = [] # median
q75 = [] # 75th percentile
for summary_file in summary_files:
    with open(summary_file, 'rb') as f:
        summary = pkl.load(f, encoding='latin1')
        q25.append(summary['quartiles']['delta_f'][0]*1.e3)
        q50.append(summary['quartiles']['delta_f'][1]*1.e3)
        q75.append(summary['quartiles']['delta_f'][2]*1.e3)
fig, ax = plt.subplots(figsize=(10,6))
ax.plot(q50, 'k.-', label='median')
ax.fill_between(x=range(len(wafers)), y1=q25, y2=q75, color='k', alpha=0.5, label='interquartile range')
ax.set_ylabel('Pairwise channel spacing [MHz]')
ax.set_xticks(range(len(wafers)))
ax.set_xticklabels([f"Wafer {w:02d}" for w in wafers], rotation=45, ha='right')
ax.legend()
fig.savefig(os.path.join(plot_dir, 'trend_pairwise_spacing.png'))


# absolute frequency placement accuracy
fig, ax = plt.subplots(figsize=(10,6))
for i, summary_file in enumerate(summary_files):
    with open(summary_file, 'rb') as f:
        summary = pkl.load(f, encoding='latin1')
    for upper in summary['upper_band_edge_errors']:
        if i == 0 and upper == summary['upper_band_edge_errors'][0]:
            ax.plot(i, upper*1.e-6, 'r.', label='upper edge', alpha=0.5)
        else:
            ax.plot(i, upper*1.e-6, 'r.', alpha=0.5)
    for lower in summary['lower_band_edge_errors']:
        if i == 0 and lower == summary['lower_band_edge_errors'][0]:
            ax.plot(i, lower*1.e-6, 'b.', label='lower edge', alpha=0.5)
        else:
            ax.plot(i, lower*1.e-6, 'b.', alpha=0.5)
ax.set_ylabel('Absolute frequency error of band edges [MHz]')
ax.set_xticks(range(len(wafers)))
ax.set_xticklabels([f"Wafer {w:02d}" for w in wafers], rotation=45, ha='right')
ax.legend()
ax.axhline(0, linestyle='--', color='k')
fig.savefig(os.path.join(plot_dir, 'trend_in_absolute_placement.png'))

# yield estimate
yields = []
for i, summary_file in enumerate(summary_files):
    with open(summary_file, 'rb') as f:
        summary = pkl.load(f, encoding='latin1')
    yield_estimate = summary['yield']['all_cuts'] / summary['yield']['max_possible']
    yields.append(yield_estimate*100)
fig, ax = plt.subplots(figsize=(10,6))
ax.plot(yields, 'ko')
ax.set_ylabel('Estimated yield of usable channels [percent]')
ax.set_xticks(range(len(wafers)))
ax.grid(axis='y')
ax.set_xticklabels([f"Wafer {w:02d}" for w in wafers], rotation=45, ha='right')
fig.savefig(os.path.join(plot_dir, 'trend_in_yield.png'))



# screening temperatures and powers at resonators
fig, ax = plt.subplots(nrows=3, ncols=1, sharex=True, figsize=(8,8))
for i, summary_file in enumerate(summary_files):
    with open(summary_file, 'rb') as f:
        summary = pkl.load(f, encoding='latin1')
    unique_temps = np.unique(summary['temperature_mK'])
    unique_attenuations = np.unique(summary['attenuation'])
    unique_sweep_powers = np.unique(summary['sweep_power'])
    unique_lambda_powers = np.unique(summary['lambda_power'])
    for t in unique_temps:
        ax[0].plot(i, t, 'ko')
    # this could easily fail - watch out.  Naive assumption that they're all the same length
    for a, s, l in zip(unique_attenuations, unique_sweep_powers, unique_lambda_powers):
        sweep_power_at_res = s + a
        lambda_power_at_res = l + a
        ax[1].plot(i, sweep_power_at_res, 'ko')
        ax[2].plot(i, lambda_power_at_res, 'ko')
ax[2].set_xticks(range(len(wafers)))
ax[2].set_xticklabels([f"Wafer {w:02d}" for w in wafers], rotation=45, ha='right')
ax[0].set_ylabel('Screening temperature [mK]')
ax[1].set_ylabel('Power used for everything\nbut $\lambda$ [dBm at resonators]')
ax[2].set_ylabel('Power used\nfor $\lambda$ [dBm at resonators]')
plt.tight_layout()
fig.savefig(os.path.join(plot_dir, 'screening_parameter_trends.png'))
        
plt.show()


