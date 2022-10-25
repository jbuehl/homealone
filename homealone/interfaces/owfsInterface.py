from homealone import *

# One Wire File System interface

class OWFSInterface(Interface):
    def __init__(self, name, interface=None, home="/mnt/1wire/", event=None):
        Interface.__init__(self, name, interface, event=event)
        self.home = home

    def read(self, addr):
        debug('debugTemp', self.name, "read", addr)
        try:
            with open(self.home+addr+"/temperature") as owfs:
                value = owfs.read()
                try:
                    return float(value)
                except Exception as ex:
                    logException(self.name, addr, str(value), ex)
                    return 0
        except:
            return 0
