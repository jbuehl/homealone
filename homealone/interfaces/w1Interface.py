from w1thermsensor import W1ThermSensor
from w1thermsensor import errors
from homealone import *

# One Wire interface

class W1Interface(Interface):
    def __init__(self, name, interface=None, event=None):
        Interface.__init__(self, name, interface=interface, event=event)

    def start(self, notify=None):
        self.getSensors()
        startThread(name="readStateThread", target=self.readStates, notify=notify)

    def getSensors(self):
        self.sensors = {}
        for sensor in W1ThermSensor.get_available_sensors():
            self.sensors[sensor.id.lower()] = sensor

    # thread to constantly read and cache values
    def readStates(self):
        while True:
            for sensor in list(self.sensors.keys()):
                try:
                    self.states[sensor.lower()] = float(self.sensors[sensor].get_temperature()) * 9 / 5 + 32
                except KeyError:                        # sensor wasn't previously detected
                    self.states[sensor.lower()] = None
                except errors.SensorNotReadyError:      # sensor isn't responding
                    log(self.name, sensor, "not responding")
                    self.getSensors()
                    self.states[sensor.lower()] = None
                time.sleep(1)

    def read(self, addr):
        return self.states[addr.lower()]
