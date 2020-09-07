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
            self.port = int(round(port))
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
            self.ctrl.write(write_str.encode("utf-8"))

    def say_hello(self):
        self.write("FLOQ")
        self.write('SNDT ' + self.port + ', "*IDN?"')
        time.sleep(0.1)
        if self.is_gpib:
            self.device_id = self.ctrl.query('GETN? ' + str(self.ctrl.port) + ',100')[5:].rstrip()
        else:
            self.write('GETN? ' + self.port + ',100')
            self.device_id = str(self.ctrl.read_all())
        print("Connected to : " + self.device_id)
        
    def setvolt(self, volts = 0):
        #print('SNDT ' + str(self.ctrl.port) + ', "VOLT ' + str(volts) + '"')
        self.ctrl.write('SNDT ' + str(self.ctrl.port) + ', "VOLT ' + str(volts) + '"')
        
    def getvolt(self, max_bytes = 80):
        self.ctrl.write("FLOQ")
        self.ctrl.write('SNDT ' + str(self.ctrl.port) + ', "VOLT?"')
        time.sleep(0.1)
        resp = self.ctrl.query('GETN? ' + str(self.ctrl.port) + ',80')
        self.volts = float(resp[5:].rstrip())
        return self.volts
        
    def output_on(self):
        self.ctrl.write('SNDT ' + str(self.ctrl.port) + ', "OPON"')
        
    def output_off(self):
        self.ctrl.write('SNDT ' + str(self.ctrl.port) + ', "OPOF"')
        
    def close(self):
        self.ctrl.close()
        print("Voltage source control closed")


if __name__ == "__main__":
    vc = SRS_SIM928(com_num=2)