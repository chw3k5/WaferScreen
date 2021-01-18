"""
Purpose:
 Rudimentary peak finder based on the algorithm
 developed by Mariscotti [1967] for high resolution
 gamma ray spectroscopy.

 Mariscotti, M.A., A method for automatic identification of
  peaks in the presence of background and its application
  to spectrum analysis, Nuclear Instruments and Methods
  Volume 50, Issue 2, 1 May 1967, Pages 309-320.

Method:
 The generalized second derivative (GSD) is calculated and
 zero crossings are found.  The upper channel for
 each positive crossing is stored along with the
 lower channel for each negative crossing. Pairs
 of crossings are sought within which the GSD is positive
 (top of the sombrero). Such pairs contain peaks.
 Valid peaks are those for which the peak GSD value
 is greater than some factor times the propogated
 uncertainty of the peak GSD value.

 Two methods are available for determining the
 peak channel.  The default is to find the maximum
 function (y) value within the two crossing channels.
 If pk_gsd is set, then the maximum value of the
 GSD (peak of the sombrero) is used. The pk_gsd
 method might be preferred if the data are very
 noisy.

Inputs:
 y         - vector of values representing a spectrum
             containing peaks
 err       - keyword, contains the
             uncertainty in the y values.  If not set,
             then the y values are assumed to be
             Poisson random variates (counts)
 nsmooth   - keyword, contains the number
             of smoothing steps (must be greater than 0).
             if not set, then 5 smoothing steps are used
 errFactor - keyword, for peak detection, the generalized
             second derivative (GSD) at candidate peak
             locations must by greater than factor times
             the GSD uncertainty. The default is
             errfactor=1.
 plot     -  keyword, if set produces a diagnostic plot
 pk_gsd   -  keyword, if set uses the maximum GSD value
             to identify the peak channel# otherwise,
             the maximum y value is used to determine the
             peak channel.

Outputs:
 gaussParametersArray   - 'None' or [] or np array
   if no crossing points (inflection points) are found for the generalized second derivative,
      None is returned

   if there are crossing points but none are selected by the algorithim as peaks,
      [] the empty list is returned

   if peaks are identified by the algorithm,
      A np array is returned of the Gaussian parameters.
      The parameters [A, B, and C] = gaussParametersArray[peakNum,:] for the
      parameters for a single peak with index equal to peakNum
      where A gaussian distribution is defined as G(x)=A * exp((x-B)^2 / (2 * C^2)).
      The amplitudes (A) of the peaks can be found as gaussParametersArray[:,0],
      the peak index value or mean (B) of the peaks can be found as gaussParametersArray[:,1],
      and the standard deviation or sigma (C) of the peaks can be found as gaussParametersArray[:,2],



Concerns:
 The function does not close out plot windows and generates
 new ones every time it is called with /plot. The user needs
 to close windows periodically to avoid making a mess (e.g.,
 using closewin.pro).

 When the max y approach (default) is used to find
 the peak location, the channel number for max y
 in each candidate peak region is used to test if
 the GSD is factor times greater than uncertainty
 in the GSD value.  As a result, fewer peaks are
 identified using the max y method than for the
 pk_gsb method when the data are noisy.  A future
 improvement might be to always select a peak region
 based on peak GSD and have the option to select
 the channel within the accepted region as max y.

Revision history:
$Id: mariscotti.pro,v 1.2 2010/06/16 02:58:24 jpmorgen Exp $
 v1.0 Thomas H. Prettyman (THP), Planetary Science Institute
 26-Mar-2010 (THP)
    corrected the GSD standard deviation estimate:
     err=sqrt(1./float(m)^5*err) --> err=sqrt(1./float(m)^m*err)
    adjusted the index range for gsd so that nsmooth=0 and 1 will
     work
    updated documentation
    added the pk_gsd option
 v1.2 Jeff Morgenthaler (jpm), Planetary Science Institute
15-Jun-2010 (jpm)
Experimented with IDL native deriv and derivsig functions.  Failed
miserably.  Cleaned up plotting.

On March 1 2017, this code was translated form IDL to python 2.7 by
Caleb Wheeler for the Fisk Cube sat program.

Converted to python 3 and rewritten for clarity. Jan 2021 By Caleb
while at NIST.
"""


import numpy as np
import matplotlib.pyplot as plt
from operator import itemgetter
from scipy.signal import savgol_filter
from waferscreen.plot.quick_plots import quick_plotter, rescale


def boxCar(anArray, kernalSize = 3, mode='same'):
    kernel = np.ones((kernalSize))
    convArray = np.convolve(anArray, kernel, mode=mode)
    return convArray


def mariscotti(y, nsmooth=5, err=None, error_factor=1.0e6, pk_gsd=True, polyorder=2, find_peaks=False, show_plot=True, verbose=True):
    y = np.array(y)
    # defaults

    # kwargs err
    if nsmooth <= polyorder:
        print(F"nsmooth={nsmooth}, the number of indexes to smooth over must be greater than polyorder={polyorder}")
        nsmooth = polyorder + 1
        print(F"nsmooth set to: {nsmooth}")
    if nsmooth % 2 == 0:
        print(F"nsmooth={nsmooth} must be odd.")
        nsmooth += 1
        print(F"nsmooth set to: {nsmooth}")
    if verbose:
        print("Starting the Mariscotti peak finding and Gaussian parametrization algorithm.")

    # rudimentary peak finder based on Mariscotti [1966]
    kernel1 = np.array([-1, 2, -1])
    # gsd stands for generalized second derivative
    gsd = np.convolve(y, kernel1, 'same')
    # Filter
    gsd = savgol_filter(gsd, window_length=nsmooth, polyorder=polyorder)

    # Error
    if err is None:
        err = np.ones(len(y)) * np.std(y)
    else:
        kernel2 = np.array([1, 4, 1])
        err = np.convolve(err, kernel2, 'same')
        # Filter
        err = savgol_filter(err, window_length=nsmooth, polyorder=polyorder)
    max_allowed_error = error_factor * np.sqrt(err)
    mean_y = np.mean(y)
    # minimum section length to contain an extrema
    section_len = 3

    # find the zero crossings that are in inflection points
    icross_maxima = []
    icross_minima = []
    for i in range(len(gsd) - 1):

        # neg to positive test
        if (gsd[i] < 0.0) and (0.0 <= gsd[i + 1]):
            # if looking for local maxima append to include positive values
            icross_maxima.append(i + 1)
            # if looking for local minima append to include negative values
            icross_minima.append(i)
        # pos to negative test
        elif (0.0 < gsd[i]) and (gsd[i + 1] <= 0.0):
            # if looking for local maxima append to include positive values
            icross_maxima.append(i)
            # if looking for local minima append to include negative values
            icross_minima.append(i + 1)
    if find_peaks:
        icross = icross_maxima
    else:
        icross = icross_minima

    plot_dict = {}
    plot_dict['x_fig_size'] = 24
    plot_dict['y_fig_size'] = 10
    plot_dict['verbose'] = verbose
    plot_dict['show'] = True
    if icross == []:
        print('No places where the second derivative crosses zero, so no peaks were found by Mariscotti algorithm.')
        if show_plot:
            # plot formatting for index (x) and spectrum values (y) where the gsd (generalized 2nd derivative)
            # crosses zero (this is marks a boundaries for finding local extrema)
            x = range(len(y))
            # plot formatting for the gsd (generalized second derivative)
            gsd_rescaled = rescale(y, gsd)
            gsd_zeroLine = rescale(y, gsd, np.zeros(len(y)))
            # These can be a list or a single value
            plot_dict['y_data'] = [y, gsd_rescaled, gsd_zeroLine]
            plot_dict['x_data'] = [x, x, x]
            plot_dict['colors'] = ['firebrick', 'darkorchid', "black"]
            plot_dict['ls'] = ['-', 'dashed', 'dotted']
            plot_dict['line_width'] = [2, 1, 1]
            plot_dict['legendLabel'] = ['The data', '2nd derivative', '2nd deri = 0']
            plot_dict['fmt'] = ['None', 'None', 'None']
            plot_dict['markersize'] = [5, 5, 5]
            plot_dict['alpha'] = [1.0, 1.0, 1.0]
            plot_dict['legend_lines'] = [plt.Line2D(range(10), range(10), color=color, ls=ls, linewidth=linew,
                                                    marker=fmt,
                                                    markersize=markersize, markerfacecolor=color,
                                                    alpha=alpha)
                                         for color, ls, linew, fmt, markersize, alpha in
                                         zip(plot_dict['colors'], plot_dict['ls'], plot_dict['line_width'],
                                             plot_dict['fmt'], plot_dict['markersize'], plot_dict['alpha'])]
            # These must be a single value
            plot_dict['title'] = '2nd Derivative Zero Crossing Zero (None Found!)'
            plot_dict['x_label'] = 'Channel Number'
            plot_dict['legendAutoLabel'] = False
            plot_dict['do_legend'] = True
            plot_dict['legendLoc'] = 0
            plot_dict['legendNumPoints'] = 3
            plot_dict['legendHandleLength'] = 5
            quick_plotter(plot_dict=plot_dict)
        if verbose:
            print("Mariscotti algorithm completed.\n")
        return []


    # find the peaks
    maxima_list = []
    for inflection_index in range(len(icross_maxima) - 1):
        icross_start = icross_maxima[inflection_index]
        icross_end = icross_maxima[inflection_index + 1]
        if len(gsd[icross_start: icross_end]) >= section_len:
            test_gsd_maxima = gsd[icross_start: icross_end]
            if all(test_gsd_maxima >= 0.0):
                index_list = np.arange(len(test_gsd_maxima))
                if pk_gsd:
                    y_subSmaple = y[icross_start: icross_end]
                    maxval = max(y_subSmaple)
                    indexOfPeak_gsd_subSample = list(index_list[y_subSmaple == maxval])
                else:
                    maxval = max(test_gsd_maxima)
                    indexOfPeak_gsd_subSample = list(index_list[test_gsd_maxima == maxval])
                if 1 == len(indexOfPeak_gsd_subSample):
                    index_of_maxima = indexOfPeak_gsd_subSample[0] + icross_start
                # if more than one index with the max value, take the max GSD value closest to the max y value
                else:
                    highest_gsd_value = float('-Inf')
                    index_of_maxima = None
                    for test_index in indexOfPeak_gsd_subSample:
                        current_gsd_value = test_gsd_maxima[test_index]
                        if highest_gsd_value < current_gsd_value:
                            highest_gsd_value = current_gsd_value
                            index_of_maxima = test_index
                # rejection
                if abs(mean_y - y[index_of_maxima]) < max_allowed_error[index_of_maxima]:
                    sigma = float(icross_start - icross_end) / float(2.0)
                    maxima_list.append((maxval, index_of_maxima, sigma))
    # find valleys
    minima_list = []
    for inflection_index in range(len(icross_minima) - 1):
        icross_start = icross_minima[inflection_index]
        icross_end = icross_minima[inflection_index + 1]
        test_gsd_minima = gsd[icross_start: icross_end]
        if len(test_gsd_minima) >= section_len:
            if all(test_gsd_minima <= 0.0):
                index_list = np.arange(len(test_gsd_minima))
                if pk_gsd:
                    y_test_minima = y[icross_start: icross_end]
                    minval = min(y_test_minima)
                    indexOfPeak_gsd_subSample = list(index_list[y_test_minima == minval])
                else:
                    minval = min(test_gsd_minima)
                    indexOfPeak_gsd_subSample = list(index_list[test_gsd_minima == minval])
                if 1 == len(indexOfPeak_gsd_subSample):
                    index_of_minima = indexOfPeak_gsd_subSample[0] + icross_start
                # if more than one index with the min value, take the min GSD value closest to the min y value
                else:
                    lowest_gsd_value = float('Inf')
                    index_of_minima = None
                    for test_index in indexOfPeak_gsd_subSample:
                        current_gsd_value = test_gsd_minima[test_index]
                        if lowest_gsd_value > current_gsd_value:
                            lowest_gsd_value = current_gsd_value
                            index_of_minima = test_index
                # rejection
                # if abs(mean_y - y[index_of_minima]) < max_allowed_error[index_of_minima]:
                sigma = float(icross_start - icross_end) / float(2.0)
                minima_list.append((minval, index_of_minima, sigma))
    
    if find_peaks:
        gaussParameters = maxima_list
    else:
        gaussParameters = minima_list
    if gaussParameters == []:
        print("No peaks were found by the Mariscotti algorithm, "+
              "but there were places where the second derivative crossed zero.")
        print("This can happen if the maximum allowed error at a peak is greater then the generalized "+
              "second derivative (gsd) at that point.")
        print("The 'errFactor' =", error_factor, "can be set using the kwarg 'errFactor' to scale the "+
              "maximum allowed error.")
        if show_plot:
            # plot formatting for index (x) and spectrum values (y) where the gsd (generalized 2nd derivative)
            # crosses zero (this is marks a boundaries for finding local extrema)
            y_icrossVals = [y[icrossVal] for icrossVal in icross]
            x = range(len(y))
            # plot formatting for the gsd (generalized second derivative)
            gsd_rescaled = rescale(y, gsd)
            gsd_zeroLine = rescale(y, gsd, np.zeros(len(y)))
            gsd_zeroLine_icrossVals = rescale(y, gsd, np.zeros(len(icross)))
            max_allowed_error_rescaled  = rescale(y, gsd, max_allowed_error)

            # These can be a list or a single value
            plot_dict['y_data'] = [y, max_allowed_error_rescaled, gsd_rescaled, gsd_zeroLine, gsd_zeroLine_icrossVals, y_icrossVals]
            plot_dict['x_data'] = [x, x, x, x, icross, icross]
            plot_dict['colors'] = ['firebrick', 'LawnGreen', 'darkorchid', "black", 'black', 'dodgerblue']
            plot_dict['legendLabel'] = ['The data', 'max allowed error', '2nd derivative', '2nd deri = 0', 'cross point', 'cross point']
            plot_dict['fmt'] = ['None', 'None', 'None', 'None', 'x', 'o']
            plot_dict['markersize'] = [5, 5, 5, 5, 10, 9]
            plot_dict['alpha'] = [1.0, 1.0, 1.0, 1.0, 0.7, 0.7]
            plot_dict['ls'] = ['-', '-', 'dashed', 'dotted', 'None', 'None']
            plot_dict['line_width'] = [2, 1, 1, 1, 1, 1]
            plot_dict['legend_lines'] = [plt.Line2D(range(10), range(10), color=color, ls=ls, linewidth=linew,
                                                    marker=fmt,
                                                    markersize=markersize, markerfacecolor=color,
                                                    alpha=alpha)
                                         for color, ls, linew, fmt, markersize, alpha in
                                         zip(plot_dict['colors'], plot_dict['ls'], plot_dict['line_width'],
                                             plot_dict['fmt'], plot_dict['markersize'], plot_dict['alpha'])]
            # These must be a single value
            plot_dict['title'] = '2nd Derivative Zero Crossing Zero and Peaks Found'
            plot_dict['xlabel'] = 'Channel Number'
            plot_dict['legendAutoLabel'] = False
            plot_dict['do_legend'] = True
            plot_dict['legendLoc'] = 0
            plot_dict['legendNumPoints'] = 3
            plot_dict['legendHandleLength'] = 5
            quick_plotter(plot_dict=plot_dict)
        if verbose:
            print("Mariscotti algorithm completed.\n")
        return gaussParameters

    else:
        gaussParametersArray = np.array(gaussParameters)
        numOfPeaksFound = len(gaussParametersArray[:, 0])
        if verbose:
            optional_s = ''
            optional_es = ''
            if 1 < numOfPeaksFound:
                optional_s += 's'
                optional_es += 'es'
            print("A gaussian distribution is defined as G(x)=A * exp((x-B)^2 / (2 * C^2))")
            print("The Mariscotti algorithm has identified", numOfPeaksFound , "peak" + optional_s + ".")
            print("The index" + optional_es + " of the data where the peak can be found (B) are:", gaussParametersArray[:,1])
            print("And the corresponding data value" + optional_s + " for the peak" + optional_s + " (A) are data values:", gaussParametersArray[:,0])
            print("Finally, the sigma value" + optional_s + " (C) of the peak" + optional_s + " (calculated from the inflection points) are", gaussParametersArray[:,2])

        if show_plot:
            # plot formatting for index (x) and spectrum values (y) where the gsd (generalized 2nd derivative)
            # crosses zero (this is marks a boundaries for finding local extrema)
            y_icrossVals = [y[icrossVal] for icrossVal in icross]
            x = range(len(y))
            # plot formatting for the gsd (generalized second derivative)
            gsd_rescaled = rescale(y, gsd)
            gsd_zeroLine = rescale(y, gsd, np.zeros(len(y)))
            gsd_zeroLine_icrossVals = rescale(y, gsd, np.zeros(len(icross)))
            max_allowed_error_rescaled  = rescale(y, gsd, max_allowed_error)

            # These can be a list or a single value
            plot_dict['y_data'] = [y, max_allowed_error_rescaled, gsd_rescaled, gsd_zeroLine, gsd_zeroLine_icrossVals, y_icrossVals, gaussParametersArray[:,0]]
            plot_dict['x_data'] = [x, x, x, x, icross, icross, gaussParametersArray[:,1]]
            plot_dict['colors'] = ['firebrick', 'LawnGreen', 'darkorchid', "black", 'black', 'dodgerblue', 'darkorange']
            plot_dict['legendLabel'] = ['The data', 'max allowed error', '2nd derivative', '2nd deri = 0', 'cross point','cross point', 'found peaks']
            plot_dict['fmt'] = ['None', 'None', 'None', 'None', 'x', 'o', 'd']
            plot_dict['markersize'] = [5, 5, 5, 5, 10, 9, 10]
            plot_dict['alpha'] = [1.0, 1.0, 1.0, 1.0, 0.7, 0.7, 0.7]
            plot_dict['ls'] = ['-', '-', 'dashed', 'dotted', 'None', 'None', 'None']
            plot_dict['line_width'] = [2, 1, 1, 1, 1, 1, 1]
            plot_dict['legend_lines'] = [plt.Line2D(range(10), range(10), color=color, ls=ls, linewidth=linew,
                                                    marker=fmt,
                                                    markersize=markersize, markerfacecolor=color,
                                                    alpha=alpha)
                                         for color, ls, linew, fmt, markersize, alpha in
                                         zip(plot_dict['colors'], plot_dict['ls'], plot_dict['line_width'],
                                             plot_dict['fmt'], plot_dict['markersize'], plot_dict['alpha'])]
            # These must be a single value
            plot_dict['title'] = '2nd Derivative Zero Crossing Zero and Peaks Found'
            plot_dict['xlabel'] = 'Channel Number'
            plot_dict['legendAutoLabel'] = False
            plot_dict['do_legend'] = True
            plot_dict['legendLoc'] = 0
            plot_dict['legendNumPoints'] = 3
            plot_dict['legendHandleLength'] = 5
            quick_plotter(plot_dict=plot_dict)
        if verbose:
            print("Mariscotti algorithm completed.\n")
        return gaussParametersArray


def peak_finder(spectrum,
               x,
               numberOfIndexesToSmoothOver=1,
               errFactor=1,
               show_plot_peakFinder=False,
               verbose=True):
    # apply the mariscotti peak finding algorithm
    gaussParametersArray = np.array(mariscotti(spectrum, nsmooth=numberOfIndexesToSmoothOver,
                                                  errFactor=errFactor, plot=showPlot_peakFinder, verbose=verbose))

    # apply some simple offset so that this can work with energy units or channel numbers.
    if len(gaussParametersArray) == 0:
        return []
    else:
        energy_offset = float(x[0])
        energySpacing = (float(x[-1]) - float(x[0]))/float(len(x) - 1)
        gaussParametersArray_absouleUnits = gaussParametersArray
        for (valIndex, meanVal) in list(enumerate(gaussParametersArray[:, 1])):
            gaussParametersArray_absouleUnits[valIndex, 1] = x[int(meanVal)]
        gaussParametersArray_absouleUnits[:, 2] = gaussParametersArray[:, 2] * energySpacing

        # Sort the peaks from highest to lowest and put them in a list
        guessParametersSet = sorted(gaussParametersArray_absouleUnits, key=itemgetter(0), reverse=True)
        return guessParametersSet



