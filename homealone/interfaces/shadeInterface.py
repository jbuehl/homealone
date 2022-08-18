
import time
import threading
from homealone.interfaces.gpioInterface import *
from homealone import *

# shade states
shadeUp = 0
shadeDown = 1
shadeRaising = 2
shadeLowering = 3

travelTime = [15, 15, 12, 12]

class ShadeInterface(Interface):
    def __init__(self, name, interface=None, gpioPins=None, event=None):
        Interface.__init__(self, name, interface=interface, event=event)
        self.gpioPins = gpioPins
        if not self.gpioPins:
            self.gpioPins = [18, 23, 24, 25, 22, 27, 17, 4]
        self.timers = [None, None, None, None]
        self.lock = threading.Lock()

    def addSensor(self, sensor):
        Interface.addSensor(self, sensor)
        self.states[sensor.addr] = 0    # initialize state to 0

    def read(self, addr):
        try:
            return self.states[addr]
        except:
            return 0

    def write(self, addr, value):
        self.newValue = value
        self.states[addr] = value + 2  # moving
        self.sensorAddrs[addr].notify()
        debug('debugShades', self.name, "state", addr, self.states[addr])
        # cancel the timer if it is running
        if self.timers[addr]:
            self.timers[addr].cancel()
        with self.lock:
            # set the direction
            debug('debugShades', self.name, "direction", addr, value)
            self.interface.write(self.gpioPins[addr*2], value)
            # start the motion
            debug('debugShades', self.name, "motion", addr, 1)
            self.interface.write(self.gpioPins[addr*2+1], 1)
        # clean up and set the final state when motion is finished
        def doneMoving():
            with self.lock:
                # stop the motion
                debug('debugShades', self.name, "motion", addr, 0)
                self.interface.write(self.gpioPins[addr*2+1], 0)
                # reset the direction
                debug('debugShades', self.name, "direction", addr, 0)
                self.interface.write(self.gpioPins[addr*2], 0)
                self.states[addr] = self.newValue # done moving
                self.sensorAddrs[addr].notify()
                debug('debugShades', self.name, "state", addr, self.states[addr])
        self.timers[addr] = threading.Timer(travelTime[addr], doneMoving)
        self.timers[addr].start()
