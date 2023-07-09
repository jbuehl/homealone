from homealone import *

# TC74 temp sensor

class TC74Interface(Interface):
    def __init__(self, name, interface, scale="F"):
        Interface.__init__(self, name, interface)
        self.scale = scale.upper()

    def read(self, addr):
        debug('debugTemp', self.name, "read", addr)
        try:
            value = self.interface.read((addr, 0))
            if value > 127:
                value = (256-value) * (-1)
            if self.scale == "F":
                value = float(value) * 9 / 5 + 32
            return value
        except:
            return 0
