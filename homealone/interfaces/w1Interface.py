from w1thermsensor import W1ThermSensor
from w1thermsensor import errors
from homealone import *

class W1Interface(Interface):
    def __init__(self, name, interface=None, event=None):
        Interface.__init__(self, name, interface=interface, event=event)
        self.sensors = {}
        for sensor in W1ThermSensor.get_available_sensors():
            self.sensors[sensor.id] = sensor

    def read(self, addr):
        try:
            return round(float(self.sensors[addr].get_temperature()) * 9 / 5 + 32, 2)
        except KeyError:
            return 0
        except errors.SensorNotReadyError:    # sensor isn't responding
            self.sensors = {}
            for sensor in W1ThermSensor.get_available_sensors():
                self.sensors[sensor.id] = sensor
            return 0
