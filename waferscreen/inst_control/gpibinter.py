import platform
from ctypes import *
from ctypes.util import find_library

# define some ugly constants
TNONE = 0    #Never timeout.
T10us = 1    #10 microseconds
T30us = 2    #30 microseconds
T100us = 3  #100 microseconds
T300us = 4    #300 microseconds
T1ms = 5    #1 millisecond
T3ms = 6    #3 milliseconds
T10ms = 7    #10 milliseconds
T30ms = 8   #30 milliseconds
T100ms = 9    #100 milliseconds
T300ms = 10    #300 milliseconds
T1s = 11    #1 second
T3s = 12    #3 seconds
T10s = 13    #10 seconds
T30s = 14    #30 seconds
T100s = 15    #100 seconds
T300s =16    #300 seconds
T1000s= 17    #1000 seconds

# status bits
DCAS  = 0x1
DTAS  = 0x2
LACS  = 0x4
TACS  = 0x8
ATN   = 0x10
CIC   = 0x20
REM   = 0x40
LOK   = 0x80
CMPL  = 0x100
EVENT = 0x200
SPOLL = 0x400
RQS   = 0x800
SRQI  = 0x1000
END   = 0x2000
TIMO  = 0x4000
ERR   = 0x8000


if platform.system() == 'Linux':
    libname = find_library('gpib') # open source gpib driver
    ni_style = 0
    if not libname:
        libname =  find_library('gpibapi') # NI gpib driver
        ni_style = 1
    if not libname:
        raise ValueError, 'gpib library not found'
    gpiblib = CDLL(libname)

elif platform.system() == 'Windows':
    # docs say hardcorded name may be better on windows
    libname = find_library('ni4882')## or gpi32 ???
    if not libname:
        raise ValueError, 'NI488 library not found'
    ni_style = 1
    gpiblib = WinDLL(libname)

elif platform.system() == 'Darwin':##???
    libname = find_library('NI488')
    if not libname:
        raise ValueError, 'NI488 library not found'
    ni_style = 1
    gpiblib = CDLL(libname)

# try and replicate a useful subset of the library faithfully as possible

def ib_status(code):
    '''Given a ibsta code, return the text status [not working yet]'''
    result = ''
    
    status_strings = [ \
                      "Device Clear State. ", \
                      "Device Trigger State. ", \
                      "Listener. ", \
                      "Talker. ", \
                      "ATN line is asserted. ", \
                      "Controller-In-Charge. ", \
                      "Remote State. ", \
                      "Lockout State. ", \
                      "I/O completed. ", \
                      "", \
                      "", \
                      "Device requesting service. ", \
                      "SRQ line is asserted. ", \
                      "END or EOS detected. ", \
                      "Time limit exceeded. ", \
                      "GPIB error. " \
                      ]
    
    for i in range(16):
        print i, 2**i
        if (2**i) & code:
            result += status_strings[i]
    
    return result

def ib_error(code):
    '''Given an error code, return the error text. '''

    error_strings = [ \
                     "System error", \
                     "Function requires GPIB board to be CIC", \
                     "No Listeners on the GPIB", \
                     "GPIB board not addressed correctly", \
                     "Invalid argument to function call", \
                     "GPIB board not System Controller as required", \
                     "I/O operation aborted (timeout)", \
                     "Nonexistent GPIB board", \
                     "DMA error", \
                     "", \
                     "Asynchronous I/O in progress", \
                     "No capability for operation", \
                     "File system error", \
                     "", \
                     "GPIB bus error", \
                     "", \
                     "SRQ stuck in ON position", \
                     "", \
                     "", \
                     "", \
                     "Table problem", \
                     "Interface is locked", \
                     "Ibnotify callback failed to rearm", \
                     "Input handle is invalid", \
                     "", \
                     "", \
                     "Wait in progress on specified input handle", \
                     "Event notification was cancelled due to a reset of the interface", \
                     "The interface lost power" \
                     ]
    
    return error_strings[code]

def iberr():
    '''Returns the current error code'''
    #if not ni_style:
    #    return gpiblib.iberr # a constant?
    #else:
    #    return gpiblib.Iberr()
    result = c_int.in_dll(gpiblib, "iberr")

    return result.value

#def Iberr():
#    return iberr()

def ibwait(ud, status_mask = CMPL):
    '''wait for event (board or device)'''
    result = gpiblib.ibwait(ud, status_mask)
    
    return result

def ibdev(board_index=0, pad=0, sad=0, timeout=T10s, send_eoi=1, eos=0 ):
    '''Returns a device handle to device on board board_index at primary address pad'''
    ud = gpiblib.ibdev(board_index, pad, sad, timeout, send_eoi, eos)
    # error check on return code? (for all calls)

    return ud

def ibfind(devicename='gpib0'):
    '''finds a device by name (defined in /etc/gpib in linux ??? elsewhere)'''
    if not ni_style:
        result = gpiblib.ibfind(devicename)
    else:
        result = gpiblib.ibfindA(devicename)  #A for ascii, W for unicode?? OS X???
    
    return result

def ibrd(ud, length=512):  # what about bin vs ascii?
    '''Read data from a device into a user buffer'''
    #    result = c_char_p('\000'* length)
    result = create_string_buffer('\000', length)
    #    retval = gpiblib.ibrd(ud,addressof(result),length)
    retval = gpiblib.ibrd(ud, result, length)
    
    #print "string [%s]" % result.raw
    #print "raw", result.raw
    str = "%s" % result.raw
    
    return str

def ibrda(ud, length=512):  # what about bin vs ascii?
    '''Read data asynchronously from a device into a user buffer'''
    #    result = c_char_p('\000'* length)
    result = create_string_buffer('\000', length)
    #    retval = gpiblib.ibrd(ud,addressof(result),length)
    retval = gpiblib.ibrda(ud, result, length)
    
    str = "%s" % result.raw
    
    return str

def ibwrt(ud, data, length=None):
    '''Write data to a device from a user buffer'''
    if not length:
        length = len(data)
    result = gpiblib.ibwrt(ud, data, length)
    
    return result

def ibwrta(ud, data, length=None):
    '''Write data asynchronously to a device from a user buffer'''
    if not length:
        length = len(data)
    result = gpiblib.ibwrta(ud, data, length)
    
    return result

def ibsta():
    '''Get the status'''
    result = c_int.in_dll(gpiblib, "ibsta")

    return result.value

def ibclr(ud):
    '''Clear a specific device. Returns a ibsta value. '''
    result = gpiblib.ibclr(ud)

    return result

def ibonl(ud, v):
    '''Place the device or interface online or offline. v = 0 offline, v = 1 online. '''
    result = gpiblib.ibonl(ud, v)
    
    return result

def ibln(ud, pad = 0, sad = 0):
    '''check if listener is present (board or device)'''
    listen = c_short()
    result = gpiblib.ibln(ud, pad, sad, byref(listen))
    
    return listen.value

def ibloc(ud):
    '''Go to Local.'''
    result = gpiblib.ibloc(ud)
    
    return result

def ibcmd(ud, cmdbuf, length=None):
    '''Send GPIB commands.'''
    if not length:
        length = len(cmdbuf)
    
    result = gpiblib.ibcmd(ud, cmdbuf, length)

    return result

def ibcmda(ud, cmdbuf, length=None):
    '''Send GPIB commands asynchronously.'''
    if not length:
        length = len(cmdbuf)
    
    result = gpiblib.ibcmda(ud, cmdbuf, length)

    return result
