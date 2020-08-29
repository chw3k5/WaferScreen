import visa
import time


class SRS_SIM928(): 
    """ Stanford Research Systems SIM928 Isolated Voltage Source """
    def __init__( self, address="GPIB0::16::INSTR", port = 1):
        self.ResourceManager = visa.ResourceManager()
        self.ctrl = self.ResourceManager.open_resource( "%s" % address, write_termination='\n' )
        self.ctrl.timeout = 1000
        self.ctrl.port = int(round(port))
        self.ctrl.write("FLOQ")
        self.ctrl.write('SNDT ' + str(self.ctrl.port) + ', "*IDN?"')
        time.sleep(0.1)
        self.ctrl.device_id = self.ctrl.query('GETN? ' + str(self.ctrl.port) + ',100')[5:].rstrip()
        print("Connected to : " + self.ctrl.device_id)
        
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