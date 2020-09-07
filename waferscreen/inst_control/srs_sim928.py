import visa
import time
import serial


class SRS_SIM928(): 
    """ Stanford Research Systems SIM928 Isolated Voltage Source """
    def __init__(self, com_num=None, address="GPIB0::16::INSTR", port=1):
        self.port = str(port)
        if com_num is None:
            self.ResourceManager = visa.ResourceManager()
            self.ctrl = self.ResourceManager.open_resource("%s" % address, write_termination='\n')
            self.ctrl.timeout = 1000
            self.is_gpib = True
        else:
            self.ctrl = serial.Serial()
            self.ctrl.baudrate = '115200'
            self.ctrl.port = F"COM{com_num}"
            self.ctrl.open()
            self.is_open = self.ctrl.is_open
            self.is_gpib = False
        self.port = str(port)
        self.say_hello()

    def write(self, write_str):
        if self.is_gpib:
            self.ctrl.write(write_str)
        else:
            write_str += "\n"
            b_str = write_str.encode("utf-8")
            self.ctrl.write(b_str)

    def query(self, query_str):
        if self.is_gpib:
            resp = self.ctrl.query(query_str)
        else:
            self.write(write_str=query_str)
            b_resp = self.ctrl.read_all()
            resp = b_resp.decode(encoding="utf-8")
        return resp.strip()

    def say_hello(self):
        self.write("FLOQ")
        self.write('SNDT ' + self.port + ', "*IDN?"')
        time.sleep(0.1)
        self.device_id = self.query('GETN? ' + str(self.port) + ',100')  # [5:].rstrip()
        print("Connected to :", self.device_id)
        
    def setvolt(self, volts = 0):
        #print('SNDT ' + str(self.port) + ', "VOLT ' + str(volts) + '"')
        self.write('SNDT ' + str(self.port) + ', "VOLT ' + str(volts) + '"')
        
    def getvolt(self, max_bytes = 80):
        self.write("FLOQ")
        self.write('SNDT ' + str(self.port) + ', "VOLT?"')
        time.sleep(0.1)
        resp = self.query('GETN? ' + str(self.port) + ',80')
        self.volts = float(resp)
        return self.volts
        
    def output_on(self):
        self.write('SNDT ' + str(self.port) + ', "OPON"')
        
    def output_off(self):
        self.write('SNDT ' + str(self.port) + ', "OPOF"')
        
    def close(self):
        self.ctrl.close()
        print("Voltage source control closed")


if __name__ == "__main__":
    vc = SRS_SIM928(com_num=2)
    print(vc.query("*IDN?"))