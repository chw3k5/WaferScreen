import named_serial

def twos_comp(val, bits=32):
    """compute the 2's complement of int value val
    from https://stackoverflow.com/questions/1604464/twos-complement-in-python"""
    if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val    

class ELL():
    debug = False
    pulses_per_revolution = 262144
    errors = {
        0: "OK, no error",
        1: "Communication time out",
        2: "Mechanical time out",
        3: "Command error or not supported",
        4: "Value out of range",
        5: "Module isolated",
        6: "Module out of isolation",
        7: "Initializing error",
        8: "thermal error",
        9: "Busy",
        10: "Sensor Error",
        11: "Motor Error",
        12: "Out of Range (eg stage has been instructed to move out of range)",
        13: "Over current error",
        14: "Reserved"
    }
    def __init__(self, port="rs482", address=0):
        self.serial = named_serial.Serial(port, baud=9600)
        self.serial.timeout = 0.05
        self.address = address

    def myread(self):
        r = ""
        while True:
            c = self.serial.read()
            r += c
            if c == "\n":
                break
            elif c == "":
                break
        return r.rstrip()

    def ask(self, s):
        s2 = "{}{}".format(self.address,s)
        self.serial.write(s2)
        if self.debug: print("wrote {}".format(s2))
        r=self.myread()
        if self.debug: print("got {}".format(r))
        return r

    def position_from_reply(self,r):
        # take a string like "0PO00000006" and return an interger representing position
        p = int(r[3:],16)
        return twos_comp(p)

    def get_status(self):
        r = e.ask("gs")
        if r != "":
            if r[1:3] == "GS":
                v = self.position_from_reply(r)
                raise Exception("ELL error: {}".format(self.errors[v]))
            elif r[1:3] == "PO":
                return True, self.position_from_reply(r)
        return False, 0


    def home(self):
        self.ask("ho")
        while True:
            done, p = self.get_status()
            if done:
                break
        self.position = p
        return self.position

    def move_absolute_position(self, p):
        if p < 0: 
            raise Exception()
        self.ask("ma{:08X}".format(p))
        while True:
            done, p = self.get_status()
            if done:
                break
        self.position = p
        return self.position

    def move_relative_position(self, p):
        if p < 0: 
            raise Exception()
        self.ask("mr{:08X}".format(p))
        while True:
            done, p = self.get_status()
            if done:
                break
        self.position = p
        return self.position

    def position_to_degree(self,p):
        return (p/float(self.pulses_per_revolution))*360

    def degree_to_position(self,theta):
        return int((theta%360)*self.pulses_per_revolution/360.0)

    def move_absolute_degree(self, theta):
        p = self.move_absolute_position(self.degree_to_position(theta))
        return self.position_to_degree(p)

    def move_absolute_onedir_position(self, p):
        if p > self.position:
            return self.move_relative_position(p-self.position)
        elif p == self.position:
            return self.position
        else:
            return self.move_relative_position(p+self.pulses_per_revolution-self.position)

    def move_absolute_onedir_degree(self, theta):
        p = self.move_absolute_onedir_position(self.degree_to_position(theta))
        return self.position_to_degree(p)
        



if __name__ == "__main__":
    e = ELL()
    print e.home()
    print e.move_absolute_onedir_degree(0)
    print e.move_absolute_onedir_degree(270)
    print e.move_absolute_onedir_degree(360)



    