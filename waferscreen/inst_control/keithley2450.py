import os
import sys
import time
import socket
import serial

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


def read_lan(lan_device, termination=b'\n', buffer=1000):
    all_data = b""
    while all_data == b"" or all_data[-1:] != termination:
        all_data += lan_device.recv(buffer)
    return all_data[:-1]


def number_format(number):
    if sys.version_info.major == 3:
        formatted = bytes(str('%1.6e' % number), "UTF-8")
    else:
        formatted = str("%1.6e" % number)
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
            return read_lan(lan_device=self.device, buffer=self.buffer)
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

    def get_volt(self):
        self.write(write_str=b'MEAS:VOLT?\n')
        return_str = self.read()
        voltage = float(return_str)
        if self.verbose:
            print(F"{voltage} is the read voltage from the Keithley 2450")
        return voltage

    def set_volt(self, voltage):
        self.write(write_str=b"SENS:FUNC VOLT\n")
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
        self.write(write_str=b"SOUR:FUNC CURR\n")
        write_str = b":SOUR:CURR " + number_format(current_amps) + b"\n"
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

    def init_sweep(self):
        self.write(write_str=b"*RST")
        self.write(write_str=b'''SENS: FUNC "VOLT"''')
        self.write(write_str=b":SENS:RES:RANG:AUTO ON")

    def get_range_keithley2450(self):
        write_str = b":CURR:RANG?\n"
        self.write(write_str=write_str)
        the_range = self.read()
        if self.verbose:
            print(the_range, "is the current RANGE from the Keithley 2450")
        return the_range

    def zero(self):
        self.set_volt(voltage=0.0)

    def startup(self):
        self.open()
        self.zero()
        self.output_on()
    
    def __enter__(self):
        self.startup()

    def shutdown(self):
        self.zero()
        self.output_off()
        self.close()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.shutdown()


if __name__ == "__main__":
    keithley2450 = Keithley2450(connection_type='lan', verbose=True)
    keithley2450.startup()
    keithley2450.init_sweep()
    keithley2450.shutdown()

