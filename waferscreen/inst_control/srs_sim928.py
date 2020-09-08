import visa
import time
import serial



class SRS_SIM928:
    """ Stanford Research Systems SIM928 Isolated Voltage Source """
    def __init__(self, com_num=None, address="GPIB0::16::INSTR", port=1):
        self.port = str(port)
        self.voltage_precision = '3'
        self.voltage_format_str = '%1.' + self.voltage_precision + 'e'
        if com_num is None:
            self.ResourceManager = visa.ResourceManager()
            self.ctrl = self.ResourceManager.open_resource("%s" % address, write_termination='\n')
            self.ctrl.timeout = 1000
            self.is_gpib = True
        else:
            baud_rate = '115200'
            self.ctrl = serial.Serial()
            self.ctrl.baudrate = baud_rate
            self.ctrl.port = F"COM{com_num}"
            self.ctrl.open()
            self.is_open = self.ctrl.is_open
            self.is_gpib = False
            # self.write_to_port('BAUD' + baud_rate)
        self.say_hello()

    def write(self, write_str):
        if self.is_gpib:
            self.ctrl.write(write_str)
        else:
            write_str += "\n"
            b_str = write_str.encode("utf-8")
            self.ctrl.write(b_str)

    def try_query(self, query_str):
        if self.is_gpib:
            resp = self.ctrl.query(query_str)
        else:
            self.write(write_str=query_str)
            time.sleep(0.1)
            b_resp = self.ctrl.read_all()
            resp = b_resp.decode(encoding="utf-8")
        return resp.strip()

    def query(self, query_str):
        raw_resp = "#3000"
        while raw_resp == "#3000":
            raw_resp = self.try_query(query_str=query_str)
        resp = raw_resp[5:]
        return resp

    def write_to_port(self, write_str):
        to_port_write_str = 'SNDT' + self.port + ',\"' + write_str + '\"'
        self.write(write_str=to_port_write_str)

    def query_from_port(self, len_str):
        question = 'GETN?'
        from_port_query_str = question + str(self.port) + ',' + str(len_str)
        return self.query(query_str=from_port_query_str)

    def flush_queue(self):
        self.write("FLOQ")

    def say_hello(self):
        self.write_to_port('*IDN?')
        self.device_id = self.query_from_port(len_str='100')  # [5:].rstrip()
        print("Connected to :", self.device_id)
        
    def setvolt(self, voltage=0.0):
        self.write_to_port(F"VOLT{self.voltage_format_str % voltage}")

    def getvolt(self, max_bytes=80):
        self.flush_queue()
        self.write_to_port('VOLT?')
        resp = self.query_from_port(str(max_bytes))
        self.volts = float(resp)
        return self.volts
        
    def output_on(self):
        self.write_to_port('OPON')
        
    def output_off(self):
        self.write_to_port('OPOF')
        
    def close(self):
        self.ctrl.close()
        print("Connection to SIM 928 Voltage source is closed")


if __name__ == "__main__":
    vc = SRS_SIM928(com_num=2, address="GPIB0::16::INSTR", port=1)
    vc.write_to_port("VOLT?")
    vc.query_from_port('100')
    vc.write_to_port("VOLT?")
    vc.query_from_port('100')

