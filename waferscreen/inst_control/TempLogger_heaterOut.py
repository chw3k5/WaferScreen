#!/usr/bin/env python

# A template for a real time data plotter
# Based on BodeDemo.py and Stripchart
# By Douglas Bennett


import sys
from PyQt4.Qt import *
from PyQt4.Qwt5 import *
import PyQt4.Qwt5.anynumpy as np
from PyQt4 import QtGui, QtCore
import lakeshore370
from time import time
import numpy

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

        self.setTitle('Heater Out Logger')
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
        self.setAxisTitle(QwtPlot.yLeft, 'Heater Out (%)')

        self.setAxisMaxMajor(QwtPlot.xBottom, 6)
        #self.setAxisMaxMinor(QwtPlot.xBottom, 10)
        #self.setAxisScaleEngine(QwtPlot.xBottom, QwtLinearScaleEngine())

        # curve
        self.curve1 = QwtPlotCurve('Heater Out')
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

  
        toolBar.addSeparator()

        #Create  box for the timer button
        timerBox = QWidget(toolBar)
        #Create a loyout widget for the box
        timerBoxLayout = QHBoxLayout(timerBox)
        timerBoxLayout.setSpacing(0)
        timerBoxLayout.addWidget(QWidget(timerBox), 10) # spacer
        timerBoxLayout.addWidget(QLabel("Time Between Samples (ms)", timerBox), 0)
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
        self.connect(self.picker,
                     SIGNAL('selected(const QaPolygon &)'),
                     self.selected)

        self.timeData = np.zeros(0, float)
        self.temperatureData = np.zeros(0, float)
        self.counter = 0.0
        self.phase = 0.0

        # __init__()


    def setTimer(self, timerstep):
        self.timerstep = timerstep


    # setTimer()
    
    def resetData(self):
        self.timeData = np.zeros(0, float)
        self.temperatureData = np.zeros(0, float)
        self.time0 = time()

    def timerEvent(self, e):
        
        currentTemperature = self.lakeshore.getHeaterOut()
        currentTime = time()-self.time0
        
        self.timeData = np.append(self.timeData,currentTime)
        self.temperatureData = np.append(self.temperatureData,currentTemperature)
        self.yStdDev = np.std(self.temperatureData)
        self.plot.setTitle('Heater Out Std Deviation = %f mK'%self.yStdDev)
        
        self.plot.curve1.setData(self.timeData, self.temperatureData)
        
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
        self.the_event_timer = self.startTimer(self.timerstep)

    def stop_event(self):
        self.plot.killTimer(self.the_event_timer)

    def save_event(self):
        dataout = np.vstack((self.timeData,self.temperatureData))
        dataout = dataout.transpose()
        saveLocation = "/home/pcuser/data/ADRLogs/PostMag.txt"
        numpy.savetxt(saveLocation, dataout)
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



# class MainWindow
    

def make():
    mainWin = MainWindow()
    mainWin.resize(640, 400)
    mainWin.show()
    return mainWin

# make()


def main(args, app = None, startdata = False):

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

