
import RPi.GPIO as gpio
from homealone import *

# available GPIO pins
if int(gpio.RPI_INFO['REVISION'], 16) < 0x0010:
    bcmPins = [4, 17, 18, 22, 23, 24, 25, 27] # A/B
else:
    bcmPins = [0, 1, 4, 5, 6, 7, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27] # B+,02W
    # bcmPins = [4, 5, 6, 12, 13, 16, 17, 18, 22, 23, 24, 25, 26, 27] # B+

# pin mapping to RPi expander v2.0
#   23,  7,  1, 12, 16,  5,  0, 27      # expansion board 1
#   21, 20, 26, 19, 13,  6, 22, 17      # expansion board 2
#   14, 15                              # serial
#   18                                  # PCM
#    2,  3                              # I2C
#    4                                  # 1-wire

gpioInterface = None

# initial interrupt callback routine that is called when an interrupt pin changes
def interruptCallback(pin):
    debug('debugGPIOinterrupt', "interruptCallback", "pin:", pin)
    try:
        sensor = gpioInterface.sensorAddrs[pin]
        state = gpio.input(pin)
        if sensor.interrupt:
            debug('debugGPIOinterrupt', gpioInterface.name, "calling", sensor.name, "interrupt", state)
            sensor.interrupt(sensor, state)
        debug('debugGPIOinterrupt', gpioInterface.name, "notifying", sensor.name, state)
        sensor.notify(state)
    except KeyError:
        debug('debugGPIOinterrupt', gpioInterface.name, "no sensor for interrupt on pin", pin)

# Interface to direct GPIO
class GPIOInterface(Interface):
    def __init__(self, name, interface=None, event=None, input=[], output=[], inverts=[], invert=False):
        Interface.__init__(self, name, interface=interface, event=event)
        global gpioInterface
        gpioInterface = self
        self.input = input
        self.output = output
        self.inverts = inverts
        # initialize everything
        gpio.setwarnings(False)
        gpio.setmode(gpio.BCM)
        # set I/O direction of pins
        for pin in self.input:
            if pin in bcmPins:
                debug('debugGPIO', self.name, "setup", pin, gpio.IN)
                gpio.setup(pin, gpio.IN, pull_up_down=gpio.PUD_UP)
                gpio.add_event_detect(pin, gpio.BOTH, callback=interruptCallback)
            else:
                debug('debugGPIO', self.name, "ignoring", pin)
        for pin in self.output:               # output pin
            if pin in bcmPins:
                debug('debugGPIO', self.name, "setup", pin, gpio.OUT)
                gpio.setup(pin, gpio.OUT)
                self.states[pin] = 0
                debug('debugGPIO', self.name, "write", pin, 0)
                if pin in self.inverts:
                    gpio.output(pin, 1)
                else:
                    gpio.output(pin, 0)
            else:
                debug('debugGPIO', self.name, "ignoring", pin)

    def read(self, addr):
        if addr in self.input:
            value = gpio.input(addr)
            if addr in self.inverts:
                value = 1 - value
            debug('debugGPIO', self.name, "read", "addr:", addr, "value:", value)
            return value
        elif addr in self.output:
            debug('debugGPIO', self.name, "read", "addr:", addr, "value:", self.states[addr])
            return self.states[addr]
        else:
            debug('debugGPIO', self.name, "read", "addr:", addr, "invalid")
            return None

    def write(self, addr, value):
        if addr in self.output:
            debug('debugGPIO', self.name, "write", "addr:", addr, "value:", value)
            self.states[addr] = value
            if addr in self.inverts:
                value = 1 - value
            gpio.output(addr, value)
        else:
            debug('debugGPIO', self.name, "write", "addr:", addr, "invalid")
