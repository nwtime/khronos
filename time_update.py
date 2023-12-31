'''Copyright (c) <2019> <Neta Rozen Schiff>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''

# Inspired by https://stackoverflow.com/questions/12081310/python-module-to-change-system-date-and-time
import sys
import datetime


if sys.platform.startswith('linux'):
    import ctypes
    import ctypes.util
    import time

    # /usr/include/linux/time.h:
    #
    # define CLOCK_REALTIME                     0
    CLOCK_REALTIME = 0

    # /usr/include/time.h
    #
    # struct timespec
    #  {
    #    __time_t tv_sec;            /* Seconds.  */
    #    long int tv_nsec;           /* Nanoseconds.  */
    #  };
    class timespec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long),
                    ("tv_nsec", ctypes.c_long)]


    # struct timeval
    # {
    #     time_t tv_sec; / *seconds * /
    #     suseconds_t tv_usec; / *microseconds * /
    # };
    class timeval(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long),
                    ("tv_usec", ctypes.c_long)]

    librt = ctypes.CDLL(ctypes.util.find_library("rt"))


elif  sys.platform=='win32':
    import win32api # pywin32


def _win_set_time_tuple(time_tuple):
    # http://timgolden.me.uk/pywin32-docs/win32api__SetSystemTime_meth.html
    # pywin32.SetSystemTime(year, month , dayOfWeek , day , hour , minute , second , millseconds )
    dayOfWeek = datetime.datetime(time_tuple).isocalendar()[2]
    win32api.SetSystemTime( time_tuple[:2] + (dayOfWeek,) + time_tuple[2:])


def _linux_set_time_tuple(time_tuple):
    ts = timespec()
    ts.tv_sec = int( time.mktime( datetime.datetime( *time_tuple[:6]).timetuple() ) )
    ts.tv_nsec = time_tuple[6] * 1000000 # Millisecond to nanosecond

    # http://linux.die.net/man/3/clock_settime
    librt.clock_settime(CLOCK_REALTIME, ctypes.byref(ts))


def _linux_set_time_sec(sec):
    ts = timespec()
    ts.tv_sec = int(sec)
    ts.tv_nsec = int((sec%1) * 1000000000)

    # http://linux.die.net/man/3/clock_settime
    res = librt.clock_settime(CLOCK_REALTIME, ctypes.byref(ts))
    return res


def _linux_adjtime(sec):
    tv = timeval()
    tv.tv_sec = long(sec)
    if sec > 0:
        tv.tv_usec = long((sec%1) * 1000000)
    else:
        tv.tv_usec = -long((-sec % 1) * 1000000)
    tv2 = timeval()
    # http://linux.die.net/man/3/adjtime
    res = librt.adjtime(ctypes.byref(tv), ctypes.byref(tv2))
    return res, tv2.tv_sec + tv2.tv_usec/1000000.0


def _linux_adjtime_quick(sec):
    return  _linux_set_time_sec(time.time()+sec)


def set_time_tuple(time_tuple):
    if sys.platform.startswith('linux'):
        _linux_set_time_tuple(time_tuple)
    elif sys.platform == 'win32':
        _win_set_time_tuple(time_tuple)


def test_set_time_tuple():
    time_tuple = (2012,  # Year
                  9,  # Month
                  6,  # Day
                  0,  # Hour
                  38,  # Minute
                  0,  # Second
                  0,  # Millisecond
                  )
    set_time_tuple(time_tuple)


def set_time_sec(sec):
    if sys.platform.startswith('linux'):
        _linux_set_time_sec(sec)
    elif sys.platform == 'win32':
        raise Exception("_win_set_time_sec not implemented yet")
        #_win_set_time_sec(time_tuple)


if __name__ == "__main__":
    import os
    dif = int(os.sys.argv[1])
    print _linux_adjtime(dif/1000.0)
