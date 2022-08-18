
import time
import threading
from homealone import *
from homealone.resources.extraResources import *

# Compute power using a current measurement and a voltage measurement
# Voltage can either be from a specified sensor or a constant
class PowerSensor(Sensor):
    def __init__(self, name, interface=None, addr=None, currentSensor=None, voltageSensor=None, voltage=0.0, powerFactor=1.0, **kwargs):
        Sensor.__init__(self, name, interface, addr, **kwargs)
        self.className = "Sensor"
        self.currentSensor = currentSensor
        self.voltageSensor = voltageSensor
        self.voltage = voltage
        self.powerFactor = powerFactor

    def getState(self, missing=0.0):
        if self.voltageSensor:
            self.voltage = self.voltageSensor.getState(missing=0.0)
        power = self.currentSensor.getState(missing=0.0) * self.voltage * self.powerFactor
        return round(power * self.factor, self.resolution)

# Compute battery percentage using a voltage measurement
socLevels = {
            "AGM": [10.50, 11.51, 11.66, 11.81, 11.95, 12.05, 12.15, 12.30, 12.50, 12.75]
}
class BatterySensor(Sensor):
    def __init__(self, name, interface=None, addr=None, voltageSensor=None, batteryType="AGM", threshold=0.0, **kwargs):
        Sensor.__init__(self, name, interface, addr, **kwargs)
        self.className = "Sensor"
        self.voltageSensor = voltageSensor
        self.batteryType = batteryType
        self.threshold = threshold
        self.lastLevel = 0.0
        try:
            self.chargeLevels = socLevels[self.batteryType]
        except KeyError:
            self.chargeLevels = [0.0]*10

    def getState(self, missing=0.0):
        voltage = self.voltageSensor.getState(missing=0.0)

        # Use table lookup
        # level = 100
        # for chargeLevel in self.chargeLevels:
        #     if voltage < chargeLevel:
        #         level = self.chargeLevels.index(chargeLevel) * 10
        #         break

        # Calculate the percentage -  https://mycurvefit.com/
        if voltage > 13.0:
            level = 100.0
        else:
            level = 43940.64 - 11224.35*voltage + 949.6667*voltage**2 - 26.59379*voltage**3

        if level > self.threshold:
            if abs(level - self.lastLevel) > self.threshold:
                self.notify()
            self.lastLevel = level
            return level
        else:
            self.lastLevel = level
            return 0.0

# Accumulate the energy of a power measurement over time
class EnergySensor(Sensor):
    def __init__(self, name, interface=None, addr=None, powerSensor=None, poll=10, persistence=None, initial=0.0, **kwargs):
        Sensor.__init__(self, name, interface, addr, poll=poll, **kwargs)
        self.className = "Sensor"
        self.powerSensor = powerSensor
        self.persistence = persistence  # FileInterface for state persistence
        self.initial = initial
        if self.persistence:
            self.stateControl = StateControl(self.name+"State", self.persistence, self.name, initial=self.initial)
            self.energy = self.stateControl.getState(missing=0.0)
        else:
            self.energy = 0.0
        self.lastTime = time.time()

    def getState(self, missing=0.0):
        value = self.powerSensor.getState(missing=0.0)
        curTime = time.time()
        interval = curTime - self.lastTime
        self.lastTime = curTime
        self.energy += value * interval / 3600
        debug("debugEnergy", self.name, value, self.energy)
        if self.persistence:
            self.stateControl.setState(self.energy)
        return round(self.energy * self.factor, self.resolution)

    def setState(self, value):
        self.energy = value
        if self.persistence:
            self.stateControl.setState(value)

# ADS1x15 sensor
class ADSSensor(Sensor):
    def __init__(self, name, interface=None, addr=None, gain=4096, **kwargs):
        Sensor.__init__(self, name, interface, addr, **kwargs)
        self.className = "Sensor"
        self.gain = gain

    def getState(self, missing=0.0):
        self.interface.gain = self.gain
        value = round(self.interface.read(self.addr) * self.factor, self.resolution)
        debug('debugAds', self.name, "value", value)
        return value
