import os
import time
import scipy
import scipy.stats
import datetime
import numpy as np
from ref import working_dir
from waferscreen.inst_control.keithley2450 import Keithley2450
import matplotlib.pyplot as plt

location = 'nist'
location_dir = os.path.join(working_dir, location)
if not os.path.isdir(location_dir):
    os.mkdir(location_dir)
iv_output_dir = os.path.join(location_dir, 'iv')
if not os.path.isdir(iv_output_dir):
    os.mkdir(iv_output_dir)


def derivative(data, deriv_int):
    # y'=df(mV)/dmV
    # y'=d(data[:,1:])/d(data[:,0])
    last_index = len(data[:, 0])

    lenF = len(data[0, 1:])
    deriv = np.zeros((last_index - deriv_int, len(data[0, :])))

    Fdata1 = data[:last_index - deriv_int, 1:]
    Fdata2 = data[deriv_int:, 1:]
    Xdata1 = data[:last_index - deriv_int, 0]
    Xdata2 = data[deriv_int:, 0]

    Fdiff = Fdata2 - Fdata1
    Xdiff = Xdata2 - Xdata1
    for n in range(lenF):
        deriv[:, n + 1] = Fdiff[:, n] / Xdiff
    deriv[:, 0] = (Xdata1 + Xdata2) / 2
    status = True
    return status, deriv


def conv(data, mesh, min_cdf, sigma, verbose):
    status = False
    if verbose:
        print('Doing convolution of data cdf = ' + str(min_cdf) + '  sigma = ' + str(sigma))
    sigmaSteps = np.ceil(sigma / mesh)  # unitless, rounded up to nearest integer
    # Normal Kernel Calculation
    n = 0
    finished = False
    try:
        mV_len = len(data[:, 0])
        while not finished:
            n = n + 1
            Xnorm = range(-n, n + 1)
            norm = scipy.stats.norm(0, sigmaSteps).pdf(Xnorm)
            cdf = sum(norm)
            if cdf >= min_cdf:
                finished = True
        Xnorm = range(-n, n + 1)
        norm = scipy.stats.norm(0, sigmaSteps).pdf(Xnorm)
        normMatrix = np.zeros((mV_len, mV_len + len(norm) - 1), dtype=float)

        # matrix kernal for convolution
        for m in range(0, mV_len):
            tempVec = np.zeros((mV_len + len(norm) - 1), dtype=float)
            tempVec[m:m + 2 * n + 1] = norm
            normMatrix[m,] = tempVec

        normMatrix2 = normMatrix[:, n:len(normMatrix[0, :]) - n]
        # here is the point where the actual convolution takes place
        weight = np.sum(normMatrix2, axis=1)
        for p in range(len(data[0, :]) - 1):
            data[:, p + 1] = np.dot(data[:, p + 1], normMatrix2) / weight
            status = True
    except IndexError:
        status = False
    except TypeError:
        status = False
    return data, status


def do_derivatives(matrix, der1_int, do_der1_conv, der1_min_cdf, der1_sigma,
                   der2_int, do_der2_conv, der2_min_cdf, der2_sigma, regrid_mesh,
                   verbose):
    status, der1 = derivative(matrix, der1_int)
    if der1 is not None:
        if do_der1_conv:
            der1, status = conv(der1, regrid_mesh, der1_min_cdf, der1_sigma, verbose)
        status, der2 = derivative(der1, der2_int)
        if do_der2_conv:
            der2, status = conv(der2, regrid_mesh, der2_min_cdf, der2_sigma, verbose)
    else:
        der2 = None
        print("der1 = ", der1)
        print("der2 = ", der2)
    return der1, der2


def findlinear(x, ydprime, linif, verbose):
    status = True
    if len(x) == len(ydprime):
        status = True
    else:
        status = False
        print("In the function findlinear the dependent and independent variables do not have the same length,\n" +
              " returning statuse false")
    linMask = np.zeros(len(x))
    dataMax = max(abs(ydprime))
    normal_data = abs(ydprime / dataMax)
    np.putmask(linMask, normal_data < linif, 1)
    lin_start = []
    lin_end = []
    for n in range(len(x)):
        if n == 0:
            if linMask[n] == 1:
                lin_start.append(n)
        else:
            if linMask[n - 1] == 1 and linMask[n] == 0:
                lin_end.append(n - 1)
            elif linMask[n - 1] == 0 and linMask[n] == 1:
                lin_start.append(n)
            elif n == len(x) - 1 and linMask[n] == 1:
                lin_end.append(n)
    if verbose:
        print(str(len(lin_end)) + " linear regions were found:")
    return status, lin_start, lin_end


def resfitter(x, y, lin_start, lin_end):
    # this reports the slopes and the data for the best-fit lines for linear regions
    big = -1
    Y = np.zeros((2, len(lin_end)))
    X = np.zeros((2, len(lin_end)))
    slopes = np.zeros(len(lin_end))
    intercepts = np.zeros(len(lin_end))
    for ii in range(len(lin_end)):
        size = lin_end[0] - lin_start[0]
        if (size > big):
            big = size
        if lin_start[ii] != lin_end[ii]:
            slope, intercept = np.polyfit(x[lin_start[ii] + 1:lin_end[ii] + 1], y[lin_start[ii] + 1:lin_end[ii] + 1], 1)
            Y[0, ii] = slope * x[lin_start[ii] + 1] + intercept
            Y[1, ii] = slope * x[lin_end[ii] + 1] + intercept

            X[0, ii] = x[lin_start[ii] + 1]
            X[1, ii] = x[lin_end[ii] + 1]
            slopes[ii] = slope
            intercepts[ii] = intercept
    return slopes, intercepts, X, Y


def linfit(X, Y, linif, der1_int, do_der1_conv, der1_min_cdf, der1_sigma,
           der2_int, do_der2_conv, der2_min_cdf, der2_sigma,
           verbose):
    matrix = np.zeros((len(X), 2))
    matrix[:, 0] = X
    matrix[:, 1] = Y
    try:
        regrid_mesh = abs(X[1] - X[0])
    except IndexError:
        regrid_mesh = 0.01
    der1, der2 = do_derivatives(matrix, der1_int, do_der1_conv, der1_min_cdf, der1_sigma,
                                der2_int, do_der2_conv, der2_min_cdf, der2_sigma, regrid_mesh,
                                verbose)
    try:
        # print der1 != [], der1
        status, lin_start, lin_end = findlinear(der2[:, 0], der2[:, 1], linif, verbose)
        slopes, intercepts, bestfits_X, bestfits_Y = resfitter(X, Y, lin_start, lin_end)
    except TypeError:
        slopes = None
        intercepts = None
        bestfits_X = None
        bestfits_Y = None
    return slopes, intercepts, bestfits_X, bestfits_Y


def linifxyplotgen(x_vector, y_vector, label='', plot_list=None, leglines=None, leglabels=None,
                   color='black', linw=1, scale_str='', linif=0.3,
                   der1_int=1, do_der1_conv=False, der1_min_cdf=0.90, der1_sigma=0.05, der2_int=1,
                   do_der2_conv=False, der2_min_cdf=0.9, der2_sigma=0.1, verbose=False):
    if plot_list is None:
        plot_list = []
    if leglines is None:
        leglines = []
    if leglabels is None:
        leglabels = []
    slopes, intercepts, bestfits_x, bestfits_y \
                = linfit(x_vector, y_vector, linif, der1_int, do_der1_conv, der1_min_cdf, der1_sigma, der2_int,
                          do_der2_conv, der2_min_cdf, der2_sigma, verbose)
    if slopes is not None:
        ### Line styles for ohm regions
        lineStyles = ["--", '-', ':', "-."]
        counter = 0
        len_lineStyles = len(lineStyles)
        for n in range(len(bestfits_x[0,:])):
            ls = lineStyles[counter % len_lineStyles]
            plot_list.append([bestfits_x[:,n], bestfits_y[:, n], color, linw, ls, scale_str])
            leglines.append([color, ls, linw])
            resist = 1000*(1.0/slopes[n])
            if label is None:
                leglabels.append(None)
            else:
                leglabels.append(str('%3.1f' % resist)+label)
                # leglabels.append(str(resist)+label)
            counter += 1
    return plot_list, leglines, leglabels


def gen_output_path(wafer, wafer_coord, structure_name, utc):
    utc_str = str(utc).replace(":", "-")
    basename = F"wafer{wafer}_coord{wafer_coord[0]}_{wafer_coord[1]}_{structure_name}_utc{utc_str}.csv"
    return os.path.join(iv_output_dir, basename)


class IVSweep:
    def __init__(self, wafer, wafer_coord, structure_name, acquire_new=False, connection_type='lan', verbose=True):
        self.wafer = wafer
        self.wafer_coord = wafer_coord
        self.test_structure = structure_name
        self.connection_type = connection_type
        self.verbose = verbose

        if acquire_new:
            self.source = Keithley2450(connection_type=self.connection_type, verbose=self.verbose)
            self.source.startup()
            self.source.set_source_type(v_range=b"2e1", i_range=b"100e-6")
        else:
            self.source = None

        self.output_file_name = None
        self.start_ua = None
        self.end_ua = None
        self.num_points = None
        self.step_ua = None
        self.sweep_array_ua = None
        self.sweeps_array_v = None
        self.meas_utc = None

    def sweep(self, start_ua, end_ua, num_points=101, v_gain=1.0):
        self.start_ua = start_ua
        self.end_ua = end_ua
        if self.start_ua > self.end_ua:
            self.start_ua, self.end_ua = self.end_ua, self.start_ua
        self.num_points = num_points

        output_data = self.source.sweep(start_curr=start_ua * 1.0e-6, stop_curr=end_ua * 1.0e-6, num_points=num_points,
                                        delay_s=0.1)
        self.sweep_array_ua = np.array([1.0e6 * a_tup[1] for a_tup in output_data])
        self.sweeps_array_v = np.array([a_tup[2] for a_tup in output_data]) / v_gain
        self.meas_utc = datetime.datetime.utcnow()

    def write(self):
        self.output_file_name = gen_output_path(wafer=self.wafer, wafer_coord=self.wafer_coord,
                                                structure_name=self.test_structure, utc=self.meas_utc)
        with open(self.output_file_name, 'w') as f:
            f.write("current_ua,voltage_v\n")
            for current_ua, voltage_v in zip(self.sweep_array_ua, self.sweeps_array_v):
                f.write(F"{current_ua},{voltage_v}\n")

    def read(self, path):
        with open(path, 'r') as f:
            raw_lines = [a_line.rstrip().split(",") for a_line in f.readlines()]
        header = raw_lines[0]
        body = raw_lines[1:]
        data_dict = {column_name: [] for column_name in header}
        [[data_dict[column_name].append(float(datum_str)) for column_name, datum_str in zip(header, data_line)]
         for data_line in body]
        self.sweep_array_ua = np.array(data_dict["current_ua"])
        self.sweeps_array_v = np.array(data_dict["voltage_v"])

    def close(self):
        self.source.shutdown()

    def plot(self, simple=True):
        # calculations
        a_array = self.sweep_array_ua * 1.0e-6
        mv_array = self.sweeps_array_v * 1.0e3

        # plot of the data
        raw_data_markercolor = "dodgerblue"
        raw_data_marker = "o"
        raw_data_markersize = 8
        raw_data_alpha = 0.5
        raw_data_ls = 'solid'
        raw_data_linewidth = 1
        raw_data_line_color = 'black'
        plt.plot(mv_array, self.sweep_array_ua, ls=raw_data_ls, linewidth=raw_data_linewidth, color=raw_data_line_color,
                 marker=raw_data_marker, alpha=raw_data_alpha, markerfacecolor=raw_data_markercolor,
                 markersize=raw_data_markersize)
        leglines = [plt.Line2D(range(10), range(10), color=raw_data_line_color, ls=raw_data_ls,
                                   linewidth=raw_data_linewidth,
                                   marker=raw_data_marker,
                                   markersize=raw_data_markersize,
                                   markerfacecolor=raw_data_markercolor, alpha=raw_data_alpha)]
        leglabels = ["raw data"]

        if simple:
            res, v_offset = np.polyfit(a_array, self.sweeps_array_v, deg=1)
            fit_mv_array = ((self.sweep_array_ua * 1.0e-6 * res) + v_offset) * 1.0e3
            res_color = 'firebrick'
            res_linewidth = 5
            res_ls = 'solid'
            plt.plot(fit_mv_array, self.sweep_array_ua, ls=res_ls, color=res_color, linewidth=res_linewidth)

            leglines.append(plt.Line2D(range(10), range(10), color=res_color, ls=res_ls, linewidth=res_linewidth))
            leglabels.append(F"Resistance: {'%2.3f' % res} Ohms")
        else:
            plot_list, _leglines, res_leglabels = linifxyplotgen(x_vector=mv_array, y_vector=self.sweep_array_ua,
                                                                 label='', plot_list=None, leglines=None,
                                                                 leglabels=None,
                                                                 color='goldenrod', linw=2, scale_str='', linif=0.005,
                                                                 der1_int=5, do_der1_conv=False, der1_min_cdf=0.90,
                                                                 der1_sigma=0.05, der2_int=5,
                                                                 do_der2_conv=False, der2_min_cdf=0.9, der2_sigma=0.1,
                                                                 verbose=self.verbose)

            for (mv, ua, color, linewidth, ls, extra_text), label_text in zip(plot_list, res_leglabels):
                if float(label_text) > 10:
                    plt.plot(mv, ua, color=color, linewidth=linewidth, ls=ls)
                    leglines.append(plt.Line2D(range(10), range(10), color=color, ls=ls, linewidth=linewidth))
                    leglabels.append(label_text + " Ohms")


        plt.legend(leglines, leglabels, loc=0, numpoints=3, handlelength=5, fontsize=10)
        plt.ylabel("Current (uA)")
        plt.xlabel("Voltage (mV)")
        plt.show(block=True)


class VVSweep:
    def __init__(self):
        self.sweeps_array_mv = None
        self.sweeps_array_uv = None

        self.source = Keithley2450(connection_type='lan', verbose=True)
        self.source.startup()
        self.source.set_source_type(source_type='voltage', sense_type='voltage', v_range=b'2')

    def sweep(self, start_uv=-10000, end_uv=10000, num_points=101):
        output_data = self.source.sweep(start_curr=start_uv * 1.0e-6, stop_curr=end_uv * 1.0e-6, num_points=num_points,
                                        delay_s=0.1)
        self.sweeps_array_uv = np.array([1.0e6 * a_tup[1] for a_tup in output_data])
        self.sweeps_array_mv = np.array([1.0e3 * a_tup[2] for a_tup in output_data])

    def plot(self):
        xv_array = self.sweeps_array_uv * 1.0e-6
        yv_array = self.sweeps_array_mv * 1.0e-3
        gain, v_offset = np.polyfit(xv_array, yv_array, deg=1)
        # plt.plot(self.sweeps_array_uv, (self.sweeps_array_uv * gain) + (v_offset * 1.0e3), ls='solid',
        #          color="firebrick", linewidth=5)
        plt.plot(self.sweeps_array_uv, self.sweeps_array_mv, ls='solid', linewidth=1, color='black',
                 marker="o", alpha=0.5, markerfacecolor="dodgerblue")

        plt.ylabel("Current (mV)")
        plt.xlabel("Voltage (uV)")
        plt.title(F"PreAmp Gain: {'%2.3f' % gain} V/V")
        plt.show(block=True)

    def close(self):
        self.source.shutdown()


def sweeper(start_ua, end_ua, num_points, wafer, wafer_coord, structure_name, plot=True, verbose=True, close=True):
    iv = IVSweep(wafer=wafer, wafer_coord=wafer_coord, structure_name=structure_name,
                 acquire_new=True, connection_type='lan', verbose=verbose)
    iv.sweep(start_ua=start_ua, end_ua=end_ua, num_points=num_points, v_gain=96.0)
    if close:
        iv.close()
    iv.write()
    if plot:
        iv.plot()
    return iv


def dipped_squid_sweep(wafer, wafer_coord, structure_name=None):
    if structure_name is None:
        structure_name = "4K dip sweep"
    return sweeper(start_ua=-100, end_ua=100, num_points=1000, wafer=wafer, wafer_coord=wafer_coord,
                   structure_name=structure_name, plot=True, verbose=True, close=True)


def warm_squid_sweep(wafer, wafer_coord, structure_name=None):
    if structure_name is None:
        structure_name = "warm sweep"
    return sweeper(start_ua=-10, end_ua=10, num_points=100, wafer=wafer, wafer_coord=wafer_coord,
                   structure_name=structure_name, plot=True, verbose=True, close=True)


def is_alive_squid_sleep(wafer, wafer_coord, structure_name=None):
    if structure_name is None:
        structure_name = "warm is_alive"
    return sweeper(start_ua=-1, end_ua=1, num_points=10, wafer=wafer, wafer_coord=wafer_coord,
                   structure_name=structure_name, plot=True, verbose=True, close=True)


def test_preamp_gain():
    vv = VVSweep()
    vv.sweep()
    vv.plot()
    vv.close()
    return vv


def read_file_iv(path, verbose=True):
    iv = IVSweep(wafer=None, wafer_coord=None, structure_name=None,
                 acquire_new=False, verbose=verbose)
    iv.read(path=path)
    iv.plot(simple=False)
    return iv


if __name__ == "__main__":
    preamp_gain_test = False
    is_alive_test = False
    warm_squid_test = False
    dipped_squid_test = False
    wafer = '6'
    wafer_coord = (0, 0)  # add and a/b later
    structure_name = 'dipped 2.5umx2.5um series pos70'

    read_from_file = True
    read_path = os.path.join(iv_output_dir,
                             "wafer6_coord0_0_dipped 2.5umx2.5um series pos70_utc2021-03-03 17-21-59.074663.csv")

    if preamp_gain_test:
        vv = test_preamp_gain()
    if is_alive_test:
        iv = is_alive_squid_sleep(wafer=wafer, wafer_coord=wafer_coord, structure_name=structure_name)
    if warm_squid_test:
        iv = warm_squid_sweep(wafer=wafer, wafer_coord=wafer_coord, structure_name=structure_name)
    if dipped_squid_test:
        iv = dipped_squid_sweep(wafer=wafer, wafer_coord=wafer_coord, structure_name=structure_name)
    if read_from_file:
        iv = read_file_iv(path=read_path)
