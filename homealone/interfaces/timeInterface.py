from homealone import *
import time
import os
import datetime
import pytz

class TimeInterface(Interface):
    def __init__(self, name, interface=None, event=None, clock=None, latLong=None, tz=None):
        Interface.__init__(self, name, interface, event)
        self.clock = None
        # interface: optional gps location data file
        if interface:
            self.clock = "gps"
            import timezonefinder
            self.timeZoneFinder = timezonefinder.TimezoneFinder()
        # clock: time source
        #   local - system clock is local tz (default)
        #   utc - system clock is UTC
        #   gps - gps time via file interface
        if clock:
            self.clock = clock
        else:
            if not self.clock:
                self.clock = "local"
        # latLong: location coordinates as tuple(lat, long)
        if latLong:
            self.latLong = latLong
        else:
            self.latLong = (0, 0)
        # tz: time zone in Olson format (e.g. "America/Los_Angeles")
        if tz:
            self.tz = tz
        else:
            if self.clock == "local":   # local TZ if clock is local
                self.tz = '/'.join(os.readlink('/etc/localtime').split('/')[-2:])
            else:
                self.tz = "UTC"

        debug('debugTime', self.name, "clock:", self.clock, "latLong:", self.latLong, "tz:", self.tz)

    def read(self, addr=None):
        # get gps location and figure out the time zone
        if self.interface:
            self.latLong = (self.interface.read("Lat"), self.interface.read("Long"))
            if self.latLong == (0, 0):
                self.tz = "UTC"
            else:
                self.tz = self.timeZoneFinder.timezone_at(lat=self.latLong[0], lng=self.latLong[1])
            debug('debugTime', self.name, "lat:", self.latLong[0], "long:", self.latLong[1], "tz:", self.tz)
        # get the naive UTC time
        if self.clock == "gps":                 # from file
            utcNow = datetime.datetime(*time.strptime(self.interface.read("Time"), "%Y-%m-%d %H:%M:%S")[0:6])
        elif self.clock in ["utc", "local"]:    # from system clock
            utcNow = datetime.datetime.utcnow()
        # convert to TZ aware local time
        localNow = utcNow.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(self.tz))
        debug('debugTime', self.name, "now:", localNow, "tz:", self.tz, "latLong:", self.latLong)
        # return the requested item
        if addr:
            if addr == "daylight":
                return normalState(sunIsUp(localNow, self.latLong))
            elif addr == "sunrise":
                return sunrise(localNow, self.latLong).strftime("%I:%M %p").lstrip("0")
            elif addr == "sunset":
                return sunset(localNow, self.latLong).strftime("%I:%M %p").lstrip("0")
            elif addr == "timeZone":
                return self.tz
            elif addr == "timeZoneName":
                try:
                    return pytz.timezone(self.tz).tzname(utcNow)
                except pytz.exceptions.AmbiguousTimeError:
                    return "WTF"
            else:
                return time.strftime(addr, localNow.timetuple()).lstrip("0")
        else:
            return time.asctime()
