#!/usr/bin/env python

"""
ADRMonitor - A program to query the temperature controller.

Purpose:
* To monitor an ADR's state via the Lakeshore 370 controller.
* To store that state in a directory of binary files ("dirfile").
* To offer the latest temperature information to local client programs.

As of Feb 6, 2014, this is still a regular script, but I will investigate
making it into a daemon (system service) that runs all the time (though
maybe not started by default at bootup??).

Author:  Joe Fowler, NIST Boulder Labs
Started: January 30, 2014
"""

import sys, time, os
import struct
import numpy as np
import pygetdata
import zmq

DEFAULT_CONFIGFILE = "/etc/adr_monitor_conf.xml"


class TemperatureDevice(object):
    """Interface to the Lakeshore 370 (or whatever your device might be
    in the future)."""
    
        
    def __init__(self, lakeshore_pad):
        import lakeshore370
        self.lakeshore = lakeshore370.Lakeshore370(pad=lakeshore_pad)
        
    def read_data(self):
        """Read and return (temperature,heater,time)."""
        currentTemperature = self.lakeshore.getTemperature(1)*1e3
        currentHeaterOut = self.lakeshore.getHeaterOut()
        currentTime = time.time()
        return currentTemperature, currentHeaterOut, currentTime


def current_yyyymmdd_hhmmss():
    t = time.localtime()
    return "%4.4d%2.2d%2.2d_%2.2d%2.2d%2.2d"%(
            t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)


class TemperatureFaker(object):
    """Use this in place of TemperatureDevice class for testing with fake data."""
    PERIOD = 10 # seconds
    def read_data(self):
        t = time.time()
        frac_t = (t/self.PERIOD)%1
        temp = 70+2*np.sin(np.pi*2*frac_t) + np.random.standard_normal(1)[0]
        curr = 30+5*np.cos(np.pi*2*frac_t) + np.random.standard_normal(1)[0]
        return temp,curr,t
    
    
class DataWriter(object):
    """Interface to the output data writer. Currently, a dirfile writer.
    
    Implementation detail: for now I am using the pygetdata package to write
    the dirfile metadata (that is, the format file), but it seems easier to
    write the binary data directly through file objects with the struct.pack(...)
    function instead of using the pygetdata facilities for writing data."""
    
    def __init__(self, directory):
        directory = os.path.expandvars(directory)
        print "Trying directory ", directory
        basename = current_yyyymmdd_hhmmss()
        filename = os.path.join(directory, basename)
        self.dirfile = pygetdata.dirfile(filename, pygetdata.CREAT|pygetdata.RDWR)
        self.filename = filename

        # Not sure whether curfiles or soft links are now preferred in
        # kst2, so for now, set up one of each!
        
        # Set up a "curfile" that always points to the current dirfile.
        curfilename = os.path.join(directory, "temperatures.cur")
        prevfilename = os.path.join(directory, "temperatures.prev")
        if os.path.exists(prevfilename):
            os.unlink(prevfilename)
        if os.path.exists(curfilename):
            os.rename(curfilename, prevfilename)
        fp = open(curfilename, "w")
        fp.write("%s\n"%basename)
        fp.close()
        
        # Also set up a soft link to the current dirfile
        softlink = os.path.join(directory, "temperatures.lnk")
        if os.path.exists(softlink):
            os.unlink(softlink)
        os.symlink(basename, softlink)
        
        # Set up the dirfile fields
        fields={
            'temperature':{'type':pygetdata.FLOAT32,'spf':1},
            'current':{'type':pygetdata.FLOAT32,'spf':1},
            'ctime':{'type':pygetdata.FLOAT64,'spf':1}
                }
        for name,params in fields.iteritems():
            entry = pygetdata.entry(pygetdata.RAW_ENTRY, name, 0, params)
            self.dirfile.add(entry)
        self.dirfile.metaflush()
        
        # Open file handles for the raw data
        # Do this instead of self.dirfile.putdata(), because that's annoying
        self.dirfile.raw_close()
        self.raw_files = {}
        for f in fields.keys():
            fp = open(os.path.join(self.filename,f), "wb")
            self.raw_files[f] = fp

    def close(self):
        """Cleanly close the output files and flush their buffers."""
        for fp in self.raw_files.values():
            fp.close()
        self.dirfile.close()
        self.dirfile = None

    def __del__(self):
        """Make sure to call close on the output, if not already done."""
        if self.dirfile is not None:
            self.close()

    def store_data(self, temperature, current, ctime):
        results = locals()
        for f,fmt in zip(('temperature','current','ctime'),('f','f','d')):
            fp = self.raw_files[f]
            str = struct.pack(fmt, results[f])
            fp.write(str)
            fp.flush()


class ZMQServer(object):
    """A very simple data server, using ZeroMessageQueue (0MQ)
    in the interprocess communication mode, to answer requests
    received on a TCP-like socket from other local processes.
    
    The system avoids threading by cooperatively polling the
    socket for queries and sleeping. I hope this isn't a performance
    problem, because it sure is simple. A big drawback is that 
    the self.serve_and_delay(X) blocks for X seconds. That means
    you can only use it if you know you have nothing better to
    do during that time. Anyway, it works for the ADR cryo temperature
    monitor, because the only other work is to poll the GPIB every
    X seconds (typically, X is between 0.3 and 3).
    
    Example usage:
    The following will bind 'ipc:///home/pcuser/wherever.../socket_name',
    which the client program or programs will also need to know.
        
    server = ZMQServer('/home/pcuser/wherever.../socket_name')
    while True:
        x,y,z = lakeshore_device_object.query()
        server.newdata(x,y,z)
        server.serve_and_delay(1.0)
    
    """
    
    def __init__(self, socket_name):
        '''Sets up an ipc socket at ipc://<socket_name> where
        <socket_name> must be a file-like pathname in the computer's
        filesystem, to which this process has write access.'''
        
        self.socket_name = "ipc://%s"%os.path.expandvars(socket_name)
        self.data = 0,0,0
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        print "Binding to %s"%self.socket_name
        self.socket.bind(self.socket_name)
    
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def __del__(self):
        self.socket.close()
         
    def newdata(self, temperature, current, ctime):
        self.data = (temperature, current, ctime)
        
    def serve_and_delay(self, delay_sec):
        '''For a time period of <delay_sec> seconds, poll the socket for 
        queries
        
        '''
        t_end = time.time() + delay_sec
        while True:
            poll_interval_msec = (t_end - time.time())*1e3
            if poll_interval_msec <= 0: 
                break
            
            poll_result = dict(self.poller.poll(poll_interval_msec))
            if self.socket in poll_result and poll_result[self.socket] == zmq.POLLIN:
                msg = self.socket.recv()
                print "\nReceived request: ", msg
                msg = "%.5f %.3f %.5f"%self.data
                self.socket.send(msg)



class ADRMonitor(object):
    """Run the ADR monitor by reading from a TemperatureDevice and
    writing to a DataWriter, plus handling a ZMQServer.
    
    Usage: 
    m = ADRMonitor.ADRMonitor('/etc/adr_monitor_conf.xml')
    m.run()
    """
    
    def __init__(self, xml_config_file, simulate=False):
        from lxml import etree
        try:
            document = etree.parse(xml_config_file)
#             print etree.tostring(root, pretty_print=True)
        except:
            print "Could not parse %s"%xml_config_file

        self.doc = document
        self.root = document.getroot()
        assert self.root.get('version') == '1'
        for node in self.root:
            self.__dict__[node.tag] = node.text
    
        # This check helps make errors in the settings file be less cryptic to the user.
        REQUIRED_SETTINGS = ("dirfile_location","polling_period_msec",
                             "lakeshore_pad", "socket_name")
        for s in REQUIRED_SETTINGS:
            if s not in self.__dict__:
                raise IOError("xml config file %s does not contain a '%s' tag"%(
                        xml_config_file, s))
    
        if not simulate:
            self.device = TemperatureDevice(lakeshore_pad = int(self.lakeshore_pad))
        else:
            self.device = TemperatureFaker()
        self.writer = DataWriter(self.dirfile_location)
        self.server = ZMQServer(self.socket_name)
    
    
    def run(self):
        delay = 0.001*int(self.polling_period_msec)
        while True:
            a,b,c = self.device.read_data()
            print a,b,c
            self.writer.store_data(a,b,c)
            self.server.newdata(a,b,c)
            self.server.serve_and_delay(delay)

    def __del__(self):
        self.writer.close()
    


def create_settings_file(filename, **kwargs):
    """A quick way to generate a settings file. Normally not used, but
you can run this from a Python session to make a settings file.

If you are having trouble doing that, then perhaps you can just copy
the following lines into /etc/adr_monitor_conf.xml (the default place
is given by global variable DEFAULT_CONFIGFILE in this program).
    
<ADRMonitor version="1">
  <polling_period_msec>500</polling_period_msec>
  <dirfile_location>$HOME/data/cryo_logs</dirfile_location>
  <lakeshore_pad>13</lakeshore_pad>
  <socket_name>$HOME/data/cryo_logs/cryo_monitor</socket_name>
</ADRMonitor>
    """
    
    # Start with default settings, and update using any arguments here.
    settings = {'lakeshore_pad':13,
                'polling_period_msec':500,
                'dirfile_location':'$HOME/data/cryo_logs',
                'socket_name':'$HOME/data/cryo_logs/cryo_monitor'}
    settings.update(kwargs)
    
    # Generate an XML representation
    from lxml import etree
    root = etree.Element("ADRMonitor", version="1")
    for k,v in settings.iteritems():
        child = etree.SubElement(root, k)
        child.text = str(v)

    # Store XML to a file
    fp = open(filename, "w")
    fp.write(etree.tostring(root, pretty_print=True))
    fp.close()



def main():

    config_file = DEFAULT_CONFIGFILE
    if len(sys.argv)==2:
        config_file = sys.argv[1]
    elif len(sys.argv) > 2:
        print "usage: ADRMonitor.py [config_file]"
        print "    The default config file is %s"%DEFAULT_CONFIGFILE
        print "    If you need to construct one, see create_settings_file()"
        print "    Here is its docstring\n%s\n   "%(75*'-'),
        print create_settings_file.__doc__
        print 75*'-'
        return

    simulate = True  # Obviously, you remove this when working with a real LS370.

    if not os.path.isfile(config_file):
        if config_file == DEFAULT_CONFIGFILE:
            print "The default configuration "\
                "file %s is missing"%DEFAULT_CONFIGFILE
            print "Possibly helpful docstring from create_settings_file():\n"
            print create_settings_file.__doc__
        else:
            print "The specified configuration file %s doesn't exist."%config_file
            print "Perhaps you can try omitting the config file name and fall back"
            print "to the default?"
        return
    
    monitor = ADRMonitor(config_file, simulate=simulate)
    monitor.run()


if __name__=='__main__':
    main()
    

