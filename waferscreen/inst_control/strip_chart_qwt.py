'''
Created on Mar 13, 2009

@author: schimaf
'''
import lakeshore370
from pylab import *
import sys, os
import time
from numpy import *
from PyQt4 import Qt, QtGui, QtCore
import PyQt4.Qwt5 as Qwt
from PyQt4.Qwt5.anynumpy import *

progname = os.path.basename(sys.argv[0])
progversion = "0.1"

class StripChart(object):
    '''
    classdocs
    '''


    def __init__(self, pad = 4):
        '''
        Constructor
        '''
        
        # Make an instance of the Keithley 2700 Multimeter with primary gpib address (default of 4)
        self.multimeter = lakeshore370.Lakeshore370(pad=13)
        
        self.raw_data = [0.,0.,0.,0.,0.,0.,0.,0.,0.,0.]
        self.x_data = arange(len(self.raw_data))

        app = Qt.QApplication(sys.argv)
        demo = self.make()
        sys.exit(app.exec_())

    def make(self):
        '''
        make
        '''
        demo = DataPlot(self.multimeter)
        demo.resize(500, 300)
        demo.show()
        return demo
        
    def run(self):
        
        
        p, = plot(self.raw_data)
        
        for x in range(10):
            voltage = self.multimeter.GetTemperature()
            self.raw_data.append(voltage)
            print "voltage"
            p.set_ydata(self.raw_data[-10:])
            draw()
            time.sleep(1)

class DataPlot(Qwt.QwtPlot):

   def __init__(self, multimeter, *args):
       Qwt.QwtPlot.__init__(self, *args)

       self.multimeter = multimeter

       self.setCanvasBackground(Qt.Qt.white)
       self.alignScales()

       # Initialize data
       self.x = arange(0.0, 100.1, 0.5)
       self.y = zeros(len(self.x), Float)
       #self.z = zeros(len(self.x), Float)

       self.setTitle("A Moving QwtPlot Demonstration")
       self.insertLegend(Qwt.QwtLegend(), Qwt.QwtPlot.BottomLegend);

       #self.curveR = Qwt.QwtPlotCurve("Data Moving Right")
       #self.curveR.attach(self)
       self.curveL = Qwt.QwtPlotCurve("Data Moving Left")
       self.curveL.attach(self)

       self.curveL.setSymbol(Qwt.QwtSymbol(Qwt.QwtSymbol.Ellipse,
                                       Qt.QBrush(),
                                       Qt.QPen(Qt.Qt.yellow),
                                       Qt.QSize(7, 7)))

       #self.curveR.setPen(Qt.QPen(Qt.Qt.red))
       self.curveL.setPen(Qt.QPen(Qt.Qt.blue))

       mY = Qwt.QwtPlotMarker()
       mY.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
       mY.setLineStyle(Qwt.QwtPlotMarker.HLine)
       mY.setYValue(0.0)
       mY.attach(self)

       self.setAxisTitle(Qwt.QwtPlot.xBottom, "Time (seconds)")
       self.setAxisTitle(Qwt.QwtPlot.yLeft, "Values")

       self.startTimer(50)
       self.phase = 0.0

   # __init__()

   def alignScales(self):
       self.canvas().setFrameStyle(Qt.QFrame.Box | Qt.QFrame.Plain)
       self.canvas().setLineWidth(1)
       for i in range(Qwt.QwtPlot.axisCnt):
           scaleWidget = self.axisWidget(i)
           if scaleWidget:
               scaleWidget.setMargin(0)
           scaleDraw = self.axisScaleDraw(i)
           if scaleDraw:
               scaleDraw.enableComponent(
                   Qwt.QwtAbstractScaleDraw.Backbone, False)

   # alignScales()

   def timerEvent(self, e):
       if self.phase > pi - 0.0001:
           self.phase = 0.0

       # y moves from left to right:
       # shift y array right and assign new value y[0]
       #self.y = concatenate((self.y[:1], self.y[:-1]), 1)
       #self.y[0] = sin(self.phase) * (-1.0 + 2.0*random.random())
       #voltage = self.multimeter.data()
       #print "voltage", voltage
       #self.y[0] = voltage
        
       # z moves from right to left:
       # Shift z array left and assign new value to z[n-1].
       #self.z = concatenate((self.z[1:], self.z[:1]), 1)
       #self.z[-1] = 0.8 - (2.0 * self.phase/pi) + 0.4*random.random()
       voltage = self.multimeter.GetTemperature()
       print "voltage", voltage
       #self.z[-1] = voltage
       self.y[-1] = voltage

       #self.curveR.setData(self.x, self.y)
       self.curveL.setData(self.x, self.y)

       self.replot()
       self.phase += pi*0.02

   # timerEvent()

# class DataPlot
qApp = QtGui.QApplication(sys.argv)
#
aw = StripChart()
#aw.setWindowTitle("%s" % progname)
aw.run()
sys.exit(qApp.exec_())
qApp.exec_()
