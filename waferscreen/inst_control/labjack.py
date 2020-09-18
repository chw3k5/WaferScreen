import u3
import time


class U3:
    def __init__(self, auto_init=True):
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
        self.lj.writeRegester(register, write_val)

    def daq0(self, voltage):
        self.lj.writeRegester(5000, voltage)

    def fio0(self):
        return self.lj.writeRegester(0)

    def led(self, led_on=True):
        if led_on in {True, 1, '1'}:
            self.lj.writeRegester(6004, 1)
        else:
            self.lj.writeRegester(6004, 0)

    def say_hello(self, jumper_test=True, voltage=1.5):
        if jumper_test:
            self.daq0(voltage=voltage)
            print("Jumper DAQ0 and AIN0 test.")
            print(F"  DAQ1 writen to have a voltage of {voltage} Volts.")
            time.sleep(0.2)
            print(F"  AIN0 reads: {self.fio0()} Volts\n")

        for on_time in [0.1, 0.1, 0.2, 0.3, 0.5, 0.8, 1.3]:
            self.led(led_on=True)
            time.sleep(on_time)
            self.led(led_on=False)
            time.sleep(0.2)
        else:
            self.led(led_on=True)


if __name__ == "__main__":
    u = U3()
    u.say_hello()

