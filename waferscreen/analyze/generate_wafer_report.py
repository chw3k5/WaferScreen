"""
Looking at Zach's screening summary files (S21 sweeps and a single file w/ resonator fit data),
auto-generate the following:
- plots and heatmaps summarizing parameters of interest
- a pickle file of high-level summary data for the wafer
- a .tex file for a latex report
- a compiled .pdf of said report

The user must change the number of the wafer and add any special comments about the wafer,
but (hopefully) nothing else except for a one-time path configuration on new systems

John Groh, January 2022
"""
import numpy as np
import matplotlib.pyplot as plt
import pickle as pkl
import os
import matplotlib.patches as patches
from matplotlib.colors import Normalize
import matplotlib.cm as cm
import glob

#####################################################
# MANUALLY CHANGE THESE FOR EACH WAFER              #
# Nothing else should need to be changed, hopefully #
#####################################################
wafer_number = 28
special_comments_about_this_wafer = """
None.
"""
# whether to automatically open the report pdf when done
show_report = True

##################################################
# CHANGE THESE IF RUNNING ON A DIFFERENT MACHINE #
##################################################
data_dir = "C:\\Users\\jcg12\\SO_screening\\data\\Lazarus_wafer_summaries\\" # where the summary and s21 data live
master_report_dir = "C:\\Users\\jcg12\\SO_screening\\wafer_reports\\" # where to save summary information and the report
waferscreen_dir = "C:\\Users\\jcg12\\WaferScreen\\waferscreen\\" # where the copy of the screening mechanics repository lives

########################
# REST OF CODE FOLLOWS #
########################

# file with design info we'll use for various mapping tasks
design_filename = os.path.join(waferscreen_dir, "umux100k_v321_banddef_summary.csv")

# find the corresponding S21 files
s21_files = glob.glob(os.path.join(data_dir, f"w{wafer_number}_s21_*.csv"))

# read in the first S21 file just to take a quick look
f, re, im = np.loadtxt(s21_files[0], unpack=True, delimiter=',', skiprows=1) # note f is in GHz

# find the corresponding fit parameter file
fit_summary_file = os.path.join(data_dir, f"w{wafer_number}_fittedparams.csv")

# global limits on plots, more easily configurable here than in the individual plot code below
f_limits = [np.min(f), np.max(f)]
if f_limits[0] > 4.: # if only a short range was used for some reason, ignore it
    f_limits[0] = 4.
if f_limits[1] < 6.: # if only a short range was used for some reason, ignore it
    f_limits[0] = 6.
Q_limits = (0, 300000)
m_limits = (-10,20) # in pH

# read in the fit result summary stuff and unpack it nicely
fit_summary = np.loadtxt(fit_summary_file, unpack=True, delimiter=',', skiprows=1, usecols=np.arange(38), dtype=str) # skip the path stuff at the end
# all the following are numpy arrays with length of the number of screened channels
res_number                 = fit_summary[0].astype(int)
band                       = fit_summary[1].astype(int)
wafer                      = fit_summary[2].astype(int)
pos_x                      = fit_summary[3].astype(int)
pos_y                      = fit_summary[4].astype(str)
rf_chain                   = fit_summary[5].astype(str)
switch_number              = fit_summary[6].astype(str)
sweep_power                = fit_summary[7].astype(float)
lambda_power               = fit_summary[8].astype(float)
attenuation                = fit_summary[9].astype(float)
servo_temp_mK              = fit_summary[10].astype(float)
box_pos                    = fit_summary[11].astype(str)
fcenter_ghz                = fit_summary[12].astype(float)
fcenter_ghz_error          = fit_summary[13].astype(float)
q_i                        = fit_summary[14].astype(float)
q_i_error                  = fit_summary[15].astype(float)
q_c                        = fit_summary[16].astype(float)
q_c_error                  = fit_summary[17].astype(float)
base_amplitude_abs         = fit_summary[18].astype(float)
base_amplitude_abs_error   = fit_summary[19].astype(float)
a_phase_rad                = fit_summary[20].astype(float)
a_phase_rad_error          = fit_summary[21].astype(float)
base_amplitude_slope       = fit_summary[22].astype(float)
base_amplitude_slope_error = fit_summary[23].astype(float)
tau_ns                     = fit_summary[24].astype(float)
tau_ns_error               = fit_summary[25].astype(float)
impedance_ratio            = fit_summary[26].astype(float)
impedance_ratio_error      = fit_summary[27].astype(float)

# deal with failures to fit f(Phi) curves gracefully
lambda_fit = np.array([float(x) if x != 'None' else np.nan for x in fit_summary[28]], dtype=float)
lambda_fit_err = np.array([float(x) if x != 'None' else np.nan for x in fit_summary[29]], dtype=float)
io_fit = np.array([float(x) if x != 'None' else np.nan for x in fit_summary[30]], dtype=float)
io_fit_err = np.array([float(x) if x != 'None' else np.nan for x in fit_summary[31]], dtype=float)
m_fit = np.array([float(x) if x != 'None' else np.nan for x in fit_summary[32]], dtype=float)
m_fit_err = np.array([float(x) if x != 'None' else np.nan for x in fit_summary[33]], dtype=float)
dfpp = np.array([float(x) if x != 'None' else np.nan for x in fit_summary[34]], dtype=float)
dfpp_err = np.array([float(x) if x != 'None' else np.nan for x in fit_summary[35]], dtype=float)
f2 = np.array([float(x) if x != 'None' else np.nan for x in fit_summary[36]], dtype=float)
f2_err = np.array([float(x) if x != 'None' else np.nan for x in fit_summary[37]], dtype=float)

# compute some derived parameters
q_tot = 1./(1./q_i + 1./q_c)
BW = f2 / q_tot

# convert m to Henries (for some reason it's not yet)
Phi_0 = 2.068e-15
m_fit = m_fit * Phi_0 / (2*np.pi)
m_fit_err = m_fit_err * Phi_0 / (2*np.pi)

# complain if any of the things that should be common are not
assert np.all(wafer == wafer[0])

# make an output directory for this wafer if it doesn't exist already
report_dir = os.path.join(master_report_dir, f"wafer_{wafer[0]:03d}")
if not os.path.isdir(report_dir):
    os.mkdir(report_dir)

# sort everything by natural frequency if possible, but if the SQUID curve fits failed then
# instead use the only available frequency
if np.any(np.isnan(f2)):
    inds_sorted = np.argsort(fcenter_ghz)
    f_for_plotting = fcenter_ghz[inds_sorted]
else:
    inds_sorted = np.argsort(f2)
    f_for_plotting = f2[inds_sorted]
band = band[inds_sorted]
wafer = wafer[inds_sorted]
pos_x = pos_x[inds_sorted]
pos_y = pos_y[inds_sorted]
rf_chain = rf_chain[inds_sorted]
switch_number = switch_number[inds_sorted]
sweep_power = sweep_power[inds_sorted]
lambda_power = lambda_power[inds_sorted]
attenuation = attenuation[inds_sorted]
servo_temp_mK = servo_temp_mK[inds_sorted]
box_pos = box_pos[inds_sorted]
fcenter_ghz = fcenter_ghz[inds_sorted]
fcenter_ghz_error = fcenter_ghz_error[inds_sorted]
q_i = q_i[inds_sorted]
q_i_error = q_i_error[inds_sorted]
q_c = q_c[inds_sorted]
q_c_error = q_c_error[inds_sorted]
base_amplitude_abs = base_amplitude_abs[inds_sorted]
base_amplitude_abs_error = base_amplitude_abs_error[inds_sorted]
a_phase_rad = a_phase_rad[inds_sorted]
a_phase_rad_error = a_phase_rad_error[inds_sorted]
base_amplitude_slope = base_amplitude_slope[inds_sorted]
base_amplitude_slope_error = base_amplitude_slope_error[inds_sorted]
tau_ns = tau_ns[inds_sorted]
tau_ns_error = tau_ns[inds_sorted]
impedance_ratio = impedance_ratio[inds_sorted]
impedance_ratio_error = impedance_ratio_error[inds_sorted]
lambda_fit = lambda_fit[inds_sorted]
lambda_fit_err = lambda_fit_err[inds_sorted]
io_fit = io_fit[inds_sorted]
io_fit_err = io_fit_err[inds_sorted]
m_fit = m_fit[inds_sorted]
m_fit_err = m_fit_err[inds_sorted]
dfpp = dfpp[inds_sorted]
dfpp_err = dfpp_err[inds_sorted]
f2 = f2[inds_sorted]
f2_err = f2_err[inds_sorted]

# read in the nominal bands and store the band edges in a dictionary

btmp, ftmp = np.loadtxt(design_filename, delimiter=',', unpack=True, usecols=(0,2), dtype=float, skiprows=1) # band, frequency in GHz
btmp = btmp.astype(int)
band_edges = {}
for iband in range(14):
    inds_band = np.argwhere(btmp == iband).T[0]
    band_edges[iband] = (np.min(ftmp[inds_band]), np.max(ftmp[inds_band]))

##################################################################################
# compute some things of interest to save for easy insertion into the latex report
##################################################################################
high_level_data = {} # this will be pickled later

# metadata
high_level_data['wafer'] = wafer[0]

# info about the chips
screened_bands = []
chip_coordinates = []
box_positions = []
temps = []
attenuations = []
rf_lines = []
lambda_powers = []
sweep_powers = []
switch_numbers = []
for i in range(len(res_number)):
    # possible to screen both of each band, or even all 3 if triplicates
    if band[i] not in screened_bands or (pos_x[i], pos_y[i]) not in chip_coordinates:
        screened_bands.append(band[i])
        chip_coordinates.append((pos_x[i],pos_y[i]))
        box_positions.append(box_pos[i])
        attenuations.append(attenuation[i])
        rf_lines.append(rf_chain[i])
        switch_numbers.append(switch_number[i])
        sweep_powers.append(sweep_power[i])
        lambda_powers.append(lambda_power[i])
        temps.append(servo_temp_mK[i])
        
high_level_data['screened_bands'] = screened_bands
high_level_data['chip_coordinates'] = chip_coordinates
high_level_data['box_positions'] = box_positions
high_level_data['rf_chains'] = rf_lines
high_level_data['attenuation'] = attenuations
high_level_data['switch_number'] = switch_numbers
high_level_data['sweep_power'] = sweep_powers
high_level_data['lambda_power'] = lambda_powers
high_level_data['temperature_mK'] = temps

# 25%, 50% (i.e. median), and 75% quartiles of: Qi, Qc, lambda, dfpp, BW, delta_f, M_c
quartiles = {}
quartiles['Qi'] = (np.percentile(q_i, 25), np.median(q_i), np.percentile(q_i, 75))
quartiles['Qc'] = (np.percentile(q_c, 25), np.median(q_c), np.percentile(q_c, 75))
quartiles['lambda'] = (np.percentile(lambda_fit, 25), np.median(lambda_fit), np.percentile(lambda_fit, 75))
quartiles['dfpp'] = (np.percentile(dfpp, 25), np.median(dfpp), np.percentile(dfpp, 75))
quartiles['BW'] = (np.percentile(BW, 25), np.median(BW), np.percentile(BW, 75))
quartiles['delta_f'] = (np.percentile(np.diff(f_for_plotting), 25), np.median(np.diff(f_for_plotting)), np.percentile(np.diff(f_for_plotting), 75))
quartiles['Mc'] = (np.percentile(m_fit, 25), np.median(m_fit), np.percentile(m_fit, 75))

high_level_data['quartiles'] = quartiles


# absolute frequency shift for each measured band relative to the designed edges
lower_band_edge_errors = []
upper_band_edge_errors = []
for screened_band in screened_bands:
    inds_band = np.argwhere(band == screened_band).T[0]
    min_freq = np.min(f_for_plotting[inds_band])*1.e9 # Hz
    max_freq = np.max(f_for_plotting[inds_band])*1.e9 # Hz
    lower_error = min_freq - band_edges[screened_band][0] # Hz
    upper_error = max_freq - band_edges[screened_band][1] # Hz
    lower_band_edge_errors.append(lower_error)
    upper_band_edge_errors.append(upper_error)

high_level_data['lower_band_edge_errors'] = lower_band_edge_errors
high_level_data['upper_band_edge_errors'] = upper_band_edge_errors
    

################
# yield analysis
################

# resonators found
inds_any_res = np.intersect1d(np.argwhere(q_i > 1000).T[0], np.argwhere(q_c > 1000).T[0])

# resonators with Qi > 50000
inds_ok_Q = np.argwhere(q_i > 50000).T[0]

# resonators with bandwidth between 50 and 300 kHz
inds_good_BW = np.intersect1d(np.argwhere(BW*1.e9 > 50.e3).T[0], np.argwhere(BW*1.e9 < 300.e3).T[0])

# resonators outside smurf keepout zones
smurf_keepout_zones_ghz = [(3.981 + 0.5 * zone_number, 4.019 + 0.5 * zone_number) for zone_number in range(5)] # copied from WaferScreen, sorry...
inds_inside_smurf_zones = []
for i in range(len(f_for_plotting)):
    good = True
    for zone in smurf_keepout_zones_ghz:
        if f_for_plotting[i] > zone[0] and f_for_plotting[i] < zone[1]:
            good = False
    if good:
        inds_inside_smurf_zones.append(i)
inds_inside_smurf_zones = np.array(inds_inside_smurf_zones)

# resonators in the 4-6 GHz band
inds_in_readout_band = np.intersect1d(np.argwhere(f_for_plotting > 4.0).T[0], np.argwhere(f_for_plotting < 6.0).T[0])

# resonators not too close to neighbors
inds_not_too_close_to_neighbor = []
for i in range(len(inds_any_res)):
    is_ok = True
    if i > 0:
        if (f_for_plotting[inds_any_res[i]] - f_for_plotting[inds_any_res[i-1]])*1.e9 < 0.3e6:
            is_ok = False
    if i < len(inds_any_res)-1:
        if (f_for_plotting[inds_any_res[i+1]] - f_for_plotting[inds_any_res[i]])*1.e9 < 0.3e6:
            is_ok = False
    if is_ok:
        inds_not_too_close_to_neighbor.append(inds_any_res[i])
inds_not_too_close_to_neighbor = np.array(inds_not_too_close_to_neighbor)

# channels with any squid response
inds_squid_responding = np.argwhere(dfpp*1.e9 > 1.e3).T[0]

# channels with dfpp > 50 kHz and < 300 kHz
inds_good_fpp = np.intersect1d(np.argwhere(dfpp*1.e9 > 50.e3).T[0], np.argwhere(dfpp*1.e9 < 300.e3).T[0])

# channels with lambda < 0.6
inds_good_lambda = np.argwhere(lambda_fit < 0.6).T[0]

# channels passing all the above cuts
inds_all_cuts = np.intersect1d(inds_any_res, inds_ok_Q)
inds_all_cuts = np.intersect1d(inds_all_cuts, inds_good_BW)
inds_all_cuts = np.intersect1d(inds_all_cuts, inds_inside_smurf_zones)
inds_all_cuts = np.intersect1d(inds_all_cuts, inds_in_readout_band)
inds_all_cuts = np.intersect1d(inds_all_cuts, inds_not_too_close_to_neighbor)
inds_all_cuts = np.intersect1d(inds_all_cuts, inds_squid_responding)
inds_all_cuts = np.intersect1d(inds_all_cuts, inds_good_fpp)
inds_all_cuts = np.intersect1d(inds_all_cuts, inds_good_lambda)

yield_info = {
    'max_possible': len(screened_bands)*65, # squid-coupled resonators, that is
    'resonators_found': len(inds_any_res),
    'good_Qs': len(inds_ok_Q),
    'good_BW': len(inds_good_BW),
    'outside_smurf_keepout_zones': len(inds_inside_smurf_zones),
    'in_readout_band': len(inds_in_readout_band),
    'good_spacing': len(inds_not_too_close_to_neighbor),
    'responding_SQUID': len(inds_squid_responding),
    'good_fpp': len(inds_good_fpp),
    'good_lambda': len(inds_good_lambda),
    'all_cuts': len(inds_all_cuts)
}
high_level_data['yield'] = yield_info


# yield plot
fig_yield, ax_yield = plt.subplots(figsize=(12,5))
inds_fail_cut1 = np.setdiff1d(range(len(f_for_plotting)), inds_any_res)
inds_fail_cut2 = np.setdiff1d(range(len(f_for_plotting)), inds_ok_Q)
inds_fail_cut3 = np.setdiff1d(range(len(f_for_plotting)), inds_good_BW)
inds_fail_cut4 = np.setdiff1d(range(len(f_for_plotting)), inds_inside_smurf_zones)
inds_fail_cut5 = np.setdiff1d(range(len(f_for_plotting)), inds_in_readout_band)
inds_fail_cut6 = np.setdiff1d(range(len(f_for_plotting)), inds_not_too_close_to_neighbor)
inds_fail_cut7 = np.setdiff1d(range(len(f_for_plotting)), inds_squid_responding)
inds_fail_cut8 = np.setdiff1d(range(len(f_for_plotting)), inds_good_fpp)
inds_fail_cut9 = np.setdiff1d(range(len(f_for_plotting)), inds_good_lambda)
ax_yield.plot(f_for_plotting[inds_fail_cut2], np.full_like(f_for_plotting, fill_value=8)[inds_fail_cut2], '|', color=plt.cm.tab10(0))
ax_yield.plot(f_for_plotting[inds_fail_cut3], np.full_like(f_for_plotting, fill_value=7)[inds_fail_cut3], '|', color=plt.cm.tab10(1))
ax_yield.plot(f_for_plotting[inds_fail_cut4], np.full_like(f_for_plotting, fill_value=6)[inds_fail_cut4], '|', color=plt.cm.tab10(2))
ax_yield.plot(f_for_plotting[inds_fail_cut5], np.full_like(f_for_plotting, fill_value=5)[inds_fail_cut5], '|', color=plt.cm.tab10(3))
ax_yield.plot(f_for_plotting[inds_fail_cut6], np.full_like(f_for_plotting, fill_value=4)[inds_fail_cut6], '|', color=plt.cm.tab10(4))
ax_yield.plot(f_for_plotting[inds_fail_cut7], np.full_like(f_for_plotting, fill_value=3)[inds_fail_cut7], '|', color=plt.cm.tab10(5))
ax_yield.plot(f_for_plotting[inds_fail_cut8], np.full_like(f_for_plotting, fill_value=2)[inds_fail_cut8], '|', color=plt.cm.tab10(6))
ax_yield.plot(f_for_plotting[inds_fail_cut9], np.full_like(f_for_plotting, fill_value=1)[inds_fail_cut9], '|', color=plt.cm.tab10(7))
ax_yield.grid(axis='x')
ax_yield.set_xlim(*f_limits)
ax_yield.set_xlabel('Frequency [GHz]')
ax_yield.set_yticks([1,2,3,4,5,6,7,8])
ax_yield.set_yticklabels([
    r"bad $\lambda_{SQUID}$",
    r"bad $\Delta f_{p2p}$",
    "no SQUID response",
    "too close to neighbor channel",
    "outside of 4--6 GHz band",
    "inside SMuRF keepout zone",
    "bad bandwidth",
    r"bad $Q_i$"
])
plt.tight_layout()
fig_yield.savefig(os.path.join(report_dir, "yield.pdf"))
plt.close(fig_yield)


#########################
# Bare resonator analysis
#########################
# first, find them.  Anything with no squid resopnse and the lowest frequency in a chip counts.
inds_bare = []
fs_bare = [] # GHz
Qis_bare = [] # times 1.e-5
Qcs_bare = [] # times 1.e-5
BWs_bare = [] # kHz
for screened_band in screened_bands:
    inds_band = np.argwhere(band == screened_band).T[0]
    ind_lowest = inds_band[np.argmin(f_for_plotting[inds_band])]
    if dfpp[ind_lowest]*1.e9 < 1.e3:
        inds_bare.append(ind_lowest)
        fs_bare.append(f_for_plotting[ind_lowest])
        Qis_bare.append(q_i[ind_lowest]*1.e-5)
        Qcs_bare.append(q_c[ind_lowest]*1.e-5)
        BWs_bare.append(BW[ind_lowest]*1.e6)
fig_bare, ax_bare = plt.subplots(figsize=(5,5), nrows=2, ncols=1, sharex=True)
ax_bare[0].plot(fs_bare, Qis_bare, 'ro', label=r'$Q_i$')
ax_bare[0].plot(fs_bare, Qcs_bare, 'bo', label=r'$Q_c$')
ax_bare[1].plot(fs_bare, BWs_bare, 'ko')
ax_bare[0].set_ylabel(r'Quality factor $\times\; 10^{-5}$')
ax_bare[1].set_ylabel('Resonator bandwidth [kHz]')
ax_bare[1].set_xlabel('Frequency [GHz]')
ax_bare[0].grid()
ax_bare[1].grid()
ax_bare[0].legend()
ax_bare[0].set_title('Bare resonators')
plt.tight_layout()
fig_bare.savefig(os.path.join(report_dir, 'bare_resonators.pdf'))
plt.close(fig_bare)



#############################################################
# Full-range S21 plot that compares to nominal band locations
#############################################################
for i, s21_file in enumerate(s21_files):
    f, re, im = np.loadtxt(s21_file, unpack=True, delimiter=',', skiprows=1) # note f is in GHz
    
    fig_s21, ax_s21 = plt.subplots(figsize=(10,6), nrows=2, ncols=1, sharex=True)
    band_colors = [plt.cm.Dark2(j) for j in range(7)] * 2
    for iband in range(14):
        ax_s21[0].axvspan(xmin=band_edges[iband][0]*1.e-9, xmax=band_edges[iband][1]*1.e-9, color=band_colors[iband], alpha=0.5)
        ax_s21[1].axvspan(xmin=band_edges[iband][0]*1.e-9, xmax=band_edges[iband][1]*1.e-9, color=band_colors[iband], alpha=0.5)
        ax_s21[0].text(s = f"Band {iband:02d}", color=band_colors[iband], fontweight='bold', fontsize=6, x=band_edges[iband][0]*1.e-9+0.01, y = 0.9)    
    ax_s21[0].plot(f, 20*np.log10(np.abs(re + 1.j*im)), 'k-')
    ax_s21[1].plot(f, np.angle(re + 1.j*im, deg=True), 'k-')
    ax_s21[0].grid()
    ax_s21[1].grid()
    ax_s21[1].set_xlim(*f_limits)
    ax_s21[0].set_ylabel('$|S_{21}|$ [dB]')
    ax_s21[1].set_ylabel('arg$(S_{21})$ [degrees]')
    ax_s21[1].set_xlabel('Frequency [GHz]')
    plt.tight_layout()
    fig_s21.savefig(os.path.join(report_dir, f"s21_{i}.pdf"))
    plt.close(fig_s21)

##########################################################################
# quality factor plots:
# one showing Qi and Qc as a function of frequency, along with their ratio
# another with just histograms
##########################################################################
fig_Q, ax_Q = plt.subplots()
bins = np.linspace(Q_limits[0], Q_limits[1]*1.e-5, 50)
ax_Q.hist(q_i*1.e-5, bins=bins, histtype='step', alpha=0.75, color='r', label='$Q_i$', linewidth=2)
ax_Q.hist(q_c*1.e-5, bins=bins, histtype='step', alpha=0.75, color='b', label='$Q_c$', linewidth=2)
ax_Q.hist(q_i*1.e-5, bins=bins, histtype='stepfilled', alpha=0.25, color='r')
ax_Q.hist(q_c*1.e-5, bins=bins, histtype='stepfilled', alpha=0.25, color='b')
ax_Q.set_xlabel(r'Quality factor $\times$ $10^{-5}$')
ax_Q.grid()
ax_Q.legend()
ax_Q.set_xlim(Q_limits[0]*1.e-5, Q_limits[1]*1.e-5)
plt.tight_layout()
fig_Q.savefig(os.path.join(report_dir, "Q_hist.pdf"))
plt.close(fig_Q)

fig_Q_f, ax_Q_f = plt.subplots(figsize=(10,6), nrows=2, ncols=1, sharex=True)
ax_Q_f[0].errorbar(f_for_plotting, q_i*1.e-5, yerr=q_i_error*1.e-5, fmt='.', alpha=0.75, color='r', label='$Q_i$')
ax_Q_f[0].errorbar(f_for_plotting, q_c*1.e-5, yerr=q_c_error*1.e-5, fmt='.', alpha=0.75, color='b', label='$Q_c$')
ax_Q_f[1].plot(f_for_plotting, q_i / q_c, '.', alpha=0.75, color='k')
ax_Q_f[0].legend()
ax_Q_f[0].set_ylim(Q_limits[0]*1.e-5, Q_limits[1]*1.e-5)
ax_Q_f[1].set_ylim(0, 5)
ax_Q_f[1].set_xlim(*f_limits)
ax_Q_f[1].set_xlabel('Frequency [GHz]')
ax_Q_f[0].set_ylabel(r'Quality factor $\times$ $10^{-5}$')
ax_Q_f[1].set_ylabel('$Q_i \; / \; Q_c$')
ax_Q_f[0].grid()
ax_Q_f[1].grid()
plt.tight_layout()
fig_Q_f.savefig(os.path.join(report_dir, "Q.pdf"))
plt.close(fig_Q_f)

####################################################
# frequency trend and histogram of pairwise spacings
####################################################
fig_spacing, ax_spacing = plt.subplots(nrows=1, ncols=2, figsize=(10,4))
ax_spacing[0].plot((f_for_plotting[:-1]+f_for_plotting[1:])/2, np.diff(f_for_plotting)*1.e3, '.', color='k')
ax_spacing[1].hist(np.diff(f_for_plotting)*1.e3, bins=np.linspace(0, 15, 30), histtype='step', color='k', linewidth=2, alpha=0.75)
ax_spacing[1].hist(np.diff(f_for_plotting)*1.e3, bins=np.linspace(0, 15, 30), histtype='stepfilled', color='k', alpha=0.25)
ax_spacing[0].set_xlabel('$(f_j + f_i) / 2$ [GHz]')
ax_spacing[0].set_ylabel('$f_j - f_i$ [MHz]')
ax_spacing[0].grid()
ax_spacing[0].set_xlim(*f_limits)
ax_spacing[0].set_ylim(0,5)
ax_spacing[1].grid()
ax_spacing[1].set_xlabel('$f_j - f_i$ [MHz]')
plt.tight_layout()
fig_spacing.savefig(os.path.join(report_dir, "delta_f.pdf"))
plt.close(fig_spacing)

##############
# squid lambda
##############
fig_lambda, ax_lambda = plt.subplots(nrows=1, ncols=2, figsize=(10,4))
ax_lambda[0].errorbar(f_for_plotting, lambda_fit, yerr=lambda_fit_err, fmt='.', color='k')
ax_lambda[1].hist(lambda_fit, bins=np.linspace(0,1,25), histtype='step', color='k', alpha=0.75, linewidth=2)
ax_lambda[1].hist(lambda_fit, bins=np.linspace(0,1,25), histtype='stepfilled', color='k', alpha=0.25)
ax_lambda[0].grid()
ax_lambda[0].set_xlim(*f_limits)
ax_lambda[1].grid()
ax_lambda[0].set_xlabel('Frequency [GHz]')
ax_lambda[0].set_ylabel(r'$\lambda_{SQUID}$')
ax_lambda[1].set_xlabel(r'$\lambda_{SQUID}$')
ax_lambda[0].set_ylim(0,1)
ax_lambda[1].set_xlim(0,1)
plt.tight_layout()
fig_lambda.savefig(os.path.join(report_dir, "lambda.pdf"))
plt.close(fig_lambda)

#######################################
# flux ramp/SQUID mutual inductance
#######################################
fig_coupling, ax_coupling = plt.subplots(nrows=1, ncols=2, figsize=(10,4))
ax_coupling[0].plot(f_for_plotting, m_fit*1.e12, '.', color='k')
ax_coupling[1].hist(m_fit*1.e12, bins=np.linspace(-10,20,30), histtype='step', color='k', linewidth=2, alpha=0.75)
ax_coupling[1].hist(m_fit*1.e12, bins=np.linspace(-10,20,30), histtype='stepfilled', color='k', alpha=0.25)
ax_coupling[0].grid()
ax_coupling[0].set_xlim(*f_limits)
ax_coupling[0].set_ylim(*m_limits)
ax_coupling[1].grid()
ax_coupling[0].set_xlabel('Frequency [GHz]')
ax_coupling[0].set_ylabel(r'$M_{FR, SQUID}$ [pH]')
ax_coupling[1].set_xlabel(r'$M_{FR, SQUID}$ [pH]')
plt.tight_layout()
fig_coupling.savefig(os.path.join(report_dir, "Mc.pdf"))
plt.close(fig_coupling)


############################################
# Bandwidth and peak-to-peak frequency shift
############################################
fpp_limits = (-50,600) # for the plot against frequency only

fig_fpp_f, ax_fpp_f = plt.subplots(nrows=2, ncols=1, figsize=(10,6), sharex=True)
ax_fpp_f[0].plot(f_for_plotting, dfpp*1.e6, 'r.', alpha=0.75, label=r'Peak-to-peak frequency response')
ax_fpp_f[0].plot(f_for_plotting, BW*1.e6, 'b.', alpha=0.75, label=r'Resonator bandwidth')
ax_fpp_f[1].plot(f_for_plotting, dfpp / BW, 'k.')
ax_fpp_f[0].grid()
ax_fpp_f[1].grid()
ax_fpp_f[0].legend()
ax_fpp_f[1].set_xlim(*f_limits)
ax_fpp_f[0].set_ylim(*fpp_limits)
ax_fpp_f[1].set_xlabel('Frequency [GHz]')
ax_fpp_f[0].set_ylabel(r'$\Delta f$ [kHz]')
ax_fpp_f[1].set_ylabel(r'$\Delta f_{p2p}$ / BW')
ax_fpp_f[1].set_ylim(-0.5,5)
plt.tight_layout()
fig_fpp_f.savefig(os.path.join(report_dir, "fpp_BW_vs_f.pdf"))
plt.close(fig_fpp_f)


fig_fpp, ax_fpp = plt.subplots()
bins = np.linspace(fpp_limits[0], fpp_limits[-1], 50)
ax_fpp.hist(dfpp*1.e6, bins=bins, histtype='step', alpha=0.75, color='r', label=r'Peak-to-peak frequency response', linewidth=2)
ax_fpp.hist(BW*1.e6, bins=bins, histtype='step', alpha=0.75, color='b', label='Resonator bandwidth', linewidth=2)
ax_fpp.hist(dfpp*1.e6, bins=bins, histtype='stepfilled', alpha=0.25, color='r')
ax_fpp.hist(BW*1.e6, bins=bins, histtype='stepfilled', alpha=0.25, color='b')
ax_fpp.set_xlabel(r'$\Delta f$ [kHz]')
ax_fpp.grid()
ax_fpp.legend()
ax_fpp.set_xlim(bins[0], bins[-1])
plt.tight_layout()
fig_fpp.savefig(os.path.join(report_dir, "fpp_BW_hist.pdf"))
plt.close(fig_fpp)


#########################
# position space analysis
#########################

def wafer_map(parameter, vmin, vmax, label, savename, show=False):
    """
    Generic heatmap utility function
    """
    
    fig_map = plt.figure(figsize=(6,7))
    ax_map = fig_map.add_subplot(1,1,1, aspect='equal')

    # make the wafer outline
    wafer_diameter = 76.2 # mm
    left_corner = (-12.15, -36.1) # mm
    right_corner = (12.15, -36.1)
    end_angle = np.arctan2(left_corner[1],left_corner[0]) * 180 / np.pi + 360. # deg, 0 to 360
    start_angle = np.arctan2(right_corner[1],right_corner[0]) * 180 / np.pi + 360. # deg, 0 to 360
    ax_map.add_patch(patches.Arc(xy=(0,0), width=wafer_diameter, height=wafer_diameter, theta1=start_angle, theta2=end_angle, ec='k')) # circle part
    ax_map.plot([left_corner[0], right_corner[0]], [left_corner[1], right_corner[1]], 'k-') # flat part
    ax_map.set_xlim(-1.01*wafer_diameter/2, 1.01*wafer_diameter/2)
    ax_map.set_ylim(-1.01*wafer_diameter/2, 1.01*wafer_diameter/2)
    plt.axis('off')
    
    # make the chip outlines
    chip_size = (20.0, 4.0) # mm
    chip_xys = np.array([
        (-1,-4),
        (-1,-3),
        (-1,-2),
        (-1,-1),
        (-1,0),
        (-1,1),
        (-1,2),
        (-1,3),
        (-1,4),
        (0,-7),
        (0,-6),
        (0,-5),
        (0,-4),
        (0,-3),
        (0,-2),
        (0,-1),    
        (0,1),
        (0,2),
        (0,3),
        (0,4),
        (0,5),
        (0,6),
        (0,7),    
        (1,-4),
        (1,-3),
        (1,-2),
        (1,-1),
        (1,0),
        (1,1),
        (1,2),
        (1,3),
        (1,4),
    ])
    for chip_xy in chip_xys:
        bottom_left = (
            chip_xy[0]*chip_size[0] - chip_size[0]/2,
            chip_xy[1]*chip_size[1] - chip_size[1]/2
        )
        ax_map.add_patch(patches.Rectangle(xy=bottom_left, width=chip_size[0], height=chip_size[1], ec='k', fc='w'))

    # color bar
    norm = Normalize(vmin=vmin, vmax=vmax)
    m = cm.ScalarMappable(norm=norm, cmap=plt.cm.jet)
    cb = plt.colorbar(m, orientation='horizontal', fraction=0.08, pad=0.04, label=label)

    # read in the resonator number (within band) to xy (on chip) mapping
    x_on_chip, y_on_chip = np.loadtxt(design_filename, delimiter=',', unpack=True, usecols=(10,11), dtype=float, skiprows=1)

    # now map the parameter of interest to position on the chip
    for screened_band, chip_xy in zip(screened_bands, chip_coordinates):
        ax_map.text(s=f"Band {screened_band:02d}", x=float(chip_xy[0])*chip_size[0]-4, y=float(chip_xy[1])*chip_size[1], fontdict={'color':'k','size':8})
        inds_band = np.argwhere(band == screened_band).T[0]
        offset = inds_band[0]
        for i, ind_band in enumerate(inds_band):
            if i >= 66: # just ignore channels if too many were identified in a band
                continue
            if ind_band >= len(parameter): # not sure how this could happen, but it does.  Ignore
                continue
            x = x_on_chip[ind_band - offset] + float(chip_xy[0]) * chip_size[0]
            y = y_on_chip[ind_band - offset] + float(chip_xy[1]) * chip_size[1] - 0.9 # so they actually corespond to squid positions
            ax_map.plot(x, y, '.', markersize=2, color=m.to_rgba(parameter[ind_band]))
    plt.tight_layout()
    fig_map.savefig(os.path.join(report_dir, savename))
    if show:
        plt.show()
    else:
        plt.close(fig_map)

# map of Q_i
wafer_map(parameter=q_i*1.e-5, vmin=0, vmax=2, label=r'$Q_i \;\times\; 10^{-5}$', savename='Qi_position.pdf', show=False)

# map of Q_c
wafer_map(parameter=q_c*1.e-5, vmin=0, vmax=1.5, label=r'$Q_c \;\times\; 10^{-5}$', savename='Qc_position.pdf', show=False)

# map of lambda
wafer_map(parameter=lambda_fit, vmin=0, vmax=1, label=r'$\lambda_{SQUID}$', savename='lambda_position.pdf', show=False)

# map of dfpp
wafer_map(parameter=dfpp*1.e6, vmin=0, vmax=300, label=r'$\Delta f_{p2p}$ [kHz]', savename='fpp_position.pdf', show=False)

# map of pairwise frequency shift
wafer_map(parameter=np.array(list(np.diff(f_for_plotting)*1.e3)+[1.8]), vmin=0, vmax=2.5, label=r'$f_{i+1} - f_{i}$ [MHz]', savename='deltaf_position.pdf', show=False) # hack to make array lengths work

# map of flux ramp mutual inductance
wafer_map(parameter=m_fit*1.e12, vmin=5, vmax=20, label=r'$M_{FR, SQUID}$ [pH]', savename='M_position.pdf', show=False)

# map of bandwidth
wafer_map(parameter=BW*1.e6, vmin=0, vmax=300, label=r'Bandwidth [kHz]', savename='bandwidth_position.pdf', show=False)

# absolute frequency shift (estimate this first)
design_bands, design_fs = np.loadtxt(design_filename, delimiter=',', unpack=True, usecols=(0,2), dtype=float, skiprows=1)
design_bands = design_bands.astype(int)
absolute_f_error = []
for screened_band in screened_bands:
    inds_band_screened = np.argwhere(band == screened_band).T[0]
    inds_band_design = np.argwhere(design_bands == screened_band).T[0]
    for i in range(len(inds_band_screened)):
        # for some reason, sometimes more than 66 channels get identified in a band
        # just ignore the upper ones if so
        if i >= 66:
            continue
        f_meas = f_for_plotting[inds_band_screened[i]] * 1.e9 # Hz
        f_des = design_fs[inds_band_design[i]] # Hz
        absolute_f_error.append(f_meas - f_des) # Hz
absolute_f_error = np.array(absolute_f_error)
wafer_map(parameter=absolute_f_error*1.e-6, vmin=-20, vmax=20, label=r'$f - f_{design}$ [MHz]', savename='absolute_f_error_position.pdf', show=False)
        
    
####################################
# save the high level data to a file
####################################
with open(os.path.join(report_dir, 'high_level_data.pkl'), 'wb') as f:
    pkl.dump(high_level_data, f)










#############################
# ------------------------- #
# - Make the latex report - #
# ------------------------- #
#############################
report_text = r"""\documentclass{article}
\usepackage[top=1in, bottom=1in, left=1in, right=1in]{geometry}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amssymb}	
\usepackage{caption}
\usepackage{enumitem}
\usepackage{cite}
\usepackage{hyperref}
\usepackage{float}
\setlist{nolistsep}

"""
report_text += r"\graphicspath{{" + r"{:s}".format(report_dir.replace('\\','/')) + r"""}}

\begin{document}

% title
\begin{center}
"""

report_text += r"{\huge\bf Wafer " + f"{wafer[0]:02d}" + r" Screening Report}\\"

report_text += r"""
Lazarus team, NIST Boulder
\end{center}

\tableofcontents

\section{Special comments about this wafer in particular}
"""
report_text += f"{special_comments_about_this_wafer}" + r"""

\section{Measurement info}
\label{sec:info}
The identities and locations of the chips that were screened are listed in Table~\ref{tab:chips}.  The conditions under which measurements were performed are listed in Table~\ref{tab:conditions}.  After an initial sweep over the full 4--6 GHz range to identify approximate channel positions, all further characterizations are performed by setting fixed DC currents on the flux ramp line and performing a complex $S_{21}$ measurements in a narrow region around each resonance with a VNA.  During all measurements, a PID loop keeps the measurement apparatus at a constant temperature.  Further details can be found in Zachary Whipps's LTD19 proceedings.

% table of chips information
\begin{table}[H]
  \begin{center}
    \begin{tabular}{|c|c|c|}
      \hline
      \textbf{Band number (0-indexed)} & \textbf{Position on fabrication wafer} & \textbf{Position in screener box}\\
      \hline
"""
for band, xy, box_pos  in zip(screened_bands, chip_coordinates, box_positions):
    report_text += f"      {band:02d} & ({int(xy[0]):d},{int(xy[1]):d}) & {box_pos:s}" + r"""\\
       \hline
    """
report_text += r"""
    \end{tabular}
    \caption{Details of the screened chips.}
    \label{tab:chips}
  \end{center}
\end{table}

% table of measurement conditions
\begin{table}[H]
  \begin{center}
    \begin{tabular}{|c|c|c|c|c|c|c|}
      \hline
      Chip & $T$ & RF line & Attenuation & Switch number & $P_{sweep}$ & $P_{\lambda}$\\
      \hline
"""
for screened_band, chip_coordinate, temp, rf_line, attenuation, switch_number, sweep_power, lambda_power in zip(screened_bands, chip_coordinates, temps, rf_lines, attenuations, switch_numbers, sweep_powers, lambda_powers):
    report_text += f"      B{screened_band:02d} ({int(chip_coordinate[0]):d},{int(chip_coordinate[1]):d}) & {temp} mK & {rf_line:s} & {attenuation} dB & {switch_number} & {sweep_power} dBm & {lambda_power} dBm" + r"""\\
      \hline
"""

report_text += r"""
    \end{tabular}
    \caption{Conditions under which channel properties were measured.  Power levels are quoted at the VNA, so one must add the attenuation to infer power levels at the responators.}
    \label{tab:conditions}
  \end{center}
\end{table}

\section{Measured properties}
\label{sec:channel_props}
The initial frequency sweep used to identify resonances is shown in Figure~\ref{fig:s21}.  The colored nominal band edges make it easier to see how the absolute frequency accuracy may affect the yield, since resonators outside their target band may cause cross-chip collisions, fall in a SM$\mu$RF keep-out zone, or land outside the usable 4--6 GHz band.

% S21 figure
\begin{figure}[H]
  \begin{center}
"""
for i in range(len(s21_files)):
    report_text += r"    \includegraphics[width=\textwidth]{" + f"s21_{i}.pdf" + r"}"
report_text += r"""
    \caption{The magnitude (top) and phase (bottom) of the forward transmission of the partial set of multiplexer chips after the group delay has been removed.  The designed chip bands are indicated by the vertical colored bars.  Multiple RF line measurements may have been used, if there is more than one pair of axes.}
    \label{fig:s21}
  \end{center}
\end{figure}

The absolute frequency placement is partially quantified in Table~\ref{tab:shift}, which tabulates the error in the upper and lower edge of each as-fabricated band.

% absolute frequency shift table
\begin{table}[H]
  \begin{center}
    \begin{tabular}{|c|c|c|}
      \hline
      \textbf{Band number (0-indexed)} & \textbf{Lower edge shift} & \textbf{Upper edge shift}\\
      \hline
"""
for band, err_low, err_high in zip(screened_bands, lower_band_edge_errors, upper_band_edge_errors):
    report_text += f"{band} & {err_low*1.e-6:.1f} MHz & {err_high*1.e-6:.1f} MHz" + r"""\\
    \hline
    """
report_text += r"""
    \end{tabular}
    \caption{Measured upper and lower edges of the chip bands relative to the design.  Positive values indicate that the as-fabricated frequencies are greater than designed.}
    \label{tab:shift}
  \end{center}
\end{table}

The internal quality factor $Q_i$ and coupling quality factor $Q_c$ are extracted by fitting the complex $S_{21}$ curve in a narrow window around each individual resonator.  The measured values of $Q_i$ and $Q_c$, along with their ratio (which we target to be $\geq 2$), is shown as a function of channel frequency in Figure~\ref{fig:Q_vs_f}.  Their values are also histogrammed in Figure~\ref{fig:Q_hist} for simplicity.

% quality factor vs. frequency figure
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{Q.pdf}
    \caption{Frequency distribution of the internal and coupling quality factors (top) along with their ratio (bottom).}
    \label{fig:Q_vs_f}
  \end{center}
\end{figure}

% quality factor histogram
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=0.6\textwidth]{Q_hist.pdf}
    \caption{Histogram of the internal and coupling quality factors.}
    \label{fig:Q_hist}
  \end{center}
\end{figure}

The pairwise channel spacing ($|f_{i+1} - f_i|$) is important for crosstalk, and its measurement is shown in Figure~\ref{fig:delta_f}.  The channel frequencies used for this are taken from fitting the $f(\Phi)$ relation when varying flux is applied to the SQUID via the flux ramp line and extracting the resonator natural frequency.  Thus, it is a (slightly) better estimate of the channel spacing that will occur during CMB operations.

% pairwise spacing figure
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{delta_f.pdf}
    \caption{Pairwise channel spacings for nearest frequency neighbors ($j = i + 1$), where the random phase offsets of each channel's SQUID response due to ambient magnetic fields have been removed.}
    \label{fig:delta_f}
  \end{center}
\end{figure}

The resonator bandwidth $BW$ and peak-to-peak frequency response as a function of applied flux $\Delta f_{p2p}$ are shown as a function of channel frequency in Figure~\ref{fig:fpp_BW_vs_f} and are histogrammed in Figure~\ref{fig:fpp_BW_hist}.  The bandwidth is fit from $S_{21}$ measurements, and the magnitude of the frequency response is fit from the response to applied flux.

% bandwidth and frequency response vs. frequency figure
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{fpp_BW_vs_f.pdf}
    \caption{Frequency distribution of the peak-to-peak frequency responses to applied flux and the resonator bandwidths.}
    \label{fig:fpp_BW_vs_f}
  \end{center}
\end{figure}

% bandwidth and frequency response histogram
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=0.6\textwidth]{fpp_BW_hist.pdf}
    \caption{Histogram of the peak-to-peak frequency responses to applied flux and the resonator bandwidths.}
    \label{fig:fpp_BW_hist}
  \end{center}
\end{figure}

Since parasitic RF current from the resonator probe tone induces flux excursions in the SQUID that confound low-frequency ($\ll 1$ GHz) measurements, the SQUID parameter $\lambda_{SQUID}$ is measured at a lower microwave power level (listed in Table~\ref{tab:conditions}).  The measured values of $\lambda_{SQUID}$ are shown in Figure~\ref{fig:lambda}.

% lambda figure
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{lambda.pdf}
    \caption{Measured values of the SQUID parameter $\lambda_{SQUID}$, defined as the ratio of the SQUID loop self-inductance and the junction Josephson inductance.}
    \label{fig:lambda}
  \end{center}
\end{figure}

The mutual inductance between the flux ramp inductor and the SQUID also comes out of the fit to the SQUID response, and is shown in Figure~\ref{fig:Mc}.

% Mc figure
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{Mc.pdf}
    \caption{Measured mutual inductances between the flux ramp input inductor and the SQUID loop.}
    \label{fig:Mc}
  \end{center}
\end{figure}

\section{Bare resonators}
The lowest frequency resonator on each chip is designed with no SQUID, and therefore is of interest for screening and operations.  These are identified from the screening data if the lowest frequency resonator has a measured peak-to-peak frequency response of less than 1 kHz.  Figure~\ref{fig:bare_resonators} shows the resonator parameters for those that were identified in this screening data set.

\begin{figure}[H]
  \begin{center}
    \includegraphics[width=0.6\textwidth]{bare_resonators.pdf}
    \caption{Measured quality factors and bandwidths of the SQUID-less resonators identified during this screening.}
    \label{fig:bare_resonators}
  \end{center}
\end{figure}

\section{Wafer summary}
The distributions of channel properties detailed in Section~\ref{sec:channel_props} are summarized in Table~\ref{tab:percentiles}, described by their 25th, 50th (i.e. the median), and 75th percentiles.

% table of 25th percentile, median, and 75th percentile for all the measured properties of interest
\begin{table}[H]
  \begin{center}
    \begin{tabular}{|c|c|c|c|c|}
      \hline
      \textbf{Parameter} & \textbf{Design target} & \textbf{Median value} & \textbf{25th percentile} & \textbf{75th percentile}\\
      \hline
"""
report_text += f"      $Q_i$ & 200,000 & {quartiles['Qi'][1]:,.0f} & {quartiles['Qi'][0]:,.0f} & {quartiles['Qi'][2]:,.0f}" + r"""\\
      \hline
"""
report_text += f"      $Q_c$ & 50,000 (4 GHz) to 100,000 (6 GHz) & {quartiles['Qc'][1]:,.0f} & {quartiles['Qc'][0]:,.0f} & {quartiles['Qc'][2]:,.0f}" + r"""\\
      \hline
"""
report_text += f"      $BW$ & 100 kHz & {quartiles['BW'][1]*1.e6:.1f} kHz & {quartiles['BW'][0]*1.e6:.1f} kHz & {quartiles['BW'][2]*1.e6:.1f} kHz" + r"""\\
      \hline
"""
report_text += r"      $|f_{i+1} - f_i|$ & 1.8 MHz & " + f"{quartiles['delta_f'][1]*1.e3:.1f} MHz & {quartiles['delta_f'][0]*1.e3:.1f} MHz & {quartiles['delta_f'][2]*1.e3:.1f} MHz" + r"""\\
      \hline
"""
report_text += r"      $\Delta f_{p2p}$ & 100 kHz & " + f"{quartiles['dfpp'][0]*1.e6:.1f} kHz & {quartiles['dfpp'][0]*1.e6:.1f} kHz & {quartiles['dfpp'][2]*1.e6:.1f} kHz" + r"""\\
      \hline
"""
report_text += r"      $\lambda_{SQUID}$ & 0.33 & " + f"{quartiles['lambda'][1]:.2f} & {quartiles['lambda'][0]:.2f} & {quartiles['lambda'][2]:.2f}" + r"""\\
      \hline
"""
report_text += r"      $M_{FR,SQUID}$ & 13.3 pH & " + f"{quartiles['Mc'][1]*1.e12:.1f} pH & {quartiles['Mc'][0]*1.e12:.1f} pH & {quartiles['Mc'][2]*1.e12:.1f} pH" + r"""\\
      \hline
    \end{tabular}
    \caption{Summary of the measured channel properties.  The conditions under which each of these properties were measured are listed in Section~\ref{sec:info}.}
    \label{tab:percentiles}
  \end{center}
\end{table}

\section{Yield info}
A rough sense of how many channels may be expected to be usable from this wafer may be obtained by applying cuts based on target resonator and SQUID properties.  Since the relationship between each of these individual properties to the channel's operability and sensitivity during CMB observations is not well-modeled, the following numbers should be taken lightly.  Furthermore, several sources of yield hits (e.g. non-ideal $f(\Phi)$ curves causing difficulty with flux ramp demodulation, excess noise, assembly losses, RFI pickup, etc)) are not accounted for here and should not be forgotten.  Table~\ref{tab:yield} lists the number and fraction of channels which pass semi-arbitrarily defined cuts on the various easily measured parameters from this screening.

% yield table
\begin{table}[H]
  \begin{center}
    \begin{tabular}{|c|c|c|}    
      \hline
      \textbf{Criteria} & \textbf{Number of channels} & \textbf{Percent of total possible}\\
      \hline
"""
report_text += f"      Resonance found & {yield_info['resonators_found']:d} & {yield_info['resonators_found']/yield_info['max_possible']*100:.1f}" + r"""\%\\
      \hline
"""
report_text += f"      $Q_i > 50,000$ & {yield_info['good_Qs']:d} & {yield_info['good_Qs']/yield_info['max_possible']*100:.1f}" + r"""\%\\
      \hline
"""
report_text += f"      50 kHz $<$ $BW$ $<$ 300 kHz & {yield_info['good_BW']:d} & {yield_info['good_BW']/yield_info['max_possible']*100:.1f}" + r"""\%\\
      \hline
"""
report_text += r"      Not in a SM$\mu$RF keepout zone & " + f"{yield_info['outside_smurf_keepout_zones']:d} & {yield_info['outside_smurf_keepout_zones']/yield_info['max_possible']*100:.1f}" + r"""\%\\
      \hline
"""
report_text += f"      Inside the 4--6 GHz readout band & {yield_info['in_readout_band']:d} & {yield_info['in_readout_band']/yield_info['max_possible']*100:.1f}" + r"""\%\\
      \hline
"""
report_text += r"      $|f_j - f_i| >$ 0.3 MHz for $j = i \pm 1$ & " + f"{yield_info['good_spacing']:d} & {yield_info['good_spacing']/yield_info['max_possible']*100:.1f}" + r"""\%\\
      \hline
"""
report_text += f"      SQUID response seen & {yield_info['responding_SQUID']:d} & {yield_info['responding_SQUID']/yield_info['max_possible']*100:.1f}" + r"""\%\\
      \hline
"""
report_text += r"      50 kHz $< \Delta f_{p2p} <$ 300 kHz & " + f"{yield_info['good_fpp']:d} & {yield_info['good_fpp']/yield_info['max_possible']*100:.1f}" + r"""\%\\
      \hline
"""
report_text += r"      $\lambda_{SQUID} <$ 0.6 & " + f"{yield_info['good_lambda']:d} & {yield_info['good_lambda']/yield_info['max_possible']*100:.1f}" + r"""\%\\
      \hline
"""
report_text += r"      \textbf{Simultaneously passes all above cuts} & " + f"{len(inds_all_cuts):d} & {len(inds_all_cuts)/yield_info['max_possible']*100:.1f}" + r"""\%\\
      \hline
    \end{tabular}
    \caption{A crude accounting of channels which satisfy various yield cuts.  See Figure~\ref{fig:yield} for the locations of the channels which do not satisfy these criteria.  When calculating the percentage of total possible channels, the denominator is the number of designed SQUID-coupled channels.  Thus, the resonator yield could in principle exceed 100\% and go up to 101.5\%.}
    \label{tab:yield}
  \end{center}
\end{table}

% yield figure
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{yield.pdf}
    \caption{Resonant frequencies of channels which fail various yield cuts, detailed in Table~\ref{tab:yield}.}
    \label{fig:yield}
  \end{center}
\end{figure}


\section{Distributions across the fabrication wafer}
Approximate distributions of various parameters of interest are shown in Figures~\ref{fig:Qi_pos}--\ref{fig:M_pos}.  Since yield is in general less than 100\%, there are a combinatorically prohibitive number of possible frequency-to-position mappings which will require additional information not measured in the screening setup to sort out.  In order to still proceed with something useful for feedback to the fabrication team, all yield loss is assumed to be at the upper frequencies in each chip (i.e. the first resonator found in frequency space is assumed to be the first designed one, the second resonator found in frequency space is assumed to be the second designed one, and all the way up to the Nth resonator found).

% Qi
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{Qi_position.pdf}
    \caption{Position dependence on the fabrication wafer of $Q_i$.  Note that these positions are only approximate - for simplicity, all missing channels are assumed to be at the top edge of their respective bands.}
    \label{fig:Qi_pos}
  \end{center}
\end{figure}

% Qc
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{Qc_position.pdf}
    \caption{Position dependence on the fabrication wafer of $Q_c$.  Note that these positions are only approximate - for simplicity, all missing channels are assumed to be at the top edge of their respective bands.}
    \label{fig:Qc_pos}
  \end{center}
\end{figure}

% BW
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{bandwidth_position.pdf}
    \caption{Position dependence on the fabrication wafer of the resonator bandwidths.  Note that these positions are only approximate - for simplicity, all missing channels are assumed to be at the top edge of their respective bands.}
    \label{fig:BW_pos}
  \end{center}
\end{figure}

% absolute f
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{absolute_f_error_position.pdf}
    \caption{Position dependence on the fabrication wafer of the absolute frequency placement error.  Note that these positions are only approximate - for simplicity, all missing channels are assumed to be at the top edge of their respective bands.}
    \label{fig:absolute_f_error_pos}
  \end{center}
\end{figure}

% deltaf
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{deltaf_position.pdf}
    \caption{Position dependence on the fabrication wafer of the pairwise channel spacings.  Note that these positions are only approximate - for simplicity, all missing channels are assumed to be at the top edge of their respective bands.}
    \label{fig:deltaf_pos}
  \end{center}
\end{figure}

% fpp
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{fpp_position.pdf}
    \caption{Position dependence on the fabrication wafer of the peak-to-peak frequency swing $\Delta f_{p2p}$.  Note that these positions are only approximate - for simplicity, all missing channels are assumed to be at the top edge of their respective bands.}
    \label{fig:fpp_pos}
  \end{center}
\end{figure}

% lambda
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{lambda_position.pdf}
    \caption{Position dependence on the fabrication wafer of $\lambda_{SQUID}$.  Note that these positions are only approximate - for simplicity, all missing channels are assumed to be at the top edge of their respective bands.}
    \label{fig:lambda_pos}
  \end{center}
\end{figure}

% M_fr
\begin{figure}[H]
  \begin{center}
    \includegraphics[width=\textwidth]{M_position.pdf}
    \caption{Position dependence on the fabrication wafer of the mutual inductance between the flux ramp line and the SQUID, $M_{FR, SQUID}$.  Note that these positions are only approximate - for simplicity, all missing channels are assumed to be at the top edge of their respective bands.}
    \label{fig:M_pos}
  \end{center}
\end{figure}




\end{document}
"""

# write it to a file
tex_filename = os.path.join(report_dir, f"wafer_{wafer[0]:02d}_report.tex")
with open(tex_filename, 'w') as f:
    f.write(report_text)

# compile it into a pdf
# need to call this 2x in order to get internal references to work
os.system(f"pdflatex -aux-directory={report_dir} -output-directory={report_dir} {tex_filename}")
os.system(f"pdflatex -aux-directory={report_dir} -output-directory={report_dir} {tex_filename}")

# clean up the misc files that pdflatex creates that I never look at
os.system(r"del {:s}".format(os.path.join(report_dir, "*.aux")))
os.system(r"del {:s}".format(os.path.join(report_dir, "*.log")))
os.system(r"del {:s}".format(os.path.join(report_dir, "*.out")))
os.system(r"del {:s}".format(os.path.join(report_dir, "*.toc")))

# open the report pdf
report_file = os.path.join(report_dir, f"wafer_{wafer[0]:02d}_report.pdf")
if show_report:
    os.system(r"start {:s}".format(report_file))
