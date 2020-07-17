#!/usr/bin/env python

# A template for a real time data plotter
# Based on BodeDemo.py and Stripchart
# By Douglas Bennett


import sys
from PyQt4.Qt import *
from PyQt4.Qwt5 import *
#import PyQt4.Qwt5.anynumpy as np
import numpy as np
from PyQt4 import QtGui, QtCore
import lakeshore370
from time import time
from numpy.fft import rfft


import sip; sip.settracemask(0xff)

zoom_xpm = ['32 32 8 1',
            '# c #000000',
            'b c #c0c0c0',
            'a c #ffffff',
            'e c #585858',
            'd c #a0a0a4',
            'c c #0000ff',
            'f c #00ffff',
            '. c None',
            '..######################........',
            '.#a#baaaaaaaaaaaaaaaaaa#........',
            '#aa#baaaaaaaaaaaaaccaca#........',
            '####baaaaaaaaaaaaaaaaca####.....',
            '#bbbbaaaaaaaaaaaacccaaa#da#.....',
            '#aaaaaaaaaaaaaaaacccaca#da#.....',
            '#aaaaaaaaaaaaaaaaaccaca#da#.....',
            '#aaaaaaaaaabe###ebaaaaa#da#.....',
            '#aaaaaaaaa#########aaaa#da#.....',
            '#aaaaaaaa###dbbbb###aaa#da#.....',
            '#aaaaaaa###aaaaffb###aa#da#.....',
            '#aaaaaab##aaccaaafb##ba#da#.....',
            '#aaaaaae#daaccaccaad#ea#da#.....',
            '#aaaaaa##aaaaaaccaab##a#da#.....',
            '#aaaaaa##aacccaaaaab##a#da#.....',
            '#aaaaaa##aaccccaccab##a#da#.....',
            '#aaaaaae#daccccaccad#ea#da#.....',
            '#aaaaaab##aacccaaaa##da#da#.....',
            '#aaccacd###aaaaaaa###da#da#.....',
            '#aaaaacad###daaad#####a#da#.....',
            '#acccaaaad##########da##da#.....',
            '#acccacaaadde###edd#eda#da#.....',
            '#aaccacaaaabdddddbdd#eda#a#.....',
            '#aaaaaaaaaaaaaaaaaadd#eda##.....',
            '#aaaaaaaaaaaaaaaaaaadd#eda#.....',
            '#aaaaaaaccacaaaaaaaaadd#eda#....',
            '#aaaaaaaaaacaaaaaaaaaad##eda#...',
            '#aaaaaacccaaaaaaaaaaaaa#d#eda#..',
            '########################dd#eda#.',
            '...#dddddddddddddddddddddd##eda#',
            '...#aaaaaaaaaaaaaaaaaaaaaa#.####',
            '...########################..##.']



class PrintFilter(QwtPlotPrintFilter):
    def __init__(self):
        QwtPlotPrintFilter.__init__(self)

    # __init___()
    
    def color(self, c, item):
        if not (self.options() & QwtPlotPrintFilter.CanvasBackground):
            if item == QwtPlotPrintFilter.MajorGrid:
                return Qt.darkGray
            elif item == QwtPlotPrintFilter.MinorGrid:
                return Qt.gray
        if item == QwtPlotPrintFilter.Title:
            return Qt.red
        elif item == QwtPlotPrintFilter.AxisScale:
            return Qt.green
        elif item == QwtPlotPrintFilter.AxisTitle:
            return Qt.blue
        return c

    # color()

    def font(self, f, _):
        result = QFont(f)
        result.setPointSize(int(f.pointSize()*1.25))
        return result

    # font()

# class PrintFilter


class DataPlot(QwtPlot):

    def __init__(self, *args):
        QwtPlot.__init__(self, *args)

        self.setTitle('Temp Logger')
        #self.setCanvasBackground(Qt.darkBlue)
        self.setCanvasBackground(Qt.white)

        # legend
        legend = QwtLegend()
        legend.setFrameStyle(QFrame.Box | QFrame.Sunken)
        legend.setItemMode(QwtLegend.ClickableItem)
        self.insertLegend(legend, QwtPlot.BottomLegend)

        # grid
        self.grid = QwtPlotGrid()
        self.grid.enableXMin(True)
        self.grid.setMajPen(QPen(Qt.black, 0, Qt.DotLine))
        self.grid.setMinPen(QPen(Qt.gray, 0 , Qt.DotLine))
        self.grid.attach(self)

        # axes
        self.setAxisTitle(QwtPlot.xBottom, 'Time (s)')
        self.setAxisTitle(QwtPlot.yLeft, 'Temperature (mK)')

        self.setAxisMaxMajor(QwtPlot.xBottom, 6)
        #self.setAxisMaxMinor(QwtPlot.xBottom, 10)
        #self.setAxisScaleEngine(QwtPlot.xBottom, QwtLinearScaleEngine())

        # curve
        self.curve1 = QwtPlotCurve('ADR Temperature')
        #self.curve1.setRenderHint(QwtPlotItem.RenderAntialiased);
        self.curve1.setPen(QPen(Qt.blue))
        self.curve1.setYAxis(QwtPlot.yLeft)
        self.curve1.attach(self)

        # alias
#        fn = self.fontInfo().family()

        #self.setDamp(0.01)

    # __init__()


# class DataPlot


class MainWindow(QMainWindow):

    def __init__(self, *args):
        QMainWindow.__init__(self, *args)

        self.lakeshore = lakeshore370.Lakeshore370(pad=13)
        self.time0 = time()
        self.timerstep = 500

        self.plot = DataPlot(self)
        self.plot.setMargin(5)

        self.setContextMenuPolicy(Qt.NoContextMenu)
        
        self.zoomer = QwtPlotZoomer(
            QwtPlot.xBottom,
            QwtPlot.yLeft,
            QwtPicker.DragSelection,
            QwtPicker.AlwaysOff,
            self.plot.canvas())
        self.zoomer.setRubberBandPen(QPen(Qt.green))



        self.picker = QwtPlotPicker(
            QwtPlot.xBottom,
            QwtPlot.yLeft,
            QwtPicker.PointSelection | QwtPicker.DragSelection,
            QwtPlotPicker.CrossRubberBand,
            QwtPicker.AlwaysOn,
            self.plot.canvas())
        self.picker.setRubberBandPen(QPen(Qt.green))
        self.picker.setTrackerPen(QPen(Qt.red))

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget) 

        #self.setCentralWidget(self.plot)
        # Create the vertical layout widget
        self.layout_widget = QWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create the plot layout widget
        self.plot_layout_widget = QGroupBox("Plot", self.layout_widget)
        self.plot_layout = QHBoxLayout(self.plot_layout_widget)
        self.plot_layout_widget.setLayout(self.plot_layout)

        # Put the plot in the plot layout widget
        self.plot_layout.addWidget(self.plot)

        # Put plot layout widget in overall layout widget
        self.layout.addWidget(self.plot_layout_widget)

        #Buttons
        #Create the layout widget for the buttons
        self.buttons_layout_widget = QGroupBox("Buttons", self.layout_widget)
        self.buttons_layout = QHBoxLayout(self.buttons_layout_widget)
        self.buttons_layout_widget.setLayout(self.buttons_layout)

        #Create the buttons
        self.start_button       = QPushButton('Start')
        self.stop_button        = QPushButton('Stop')
        self.save_button        = QPushButton('Save Data')
        self.resetDataButton    = QPushButton('Reset Data')


        #Connect buttons to button events
        self.connect(self.start_button, SIGNAL("clicked()"), self.start_event)
        self.connect(self.stop_button, SIGNAL("clicked()"), self.stop_event)
        self.connect(self.save_button, SIGNAL("clicked()"), self.save_event)
        self.connect(self.resetDataButton, SIGNAL("clicked()"), self.resetData)
        
        #Add buttons to button layout
        self.buttons_layout.addWidget(self.start_button)
        self.buttons_layout.addWidget(self.stop_button)
        self.buttons_layout.addWidget(self.save_button)
        self.buttons_layout.addWidget(self.resetDataButton)

        # Add button layout to overall layout
        self.layout.addWidget(self.buttons_layout_widget)


        # Add GUI Actions
        # Exit Action
        exitAction = QtGui.QAction(QtGui.QIcon('icons/exitAction.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        self.connect(exitAction, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))
        # Print Action
        printdata = QtGui.QAction(QtGui.QIcon('icons/exitAction.png'), 'Print', self)
        printdata.setShortcut('Ctrl+P')
        printdata.setStatusTip('Print data')
        self.connect(printdata, QtCore.SIGNAL('triggered()'), self.print_)
        # Export PDF Action
        exportpdfaction = QtGui.QAction(QtGui.QIcon('icons/exitAction.png'), 'Export PDF', self)
        exportpdfaction.setStatusTip('Export Plot as PDF')
        self.connect(exportpdfaction, QtCore.SIGNAL('triggered()'), self.exportPDF)

        # Add menubar
        menubar = self.menuBar()
        fileMenuItem = menubar.addMenu('&File')  #Add File Item
        fileMenuItem.addAction(printdata)
        fileMenuItem.addAction(exportpdfaction)
        fileMenuItem.addSeparator()
        fileMenuItem.addAction(exitAction)  #Add Exit


        # Toolbar
        # Create toolbar
        toolBar = QToolBar(self)
        # Add toolbar to main window
        self.addToolBar(toolBar)

        # Create button to toggle zoom on and off        
        self.btnZoom = QToolButton(toolBar)
        self.btnZoom.setText("Zoom")
        self.btnZoom.setIcon(QIcon(QPixmap(zoom_xpm)))
        self.btnZoom.setCheckable(True)
        self.btnZoom.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnZoom)


        # Create e to autoscale
        btnautoscale = QToolButton(toolBar)
        btnautoscale.setText("Autoscale")
        btnautoscale.setIcon(QIcon(QPixmap(zoom_xpm)))
        btnautoscale.setCheckable(True)
        btnautoscale.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(btnautoscale)
        self.connect(btnautoscale, SIGNAL('toggled(bool)'), self.autoscale)
        btnautoscale.toggle()
        self.autoScaleOn = True
        #self.autoscale(True)
        
        # create a button to turn on and off fft
        self.fftButton = QToolButton(toolBar)
        self.fftButton.setText('FFT')
        self.fftButton.setCheckable(True)
        self.fftButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.fftButton)
        self.connect(self.fftButton, SIGNAL('toggled(bool)'), self.fftButtonClicked)
        self.doFFT = False
        
        # create a button to turn on and off detrend
        self.detrendButton = QToolButton(toolBar)
        self.detrendButton.setText('Detrend')
        self.detrendButton.setCheckable(True)
        self.detrendButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.detrendButton)
        self.connect(self.detrendButton, SIGNAL('toggled(bool)'), self.detrendButtonClicked)
        self.doDetrend = False
        
        # create a button to turn on and off heater data
        self.heaterButton = QToolButton(toolBar)
        self.heaterButton.setText('Heater')
        self.heaterButton.setCheckable(True)
        self.heaterButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.heaterButton)
        self.connect(self.heaterButton, SIGNAL('toggled(bool)'), self.heaterButtonClicked)
        self.showHeaterData = False

  
        toolBar.addSeparator()

        #Create  box for the timer button
        timerBox = QWidget(toolBar)
        #Create a loyout widget for the box
        timerBoxLayout = QHBoxLayout(timerBox)
        timerBoxLayout.setSpacing(0)
        timerBoxLayout.addWidget(QWidget(timerBox), 10) # spacer
        timerBoxLayout.addWidget(QLabel("Time Between Temp Samples (ms)", timerBox), 0)
        timerBoxLayout.addSpacing(10)

        # Counter for Timing
        self.cntTimer = QwtCounter(timerBox)
        self.cntTimer.setRange(1, 100000, 1)
        self.cntTimer.setValue(self.timerstep)
        timerBoxLayout.addWidget(self.cntTimer, 10)

        # Add the box to timerBox to the toolbar
        toolBar.addWidget(timerBox)

        self.statusBar()
        
        self.zoom(False)
        self.showInfo()
        
        self.connect(self.cntTimer,
                     SIGNAL('valueChanged(double)'),
                     self.setTimer)
        self.connect(self.btnZoom,
                     SIGNAL('toggled(bool)'),
                     self.zoom)
        self.connect(self.picker,
                     SIGNAL('moved(const QPoint &)'),
                     self.moved)
        #self.connect(self.picker,
                     #SIGNAL('selected(const QaPolygon &)'),
                     #self.selected)

#        self.counter = 0.0
#        self.phase = 0.0

        # __init__()


    def setTimer(self, timerstep):
        self.timerstep = timerstep


    # setTimer()
    
    def resetData(self):
        self.timeData = np.zeros(0, float)
        self.temperatureData = np.zeros(0, float)
        self.heaterOutData = np.zeros(0,float)
        self.time0 = time()

    def timerEvent(self, e):
        
        currentTemperature = self.lakeshore.getTemperature(1)*1e3
        currentHeaterOut = self.lakeshore.getHeaterOut()
        currentTime = time()-self.time0
        
        self.timeData = np.append(self.timeData,currentTime)
        self.temperatureData = np.append(self.temperatureData,currentTemperature)
        self.heaterOutData = np.append(self.heaterOutData, currentHeaterOut )
        
        
        slopeTemp = polySlope(self.timeData, self.temperatureData) #K/s
        slopeHeater = polySlope(self.timeData, self.heaterOutData)	
        print('Temp Slope = %f mK/hour, Heater Slope = %f %%/hour'%(slopeTemp*3600, slopeHeater*3600))
        
        if self.doDetrend is True:
            self.plot.setTitle('Detrended Temp Std Dev = %f mK'%np.std(polyDetrend(self.temperatureData, n=1)))
        else:
            self.plot.setTitle('Temp Std Deviation = %f mK'%np.std(self.temperatureData))
        
        if self.showHeaterData is False:
            if self.doFFT is True and self.doDetrend is False:
                # put detrended autocorrelation data on plot
                freqBins = np.fft.fftfreq(len(self.timeData), np.mean(np.diff(self.timeData)))
                fftPower = (np.abs(np.fft.rfft(self.temperatureData-np.mean(self.temperatureData)))**2)
                
                if len(self.timeData) %2 == 1 and len(self.timeData)>1:
                    self.plot.curve1.setData(freqBins[1:],fftPower[1:])
                self.plot.setAxisScaleEngine(QwtPlot.xBottom, QwtLog10ScaleEngine())
                self.plot.setAxisTitle(QwtPlot.xBottom, 'Frequency (Hz) (Dont change timestep size!)')
                self.plot.setAxisTitle(QwtPlot.yLeft, 'FFT^2 (K^2/Hz ??)')
            elif self.doDetrend is True and self.doFFT is False:
                self.plot.curve1.setData(self.timeData,polyDetrend(self.temperatureData, n=1))
                self.plot.setAxisScaleEngine(QwtPlot.xBottom, QwtLinearScaleEngine())
                self.plot.setAxisTitle(QwtPlot.xBottom, 'Time (s)')
                self.plot.setAxisTitle(QwtPlot.yLeft, 'Detrended Temperature (mK)')
            elif self.doDetrend is True and self.doFFT is True:
                # put detrended autocorrelation data on plot
                freqBins = np.fft.fftfreq(len(self.timeData), np.mean(np.diff(self.timeData)))
                fftPower = (np.abs(np.fft.rfft(polyDetrend(self.temperatureData, n=2)))**2)
                
                if len(self.timeData) %2 == 1 and len(self.timeData)>1:
                    self.plot.curve1.setData(freqBins[1:],fftPower[1:])
                self.plot.setAxisScaleEngine(QwtPlot.xBottom, QwtLog10ScaleEngine())
                self.plot.setAxisTitle(QwtPlot.xBottom, 'Frequency (Hz) (Dont change timestep size!)')
                self.plot.setAxisTitle(QwtPlot.yLeft, 'FFT^2 of Detrended Temp (K^2/Hz ??)')
            else:
                # put time and temperature data on plot
                self.plot.curve1.setData(self.timeData, self.temperatureData)
                self.plot.setAxisScaleEngine(QwtPlot.xBottom, QwtLinearScaleEngine())
                self.plot.setAxisTitle(QwtPlot.xBottom, 'Time (s)')
                self.plot.setAxisTitle(QwtPlot.yLeft, 'Temperature (mK)')
        else: 
                self.plot.curve1.setData(self.timeData, self.heaterOutData)
                self.plot.setAxisScaleEngine(QwtPlot.xBottom, QwtLinearScaleEngine())
                self.plot.setAxisTitle(QwtPlot.xBottom, 'Time (s)')
                self.plot.setAxisTitle(QwtPlot.yLeft, 'Heater Out (%%)')
            
        
        
        if self.autoScaleOn == True:
            self.clearZoomStack()
        
        self.plot.replot()

    # timerEvent()

    def clearZoomStack(self):
        """Auto scale and clear the zoom stack
        """

        self.plot.setAxisAutoScale(Qwt.QwtPlot.xBottom)
        self.plot.setAxisAutoScale(Qwt.QwtPlot.yLeft)
        self.plot.replot()
        self.zoomer.setZoomBase()

    # clearZoomStack()

    def start_event(self):
        #self.the_event_timer = self.plot.startTimer(50)
        self.resetData()
        self.the_event_timer = self.startTimer(self.timerstep)

    def stop_event(self):
        self.plot.killTimer(self.the_event_timer)

    def save_event(self):
        dataout = np.vstack((self.timeData,self.temperatureData))
        dataout = dataout.transpose()
        saveLocation = "/home/pcuser/data/ADRLogs/PostMag.txt"
        write_array(saveLocation, dataout)
        print('saved data to %s'%saveLocation)


    def print_(self):
        printer = QPrinter(QPrinter.HighResolution)

        printer.setOutputFileName('ADRTemp-%s.ps' % qVersion())

        printer.setCreator('DataPloter')
        printer.setOrientation(QPrinter.Landscape)
        printer.setColorMode(QPrinter.Color)

        docName = self.plot.title().text()
        if not docName.isEmpty():
            docName.replace(QRegExp(QString.fromLatin1('\n')), self.tr(' -- '))
            printer.setDocName(docName)

        dialog = QPrintDialog(printer)
        if dialog.exec_():
            printFilter = PrintFilter()
            if (QPrinter.GrayScale == printer.colorMode()):
                printFilter.setOptions(
                    QwtPlotPrintFilter.PrintAll
                    & ~QwtPlotPrintFilter.PrintBackground
                    | QwtPlotPrintFilter.PrintFrameWithScales)
            self.plot.print_(printer, printFilter)

    # print_()
    
    def exportPDF(self):
        if QT_VERSION > 0x040100:
            fileName = QFileDialog.getSaveFileName(
                self,
                'Export File Name',
                'ADRTemp-%s.pdf' % qVersion(),
                'PDF Documents (*.pdf)')

        if not fileName.isEmpty():
            printer = QPrinter()
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOrientation(QPrinter.Landscape)
            printer.setOutputFileName(fileName)

            printer.setCreator('DataPloter')
            self.plot.print_(printer)

    # exportPDF()


    def zoom(self, on):
        self.zoomer.setEnabled(on)
        self.zoomer.zoom(0)
        

        if on:
            self.picker.setRubberBand(Qwt.QwtPicker.NoRubberBand)
        else:
            self.picker.setRubberBand(Qwt.QwtPicker.CrossRubberBand)

        self.showInfo()

    # zoom()

    def autoscale(self, on):
        
        if on:
            self.autoScaleOn = True
            self.clearZoomStack()
        else:
            self.autoScaleOn = False
            self.zoom(True)
        #self.btnZoom.setOn(QToolButton.on)
        #self.btnZoom.toggle()

    # autoscale()
    
    def fftButtonClicked(self, on):
        self.doFFT = on
        
            
    def detrendButtonClicked(self, on):
        self.doDetrend = on
        
    def heaterButtonClicked(self, on):
        self.showHeaterData = on
 


    def showInfo(self, text=None):
        if not text:
            if self.picker.rubberBand():
                text = 'Cursor Pos: Press left mouse button in plot region'
            else:
                text = 'Zoom: Press mouse button and drag'
                
        self.statusBar().showMessage(text)
                
    # showInfo()
    
    def moved(self, point):
        info = "Time=%g, Temp=%g" % (
            self.plot.invTransform(Qwt.QwtPlot.xBottom, point.timeData()),
            self.plot.invTransform(Qwt.QwtPlot.yLeft, point.temperatureData()))
        self.showInfo(info)

    # moved()

    def selected(self, _):
        self.showInfo()

    # selected()


def reverseAutoCorrelate(xin, correctAutoCorrelationForFiniteSize=False):
    """ usage: autoCorrelate(xin, correctAutoCorrelationForFiniteSize=False)
    removes mean, linear, and quadtraic components, then convolves with itself 
    convlve already flips it, so this is what you might intuitivitly think of convolving with itself backwards.  it is less sensitive to spiky noise
    if correctAutoCorrelationForFiniteSize = True, then it tries to correct for the finite size of the data set by assuming it is linear
    """
    
    xin = polyDetrend(xin,n=2) # mean, remove linear and quadtratic components (usually from drift)
    ac = np.convolve(xin, xin, 'full')  # not flipping actually gives better signal to noise, but the interpreation is more confusing
    ac = ac[np.floor(ac.size/2.0):]
    
    if correctAutoCorrelationForFiniteSize:
        ac = ac/(ac.size-np.arange(ac.size))
    return ac

def polyDetrend(yin, n=1):
    """ usage: polyDetrend(yin, n=2)
    yin is the array to be detrended
    n is the order of polynomial to subtract
    works by fitting a polynomial to yin, then subtracting the fit polynomrial
    """
    assert(yin.size == yin.shape[-1])
    if yin.size >2:
        xcoords = np.arange(yin.size)
        pfit = np.polyfit(xcoords, yin, n)
        return yin - np.polyval(pfit, xcoords)
    else: 
        return yin

def polySlope(xin, yin):
    """ usage: polySlope(xin,yin)
    yin is the array to be detrended
    n is the order of polynomial to subtract
    works by fitting a polynomial to yin, then subtracting the fit polynomrial
    """
    assert(yin.size == yin.shape[-1])
    if yin.size>2:
        pfit = np.polyfit(xin, yin, 1)
        slope = pfit[0]
        return slope
    else:
        return 0


# class MainWindow
    

def make():
    mainWin = MainWindow()
    mainWin.resize(640, 400)
    mainWin.show()
    return mainWin

# make()


def main(args, app = None, startdata = True):

    if app is None:
        app = QApplication(args)

    fonts = QFontDatabase()
    for name in ('Verdana', 'STIXGeneral'):
        if QString(name) in fonts.families():
            app.setFont(QFont(name))
            break
    tempLogger = make()
    if startdata is True:
        tempLogger.start_event()
    
    sys.exit(app.exec_())

# main()


# Admire!
if __name__ == '__main__':
    main(sys.argv)

# Local Variables: ***
# mode: python ***
# End: ***

