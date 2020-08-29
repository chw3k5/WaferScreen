import numpy as np
import math
import time
import os
from ref import output_dir, today_str
from waferscreen.inst_control import Keysight_USB_VNA
from waferscreen.inst_control import srs_sim928
from waferscreen.analyze.find_and_fit import ResParams

###
#  This code takes a single flux ramp sweep at one RF read power over a number of resonators
###
wafer = 7
trace_number = 0
run_number = 3
# output location
# datafolder = "C:\\datafolder"
# datafilename = "datafilename" #text file of f, re,
data_output_folder = os.path.join(output_dir, 's21', F"{wafer}", F'Trace{trace_number}', today_str, "flux_ramp")  # "C:\\Users\\uvwave\\Desktop\\Jake_VNA\\Data\\29Aug2020\\wafer7_band0_fluxramp_run2\\"
if not os.path.isdir(data_output_folder):
    os.mkdir(data_output_folder)
file_delimiter = ","

# resonator frequencies file
freqs_filename = os.path.join(output_dir, 's21', F"{wafer}", F'Trace{trace_number}', today_str,
                              F"{wafer}_Trace{str(trace_number)}_{today_str}_run{run_number}_fit.csv")  # "C:\\Users\\uvwave\\Desktop\\Jake_VNA\\Data\\29Aug2020\\wafer7_band0_150mK_freqs.txt"
res_freq_units = "GHz"
res_num_limits = [1, -1]  # set to -1 to ignore limits

# instrument addresses
vna_address = "TCPIP0::687UWAVE-TEST::hislip_PXI10_CHASSIS1_SLOT1_INDEX0::INSTR"  # go into Keysight GUI, enable HiSlip Interface, find address in SCPI Parser I/O
volt_source_address = "GPIB0::16::INSTR"
volt_source_port = 1

# frequency sweep options
meas_span = 1000  # kHz
num_pts_per_sweep = 501  # 1601 for Aly8722ES, 100001 for P5002A
port_power = -40  # dBm
if_bw = 300  # Hz
ifbw_track = False  # ifbw tracking, reduces IFBW at low freq to overcome 1/f noise
vna_avg = 1  # number of averages. if one, set to off
preset_vna = False  # preset the VNA? Do if you don't know the state of the VNA ahead of time
keep_away_collisions = True  # option to modify frequency boundaries of s21 measurement so that we can fit better

# flux ramp options
rseries = 10000  # ohms
current_min = -125  # uA
current_max = 125  # uA
current_steps = 251
currents = np.linspace(current_min, current_max, current_steps)
volts = np.linspace(current_min * rseries * 1e-6, current_max * rseries * 1e-6, current_steps)  # volts
print("Currents to measure at:")
print(currents)
# make sure volts are in integer # of mV so SRS doesn't freak out
for i in range(0, len(volts)):
    millivolts = int(round(volts[i] * 1000))
    volts[i] = millivolts / 1000
print("Voltages to measure at:")
print(volts)

###group delay removal (best to get correct within 180degs over dataset) ####
remove_group_delay = True
group_delay = 27.292  # nanoseconds

# open resonant frequencies file
with open(freqs_filename, 'r') as f:
    lines = f.readlines()
header = lines[0].strip().split(",")
res_params = []
for line in lines[1:]:
    datavec = line.split(",")
    res_params.append(ResParams(**{column_name: float(value) for column_name, value in zip(header, datavec)}))
res_freqs = np.array([res_param.f0 for res_param in res_params])


# put res freqs into GHz since fittng code requires it
if res_freq_units == "MHz":
    res_freqs = res_freqs / 1e3
elif res_freq_units == "kHz":
    res_freqs = res_freqs / 1e6
elif res_freq_units == "Hz":
    res_freqs = res_freqs / 1e9

# figure out boundaries between resonators so we don't measure a neighbor
freq_bounds = []
approach_factor = 0.65  # fraction of distance between resonators to draw boundary, should be between 0.5 and 1
for i, freq in list(enumerate(res_freqs)):
    if i == 0:
        lower_bound = freq - meas_span * 1e-6 / 2.0
        if (res_freqs[i + 1] - res_freqs[i]) * approach_factor < meas_span * 1e-6 / 2.0:
            upper_bound = res_freqs[i] + (res_freqs[i + 1] - res_freqs[i]) * approach_factor
        else:
            upper_bound = res_freqs[i] + meas_span * 1e-6 / 2.0
    elif i == len(res_freqs) - 1:
        upper_bound = res_freqs[i] + meas_span * 1e-6 / 2.0
        if (res_freqs[i] - res_freqs[i - 1]) * approach_factor < meas_span * 1e-6 / 2.0:
            lower_bound = res_freqs[i] - (res_freqs[i] - res_freqs[i - 1]) * approach_factor
        else:
            lower_bound = res_freqs[i] - meas_span * 1e-6 / 2.0
    else:
        if (res_freqs[i] - res_freqs[i - 1]) * approach_factor < meas_span * 1e-6 / 2.0:
            lower_bound = res_freqs[i] - (res_freqs[i] - res_freqs[i - 1]) * approach_factor
        else:
            lower_bound = res_freqs[i] - meas_span * 1e-6 / 2.0
        if (res_freqs[i + 1] - res_freqs[i]) * approach_factor < meas_span * 1e-6 / 2.0:
            upper_bound = res_freqs[i] + (res_freqs[i + 1] - res_freqs[i]) * approach_factor
        else:
            upper_bound = res_freqs[i] + meas_span * 1e-6 / 2.0
    freq_bounds.append([lower_bound, upper_bound])
freq_bounds = np.array(freq_bounds)

print("")
total_est_time = (current_steps * len(res_freqs) * (0.5 + num_pts_per_sweep / if_bw)) / 3600.0
print("Total time to do FR sweep: " + str(total_est_time) + " hours")

# connect to USB VNA
# Set up Network Analyzer
vna = Keysight_USB_VNA.USBVNA(address=vna_address)
if preset_vna:
    vna.preset()
vna.setup_thru()
vna.set_cal(calstate='OFF')  # get raw S21 data
vna.set_freq_center(center=res_freqs[0], span=meas_span * 1e-6)
vna.set_sweep(num_pts_per_sweep, type='lin')
vna.set_avg(count=vna_avg)
vna.set_ifbw(if_bw, track=ifbw_track)
vna.set_power(port=1, level=port_power, state="ON")
time.sleep(1.0)  # sleep for a second in case we've just over-powered the resonators

print("")

# connect to SIM928
voltsource = srs_sim928.SRS_SIM928(address=volt_source_address, port=volt_source_port)
voltsource.setvolt(volts[0])
voltsource.output_on()

print("")

for j in range(0, len(res_freqs)):

    # only fit resonators we want to fit...
    mask_res = False
    if res_num_limits[0] != -1 and res_num_limits[1] != -1:
        if j >= res_num_limits[0] and j <= res_num_limits[1]:
            mask_res = True
    elif res_num_limits[0] == -1 and res_num_limits[1] != -1:
        if j <= res_num_limits[1]:
            mask_res = True
    elif res_num_limits[0] != -1 and res_num_limits[1] == -1:
        if j >= res_num_limits[0]:
            mask_res = True
    elif res_num_limits[0] == -1 and res_num_limits[1] == -1:
        mask_res = True
    else:
        print("There is an error in this code....")

    if mask_res:

        # set frequency limits
        if keep_away_collisions:
            vna.set_freq_limits(start=freq_bounds[j, 0], stop=freq_bounds[j, 1])
            freqs = np.linspace(freq_bounds[j, 0], freq_bounds[j, 1], num_pts_per_sweep)
        else:
            vna.set_freq_center(center=res_freqs[j], span=meas_span * 1e-6)
            freqs = np.linspace(res_freqs[j] - meas_span * 1e-6 / 2.0, res_freqs[j] + meas_span * 1e-6 / 2.0,
                                num_pts_per_sweep)
        vna.set_sweep(num_pts_per_sweep, type='lin')

        for k in range(0, len(volts)):

            # set voltage source
            cur_volt = voltsource.getvolt()
            while abs(cur_volt - volts[k]) > 0.001:
                voltsource.setvolt(volts[k])
                time.sleep(0.1)
                cur_volt = voltsource.getvolt()
            time.sleep(0.1)

            print("Measuring resonator # " + str(j + 1) + "/" + str(len(res_freqs)) + " at flux bias current " + str(
                currents[k]) + "uA")

            # trigger a sweep to be done
            vna.reset_sweep()
            vna.trig_sweep()

            # collect data according to data_format LM or RI
            (s21Au, s21Bu) = vna.get_S21(format='RI')
            print("Trace Acquired")

            # put uncalibrated data in complex format
            s21 = []
            for i in range(0, len(freqs)):
                s21.append(s21Au[i] + 1j * s21Bu[i])
            s21 = np.array(s21)

            # remove group delay
            if remove_group_delay:
                phase_factors = np.exp(-1j * 2.0 * math.pi * freqs * group_delay)
                s21 = s21 / phase_factors

            if currents[k] >= 0:
                ind_filename = "sdata_res_" + str(int(round(j))) + "_cur_" + str(int(round(currents[k]))) + "uA.csv"
            else:
                ind_filename = "sdata_res_" + str(int(round(j))) + "_cur_m" + str(
                    int(round(-1 * currents[k]))) + "uA.csv"

            # write out sdata
            f = open(os.path.join(data_output_folder, ind_filename), 'w')
            for i in range(0, len(freqs)):
                f.write(str(freqs[i]) + "," + str(s21[i].real) + "," + str(s21[i].imag) + "\n")
            f.close()

# close connection to instruments
vna.reset_sweep()
vna.close()
voltsource.setvolt(0.0)
voltsource.output_off()
voltsource.close()

print("Connection to Instruments Closed")
