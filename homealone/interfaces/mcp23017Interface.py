from homealone import *
# import whichever gpio library is installed
try:
    import RPi.GPIO as gpio
    gpioLibrary = "RPi.GPIO"
except ImportError:
    import RPIO as gpio
    gpioLibrary = "RPIO"

# dictionary of MCP23017Interfaces indexed by their interrupt pins
gpioInterfaces = {}

# initial interrupt callback routine that is called when an interrupt pin goes low
def interruptCallback(pin, value=1):
    debug('debugGPIO', "interruptCallback", "pin:", pin, "value:", value)
    try:
        # call the interrupt routine for the MCP23017Interface associated with the pin
        gpioInterfaces[pin].interrupt()
    except KeyError:
        # the interrupt occurred on a pin not associated with a MCP23017Interface
        log("interruptCallback", "unknown interrupt", "pin:", pin, "value:", value, "gpioInterfaces:", gpioInterfaces)


# Interface to GPIO via MCP23017 I2C I/O expander
class MCP23017Interface(Interface):
    # MCP23017 I2C I/O expander
    IODIR = 0x00        # I/O direction
    IPOL = 0x02         # input polarity
    GPINTEN = 0x04      # interrupt on change
    DEFVAL = 0x06       # default value
    INTCON = 0x08       # interrupt control
    IOCON = 0x0a        # configuration
    GPPU = 0x0c         # pull up resistor
    INTF = 0x0e         # interrupt flag
    INTCAP = 0x10       # interrupt capture
    GPIO = 0x12         # I/O data
    OLAT = 0x14         # output latch

    # direct GPIO
    gpioPins = [12, 16, 18, 22, 15, 13, 11, 7]   # A/B
#            32, 36, 38, 40, 37, 35, 33, 31]     # B+

    def __init__(self, name, interface=None, event=None,
                                             addr=0x20,         # I2C address of MCP23017
                                             bank=0,            # bank within MCP23017 A=0, B=1
                                             inOut=0x00,        # I/O direction out=0, in=1
                                             interruptPin=17,   # RPIO pin used for interrupt (BCM number)
                                             config=[]):        # additional configuration
        Interface.__init__(self, name, interface=interface, event=event)
        global gpioInterfaces
        self.name = name
        if interface:
            self.addr = addr
            self.bank = bank
            self.inOut = inOut
            self.interruptPin = interruptPin+self.bank  # offset pin with bank
            self.config = config
            self.state = 0x00
            gpioInterfaces[self.interruptPin] = self
        else:
            self.interface = None
            self.bank = 0

    def start(self):
        debug('debugGPIO', self.name, "using GPIO library", gpioLibrary)
        gpio.setwarnings(False)
        if self.interface:
            gpio.setmode(gpio.BCM)
            # configure the MCP23017
            self.interface.write((self.addr, MCP23017Interface.IODIR+self.bank), self.inOut)    # I/O direction
            self.interface.write((self.addr, MCP23017Interface.GPINTEN+self.bank), self.inOut)  # enable interrupts for inputs
            self.interface.write((self.addr, MCP23017Interface.GPPU+self.bank), self.inOut)     # pull up resistors on inputs
            self.interface.write((self.addr, MCP23017Interface.IOCON), 0x04)                    # interrupt pins are open drain
            # additional configuration
            for config in self.config:
                reg = config[0]+self.bank   # offset register with bank
                debug('debugGPIO', self.name, "start", "addr: 0x%02x"%self.addr, "reg: 0x%02x"%reg, "value: 0x%02x"%config[1])
                self.interface.write((self.addr, reg), config[1])
            # get the current state
            self.readState()
            # set up the interrupt handling
            if gpioLibrary == "RPIO":
                gpio.add_interrupt_callback(self.interruptPin, interruptCallback, edge="falling", pull_up_down=gpio.PUD_UP)
                gpio.wait_for_interrupts(threaded=True)
            elif gpioLibrary == "RPi.GPIO":
                gpio.setup(self.interruptPin, gpio.IN, pull_up_down=gpio.PUD_UP)
                gpio.add_event_detect(self.interruptPin, gpio.FALLING, callback=interruptCallback)
        else:   # direct only supports output - FIXME
            gpio.setmode(gpio.BOARD)
            for pin in MCP23017Interface.gpioPins:
                debug('debugGPIO', self.name, "setup", pin, gpio.OUT)
                gpio.setup(pin, gpio.OUT)
                debug('debugGPIO', self.name, "write", pin, 0)
                gpio.output(pin, 0)

    # interrupt handler for this interface
    def interrupt(self):
        intFlags = self.interface.read((self.addr, MCP23017Interface.INTF+self.bank))
        debug('debugGPIO', self.name, "interrupt", "addr: 0x%02x"%self.addr, "bank:", self.bank, "intFlags: 0x%02x"%intFlags)
        self.readState()
        for i in range(8):
            if (intFlags >> i) & 0x01:
                try:
                    sensor = self.sensorAddrs[i]
                    state = (self.state >> i) & 0x01
                    debug('debugGPIO', self.name, "notifying", sensor.name, state)
                    sensor.notify(state)
                except KeyError:
                    debug('debugGPIO', self.name, "no sensor for interrupt on addr", i, self.sensorAddrs)


    def read(self, addr):
        if self.interface:
            self.readState()
            return (self.state >> addr) & 0x01
        else:
            return 0

    def readState(self):
        byte = self.interface.read((self.addr, MCP23017Interface.GPIO+self.bank))
        debug('debugGPIO', self.name, "read", "addr: 0x%02x"%self.addr, "reg: 0x%02x"%(MCP23017Interface.GPIO+self.bank), "value: 0x%02x"%byte)
        self.state = byte

    def write(self, addr, value):
        if self.interface:
            byte = self.state
            mask = 0x01<<addr
            byte = (byte & (~mask)) | ((value << addr) & mask)
            debug('debugGPIO', self.name, "write", "addr: 0x%02x"%self.addr, "reg: 0x%02x"%(MCP23017Interface.GPIO+self.bank), "value: 0x%02x"%byte)
            self.interface.write((self.addr, MCP23017Interface.GPIO+self.bank), byte)
            self.state = byte
        else:
            debug('debugGPIO', self.name, "write", "addr: 0x%02x"%addr, "value: 0x%02x"%value)
            gpio.output(MCP23017Interface.gpioPins[addr], value)
