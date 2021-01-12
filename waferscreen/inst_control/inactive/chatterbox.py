import serial_instrument

port = "rack"

s= serial_instrument.SerialInstrument(port=port)

while True:
    s.serial.write("test")
