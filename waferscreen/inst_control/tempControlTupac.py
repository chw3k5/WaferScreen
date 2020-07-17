import adr_system
import time


class TempControlTupac():
    def __init__(self, tempTarget = 0.035, adr_system_in = None):
        if adr_system_in is None:
            self.a = adr_system.AdrSystem()
        else:
            self.a = adr_system_in
            
        self.controlThermExcitation = 31.6e-9
        self.baseTempResistance = 60e3
        self.rampRate = 0.050
        self.readyToControl = False


        self.setupTempControl()
        self.goToTemp(tempTarget)

    def setupTempControl(self):
        heaterOut = self.a.temperature_controller.getHeaterOut()
        if heaterOut == 0:
            self.a.magnet_control_relay.setRelayToControl()
            self.a.temperature_controller.setScan(channel = 1, autoscan = 'off')
            self.a.temperature_controller.setHeaterRange(range=0)
            # temp setpoint should respond instantly when heater range is zero
            self.a.temperature_controller.setTemperatureControlSetup(channel=1, units='Kelvin', maxrange=100, delay=2, output='current', filterread='unfiltered')
            self.a.temperature_controller.setControlMode(controlmode = 'closed')
            self.a.temperature_controller.setControlPolarity(polarity = 'unipolar')
            self.a.temperature_controller.setTemperatureSetPoint(setpoint=0.035)
            self.a.temperature_controller.setRamp(rampmode = 'on' , ramprate = self.rampRate)
            self.a.temperature_controller.setHeaterRange(range=100)

            self.readyToControl = True
        elif self.readyToControl is False:
            print('tempControlTupac wont take control until the heaterOut is 0, get it there manually and try again')
        else:
            print('tempControlTupac thinks it is already controlling the temperature, so it didnt change anything')
    
    def goToTemp(self, tempTarget = 0.035):
        if self.readyToControl is True:
            self.a.temperature_controller.setReadChannelSetup(exciterange=self.controlThermExcitation, resistancerange=self.baseTempResistance)
            time.sleep(3)
            self.a.temperature_controller.setTemperatureSetPoint(tempTarget)
        else:
            print("did not goToTemp because readyToControl is False")
            
    def safeAutorange(self):
        resistance = self.a.temperature_controller.getResistance(channel=1)
        self.a.temperature_controller.setReadChannelSetup(exciterange=self.controlThermExcitation, resistancerange=resistance*1.1)

    def getTemp(self, channel=1):
        return self.a.temperature_controller.getTemperature(channel)
    
    def getTempError(self, channel=1):
        setPoint = self.a.temperature_controller.getTemperatureSetPoint()
        currentTemp = self.getTemp(channel)
        return currentTemp-setPoint
        



