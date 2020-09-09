import visa
import time
import serial


class SRS_SIM928:
    """ Stanford Research Systems SIM928 Isolated Voltage Source """
    def __init__(self, com_num=None, address="GPIB0::16::INSTR", port=1):
        self.device_id = None
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
        self.flush_queue()
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

    def query(self, query_str, resp_type=None):
        raw_resp = "#3000"
        count = 0
        if resp_type is None:
            while raw_resp == "#3000" and count < 5:
                count += 1
                raw_resp = self.try_query(query_str=query_str)
        else:
            while raw_resp[:5] != resp_type and count < 5:
                raw_resp = self.try_query(query_str=query_str)
        resp = raw_resp[5:]
        return resp

    def write_to_port(self, write_str):
        to_port_write_str = 'SNDT' + self.port + ',\"' + write_str + '\"'
        self.write(write_str=to_port_write_str)

    def query_from_port(self, write_to_port_str, len_str, resp_type=None):
        question = 'GETN?'
        from_port_query_str = question + str(self.port) + ',' + str(len_str)
        resp = ""
        while resp == "":
            self.write_to_port(write_to_port_str)
            resp = self.query(query_str=from_port_query_str, resp_type=resp_type)
        return resp

    def flush_queue(self):
        self.write("FLOQ")

    def say_hello(self):
        self.device_id = self.query_from_port(write_to_port_str='*IDN?', len_str='100', resp_type="#3051")
        print("Connected to :", self.device_id)
        
    def setvolt(self, voltage=0.0):
        self.write_to_port(F"VOLT{self.voltage_format_str % voltage}")

    def getvolt(self, max_bytes=80):
        resp = self.query_from_port(write_to_port_str='VOLT?', len_str=str(max_bytes), resp_type="#3008")
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

