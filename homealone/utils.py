# Utility functions

pollResolution = 10 # how many times per second to possibly check for resource state changes

import syslog
import os
import time
import threading
import traceback
import json
import copy
import subprocess
from rutifu import *
from .core import *
from .env import *

# Resource collection state cache
class StateCache(object):
    def __init__(self, name, resources, event, start=False):
        self.name = name
        self.resources = resources
        self.resourceEvent = event          # externalresource state change event
        self.stateEvent = threading.Event() # state change event
        self.noneState = False              # at least one state is invalid
        self.states = {}                    # cache of current sensor states
        if start:
            self.start()

    def start(self):
        # initialize the resource state cache
        debug("debugStateCache", self.name, "starting")
        for resource in list(self.resources.values()):
            if isinstance(resource, Sensor):   # skip resources that don't have a state
                try:
                    self.states[resource.name] = resource.getState()    # load the initial state
                except Exception as ex:
                    logException(self.name+" start", ex)
        startThread("pollStatesThread", self.pollStatesThread)
        startThread("watchEventsThread", self.watchEventsThread)

    # thread to periodically poll the state of the resources in the collection
    def pollStatesThread(self):
        debug("debugStateCache", self.name, "starting pollStatesThread")
        resourcePollCounts = {}
        while True:
            stateChanged = False
            debug("debugStateCache", self.name, "polling", len(self.resources), "resources")
            with self.resources.lock:
                for resource in list(self.resources.values()):
                    try:
                        if isinstance(resource, Sensor) and \
                                (resource.enabled) and (not resource.event):            # only poll enabled sensors without events
                            if resource.name not in list(resourcePollCounts.keys()):    # a resource not seen before
                                resourcePollCounts[resource.name] = resource.poll * pollResolution
                                self.states[resource.name] = resource.getState()
                                stateChanged = True
                            if resourcePollCounts[resource.name] == 0:                  # count has decremented to zero
                                resourceState = resource.getState()
                                if resourceState != self.states[resource.name]:         # save the state if it has changed
                                    self.states[resource.name] = resourceState
                                    stateChanged = True
                                if resourceState is None:
                                    self.noneState = True
                                resourcePollCounts[resource.name] = resource.poll * pollResolution
                            else:   # decrement the count
                                resourcePollCounts[resource.name] -= 1
                    except KeyError:
                        log(self.name, "no previous state", resource.name)
                    except Exception as ex:
                        logException(self.name+" pollStates", ex)
            if stateChanged:    # at least one resource state changed
                self.stateEvent.set()
                stateChanged = False
            time.sleep(1 / pollResolution)

    # thread to watch for state change events
    def watchEventsThread(self):
        debug("debugStateCache", self.name, "starting watchEventsThread")
        while True:
            debug("debugStateCache", self.name, "waiting for", len(self.resources), "resources")
            self.resourceEvent.clear()
            self.resourceEvent.wait()
            debug("debugStateCache", self.name, "state change event")
            stateChanged = False
            with self.resources.lock:
                for resource in list(self.resources.values()):
                    try:
                        if resource.event:                                      # only get resources with events
                            resourceState = resource.getState()
                            if resourceState != self.states[resource.name]:     # save the state if it has changed
                                self.states[resource.name] = resourceState
                                stateChanged = True
                            if resourceState is None:
                                self.noneState = True
                    except KeyError:                                            # resource hasn't been seen before, save the state
                        self.states[resource.name] = resourceState
                    except Exception as ex:
                        logException(self.name+" watchEvents", ex)
            if stateChanged:    # at least one resource state changed
                self.stateEvent.set()
                stateChanged = False

    # wait for a change and return the current state of all sensors in the resource collection
    def getStates(self, wait=True):
        if wait:
            self.noneState = False
            self.stateEvent.clear()
            self.stateEvent.wait()
        return copy.copy(self.states)

    # set the state of the specified sensor in the cache
    def setState(self, sensor, state):
        self.states[sensor.name] = state

    # set state values of all sensors into the cache
    def setStates(self, states):
        for sensor in list(states.keys()):
            self.states[sensor] = states[sensor]

# Compare two state dictionaries and return a dictionary containing the items
# whose values don't match or aren't in the old dict.
# If an item is in the old but not in the new, optionally include the item with value None.
def diffStates(old, new, deleted=True):
    diff = copy.copy(new)
    for key in list(old.keys()):
        try:
            if new[key] == old[key]:
                del diff[key]   # values match
        except KeyError:        # item is missing from the new dict
            if deleted:         # include deleted item in output
                diff[key] = None
    return diff

# find a zeroconf service being advertised on the local network
def findService(serviceName, serviceType="tcp", ipVersion="IPv4"):
    servers = []
    serverList = subprocess.check_output("avahi-browse -tp --resolve _"+serviceName+"._"+serviceType ,shell=True).decode().split("\n")
    for server in serverList:
        serverData = server.split(";")
        if len(serverData) > 6:
            if serverData[2] == ipVersion:
                host = serverData[6]
                port = serverData[8]
                servers.append((host, int(port)))
    return servers

# register a zeroconf service on the local host
def registerService(serviceName, servicePort, serviceType="tcp"):
    serviceDir = "/etc/avahi/services/"
    with open(serviceDir+serviceName+".service", "w") as serviceFile:
        serviceFile.write('<?xml version="1.0" standalone="no"?>\n')
        serviceFile.write('<!DOCTYPE service-group SYSTEM "avahi-service.dtd">\n')
        serviceFile.write('<service-group>\n')
        serviceFile.write('  <name replace-wildcards="yes">%h</name>\n')
        serviceFile.write('  <service>\n')
        serviceFile.write('    <type>_'+serviceName+'._'+serviceType+'</type>\n')
        serviceFile.write('    <port>'+str(servicePort)+'</port>\n')
        serviceFile.write('  </service>\n')
        serviceFile.write('</service-group>\n')

# unregister a zeroconf service on the local host
def unregisterService(serviceName):
    serviceDir = "/etc/avahi/services/"
    os.remove(serviceDir+serviceName+".service")
