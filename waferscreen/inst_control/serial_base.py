import serial
import time


def bitfield(n, expected_len=None):
    bit_list = [int(digit) for digit in bin(n)[2:]]
    if expected_len is not None:
        while len(bit_list) != expected_len:
            bit_list.insert(0, 0)
    return bit_list


def checksum(msg):
    check_sum = sum(msg) % 256
    check_sum_bits = bitfield(check_sum, expected_len=8)
    check_sum_1_bits = check_sum_bits[0:4]
    check_sum_2_bits = check_sum_bits[4:8]
    check_sum_1_string = ""
    check_sum_2_string = ""
    for count in range(4):
        check_sum_1_string += str(check_sum_1_bits[count])
        check_sum_2_string += str(check_sum_2_bits[count])
    check_sum1 = bytes(chr(int(check_sum_1_string, 2) + 48), encoding="ascii")
    check_sum2 = bytes(chr(int(check_sum_2_string, 2) + 48), encoding="ascii")
    return check_sum1, check_sum2


def getbytes(bits):
    done = False
    while not done:
        byte = 0
        for _ in range(0, 8):
            try:
                bit = next(bits)
            except StopIteration:
                bit = 0
                done = True
            byte = (byte << 1) | bit
        yield byte


def command_resp_byte(cmd_num, resp_num):
    cmd_bits = bitfield(cmd_num, expected_len=4)
    resp_bits = bitfield(resp_num, expected_len=3)
    all_bits = cmd_bits + resp_bits + [0]

    cmd_byte = [b.to_bytes(length=1, byteorder='big') for b in getbytes(iter(all_bits))]
    return cmd_byte[0]





class SerialConnection:
    def __init__(self, com_num=1, baud_rate=9600, encoding="utf-8", auto_open=True):
        self.com_num = com_num
        self.baud_rate = baud_rate
        self.encoding = encoding
        self.ctrl = serial.Serial(timeout=2)
        self.ctrl.baudrate = baud_rate
        self.ctrl.port = F"COM{self.com_num}"

        self.last_sent = None
        self.last_received = None
        if auto_open:
            self.open()

    def open(self):
        self.ctrl.open()

    def close(self):
        self.ctrl.close()

    def send(self, write_bstr):
        if isinstance(write_bstr, str):
            write_bstr = write_bstr.encode(self.encoding)
        self.ctrl.write(write_bstr)
        self.last_sent = write_bstr

    def receive(self, decode=False):
        b_resp = self.ctrl.read_all()
        self.last_received = b_resp
        if decode:
            return b_resp.decode(encoding=self.encoding)
        else:
            return b_resp


if __name__ == "__main__":
    s = SerialConnection(com_num=6, encoding="ascii")
    try:
        msg_data = b"\x63\x45\x4C\x00"

        cmd_rsp = command_resp_byte(cmd_num=8, resp_num=0)
        msg = b"\x10" + cmd_rsp + msg_data
        check_sum1, check_sum2 = checksum(msg)
        # s.send(b"\x02" + msg + check_sum1 + check_sum2 + b"\x0D")
        s.send(b"*IDN?\n")
        time.sleep(2)
        reply = s.receive(decode=False)
    except:
        s.close()
        raise
    s.close()
