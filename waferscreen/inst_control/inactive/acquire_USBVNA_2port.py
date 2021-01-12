import time
import numpy as np
import sys
import math
import matplotlib.pyplot as plt
sys.path.append('..//Drivers')
sys.path.append('..//PlotModules')
from waferscreen.inst_control.Keysight_USB_VNA import USBVNA

"""
Code which will take an S21 measurement with a Keysight USB VNA (P937XA) and plot it LM and in a Smith Chart
And then write the data to a file with (freq, s21A, s21B) where A and B are determined by the data_format
"""

outputfilename = "C:\\Users\\jac15\\Code\\VNA\\Data\\SO_launch\\oldboard_short_rm_re" # leave extension off, added according to file type

#calibration options
calfilename = "CalSet_1"
cal_vna = True

#output format settings
data_format = 'RI'  # 'LM' or 'RI' # records this data type in file
output_format = 'TXT'  # 'TXT' or 'CSV' or 'BOTH'

#plotting options
plotphase = True

#User VNA settings (some settings will be set by cal if applied)
vna_address     = "TCPIP0::687JC1::hislip0,4880::INSTR" #go into Keysight GUI, Utility>System>System Setup>Remote Interface -> First enable HiSLIP Interface, then find instrument address in SCPI Parser Console>Status>HiSLIP
flow            = 0.001 #GHz
fhigh           = 9     #GHz
num_freq_points = 401   #number of frequency points to measure at
sweeptype       = 'lin' #lin or log in freq space
if_bw           = 10    #Hz
ifbw_track      = False #ifbw tracking, reduces IFBW at low freq to overcome 1/f noise
port_power      = 0     #dBm
vna_avg         = 1     #number of averages. if one, set to off
preset_vna      = True  #preset the VNA? Do if you don't know the state of the VNA ahead of time

##########################################################
####Code begins here######################################
##########################################################

# Set up Network Analyzer
vna = USBVNA(address=vna_address)  # "PXI10::0-0.0::INSTR") #"PXI10::CHASSIS1::SLOT1::FUNC0::INSTR"
if preset_vna:
    vna.preset()
vna.setup2port()
if cal_vna:
    vna.set_cal(calfilename, calstate = "ON")
else: # if you're not applying a cal, you need to specify settings
    vna.set_freq_limits(start = flow, stop = fhigh)
    vna.set_sweep(num_freq_points, type = sweeptype)
    vna.set_ifbw(if_bw,track = ifbw_track)
    vna.set_power(port = 1, level = port_power, state = "ON")
vna.set_avg(count = vna_avg)
time.sleep(1.0) #sleep for a second in case we've just over-powered the resonators

#Figure out frequency points for recording
fmin = flow  #fcenter - fspan/(2000.0)
fmax = fhigh #fcenter + fspan/(2000.0)
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

#collect data in RI format
(s11A,s11B) = vna.get_trace(1,format = 'RI')
print("S11 acquired")
(s12A,s12B) = vna.get_trace(2,format = 'RI')
print("S12 acquired")
(s21A,s21B) = vna.get_trace(3,format = 'RI')
print("S21 acquired")
(s22A,s22B) = vna.get_trace(4,format = 'RI')
print("S22 acquired")

vna.reset_sweep()
vna.close()

#put data in complex format
sdata = []
for i in range(0,len(freqs)):
    sdata.append([[s11A[i] + 1j*s11B[i],s12A[i] + 1j*s12B[i]],[s21A[i] + 1j*s21B[i],s22A[i] + 1j*s22B[i]]])
sdata = np.array(sdata)

#Save the data
if output_format == "TXT" or output_format == "BOTH":
    fout = open(outputfilename + '.txt', 'w')
    for i in range(0,len(freqs)):
        if data_format == 'LM':
            s11LM = 20.0*np.log10(np.absolute(sdata[i,0,0]))
            s12LM = 20.0*np.log10(np.absolute(sdata[i,0,1]))
            s21LM = 20.0*np.log10(np.absolute(sdata[i,1,0]))
            s22LM = 20.0*np.log10(np.absolute(sdata[i,1,1]))
            s11PH = 180.0/math.pi*np.arctan2(np.imag(sdata[i,0,0]),np.real(sdata[i,0,0]))
            s12PH = 180.0/math.pi*np.arctan2(np.imag(sdata[i,0,1]),np.real(sdata[i,0,1]))
            s21PH = 180.0/math.pi*np.arctan2(np.imag(sdata[i,1,0]),np.real(sdata[i,1,0]))
            s22PH = 180.0/math.pi*np.arctan2(np.imag(sdata[i,1,1]),np.real(sdata[i,1,1]))
            out = str(freqs[i]) + " " + str(s11LM) + " " + str(s11PH) +  " " + str(s12LM) + " " + str(s12PH) +  " " + str(s21LM) + " " + str(s21PH) +  " " + str(s22LM) + " " + str(s22PH) + "\n"
        elif data_format == 'RI':
            out = str(freqs[i]) + " " + str(np.real(sdata[i,0,0])) + " " + str(np.imag(sdata[i,0,0])) + " " + str(np.real(sdata[i,0,1])) + " " + str(np.imag(sdata[i,0,1])) + " " + str(np.real(sdata[i,1,0])) + " " + str(np.imag(sdata[i,1,0])) + " " + str(np.real(sdata[i,1,1])) + " " + str(np.imag(sdata[i,1,1])) + "\n"
        else:
            print('Data format not recognized!')
        fout.write(out)
    fout.close()
    print('TXT file written')
if output_format == "CSV" or output_format == "BOTH":
    print("Need to code CSV writer")
    # with open(outputfilename + '.csv', 'w') as csvfile:
        # csvwriter = csv.writer(csvfile, delimiter=',')
        # for i in range(0,len(freqs)):
            # if data_format == 'LM':
                # csvwriter.writerow([freqs[i],s21LM[i],s21PH[i]])
            # elif data_format == 'RI':
                # csvwriter.writerow([freqs[i],s21R[i],s21I[i]])
            # else:
                # print('Data format not recognized!')
    # print('CSV file written')

#create figure w/ plot labels
fig1 = plt.figure(1)
fig1.subplots_adjust(top=0.94,bottom=0.07,left=0.075,right=0.945,hspace=0.2,wspace=0.26)
#s11
ax11 = fig1.add_subplot(221)
ax11.set_xlabel("Freq. (GHz)")
if sweeptype == 'log':
    ax11.set_xscale('log')
ax11.set_ylabel(r"$\left| S_{11} \right|^2$ (dB)")
if plotphase:
    ax11t = ax11.twinx()
    ax11t.set_ylabel(r"$\angle S_{11}$ (deg)")
#s12
ax12 = fig1.add_subplot(222)
ax12.set_xlabel("Freq. (GHz)")
if sweeptype == 'log':
    ax12.set_xscale('log')
ax12.set_ylabel(r"$\left| S_{12} \right|^2$ (dB)")
if plotphase:
    ax12t = ax12.twinx()
    ax12t.set_ylabel(r"$\angle S_{12}$ (deg)")
#s21
ax21 = fig1.add_subplot(223)
ax21.set_xlabel("Freq. (GHz)")
if sweeptype == 'log':
    ax21.set_xscale('log')
ax21.set_ylabel(r"$\left| S_{21} \right|^2$ (dB)")
if plotphase:
    ax21t = ax21.twinx()
    ax21t.set_ylabel(r"$\angle S_{21}$ (deg)")
#s22
ax22 = fig1.add_subplot(224)
ax22.set_xlabel("Freq. (GHz)")
if sweeptype == 'log':
    ax22.set_xscale('log')
ax22.set_ylabel(r"$\left| S_{22} \right|^2$ (dB)")
if plotphase:
    ax22t = ax22.twinx()
    ax22t.set_ylabel(r"$\angle S_{22}$ (deg)")
#plot s11
ax11.plot(freqs,20.0*np.log10(np.absolute(sdata[:,0,0])))
if plotphase:
    ax11t.plot(freqs,180.0/math.pi*np.arctan2(np.imag(sdata[:,0,0]),np.real(sdata[:,0,0])),c='r')
#plot s12
ax12.plot(freqs,20.0*np.log10(np.absolute(sdata[:,0,1])))
if plotphase:
    ax12t.plot(freqs,180.0/math.pi*np.arctan2(np.imag(sdata[:,0,1]),np.real(sdata[:,0,1])),c='r')
#plot s21
ax21.plot(freqs,20.0*np.log10(np.absolute(sdata[:,1,0])))
if plotphase:
    ax21t.plot(freqs,180.0/math.pi*np.arctan2(np.imag(sdata[:,1,0]),np.real(sdata[:,1,0])),c='r')
#plot s22
ax22.plot(freqs,20.0*np.log10(np.absolute(sdata[:,1,1])))
if plotphase:
    ax22t.plot(freqs,180.0/math.pi*np.arctan2(np.imag(sdata[:,1,1]),np.real(sdata[:,1,1])),c='r')
    
ax11.grid(True)
ax12.grid(True)
ax21.grid(True)
ax22.grid(True)
    
#show maximized plot
figManager = plt.get_current_fig_manager()
figManager.window.showMaximized()
plt.show()