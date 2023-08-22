# Core class definitions

import time
import threading
import copy
from collections import OrderedDict
from rutifu import *
from .utils import *

# sensor states
off = 0
Off = 0
on = 1
On = 1

# normalize state values from boolean to integers
def normalState(value):
    if value == True: return On
    elif value == False: return Off
    else: return value

# Abstract base class for everything
class Object(object):
    def __init__(self):
        self.className = self.__class__.__name__    # Used to optionally override the real class name in dump()

    # dump the resource attributes to a serialized dict
    def dump(self, expand=False):
        return {"class": self.className,
                "args": self.dict(expand)}

# Abstract base class for Resources
class Resource(Object):
    def __init__(self, name, event):
        Object.__init__(self)
        try:
            if self.name:   # init has already been called for this object
                # log("Resource", self.name, "already initialized")
                return
        except AttributeError:
            self.name = name
            self.event = event
            self.enabled = True
            self.collections = {}   # list of collections that include this resource

    # enable the resource
    def enable(self):
        self.enabled = True

    # disable the resource
    def disable(self):
        if self.enabled:
            self.enabled = False
            if self.interface:
                self.interface.states[self.name] = None

    # trigger the sending of a state change notification
    def notify(self, state=None):
        if self.event:
            self.event.set()

    # add this resource to the specified collection
    def addCollection(self, collection):
        self.collections[collection.name] = collection

    # remove this resource from the specified collection
    def delCollection(self, collection):
        del self.collections[collection.name]

    # jquery doesn't like periods in names
    def jqName(self):
        return self.name.replace(".", "_")

    def __str__(self):
        return self.name

# Abstract base class for Interfaces
class Interface(Resource):
    def __init__(self, name, interface=None, event=None):
        Resource.__init__(self, name, event)
        self.interface = interface
        if (self.interface) and (not self.event):
            self.event = interface.event    # inherit event from this interface's interface
        self.sensors = {}       # sensors using this instance of the interface by name
        self.sensorAddrs = {}   # sensors using this instance of the interface by addr
        self.states = {}        # sensor state cache

    def start(self):
        return True

    def stop(self):
        return True

    def read(self, addr):
        return None

    def write(self, addr, value):
        return True

    def dump(self):
        return None

    # add a sensor to this interface
    def addSensor(self, sensor):
        self.sensors[sensor.name] = sensor
        self.sensorAddrs[sensor.addr] = sensor
        self.states[sensor.addr] = None
        sensor.event = self.event

# Resource collection
class Collection(Resource, OrderedDict):
    def __init__(self, name, resources=[]):
        Resource.__init__(self, name, None)
        OrderedDict.__init__(self)
        self.lock = threading.Lock()
        for resource in resources:
            self.addRes(resource)

    # Add a list of resources to this collection
    def addRes(self, resources, state=None):
        if not isinstance(resources, list):
            resources = [resources]
        for resource in resources:
            with self.lock:
                try:
                    self.__setitem__(str(resource), resource)
                    resource.addCollection(self)
                except Exception as ex:
                    logException(self.name+" addRes", ex)

    # Delete a list of resources from this collection
    def delRes(self, names):
        if not isinstance(names, list):
            names = [names]
        for name in names:
            with self.lock:
                try:
                    self.__getitem__(name).delCollection(self)
                    self.__delitem__(name)
                except Exception as ex:
                    logException(self.name+" delRes", ex)

    # Get a resource from the collection
    # Return dummy sensor if not found
    def getRes(self, name, dummy=True):
        try:
            return self.__getitem__(name)
        except KeyError:
            if dummy:
                return Sensor(name)
            else:
                raise

    # Return the list of resources that have the names specified in the list
    def getResList(self, names):
        resList = []
        for name in names:
            try:
                resList.append(self.getRes(name))
            except:
                pass
        return resList

    # Return a list of resource references that are members of the specified group
    # in order of addition to the table
    def getGroup(self, group):
        resourceList = []
        for resourceName in list(self.keys()):
            resource = self.__getitem__(resourceName)
            if group in listize(resource.group):
                resourceList.append(resource)
        return resourceList

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        return {"name":self.name,
                "resources":([attr.dump(expand) for attr in list(self.values())] if expand else list(self.keys()))}

# A Sensor represents a device that has a state that is represented by a scalar value.
# The state is associated with a unique address on an interface.
# Sensors can also optionally be associated with a group and a physical location.
class Sensor(Resource):
    def __init__(self, name, interface=None, addr=None, type=None, style="sensor", event=None,
                 factor=1, offset=0, resolution=0, poll=10, persistence=None, interrupt=None,
                 label="", group="", location=None):
        Resource.__init__(self, name, event)
        self.interface = interface
        self.addr = addr
        self.type = type
        if not type:
            self.type = style
        if self.interface:
            self.interface.addSensor(self)
        if (self.interface) and (not self.event):
            self.event = interface.event    # inherit event from the interface
        self.resolution = resolution
        self.factor = factor
        self.offset = offset
        self.poll = poll
        self.persistence = persistence
        self.interrupt = interrupt
        self.location = location
        self.group = listize(group)
        self.label = label
        self.__dict__["state"] = None   # dummy class variable so hasattr() returns True
        # FIXME - use @property

    # Return the state of the sensor by reading the value from the address on the interface.
    def getState(self, missing=None):
        state = (normalState(self.interface.read(self.addr)) if self.interface else None)
        try:
            return round(state * self.factor + self.offset, self.resolution)
        except TypeError:
            return state

    # Define this function for sensors even though it does nothing
    def setState(self, state, wait=False):
        debug('debugState', "Sensor", self.name, "setState ", state)
        return False

    # override to handle special cases of state
    def __getattribute__(self, attr):
        if attr == "state":
            return self.getState()
        else:
            return Resource.__getattribute__(self, attr)

    # override to handle special case of state
    def __setattr__(self, attr, value):
        if attr == "state":
            self.setState(value)
        else:
            Resource.__setattr__(self, attr, value)

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        return {"name":self.name,
                "interface":(self.interface.name if self.interface else None),
                "addr":self.addr,
                "type":self.type,
                "resolution": self.resolution,
                "poll": self.poll,
                "persistence": str(self.persistence),
                "location":self.location,
                "group":self.group,
                "label":self.label}

# A Control is a Sensor whose state can be set
class Control(Sensor):
    def __init__(self, name, interface=None, addr=None, type=None, style="control", stateSet=None, **kwargs):
        Sensor.__init__(self, name, interface=interface, addr=addr, type=type, style=style, **kwargs)
        self.stateSet = stateSet  # optional callback when state is set

    # Set the state of the control by writing the value to the address on the interface.
    def setState(self, state, wait=False):
        debug('debugState', "Control", self.name, "setState ", state)
        debug("debugState", self.interface.name, self.addr)
        if self.enabled:
            self.interface.write(self.addr, state)
            self.notify(state)
            if self.stateSet:
                self.stateSet(self, state)
            return True
        else:
            return False
