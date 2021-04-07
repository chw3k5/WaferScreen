import u3
import time
import os
from datetime import datetime
from typing import NamedTuple
from functools import partial
from tkinter import *
from tkinter import ttk


class U3:
    def __init__(self, auto_init=True, verbose=True, local_id=None):
        self.verbose = verbose
        self.local_id = local_id
        self.lj = None
        self.is_open = False

        self.num_channels = 1
        self.sample_frequency_hz = 5000
        self.voltage_resolution = 0
        self.stream_file = ""
        self.sample_time_s = 10

        if auto_init:
            self.open()

    def open(self):
        self.lj = u3.U3(autoOpen=False)
        self.lj.open(localId=self.local_id)
        self.is_open = True

    def close(self):
        self.lj.close()
        self.is_open = False

    def write(self, register, write_val):
        self.lj.writeRegister(register, write_val)

    def daq(self, voltage, daq_num=0):
        register_num = 5000 + (2 * daq_num)
        self.lj.writeRegister(register_num, voltage)

    def ain(self, ain_number=0):
        return self.lj.readRegister(ain_number)

    def led(self, led_on=True):
        if led_on in {True, 1, '1'}:
            self.lj.writeRegister(6004, 0)
            if self.verbose:
                print("LED: ON")
        else:
            self.lj.writeRegister(6004, 1)
            if self.verbose:
                print("LED: OFF")

    def alive_test(self, voltage=0.0, sleep_time=0.2, zero_after=True):
        voltage = float(voltage)
        self.daq(voltage=voltage)
        if self.verbose:
            print("Jumper DAQ0 and AIN0 for this test.")
            print(F"  DAQ0 writen to have a voltage of {voltage} Volts.")
        time.sleep(sleep_time)
        if self.verbose:
            print(F"  AIN0 reads: {self.ain()} Volts\n")
        if zero_after and voltage != 0.0:
            time.sleep(sleep_time)
            self.daq(voltage=0.0)
            if self.verbose:
                print('  Voltage reset to 0 Volts')

    def say_hello(self, jumper_test=True, led_test=False, voltage=1.5):
        if jumper_test:
            self.daq(voltage=voltage)
            if self.verbose:
                print("Jumper DAQ0 and AIN0 for this test.")
                print(F"  DAQ0 writen to have a voltage of {voltage} Volts.")
            time.sleep(0.2)
            if self.verbose:
                print(F"  AIN0 reads: {self.ain()} Volts\n")

        if led_test:
            for on_time in [0.1, 0.1, 0.2, 0.3, 0.5, 0.8, 1.3]:
                self.led(led_on=True)
                time.sleep(on_time)
                self.led(led_on=False)
                time.sleep(0.2)
            else:
                self.led(led_on=True)

    def stream_config(self, num_channels=1, sample_frequency_hz=5000, voltage_resolution=0, sample_time_s=10, stream_file=""):
        self.num_channels = num_channels
        self.sample_frequency_hz = sample_frequency_hz
        self.voltage_resolution = voltage_resolution
        self.stream_file = stream_file
        self.sample_time_s = sample_time_s

    def stream(self, num_channels=None, sample_frequency_hz=None, voltage_resolution=None, sample_time_s=None,
               stream_file=None):
        if num_channels is not None:
            self.num_channels = num_channels
        if sample_frequency_hz is not None:
            self.sample_frequency_hz = sample_frequency_hz
        if voltage_resolution is not None:
            self.voltage_resolution = voltage_resolution
        if stream_file is not None:
            self.stream_file = stream_file
        if sample_time_s is not None:
            self.sample_time_s = sample_time_s
        """
        voltage_resolution = 0 # 0,1,2, or 3 () is highest resolution, 3 is the lowest)
        """
        self.lj.streamConfig(NumChannels=self.num_channels,
                             PChannels=range(self.num_channels),
                             NChannels=[31 for x in range(self.num_channels)],
                             Resolution=self.voltage_resolution,
                             SampleFrequency=self.sample_frequency_hz)

        if not os.path.isfile(self.stream_file):
            with open(self.stream_file, 'w') as f:
                f.write("frequency=%d" % self.sample_frequency_hz)
                wavenames = ['wave%d' % n for n in range(self.num_channels)]
                f.write('\t'.join(wavenames) + '\n')

        # start the stream
        self.lj.streamStart()
        loop = 0

        try:
            finished = False
            start = time.time()
            while not finished:
                self.get_stream()
                loop += 1
                diff_time = time.time() - start
                if self.sample_time_s < diff_time:
                    finished = True
                if self.verbose:
                    print("[%.4d %.2f s]" % (loop, diff_time))
                    # print "start time", start
                    # print 'Sample Time', SampleTime
                    # print 'diff time', diff_time
        finally:
            self.lj.streamStop()
        return

    def get_stream(self):
        try:
            for buffer_data in self.lj.streamData():
                if buffer_data is not None:
                    if buffer_data['errors'] or buffer_data['numPackets'] != self.lj.packetsPerRequest or buffer_data['missed']:
                        print("error: errors = '%s', numpackets = %d, missed = '%s'" % (
                        buffer_data['errors'], buffer_data['numPackets'], buffer_data['missed']))
                    break
        finally:
            pass
        with open(self.stream_file, 'a') as f:
            chans = [buffer_data['AIN%d' % n] for n in range(self.num_channels)]
            for i in range(len(chans[0])):
                f.write("\t".join(['%.6f' % c[i] for c in chans]) + '\n')


class ValvesStatus(NamedTuple):
    valve1: bool
    valve2: bool

    def __str__(self):
        status_str = ""
        for valve_status, valve_name in [(self.valve1, 'Valve 1'), (self.valve2, 'Valve 2')]:
            if valve_status:
                open_or_closed = "'OPEN'"
            else:
                open_or_closed = "'closed'"
            status_str += F"  {valve_name} is {open_or_closed}\n"
        return status_str


class VacuumControlLJ(U3):
    def __init__(self, auto_init=True, verbose=True):
        self.verbose = verbose
        self.local_id = 3
        self.lj = None
        self.is_open = False

        self.num_channels = 1
        self.sample_frequency_hz = 5000
        self.voltage_resolution = 0
        self.stream_file = ""
        self.sample_time_s = 10

        self.valves_status = ValvesStatus(valve1=True, valve2=True)
        self.forbidden_statuses = {ValvesStatus(valve1=True, valve2=True), }
        self.valve_name_to_daq_num = {"valve1": 0, "valve2": 1}
        self.valve1_aliases = {"valve1", "valve 1", "green", '1', 'one', 'valve one'}
        self.valve2_aliases = {"valve2", "valve 2", "blue", 'white', '2', 'two', 'valve two'}
        self.all_valve_names = self.valve1_aliases | self.valve2_aliases

        if auto_init:
            self.open()
        for valve_name in list(self.valves_status._fields):
            self.move_valve(user_valve_name=valve_name, open_valve=False)

    def open_all(self):
        for valve_name in list(self.valves_status._fields):
            self.daq(voltage=5, daq_num=self.valve_name_to_daq_num[valve_name])

    def close_all(self):
        for possible_valve_name in list(self.valves_status._fields):
            self.daq(voltage=0, daq_num=self.valve_name_to_daq_num[possible_valve_name])

    def move_valve(self, user_valve_name, open_valve=False):
        formatted_value_name = str(user_valve_name).lower().strip()
        if formatted_value_name not in self.all_valve_names:
            raise KeyError(F"Valve name {user_valve_name} is not of the expected types:\n{self.all_valve_names}")
        elif formatted_value_name in self.valve1_aliases:
            internal_valve_name = 'valve1'
        else:
            internal_valve_name = 'valve2'
        valve_current_state = self.valves_status.__getattribute__(internal_valve_name)
        proposed_status_list = []
        for possible_valve_name in list(self.valves_status._fields):
            if possible_valve_name == internal_valve_name:
                proposed_status_list.append(open_valve)
            else:
                proposed_status_list.append(self.valves_status.__getattribute__(possible_valve_name))

        proposed_status = ValvesStatus(*proposed_status_list)
        if open_valve:
            voltage = 5
            command_type = "open"
        else:
            voltage = 0
            command_type = 'close'
        if valve_current_state == open_valve:
            print(F"\nA command was set to {command_type} {internal_valve_name},\n")
            print(F"but the valves status is indicated that {internal_valve_name} is already currently {command_type}.")
        elif proposed_status in self.forbidden_statuses:
            print(F"\nA command to {command_type} {internal_valve_name},\n")
            print("but this would lead to the forbidden command state:")
            print(str(proposed_status))
            print("Command REJECTED")
        else:
            self.daq(voltage=voltage, daq_num=self.valve_name_to_daq_num[internal_valve_name])
            self.valves_status = proposed_status
            if self.verbose:
                print(F"A '{command_type}' command was issued to the '{internal_valve_name}' valve.")
                print(F"The current valve status is ({datetime.now()}):")
                print(self.valves_status)


class VacuumInterface:
    exchange_cycle_time = 0.5
    button_width = 30
    button_height = 6

    def __init__(self, root, debug_mode=False):
        self.debug_mode = debug_mode
        if self.debug_mode:
            self.vacuum_control_lj = None
        else:
            self.vacuum_control_lj = VacuumControlLJ()

        # create a frame to hold the contents of the application
        root.title("Vacuum Controller")

        # define the main window Frame, it takes up the entire window
        self.mainframe = ttk.Frame(root, padding=(3, 3, 12, 12))  # (left, top, right, bottom)
        self.mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.mainframe.columnconfigure(0, weight=1)
        self.mainframe.columnconfigure(1, weight=1)

        # Initialize variables to track the valve states
        self.valve1_is_open = BooleanVar(value=False)
        self.exchange_valve_was_opened = BooleanVar(value=False)
        self.text_valve1_label = StringVar()
        self.text_valve2_label = StringVar()
        self.text_valve1_button = StringVar()

        # Valve 1 - The vent valve
        self.valve1_label = ttk.Label(self.mainframe, textvariable=self.text_valve1_label)
        self.valve1_label.grid(column=0, row=0, sticky=W)
        self.valve1_button = ttk.Button(self.mainframe, textvariable=self.text_valve1_button,
                                        command=self.change_vent_valve,
                                        width=self.button_width)
        self.valve1_button.grid(column=0, row=1, sticky=W)

        # Valve 2 - the heat exchange valve
        self.valve2_label = ttk.Label(self.mainframe, textvariable=self.text_valve2_label)
        self.valve2_label.grid(column=1, row=0, sticky=E)
        self.valve2_button = ttk.Button(self.mainframe, text="Cycle Exchange Gas Valve",
                                        command=self.exchange_valve_confirm,
                                        width=self.button_width)
        self.valve2_button.grid(column=1, row=1, sticky=E)

        # add some padding for each cell in the mainframe's grid
        for child in self.mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)

        # make sure the valves are close by default
        self.close_vent_valve()
        self.close_exchange_valve()

    def change_vent_valve(self):
        if self.valve1_is_open.get():
            self.close_vent_valve()
        else:
            self.vent_valve_confirmation()

    def close_vent_valve(self):
        if self.debug_mode:
            print("Debug Mode:\n  Simulated Vent Close Command")
        else:
            self.vacuum_control_lj.move_valve(user_valve_name='valve1', open_valve=False)
        self.text_valve1_label.set("The Vent Valve is Closed")
        self.text_valve1_button.set("Open Vent Valve")
        self.valve1_is_open.set(value=False)
        if not self.exchange_valve_was_opened.get():
            self.valve2_button.state(['!disabled'])

    def open_vent_valve(self, root_vv_popup):
        if self.debug_mode:
            print("Debug Mode:\n  Simulated Vent Open Command")
        else:
            self.vacuum_control_lj.move_valve(user_valve_name='valve1', open_valve=True)
        root_vv_popup.destroy()
        self.text_valve1_label.set("The Vent Valve is Open")
        self.text_valve1_button.set("Close Vent Valve")
        self.valve1_is_open.set(value=True)
        self.valve2_button.state(['disabled'])

    def vent_valve_confirmation(self):
        root_vv_popup = Toplevel()
        mainframe_vv_popup = ttk.Frame(root_vv_popup, padding=(3, 3, 12, 12))
        mainframe_vv_popup.grid(column=0, row=0, sticky=(N, W, E, S))
        root_vv_popup.columnconfigure(0, weight=1)
        root_vv_popup.rowconfigure(0, weight=1)

        vv_text = "Confirm that you want to open the Vent Valve.\n"
        vv_text += "Open this valve to start/continue pumping the cryostat\n"
        vv_text += "or to vent the cryostat to atmosphere."
        vv_label = ttk.Label(mainframe_vv_popup, text=vv_text)
        vv_label.grid(column=0, row=0, columnspan=2)
        cancel_button = ttk.Button(mainframe_vv_popup, text="\nCancel", command=root_vv_popup.destroy,
                                   width=self.button_width)
        cancel_button.grid(column=0, row=1)
        cancel_button.state(['active'])
        confirm_button = ttk.Button(mainframe_vv_popup, text="Confirm\nOpen",
                                    command=partial(self.open_vent_valve, root_vv_popup),
                                    width=self.button_width)
        confirm_button.grid(column=1, row=1)

    def close_exchange_valve(self):
        if self.debug_mode:
            print("Debug Mode:\n  Simulated Exchange Valve Closed Command")
        else:
            self.vacuum_control_lj.move_valve(user_valve_name='valve2', open_valve=False)
        self.text_valve2_label.set("Gas Exchange Valve is Closed")
        self.valve1_button.state(['!disabled'])

    def cycle_exchange_valve(self, root_ex_popup):
        # open the valve to let exchange gas into the cryostat
        if self.debug_mode:
            print("Debug Mode:\n  Simulated Exchange Valve Open Command")
        else:
            self.vacuum_control_lj.move_valve(user_valve_name='valve2', open_valve=True)
        # kill the pop up window and record the current valve state, and disable the valve 1 open button
        root_ex_popup.destroy()
        self.text_valve2_label.set("Gas Exchange Valve is Open")
        self.exchange_valve_was_opened.set(value=True)
        self.valve1_button.state(['disabled'])
        # sleep for the cycle time
        time.sleep(self.exchange_cycle_time)
        # close the valve to complete the exchange gas cycle and disable the valve 2 button from being used again.
        self.close_exchange_valve()
        self.valve2_button.state(['disabled'])

    def exchange_valve_confirm(self):
        root_ex_popup = Toplevel()
        mainframe_ex_popup = ttk.Frame(root_ex_popup, padding=(3, 3, 12, 12))
        mainframe_ex_popup.grid(column=0, row=0, sticky=(N, W, E, S))
        root_ex_popup.columnconfigure(0, weight=1)
        root_ex_popup.rowconfigure(0, weight=1)

        ex_text = "Confirm that you want to Cycle the Thermal Exchange Gas Valve.\n"
        ex_text += F"The Cycle will last Open the Exchange Gas Valve for:\n"
        ex_text += F"   {self.exchange_cycle_time} seconds and then close.\n"
        ex_text += "It is expected that this valve has been filled with gas phase Helium\n"
        ex_text += "    and the valve is currently capped.\n"
        ex_label = ttk.Label(mainframe_ex_popup, text=ex_text)
        ex_label.grid(column=0, row=0, columnspan=2)
        cancel_button = ttk.Button(mainframe_ex_popup, text="\nCancel", command=root_ex_popup.destroy,
                                   width=self.button_width)
        cancel_button.grid(column=0, row=1)
        cancel_button.state(['active'])
        confirm_button = ttk.Button(mainframe_ex_popup, text="Confirm\nCycle",
                                    command=partial(self.cycle_exchange_valve, root_ex_popup),
                                    width=self.button_width)
        confirm_button.grid(column=1, row=1)


if __name__ == "__main__":
    a_root = Tk()
    vac_interface = VacuumInterface(root=a_root, debug_mode=False)
    a_root.mainloop()
