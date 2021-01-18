from matplotlib.backends.backend_pdf import PdfPages
from multitone_kidPy import read_multitone
from KIDs import resonance_fitting
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import binned_statistic
from scipy import interpolate
from KIDs import calibrate
import pickle
from KIDs import PCA


# this function fits a fine and gain scan combo produced by the ASU multitone system
# and uses the error produced by the system to determine if the fit is good
def fit_fine_gain_std(fine_name,gain_name,reduced_chi_squared_cutoff = 1000.,plot = True):

        
    fine = read_multitone.read_iq_sweep(fine_name,load_std = True)
    gain = read_multitone.read_iq_sweep(gain_name,load_std = True)
    outfile_dir = fine_name
    center_freqs = fine['freqs'][fine['freqs'].shape[0]//2,:]

    if plot:
        pdf_pages = PdfPages(outfile_dir+"/"+"fit_plots.pdf")

    all_fits_mag = np.zeros((9,fine['freqs'].shape[1]))
    all_fits_iq = np.zeros((10,fine['freqs'].shape[1]))

    for i in range(0,fine['freqs'].shape[1]):
        fine_f = fine['freqs'][:,i]*10**6
        gain_f = gain['freqs'][:,i]*10**6
        fine_z = fine['I'][:,i]+1.j*fine['Q'][:,i]
        fine_z_err = fine['I_std'][:,i]+1.j*fine['Q_std'][:,i]
        gain_z = gain['I'][:,i]+1.j*gain['Q'][:,i]
        gain_z_err = gain['I_std'][:,i]+1.j*gain['Q_std'][:,i]

        #flag data that is too close to other resonators              
        distance = center_freqs-center_freqs[i]
        if center_freqs[i] != np.min(center_freqs): #don't do if lowest frequency resonator
            closest_lower_dist = -np.min(np.abs(distance[np.where(distance<0)]))
            closest_lower_index = np.where(distance ==closest_lower_dist)[0][0]
            halfway_low = (center_freqs[i] + center_freqs[closest_lower_index])/2.
        else:
            halfway_low = 0

        if center_freqs[i] != np.max(center_freqs): #don't do if highest frequenct
            closest_higher_dist = np.min(np.abs(distance[np.where(distance>0)]))
            closest_higher_index = np.where(distance ==closest_higher_dist)[0][0]
            halfway_high = (center_freqs[i] + center_freqs[closest_higher_index])/2.
        else:
            halfway_high = np.inf
           
        use_index = np.where(((fine_f/10**6>halfway_low) & (fine_f/10**6<halfway_high)))
        fine_f = fine_f[use_index]
        fine_z = fine_z[use_index]
        fine_z_err = fine_z_err[use_index]

        #flag gain data that is to close to all of the resonators
        fine_span = (fine_f[-1]-fine_f[0])/10**6
        use_boolean = np.zeros(len(gain_f))
        for j in range(0,len(gain_f)):
            if (np.abs(gain_f[j]/10**6-center_freqs)< fine_span/2.).any():
                use_boolean[j] = 1

        use_index_gain = np.where(use_boolean != 1)
        if len(use_index_gain[0]>1):
            gain_f = gain_f[use_index_gain]
            gain_z = gain_z[use_index_gain]
            gain_z_err = gain_z_err[use_index_gain]

        if plot:
            fig = plt.figure(i,figsize = (16,10))

            ax1 = plt.subplot(231)
            plt.title("Resonator Index "+str(i))
            plt.plot(fine['freqs'][:,i],10*np.log10(fine['I'][:,i]**2+fine['Q'][:,i]**2),'o',label = "fine")
            plt.plot(gain['freqs'][:,i],10*np.log10(gain['I'][:,i]**2+gain['Q'][:,i]**2),'o',label = "gain")
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Power (dB)")

            ax2 = plt.subplot(232)
            plt.plot(fine['freqs'][:,i],10*np.log10(fine['I'][:,i]**2+fine['Q'][:,i]**2),'o')
            plt.plot(gain['freqs'][:,i],10*np.log10(gain['I'][:,i]**2+gain['Q'][:,i]**2),'o')
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Power (dB)")
            plt.xlim(np.min(fine['freqs'][:,i]),np.max(fine['freqs'][:,i]))

        # fit nonlinear magnitude
        try:
            x0 = resonance_fitting.guess_x0_mag_nonlinear_sep(fine_f,fine_z,gain_f,gain_z,verbose = True)
            fit_dict_mag = resonance_fitting.fit_nonlinear_mag_sep(fine_f,fine_z,gain_f,gain_z,fine_z_err = fine_z_err, gain_z_err = gain_z_err, x0=x0)#,bounds =bounds)
            all_fits_mag[0:8,i] = fit_dict_mag['fit'][0]
            all_fits_mag[8,i] = fit_dict_mag['red_chi_sqr']
            if plot:
                plt.subplot(231)
                plt.plot(fit_dict_mag['fit_freqs']/10**6,10*np.log10(fit_dict_mag['fit_result']),"+",label = "fit")
                plt.plot(fit_dict_mag['fit_freqs']/10**6,10*np.log10(fit_dict_mag['x0_result']),"x",label = "x0 guess")
                plt.title("f ="+str(fit_dict_mag['fit'][0][0]/10**6)[0:7]+"MHz, a="+"{:.2f}".format(fit_dict_mag['fit'][0][4]))
                plt.legend()
                if fit_dict_mag['red_chi_sqr']>reduced_chi_squared_cutoff:
                    ax1.set_facecolor('lightyellow')
                    ax2.set_facecolor('lightyellow')
                
            
                plt.subplot(232)
                plt.plot(fit_dict_mag['fit_freqs']/10**6,10*np.log10(fit_dict_mag['fit_result']),"+")
                plt.plot(fit_dict_mag['fit_freqs']/10**6,10*np.log10(fit_dict_mag['x0_result']),"x")

                plt.text(0.75, 0.9, "fr  = "+"{:.3f}".format(fit_dict_mag['fit'][0][0]/10**6)+" MHz", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.85, "Qr  = "+"{:.0f}".format(fit_dict_mag['fit'][0][1])+" ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.8, "amp = "+"{:.2f}".format(fit_dict_mag['fit'][0][2])+" ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.75, "phi = "+"{:.2f}".format(fit_dict_mag['fit'][0][3])+" radians", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.70, "a   = "+"{:.2f}".format(fit_dict_mag['fit'][0][4])+" ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.65, "b0  = "+"{:.0f}".format(fit_dict_mag['fit'][0][5])+" ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.6, "b1  = "+"{:.0f}".format(fit_dict_mag['fit'][0][6])+" ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.55, "reduced chi squared  = "+"{:.2f}".format(fit_dict_mag['red_chi_sqr'])+" ", fontsize=14, transform=plt.gcf().transFigure)
            
        except Exception as e:
            print(e)
            print("could not fit the resonator")

        if plot:
            ax3 = plt.subplot(234,aspect ='equal')
            plt.plot(fine['I'][:,i],fine['Q'][:,i],'o')
            plt.plot(gain['I'][:,i],gain['Q'][:,i],'o')
            plt.xlabel("I")
            plt.ylabel("Q")

            ax4 = plt.subplot(235,aspect ='equal')
            plt.plot(fine['I'][:,i],fine['Q'][:,i],'o')
            plt.plot(gain['I'][:,i],gain['Q'][:,i],'o')
            plt.xlabel("I")
            plt.ylabel("Q")
            plt.xlim(np.min(fine['I'][:,i]),np.max(fine['I'][:,i]))
            plt.ylim(np.min(fine['Q'][:,i]),np.max(fine['Q'][:,i]))


        # fit nonlinear iq 
        try:
            x0 = resonance_fitting.guess_x0_iq_nonlinear_sep(fine_f,fine_z,gain_f,gain_z,verbose = True)
            fit_dict_iq = resonance_fitting.fit_nonlinear_iq_sep(fine_f,fine_z,gain_f,gain_z,fine_z_err = fine_z_err, gain_z_err = gain_z_err,x0=x0)
            all_fits_iq[0:9,i] = fit_dict_iq['fit'][0]
            all_fits_iq[9,i] = fit_dict_iq['red_chi_sqr']
            if plot:
                plt.subplot(234,aspect ='equal')
                plt.plot(np.real(fit_dict_iq['fit_result']),np.imag(fit_dict_iq['fit_result']),"+")
                plt.plot(np.real(fit_dict_iq['x0_result']),np.imag(fit_dict_iq['x0_result']),"x")
                plt.title("f ="+str(fit_dict_iq['fit'][0][0]/10**6)[0:7]+"MHz, a="+"{:.2f}".format(fit_dict_iq['fit'][0][4]))
                plt.subplot(235,aspect ='equal')
                plt.plot(np.real(fit_dict_iq['fit_result']),np.imag(fit_dict_iq['fit_result']),"+")
                plt.plot(np.real(fit_dict_iq['x0_result']),np.imag(fit_dict_iq['x0_result']),"x")
                plt.plot(fine['I'][:,i],fine['Q'][:,i])

                if fit_dict_iq['red_chi_sqr']>reduced_chi_squared_cutoff:
                    ax3.set_facecolor('lightyellow')
                    ax4.set_facecolor('lightyellow')

                plt.text(0.75, 0.45, "fr  = "+"{:.3f}".format(fit_dict_iq['fit'][0][0]/10**6)+" MHz", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.4, "Qr  = "+"{:.0f}".format(fit_dict_iq['fit'][0][1])+" ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.35, "amp = "+"{:.2f}".format(fit_dict_iq['fit'][0][2])+" ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.3, "phi = "+"{:.2f}".format(fit_dict_iq['fit'][0][3])+" radians", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.25, "a   = "+"{:.2f}".format(fit_dict_iq['fit'][0][4])+" ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.2, "i0  = "+"{:.0f}".format(fit_dict_iq['fit'][0][5])+" ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.15, "q0  = "+"{:.0f}".format(fit_dict_iq['fit'][0][6])+" ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.1, "tau = "+"{:.2f}".format(fit_dict_iq['fit'][0][7]*10**7)+" x 10^-7 ", fontsize=14, transform=plt.gcf().transFigure)
                plt.text(0.75, 0.05, "reduced chi squared  = "+"{:.2f}".format(fit_dict_iq['red_chi_sqr'])+" ", fontsize=14, transform=plt.gcf().transFigure)
            
        except Exception as e:
            print(e)
            print("could not fit the resonator")

        if plot:
            plt.suptitle("Resonator index = " +str(i) +", Frequency = "+str(center_freqs[i])[0:7])



            pdf_pages.savefig(fig)
            plt.close(fig)
    if plot:
        pdf_pages.close()

    pdf_pages = PdfPages(outfile_dir+"/"+"fit_results.pdf")

    fig = plt.figure(1, figsize = (12,6))
    plt.title("Center frequency")
    res_index = np.arange(0,all_fits_mag.shape[1])
    
    plt.plot(res_index,all_fits_mag[0,:]/10**6,'o',label = "Mag fit")
    plt.plot(res_index,all_fits_iq[0,:]/10**6,'o',label = "IQ fit")
    
    bad_fit_mag = np.where(all_fits_mag[8,:]>reduced_chi_squared_cutoff)
    failed_fit_mag = np.where(all_fits_mag[0,:]==0)
    bad_fit_mag = np.append(bad_fit_mag,failed_fit_mag)
    bad_fit_iq = np.where(all_fits_iq[9,:]>reduced_chi_squared_cutoff)
    failed_fit_iq = np.where(all_fits_iq[0,:]==0)
    bad_fit_iq = np.append(bad_fit_mag,failed_fit_iq)


    plt.plot(res_index[bad_fit_mag],all_fits_mag[0,:][bad_fit_mag]/10**6,'o',label = "bad fit",color = 'k')
    plt.plot(res_index[bad_fit_iq],all_fits_iq[0,:][bad_fit_iq]/10**6,'o',color = 'k')
    
    plt.xlabel("resonator index")
    plt.ylabel("Resonator Frequency (MHz)")
    plt.legend(loc = 4)
    pdf_pages.savefig(fig)
    plt.close()

    fig = plt.figure(2,figsize = (12,6))
    plt.title("Resonator Qs")
    plt.plot(res_index,all_fits_mag[1,:],'o',label = "Qr Mag",color = 'g')
    plt.plot(res_index,all_fits_iq[1,:],'*',label = "Qr IQ",color = 'g')
    plt.plot(res_index[bad_fit_mag],all_fits_mag[1,:][bad_fit_mag],'o',color = 'k')
    plt.plot(res_index[bad_fit_iq],all_fits_iq[1,:][bad_fit_iq],'*',color = 'k')
    
    plt.plot(res_index,all_fits_mag[1,:]/all_fits_mag[2,:],'o',label = "Qc Mag",color = 'b')
    plt.plot(res_index,all_fits_iq[1,:]/all_fits_mag[2,:],'*',label = "Qc IQ",color = 'b')
    plt.plot(res_index[bad_fit_mag],all_fits_mag[1,:][bad_fit_mag]/all_fits_mag[2,:][bad_fit_mag],'o',color = 'k')
    plt.plot(res_index[bad_fit_iq],all_fits_iq[1,:][bad_fit_iq]/all_fits_mag[2,:][bad_fit_iq],'*',color = 'k')
    
    plt.plot(res_index,1/(1/all_fits_mag[1,:]-1/(all_fits_mag[1,:]/all_fits_mag[2,:])),'o',label = "Qi Mag",color = 'r')
    plt.plot(res_index,1/(1/all_fits_iq[1,:]-1/(all_fits_iq[1,:]/all_fits_iq[2,:])),'*',label = "Qi IQ",color = 'r')
    plt.plot(res_index[bad_fit_mag],1/(1/all_fits_mag[1,:][bad_fit_mag]-1/(all_fits_mag[1,:][bad_fit_mag]/all_fits_mag[2,:][bad_fit_mag])),'o',color = 'k')
    plt.plot(res_index[bad_fit_iq],1/(1/all_fits_iq[1,:][bad_fit_iq]-1/(all_fits_iq[1,:][bad_fit_iq]/all_fits_iq[2,:][bad_fit_iq])),'*',color = 'k')
    
    plt.xlabel("Resonator index")
    plt.ylabel("Resonator Q")
    plt.yscale('log')
    plt.legend()
    pdf_pages.savefig(fig)
    plt.close()

    fig = plt.figure(3,figsize = (12,6))
    plt.title("Non linearity parameter a")
    plt.plot(res_index,all_fits_mag[4,:],'o',label = "a Mag")
    plt.plot(res_index,all_fits_iq[4,:],'o',label = "a IQ")
    plt.plot(res_index[bad_fit_mag],all_fits_mag[4,:][bad_fit_mag],'o',color = 'k')
    plt.plot(res_index[bad_fit_iq],all_fits_iq[4,:][bad_fit_iq],'o',color = 'k')
    
    plt.xlabel("Resonator index")
    plt.ylabel("Non-linearity parameter a")
    plt.ylim(0,1)
    plt.legend()
    pdf_pages.savefig(fig)
    plt.close()

    pdf_pages.close()

    np.save(outfile_dir+"/"+"all_fits_mag",all_fits_mag)
    np.save(outfile_dir+"/"+"all_fits_iq",all_fits_iq)
    np.savetxt(outfile_dir+"/"+"all_fits_mag.csv",all_fits_mag,delimiter = ',')
    np.savetxt(outfile_dir+"/"+"all_fits_iq.csv",all_fits_iq,delimiter = ',')




# this function fits a fine and gain scan combo produced by the ASU multitone system
def fit_fine_gain(fine_name,gain_name):

        
    fine = read_multitone.read_iq_sweep(fine_name)
    gain = read_multitone.read_iq_sweep(gain_name)
    outfile_dir = fine_name
    center_freqs = fine['freqs'][fine['freqs'].shape[0]//2,:]


    pdf_pages = PdfPages(outfile_dir+"/"+"fit_plots.pdf")

    all_fits_mag = np.zeros((8,fine['freqs'].shape[1]))
    all_fits_iq = np.zeros((9,fine['freqs'].shape[1]))

    for i in range(0,fine['freqs'].shape[1]):
        fine_f = fine['freqs'][:,i]*10**6
        gain_f = gain['freqs'][:,i]*10**6
        fine_z = fine['I'][:,i]+1.j*fine['Q'][:,i]
        gain_z = gain['I'][:,i]+1.j*gain['Q'][:,i]

        #flag data that is too close to other resonators              
        distance = center_freqs-center_freqs[i]
        if center_freqs[i] != np.min(center_freqs): #don't do if lowest frequency resonator
            closest_lower_dist = -np.min(np.abs(distance[np.where(distance<0)]))
            closest_lower_index = np.where(distance ==closest_lower_dist)[0][0]
            halfway_low = (center_freqs[i] + center_freqs[closest_lower_index])/2.
        else:
            halfway_low = 0

        if center_freqs[i] != np.max(center_freqs): #don't do if highest frequenct
            closest_higher_dist = np.min(np.abs(distance[np.where(distance>0)]))
            closest_higher_index = np.where(distance ==closest_higher_dist)[0][0]
            halfway_high = (center_freqs[i] + center_freqs[closest_higher_index])/2.
        else:
            halfway_high = np.inf
           
        use_index = np.where(((fine_f/10**6>halfway_low) & (fine_f/10**6<halfway_high)))
        fine_f = fine_f[use_index]
        fine_z = fine_z[use_index]

        #flag gain data that is to close to all of the resonators
        fine_span = (fine_f[-1]-fine_f[0])/10**6
        use_boolean = np.zeros(len(gain_f))
        for j in range(0,len(gain_f)):
            if (np.abs(gain_f[j]/10**6-center_freqs)< fine_span/2.).any():
                use_boolean[j] = 1

        use_index_gain = np.where(use_boolean != 1)
        if len(use_index_gain[0]>1):
            gain_f = gain_f[use_index_gain]
            gain_z = gain_z[use_index_gain]


        fig = plt.figure(i,figsize = (16,10))

        plt.subplot(231)
        plt.title("Resonator Index "+str(i))
        plt.plot(fine['freqs'][:,i],10*np.log10(fine['I'][:,i]**2+fine['Q'][:,i]**2),'o',label = "fine")
        plt.plot(gain['freqs'][:,i],10*np.log10(gain['I'][:,i]**2+gain['Q'][:,i]**2),'o',label = "gain")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Power (dB)")

        plt.subplot(232)
        plt.plot(fine['freqs'][:,i],10*np.log10(fine['I'][:,i]**2+fine['Q'][:,i]**2),'o')
        plt.plot(gain['freqs'][:,i],10*np.log10(gain['I'][:,i]**2+gain['Q'][:,i]**2),'o')
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Power (dB)")
        plt.xlim(np.min(fine['freqs'][:,i]),np.max(fine['freqs'][:,i]))

        # fit nonlinear magnitude
        try:
            x0 = resonance_fitting.guess_x0_mag_nonlinear_sep(fine_f,fine_z,gain_f,gain_z,verbose = True)
            fit_dict_mag = resonance_fitting.fit_nonlinear_mag_sep(fine_f,fine_z,gain_f,gain_,fine_z_err = fine_z_err, gain_z_err = gain_z_errz,x0=x0)
            #,bounds =bounds)
            all_fits_mag[:,i] = fit_dict_mag['fit'][0]
            plt.subplot(231)
            plt.plot(fit_dict_mag['fit_freqs']/10**6,10*np.log10(fit_dict_mag['fit_result']),"+",label = "fit")
            plt.plot(fit_dict_mag['fit_freqs']/10**6,10*np.log10(fit_dict_mag['x0_result']),"x",label = "x0 guess")
            plt.title("f ="+str(fit_dict_mag['fit'][0][0]/10**6)[0:7]+"MHz, a="+"{:.2f}".format(fit_dict_mag['fit'][0][4]))
            plt.legend()
            plt.subplot(232)
            plt.plot(fit_dict_mag['fit_freqs']/10**6,10*np.log10(fit_dict_mag['fit_result']),"+")
            plt.plot(fit_dict_mag['fit_freqs']/10**6,10*np.log10(fit_dict_mag['x0_result']),"x")

            plt.text(0.75, 0.85, "fr  = "+"{:.3f}".format(fit_dict_mag['fit'][0][0]/10**6)+" MHz", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.80, "Qr  = "+"{:.0f}".format(fit_dict_mag['fit'][0][1])+" ", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.75, "amp = "+"{:.2f}".format(fit_dict_mag['fit'][0][2])+" ", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.70, "phi = "+"{:.2f}".format(fit_dict_mag['fit'][0][3])+" radians", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.65, "a   = "+"{:.2f}".format(fit_dict_mag['fit'][0][4])+" ", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.60, "b0  = "+"{:.0f}".format(fit_dict_mag['fit'][0][5])+" ", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.55, "b1  = "+"{:.0f}".format(fit_dict_mag['fit'][0][6])+" ", fontsize=14, transform=plt.gcf().transFigure)
            
        except Exception as e:
            print(e)
            print("could not fit the resonator")


        plt.subplot(234,aspect ='equal')
        plt.plot(fine['I'][:,i],fine['Q'][:,i],'o')
        plt.plot(gain['I'][:,i],gain['Q'][:,i],'o')
        plt.xlabel("I")
        plt.ylabel("Q")

        plt.subplot(235,aspect ='equal')
        plt.plot(fine['I'][:,i],fine['Q'][:,i],'o')
        plt.plot(gain['I'][:,i],gain['Q'][:,i],'o')
        plt.xlabel("I")
        plt.ylabel("Q")
        plt.xlim(np.min(fine['I'][:,i]),np.max(fine['I'][:,i]))
        plt.ylim(np.min(fine['Q'][:,i]),np.max(fine['Q'][:,i]))


        # fit nonlinear iq 
        try:
            x0 = resonance_fitting.guess_x0_iq_nonlinear_sep(fine_f,fine_z,gain_f,gain_z,verbose = True)
            fit_dict_iq = resonance_fitting.fit_nonlinear_iq_sep(fine_f,fine_z,gain_f,gain_z,fine_z_err = fine_z_err, gain_z_err = gain_z_err,x0=x0)
            all_fits_iq[:,i] = fit_dict_iq['fit'][0]
            plt.subplot(234,aspect ='equal')
            plt.plot(np.real(fit_dict_iq['fit_result']),np.imag(fit_dict_iq['fit_result']),"+")
            plt.plot(np.real(fit_dict_iq['x0_result']),np.imag(fit_dict_iq['x0_result']),"x")
            plt.title("f ="+str(fit_dict_iq['fit'][0][0]/10**6)[0:7]+"MHz, a="+"{:.2f}".format(fit_dict_iq['fit'][0][4]))
            plt.subplot(235,aspect ='equal')
            plt.plot(np.real(fit_dict_iq['fit_result']),np.imag(fit_dict_iq['fit_result']),"+")
            plt.plot(np.real(fit_dict_iq['x0_result']),np.imag(fit_dict_iq['x0_result']),"x")
            plt.plot(fine['I'][:,i],fine['Q'][:,i])

            plt.text(0.75, 0.45, "fr  = "+"{:.3f}".format(fit_dict_iq['fit'][0][0]/10**6)+" MHz", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.4, "Qr  = "+"{:.0f}".format(fit_dict_iq['fit'][0][1])+" ", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.35, "amp = "+"{:.2f}".format(fit_dict_iq['fit'][0][2])+" ", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.3, "phi = "+"{:.2f}".format(fit_dict_iq['fit'][0][3])+" radians", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.25, "a   = "+"{:.2f}".format(fit_dict_iq['fit'][0][4])+" ", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.2, "i0  = "+"{:.0f}".format(fit_dict_iq['fit'][0][5])+" ", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.15, "q0  = "+"{:.0f}".format(fit_dict_iq['fit'][0][6])+" ", fontsize=14, transform=plt.gcf().transFigure)
            plt.text(0.75, 0.1, "tau = "+"{:.2f}".format(fit_dict_iq['fit'][0][7]*10**7)+" x 10^-7 ", fontsize=14, transform=plt.gcf().transFigure)
            
        except Exception as e:
            print(e)
            print("could not fit the resonator")


        plt.suptitle("Resonator index = " +str(i) +", Frequency = "+str(center_freqs[i])[0:7])



        pdf_pages.savefig(fig)
        plt.close(fig)

    pdf_pages.close()

    pdf_pages = PdfPages(outfile_dir+"/"+"fit_results.pdf")

    fig = plt.figure(1, figsize = (12,6))
    plt.title("Center frequency")
    plt.plot(all_fits_mag[0,:]/10**6,'o',label = "Mag fit")
    plt.plot(all_fits_iq[0,:]/10**6,'o',label = "IQ fit")
    plt.xlabel("resonator index")
    plt.ylabel("Resonator Frequency (MHz)")
    plt.legend(loc = 4)
    pdf_pages.savefig(fig)
    plt.close()

    fig = plt.figure(2,figsize = (12,6))
    plt.title("Resonator Qs")
    plt.plot(all_fits_mag[1,:],'o',label = "Qr Mag",color = 'g')
    plt.plot(all_fits_iq[1,:],'*',label = "Qr IQ",color = 'g')
    plt.plot(all_fits_mag[1,:]/all_fits_mag[2,:],'o',label = "Qc Mag",color = 'b')
    plt.plot(all_fits_iq[1,:]/all_fits_mag[2,:],'*',label = "Qc IQ",color = 'b')
    plt.plot(1/(1/all_fits_mag[1,:]-1/(all_fits_mag[1,:]/all_fits_mag[2,:])),'o',label = "Qi Mag",color = 'r')
    plt.plot(1/(1/all_fits_iq[1,:]-1/(all_fits_iq[1,:]/all_fits_iq[2,:])),'*',label = "Qi IQ",color = 'r')
    plt.xlabel("Resonator index")
    plt.ylabel("Resonator Q")
    plt.yscale('log')
    plt.legend()
    pdf_pages.savefig(fig)
    plt.close()

    fig = plt.figure(3,figsize = (12,6))
    plt.title("Non linearity parameter a")
    plt.plot(all_fits_mag[4,:],'o',label = "a Mag")
    plt.plot(all_fits_iq[4,:],'o',label = "a IQ")
    plt.xlabel("Resonator index")
    plt.ylabel("Non-linearity parameter a")
    plt.ylim(0,1)
    plt.legend()
    pdf_pages.savefig(fig)
    plt.close()

    pdf_pages.close()

    np.save(outfile_dir+"/"+"all_fits_mag",all_fits_mag)
    np.save(outfile_dir+"/"+"all_fits_iq",all_fits_iq)
    np.savetxt(outfile_dir+"/"+"all_fits_mag.csv",all_fits_mag,delimiter = ',')
    np.savetxt(outfile_dir+"/"+"all_fits_iq.csv",all_fits_iq,delimiter = ',')


def calibrate_multi(fine_filename,gain_filename,stream_filename,skip_beginning = 0,plot_period = 10,bin_num = 1,outfile_dir = "./",sample_rate = 488.28125, **keywords):

    fine_dict = read_multitone.read_iq_sweep(fine_filename)
    gain_dict = read_multitone.read_iq_sweep(gain_filename)
    stream_dict = read_multitone.read_stream(stream_filename)

    gain_z = gain_dict['I'] +1.j*gain_dict['Q']
    fine_z = fine_dict['I'] +1.j*fine_dict['Q']
    stream_z = stream_dict['I_stream'][skip_beginning:] +1.j*stream_dict['Q_stream'][skip_beginning:]
    stream_time = np.asarray(stream_dict['packet_count'])[skip_beginning:]*1/sample_rate
    stream_time = stream_time - stream_time[0]


    #bin the data if you like
    if bin_num !=1:
        for i in range(0,stream_z.shape[1]):
            if i == 0:
                stream_z_downsamp = np.zeros((stream_z.shape[0]/bin_num,stream_z.shape[1]),dtype = 'complex')
            stream_z_downsamp[:,i] = np.mean(stream_z[0:stream_z.shape[0]/bin_num*bin_num,i].reshape(-1,bin_num),axis = 1) #int math
        stream_time_downsamp = np.mean(stream_time[0:stream_time.shape[0]/bin_num*bin_num].reshape(-1,bin_num),axis = 1) #int math 
        stream_z = stream_z_downsamp
        stream_time = stream_time_downsamp
        

    #initalize some arrays to hold the calibrated data
    stream_corr_all = np.zeros(stream_z.shape,dtype = 'complex')
    gain_corr_all = np.zeros(gain_z.shape,dtype = 'complex')
    fine_corr_all = np.zeros(fine_z.shape,dtype = 'complex')
    stream_df_over_f_all = np.zeros(stream_z.shape)

    pdf_pages = PdfPages(outfile_dir+"cal_plots.pdf")

    for k in range(0,min(fine_dict['I'].shape[1], stream_z.shape[1])):
        print(k)


        fig = plt.figure(k,figsize = (16,10))

        plt.subplot(241,aspect = 'equal')
        plt.title("Raw data")
        plt.plot(fine_dict['I'][:,k],fine_dict['Q'][:,k],'o')
        plt.plot(np.real(stream_z[:,k][::plot_period]),np.imag(stream_z[:,k][::plot_period]),'.')
        plt.plot(gain_dict['I'][:,k],gain_dict['Q'][:,k],'o')

        plt.subplot(242)
        plt.title("Raw data")
        plt.plot(fine_dict['I'][:,k],fine_dict['Q'][:,k],'o')
        plt.plot(np.real(stream_z[:,k][::plot_period]),np.imag(stream_z[:,k][::plot_period]),'.')

        
        f_stream = fine_dict['freqs'][len(fine_dict['freqs'][:,k])/2,k]*10**6
        #normalize amplitude varation in gain scan
        amp_norm_dict = resonance_fitting.amplitude_normalization_sep(gain_dict['freqs'][:,k]*10**6,
                                                                          gain_z[:,k],
                                                                          fine_dict['freqs'][:,k]*10**6,
                                                                          fine_z[:,k],
                                                                          f_stream,
                                                                          stream_z[:,k])

        plt.subplot(243)
        plt.title("Gain amplitude variation fit")
        plt.plot(gain_dict['freqs'][:,k]*10**6,10*np.log10(np.abs(gain_z[:,k])**2),'o')
        plt.plot(gain_dict['freqs'][:,k]*10**6,10*np.log10(np.abs(amp_norm_dict['normalized_gain'])**2),'o')
        plt.plot(fine_dict['freqs'][:,k]*10**6,10*np.log10(np.abs(amp_norm_dict['normalized_fine'])**2),'o')
        plt.plot(gain_dict['freqs'][:,k]*10**6,10*np.log10(np.abs(amp_norm_dict['poly_data'])**2))

        plt.subplot(244)
        plt.title("Data nomalized for gain amplitude variation")
        plt.plot(np.real(amp_norm_dict['normalized_fine']),np.imag(amp_norm_dict['normalized_fine']),'o')
        #plt.plot(gain_dict['freqs'][:,k]*10**6,np.log10(np.abs(amp_norm_dict['poly_data'])**2))
        plt.plot(np.real(amp_norm_dict['normalized_stream'][::plot_period]),np.imag(amp_norm_dict['normalized_stream'][::plot_period]),'.')

        #fit the gain
        gain_phase = np.arctan2(np.real(amp_norm_dict['normalized_gain']),np.imag(amp_norm_dict['normalized_gain']))
        tau,fit_data_phase,gain_phase_rot = calibrate.fit_cable_delay(gain_dict['freqs'][:,k]*10**6,gain_phase)
        
        #gain_phase = np.arctan2(np.real(gain_z[:,k]),np.imag(gain_z[:,k]))
        #tau,fit_data_phase,gain_phase_rot = calibrate.fit_cable_delay(gain_dict['freqs'][:,k]*10**6,gain_phase)
        
        plt.subplot(245)
        plt.title("Gain phase fit")
        plt.plot(gain_dict['freqs'][:,k],gain_phase_rot,'o')
        plt.plot(gain_dict['freqs'][:,k],fit_data_phase)
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Phase")

        #remove cable delay
        gain_corr = calibrate.remove_cable_delay(gain_dict['freqs'][:,k]*10**6,amp_norm_dict['normalized_gain'],tau)
        fine_corr = calibrate.remove_cable_delay(fine_dict['freqs'][:,k]*10**6,amp_norm_dict['normalized_fine'],tau)
        stream_corr = calibrate.remove_cable_delay(f_stream,amp_norm_dict['normalized_stream'],tau)
        #gain_corr = calibrate.remove_cable_delay(gain_dict['freqs'][:,k]*10**6,gain_z[:,k],tau)
        #fine_corr = calibrate.remove_cable_delay(fine_dict['freqs'][:,k]*10**6,fine_z[:,k],tau)
        #stream_corr = calibrate.remove_cable_delay(f_stream,stream_z[:,k],tau)
        
        plt.subplot(246)
        plt.title("Cable delay removed")
        plt.plot(np.real(gain_corr),np.imag(gain_corr),'o')
        plt.plot(np.real(fine_corr),np.imag(fine_corr),'o')
        plt.plot(np.real(stream_corr)[10:-10][::plot_period],np.imag(stream_corr)[10:-10][::plot_period],'.')

        # fit a cicle to the data
        xc, yc, R, residu  = calibrate.leastsq_circle(np.real(fine_corr),np.imag(fine_corr))

        #move the data to the origin

        gain_corr = gain_corr - xc -1j*yc
        fine_corr = fine_corr - xc -1j*yc
        stream_corr = stream_corr  - xc -1j*yc

        # rotate so streaming data is at 0 pi
        phase_stream = np.arctan2(np.imag(stream_corr),np.real(stream_corr))
        if ("rotate_fine_first" in keywords): # if you have data that covers a large part of the iq loop
            med_phase = np.arctan2(np.imag(fine_corr),np.real(fine_corr))[0]+np.pi
        else:
            med_phase = np.median(phase_stream)

        gain_corr_all[:,k]  = gain_corr = gain_corr*np.exp(-1j*med_phase) 
        fine_corr_all[:,k] = fine_corr = fine_corr*np.exp(-1j*med_phase) 
        stream_corr_all[:,k] = stream_corr = stream_corr*np.exp(-1j*med_phase)


        plt.subplot(247)
        plt.title("Moved to 0,0 and rotated")
        plt.plot(np.real(stream_corr)[2:-1][::plot_period],np.imag(stream_corr)[2:-1][::plot_period],'.')
        plt.plot(np.real(gain_corr),np.imag(gain_corr),'o')
        plt.plot(np.real(fine_corr),np.imag(fine_corr),'o')
        calibrate.plot_data_circle(np.real(fine_corr)-xc,np.imag(fine_corr)-yc, 0, 0, R)

        phase_fine = np.arctan2(np.imag(fine_corr),np.real(fine_corr))
        use_index = np.where((-np.pi/2.<phase_fine) & (phase_fine<np.pi/2))
        phase_stream = np.arctan2(np.imag(stream_corr),np.real(stream_corr))

        #interp phase to frequency
        f_interp = interpolate.interp1d(phase_fine, fine_dict['freqs'][:,k],kind = 'quadratic',bounds_error = False,fill_value = 0)

        phase_small = np.linspace(np.min(phase_fine),np.max(phase_fine),1000)
        freqs_stream = f_interp(phase_stream)
        stream_df_over_f_all[:,k] = stream_df_over_f = freqs_stream/np.mean(freqs_stream)-1.

        plt.subplot(248)
        plt.plot(phase_fine,fine_dict['freqs'][:,k],'o')
        plt.plot(phase_small,f_interp(phase_small),'--')
        plt.plot(phase_stream[::plot_period],freqs_stream[::plot_period],'.')
        plt.ylim(np.min(freqs_stream)-(np.max(freqs_stream)-np.min(freqs_stream))*3,np.max(freqs_stream)+(np.max(freqs_stream)-np.min(freqs_stream))*3)
        plt.xlim(np.min(phase_stream)-np.pi/4,np.max(phase_stream)+np.pi/4)
        plt.xlabel("phase")
        plt.ylabel("Frequency")



        pdf_pages.savefig(fig)
        plt.close(fig)

    pdf_pages.close()


    #save everything to a dictionary
    cal_dict = {'fine_z': fine_z,
                    'gain_z': gain_z,
                    'stream_z': stream_z,
                    'fine_freqs':fine_dict['freqs'],
                    'gain_freqs':fine_dict['freqs'],
                    'stream_corr':stream_corr_all,
                    'gain_corr':gain_corr_all,
                    'fine_corr':fine_corr_all,
                    'stream_df_over_f':stream_df_over_f_all,
                    'time':stream_dict['time'],
                    'stream_time':stream_time}

    #save the dictionary
    pickle.dump( cal_dict, open(outfile_dir+ "cal.p", "wb" ),2 )
    return cal_dict


def calibrate_list(fine_filename,gain_filename,stream_list,skip_beginning = 0,plot_period = 10,bin_num = 1,outfile_dir = "./",sample_rate = 488.28125):
    #this is for batch fitting stream data in multiple dir files, mostly
    #for the beam map separate
    fine_dict = read_multitone.read_iq_sweep(fine_filename)
    gain_dict = read_multitone.read_iq_sweep(gain_filename)
    stream_dicts = [read_multitone.read_stream(stream_filename)
            for stream_filename in stream_list]

    gain_z = gain_dict['I'] +1.j*gain_dict['Q']
    fine_z = fine_dict['I'] +1.j*fine_dict['Q']
    stream_z = [stream_dict['I_stream'][skip_beginning:] +1.j*stream_dict['Q_stream'][skip_beginning:] for stream_dict in stream_dicts]
    stream_time = [np.asarray(stream_dict['packet_count'])[skip_beginning:]*1/sample_rate
            for stream_dict in stream_dicts]
    stream_time = [time - time[0] for time in stream_time]


    #bin the data if you like
    if bin_num !=1:
        for i in range(0,stream_z.shape[1]):
            if i == 0:
                stream_z_downsamp = np.zeros((stream_z.shape[0]/bin_num,stream_z.shape[1]),dtype = 'complex')
            stream_z_downsamp[:,i] = np.mean(stream_z[0:stream_z.shape[0]/bin_num*bin_num,i].reshape(-1,bin_num),axis = 1) #int math
        stream_time_downsamp = np.mean(stream_time[0:stream_time.shape[0]/bin_num*bin_num].reshape(-1,bin_num),axis = 1) #int math 
        stream_z = stream_z_downsamp
        stream_time = stream_time_downsamp
        

    #initalize some arrays to hold the calibrated data
    stream_corr_all = [np.zeros(set_z.shape,dtype = 'complex')
            for set_z in stream_z]
    gain_corr_all = np.zeros(gain_z.shape,dtype = 'complex')
    fine_corr_all = np.zeros(fine_z.shape,dtype = 'complex')
    stream_df_over_f_all = [np.zeros(set_z.shape) for set_z in stream_z]
    fit_vals = np.zeros((3,fine_z.shape[1]))


    for k in range(0,min(fine_dict['I'].shape[1], stream_z[0].shape[1])):
        print(k)
       
        f_stream = fine_dict['freqs'][len(fine_dict['freqs'][:,k])/2,k]*10**6
        #normalize amplitude varation in gain scan
        amp_norm_dict = [resonance_fitting.amplitude_normalization_sep(
                gain_dict['freqs'][:,k]*10**6, gain_z[:,k],
                fine_dict['freqs'][:,k]*10**6, fine_z[:,k], f_stream,
                set_z[:,k]) for set_z in stream_z]


        #fit the gain
        gain_phase = np.arctan2(np.real(amp_norm_dict[0]['normalized_gain']),np.imag(amp_norm_dict[0]['normalized_gain']))
        tau,fit_data_phase,gain_phase_rot = calibrate.fit_cable_delay(gain_dict['freqs'][:,k]*10**6,gain_phase)
        
        #remove cable delay
        gain_corr = calibrate.remove_cable_delay(gain_dict['freqs'][:,k]*10**6,amp_norm_dict[0]['normalized_gain'],tau)
        fine_corr = calibrate.remove_cable_delay(fine_dict['freqs'][:,k]*10**6,amp_norm_dict[0]['normalized_fine'],tau)
        stream_corr = [calibrate.remove_cable_delay(f_stream,set_norm_dict['normalized_stream'],tau) for set_norm_dict in amp_norm_dict]
        
        # fit a cicle to the data
        xc, yc, R, residu  = calibrate.leastsq_circle(np.real(fine_corr),np.imag(fine_corr))
        fit_vals[0,k] = xc
        fit_vals[1,k] = yc
        fit_vals[2,k] = R

        #move the data to the origin

        gain_corr = gain_corr - xc -1j*yc
        fine_corr = fine_corr - xc -1j*yc
        stream_corr = [set_corr  - xc -1j*yc for set_corr in stream_corr]

        # rotate so streaming data is at 0 pi
        phase_stream = [np.arctan2(np.imag(set_corr),np.real(set_corr))
                for set_corr in stream_corr]
        med_phase = np.median(phase_stream)

        gain_corr_all[:,k]  = gain_corr = gain_corr*np.exp(-1j*med_phase) 
        fine_corr_all[:,k] = fine_corr = fine_corr*np.exp(-1j*med_phase) 
        for i in range(len(stream_corr)):
            stream_corr_all[i][:,k] = stream_corr[i] = stream_corr[i]*np.exp(
                    -1j*med_phase)

        phase_fine = np.arctan2(np.imag(fine_corr),np.real(fine_corr))
        use_index = np.where((-np.pi/2.<phase_fine) & (phase_fine<np.pi/2))
        phase_stream = [np.arctan2(np.imag(set_corr),np.real(set_corr))
                for set_corr in stream_corr]

        #interp phase to frequency
        f_interp = interpolate.interp1d(phase_fine, fine_dict['freqs'][:,k],kind = 'quadratic',bounds_error = False,fill_value = 0)

        phase_small = np.linspace(np.min(phase_fine),np.max(phase_fine),1000)
        for i in range(len(phase_stream)):
            freqs_stream = f_interp(phase_stream[i])
            stream_df_over_f_all[i][:,k] = freqs_stream/np.mean(freqs_stream)-1.


    #save everything to a dictionary
    cal_dict = {
    #                'fine_z': fine_z,
    #                'gain_z': gain_z,
    #                'stream_z': stream_z,
    #                'fine_freqs':fine_dict['freqs'],
    #                'gain_freqs':fine_dict['freqs'],
    #                'stream_corr':stream_corr_all,
                    'gain_corr':gain_corr_all,
                    'fine_corr':fine_corr_all,
    #                'stream_df_over_f':stream_df_over_f_all,
    #                'time':stream_dict['time'],
    #                'stream_time':stream_time}
                     'fit_coords':fit_vals}

    #save the dictionary
    #pickle.dump( cal_dict, open(outfile_dir+ "cal.p", "wb" ),2 )
    return stream_df_over_f_all, stream_time, cal_dict


def noise_multi(cal_dict, sample_rate = 488.28125,outfile_dir = "./",n_comp_PCA = 0):
    pdf_pages = PdfPages(outfile_dir+"psd_plots.pdf")

    if n_comp_PCA >0:
        do_PCA = True
        #do PCA on the data
        PCA_dict = PCA.PCA(cal_dict['stream_df_over_f'],n_comp_PCA,sample_rate = sample_rate)
    else:
        do_PCA = False

    for k in range(0,min(cal_dict['fine_corr'].shape[1],
             cal_dict['stream_df_over_f'].shape[1])):
        print(k)


        #lets fourier transfer that crap
        fft_freqs,Sxx,S_per,S_par = calibrate.fft_noise(cal_dict['stream_corr'][:,k],cal_dict['stream_df_over_f'][:,k],sample_rate)
        if do_PCA:
            fft_freqs_2,Sxx_clean,S_per_2,S_par_2 = calibrate.fft_noise(cal_dict['stream_corr'][:,k],PCA_dict['cleaned'][:,k],sample_rate)
        if k == 0:
            #intialize some arrays
            Sxx_all = np.zeros((Sxx.shape[0],cal_dict['fine_corr'].shape[1]))
            Sxx_all_clean = np.zeros((Sxx.shape[0],cal_dict['fine_corr'].shape[1]))
            S_per_all = np.zeros((S_per.shape[0],cal_dict['fine_corr'].shape[1]))
            S_par_all = np.zeros((S_par.shape[0],cal_dict['fine_corr'].shape[1]))

        Sxx_all[:,k] = np.abs(Sxx)
        if do_PCA:
            Sxx_all_clean = np.abs(Sxx_clean)
        S_per_all[:,k] = np.abs(S_per)
        S_par_all[:,k] = np.abs(S_par)

        # bin it for ploting
        plot_bins = np.logspace(-3,np.log10(250),100)
        binnedfreq =  binned_statistic(fft_freqs, fft_freqs, bins=plot_bins)[0] #bin the frequecy against itself
        binnedpsd = binned_statistic(fft_freqs, np.abs(Sxx), bins=plot_bins)[0]
        if do_PCA:
            binnedpsd_clean = binned_statistic(fft_freqs, np.abs(Sxx_clean), bins=plot_bins)[0]
        binnedper = binned_statistic(fft_freqs, np.abs(S_per), bins=plot_bins)[0]
        binnedpar = binned_statistic(fft_freqs, np.abs(S_par), bins=plot_bins)[0]
        amp_subtracted = np.abs(binnedpsd)*(binnedpar-binnedper)/binnedpar
        if k == 0:
            Sxx_binned_all = np.zeros((binnedfreq.shape[0],cal_dict['fine_corr'].shape[1]))
            Sxx_binned_all_clean = np.zeros((binnedfreq.shape[0],cal_dict['fine_corr'].shape[1]))
            S_per_binned_all = np.zeros((binnedfreq.shape[0],cal_dict['fine_corr'].shape[1]))
            S_par_binned_all = np.zeros((binnedfreq.shape[0],cal_dict['fine_corr'].shape[1]))
            amp_subtracted_all = np.zeros((binnedfreq.shape[0],cal_dict['fine_corr'].shape[1]))

        Sxx_binned_all[:,k] = binnedpsd
        if do_PCA:
             Sxx_binned_all_clean[:,k] = binnedpsd_clean
        S_per_binned_all[:,k] = binnedper
        S_par_binned_all[:,k] = binnedpar
        amp_subtracted_all[:,k] = amp_subtracted


        fig = plt.figure(k,figsize = (16,6))
        plt.subplot(122)
        plt.title("Sxx")
        #plt.loglog(fft_freqs,np.abs(Sxx))
        plt.loglog(binnedfreq,np.abs(binnedpsd),linewidth = 2,label = "Sxx raw")
        if do_PCA:
            plt.loglog(binnedfreq,np.abs(binnedpsd_clean),linewidth = 2,label = "PCA " +str(n_comp_PCA)+" comps")
        plt.loglog(binnedfreq,amp_subtracted,linewidth = 2,label = "raw amp subtracted")
        #plt.ylim(10**-18,10**-15)
        plt.ylabel("Sxx (1/Hz)")
        plt.xlabel("Frequency (Hz)")
        plt.legend()

        plt.subplot(121)
        plt.title("Res indx = "+str(k))
        #plt.loglog(fft_freqs,S_per)
        #plt.loglog(fft_freqs,S_par)

        plt.loglog(binnedfreq,binnedper,label = "amp noise")
        plt.loglog(binnedfreq,binnedpar,label = "detect noise")
        plt.legend()
        #plt.ylim(10**2,10**6)
        plt.xlabel("Frequency (Hz)")

        pdf_pages.savefig(fig)
        plt.close(fig)

    pdf_pages.close()

    #make a psd dictionary
    psd_dict = {'fft_freqs':fft_freqs,
                    'Sxx':Sxx_all,
                    'S_per':S_per_all,
                    'S_par':S_par_all,
                    'binned_freqs':binnedfreq,
                    'Sxx_binned':Sxx_binned_all,
                    'S_per_binned':S_per_binned_all,
                    'S_par_binned':S_par_binned_all,
                    'amp_subtracted':amp_subtracted_all,
                    'Sxx_clean':Sxx_all_clean,
                    'Sxx_binned_clean':Sxx_binned_all_clean}

    #save the psd dictionary
    pickle.dump( psd_dict, open( outfile_dir+"psd.p", "wb" ),2 )

    return psd_dict
