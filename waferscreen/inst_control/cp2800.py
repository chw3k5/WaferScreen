import math
from time import sleep
import struct

import serial_instrument

#########################################################################
#
# Cryomech CP2800 Class
#
# Class to control the Cryomech CP2800 compressor via serial port. This is usually used 
# as a heat switch. 
#
# by Frank Schima
##########################################################################


class CP2800(serial_instrument.SerialInstrument):

######################################################################################
    # Zaber class

    def __init__(self, port='zaber', baud=115200, shared=True, smdp_address=0x10):
        '''Cryomech CP2800 motor - parameters:
        port - a logical portname defined in namedserialrc
        baud -  115200 for cp2800 
        shared - allow other processes to open this device
                 only works on posix
        smdp_address - Address of compressor. 0x10 is factory default. 
        '''

        super(CP2800, self).__init__(port, baud, shared)

        self.manufacturer = 'Cryomech'
        self.model_number = 'CP2800'
        
        self.smdp_address = smdp_address

        self.port = port
        self.baud = baud
        self.shared = shared

########################################### Private Methods #################################################

    def __writeBytes(self, bytestowrite):

        result = self.serial.writelist(bytestowrite)
        if result is not None:
            print 'Error in serial write to Zaber'
        return result

    def __calcChecksum(self, rw_byte, byte1, byte2, index_byte, write_byte = 0x0):

        checksum = (self.smdp_address + 0x80 + rw_byte + byte1 + byte2 + index_byte + write_byte) % 256
        #print "checksum = ", checksum

        chk1 = ((checksum & 0xF0) >> 4) + 0x30
        chk2 = (checksum & 0xF) + 0x30
        #print "chk1, chk2", chr(chk1), hex(chk1), chr(chk2), hex(chk2)

        return chk1, chk2

    def __genericWriteCommand(self, byte1, byte2, rw_byte, index_byte, write_byte):

        chk1, chk2 = self.__calcChecksum(rw_byte, byte1, byte2, index_byte, write_byte)
        
        command = [0x2, self.smdp_address, 0x80, rw_byte, byte1, byte2, index_byte, \
                   0x0, 0x0, 0x0, write_byte, chk1, chk2, 0xd]
        #for a in command:
        #    print hex(a)

        result = self.__writeBytes(command)

        # Read the junk that is returned and ignore it to clear the serial buffer
        return_string = self.serial.read(6)
        #for char in return_string:
        #    print hex(ord(char))

    def __genericReadCommand(self, byte1, byte2, rw_byte, index_byte):
        
        chk1, chk2 = self.__calcChecksum(rw_byte, byte1, byte2, index_byte)
        
        num_escape_bytes = 0
        
        command = [0x2, self.smdp_address, 0x80, rw_byte, byte1, byte2, index_byte, chk1, chk2, 0xd]

        #Account for reserved characters with the escapes
        if byte1 == 0xd:
            command[4] = 0x7
            command.insert(5, 0x31)
            num_escape_bytes += 1 #Extra bytes to account for escapes
        if byte2 == 0xd:
            command[5+num_escape_bytes] = 0x7
            command.insert(6 + num_escape_bytes, 0x31)
            num_escape_bytes += 1 #Extra bytes to account for escapes
        if index_byte == 0x2:
            command[6+num_escape_bytes] = 0x7
            command.insert(7 + num_escape_bytes, 0x30)
            num_escape_bytes += 1 #Extra bytes to account for escapes

#        for a in command:
#            print hex(a)
            
        result = self.__writeBytes(command)
        
        return_string = self.serial.read(14+num_escape_bytes)
        
#        for char in return_string:
#            print hex(ord(char))
        
        # Need to account for escape characters in returned data. 
        # Escaped characters add to the length of the returned string. We
        # check twice in case any of the returned characters have escapes
        # in them just to be safe. 
        return_string = return_string[:]  #make a copy
        num_escapes = return_string.count(chr(0x07))
        #print 'Number of escapes', num_escapes
        missing_chrs = ''
        if self.serial.inWaiting() > 0:
            missing_chrs = self.serial.read(num_escapes)
        return_string = return_string + missing_chrs
        #Run again in case there were escapes in the missing_chrs
        new_num_escapes = return_string.count(chr(0x07))
        #print 'New Number of escapes', new_num_escapes
        if self.serial.inWaiting() > 0:
            missing_chrs = self.serial.read(new_num_escapes-num_escapes)
        return_string = return_string + missing_chrs
                
        return_string = return_string.replace(chr(0x07)+chr(0x30),chr(0x02))
        return_string = return_string.replace(chr(0x07)+chr(0x31),chr(0x0D))
        return_string = return_string.replace(chr(0x07)+chr(0x32),chr(0x07))
#        for char in return_string:
#            print hex(ord(char))

        output_num = (ord(return_string[10])&0xFF) + \
                    ((ord(return_string[9])&0xFF)<<8) + \
                    ((ord(return_string[8])&0xFF)<<16) + \
                    ((ord(return_string[7])&0xFF)<<24)

        return output_num

########################################### Public Methods #################################################

# Control Methods

    def compressorOn(self):
        
        byte1 = 0xD5
        byte2 = 0x01
        rw_byte = 0x61  # 0x63 is read, 0x61 is write
        index_byte = 0
        write_byte = 0x1

        self.__genericWriteCommand(byte1, byte2, rw_byte, index_byte, write_byte)

    def compressorOff(self):

        byte1 = 0xC5
        byte2 = 0x98
        rw_byte = 0x61  # 0x63 is read, 0x61 is write
        index_byte = 0
        write_byte = 0x0

        self.__genericWriteCommand(byte1, byte2, rw_byte, index_byte, write_byte)

    def clearTemperaturePressureMarkers(self):

        byte1 = 0xD3
        byte2 = 0xDB
        rw_byte = 0x61  # 0x63 is read, 0x61 is write
        index_byte = 0
        write_byte = 1

        self.__genericWriteCommand(byte1, byte2, rw_byte, index_byte, write_byte)

# Read methods

    def getFirmwareChecksum(self):
        
        byte1 = 0x2B
        byte2 = 0x0D
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        
        return value

    def isCompressorOn(self):
        
        ''' Returns 1 if the compressor is on, or 0 if it is off. '''
        
        byte1 = 0x5F
        byte2 = 0x95
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        
        return value

    def isTemperatureSensorError(self):
        
        ''' Returns 1 if there is a failure in any temperature sensor, or 0 if not. '''
        
        byte1 = 0x6E
        byte2 = 0x2D
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        
        return value

    def isPressureSensorError(self):
        
        ''' Returns 1 if there is a failure in any pressure sensor, or 0 if not. '''
        
        byte1 = 0xF8
        byte2 = 0x2B
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        
        return value

    def getCompressorMinutes(self):
        
        ''' Returns the number of minutes that the compressor has run. '''
        
        byte1 = 0x45
        byte2 = 0x4C
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        
        return value

    def getCompressorStatus(self):
        
        byte1 = 0x5F
        byte2 = 0x95
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        
        return value

    def getErrorCodeStatus(self):
        
        byte1 = 0x65
        byte2 = 0xA4
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        
        return value

    def parseErrorCodeStatus(self, error_code):
        
        #parse_dict = {0, ''}
        
        return error_code

    def getCompressorMotorCurrentDraw(self):
        
        '''Returns compressor motor current draw in Amps. '''
        
        byte1 = 0x63
        byte2 = 0x8B
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        amps = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        
        return amps


    # Temperatures return a value in 0.1 degrees C. The functions divide by 10 to return straight degrees C. 

    def getCPUTemperature(self):
        
        ''' Returns CPU Temperature in degrees c.'''
        
        byte1 = 0x35
        byte2 = 0x74
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getInputWaterTemperature(self):
        
        byte1 = 0x0D
        byte2 = 0x8F
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getOutputWaterTemperature(self):
        
        byte1 = 0x0D
        byte2 = 0x8F
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 1

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getHeliumTemperature(self):
        
        byte1 = 0x0D
        byte2 = 0x8F
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 2

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)      
        temperature = value/10.0
        
        return temperature

    def getOilTemperature(self):
        
        byte1 = 0x0D
        byte2 = 0x8F
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 3

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getHighSidePressure(self):
        
        byte1 = 0xAA
        byte2 = 0x50
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        psi = value/10.0
        
        return psi

    def getMinimumInputWaterTemperature(self):

        byte1 = 0x6E
        byte2 = 0x58
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getMinimumOutputWaterTemperature(self):

        byte1 = 0x6E
        byte2 = 0x58
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 1

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getMinimumHeliumTemperature(self):

        byte1 = 0x6E
        byte2 = 0x58
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 2

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getMinimumOilTemperature(self):

        byte1 = 0x6E
        byte2 = 0x58
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 3

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getMaximumInputWaterTemperature(self):

        byte1 = 0x8A
        byte2 = 0x1C
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getMaximumOutputWaterTemperature(self):

        byte1 = 0x8A
        byte2 = 0x1C
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 1

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getMaximumHeliumTemperature(self):

        byte1 = 0x8A
        byte2 = 0x1C
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 2

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    def getMaximumOilTemperature(self):

        byte1 = 0x8A
        byte2 = 0x1C
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 3

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        temperature = value/10.0
        
        return temperature

    # Pressures return a value in 0.1 psia. The functions divide by 10 to return straight psia. 

    def getAverageLowSidePressure(self):
        
        byte1 = 0xBB
        byte2 = 0x94
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 1

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        psi = value/10.0
        
        return psi

    def getAverageHighSidePressure(self):
        
        byte1 = 0x7E
        byte2 = 0x90
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 1

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        psi = value/10.0
        
        return psi

    def getAverageDeltaPressure(self):
        
        ''' Returns the average delta pressure in degrees C.'''
        
        byte1 = 0x31
        byte2 = 0x9C
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 1

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        psi = value/10.0
        
        return psi

    def getLowSidePressure(self):
        
        byte1 = 0xAA
        byte2 = 0x50
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 1

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        psi = value/10.0
        
        return psi

    def getMinimumHighSidePressure(self):
        
        byte1 = 0x5E
        byte2 = 0x0B
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        psi = value/10.0
        
        return psi

    def getMinimumLowSidePressure(self):
        
        byte1 = 0x5E
        byte2 = 0x0B
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 1

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        psi = value/10.0
        
        return psi

    def getMaximumHighSidePressure(self):
        
        byte1 = 0x7A
        byte2 = 0x62
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 0

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        psi = value/10.0
        
        return psi

    def getMaximumLowSidePressure(self):
        
        byte1 = 0x7A
        byte2 = 0x62
        rw_byte = 0x63  # 0x63 is read, 0x61 is write
        index_byte = 1

        value = self.__genericReadCommand(byte1, byte2, rw_byte, index_byte)
        psi = value/10.0
        
        return psi
