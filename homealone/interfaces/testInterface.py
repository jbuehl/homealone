
from homealone.core import *

# Dummy test interface
class TestInterface(Interface):
    def __init__(self, name, interface=None, event=None, **params):
        Interface.__init__(self, name, interface=interface, event=event)

    def read(self, addr):
        return 0

    def write(self, addr, value):
        return True
