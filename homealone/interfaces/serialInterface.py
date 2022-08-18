import serial
import sys
from homealone import *

class SerialInterface(Interface):
    def __init__(self, name, interface=None, event=None, device="", config={}):
        Interface.__init__(self, name, interface=interface, event=event)
        self.device = device
        self.config = config

    def start(self):
        if self.device == "/dev/stdin":
            log(self.name, "using stdin", self.device)
            self.inPort = sys.stdin
            self.outPort = sys.stdout
        else:
            try:
                log(self.name, "opening serial port", self.device)
                self.inPort = self.outPort = serial.Serial(self.device, **self.config)
            except:
                log(self.name, "unable to open serial port")
                return

    def stop(self):
        if self.device != "/dev/stdin":
            self.inPort.close()

    def read(self, addr, theLen=1):
        return self.inPort.read(theLen)

    def write(self, addr, value):
        self.outPort.write(value)

    def readline(self, addr):
        return self.inPort.readline()

    def writeline(self, addr, value):
        self.outPort.writeline(value)
