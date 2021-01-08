import u3
import time
import os
from datetime import datetime
from typing import NamedTuple


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
            self.move_valve(valve_name=valve_name, open_valve=False)

    def open_all(self):
        for valve_name in list(self.valves_status._fields):
            self.daq(voltage=5, daq_num=self.valve_name_to_daq_num[valve_name])

    def close_all(self):
        for valve_name in list(self.valves_status._fields):
            self.daq(voltage=0, daq_num=self.valve_name_to_daq_num[valve_name])

    def move_valve(self, valve_name, open_valve=False):
        formatted_value_name = str(valve_name).lower().strip()
        if formatted_value_name not in self.all_valve_names:
            raise KeyError(F"Valve name {valve_name} is not of the expected types:\n{self.all_valve_names}")
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
                proposed_status_list.append(self.valves_status.__getattribute__(valve_name))
        
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


if __name__ == "__main__":
    vc = VacuumControlLJ()
    # vc.move_valve(valve_name='valve1', open_valve=True)

