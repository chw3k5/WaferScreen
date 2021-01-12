'''
cryocon 44c control over ethernet
created June 2012 by Galen O'Neil
modified by Frank Schima 6/12/2012
'''
import time
import ethernet_instrument

class Cryocon44c(ethernet_instrument.EthernetInstrument):

    def __init__(self, hostname='686tupac-cryocon.bw.nist.gov', tcpPort = 5000, maxBufferSize = 1024, udpPort=5001, useUDP = True):
        
        super(Cryocon44c, self).__init__(hostname=hostname, udpPort = udpPort, tcpPort=tcpPort, maxBufferSize=maxBufferSize, useUDP=useUDP)

    def startDataLog(self, timeBetweenPoints=600, resetDataLog=False):
        if resetDataLog:
            self.send('DLOG:RESET;DLOG:CLEAR')
        self.send('DLOG:INTERVAL '+str(timeBetweenPoints)+';DLOG:STAT ON')
        
    def getTemperature(self, channel=1):
        if channel == 1 or channel ==2  or channel == 3 or channel == 4:
            data = self.ask('input? '+str(channel)+':units k')
            if data == '.......':
                print('WARNING: Cryocon returned a voltage out of range signal, Temperature = -7777')
                return -7777
            elif data == '-------':
                print('WARNING: Cryocon returned a temperature out of range signal, Temperature = -9999')
                data = -9999
            else:
                return float(data)
        else:
            raise ValueError
        
    def getTemperatures(self):
        data = []
        for channel in range(4):
            data.append(self.getTemperature(channel+1))
        return data

    
    def getDataLog(self):
        print('cryocon44c getting data log, this can take up to 2 minutes')
        startTime = time.time() # time the function execution

        originalDlogStatus = self.ask('DLOG:STAT?') # check DLOG status
        self.send('DLOG:STAT OFF') # Logging must be off to read log
        data = self.askLong('DLOG:READ?',endSymbol=';')
        self.send('DLOG:STAT ' + originalDlogStatus) # return to previous DLOG status
#        print('DLOG:STAT ' + originalDlogStatus)
        endTime = time.time() # time the function execution
        executionTime = endTime-startTime
        print('getting log data took ' + str(executionTime) + ' seconds')
        # process dlog data
        data = data.split('\r\n')
        data = data[:-1] # trim off the last entry which is empty
        
        logpoint = []
        timepoint = []
        tempCh1 = []
        tempCh2 = []
        tempCh3 = []
        tempCh4 = []
        
        array_data = []
        for line in data:
            splitline = line.split(',')
            logpoint.append(int(splitline[0]))
            date = splitline[1].split('/')
            time_hms = splitline[2].split(':')
            tempCh1.append(float(splitline[3]))
            tempCh2.append(float(splitline[4]))
            tempCh3.append(float(splitline[5]))
            tempCh4.append(float(splitline[6]))
            #make time tuple (y, m, d, h, m, s)
            
            timetuple= ( int(date[2]), int(date[0]), int(date[1]), int(time_hms[0]),
                                     int(time_hms[1]), int(time_hms[2]),0,0,0)
            
            timepoint.append(time.mktime(timetuple))
        
        
        

        return array_data, logpoint, timepoint, tempCh1, tempCh2, tempCh3, tempCh4
        