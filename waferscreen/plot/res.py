import numpy as np
from matplotlib import pyplot as plt


def plot_res_sweep(res_params, plot_file_name=None):
    # plot fit results vs. frequency
    fig = plt.figure(figsize=(14, 8))
    ax22 = fig.add_subplot(222)
    ax23 = fig.add_subplot(223)
    ax24 = fig.add_subplot(224)
    # ["Amag", "Aphase", "Aslope", "tau", "f0", "Qi", "Qc", "Zratio"]
    f0_vec = np.array([single_params.f0 for single_params in res_params])
    Qi_vec = np.array([single_params.Qi for single_params in res_params])
    Qc_vec = np.array([single_params.Qc for single_params in res_params])
    Zratio_vec = np.array([single_params.Zratio for single_params in res_params])
    # ax21 = fig.add_subplot(221)
    # ax21.scatter(freq_ghz, 1.0e6 * (f0_vec - res_freq_est))
    # ax21.set_xlabel("Found Resonance Freq. (GHz)")
    # ax21.set_ylabel("Fit - Found Resonance Freq. (kHz)")
    # ax21.set_ylim([-100, 100])
    ax22.scatter(f0_vec, Qi_vec)
    ax22.set_xlabel("Found Resonance Freq. (GHz)")
    ax22.set_ylabel(r"$Q_i$")
    ax22.set_ylim([0, 1.5e5])
    ax23.scatter(f0_vec, Qc_vec)
    ax23.set_xlabel("Found Resonance Freq. (GHz)")
    ax23.set_ylabel(r"$Q_c$")
    ax23.set_ylim([0, 1.5e5])
    ax24.scatter(f0_vec, Zratio_vec)
    ax24.set_xlabel("Found Resonance Freq. (GHz)")
    ax24.set_ylabel("Fano Parameter")
    ax24.set_ylim([-1, 1])
    fig.suptitle(F"{len(res_params)} Resonators", fontsize=16)

    if plot_file_name is not None:
        fig.savefig(plot_file_name)
    else:
        plt.show()
    return


def histogram_res_sweep(freq_ghz, res_params, plot_file_name=None):
    # plot histograms of fit results
    fig = plt.figure()
    ax31 = fig.add_subplot(221)
    ax32 = fig.add_subplot(222)
    ax33 = fig.add_subplot(223)
    ax34 = fig.add_subplot(224)
    f0_vec = np.array([single_params.f0 for single_params in res_params])
    Qi_vec = np.array([single_params.Qi for single_params in res_params])
    Qc_vec = np.array([single_params.Qc for single_params in res_params])
    Zratio_vec = np.array([single_params.Zratio for single_params in res_params])

    ax31.hist(1e6 * (f0_vec - freq_ghz), bins=np.linspace(-100, 100, 51))
    ax31.set_xlabel("Fit - Found Resonance Freq. (kHz)")
    ax31.set_ylabel("# of occurrences")
    ax32.hist(Qi_vec, bins=np.linspace(0, 150000, 31))
    ax32.set_xlabel(r"$Q_i$")
    ax32.set_ylabel("# of occurrences")
    ax33.hist(Qc_vec, bins=np.linspace(0, 150000, 31))
    ax33.set_xlabel(r"$Q_c$")
    ax33.set_ylabel("# of occurrences")
    ax34.hist(Zratio_vec, bins=np.linspace(-1, 1, 21))
    ax34.set_xlabel("Fano Parameter")
    ax34.set_ylabel("# of occurrences")
    if plot_file_name is not None:
        fig.savefig(plot_file_name)
    else:
        plt.show()
    return


if __name__ == '__main__':
    import os
    from ref import pro_data_dir
    from waferscreen.mc.prodata import read_res_params

    path = os.path.join(pro_data_dir, "princton_s21_fits.csv")
    plot_path = path.replace(".csv", ".pdf")
    res_params = read_res_params(path)
    plot_res_sweep(res_params, plot_file_name=plot_path)
