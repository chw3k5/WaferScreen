import numpy as np
from matplotlib import pyplot as plt
from waferscreen.read.table_read import floats_table


def plot_21(file):
    data_dict = floats_table(file, delimiter=",")
    if isinstance(data_dict, list):
        data_dict = {'freq': data_dict[0], 'real': data_dict[1], 'imag': data_dict[2]}
    data_dict["mag"] = 20.0 * np.log10(np.sqrt(np.square(data_dict['real']) + np.square(data_dict['imag'])))
    data_dict['phase'] = np.arctan2(data_dict['imag'], data_dict['real'])

    plt.figure(figsize=(20, 8))
    plt.plot(data_dict["freq"], data_dict['mag'], color='firebrick')
    plt.show()
    return


if __name__ == "__main__":
    # file = os.path.join(s21_dir, "so", "7_Band01_2020-09-08_run9.csv")
    file = "D:\\waferscreen\\output\\s21\\8\\Band03\\2020-09-28\\flux_ramp\\sdata_res_19_cur_30uA.csv"
    plot_21(file=file)
