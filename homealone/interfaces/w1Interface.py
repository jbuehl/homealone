from w1thermsensor import W1ThermSensor
from w1thermsensor import errors
from homealone import *

class W1Interface(Interface):
    def __init__(self, name, interface=None, event=None):
        Interface.__init__(self, name, interface=interface, event=event)
        self.getSensors()

    def getSensors(self):
        self.sensors = {}
        for sensor in W1ThermSensor.get_available_sensors():
            self.sensors[sensor.id.upper()] = sensor

    def read(self, addr):
        try:
            return float(self.sensors[addr.upper()].get_temperature()) * 9 / 5 + 32
        except KeyError:                        # sensor wasn't previously detected
            return 0
        except errors.SensorNotReadyError:      # sensor isn't responding
            log(self.name, addr, "not responding")
            self.getSensors()
            return 0
