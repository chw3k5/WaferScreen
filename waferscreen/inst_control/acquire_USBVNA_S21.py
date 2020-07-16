import time
import numpy as np
import sys
sys.path.append('..//Drivers')
sys.path.append('..//PlotModules')
import math
import csv
import matplotlib.pyplot as plt
from waferscreen.inst_control.Keysight_USB_VNA import USBVNA

#####
# Code which will take an S21 measurement with a Keysight USB VNA (P937XA) and plot it LM and in a Smith Chart
# And then write the data to a file with (freq, s21A, s21B) where A and B are determined by the data_format
#####

outputfilename = "C:\\Users\\jac15\\Code\\VNA\\Data\\test_sweep"  # leave extension off, added according to file type

#group delay removel settings
group_delay = 2.787 #nanoseconds
remove_group_delay = True #just removes phase delay

#output format settings
data_format = 'RI' # 'LM' or 'RI' # records this data type in file
output_format = 'TXT' # 'TXT' or 'CSV' or 'BOTH'
plotphase = 1

#User VNA settings
vna_address     = "TCPIP0::687JC1::hislip0,4880::INSTR" #go into Keysight GUI, enable HiSlip Interface, find address in SCPI Parser I/O
fcenter         = 6     #GHz
fspan           = 4000  #MHz
num_freq_points = 201   #number of frequency points to measure at
sweeptype       = 'lin' #lin or log in freq space
if_bw           = 10    #Hz
ifbw_track      = False #ifbw tracking, reduces IFBW at low freq to overcome 1/f noise
port_power      = -40   #dBm
vna_avg         = 1     #number of averages. if one, set to off
preset_vna      = False #preset the VNA? Do if you don't know the state of the VNA ahead of time

##########################################################
####Code begins here######################################
##########################################################

#Set up Network Analyzer
vna = USBVNA(address=vna_address) #"PXI10::0-0.0::INSTR") #"PXI10::CHASSIS1::SLOT1::FUNC0::INSTR"
if preset_vna:
    vna.preset()
vna.setup_thru()
vna.set_cal(calstate = 'OFF') # get raw S21 data
vna.set_freq_center(center = fcenter, span = fspan/1000.0)
vna.set_sweep(num_freq_points, type = sweeptype)
vna.set_avg(count = vna_avg)
vna.set_ifbw(if_bw,track = ifbw_track)
vna.set_power(port = 1, level = port_power, state = "ON")
time.sleep(1.0) #sleep for a second in case we've just over-powered the resonators

#Figure out frequency points for recording
fmin = fcenter - fspan/(2000.0)
fmax = fcenter + fspan/(2000.0)
if sweeptype == "lin":
    freqs = np.linspace(fmin,fmax,num_freq_points)
elif sweeptype == 'log':
    logfmin = np.log10(fmin)
    logfmax = np.log10(fmax)
    logfreqs = np.linspace(logfmin,logfmax,num_freq_points)
    freqs = 10**logfreqs
    
#trigger a sweep to be done    
vna.reset_sweep()
vna.trig_sweep()

#collect data according to data_format LM or RI
(s21Au,s21Bu) = vna.get_S21(format = 'RI')
print("Trace Acquired")

#put uncalibrated data in complex format
s21data = []
for i in range(0,len(freqs)):
    s21data.append(s21Au[i] + 1j*s21Bu[i])
s21data = np.array(s21data)

#remove group delay if desired
if not remove_group_delay:
    group_delay = 0.0
phase_delay = np.exp(-1j*freqs*2.0*math.pi*group_delay)

#calculate the 'calibrated' S21 data by dividing by phase delay
s21R = []
s21I = []
for i in range(0, len(freqs)):
    s21R.append(np.real(s21data[i]/phase_delay[i]))
    s21I.append(np.imag(s21data[i]/phase_delay[i]))
s21R = np.array(s21R)
s21I = np.array(s21I)

#convert data from data_format to both LM for plotting
s21LM = []
s21PH = []
for i in range(0, len(freqs)):
    s21LM.append(10*np.log10(s21R[i]**2 + s21I[i]**2))
    s21PH.append(180.0/math.pi*math.atan2(s21I[i],s21R[i]))
s21LM = np.array(s21LM)
s21PH = np.array(s21PH)

vna.reset_sweep()
vna.close()

plot_freqs = []
for i in range(0,len(freqs)):
    plot_freqs.append(freqs[i])
plot_freqs = np.array(plot_freqs)

fig1 = plt.figure(1)

ax11 = fig1.add_subplot(121)
ax11.set_xlabel("Freq. (GHz)")
if sweeptype == 'log':
    ax11.set_xscale('log')
ax11.set_ylabel("S21 (dB)")
if plotphase:
    ax11t = ax11.twinx()
    ax11t.set_ylabel("S21 (deg)")
ax12 = pySmith.get_smith(fig1, 122)
    
#plot Log Magnitude and possibly Phase data
ax11.plot(plot_freqs,s21LM)
if plotphase == 1:
    ax11t.plot(plot_freqs,s21PH,c='r')
    
#plot Smith Chart data
ax12.plot(s21R,s21I)

#Save the data
if output_format == "TXT" or output_format == "BOTH":
    fout = open(outputfilename + '.txt', 'w')
    for i in range(0,len(freqs)):
        if data_format == 'LM':
            out = str(freqs[i]) + " " + str(s21LM[i]) + " " + str(s21PH[i]) + "\n"
        elif data_format == 'RI':
            out = str(freqs[i]) + " " + str(s21R[i]) + " " + str(s21I[i]) + "\n"
        else:
            print('Data format not recognized!')
        fout.write(out)
    fout.close()
    print('TXT file written')
if output_format == "CSV" or output_format == "BOTH":
    with open(outputfilename + '.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        for i in range(0,len(freqs)):
            if data_format == 'LM':
                csvwriter.writerow([freqs[i],s21LM[i],s21PH[i]])
            elif data_format == 'RI':
                csvwriter.writerow([freqs[i],s21R[i],s21I[i]])
            else:
                print('Data format not recognized!')
    print('CSV file written')
else:
    print('Output file format not recoginzed!')
    
#show maximized plot
figManager = plt.get_current_fig_manager()
figManager.window.showMaximized()
plt.show()