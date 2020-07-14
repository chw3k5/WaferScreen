import matplotlib.pyplot as plt
import random


colors = ['BlueViolet', 'Brown', 'CadetBlue', 'Chartreuse', 'Chocolate', 'Coral', 'CornflowerBlue', 'Crimson', 'Cyan',
          'DarkBlue', 'DarkCyan', 'DarkGoldenRod', 'DarkGreen', 'DarkMagenta', 'DarkOliveGreen', 'DarkOrange',
          'DarkOrchid', 'DarkRed', 'DarkSalmon', 'DarkSeaGreen', 'DarkSlateBlue', 'DodgerBlue', 'FireBrick',
          'ForestGreen', 'Fuchsia', 'Gold', 'GoldenRod', 'Green', 'GreenYellow', 'HotPink', 'IndianRed', 'Indigo', 
          'LawnGreen', 'LightCoral', 'Lime', 'LimeGreen', 'Magenta', 'Maroon', 'MediumAquaMarine', 'MediumBlue', 
          'MediumOrchid', 'MediumPurple', 'MediumSeaGreen', 'MediumSlateBlue', 'MediumTurquoise', 'MediumVioletRed', 
          'MidnightBlue', 'Navy', 'Olive', 'OliveDrab', 'Orange', 'OrangeRed', 'Orchid', 'PaleVioletRed', 'Peru', 
          'Pink', 'Plum', 'Purple', 'Red', 'RoyalBlue', 'SaddleBrown', 'Salmon', 'SandyBrown', 'Sienna', 'SkyBlue', 
          'SlateBlue', 'SlateGrey', 'SpringGreen', 'SteelBlue', 'Teal', 'Tomato', 'Turquoise', 'Violet', 'Yellow', 
          'YellowGreen']
len_colors = len(colors)


ls = ['solid', 'dotted', 'dashed', 'dashdot']
len_ls = len(ls)

hatches = ['/', '*', '|', '\\', 'x', 'o', '-', '.', '0', '+']
len_hatches = len(hatches)


default_plot_dict = {}

# These can be a list or a single value
random.shuffle(colors)
random.shuffle(hatches)
default_plot_dict['colors'] = colors

default_plot_dict['fmt'] = 'o'
default_plot_dict['markersize'] = 5
default_plot_dict['alpha'] = 1.0
default_plot_dict['ls'] = '-'
default_plot_dict['marker'] = None
default_plot_dict['line_width'] = 1

default_plot_dict['ErrorMaker'] = '|'
default_plot_dict['ErrorCapSize'] = 4
default_plot_dict['Errorls'] = 'None'
default_plot_dict['Errorliw'] = 1
default_plot_dict['x_error'] = None
default_plot_dict['y_error'] = None
default_plot_dict['legendAutoLabel'] = True
default_plot_dict['legendLabel'] = ''

# These must be a single value
default_plot_dict['title'] = ''
default_plot_dict['xlabel'] = ''
default_plot_dict['ylabel'] = ''

default_plot_dict['xmax'] = None
default_plot_dict['xmin'] = None
default_plot_dict['ymax'] = None
default_plot_dict['ymin'] = None
default_plot_dict['x_fig_size'] = 6
default_plot_dict['y_fig_size'] = 4
default_plot_dict['x_ticks_min_number'] = None
default_plot_dict['y_ticks_min_number'] = None

default_plot_dict['do_legend'] = False
default_plot_dict['legendLoc'] = 0
default_plot_dict['legendNumPoints'] = 3
default_plot_dict['legendHandleLength'] = 5
default_plot_dict['legendFontSize'] = 'small'

default_plot_dict['save'] = False
default_plot_dict['plot_file_name'] = 'plot'
default_plot_dict['do_pdf'] = True
default_plot_dict['show'] = False
default_plot_dict['clearAtTheEnd'] = True

default_plot_dict['xLog'] = False
default_plot_dict['yLog'] = False

default_plot_dict["top_x_funcs"] = None
default_plot_dict["top_x_axis_label"] = None

default_plot_dict["do_text"] = False
default_plot_dict['text_fontsize'] = 10
default_plot_dict['text_rotation'] = 0
default_plot_dict["text_xy"] = []
default_plot_dict["texts"] = []
default_plot_dict["texts_colors"] = []


# this definition uses the default values defined above is there is no user defined value in dataDict
def extract_plot_val(plot_dict, val_string, list_index=0, keys=None):
    # extract the plot value for the list or use a the singleton value
    if keys is None:
        keys = plot_dict.keys()
    if val_string in keys:
        if isinstance(plot_dict[val_string], list):
            val = plot_dict[val_string][list_index]
        else:
            val = plot_dict[val_string]
    else:
        val = default_plot_dict[val_string]
    return val


def get_more_ticks(xmin, xmax, x_ticks_min_number, plt):
    x_diff = xmax - xmin
    default_ticks = plt.xticks()
    first_tick = float(default_ticks[0][0])
    default_tick_step = float(default_ticks[0][1]) - first_tick
    tick_step = default_tick_step
    while x_ticks_min_number > x_diff / tick_step:
        tick_step = tick_step / 2.0
    tick_list = [first_tick]
    while tick_list[0] > xmin:
        tick_list.insert(0, tick_list[0] - tick_step)
    while tick_list[-1] < xmax:
        tick_list.append(tick_list[-1] + tick_step)
    return tick_list


def quick_plotter(plot_dict):
    keys = plot_dict.keys()
    if 'verbose' in keys:
        verbose = plot_dict['verbose']
    else:
        verbose = True
    if verbose:
        print('Starting the quick plotting program...')

    # decide if the user wants to plot a legend
    if 'do_legend' in keys:
        do_legend = plot_dict['do_legend']
    else:
        do_legend = default_plot_dict['do_legend']
    leglabels = []
    leglines = []

    x_fig_size = extract_plot_val(plot_dict, 'x_fig_size', keys=keys)
    y_fig_size = extract_plot_val(plot_dict, 'y_fig_size', keys=keys)
    fig, ax = plt.subplots(constrained_layout=True, figsize=(x_fig_size, y_fig_size))
    # plot the lists of data
    for (listIndex, y_data) in list(enumerate(plot_dict['y_data'])):
        # Extract the x data for this plot, or use the length of the y_data to make x array
        if 'x_data' not in keys:
            if verbose:
                print('no axis found, using the length of the y_data')
            x_data = range(len(y_data))
        else:
            x_data = plot_dict['x_data'][listIndex]

        # extract the plot color for this y_data
        if 'colors' in keys:
            if isinstance(plot_dict['colors'], list):
                color = plot_dict['colors'][listIndex]
            else:
                color = plot_dict['colors']
        else:
            color = default_plot_dict['colors'][listIndex]

        # extract the plot line style
        ls = extract_plot_val(plot_dict, 'ls', listIndex, keys=keys)
        # extract the plot line width
        line_width = extract_plot_val(plot_dict, 'line_width', listIndex, keys=keys)
        # extract the plot marker format
        fmt = extract_plot_val(plot_dict, 'fmt', listIndex, keys=keys)
        # exact the marker size
        markersize = extract_plot_val(plot_dict, 'markersize', listIndex, keys=keys)
        # extract the marker transparency
        alpha = extract_plot_val(plot_dict, 'alpha', listIndex, keys=keys)
        # extract the error marker
        ErrorMaker = extract_plot_val(plot_dict, 'ErrorMaker', listIndex, keys=keys)
        # extract the error marker's cap  size
        ErrorCapSize = extract_plot_val(plot_dict, 'ErrorCapSize', listIndex, keys=keys)
        # extract the error marker line style
        Errorls = extract_plot_val(plot_dict, 'Errorls', listIndex, keys=keys)
        # extract the erro marker line width
        Errorliw = extract_plot_val(plot_dict, 'Errorliw', listIndex, keys=keys)

        if do_legend:
            if extract_plot_val(plot_dict, 'legendAutoLabel', keys=keys):
                # create the legend line and label
                leglines.append(plt.Line2D(range(10), range(10),
                                           color=color, ls=ls,
                                           linewidth=line_width, marker=fmt,
                                           markersize=markersize, markerfacecolor=color,
                                           alpha=alpha))
                leglabels.append(extract_plot_val(plot_dict, 'legendLabel', listIndex, keys=keys))

        # this is where the data is plotted
        if verbose:
            print('plotting data in index', listIndex)

        # plot the y_data in Linear-Linear for this loop
        ax.plot(x_data, y_data, linestyle=ls, color=color,
                linewidth=line_width, marker=fmt, markersize=markersize,
                markerfacecolor=color, alpha=alpha)
        # are there errorbars on this plot?
        if 'x_error' in keys or 'y_error' in keys:
            # extract the x error (default is "None")
            try:
                x_error = extract_plot_val(plot_dict, 'x_error', listIndex, keys=keys)
                # extract the y error (default is "None")
                y_error = extract_plot_val(plot_dict, 'y_error', listIndex, keys=keys)
                if x_error is not None or y_error is not None:
                    ax.errorbar(x_data, y_data, xerr=x_error, yerr=y_error,
                                marker=ErrorMaker, color=color, capsize=ErrorCapSize,
                                linestyle=Errorls, elinewidth=Errorliw)
            except IndexError:
                pass

        # options for displaying Log plots
        if extract_plot_val(plot_dict, 'xLog', keys=keys):
            ax.xscale('log')
        if extract_plot_val(plot_dict, 'yLog', keys=keys):
            ax.yscale('log')

    # now we will add the title and x and y axis labels
    ax.set_title(extract_plot_val(plot_dict, 'title', keys=keys))
    ax.set_xlabel(extract_plot_val(plot_dict, 'xlabel', keys=keys))
    ax.set_ylabel(extract_plot_val(plot_dict, 'ylabel', keys=keys))

    # now we will make the legend (do_legend is True)
    if do_legend:
        # extract the legend info
        if verbose:
            print('rendering a legend for this plot')
        legendLoc = extract_plot_val(plot_dict, 'legendLoc', keys=keys)
        legendNumPoints = extract_plot_val(plot_dict, 'legendNumPoints', keys=keys)
        legendHandleLength = extract_plot_val(plot_dict, 'legendHandleLength', keys=keys)
        legendFontSize = extract_plot_val(plot_dict, 'legendFontSize', keys=keys)
        if not extract_plot_val(plot_dict, 'legendAutoLabel', keys=keys):
            leglines = plot_dict["legend_lines"]
            leglabels = plot_dict["legendLabel"]
        # call the legend command
        plt.legend(leglines, leglabels, loc=legendLoc,
                   numpoints=legendNumPoints, handlelength=legendHandleLength,
                   fontsize=legendFontSize)

    # now we adjust the x and y limits of the plot
    current_xmin, current_xmax = plt.xlim()
    current_ymin, current_ymax = plt.ylim()
    if extract_plot_val(plot_dict, 'xmin', keys=keys) is None:
        xmin = current_xmin
    else:
        xmin = plot_dict["xmin"]
    if extract_plot_val(plot_dict, 'xmax', keys=keys) is None:
        xmax = current_xmax
    else:
        xmax = plot_dict["xmax"]
    if extract_plot_val(plot_dict, 'ymax', keys=keys) is None:
        ymin = current_ymin
    else:
        ymin = plot_dict["ymin"]
    if extract_plot_val(plot_dict, 'ymax', keys=keys) is None:
        ymax = current_ymax
    else:
        ymax = plot_dict["ymax"]
    # set the values
    plt.xlim((xmin, xmax))
    plt.ylim((ymin, ymax))

    # tick marks
    x_ticks_min_number = extract_plot_val(plot_dict, 'x_ticks_min_number', keys=keys)
    if x_ticks_min_number is not None:
        tick_list = get_more_ticks(xmin, xmax, x_ticks_min_number, plt)
        plt.xticks(ticks=tick_list[1:-1])
    y_ticks_min_number = extract_plot_val(plot_dict, 'y_ticks_min_number', keys=keys)
    if y_ticks_min_number is not None:
        tick_list = get_more_ticks(ymin, ymax, y_ticks_min_number, plt)
        plt.yticks(ticks=tick_list[1:-1])

    # add a second x-axis on the top of the graph.
    top_x_funcs = extract_plot_val(plot_dict, 'top_x_funcs', keys=keys)
    if top_x_funcs is not None:
        secax = ax.secondary_xaxis('top', functions=top_x_funcs)
        top_x_axis_label = extract_plot_val(plot_dict, 'top_x_axis_label', keys=keys)
        if top_x_axis_label is not None:
            secax.set_xlabel(top_x_axis_label)

    # text added to the plot
    if extract_plot_val(plot_dict, 'do_text', keys=keys):
        for xy, text_color, text, in zip(plot_dict["text_xy"], plot_dict["texts_colors"], plot_dict["texts"]):
            text_fontsize = extract_plot_val(plot_dict, 'text_fontsize', keys=keys)
            text_rotation = extract_plot_val(plot_dict, 'text_rotation', keys=keys)
            x, y = xy
            plt.text(x, y, text, fontsize=text_fontsize, color=text_color, rotation=text_rotation)

    # here the plot can be saved
    if extract_plot_val(plot_dict, 'save', keys=keys):
        full_plot_file_name = extract_plot_val(plot_dict, 'plot_file_name', keys=keys)
        if extract_plot_val(plot_dict, 'do_pdf', keys=keys):
            full_plot_file_name += '.pdf'
        else:
            full_plot_file_name += '.png'
        if verbose:
            print('saving the plot:', full_plot_file_name)
        plt.savefig(full_plot_file_name)

    # here the plot can be shown
    if extract_plot_val(plot_dict, 'show', keys=keys):
        if verbose:
            print('showing the plot in a pop up window')
        plt.show()

    if extract_plot_val(plot_dict, 'clearAtTheEnd', keys=keys):
        plt.clf()
        plt.close('all')
        print("Closing all plots.")
    if verbose:
        print('...the quick plotting program has finished.')
    return plt


def rescale(desired, current, target=None):
    if target is None:
        target = current
    maxDesired = max(desired)
    minDesired = min(desired)
    maxCurrent = max(current)
    minCurrent = min(current)

    rangeDesired = float(maxDesired - minDesired)
    rangeCurrent = float(maxCurrent - minCurrent)

    if rangeCurrent == float(0.0):
        # This is the case where current is an array of all the same number.
        # Here we take the middle value of the desired scale and make an array
        # that is only made up of the middle value.
        middleDesired = (rangeDesired / 2.0) + minDesired
        rescaledTarget1 = (target * float(0.0)) + middleDesired
        return rescaledTarget1
    else:
        # 1) set the minimum value of the current to zero
        rescaledTarget1 = target - minCurrent

        # 2) set the maximum value of the rescaledCurrent1 to 1.0
        # (max of rescaledCurrent2 is 1.0, min is 0.0)
        rescaledTarget2 = rescaledTarget1 / rangeCurrent

        # 3 make the range of rescaledCurrent2 the same as the range of the desired
        # (max of rescaledCurrent3 is rangeDesired, min is zero)
        rescaledTarget3 = rescaledTarget2 * rangeDesired

        # 4 make the min of rescaledCurrent3 equal to the min of desired
        # (max of rescaledCurrent3 is rangeDesired + minDesired = maxDesired, min is minDesired)
        rescaledTarget4 = rescaledTarget3 + minDesired

        return rescaledTarget4
