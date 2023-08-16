# Utility functions

import syslog
import os
import time
import threading
import traceback
import json
import copy
import subprocess
from rutifu import *
from .env import *

# states
off = 0
Off = 0
on = 1
On = 1

# Resource collection state cache
class StateCache(object):
    def __init__(self, name, resources, event=None, start=False):
        self.name = name
        self.resources = resources
        self.states = {}    # cache of current sensor states
        if event:
            self.event = event
        else:
            self.event = threading.Event()
        if start:
            self.start()

    def start(self):
        # initialize the resource state cache
        for resource in list(self.resources.values()):
            if resource.type not in ["schedule", "collection"]:   # skip resources that don't have a state
                try:
                    self.states[resource.name] = resource.getState()    # load the initial state
                except Exception as ex:
                    logException(self.name+" start", ex)
        startThread("pollStatesThread", self.pollStatesThread)
        startThread("watchEventsThread", self.watchEventsThread)

    # thread to periodically poll the state of the resources in the collection
    def pollStatesThread(self):
        resourcePollCounts = {}
        while True:
            stateChanged = False
            with self.resources.lock:
                for resource in list(self.resources.values()):
                    try:
                        if not resource.event:                                              # don't poll resources with events
                            if resource.type not in ["schedule", "collection", "task"]:     # skip resources that don't have a state
                                if resource.name not in list(resourcePollCounts.keys()):    # a resource not seen before
                                    resourcePollCounts[resource.name] = resource.poll
                                    self.states[resource.name] = resource.getState()
                                    stateChanged = True
                                if resourcePollCounts[resource.name] == 0:                  # count has decremented to zero
                                    resourceState = resource.getState()
                                    if resourceState != self.states[resource.name]:         # save the state if it has changed
                                        self.states[resource.name] = resourceState
                                        stateChanged = True
                                    resourcePollCounts[resource.name] = resource.poll
                                else:   # decrement the count
                                    resourcePollCounts[resource.name] -= 1
                    except Exception as ex:
                        logException(self.name+" pollStates", ex)
            if stateChanged:    # at least one resource state changed
                self.event.set()
                stateChanged = False
            time.sleep(1)

    # thread to watch foor state change events
    def watchEventsThread(self):
        while True:
            self.event.clear()
            self.event.wait()
            with self.resources.lock:
                for resource in list(self.resources.values()):
                    try:
                        if resource.event:                                              # only get resources with events
                            resourceState = resource.getState()
                            if resourceState != self.states[resource.name]:             # save the state if it has changed
                                self.states[resource.name] = resourceState
                                stateChanged = True
                    except Exception as ex:
                        logException(self.name+" watchEvents", ex)

    # get the current state of all sensors in the resource collection
    def getStates(self, wait=False):
        if self.event and wait:
            self.event.clear()
            self.event.wait()
        return copy.copy(self.states)

    # set the state of the specified sensor in the cache
    def setState(self, sensor, state):
        self.states[sensor.name] = state

    # set state values of all sensors into the cache
    def setStates(self, states):
        for sensor in list(states.keys()):
            self.states[sensor] = states[sensor]

# normalize state values from boolean to integers
def normalState(value):
    if value == True: return On
    elif value == False: return Off
    else: return value

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
