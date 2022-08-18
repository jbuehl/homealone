from homealone import *

# TC74 temp sensor

class TC74Interface(Interface):
    def __init__(self, name, interface):
        Interface.__init__(self, name, interface)

    def read(self, addr):
        debug('debugTemp', self.name, "read", addr)
        try:
            value = self.interface.read((addr, 0))
            if value > 127:
                value = (256-value) * (-1)
            return float(value) * 9 / 5 + 32
        except:
            return 0
