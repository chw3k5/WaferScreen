#!/usr/bin/python
import numpy as np
import math
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter


def find_resonances(freqs, 
                    sdata, 
                    group_delay_ns=0,
                    edge_search_depth=50,
                    smoothing_scale_kHz=75,
                    smoothing_order=5,
                    cutoff_rate=500,
                    minimum_spacing_kHz=100.0,
                    remove_baseline_ripple=True,
                    baseline_scale_kHz=3000,
                    baseline_order=3,
                    input_freq_units="GHz",
                    write_out_freqs=False,
                    freqs_filename="D:\\Data\\uMux\\scratch\\test_freq_output.txt",
                    verbose=False,
                    make_plots=False):
    """
    Resonance Finding Script
    Written by Jake Connors 24 Jan 2020, v2 10 March 2020
    Consumes an array of complex s21 transmission data
    Removes absolute gain, gain slope and group delay from data
    Smooths data using a savitsky-golay filter to reduce noise in derivatives
    Optionally removes baseline ripple using a wider savitsky-golay filter
    Takes complex 1st derivative of s21 data w.r.t. frequency
    Finds component of 1st derivative in the amplitude and phase directions given s21 position
    Searches for maxima of Qt~f/2*ds21/df*theta-hat above a given threshold and minimum spacing to identify resonances
    Returns a list of resonant frequencies and optionally writes this to a text file
    """

    # start by converting frequencies to GHz and making sure it is in array form
    if input_freq_units == "Hz":
        freqs = np.array(freqs)*1e-9 #convert to GHz from Hz
    elif input_freq_units == "kHz":
        freqs = np.array(freqs)*1e-6 #convert to GHz from kHz
    elif input_freq_units == "MHz":
        freqs = np.array(freqs)*1e-3 #convert to GHz from MHz
    elif input_freq_units == "GHz":
        freqs = np.array(freqs) #no need to convert
        
    if verbose:
        print("Taken in Data")
        
    # now remove given group delay and make sure sdata is array
    phase_factors = np.exp(-1j*2.0*math.pi*freqs*group_delay_ns) #e^(-j*w*t)
    sdata = np.array(sdata)/phase_factors
    
    if verbose:
        print("Removed Group Delay")

    # figure out complex gain and gain slope
    ave_left_gain = 0
    ave_right_gain = 0
    for j in range(0,edge_search_depth):
        ave_left_gain = ave_left_gain + sdata[j]/edge_search_depth
        ave_right_gain = ave_right_gain + sdata[len(sdata)-1-j]/edge_search_depth
    left_freq =  freqs[int(edge_search_depth/2.0)]
    right_freq = freqs[len(freqs)-1-int(edge_search_depth/2.0)]
    gain_slope = (ave_right_gain-ave_left_gain)/(right_freq-left_freq)
    if verbose:
        # calculate extra group delay and abs gain slope removed for printing out purposes
        left_phase = np.arctan2(np.imag(ave_left_gain),np.real(ave_left_gain))
        right_phase = np.arctan2(np.imag(ave_right_gain),np.real(ave_right_gain))
        excess_tau = (left_phase - right_phase)/(2.0*math.pi*(right_freq-left_freq))
        abs_gain = np.absolute(0.5*ave_right_gain + 0.5*ave_left_gain)
        abs_gain_slope = (np.absolute(ave_right_gain)-np.absolute(ave_left_gain))/(right_freq-left_freq)
        print("Removing an excess group delay of " + str(excess_tau) + "ns from data")
        print("Removing a gain of " + str(abs_gain) + " and slope of " + str(abs_gain_slope) + "/GHz from data")
    gains = ave_left_gain + (freqs-left_freq)*gain_slope
    sdata = sdata/gains
    
    if verbose:
        print("Removed Group Delay and Gain")

    #remove baseline ripple if desired
    if remove_baseline_ripple:
        freq_spacing = (freqs[1]-freqs[0])*1e6 #GHz -> kHz
        baseline_scale = int(round(baseline_scale_kHz/freq_spacing))
        if baseline_scale%2 == 0: #if even
            baseline_scale = baseline_scale + 1 #make it odd
        if verbose:
            print("Freq Spacing is " + str(freq_spacing) + "kHz")
            print("Requested baseline smoothing scale is " + str(baseline_scale_kHz) + "kHz")
            print("Number of points to smooth over is " + str(baseline_scale))
        #smooth s21 trace in both real and imaginary to do peak finding
        baseline_real = savgol_filter(np.real(sdata), baseline_scale, baseline_order)
        baseline_imag = savgol_filter(np.imag(sdata), baseline_scale, baseline_order)
        baseline = np.array(baseline_real + 1j*baseline_imag)
        pre_baseline_removal_sdata = np.copy(sdata)
        sdata = sdata/baseline
    
    #figure out freq spacing, convert smoothing_scale_kHz to smoothing_scale (must be an odd number)
    freq_spacing = (freqs[1]-freqs[0])*1e6 #GHz -> kHz
    smoothing_scale = int(round(smoothing_scale_kHz/freq_spacing))
    if smoothing_scale%2 == 0: #if even
        smoothing_scale = smoothing_scale + 1 #make it odd
    if verbose:
        print("Freq Spacing is " + str(freq_spacing) + "kHz")
        print("Requested smoothing scale is " + str(smoothing_scale_kHz) + "kHz")
        print("Number of points to smooth over is " + str(smoothing_scale))
    #smooth s21 trace in both real and imaginary to do peak finding
    sdata_smooth_real = savgol_filter(np.real(sdata), smoothing_scale, smoothing_order)
    sdata_smooth_imag = savgol_filter(np.imag(sdata), smoothing_scale, smoothing_order)
    sdata_smooth = np.array(sdata_smooth_real + 1j*sdata_smooth_imag)
    
    if verbose:
        print("Smoothed Data")
    
    #take derivative of data (optional) and smoothed data
    first_deriv_smooth = []
    first_deriv_freqs = []
    for j in range(0,len(sdata_smooth)-1):
        first_deriv_smooth.append((sdata_smooth[j+1] - sdata_smooth[j])/(freqs[j+1]-freqs[j]))
        first_deriv_freqs.append((freqs[j+1]+freqs[j])/2.0)
    first_deriv_smooth = np.array(first_deriv_smooth)
    first_deriv_freqs = np.array(first_deriv_freqs)
        
    if verbose:
        print("Derivative Taken")
    
    #rotate first deriv into r-hat vs. theta-hat coordinates using original position of s21
    first_deriv_rot_smooth = []
    for j in range(0,len(first_deriv_smooth)):
        sdata_pt_smooth = (sdata_smooth[j] + sdata_smooth[j+1])/2.0
        theta_smooth = np.arctan2(np.imag(sdata_pt_smooth),np.real(sdata_pt_smooth))
        first_deriv_rot_smooth.append([(np.real(first_deriv_smooth[j])*np.cos(theta_smooth) + np.imag(first_deriv_smooth[j])*np.sin(theta_smooth)),(-1.0*np.real(first_deriv_smooth[j])*np.sin(theta_smooth) + np.imag(first_deriv_smooth[j])*np.cos(theta_smooth))])
    first_deriv_rot_smooth = np.array(first_deriv_rot_smooth)
    
    if verbose:
        print("Derivative Rotated")

    #use smoothed rotated first derivatives to find resonances
    frs = []
    Qts = []
    #figure out spacing between freqs
    delta_f = first_deriv_freqs[1] - first_deriv_freqs[0]
    float_samples = minimum_spacing_kHz/(delta_f*1e6)
    n_samples = math.floor(float_samples)+1 #only need to look this far around a given point above cutoff
    if verbose:
        print("Data spacing is " + str(delta_f*1e6) + "kHz")
        print("Prescribed minimum resonator spacing is " + str(minimum_spacing_kHz) + "kHz")
        print("Need to look +/-" + str(n_samples) + " samples around each point above cutoff")
    for j in range(0,len(first_deriv_rot_smooth)):
        if first_deriv_rot_smooth[j,1]*(first_deriv_freqs[j]/2.0) > cutoff_rate:
            another_higher = False
            k = max(0,j - n_samples) #start looking at k = j - n_samples
            while not another_higher and k < len(first_deriv_rot_smooth) and k < j + n_samples + 1:
                if abs(first_deriv_freqs[j] - first_deriv_freqs[k]) < minimum_spacing_kHz*1e-6 and j!= k: #freq is within range
                    if first_deriv_rot_smooth[k,1]*(first_deriv_freqs[k]/2.0) > first_deriv_rot_smooth[j,1]*(first_deriv_freqs[j]/2.0): #found one with larger derivative
                        another_higher = True
                #increment k, check if next point is higher
                k = k + 1 
            if another_higher == False: #confirmed, this is the highest point within +/- minimum spacing
                frs.append(first_deriv_freqs[j])
                Qts.append(first_deriv_rot_smooth[j,1]*(first_deriv_freqs[j]/2.0))
                if verbose:
                    print("Added " + str(first_deriv_freqs[j]) + "GHz")
    frs = np.array(frs)
    
    if verbose:
        print("Found " + str(len(frs)) + " Resonators")

    if write_out_freqs:
        #write out resonant frequencies to files (one for each input file)
        fout = open(freqs_filename, "w")
        for j in range(0,len(frs)):
            fout.write(str(frs[j]) + "\n")
        fout.close()
        if verbose:
            print("Files Written Out")
            
    if make_plots:
        #plot data and smoothed data
        fig1 = plt.figure(1)
        ax11 = fig1.add_subplot(121)
        ax11.plot(freqs, 20.0*np.log10(np.absolute(sdata)), c = 'b', label = 'Raw')
        ax11.plot(freqs, 20.0*np.log10(np.absolute(sdata_smooth)), c = 'r', label = 'Smoothed')
        #mark resonances
        for i in range(0,len(frs)):
            ax11.plot([frs[i],frs[i]],[-15,0], c = 'k', linestyle = '--')
            ax11.text(frs[i]-0.0001, 1.0, str(i), fontsize = 10)
        ax11.set_ylim([-15,2.5])
        ax11.set_xlabel("Freq. (GHz)")
        ax11.set_ylabel(r"$\left| S_{21} \right|^2$ (dB)")
        ax11.legend(loc = 'upper right')

        ax12 = fig1.add_subplot(122)
        ax12.plot(freqs, 180.0/math.pi*np.arctan2(np.imag(sdata),np.real(sdata)), c = 'b', label = 'Raw')
        ax12.plot(freqs, 180.0/math.pi*np.arctan2(np.imag(sdata_smooth),np.real(sdata_smooth)), c = 'r', label = 'Smoothed')
        for i in range(0,len(frs)):
            ax12.plot([frs[i],frs[i]],[-180,180], c = 'k', linestyle = '--')
        ax12.set_xlabel("Freq. (GHz)")
        ax12.set_ylabel(r"$\angle S_{21}$ (Deg)")
        ax12.legend(loc = 'upper right')

        #plot 1st derivative in r-hat and theta-hat vs. freq
        fig3 = plt.figure(3)
        ax32 = fig3.add_subplot(111)
        ax32.plot(first_deriv_freqs, first_deriv_rot_smooth[:,1]*(first_deriv_freqs/2.0), c = 'r')
        ax32.set_xlabel("Freq. (GHz)")
        ax32.set_ylabel(r"$\frac{Q_t^2}{Q_c} = \frac{\omega_0}{2}\frac{\partial S_{21}}{\partial f} \cdot \hat{\theta}$")
        #mark found resonances
        for i in range(0,len(frs)):
            ax32.plot([frs[i],frs[i]],[Qts[i],-7500], c = 'k', linestyle = '--')
            ax32.text(frs[i]-0.001, -10000, str(i), fontsize = 10)
        ax32.set_ylim([-15000, 1.1*np.amax(first_deriv_rot_smooth[:,1]*(first_deriv_freqs/2.0))])
        ax32.scatter(frs, Qts, color = 'b', s = 20.0)
        ax32.plot([np.amin(freqs), np.amax(freqs)],[cutoff_rate,cutoff_rate], linestyle = '--', color = 'k')
        
        if remove_baseline_ripple:
            #plot baseline removal data
            fig4 = plt.figure(4)
            ax41 = fig4.add_subplot(121)
            ax41.plot(freqs, 20.0*np.log10(np.absolute(pre_baseline_removal_sdata)), c = 'b', label = 'Raw')
            ax41.plot(freqs, 20.0*np.log10(np.absolute(sdata)), c = 'r', label = 'Baseline Removed')
            ax41.plot(freqs, 20.0*np.log10(np.absolute(baseline)), c = 'g', label = 'Baseline')
            ax41.set_ylim([-15,2.5])
            ax41.set_xlabel("Freq. (GHz)")
            ax41.set_ylabel(r"$\left| S_{21} \right|^2$ (dB)")
            ax41.legend(loc = 'upper right')

            ax42 = fig4.add_subplot(122)
            ax42.plot(freqs, 180.0/math.pi*np.arctan2(np.imag(pre_baseline_removal_sdata),np.real(pre_baseline_removal_sdata)), c = 'b', label = 'Raw')
            ax42.plot(freqs, 180.0/math.pi*np.arctan2(np.imag(sdata),np.real(sdata)), c = 'r', label = 'Baseline Removed')
            ax42.plot(freqs, 180.0/math.pi*np.arctan2(np.imag(baseline),np.real(baseline)), c = 'g', label = 'Baseline')
            ax42.set_xlabel("Freq. (GHz)")
            ax42.set_ylabel(r"$\angle S_{21}$ (Deg)")
            ax42.legend(loc = 'upper right')
        
        plt.show()

    return frs