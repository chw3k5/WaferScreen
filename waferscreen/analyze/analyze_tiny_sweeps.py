import numpy as np
import math
import os
import time
from ref import output_dir, today_str, vna_address
from waferscreen.analyze import resonator_fitter as fit_res
from waferscreen.analyze.find_and_fit import ResParams

# data location
wafer = 7
trace_number = 0
run_number = 3
parent_data_folder = os.path.join(output_dir, 's21', F"{wafer}", F"Trace{trace_number}", today_str)
datafolder = os.path.join(parent_data_folder, 'flux_ramp')  # "C:\\Users\\uvwave\\Desktop\\Jake_VNA\\Data\\29Aug2020\\wafer7_band0_fluxramp_run1\\"
fit_num = 1
sdata_freq_units = "GHz"

# resonator frequencies file
freqs_filename = os.path.join(parent_data_folder,
                              F"{wafer}_Trace{str(trace_number)}_{today_str}_run{run_number}_fit.csv")
res_freq_units = "GHz"
delimiter = ","
res_num_limits = [39, -1]  # set to -1 to ignore

# flux ramp options
current_min = -125  # 100 # uA
current_max = 125  # uA
current_steps = 251  # 41
currents = np.linspace(current_min, current_max, current_steps)
print(currents)

###group delay removal (best to get correct within 180degs over dataset) ####
remove_group_delay = True
group_delay = 0  # nanoseconds

###resonator fitting options ####
throw_out = 0  # doesnt use N points on the edge of each sweep
fit_model = 'simple_res_gain_slope_complex'  # name of model to fit to resonance
error_est = 'prop'  # 'prop' or 'flat', proportional or constant errors
fit_guess_plots = False  # make plots of each fit guess

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

# loop over currents and fit each resonator in each file
for i in range(0, len(res_freqs)):

    # only fit resonators we want to fit...
    mask_res = False
    if res_num_limits[0] != -1 and res_num_limits[1] != -1:
        if i >= res_num_limits[0] and i <= res_num_limits[1]:
            mask_res = True
    elif res_num_limits[0] == -1 and res_num_limits[1] != -1:
        if i <= res_num_limits[1]:
            mask_res = True
    elif res_num_limits[0] != -1 and res_num_limits[1] == -1:
        if i >= res_num_limits[0]:
            mask_res = True
    elif res_num_limits[0] == -1 and res_num_limits[1] == -1:
        mask_res = True
    else:
        print("There is an error in this code....")

    if mask_res:

        # figure out output filename
        output_filename = datafolder + "sdata_res_" + str(int(round(i))) + "_fit_" + str(int(round(fit_num))) + ".txt"
        # make file to write results out to
        f = open(output_filename, "w")
        f.close()

        for k in range(0, len(currents)):

            # figure out input filename
            if currents[k] >= 0:
                input_filename = datafolder + "sdata_res_" + str(int(round(i))) + "_cur_" + str(
                    int(round(currents[k]))) + "uA.txt"
            else:
                input_filename = datafolder + "sdata_res_" + str(int(round(i))) + "_cur_m" + str(
                    int(round(-1 * currents[k]))) + "uA.txt"

            # check if input file exists yet
            if os.path.isfile(input_filename):
                time.sleep(0.1)  # make sure no one is writing to this file anymore
            ever_False = False
            while os.path.isfile(input_filename) is False:
                ever_false = True
                print("Waiting for data to be taken")
                time.sleep(0.2)
            if ever_False:
                time.sleep(
                    0.4)  # if we had to wait for it to be created, just wait again to make sure we aren't opening during writing

            # now check that no one is writing to this file currently ### this doesn't work since I don't have the right permissions on Lazarus' computer
            # still_writing = True
            # while still_writing:
            #    still_writing = False
            #    #iterate through processes and check if one of them is writing to this file
            #    for proc in psutil.process_iter():
            #        for item in proc.open_files():
            #            if input_filename == item.path:
            #                #soemthing is writing to this file
            #                still_writing = True
            #    if still_writing:
            #        time.sleep(0.1)
            #        print("File being written to still")

            # open data file and consume freqs, real and imag
            f = open(input_filename, 'r')
            data = []
            freqs = []
            s21 = []
            for line in f:
                datavec = line.split(delimiter)
                datarow = []
                for j in range(0, len(
                        datavec)):  # loop through parsed items and make sure they're not returns or spaces or some combo
                    if datavec[j] != " " and datavec[j] != "\r" and datavec[j] != "\n" and datavec[j] != "\r\n" and \
                            datavec[j] != "\n\r" and datavec[j] != " \r\n":
                        datarow.append(float(datavec[j]))
                data.append(datarow)
            data = np.array(data)
            f.close()
            freqs = data[:, 0]
            s21 = data[:, 1] + 1j * data[:, 2]

            # put freqs into GHz since fittng code requires it
            if sdata_freq_units == "MHz":
                freqs = freqs / 1e3
            elif sdata_freq_units == "kHz":
                freqs = freqs / 1e6
            elif sdata_freq_units == "Hz":
                freqs = freqs / 1e9

            # remove group delay if desired
            if remove_group_delay:
                phase_factors = np.exp(-1j * 2.0 * math.pi * freqs * group_delay)
                s21 = s21 / phase_factors

            # fit resonator model
            print("Fitting found resonance #" + str(i + 1) + "/" + str(len(res_freqs)) + " at FR current " + str(
                currents[k]) + "uA")
            # only pass section of data that's within range of the resonance
            # now fit the resonance
            try:
                popt, pcov = fit_res.fit_resonator(freqs, s21, data_format='COM', model=fit_model, error_est=error_est,
                                                   throw_out=throw_out, make_plot=fit_guess_plots)

                fit_Amag = popt[0]
                fit_Aphase = popt[1]
                fit_Aslope = popt[2]
                fit_tau = popt[3]
                fit_f0 = popt[4]
                fit_Qi = popt[5]
                fit_Qc = popt[6]
                fit_Zratio = popt[7]

                error_Amag = np.sqrt(pcov[0, 0])
                error_Aphase = np.sqrt(pcov[1, 1])
                error_Aslope = np.sqrt(pcov[2, 2])
                error_tau = np.sqrt(pcov[3, 3])
                error_f0 = np.sqrt(pcov[4, 4])
                error_Qi = np.sqrt(pcov[5, 5])
                error_Qc = np.sqrt(pcov[6, 6])
                error_Zratio = np.sqrt(pcov[7, 7])

                print('Fit Result')
                print('Amag          : %.4f +/- %.6f' % (fit_Amag, error_Amag))
                print('Aphase        : %.2f +/- %.4f Deg' % (fit_Aphase, error_Aphase))
                print('Aslope        : %.3f +/- %.3f /GHz' % (fit_Aslope, error_Aslope))
                print('Tau           : %.3f +/- %.3f ns' % (fit_tau, error_tau))
                print('f0            : %.8f +/- %.8f GHz' % (fit_f0, error_f0))
                print('Qi            : %.0f +/- %.0f' % (fit_Qi, error_Qi))
                print('Qc            : %.0f +/- %.0f' % (fit_Qc, error_Qc))
                print('Im(Z0)/Re(Z0) : %.2f +/- %.3f' % (fit_Zratio, error_Zratio))
                print('')
            except:
                print("Fitting Error, returning zeros for fit results")
                print("")
                popt = np.zeros(8)
                pcov = np.zeros((8, 8))

            f = open(output_filename, "a")
            f.write(
                str(currents[k]) + "," + str(popt[0]) + "," + str(np.sqrt(pcov[0, 0])) + "," + str(popt[1]) + "," + str(
                    np.sqrt(pcov[1, 1])) + "," + str(popt[2]) + "," + str(np.sqrt(pcov[2, 2])) + "," + str(
                    popt[3]) + "," + str(np.sqrt(pcov[3, 3])) + "," + str(popt[4]) + "," + str(
                    np.sqrt(pcov[4, 4])) + "," + str(popt[5]) + "," + str(np.sqrt(pcov[5, 5])) + "," + str(
                    popt[6]) + "," + str(np.sqrt(pcov[6, 6])) + "," + str(popt[7]) + "," + str(
                    np.sqrt(pcov[7, 7])) + "\n")
            f.close()