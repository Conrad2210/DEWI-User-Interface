#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import csv
import time
import numpy as np
from statsmodels.distributions.empirical_distribution import ECDF
import serial
import thread
import sqlite3
import datetime
import threading
import random
from threading import Timer
from PyQt4 import QtGui
from cycler import cycler
from PyQt4.QtCore import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import databaseClassi
import plotly.plotly as py
import plotly.tools as tls
import networkx as nx


# configures the serial connections (the parameters differ depending on
# the device you are connected to)
ser = serial.Serial(
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS
)

# This lock serves as a MUTEX to prevent the different thread to access
# the database simultaneously
db_lock = thread.allocate_lock()

# A global declaration used by the store the TEST function to give the
# experiment name to the store process
experiment_name = ""


# This Script consists in three main threads.
# One to receive data and select which should be store.
# Another one to store the data selected in the database.
# The last one is the PyQt4 interface that permit the communication with
# the device and the management of the tests.


def receiving():  # receiving prints the informations received on the serial port
    print("Receiving started!")
    global node_list  # node_list contains the list of the shortadr of each registered node
    global output  # output serves as a FIFO buffer for the serial_output to be print in the pyQt window
    global data  # data serves as a FIFO buffer for the store thread

    try:
        # temp is the temporary character read from the serial port
        temp = ser.read(1)
        msg_end = 0
        while 1:
            out = ''  # out stores the string read from the ser.read
            # useful helps selecting which part of the string read we want to
            # keep in the list (the shortadr)
            useful = 0
            test = 0  # test helps us determine which which string read we want to store as a data
            elem = ""  # elem is the string selected to be a part of the list or the data from the string read on the serial port

            while ser.inWaiting() > 0:
                if temp == '\n':
                    temp = ser.read(1)
                    break
                if temp == "":  #  marks the end of the parameters of an answer
                    # We need to skip some characters (0\n) in order to
                    # properly stop to read
                    if test == 1:
                        test = 2
                    msg_end = 1
                    temp = ser.read(1)
                    break
                if temp == '0' and msg_end == 1:
                    msg_end = 0
                    while temp != "":
                        temp = ser.read(1)
                    break

                # Here we select which answer gives us the shortadr of a node
                if out == "DING" or out == "RESP" or out == "ROUT" or out == "DONG":
                    useful = 1
                # Here we select which answer are to be stored in the data.txt
                # file
                if out == "DATA" or out == "CAST" or out == "DATC":
                    test = 1
                if temp == "|":  # We don't need to have more than the first parameter the store the shortadr
                    useful = 0
                if useful == 1 or test == 1:
                    elem += temp
                out += temp
                temp = ser.read(1)

            if out != '':
                # As long as something is read, we havee to print it.
                if out.find('\n') == -1:
                    output.append(out)
    except:
        print "Receiveing terminated"  # ------------------PRINT------------------
        return

        # The database_init fonction creates a table in the database named experiment_name, removed the previous
        # with the same name and also creates the tables table if it doesn't
        # exist yet

        # The Worker classes aree used by the PyQt window to create threads
        # They are either working for ever, like the Out_Worker or are called at a precise moment when needed.


# Out_Worker is the Qthread responsible for the update of the ser_out text


class Out_Worker(QThread):
    def __init__(self, parent=None):

        QThread.__init__(self, parent)
        self.stop = 0

    def run(self):  # The run method is the method called as a thread
        global output

        while 1:
            if len(output) != 0:
                self.emit(SIGNAL("output(PyQt_PyObject)"), output[0])

                output.remove(output[0])

                if self.stop == 1:
                    print("\nOutput thread ended")
                    self.terminate()

    def stop_order(self):
        self.stop = 1


# Plt_Worker is the Qthread responsible for the update of the different
# axes used to plot the datas
class Plt_Worker(QThread):
    # It is called at the end
    # of each burst_processing
    # session

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.stop = 0
        self.delay = []

    def run(self):
        print("\nUpdating the graph...\n")
        self.delay = sorted(self.delay)
        self.window_reset()
        self.latency_draw(self.delay)

        if self.stop == 1:
            print("\nPlt thread ended")
            self.terminate()

    # Draws the current data list in order to make it easier to have latency
    # info
    def latency_draw(self, data):
        self.emit(SIGNAL("latency_draw(PyQt_PyObject)"), data)

    def window_reset(self):  # Clears the current axes and reset the axis and title parameters
        self.emit(SIGNAL("window_reset()"))

    # The launching method helps sending data to the thread before starting it
    def launching(self, delay_queue):
        self.delay = delay_queue
        self.start()

    def stop_order(self):
        self.stop = 1


class resultTimerThread(QThread):
    # It is called at the end
    # of each burst_processing
    # session

    def __init__(self, parent=None):
        QThread.__init__(self, parent)

        self.resultTimer = Timer(5, self.startRequestResults)

        self.connect(parent, SIGNAL("stopTimer()"), self.stopTimer)
        self.connect(parent, SIGNAL("startTimer()"), self.run)

    def run(self):
        print "timer started"
        self.resultTimer = Timer(5, self.startRequestResults)
        self.resultTimer.start()

    # Draws the current data list in order to make it easier to have latency
    # info
    def startRequestResults(self):
        print "timer ecpired"
        self.emit(SIGNAL("requestResult()"))

    # The launching method helps sending data to the thread before starting it
    def stopTimer(self):
        print "timer stopped"
        self.resultTimer.cancel()


# Test_Worker is the Qthread responsible for the running of the experiments
class Experiment_Worker(QThread):
    # It is called at the end
    # of the TEST function and
    # is there to time the
    # different steps of an
    # experiement

    # This way, the time.sleep() commands don't freeze the main thread which
    # is the whole window.
    def __init__(self, parent=None):
        # It acts the same way as
        # the end of the old TEST
        # function
        QThread.__init__(self, parent)
        self.parent = parent
        self.experiment_name = ""
        self.numberBursts = 0
        self.interval = 0
        self.msgPerBurst = 0
        self.listNeighbours = []
        self.burst_stop = 0
        self.connect(self.parent, SIGNAL(
            "neighbourList(PyQt_PyObject)"), self.neighbourListreceived)

    def run(self):
        print "test"
        print self.listNeighbours
        if (len(self.listNeighbours) != 0):
            global output
            global name_labels
            global burst
            global delay_queue  # CAST_end is a global flag used to tell this thread that the store thread has received the last CAST of the burst
            # This way, the Test thread can wait for the last CAST to begin the RQDT sequence.
            # These two variable link the data of the process with the other
            # threads (including the main)
            self.plr_y = []
            temp_plr_y = []
            delay_queue = []
            output.append(
                ("---------------Begin experiment: {0}!----------------").format(self.experiment_name))
            for j in range(self.numberBursts):
                timeout_count = 0
                burst_time_begin = datetime.datetime.now()
                output.append("---------------Begining of burst" +
                              str(j + 1) + "!----------------")

                for i in range(self.msgPerBurst):
                    ser.write("Experiment\n")
                    time.sleep(float(self.interval) / 1000.0)

                sleep = random.uniform(2.0, 4.0)
                print "time sleep: {0:.2f}".format(sleep)

                time.sleep(sleep)
                self.status_bar_print(
                    "----------Burst {0} of {1} processed----------".format(j + 1, self.numberBursts))
                if self.burst_stop == 1:
                    break

            self.emit(SIGNAL("experimentFinished()"))
        else:
            output.append("Can't run experiment, neighbourlist is 0")

        if self.stop == 1:
            print("\nTest thread ended")
            self.terminate()

    def neighbourListreceived(self, neighlist):
        print "Received Lsit"
        self.listNeighbours = neighlist
        print self.listNeighbours

    def launching(self, experiment_name, numberBursts, interval, msgPerBurst):
        self.experiment_name = experiment_name
        self.numberBursts = numberBursts
        self.interval = interval
        self.msgPerBurst = msgPerBurst

        self.start()

    def status_bar_print(self, str):  # This method prints a message on the status bar
        self.emit(SIGNAL("status_bar_print(PyQt_PyObject)"), str)

    # This method calls the experiments_combo_update method of the main window
    def experiments_combo_update(self):
        self.emit(SIGNAL("experiments_combo_update()"))

    # This method launches the plt_thread from the main window
    def plt_thread_launch(self, delay_queue):
        self.emit(SIGNAL("plt_thread_launch(PyQt_PyObject)"), delay_queue)

    def list_update(self):  # This method calls the list_update method of the main window
        self.emit(SIGNAL("list_update(PyQt_PyObject)"), self.plr_y)

    # This method is called when the user presses the STOP button
    def burst_stop_order(self):
        self.burst_stop = 1  # It stops the waiting for the end of the Cast
        # Or finishes the last RQDT sequence if received after the last CAST is
        # received
        self.status_bar_print("Waiting for the end of burst")

    def stop_order(self):  # This method terminates the thread
        self.stop = 1
        self.status_bar_print("Ending the Test Thread")


# The MainWindow is the core of the graphical interface
class MainWindow(QtGui.QMainWindow):
    output = ""

    def __init__(self):
        super(MainWindow, self).__init__()
        self.db = databaseClassi.databaseConnection()
        self.initUI()

    def serial_ports(self):
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def initUI(self):  # The initUI method initiates the whole graphical layout and start the output Qthread

        global delay_queue

        # The statusBar helps the user know what is going on and sends general
        # and shows the progress of an experiement
        self.statusBar().showMessage('Ready !')

        #####################################################
        parseFlockLabAction = QtGui.QAction("&Parse FlockLab",self)
        parseFlockLabAction.setShortcut('Ctrl+p');
        parseFlockLabAction.setStatusTip("Parse serial.csv files from FlockLab");
        parseFlockLabAction.triggered.connect(self.parseFlockLab)
        parseIoTLabAction = QtGui.QAction("&Parse IoTLab",self)
        parseIoTLabAction.setShortcut('Ctrl+p');
        parseIoTLabAction.setStatusTip("Parse serial.csv files from IoTLab");
        parseIoTLabAction.setEnabled(False);


        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&Parse')
        fileMenu.addAction(parseFlockLabAction)
        fileMenu.addAction(parseIoTLabAction)



        self.lastPath = "C:\Users\R00118979\Desktop"

        ##################################################


        self.xmax = 2000  # xmax defines the highest horizontal lenght of the latency graph
        self.x_list = []  # x_list is the list of the currently plot x_data for the the latency graph
        self.y_list = []  # y_list is the list of the currently plot y_data for the the latency graph
        self.plr_x = []  # x_list is the list of the currently plot x_data for the the plr graph
        self.plr_y = []  # y_list is the list of the currently plot y_data for the the plr graph
        self.PlotLegend = []
        delay_queue = []
        # Our figure, canvas and axes necessary to plot
        self.figure_latency = plt.figure()
        self.figure_plr = plt.figure()
        self.figure_topology = plt.figure()
        self.canvas_latency = FigureCanvas(self.figure_latency)
        self.canvas_plr = FigureCanvas(self.figure_plr)
        self.axes_latency = self.figure_latency.add_subplot(111)
        self.axes_latency.hold(True)
        self.axes_plr = self.figure_plr.add_subplot(111)
        self.axes_plr.hold(True)
        # self.axes_plr.set_prop_cycle(cycler('color', ['c', 'm', 'y', 'k']))
        self.window_reset()
        # Then, a lot of declarations appears.
        # The following declaration serves for the TEST part of the window
        msgPerBurst_label = QtGui.QLabel()
        msgPerBurst_label.setText("# MSG's per Burst:")
        self.msgPerBurst_text = QtGui.QLineEdit()

        self.neighConnected_label = QtGui.QLabel()
        self.neighConnected_label.setText(
            ("Neighbours Connected: {0}").format(0))

        RSSIRadius_label = QtGui.QLabel()
        RSSIRadius_label.setText("RSSI Radius [dB]:")
        self.RSSIRadius_text = QtGui.QLineEdit()
        self.RSSIRadius_button = QtGui.QPushButton('RSSI Send')
        self.RSSIRadius_button.clicked.connect(self.RSSISend)
        LQIRadius_label = QtGui.QLabel()
        LQIRadius_label.setText("LQI Radius [0-255]:")
        self.LQIRadius_button = QtGui.QPushButton('LQI Send')
        self.LQIRadius_button.clicked.connect(self.LQISend)

        self.LQIRadius_text = QtGui.QLineEdit()

        TXPower_label = QtGui.QLabel()
        TXPower_label.setText("Tx Power [-23..7dBm]:")
        self.TXPower_button = QtGui.QPushButton('TXPower Send')
        self.TXPower_button.clicked.connect(self.TXPowerSend)
        self.TXPower_text = QtGui.QLineEdit()

        numberBursts_label = QtGui.QLabel()
        numberBursts_label.setText("# Bursts:")
        self.numberBursts_text = QtGui.QLineEdit()

        test_label = QtGui.QLabel()
        test_label.setText("Description: ")
        self.experiment_line = QtGui.QLineEdit()

        serialPort_label = QtGui.QLabel()
        serialPort_label.setText("Serial Port")

        interval_label = QtGui.QLabel()
        interval_label.setText("Interarrivaltime [ms]:")
        self.interval_combo = QtGui.QComboBox()
        self.interval_combo.addItem("100")
        self.interval_combo.addItem("110")
        self.interval_combo.addItem("120")
        self.interval_combo.addItem("130")
        self.interval_combo.addItem("140")
        self.interval_combo.addItem("150")
        self.interval_combo.addItem("160")
        self.interval_combo.addItem("170")
        self.interval_combo.addItem("180")
        self.interval_combo.addItem("190")
        self.interval_combo.addItem("200")
        self.interval_combo.addItem("210")
        self.interval_combo.addItem("220")
        self.interval_combo.addItem("230")
        self.interval_combo.addItem("240")
        self.interval_combo.addItem("250")

        self.serialPorts_combo = QtGui.QComboBox()

        for string in self.serial_ports():
            self.serialPorts_combo.addItem(string)

        self.compare1 = QtGui.QComboBox()
        self.compare2 = QtGui.QComboBox()
        self.compare3 = QtGui.QComboBox()
        self.compare4 = QtGui.QComboBox()
        self.compare5 = QtGui.QComboBox()

        self.check1 = QtGui.QCheckBox("1:")
        self.check2 = QtGui.QCheckBox("2:")
        self.check3 = QtGui.QCheckBox("3:")
        self.check4 = QtGui.QCheckBox("4:")
        self.check5 = QtGui.QCheckBox("5:")

        self.START_button = QtGui.QPushButton('~  START  ~')
        self.NEXT_button = QtGui.QPushButton('Next Result')
        self.lastAddr = ""
        STOP_button = QtGui.QPushButton('~  STOP  ~')
        PLOT_button = QtGui.QPushButton('PLOT')

        ser_out_label = QtGui.QLabel()  # Then the Communication part
        ser_out_label.setText("Serial Output : ")
        self.ser_out = QtGui.QTextEdit()

        self.NeighUpdate_button = QtGui.QPushButton('Neigh Update')
        self.PRINT_button = QtGui.QPushButton('Print List')
        self.FlushResults_button = QtGui.QPushButton('FlushResults')
        self.StartCIDER_button = QtGui.QPushButton('StartCIDER')
        REQUEST_button = QtGui.QPushButton('Request Results')
        self.CONNECT_button = QtGui.QPushButton('Connect')


        self.HEATMAP_buttion1 = QtGui.QPushButton('Draw Heatmap 1')
        self.SelectHeatmap_buttion1 = QtGui.QPushButton('SelectHeatmap 1')
        self.SelectHeatmap_file1 = QtGui.QLineEdit()
        self.SelectHeatmap_file1.setEnabled(False)
        self.HEATMAP_buttion2 = QtGui.QPushButton('Draw Heatmap 2')
        self.SelectHeatmap_buttion2 = QtGui.QPushButton('SelectHeatmap 2')
        self.SelectHeatmap_file2 = QtGui.QLineEdit()
        self.SelectHeatmap_file2.setEnabled(False)
        self.HEATMAP_buttion3 = QtGui.QPushButton('Draw Heatmap 3')
        self.SelectHeatmap_buttion3 = QtGui.QPushButton('SelectHeatmap 3')
        self.SelectHeatmap_file3 = QtGui.QLineEdit()
        self.SelectHeatmap_file3.setEnabled(False)
        self.HEATMAP_buttion4 = QtGui.QPushButton('Draw Heatmap 4')
        self.SelectHeatmap_buttion4 = QtGui.QPushButton('SelectHeatmap 4')
        self.SelectHeatmap_file4 = QtGui.QLineEdit()
        self.SelectHeatmap_file4.setEnabled(False)
        self.HEATMAP_buttion5 = QtGui.QPushButton('Draw Heatmap 5')
        self.SelectHeatmap_buttion5 = QtGui.QPushButton('SelectHeatmap 5')
        self.SelectHeatmap_file5 = QtGui.QLineEdit()
        self.SelectHeatmap_file5.setEnabled(False)


        self.Topology_buttion1 = QtGui.QPushButton('Draw Topology 1')
        self.Topology_buttion1.clicked.connect(self.drawTopology1)
        self.Topology_buttion2 = QtGui.QPushButton('Draw Topology 2')
        self.Topology_buttion3 = QtGui.QPushButton('Draw Topology 3')
        self.Topology_buttion4 = QtGui.QPushButton('Draw Topology 4')
        self.Topology_buttion5 = QtGui.QPushButton('Draw Topology 5')


        self.HEATMAP_buttion1.clicked.connect(self.drawHeatmap1)
        self.SelectHeatmap_buttion1.clicked.connect(self.selectHeatmapFile1)
        self.HEATMAP_buttion2.clicked.connect(self.drawHeatmap2)
        self.SelectHeatmap_buttion2.clicked.connect(self.selectHeatmapFile2)
        self.HEATMAP_buttion3.clicked.connect(self.drawHeatmap3)
        self.SelectHeatmap_buttion3.clicked.connect(self.selectHeatmapFile3)
        self.HEATMAP_buttion4.clicked.connect(self.drawHeatmap4)
        self.SelectHeatmap_buttion4.clicked.connect(self.selectHeatmapFile4)
        self.HEATMAP_buttion5.clicked.connect(self.drawHeatmap5)
        self.SelectHeatmap_buttion5.clicked.connect(self.selectHeatmapFile5)

        self.START_button.clicked.connect(self.START)
        # The buttons are then connected to their method


        self.addCheckBox = QtGui.QRadioButton("add")
        self.seperateCheckBox = QtGui.QRadioButton("seperate")
        PLOT_button.clicked.connect(self.compare)
        self.NeighUpdate_button.clicked.connect(self.neighUpdate)
        self.PRINT_button.clicked.connect(self.printList)
        REQUEST_button.clicked.connect(self.startRequestResults)
        self.CONNECT_button.clicked.connect(self.connectSerial)
        self.FlushResults_button.clicked.connect(self.FlushResults)
        self.StartCIDER_button.clicked.connect(self.StartCIDER)
        self.NEXT_button.clicked.connect(self.SkipResult)

        # Since the mainwindow is a MainWindow, it need a QWidget as a Central
        # Widget
        top_widget = QtGui.QWidget()
        # The Layout is done with QVBoxLayout and QHBoxLayout
        top_Hbox = QtGui.QHBoxLayout()

        comm_VBox = QtGui.QVBoxLayout()
        comm_HBox1 = QtGui.QHBoxLayout()
        comm_HBox2 = QtGui.QHBoxLayout()
        comm_HBox3 = QtGui.QHBoxLayout()
        comm_HBox4 = QtGui.QHBoxLayout()
        comm_HBox5 = QtGui.QHBoxLayout()
        comm_HBox6 = QtGui.QHBoxLayout()

        comm_VBox.addLayout(comm_HBox1)
        comm_VBox.addLayout(comm_HBox2)
        comm_VBox.addLayout(comm_HBox3)
        comm_VBox.addLayout(comm_HBox4)
        comm_VBox.addLayout(comm_HBox5)
        comm_VBox.addLayout(comm_HBox6)
        comm_VBox.addWidget(ser_out_label)
        comm_VBox.addWidget(self.ser_out)

        comm_HBox1.addWidget(self.NeighUpdate_button)
        comm_HBox1.addWidget(self.PRINT_button)
        comm_HBox1.addWidget(self.FlushResults_button)
        comm_HBox1.addWidget(self.StartCIDER_button)

        comm_HBox2.addWidget(self.neighConnected_label)
        comm_HBox2.addWidget(REQUEST_button)

        comm_HBox3.addWidget(serialPort_label)
        comm_HBox3.addWidget(self.serialPorts_combo)
        comm_HBox3.addWidget(self.CONNECT_button)

        comm_HBox4.addWidget(RSSIRadius_label)
        comm_HBox4.addWidget(self.RSSIRadius_text)
        comm_HBox4.addWidget(self.RSSIRadius_button)
        comm_HBox5.addWidget(LQIRadius_label)
        comm_HBox5.addWidget(self.LQIRadius_text)
        comm_HBox5.addWidget(self.LQIRadius_button)
        comm_HBox6.addWidget(TXPower_label)
        comm_HBox6.addWidget(self.TXPower_text)
        comm_HBox6.addWidget(self.TXPower_button)

        test_VBox = QtGui.QVBoxLayout()
        test_HBox1 = QtGui.QHBoxLayout()
        test_HBox2 = QtGui.QHBoxLayout()
        test_HBox4 = QtGui.QHBoxLayout()
        test_HBox5 = QtGui.QHBoxLayout()
        test_HBox6 = QtGui.QHBoxLayout()
        test_HBox7 = QtGui.QHBoxLayout()
        test_HBox8 = QtGui.QHBoxLayout()
        test_HBox9 = QtGui.QHBoxLayout()
        test_HBox10 = QtGui.QHBoxLayout()
        test_HBox11 = QtGui.QHBoxLayout()

        test_HBox1.addStretch(1)
        test_HBox1.addWidget(test_label)
        test_HBox1.addWidget(self.experiment_line)
        test_HBox1.addStretch(1)

        test_HBox21 = QtGui.QHBoxLayout()
        test_HBox22 = QtGui.QHBoxLayout()
        test_HBox23 = QtGui.QHBoxLayout()
        test_HBox24 = QtGui.QHBoxLayout()
        test_VBox1 = QtGui.QVBoxLayout()
        test_VBox2 = QtGui.QVBoxLayout()

        test_HBox21.addWidget(numberBursts_label)
        test_HBox21.addStretch(1)
        test_HBox21.addWidget(self.numberBursts_text)
        test_HBox21.addStretch(1)
        test_HBox22.addWidget(interval_label)
        test_HBox22.addStretch(1)
        test_HBox22.addWidget(self.interval_combo)
        test_HBox22.addStretch(1)

        test_VBox1.addLayout(test_HBox21)
        test_VBox1.addLayout(test_HBox22)

        test_HBox23.addWidget(msgPerBurst_label)
        test_HBox23.addStretch(1)
        test_HBox23.addWidget(self.msgPerBurst_text)

        test_VBox2.addLayout(test_HBox23)
        test_VBox2.addLayout(test_HBox24)

        test_HBox2.addLayout(test_VBox1)
        test_HBox2.addLayout(test_VBox2)

        test_HBox4.addStretch(1)
        test_HBox4.addWidget(self.START_button)
        test_HBox4.addWidget(STOP_button)
        test_HBox4.addWidget(self.NEXT_button)
        test_HBox4.addStretch(1)

        test_HBox5.addWidget(self.canvas_latency)
        test_HBox5.addWidget(self.canvas_plr)

        test_HBox6.addStretch(1)
        test_HBox6.addWidget(self.check1)
        test_HBox6.addWidget(self.compare1)
        test_HBox6.addWidget(self.SelectHeatmap_file1)
        test_HBox6.addWidget(self.SelectHeatmap_buttion1)
        test_HBox6.addWidget(self.HEATMAP_buttion1)
        test_HBox6.addWidget(self.Topology_buttion1)
        test_HBox6.addStretch(1)

        test_HBox7.addStretch(1)
        test_HBox7.addWidget(self.check2)
        test_HBox7.addWidget(self.compare2)
        test_HBox7.addWidget(self.SelectHeatmap_file2)
        test_HBox7.addWidget(self.SelectHeatmap_buttion2)
        test_HBox7.addWidget(self.HEATMAP_buttion2)
        test_HBox7.addStretch(1)

        test_HBox8.addStretch(1)
        test_HBox8.addWidget(self.check3)
        test_HBox8.addWidget(self.compare3)
        test_HBox8.addWidget(self.SelectHeatmap_file3)
        test_HBox8.addWidget(self.SelectHeatmap_buttion3)
        test_HBox8.addWidget(self.HEATMAP_buttion3)
        test_HBox8.addStretch(1)

        test_HBox9.addStretch(1)
        test_HBox9.addWidget(self.check4)
        test_HBox9.addWidget(self.compare4)
        test_HBox9.addWidget(self.SelectHeatmap_file4)
        test_HBox9.addWidget(self.SelectHeatmap_buttion4)
        test_HBox9.addWidget(self.HEATMAP_buttion4)
        test_HBox9.addStretch(1)

        test_HBox10.addStretch(1)
        test_HBox10.addWidget(self.check5)
        test_HBox10.addWidget(self.compare5)
        test_HBox10.addWidget(self.SelectHeatmap_file5)
        test_HBox10.addWidget(self.SelectHeatmap_buttion5)
        test_HBox10.addWidget(self.HEATMAP_buttion5)

        test_HBox10.addStretch(1)

        test_HBox11.addStretch(1)
        test_HBox11.addWidget(PLOT_button)
        test_HBox11.addWidget(self.addCheckBox)
        test_HBox11.addWidget(self.seperateCheckBox)
        test_HBox11.addStretch(1)

        test_VBox.addLayout(test_HBox1)
        test_VBox.addLayout(test_HBox2)
        test_VBox.addLayout(test_HBox4)
        test_VBox.addLayout(test_HBox5)
        test_VBox.addLayout(test_HBox6)
        test_VBox.addLayout(test_HBox7)
        test_VBox.addLayout(test_HBox8)
        test_VBox.addLayout(test_HBox9)
        test_VBox.addLayout(test_HBox10)
        test_VBox.addLayout(test_HBox11)

        top_Hbox.addLayout(comm_VBox)
        top_Hbox.addLayout(test_VBox)

        top_widget.setLayout(top_Hbox)
        self.setCentralWidget(top_widget)

        self.setGeometry(40, 40, 1200, 650)
        self.setWindowTitle('Network testing')

        self.plt_thread = Plt_Worker()  # Initialization different of the Qthreads
        self.connect(self.plt_thread, SIGNAL(
            "window_reset()"), self.window_reset)

        self.experiment_thread = Experiment_Worker(self)
        self.connect(self.experiment_thread, SIGNAL(
            "experimentFinished()"), self.experimentFinished)
        self.connect(self.experiment_thread, SIGNAL(
            "plt_thread_launch(PyQt_PyObject)"), self.plt_thread.launching)
        self.connect(self.experiment_thread, SIGNAL(
            "experiments_combo_update()"), self.experiments_combo_update)
        self.connect(self.experiment_thread, SIGNAL(
            "list_update(PyQt_PyObject)"), self.list_update)
        self.connect(self.experiment_thread, SIGNAL(
            "status_bar_print(PyQt_PyObject)"), self.status_bar_print)

        self.out_thread = Out_Worker()
        self.connect(self.out_thread, SIGNAL(
            "output(PyQt_PyObject)"), self.output_update)
        self.out_thread.start()

        self.requestResultTimer = resultTimerThread(self)
        self.connect(self.requestResultTimer, SIGNAL(
            "requestResult()"), self.startRequestResults)

        self.experiments_combo_update()

        self.show()


    def parseFlockLab(self):
        # results = ["test":[]];
        self.lastPath = QtGui.QFileDialog.getOpenFileName(self, "Open FlockLab file",self.lastPath,"CSV (*.csv)")
        self.txPackets = {};
        self.rxPackets = {};
        with open(self.lastPath, 'rb') as csvfile:
            file =csv.reader(csvfile);

            for row in file:
                try:
                    if "Packets:" in row[6]:
                        if "rx" in row[6]:
                            try:
                                if self.rxPackets[int(row[1])] != None:
                                    self.rxPackets[int(row[1])].append([row[0],int(row[5][row[5].index(":") + 1:len(row[6])])])
                            except KeyError:
                                self.rxPackets[int(row[1])] = [[row[0],int(row[5][row[5].index(":") + 1:len(row[6])])]];
                            self.db.insertRxPacketsParseFlockLab(0,0,int(row[1]),int(row[6][row[6].index(" ") + 1:len(row[6])]))
                        elif "tx" in row[6]:
                            try:
                                if self.txPackets[int(row[1])] != None:
                                    self.txPackets[int(row[1])].append([row[0],int(row[5][row[5].index(":") + 1:len(row[6])])])
                            except KeyError:
                                self.txPackets[int(row[1])] = [[row[0],int(row[5][row[5].index(":") + 1:len(row[6])])]];
                            self.db.insertTxPacketsParseFlockLab(0,0,int(row[1]),int(row[6][row[6].index(" ") + 1:len(row[6])]))
                except IndexError:
                    print "not in range"

            for dataSetTx in self.txPackets:
                for entryTx in self.txPackets[dataSetTx]:
                    for dataSetRx in self.rxPackets:
                        for entryRx in self.rxPackets[dataSetRx]:
                            if entryTx[1] == entryRx[1]:
                                entryRx[0] = float(entryRx[0]) - float(entryTx[0]);
                                if entryRx[0] > 0:
                                    self.db.insertLatency(0,0,entryRx[1],entryRx[0],1);
                                break;

            print "done"


    # These are the methods to call when the window is being closed. The two
    # Qthreads are asked to stop.
    def closeEvent(self, event):
        self.out_thread.stop_order()
        self.plt_thread.stop_order()

    def keyPressEvent(self, event):  # If the 'ENTER' key is pressed, SEND the message
        key = event.key()

        if key == 16777220:
            self.SEND()

    # This method displays the str message on the statusBar
    def status_bar_print(self, str):
        self.statusBar().showMessage(str)

    # This method is called via a signal by the test_thread to update values
    # to plot the data
    def list_update(self, plr_mean):
        self.plr_y = [plr_mean]
        self.x_list = []
        self.y_list = []

    # This method update the ser_out text when receiveng a signal from the
    # out_thread
    def output_update(self, str):
        #print str
        self.ser_out.append(str)
        str = str.replace(' ', '')
        if len("[QUEUE]:") < len(str):
            if "[QUEUE]:" in str:
                print str
            if "TSCH-queue:!" in str:
                print str

        if len("TPReply:") < len(str):
            if "TPReply:" in str:
                print str
                result = str[str.index(":") + 1:len(str)]
                result = result.split(",")
                self.db.insertTempNeighbour(
                    0, result[0], result[1], result[2], result[3])
            if "RESULTReplyTxPackets:" in str:
                print str
                result = str[str.index(":") + 1:len(str)]
                result = result.split(",")
                self.db.insertTxPackets(0, self.db.getLastExperimentID(), result[0], result[1])
                self.NextRequestResult(result[0])
            if "RESULTReplyRxPackets:" in str:
                print str
                result = str[str.index(":") + 1:len(str)]
                result = result.split(",")
                self.db.insertRxPackets(0, self.db.getLastExperimentID(), result[0], result[1])
                self.NextRequestResult(result[0])
            if "RESULTReplyLatency:" in str:
                print str
                result = str[str.index(":") + 1:len(str)]
                result = result.split(",")
                self.db.insertLatency(0, self.db.getLastExperimentID(), result[0], result[1], result[2])
                # self.db.insertTempNeighbour(0,hex(result[0]),hex(result[1]),result[2],result[3])

        c = self.ser_out.textCursor()
        c.movePosition(QtGui.QTextCursor.End)
        self.ser_out.setTextCursor(c)

    def experiments_combo_update(self):  #
        self.compare1.clear()
        self.compare2.clear()
        self.compare3.clear()
        self.compare4.clear()
        self.compare5.clear()
        self.compare1.addItem(str("[session_id]: description, #Bursts, duration, #msg, TXPower, RSSIRadius, Date"))
        self.compare2.addItem(str("[session_id]: description, #Bursts, duration, #msg, TXPower, RSSIRadius, Date"))
        self.compare3.addItem(str("[session_id]: description, #Bursts, duration, #msg, TXPower, RSSIRadius, Date"))
        self.compare4.addItem(str("[session_id]: description, #Bursts, duration, #msg, TXPower, RSSIRadius, Date"))
        self.compare5.addItem(str("[session_id]: description, #Bursts, duration, #msg, TXPower, RSSIRadius, Date"))
        experiment_list = self.db.getExperiments()
        for i in range(0, len(experiment_list)):
            self.compare1.addItem(str(
                "[{0}]: {1}, {2}, {3}s, {4}, {5} dBm, {6} dB, {7}".format(experiment_list[i][1], experiment_list[i][0], experiment_list[i][2],
                                                    experiment_list[i][3], experiment_list[i][4], experiment_list[i][5], experiment_list[i][6], QDateTime.fromTime_t(int(experiment_list[i][7])).toString("dd.MM.yyyy HH:mm"))))
            self.compare2.addItem(str(
                "[{0}]: {1}, {2}, {3}s, {4}, {5} dBm, {6} dB, {7}".format(experiment_list[i][1], experiment_list[i][0], experiment_list[i][2],
                                                    experiment_list[i][3], experiment_list[i][4], experiment_list[i][5], experiment_list[i][6], QDateTime.fromTime_t(int(experiment_list[i][7])).toString("dd.MM.yyyy HH:mm"))))
            self.compare3.addItem(str(
                "[{0}]: {1}, {2}, {3}s, {4}, {5} dBm, {6} dB, {7}".format(experiment_list[i][1], experiment_list[i][0], experiment_list[i][2],
                                                    experiment_list[i][3], experiment_list[i][4], experiment_list[i][5], experiment_list[i][6], QDateTime.fromTime_t(int(experiment_list[i][7])).toString("dd.MM.yyyy HH:mm"))))
            self.compare4.addItem(str(
                "[{0}]: {1}, {2}, {3}s, {4}, {5} dBm, {6} dB, {7}".format(experiment_list[i][1], experiment_list[i][0], experiment_list[i][2],
                                                    experiment_list[i][3], experiment_list[i][4], experiment_list[i][5], experiment_list[i][6], QDateTime.fromTime_t(int(experiment_list[i][7])).toString("dd.MM.yyyy HH:mm"))))
            self.compare5.addItem(str(
                "[{0}]: {1}, {2}, {3}s, {4}, {5} dBm, {6} dB, {7}".format(experiment_list[i][1], experiment_list[i][0], experiment_list[i][2],
                                                    experiment_list[i][3], experiment_list[i][4], experiment_list[i][5], experiment_list[i][6], QDateTime.fromTime_t(int(experiment_list[i][7])).toString("dd.MM.yyyy HH:mm"))))


            #        cursor = db.cursor()
        #
        #
        # for row in cursor :
        # experiment_list.append(str(row[0]))



        #
        #        print ("list of the different experiments updated : ")
        #        print(experiment_list)

    def compare(self):  # Plot the data of the chosen experiments
        if self.addCheckBox.isChecked() == True:
            session_ids = []
            templat = []
            self.PlotLegend = []
            try:
                if self.check1.isChecked() == True:
                    session_ids.append(int(self.compare1.currentText()[
                                           self.compare1.currentText().index("[") + 1:self.compare1.currentText().index(
                                               "]")]))
            except  ValueError:
                print ValueError
            try:
                if self.check2.isChecked() == True:
                    session_ids.append(int(self.compare2.currentText()[
                                           self.compare2.currentText().index("[") + 1:self.compare2.currentText().index(
                                               "]")]))
            except  ValueError:
                print ValueError
            try:
                if self.check3.isChecked() == True:
                    session_ids.append(int(self.compare3.currentText()[
                                           self.compare3.currentText().index("[") + 1:self.compare3.currentText().index(
                                               "]")]))
            except  ValueError:
                print ValueError
            try:
                if self.check4.isChecked() == True:
                    session_ids.append(int(self.compare4.currentText()[
                                           self.compare4.currentText().index("[") + 1:self.compare4.currentText().index(
                                               "]")]))
            except  ValueError:
                print ValueError
            try:
                if self.check5.isChecked() == True:
                    session_ids.append(int(self.compare5.currentText()[
                                           self.compare5.currentText().index("[") + 1:self.compare5.currentText().index(
                                               "]")]))
            except  ValueError:
                print ValueError

            for i in range(0, len(session_ids)):
                templat.append(self.db.getLatencyResult(session_ids[i]))
                self.PlotLegend.append(self.db.getDescription(session_ids[i]))



            for k in range(0, len(templat)):
                for i in range(0, len(templat[k])):
                    for j in range(0, templat[k][i][1]):
                        latency.append(int(templat[k][i][0] * 10))

            ecdf = ECDF(latency)
            self.x_list = []
            self.y_list = []
            self.x_list.append(list(ecdf.x))
            self.y_list.append(list(ecdf.y))
            self.plot()
        else:
            session_ids = []
            templat = []
            temprx = []
            temptx = []

            self.x_list = []
            self.y_list = []
            self.plr_x = []
            self.plr_y = []
            try:
                if self.check1.isChecked() == True:
                    session_ids.append(int(str(self.compare1.currentText())[
                                           str(self.compare1.currentText()).index("[") + 1:str(
                                               self.compare1.currentText()).index("]")]))
            except  ValueError:
                print ValueError
            try:
                if self.check2.isChecked() == True:
                    session_ids.append(int(str(self.compare2.currentText())[
                                           str(self.compare2.currentText()).index("[") + 1:str(
                                               self.compare2.currentText()).index("]")]))
            except  ValueError:
                print ValueError
            try:
                if self.check3.isChecked() == True:
                    session_ids.append(int(str(self.compare3.currentText())[
                                           str(self.compare3.currentText()).index("[") + 1:str(
                                               self.compare3.currentText()).index("]")]))
            except  ValueError:
                print ValueError
            try:
                if self.check4.isChecked() == True:
                    session_ids.append(int(str(self.compare4.currentText())[
                                           str(self.compare4.currentText()).index("[") + 1:str(
                                               self.compare4.currentText()).index("]")]))
            except  ValueError:
                print ValueError
            try:
                if self.check5.isChecked() == True:
                    session_ids.append(int(str(self.compare5.currentText())[
                                           str(self.compare5.currentText()).index("[") + 1:str(
                                               self.compare5.currentText()).index("]")]))
            except  ValueError:
                print ValueError
            self.PlotLegend = []
            for i in range(0, len(session_ids)):
                templat.append(self.db.getLatencyResult(session_ids[i]))
                temprx.append(self.db.getRXPackets(session_ids[i]))
                temptx.append(self.db.getTXPackets(session_ids[i]))
                self.PlotLegend.append(str(self.db.getDescription(session_ids[i])[0]))

            latency = []
            for k in range(0, len(templat)):
                latency = []
                for i in range(0, len(templat[k])):
                    for j in range(0, templat[k][i][1]):
                        latency.append(int(templat[k][i][0] * 10))

                ecdf = ECDF(latency)
                self.x_list.append(list(ecdf.x))
                self.y_list.append(list(ecdf.y))

            for k in range(0, len(temprx)):
                for i in range(0, len(temprx[k])):
                    temprx[k][i] = 100. - ((100. * float(temprx[k][i])) / float(temptx[k][0]))

                self.plr_x.append(k)
                self.plr_y.append(float(sum(temprx[k]) / len(temprx[k])))

            self.plot()

    def drawTopology1(self):
        if self.check1.isChecked() == True:
            sessionid = int(str(self.compare1.currentText())[
                            str(self.compare1.currentText()).index("[") + 1:str(
                                self.compare1.currentText()).index("]")])

            if (sessionid > -1):
                G = nx.Graph()
                topologyList = self.db.getTopology(sessionid)
                G.add_nodes_from(topologyList[1]);
                for node in topologyList[0]:
                    G.add_edge(node[0],node[1]);
                pos = nx.fruchterman_reingold_layout(G)
                color = ['b','g','r','c','m','y','k','w']


                for node in topologyList[0]:
                    nx.draw_networkx_nodes(G, pos=pos, with_labels=True, nodelist=[node[0],node[1]], node_size=2500,
                                           node_color=color[node[3]])
                    nx.draw_networkx_edges(G, pos=pos, edgelist=[[node[0],node[1]]])
                    nx.draw_networkx_labels(G, pos=pos)

                plt.show()  # display

        return
    def drawHeatmap1(self):
        if(self.SelectHeatmap_file1.text() != "" and self.check1.isChecked() == True):
            sessionid = int(str(self.compare1.currentText())[
                                           str(self.compare1.currentText()).index("[") + 1:str(
                                               self.compare1.currentText()).index("]")])

            if(sessionid > -1):
                txPackets = self.db.getTXPackets(sessionid)
                description = self.db.getDescription(sessionid)
                print txPackets
                self.topology = []
                print os.path.join(str(self.SelectHeatmap_file1.text()))
                csvfile = open(os.path.join(str(self.SelectHeatmap_file1.text())), 'r')
                print csvfile
                spamreader = csv.reader(csvfile, delimiter=',')
                for row in spamreader:
                    self.topology.append(row)
                self.topology.reverse();
                tempResult = [];
                # for i in range(0,len(self.topology)):
                #     self.topology[i].reverse();
                tempResult = self.topology

                for i in range(0,len(self.topology)):
                    for k in range(0,len(self.topology[i])):
                        if self.topology[i][k] != '':
                            tempResult[i][k] = self.db.getRXPacketsForNode(int(sessionid),self.topology[i][k])
                            print tempResult[i][k]
                            if tempResult[i][k] == None:
                                tempResult[i][k] = 0

                            tempResult[i][k] = 100 - ((100/float(txPackets[0])) * float(tempResult[i][k]))

                        else:
                            tempResult[i][k] = 0

                fig = plt.figure()
                ax = fig.add_subplot(111)

                ax.set_title(description[0])

                plotly_fig = tls.mpl_to_plotly(fig)

                trace = dict(z=tempResult, type="heatmap", zmin=0, zmax=40)

                plotly_fig['data'] = [trace]

                print plotly_fig
                plotly_fig['layout']['xaxis1'].update({'autorange': True})
                plotly_fig['layout']['yaxis1'].update({'autorange': True})

                plot_url = py.plot(plotly_fig, filename=description[0])


    def drawHeatmap2(self):
        if(self.SelectHeatmap_file2.text() != "" and self.check2.isChecked() == True):
            sessionid = int(str(self.compare2.currentText())[
                                           str(self.compare2.currentText()).index("[") + 1:str(
                                               self.compare2.currentText()).index("]")])

            if(sessionid > -1):
                txPackets = self.db.getTXPackets(sessionid)
                description = self.db.getDescription(sessionid)

                self.topology = []
                print os.path.join(str(self.SelectHeatmap_file2.text()))
                csvfile = open(os.path.join(str(self.SelectHeatmap_file2.text())), 'r')
                print csvfile
                spamreader = csv.reader(csvfile, delimiter=',')
                for row in spamreader:
                    self.topology.append(row)
                self.topology = list(self.topology)
                tempResult = self.topology
                counter1 = 0
                counter2 = 0
                for i in range(0,len(self.topology)):

                    counter2 = 0
                    for k in range(0,len(self.topology[i])):
                        if self.topology[i][k] != '':
                            tempResult[i][k] = self.db.getRXPacketsForNode(int(sessionid),self.topology[i][k])
                            if tempResult[i][k] == None:
                                tempResult[i][k] = 0
                            tempResult[i][k] = 100 - ((100/float(txPackets[0])) * float(tempResult[i][k]))
                        else:
                            tempResult[i][k] = 0

                fig = plt.figure()
                ax = fig.add_subplot(111)

                ax.set_title('PLR Heatmap')

                plotly_fig = tls.mpl_to_plotly(fig)

                trace = dict(z=tempResult, type="heatmap", zmin=0, zmax=10)

                plotly_fig['data'] = [trace]

                print plotly_fig
                plotly_fig['layout']['xaxis1'].update({'autorange': True})
                plotly_fig['layout']['yaxis1'].update({'autorange': True})

                plot_url = py.plot(plotly_fig, filename=description[0])

    def drawHeatmap3(self):
        if(self.SelectHeatmap_file3.text() != "" and self.check3.isChecked() == True):
            sessionid = int(str(self.compare3.currentText())[
                                           str(self.compare3.currentText()).index("[") + 1:str(
                                               self.compare3.currentText()).index("]")])

            if(sessionid > -1):
                txPackets = self.db.getTXPackets(sessionid)
                description = self.db.getDescription(sessionid)
                print txPackets
                self.topology = []
                print os.path.join(str(self.SelectHeatmap_file3.text()))
                csvfile = open(os.path.join(str(self.SelectHeatmap_file3.text())), 'r')
                print csvfile
                spamreader = csv.reader(csvfile, delimiter=',')
                for row in spamreader:
                    self.topology.append(row)
                self.topology = list(self.topology)
                tempResult = self.topology
                counter1 = 0
                counter2 = 0
                for i in range(0,len(self.topology)):

                    counter2 = 0
                    for k in range(0,len(self.topology[i])):
                        if self.topology[i][k] != '':
                            tempResult[i][k] = self.db.getRXPacketsForNode(int(sessionid),self.topology[i][k])
                            if tempResult[i][k] == None:
                                tempResult[i][k] = 0
                            tempResult[i][k] = 100 - ((100/float(txPackets[0])) * float(tempResult[i][k]))
                        else:
                            tempResult[i][k] = 0

                fig = plt.figure()
                ax = fig.add_subplot(111)

                ax.set_title('PLR Heatmap')

                plotly_fig = tls.mpl_to_plotly(fig)

                trace = dict(z=tempResult, type="heatmap", zmin=0, zmax=10)

                plotly_fig['data'] = [trace]

                print plotly_fig
                plotly_fig['layout']['xaxis1'].update({'autorange': True})
                plotly_fig['layout']['yaxis1'].update({'autorange': True})

                plot_url = py.plot(plotly_fig, filename=description[0])

    def drawHeatmap4(self):
        if(self.SelectHeatmap_file4.text() != "" and self.check4.isChecked() == True):
            sessionid = int(str(self.compare4.currentText())[
                                           str(self.compare4.currentText()).index("[") + 1:str(
                                               self.compare4.currentText()).index("]")])

            if(sessionid > -1):
                txPackets = self.db.getTXPackets(sessionid)
                description = self.db.getDescription(sessionid)
                print txPackets
                self.topology = []
                print os.path.join(str(self.SelectHeatmap_file4.text()))
                csvfile = open(os.path.join(str(self.SelectHeatmap_file4.text())), 'r')
                print csvfile
                spamreader = csv.reader(csvfile, delimiter=',')
                for row in spamreader:
                    self.topology.append(row)
                self.topology = list(self.topology)
                tempResult = self.topology
                counter1 = 0
                counter2 = 0
                for i in range(0,len(self.topology)):

                    counter2 = 0
                    for k in range(0,len(self.topology[i])):
                        if self.topology[i][k] != '':
                            tempResult[i][k] = self.db.getRXPacketsForNode(int(sessionid),self.topology[i][k])
                            if tempResult[i][k] == None:
                                tempResult[i][k] = 0
                            tempResult[i][k] = 100 - ((100/float(txPackets[0])) * float(tempResult[i][k]))
                        else:
                            tempResult[i][k] = 0

                fig = plt.figure()
                ax = fig.add_subplot(111)

                ax.set_title('PLR Heatmap')

                plotly_fig = tls.mpl_to_plotly(fig)

                trace = dict(z=tempResult, type="heatmap", zmin=0, zmax=10)

                plotly_fig['data'] = [trace]

                print plotly_fig
                plotly_fig['layout']['xaxis1'].update({'autorange': True})
                plotly_fig['layout']['yaxis1'].update({'autorange': True})

                plot_url = py.plot(plotly_fig, filename=description[0])

    def drawHeatmap5(self):
        if(self.SelectHeatmap_file5.text() != "" and self.check5.isChecked() == True):
            sessionid = int(str(self.compare5.currentText())[
                                           str(self.compare5.currentText()).index("[") + 1:str(
                                               self.compare5.currentText()).index("]")])

            if(sessionid > -1):
                txPackets = self.db.getTXPackets(sessionid)
                description = self.db.getDescription(sessionid)
                print txPackets
                self.topology = []
                print os.path.join(str(self.SelectHeatmap_file5.text()))
                csvfile = open(os.path.join(str(self.SelectHeatmap_file5.text())), 'r')
                print csvfile
                spamreader = csv.reader(csvfile, delimiter=',')
                for row in spamreader:
                    self.topology.append(row)
                self.topology = list(self.topology)
                tempResult = self.topology
                counter1 = 0
                counter2 = 0
                for i in range(0,len(self.topology)):

                    counter2 = 0
                    for k in range(0,len(self.topology[i])):
                        if self.topology[i][k] != '':
                            tempResult[i][k] = self.db.getRXPacketsForNode(int(sessionid),self.topology[i][k])
                            if tempResult[i][k] == None:
                                tempResult[i][k] = 0
                            tempResult[i][k] = 100 - ((100/float(txPackets[0])) * float(tempResult[i][k]))
                        else:
                            tempResult[i][k] = 0

                fig = plt.figure()
                ax = fig.add_subplot(111)

                ax.set_title('PLR Heatmap')

                plotly_fig = tls.mpl_to_plotly(fig)

                trace = dict(z=tempResult, type="heatmap", zmin=0, zmax=10)

                plotly_fig['data'] = [trace]

                print plotly_fig
                plotly_fig['layout']['xaxis1'].update({'autorange': True})
                plotly_fig['layout']['yaxis1'].update({'autorange': True})

                plot_url = py.plot(plotly_fig, filename=description[0])


    def selectHeatmapFile1(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self, "Open File","","CSV (*.csv)")
        self.SelectHeatmap_file1.setText(fileName)


    def selectHeatmapFile2(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self, "Open File","","CSV (*.csv)")
        self.SelectHeatmap_file2.setText(fileName)


    def selectHeatmapFile3(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self, "Open File","","CSV (*.csv)")
        self.SelectHeatmap_file3.setText(fileName)


    def selectHeatmapFile4(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self, "Open File","","CSV (*.csv)")
        self.SelectHeatmap_file4.setText(fileName)


    def selectHeatmapFile5(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self, "Open File","","CSV (*.csv)")
        self.SelectHeatmap_file5.setText(fileName)


    def get_burst_count(self, experiment_name):

        burst_count = 0

        return burst_count

    def neighUpdate(self):
        self.db.clearTempNeighbourList()
        ser.write("topologyrefresh\n")

    def LQISend(self):
        ser.write("LQI\n")
        ser.write("{0}\n".format(self.db.returnHex(int(self.LQIRadius_text.text()))))

    def TXPowerSend(self):
        ser.write("TXPOWER\n")

        temp = int(self.TXPower_text.text())
        if temp < 0:
            ser.write("NEGATIV\n")
        temp = abs(temp)

        print temp
        ser.write("{0}\n".format(self.db.returnHex(temp)))

    def RSSISend(self):
        ser.write("RSSI\n")
        temp = int(self.RSSIRadius_text.text())
        if temp < 0:
            temp = temp * -1
        ser.write("{0}\n".format(self.db.returnHex(temp)))

    def FlushResults(self):
        ser.write("0x0\n")

    def StartCIDER(self):
        ser.write("STARTCIDER\n")

    def startRequestResults(self):
        print self.neighList
        # for i in range(0,len(neighbourList)):
        self.requestResults(self.neighList[0])

    def SkipResult(self):
        self.NextRequestResult(self.lastAddr)

    def NextRequestResult(self, lastAddr):
        try:

            self.emit(SIGNAL("stopTimer()"))
            self.neighList.remove(str(lastAddr))
            output.append("next index is: {0}, address is {1}".format(0, self.neighList[0]))
            print "{0} results left".format(len(self.neighList))
            self.lastAddr = self.neighList[0];
            self.requestResults(self.neighList[0])
        except IndexError:
            print "All results collected"
            for i in range(0, 5):
                ser.write("0x0\n")
                time.sleep(1)

            self.START_button.setEnabled(True)
            self.NeighUpdate_button.setEnabled(True)
            self.PRINT_button.setEnabled(True)

    def requestResults(self, addr):

        self.emit(SIGNAL("startTimer()"))
        print "request result from: {0}\n".format(addr)
        ser.write("{0}\n".format(addr))

    def printList(self):
        output.append("\n==============================")
        output.append("\tNeighbourList")
        output.append("==============================")
        neighbourList = self.db.getAllNeighbours()
        for i in range(0, len(neighbourList)):
            output.append("Parent: {0}, Child: {1}, Tier: {2}, Colour:{3}".format(
                neighbourList[i][0], neighbourList[i][1], neighbourList[i][2], neighbourList[i][3]))

        output.append("==============================\n")
        self.neighList = self.db.getLinkAddressList()
        print self.neighList
        self.emit(SIGNAL("neighbourList(PyQt_PyObject)"), self.neighList)
        self.neighConnected_label.setText(
            ("Neighbours Connected: {0}").format(len(self.neighList)))

    def experimentFinished(self):
        print "Experiment finished"
        self.db.saveNeighbours()
        time.sleep(2)
        self.startRequestResults()
        self.experiments_combo_update()

    def closeSerial(self):
        ser.close()
        self.CONNECT_button.clicked.connect(self.connectSerial)
        self.CONNECT_button.setText("Connect")

    def connectSerial(self):
        print self.serialPorts_combo.currentText()
        ser.port = str(self.serialPorts_combo.currentText())
        ser.open()
        thread.start_new_thread(receiving, ())
        self.CONNECT_button.clicked.connect(self.closeSerial)
        self.CONNECT_button.setText("Close")

    def STOP(self):  # When the user presses the STOP button, it sends a burst_stop order to the test_thread
        self.experiment_thread_thread.burst_stop_order()

    def START(self):  # Execute a serie of CAST with defined parameters
        # burst is the number of the current burst (for the experiment)
        global burst
        global output
        global experiment_name  # experiment_name is the name of the current experiment
        global delay_queue
        # name_labels is a global list to pass the current experiement names to
        # add a legend on the axes
        global name_labels

        name_labels = []
        temp_plr_y = []
        self.plr_x = [[0]]
        self.plr_y = [[]]

        try:
            burst_number = 0
            cast_number = ""
            interval = ""
            rebroadcast = "0"
            numberBursts = int(self.numberBursts_text.text())
            interval = int(self.interval_combo.currentText())
            msgPerBurst = int(self.msgPerBurst_text.text())
            burst = 0
            experiment_name = str(self.experiment_line.text())
            lastExperimentID = self.db.getLastExperimentID()
            newExperimentID = lastExperimentID + 1
            assert (experiment_name != "")
            # if not ebough information is provided, ends the test and print an
            # error message
        except:  # ------------------PRINT------------------
            print "INVALID INPUT"
            return
        # One cannot name his experiment tables. It would mess up the database
        # organization... and wouldn't make much sens.
        if experiment_name != "tables" and len(self.neighList) != 0:
            self.db.insertExperiment(newExperimentID, experiment_name, int(time.time()))
            self.db.insertSettings(0, self.db.getLastExperimentID(), int(self.TXPower_text.text()), numberBursts,
                                   int((msgPerBurst * interval) / 1000), msgPerBurst,int(self.RSSIRadius_text.text()))

            self.experiment_thread.launching(
                experiment_name, numberBursts, interval, msgPerBurst)

            self.START_button.setEnabled(False)
            self.NeighUpdate_button.setEnabled(False)
            self.PRINT_button.setEnabled(False)
        else:
            # ------------------PRINT------------------
            output.append(
                "'tables' is a reserved name, use another one if you want to conduct an experiment.\n")

    # Draws the current data list in order to make it easier to have latency
    # info
    def latency_draw(self, data):

        if len(data) == 0:
            return
        i = 0
        count = 0.0
        t = 0
        occurence_count = 1

        self.x_list.append([])
        self.y_list.append([])

        while t < self.xmax:
            if data[i] == t:
                count += 1.0
                self.update_line(data[i], count / (len(data)))
                if data.count(data[i]) == occurence_count:
                    t += 1
                    occurence_count = 1
                else:
                    occurence_count += 1
                if i != len(data) - 1:
                    i += 1

            else:
                self.update_line(t, count / (len(data)))
                t += 1
                if t == self.xmax:
                    self.update_line(t, count / (len(data)))

        self.plot()

    # Updates the current list of points to be drawn with x_data and y_data
    def update_line(self, new_x_data, new_y_data):
        self.x_list[len(self.x_list) - 1].append(new_x_data)
        self.y_list[len(self.y_list) - 1].append(new_y_data)

    def plot(self):  # Plots the contents of x_list and y_list and updates the canvas
        x_99 = 0
        y_99 = 0.0
        y_200 = 0.0
        self.xmax = []
        self.xmin = []
        self.axes_latency.clear()
        self.axes_plr.clear()
        for i in range(0, len(self.x_list)):
            if self.x_list[i] != []:
                self.xmax.append(max(self.x_list[i]))
                # self.xmin.append(min(self.x_list[i]))
                self.y_list[i] = [x * 100 for x in self.y_list[i]]
                self.axes_latency.plot(self.x_list[i], self.y_list[i], linewidth=1)  # , label=name_labels[i]

        self.axes_latency.legend(self.PlotLegend,loc='upper center', bbox_to_anchor=(0.5, -0.05),fancybox=True, shadow=True, ncol=5)

        for i in range(len(self.x_list)):
            if self.x_list[i] != []:
                # for j in range(len(self.x_list[i])):
                #     if self.y_list[i][j] >= 99:
                #         y_99 = self.y_list[i][j]
                #         x_99 = self.x_list[i][j]
                #         break
                # for j in range(len(self.x_list[i])):
                #     if self.x_list[i][j] >= 240:
                #         y_200 = self.y_list[i][j]
                #         break
                # if (y_200 == 0):
                #     y_200 = 1
                # self.axes_latency.plot([240, 240], [0.0, 100.0], label="".format(
                #     y_200 * 100))

                #self.axes_latency.set_title("240ms: {0:.2f} %, 99%: {1}ms".format(y_200, x_99))
                self.axes_latency.set_title("Latency")
                self.axes_latency.set_xlabel("latency [ms]")
                self.axes_latency.set_ylabel(r"$F_x(x)$ [%]")
        if (max(self.xmax) < 200):
            self.xmax = 200
        else:
            self.xmax = max(self.xmax)

        self.axes_latency.set_xlim([0, self.xmax])

       # self.axes_latency.legend(loc='lower right')
        self.canvas_latency.draw()

        print self.plr_x
        prop_iter = iter(plt.rcParams['axes.prop_cycle'])
        for i in range(0, len(self.plr_x)):
            print self.plr_x[i]
            print self.plr_y[i]

            self.axes_plr.bar(self.plr_x[i] + 1, self.plr_y[i], align='center',color=next(prop_iter)['color'])
            self.axes_plr.set_title("Packet Loss Rate")
            self.axes_plr.set_xlabel("Number Experiment")
            self.axes_plr.set_ylabel("[%]")
            self.axes_plr.legend(self.PlotLegend, loc='upper center', bbox_to_anchor=(0.5, -0.05),fancybox=True, shadow=True, ncol=5)
            # self.axes_plr.xticks(self.plr_y[i] + 1, self.plr_y[i])

        # To add labels on top of the bars to show the precise plr, rects and
        # labels are used
        rects = self.axes_plr.patches

        labels = []
        for i in range(0, len(self.plr_x)):
            labels.append("{0:.2f} %".format(self.plr_y[i]))
        print labels
        for rect, label in zip(rects, labels):
            print rect
            print label
            height = rect.get_height()
            self.axes_plr.text(rect.get_x() + rect.get_width() / 2,
                               height + 2, label, ha='center', va='bottom')
        self.axes_plr.set_ylim([0, max(self.plr_y) + 5])
        plt.show()
        self.canvas_plr.draw()

    def window_reset(self):  # Clears the current axes and reset the axis and title parameters
        self.axes_latency.cla()
        ymax = 1.05
        self.axes_latency.set_xlim([0, self.xmax])
        self.axes_latency.set_ylim([0, ymax])
        self.axes_latency.set_title("Percentage of received data versus time")
        self.axes_latency.set_xlabel("time (ms)")
        self.axes_latency.set_ylabel("Data received ")

        self.axes_plr.cla()
        max_burst = 1
        for i in range(len(self.plr_x)):
            if len(self.plr_x[i]) != 0:
                if max(self.plr_x[i]) >= max_burst:
                    max_burst = max(self.plr_x[i]) + 1
        self.axes_plr.set_xlim([0, max_burst])
        self.axes_plr.set_ylim([0, 100])
        self.axes_plr.set_title("Package Loss Rate")
        self.axes_plr.set_xlabel("Experiment")
        self.axes_plr.set_ylabel("PLR (%)")

        self.canvas_latency.draw()
        self.canvas_plr.draw()


def data_backup(mode):  # Saves the data list in 'mode' mode
    global data

    if (len(data) > 0):
        data_file = open(
            "C:\\Users\\R00145386\\Desktop\\clement.festal\\Notes\\Scripts\\Backup\\data.txt", mode)
        data_file.write("\n------------------------\n")
        data_file.write(datetime.datetime.now().strftime(
            "%d/%m/%Y %Ih%Mm00") + "\n\n")
        for i in range(0, len(data)):
            data_file.write(data[i] + "\n")
        data_file.close()


# MAIN FUNCTION


def main():
    try:
        global node_list
        global data
        global output  # output is the buffer that will store the serial output while it's not printed in the window

        output = []
        node_list = []
        data = []
        i = 0  # ------------------------------------------------------
        # This block is use to load the python list list[]
        elem = "elem"  # with the short adress of the devices inside

        ser.isOpen()

        app = QtGui.QApplication(sys.argv)
        mainwindow = MainWindow()

        #        thread.start_new_thread (store,( ))
        thread.start_new_thread(sys.exit, (app.exec_(),))

    finally:

        # When interrutping the programm, the list has to be saved in a file
        print("Closing before leaving!")
        ser.close()


if __name__ == '__main__':
    main()
