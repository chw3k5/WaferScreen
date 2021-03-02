import os
import sys
import time
import socket
import serial
import numpy as np

"""
This is for the Keithley 2450 source meter.
This is designed to be platform independent.
"""


# These are definitions that are used by many methods in the Keithley2450 class below.
def read_serial(serial_device):
    if sys.version_info.major == 3:
        one_byte = b""
        byte_string = b""
        while one_byte != b'\n':
            one_byte = serial_device.read()
            byte_string += one_byte
    else:
        one_byte = None
        byte_string = ""
        while one_byte != "":
            one_byte = serial_device.read()
            byte_string += one_byte
    return byte_string


def read_single_lan(lan_device, termination=b'\n', buffer=10000):
    all_data = b""
    while all_data == b"" or all_data[-1:] != termination:
        all_data += lan_device.recv(buffer)
    return all_data[:-1]


def read_all_lan(lan_device):
    return lan_device.recv(1000000)


def number_format(number):
    if isinstance(number, int):
        formatted_str = str('%i' % number)
    elif isinstance(number, float):
        sci_notation = str('%e' % number)
        float_part, power_part = sci_notation.split("e")
        power_int = int(power_part) - 3
        float_part_int = int(float(float_part) * 1000.0)
        if float_part_int == 0:
            formatted_str = '0'
        else:
            formatted_str = str(float_part_int) + "e" + str(power_int)
    else:
        formatted_str = number
    formatted = bytes(formatted_str, "UTF-8")
    return formatted


"""
This is the class to control the Keithley 2450
"""


class Keithley2450:
    def __init__(self, connection_type='lan', port_name='COM2', source_mode='current', verbose=False):
        self.connection_type = connection_type.lower().strip()
        if connection_type not in {"lan", 'serial'}:
            raise TypeError(F"connection_type: {self.connection_type}, is not recognized.")
        self.source_mode = source_mode.lower().strip()
        if self.source_mode not in {"current", 'voltage'}:
            raise TypeError(F"source_mode type: {self.source_mode}, is not recognized.")
        self.device = None
        self.keithley_source_mode = None
        self.keithley_sense_mode = None
        self.source_range = None
        self.sense_range = None
        self.timeout = 2
        self.verbose = verbose
        if self.connection_type == 'lan':
            # IP address information for the Vacuum Gauge
            self.ip = '169.254.21.224'
            self.gateway = '169.254.21.224'
            self.subnet = '255.255.0.0'
            self.port = 5025
            self.buffer = 10000
        elif self.connection_type == "serial":
            self.port_name = port_name
            self.baudrate = 57600
            self.bytesize = 8
            self.stopbits = 1
            self.parity = "N"
            self.fullDataPath = None

    def open(self):
        if self.connection_type == 'lan':
            self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.device.connect((self.ip, self.port))
        elif self.connection_type == "serial":
            self.device = serial.Serial(port=self.port_name,
                                        baudrate=self.baudrate,
                                        bytesize=self.bytesize,
                                        stopbits=self.stopbits,
                                        parity=self.parity,
                                        timeout=self.timeout)
            
    def read(self):
        if self.connection_type == 'lan':
            return read_single_lan(lan_device=self.device)
        elif self.connection_type == 'serial':
            return read_serial(serial_device=self.device)
        
    def write(self, write_str):
        if self.connection_type == 'lan':
            self.device.send(write_str)
        elif self.connection_type == 'serial':
            self.device.write(write_str)
        
    def close(self):
        self.device.close()

    def output_on(self):
        self.write(write_str=b"OUTPUT ON\n")
        if self.verbose:
            print("The output for the Keithley 2450 has been set to ON")

    def output_off(self):
        self.write(write_str=b"OUTPUT OFF\n")
        if self.verbose:
            print("The output for the Keithley 2450 has been set to OFF")

    def reset(self):
        self.write(write_str=b"*RST\n")

    def set_source_type(self, source_type=None, sense_type=None, v_range=b'2', i_range=b'100e-3'):
        if source_type is None:
            source_type = self.source_mode
        self.source_mode = source_type
        if self.source_mode == "current":
            self.keithley_source_mode = b"CURR"
            self.source_range = i_range
            if sense_type is None or sense_type != "current":
                self.keithley_sense_mode = b"VOLT"
                self.sense_range = v_range
            else:
                self.keithley_sense_mode = b"CURR"
                self.sense_range = i_range
        elif self.source_mode == "voltage":
            self.keithley_source_mode = b"VOLT"
            self.source_range = v_range
            if sense_type is None or sense_type != "voltage":
                self.keithley_sense_mode = b"CURR"
                self.sense_range = i_range
            else:
                self.keithley_sense_mode = b"VOLT"
                self.sense_range = v_range
        else:
            raise TypeError(F"source_mode type: {self.source_mode}, is not recognized.")

        self.write(write_str=b"SOUR:FUNC " + self.keithley_source_mode + b"\n")
        self.write(write_str=b"SOUR:" + self.keithley_source_mode + b":RANG " + self.source_range + b"\n")
        self.write(write_str=b"SENS:FUNC \"" + self.keithley_sense_mode + b"\"\n")
        if self.keithley_source_mode != self.keithley_sense_mode:
            self.write(write_str=b"SENS:" + self.keithley_sense_mode + b":RANG " + self.sense_range + b"\n")
        # activated the 4 wire measurements
        self.write(write_str=b"SENS:" + self.keithley_sense_mode + b":RSEN ON\n")

    def get_volt(self):
        self.write(write_str=b'MEAS:VOLT?\n')
        return_str = self.read()
        voltage = float(return_str)
        if self.verbose:
            print(F"{voltage} is the read voltage from the Keithley 2450")
        return voltage

    def set_volt(self, voltage):
        write_str = b":SOUR:VOLT " + number_format(voltage) + b"\n"
        self.write(write_str=write_str)
        if self.verbose:
            print("Keithley 2450 was set to a voltage of", voltage)

    def get_current(self):
        self.write(write_str=b'SOUR:CURR?\n')
        current = float(self.read())
        if self.verbose:
            print(current, "is the read current from the Keithley 2450")

    def set_current(self, current_amps):
        write_str = b"SOUR:CURR " + number_format(current_amps) + b"\n"
        self.write(write_str=write_str)
        if self.verbose:
            print("Keithley 2450 was set to a current of", current_amps, "Amps")

    def test_output_on_off(self, sleep_time=10):
        self.open()
        self.output_on()
        print(F"sleeping for {sleep_time} seconds...")
        time.sleep(sleep_time)
        keithley2450.output_off()
        keithley2450.close()

    def init_sweep(self, v_limit=b"5.0", i_limit=b"0.100"):
        self.write(write_str=b"SOUR: " + self.keithley_source_mode + b":VLIM " + number_format(v_limit) + b"\n")
        self.write(write_str=b"SOUR: " + self.keithley_source_mode + b":ILIM " + i_limit + b"\n")

    def sweep(self, start_curr=-0.001, stop_curr=0.001, num_points=21, delay_s=0.1):
        """
        :SOURce[1]:SWEep:<function>:LINear:STEP <start>, <stop>, <steps>, <delay>, <count>,
        <rangeType>, <failAbort>, <dual>, "<bufferName>"
        SOUR:SWE:CURR:LIN:STEP -1.05, 1.05, .25, 10e-3, 1, FIXED
        """
        step_cur = (stop_curr - start_curr) / (num_points - 1.0)
        sweep_base_str = b"SOUR:SWE:" + self.keithley_source_mode + b":LIN "
        start_curr_str = number_format(start_curr) + b", "
        stop_curr_str = number_format(stop_curr) + b", "
        num_points_str = number_format(num_points) + b", "
        delay_s_str = number_format(delay_s) + b", "
        loop_count = number_format(1) + b", "
        range_type = b"FIXED, "
        fail_abort = b"OFF, "
        dual = b"ON, "
        buffer_name = b'''\"defbuffer1\"'''
        # calculations
        sweep_array_a = np.arange(start_curr, stop_curr + (step_cur / 2.0), step_cur)
        sweep_str = sweep_base_str + start_curr_str + stop_curr_str + num_points_str + delay_s_str + loop_count
        sweep_str += range_type + fail_abort + dual + buffer_name + b"\n"
        self.write(write_str=sweep_str)
        self.write(write_str=b"INIT\n")
        if self.verbose:
            print(F"Sweeping:\n   start_curr:{'%1.3f' % (1000 * start_curr)}mA, stop_current:{'%1.3f' % (1000 * stop_curr)}mA, num_points{num_points}")
        self.write(write_str=b"*WAI\n")
        get_sweep_str = b"TRAC:DATA? 1, " + bytes(str(len(sweep_array_a)), "UTF-8") + b", " + buffer_name + b", "
        get_sweep_str += b"SOUR, READ\n"
        self.write(write_str=get_sweep_str)
        split_binary_data = self.read().strip().split(b',')
        meas_data = np.array([float(v_point) for v_point in split_binary_data])
        output_data = []
        for set_point_index, set_point in list(enumerate(sweep_array_a)):
            meas_index = 2 * set_point_index
            meas_a = meas_data[meas_index]
            meas_v = meas_data[meas_index + 1]
            output_data.append((set_point, meas_a, meas_v))
        return output_data

    def get_range_keithley2450(self):
        write_str = b":" + self.keithley_source_mode + b":RANG?\n"
        self.write(write_str=write_str)
        the_range = self.read()
        if self.verbose:
            print(the_range, "is the current RANGE from the Keithley 2450")
        return the_range

    def zero(self):
        if self.source_mode == "current":
            self.set_current(current_amps=0.0)
        else:
            self.set_volt(voltage=0.0)

    def startup(self):
        self.open()
        self.reset()
    
    def __enter__(self):
        self.startup()

    def shutdown(self):
        self.output_off()
        self.close()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.shutdown()


if __name__ == "__main__":
    keithley2450 = Keithley2450(connection_type='lan', source_mode="current", verbose=True)
    keithley2450.startup()
    keithley2450.set_source_type(v_range=b"2e-2", i_range=b"100e-6")
    sweep_data = keithley2450.sweep()
    keithley2450.shutdown()

