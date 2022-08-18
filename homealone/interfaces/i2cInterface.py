
import smbus
from homealone import *

class I2CInterface(Interface):
    def __init__(self, name, interface=None, event=None, bus=0):
        Interface.__init__(self, name, interface=interface, event=event)
        self.bus = smbus.SMBus(bus)

    def read(self, addr):
        try:
            debug('debugI2C', self.name, "readByte", addr)
            return self.bus.read_byte_data(*addr)
        except OSError:
            return 0

    def readWord(self, addr):
        try:
            debug('debugI2C', self.name, "readWord", addr)
            return self.bus.read_word_data(*addr)
        except OSError:
            return 0

    def readBlock(self, addr, reg, length):
        try:
            debug('debugI2C', self.name, "readBlock", addr, reg, length)
            return self.bus.read_i2c_block_data(addr, reg, length)
        except OSError:
            return [0, 0]

    def write(self, addr, value):
        try:
            debug('debugI2C', self.name, "writeByte", addr, value)
            self.bus.write_byte_data(*addr+(value,))
        except OSError:
            return 0

    def writeWord(self, addr, value):
        try:
            debug('debugI2C', self.name, "writeWord", addr, value)
            self.bus.write_word_data(*addr+(value,))
        except OSError:
            return 0

    def writeBlock(self, addr, reg, list):
        try:
            debug('debugI2C', self.name, "writeBlock", addr, reg, list)
            self.bus.write_i2c_block_data(addr, reg, list)
        except OSError:
            return []

    def writeQuick(self, addr):
        try:
            debug('debugI2C', self.name, "writeQuick", addr)
            self.bus.write_quick(addr)
        except OSError:
            return 0
