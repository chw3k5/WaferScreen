import u3
import time


class U3:
    def __init__(self, auto_init=True, verbose=True):
        self.verbose = verbose
        self.lj = None
        self.is_open = False
        if auto_init:
            self.open()

    def open(self):
        self.lj = u3.U3()
        self.is_open = True

    def close(self):
        self.lj.close()
        self.is_open = False

    def write(self, register, write_val):
        self.lj.writeRegister(register, write_val)

    def daq0(self, voltage):
        self.lj.writeRegister(5000, voltage)

    def fio0(self):
        return self.lj.readRegister(0)

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
        self.daq0(voltage=voltage)
        if self.verbose:
            print("Jumper DAQ0 and AIN0 for this test.")
            print(F"  DAQ0 writen to have a voltage of {voltage} Volts.")
        time.sleep(sleep_time)
        if self.verbose:
            print(F"  AIN0 reads: {self.fio0()} Volts\n")
        if zero_after and voltage != 0.0:
            time.sleep(sleep_time)
            self.daq0(voltage=0.0)
            if self.verbose:
                print('  Voltage reset to 0 Volts')

    def say_hello(self, jumper_test=True, led_test=False, voltage=1.5):
        if jumper_test:
            self.daq0(voltage=voltage)
            if self.verbose:
                print("Jumper DAQ0 and AIN0 for this test.")
                print(F"  DAQ1 writen to have a voltage of {voltage} Volts.")
            time.sleep(0.2)
            if self.verbose:
                print(F"  AIN0 reads: {self.fio0()} Volts\n")

        if led_test:
            for on_time in [0.1, 0.1, 0.2, 0.3, 0.5, 0.8, 1.3]:
                self.led(led_on=True)
                time.sleep(on_time)
                self.led(led_on=False)
                time.sleep(0.2)
            else:
                self.led(led_on=True)


if __name__ == "__main__":
    u = U3()
    u.alive_test(voltage=0)

