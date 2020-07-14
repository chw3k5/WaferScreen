import cmath
import math
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import mpl_toolkits.axisartist.angle_helper as angle_helper
from matplotlib.projections import PolarAxes
from matplotlib.transforms import Affine2D
from mpl_toolkits.axisartist import SubplotHost
from mpl_toolkits.axisartist import GridHelperCurveLinear
import mpl_toolkits.axisartist.floating_axes as floating_axes
from mpl_toolkits.axisartist.grid_finder import (FixedLocator, MaxNLocator,
                                                 DictFormatter)

#code to return a figure with a blank smith chart given a figure and rect coordinates

def get_smith(fig, rect = 111, plot_impedance = True, plot_ticks = False, plot_admittance = False, plot_labels = False):
    '''Function which returns an axis with a blank smith chart, provide a figure and optional rect coords'''
    
	#Example use:
	
	# fig3 = plt.figure(3)
    # ax31 = pySmith.get_smith(fig3, 221)
    # ax31.plot(np.real(filtsmatrix[0,:,0,0]),np.imag(filtsmatrix[0,:,0,0]))
    # ax32= pySmith.get_smith(fig3, 222)
    # ax32.plot(np.real(filtsmatrix[0,:,0,1]),np.imag(filtsmatrix[0,:,0,1]))
    # ax33 = pySmith.get_smith(fig3, 223)
    # ax33.plot(np.real(filtsmatrix[0,:,1,0]),np.imag(filtsmatrix[0,:,1,0]))
    # ax34 = pySmith.get_smith(fig3, 224)
    # ax34.plot(np.real(filtsmatrix[0,:,1,1]),np.imag(filtsmatrix[0,:,1,1]))
	
    #font definition
    font = {'family': 'sans-serif',
        'color':  'black',
        'weight': 'normal',
        'size': 18,
        }

    #plot radial tick marks
    tr = PolarAxes.PolarTransform()
    num_thetas = 8#*3 #12 gives in 30 deg intervals, 8 in 45 deg, 24 in 15deg
    thetas = np.linspace(0.0, math.pi*(1-2.0/num_thetas),int(round(num_thetas/2)))
    angle_ticks = []#(0, r"$0$"),
    for theta in thetas:
        angle_info = []
        angle_info.append(theta)
        deg = int(round(180.0*theta/math.pi))
        angle_info.append(r'%d$^{\circ}$'%deg)
        angle_ticks.append(angle_info)
    grid_locator1 = FixedLocator([v for v, s in angle_ticks])
    tick_formatter1 = DictFormatter(dict(angle_ticks))
    thetas2 = np.linspace(math.pi, 2*math.pi*(1-1.0/num_thetas), int(round(num_thetas/2)))
    angle_ticks2 = []#(0, r"$0$"),
    for theta in thetas2:
        angle_info = []
        angle_info.append(theta)
        deg = int(round(180.0*theta/math.pi))
        angle_info.append(r'%d$^{\circ}$'%deg)
        angle_ticks2.append(angle_info)
    grid_locator2 = FixedLocator([v for v, s in angle_ticks2])
    tick_formatter2 = DictFormatter(dict(angle_ticks2))

    grid_helper1 = floating_axes.GridHelperCurveLinear(tr,
                                        extremes=(math.pi, 0, 1, 0),
                                        grid_locator1=grid_locator1,
                                        #grid_locator2=grid_locator2,
                                        tick_formatter1=tick_formatter1#,
                                        #tick_formatter2=None,
                                        )
                                        
    grid_helper2 = floating_axes.GridHelperCurveLinear(tr,
                                    extremes=(2*math.pi, math.pi, 1, 0),
                                    grid_locator1=grid_locator2,
                                    #grid_locator2=grid_locator2,
                                    tick_formatter1=tick_formatter2#,
                                    #tick_formatter2=None,
                                    )

    r1 = int(math.floor(rect/100))
    r2 = int(math.floor( (rect-100*r1)/10 ))
    r3 = int(math.floor( (rect - 100*r1 - 10*r2) ))
    ax = SubplotHost(fig, r1, r2, r3, grid_helper=grid_helper1)
    ax2 = SubplotHost(fig, r1, r2, r3, grid_helper=grid_helper2)
    #ax.set_aspect(math.pi/180.0,'datalim')
    fig.add_subplot(ax)
    fig.add_subplot(ax2)

    ax.axis["bottom"].major_ticklabels.set_axis_direction("top")
    ax.axis["bottom"].major_ticklabels.set_fontsize(13)
    ax.axis["left"].set_visible(False)
    ax.axis["left"].toggle(all=False)
    ax.axis["right"].set_visible(False)
    ax.axis["right"].toggle(all=False)
    ax.axis["top"].set_visible(False)
    ax.axis["top"].toggle(all=False)
    ax.patch.set_visible(False)
    
    ax2.axis["bottom"].major_ticklabels.set_fontsize(13)
    ax2.axis["left"].set_visible(False)
    ax2.axis["left"].toggle(all=False)
    ax2.axis["right"].set_visible(False)
    ax2.axis["right"].toggle(all=False)
    ax2.axis["top"].set_visible(False)
    ax2.axis["top"].toggle(all=False)
    
    #ax = fig.add_subplot(rect)

    #remove axis labels
    ax.axis('off')
    #set aspect ratio to 1
    ax.set_aspect(1)#, 'datalim')
    #set limits
    ax.set_xlim([-1.02,1.02])
    ax.set_ylim([-1.02,1.02])
    #remove axis labels
    ax2.axis('off')
    #set aspect ratio to 1
    ax2.set_aspect(1)#,'datalim')
    #set limits
    ax2.set_xlim([-1.02,1.02])
    ax2.set_ylim([-1.02,1.02])
    ax2.patch.set_visible(False)
    if plot_impedance:
        #make lines of constant resistance
        res_log = np.linspace(-4,4,9)
        react_log = np.linspace(-5,5,2001)
        res = 2**res_log
        react = 10**react_log
        react2 = np.append(-1.0*react[::-1],np.array([0]))
        react = np.append(react2,react)
        for r in res:
            z = 1j*react + r
            gam = (z-1)/(z+1)
            x = np.real(gam)
            y = np.imag(gam)
            if abs(r-1) > 1e-6:
                ax.plot(x,y,c='k',linewidth = 0.75,alpha=0.5)
            else:
                ax.plot(x,y,c='k',linewidth = 1.0,alpha=0.85)
        #make lines of constant reactance
        react_log = np.linspace(-3,3,7)
        res_log = np.linspace(-5,5,2001)
        res = 10**res_log
        react = 2**react_log
        react2 = np.append(-1.0*react[::-1],np.array([0]))
        react = np.append(react2,react)
        for chi in react:
            z = 1j*chi + res
            gam = (z-1)/(z+1)
            x = np.real(gam)
            y = np.imag(gam)
            if abs(chi-1) > 1e-6 and abs(chi+1) > 1e-6 and abs(chi) > 1e-6:
                ax.plot(x,y,c='k',linewidth = 0.75,alpha=0.5)
            else:
                ax.plot(x,y,c='k',linewidth = 1.0,alpha=0.85)
    if plot_admittance:
        #make lines of constant conductance
        res_log = np.linspace(-4,4,9)
        react_log = np.linspace(-5,5,2001)
        res = 2**res_log
        react = 10**react_log
        react = np.append(-1.0*react[::-1],react)
        for r in res:
            y = 1.0/r + 1.0/(1j*react)
            gam = (1.0/y-1)/(1.0/y+1)
            x = np.real(gam)
            y = np.imag(gam)
            if abs(r-1) > 1e-6:
                ax.plot(x,y,c='k',linewidth = 0.75,alpha=0.5)
            else:
                ax.plot(x,y,c='k',linewidth = 1.0,alpha=0.85)
        #make lines of constant susceptance
        react_log = np.linspace(-3,3,7)
        res_log = np.linspace(-5,5,2001)
        res = 10**res_log
        react = 2**react_log
        react = np.append(-1.0*react[::-1],react)
        for chi in react:
            y = 1.0/(1j*chi) + 1.0/res
            gam = (1.0/y-1)/(1.0/y+1)
            x = np.real(gam)
            y = np.imag(gam)
            if abs(chi-1) > 1e-6 and abs(chi+1) > 1e-6:
                ax.plot(x,y,c='k',linewidth = 0.75,alpha=0.5)
            else:
                ax.plot(x,y,c='k',linewidth = 1.0,alpha=0.85)
        y = 1.0/res
        gam = (1.0/y-1)/(1.0/y+1)
        x = np.real(gam)
        y = np.imag(gam)
        ax.plot(x,y,c='k',linewidth = 1.0,alpha=0.75)
    if plot_labels:
        #naive text placement only works for default python figure size with 1 subplot
        ax.text(-0.15,1.04,r'$\Gamma$ = 1j',fontdict = font)
        ax.text(-1.4,-0.035,r'$\Gamma$ = -1',fontdict = font)
        ax.text(-0.17,-1.11,r'$\Gamma$ = -1j',fontdict = font)
        ax.text(1.04,-0.035,r'$\Gamma$ = 1',fontdict = font)
    if plot_ticks:
        num_minorticks = 3
        num_thetas = num_thetas*(num_minorticks+1)
        thetas = np.linspace(0, 2.0*math.pi*(1.0-1.0/num_thetas),num_thetas)
        r_inner = 0.985
        r_outer = 1.0
        rads = np.linspace(r_inner,r_outer,2)
        ticknum = 0
        for theta in thetas:
            x = rads*np.cos(theta)
            y = rads*np.sin(theta)
            if ticknum%(num_minorticks+1) != 0:
                ax.plot(x,y,c='k',linewidth=1.0,alpha=1.0)
            ticknum = ticknum + 1


    return ax  