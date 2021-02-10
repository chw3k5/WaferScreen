import visa
import time
import serial
from collections import deque
from waferscreen.tools.timer import timer


def srs_parse(raw_string):
    parse_trigger = False
    number_of_prefix_bits = -1
    prefix = ""
    number_of_message_bits = -1
    message = ""
    for character in list(raw_string):
        if parse_trigger:
            if number_of_prefix_bits == -1:
                number_of_prefix_bits = int(character)
            elif number_of_prefix_bits > len(prefix):
                prefix += character
                if number_of_prefix_bits == len(prefix):
                    number_of_message_bits = int(prefix)
            elif number_of_message_bits > len(message):
                message += character
        if character == "#":
            parse_trigger = True
    return message

def get_srs(address):
    if isinstance(address, str):
        return SRS_Connect(address=address)
    else:
        return SRS_Connect(com_num=address)

def get_star_srs(is_gpib=False):
    if is_gpib:
        return get_srs(address="GPIB0::16::INSTR")
    else:
        return get_srs(address=5)


def get_test_srs(is_gpib=True):
    if is_gpib:
        return get_srs(address="GPIB0::17::INSTR")
    else:
        return get_srs(address=2)


class SRS_Connect:
    def __init__(self, com_num=None, address="GPIB0::17::INSTR"):
        if com_num is None:
            self.ResourceManager = visa.ResourceManager()
            self.ctrl = self.ResourceManager.open_resource("%s" % address, write_termination='\n')
            self.ctrl.timeout = 10
            self.is_gpib = True
            self.mainframe_id = address
        else:
            baud_rate = '115200'
            self.ctrl = serial.Serial()
            self.ctrl.baudrate = baud_rate
            self.ctrl.port = F"COM{com_num}"
            self.ctrl.open()
            self.is_open = self.ctrl.is_open
            self.is_gpib = False
            self.mainframe_id = self.ctrl.port

    def close(self):
        self.ctrl.close()
        print(F"Connection to the {self.mainframe_id} is closed.")


class SRS_Module:
    """ Basic communication with the an SRS module """
    def __init__(self, srs_port, srs_connect, in_a_hurry=False):
        self.device_id = None
        self.srs_port = str(srs_port)
        self.is_gpib = srs_connect.is_gpib
        self.ctrl = srs_connect.ctrl
        # SRS SIM 928 Settings
        self.voltage_precision = '5'
        self.voltage_format_str = '%1.' + self.voltage_precision + 'e'
        self.last_set_voltage = None
        # connection test
        if not in_a_hurry:
            self.say_hello()

    def write(self, write_str):
        if self.is_gpib:
            self.ctrl.write(write_str)
        else:
            write_str += "\n"
            b_str = write_str.encode("utf-8")
            self.ctrl.write(b_str)

    def read_serial(self):
        resp = ""
        while resp == "" or resp[-1] != "\n":
            binary_character = self.ctrl.read()
            resp += binary_character.decode(encoding="utf-8")
        return resp

    def try_query(self, query_str):
        if self.is_gpib:
            resp = self.ctrl.query(query_str)
        else:
            self.write(write_str=query_str)
            resp = self.read_serial()
        return srs_parse(raw_string=resp)

    def query(self, query_str):
        count = 0
        msg = ""
        while (msg == "" or msg[-1] != '\n') and count < 10 :
            count += 1
            if count > 5:
                time.sleep(0.1)
            msg += self.try_query(query_str=query_str)
        return msg.strip()

    def write_to_port(self, write_str):
        to_port_write_str = 'SNDT' + self.srs_port + ',\"' + write_str + '\"'
        self.write(write_str=to_port_write_str)

    def query_from_port(self, write_to_port_str, len_str):
        question = 'GETN?'
        from_port_query_str = question + str(self.srs_port) + ',' + str(len_str)
        self.write_to_port(write_to_port_str)
        return self.query(query_str=from_port_query_str)

    # def flush_queue(self):
    #     self.write("FLOQ")
    #     time.sleep(0.1)

    def say_hello(self):
        self.device_id = self.query_from_port(write_to_port_str='*IDN?', len_str='100')
        print("Connected to :", self.device_id)


class SRS_SIM928(SRS_Module):
    @timer
    def setvolt(self, voltage=0.0):
        self.write_to_port(F"VOLT{self.voltage_format_str % voltage}")

    @timer
    def getvolt(self, max_bytes=100):
        resp = self.query_from_port(write_to_port_str='VOLT?', len_str=str(max_bytes))
        self.volts = float(resp)
        return self.volts

    @timer
    def output_on(self):
        self.write_to_port('OPON')

    @timer
    def output_off(self):
        self.write_to_port('OPOF')


if __name__ == "__main__":
    test_srs = get_test_srs(is_gpib=False)
    volatage_source1 = SRS_SIM928(srs_port=1, srs_connect=test_srs)
    volatage_source2 = SRS_SIM928(srs_port=2, srs_connect=test_srs)
    for n in range(10):
        print(F"n = {n}")
        volatage_source1.setvolt(voltage=-0.888)
        print(volatage_source1.getvolt())
        volatage_source1.setvolt(voltage=0.777)
        print(volatage_source1.getvolt())
        print()

    for n in range(10):
        print(F"n = {n}")
        volatage_source2.setvolt(voltage=-0.555)
        print(volatage_source2.getvolt())
        volatage_source2.setvolt(voltage=0.666)
        print(volatage_source2.getvolt())
        print()

    test_srs.close()
