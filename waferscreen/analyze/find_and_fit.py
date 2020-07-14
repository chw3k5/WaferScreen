import os
import numpy as np
import matplotlib.pyplot as plt
import waferscreen.analyze.find_resonances as find_res
import waferscreen.analyze.resonator_fitter as fit_res
from ref import s21_dir, output_dir
from waferscreen.read.table_read import num_format


class ResFit:
    def __init__(self, file, group_delay=None, verbose=True, freq_units="MHz", auto_process=True):
        self.filename = file
        file_basename = os.path.basename(file)
        base_handle, _extension = file_basename.rsplit(".", 1)
        self.verbose = verbose
        self.freq_units = freq_units
        self.group_delay = group_delay  # nanoseconds
    
        """resonance finding parameters """
        self.edge_search_depth = 50                  # how many frequency points inward from edges to average in removing gain, phase and gain slope offsets
        self.smoothing_scale_kHz = 75                # smoothing scale in savitsky-golay procedure
        self.smoothing_order = 5                     # smoothing order in savitsky-golay procedure
        self.cutoff_rate = 5000                      # cutoff in Qt^2/Qc to find resonances
        self.minimum_spacing_kHz = 100.0             # minimum spacing between resonances
        self.remove_baseline_ripple_find_res = True  # uses a wider savitsky-golay procedure to remove baseline ripple during resonance finding
        self.baseline_scale_kHz_find_res = 3000      # smoothing scale for baseline ripple removal, should be ~30x smoothing_scale_kHz
        self.baseline_order_find_res = 3             # smoothing order for baseline ripple removal
        self.make_plots_find_res = True              # make plots during resonance finding

        """resonator fitting options"""
        self.fitting_range_kHz = 500.0  # kHz, range around each resonance to use to fit
        self.throw_out = 0  # doesnt use N points on the edge of each sweep
        self.fit_model = 'simple_res_gain_slope_complex'  # name of model to fit to resonance
        self.error_est = 'prop'  # 'prop' or 'flat', proportional or constant errors
        self.fit_guess_plots = False  # make plots of each fit guess
        output_folder = os.path.join(output_dir, "s21")
        if not os.path.isdir(output_folder):
            os.mkdir(output_folder)

        self.fit_filename = os.path.join(output_folder, base_handle + "_fit.txt")

        self.freqs = None
        self.s21 = None
        self.res_freqs = None
        self.res_fit_params = None
        self.res_fit_errors = None

        if auto_process:
            self.open()
            self.find_resonances()
            self.extract_params()

    def open(self):
        """open files and consume freqs, real and imag"""
        with open(self.filename, 'r') as f:
            raw_data = f.readlines()
        split_data = [striped_line.split(",") for striped_line in [raw_line.strip() for raw_line in raw_data]
                      if striped_line != ""]
        data = [[num_format(single_number) for single_number in data_row] for data_row in split_data]
        data_array = np.array(data)
        freqs = data_array[:, 0]
        self.s21 = data_array[:, 1] + 1j * data_array[:, 2]
    
        # put freqs in GHz
        if self.freq_units == "MHz":
            self.freqs = freqs / 1.e3
        elif self.freq_units == "kHz":
            self.freqs = freqs / 1.e6
        elif self.freq_units == "Hz":
            self.freqs = freqs / 1.e9
        
        # remove group delay
        if self.group_delay is not None:
            phase_factors = np.exp(-1j * 2.0 * np.pi * self.freqs * self.group_delay)
            self.s21 = self.s21 / phase_factors

    def find_resonances(self, show_plot=True):
        # pass this s21 sweep to find_resonances_fast
        self.res_freqs = find_res.find_resonances(self.freqs, self.s21, edge_search_depth=self.edge_search_depth,
                                                  smoothing_scale_kHz=self.smoothing_scale_kHz,
                                                  smoothing_order=self.smoothing_order, cutoff_rate=self.cutoff_rate,
                                                  minimum_spacing_kHz=self.minimum_spacing_kHz,
                                                  remove_baseline_ripple=self.remove_baseline_ripple_find_res,
                                                  baseline_scale_kHz=self.baseline_scale_kHz_find_res,
                                                  baseline_order=self.baseline_order_find_res,
                                                  verbose=self.verbose,
                                                  make_plots=self.make_plots_find_res)

        if show_plot:
            self.plot_resonances()

    def plot_resonances(self):
        if self.res_freqs is None:
            self.find_resonances(show_plot=False)
        # plot s21 vs. freq and show plot
        fig1 = plt.figure(1)
        ax11 = fig1.add_subplot(121)
        ax12 = fig1.add_subplot(122)

        ax11.plot(self.freqs, 20.0*np.log10(np.absolute(self.s21)))
        ax12.plot(self.freqs, 180.0/np.pi * np.arctan2(np.imag(self.s21), np.real(self.s21)))

        ax11.plot(self.freqs, 20.0 * np.log10(np.absolute(self.s21)))
        ax12.plot(self.freqs, 180.0/np.pi * np.arctan2(np.imag(self.s21), np.real(self.s21)))

        # label found resonators
        for i in range(0, len(self.res_freqs)):
            ax11.plot([self.res_freqs[i], self.res_freqs[i]], [0, -15], linestyle='--', color='k')
            ax12.plot([self.res_freqs[i], self.res_freqs[i]], [-180, 180], linestyle='--', color='k')
            ax11.text(self.res_freqs[i], 1.0, str(i), fontsize=12)
        plt.show()

    def extract_params(self, show_plot=True):
        # loop over found resonators and fit to a model to extract Qt, Qc, Qi, f0, Fano etc
        self.res_fit_params = []
        self.res_fit_errors = []
        delta_f = (self.freqs[1] - self.freqs[0]) * 1e6
        float_samples = self.fitting_range_kHz / delta_f
        n_samples = np.floor(float_samples) + 1  # only need to take data this far around a given resonance
        print("Data frequency spacing is " + str(delta_f) + "kHz")
        print("Fitting range is +/- " + str(self.fitting_range_kHz) + "kHz")
        print("Need to fit +/-" + str(n_samples) + " samples around each resonance center")
        prev_res_index = 0
        # make file to write results out to
        f = open(self.fit_filename, "w")
        f.close()
        for i in range(0, len(self.res_freqs)):
            print("Fitting found resonance #" + str(i+1) + "/" + str(len(self.res_freqs)))
            # only pass section of data that's within range of the resonance
            res_index = prev_res_index
            res_found = False
            while not res_found and res_index < len(self.freqs):
                if self.freqs[res_index] > self.res_freqs[i]:
                    res_found = True
                    prev_res_index = res_index
                else:
                    res_index = res_index + 1
            # now res_index is the index of the freq that's half a bin above the marked fr
            fit_freqs = self.freqs[int(max(res_index - n_samples - 1, 0)):
                                   int(min(res_index + n_samples + 1, len(self.freqs) - 1))]
            fit_s21data = self.s21[int(max(res_index - n_samples - 1, 0)):
                                   int(min(res_index + n_samples + 1, len(self.s21) - 1))]
            # now fit the resonance
            popt, pcov = fit_res.fit_resonator(fit_freqs, fit_s21data, data_format='COM', model=self.fit_model,
                                               error_est=self.error_est, throw_out=self.throw_out,
                                               make_plot=self.fit_guess_plots)

            fit_Amag  = popt[0]
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
            print('Amag          : %.4f +/- %.6f' %(fit_Amag,error_Amag))
            print('Aphase        : %.2f +/- %.4f Deg' % (fit_Aphase,error_Aphase))
            print('Aslope        : %.3f +/- %.3f /GHz' %(fit_Aslope,error_Aslope))
            print('Tau           : %.3f +/- %.3f ns' %(fit_tau,error_tau))
            print('f0            : %.6f +/- %.8f GHz' % (fit_f0,error_f0))
            print('Qi            : %.0f +/- %.0f' %(fit_Qi,error_Qi))
            print('Qc            : %.0f +/- %.0f' %(fit_Qc,error_Qc))
            print('Im(Z0)/Re(Z0) : %.2f +/- %.3f' %(fit_Zratio,error_Zratio))
            print('')

            with open(self.fit_filename, "a") as f:
                f.write(str(popt[0]) + "," + str(np.sqrt(pcov[0, 0])) + "," + str(popt[1]) + "," +
                        str(np.sqrt(pcov[1, 1])) + "," + str(popt[2]) + "," + str(np.sqrt(pcov[2, 2])) + "," +
                        str(popt[3]) + "," + str(np.sqrt(pcov[3,3])) + "," + str(popt[4]) + "," +
                        str(np.sqrt(pcov[4, 4])) + "," + str(popt[5]) + "," + str(np.sqrt(pcov[5, 5])) + "," +
                        str(popt[6]) + "," + str(np.sqrt(pcov[6,6])) + "," + str(popt[7]) + "," +
                        str(np.sqrt(pcov[7, 7])) + "\n")
            self.res_fit_params.append([fit_Amag, fit_Aphase, fit_Aslope, fit_tau, fit_f0, fit_Qi, fit_Qc, fit_Zratio])
            self.res_fit_errors.append([error_Amag, error_Aphase, error_Aslope, error_tau, error_f0, error_Qi, error_Qc,
                                        error_Zratio])
        self.res_fit_params = np.array(self.res_fit_params)
        self.res_fit_errors = np.array(self.res_fit_errors)

        if show_plot:
            self.plot_results()

    def plot_results(self):
        # plot fit results vs. frequency
        fig2 = plt.figure(2)
        ax21 = fig2.add_subplot(221)
        ax22 = fig2.add_subplot(222)
        ax23 = fig2.add_subplot(223)
        ax24 = fig2.add_subplot(224)

        ax21.scatter(self.res_freqs, 1.0e6 * (self.res_fit_params[:, 4] - self.res_freqs))
        ax21.set_xlabel("Found Resonance Freq. (GHz)")
        ax21.set_ylabel("Fit - Found Resonance Freq. (kHz)")
        ax21.set_ylim([-100,100])
        ax22.scatter(self.res_freqs, self.res_fit_params[:, 5])
        ax22.set_xlabel("Found Resonance Freq. (GHz)")
        ax22.set_ylabel(r"$Q_i$")
        ax22.set_ylim([0, 1.5e5])
        ax23.scatter(self.res_freqs, self.res_fit_params[:, 6])
        ax23.set_xlabel("Found Resonance Freq. (GHz)")
        ax23.set_ylabel(r"$Q_c$")
        ax23.set_ylim([0, 1.5e5])
        ax24.scatter(self.res_freqs, self.res_fit_params[:, 7])
        ax24.set_xlabel("Found Resonance Freq. (GHz)")
        ax24.set_ylabel("Fano Parameter")
        ax24.set_ylim([-1, 1])

        # plot histograms of fit results
        fig3 = plt.figure(3)
        ax31 = fig3.add_subplot(221)
        ax32 = fig3.add_subplot(222)
        ax33 = fig3.add_subplot(223)
        ax34 = fig3.add_subplot(224)

        ax31.hist(1e6*(self.res_fit_params[:, 4]-self.res_freqs), bins=np.linspace(-100,100,51))
        ax31.set_xlabel("Fit - Found Resonance Freq. (kHz)")
        ax31.set_ylabel("# of occurrences")
        ax32.hist(self.res_fit_params[:, 5], bins=np.linspace(0, 150000, 31))
        ax32.set_xlabel(r"$Q_i$")
        ax32.set_ylabel("# of occurrences")
        ax33.hist(self.res_fit_params[:, 6], bins = np.linspace(0, 150000, 31))
        ax33.set_xlabel(r"$Q_c$")
        ax33.set_ylabel("# of occurrences")
        ax34.hist(self.res_fit_params[:, 7], bins = np.linspace(-1, 1, 21))
        ax34.set_xlabel("Fano Parameter")
        ax34.set_ylabel("# of occurrences")

        plt.show()


if __name__ == "__main__":
    file = os.path.join(s21_dir, 'umux', "s4data", "s21_56_pre.txt")
    group_delay = 31.839
    res_fit = ResFit(file=file, group_delay=group_delay, verbose=True, freq_units="MHz", auto_process=True)
