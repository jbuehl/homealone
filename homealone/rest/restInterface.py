import json
import requests
import urllib.parse
import sys
from homealone import *
from homealone.rest.restConfig import *

class RestInterface(Interface):
    def __init__(self, name, interface=None, event=None, serviceAddr="", cache=True, writeThrough=True):
        Interface.__init__(self, name, interface=interface, event=event)
        self.serviceAddr = serviceAddr      # address of the REST service to target (ipAddr:port)
        self.cache = cache                  # cache the states
        self.writeThrough = writeThrough    # cache is write through
        self.enabled = False
        debug('debugRest', self.name, "created", self.serviceAddr)

    def start(self):
        debug('debugRest', self.name, "starting")
        self.enabled = True

    def stop(self):
        if self.enabled:
            self.enabled = False
            debug('debugRest', self.name, "stopping")
            # invalidate the state cache
            for state in list(self.states.keys()):
                self.states[state] = None

    # disable the RestService that uses this interface
    def disableService(self):
        debug('debugRestProxyDisable', self.name, "disabled")
        for sensor in list(self.sensors.values()):
            if sensor.type == "service":    # just disable the service, it will disable the rest
                sensor.disable("REST I/O error")
                break

    # return the state value for the specified sensor address
    # addr is the REST path to the specified resource
    def read(self, addr):
        debug('debugRestStates', self.name, "read", addr, self.states)
        if not self.enabled:
            return None
        # return the state from the cache if it is there, otherwise read it from the service
        if (not self.cache) or (self.states[addr] == None):
            self.states[addr] = self.readRest("/resources/"+addr+"/state")["state"]
        return self.states[addr]

    # get state values of all sensors on this interface
    def getStates(self, path="/states"):
        debug('debugRestStates', self.name, "getStates", "path", path)
        try:
            states = self.readRest(path)[path.split("/")[-1]]
        except KeyError:
            states = {}
        debug('debugRestStates', self.name, "getStates", "states", states)
        self.setStates(states)
        return states

    # set state values of all sensors into the cache
    def setStates(self, states):
        for sensor in list(states.keys()):
            self.states[sensor] = states[sensor]

    # read the json data from the specified path and return a dictionary
    def readRest(self, path):
        debug('debugRestStates', self.name, "readRest", path)
        try:
            url = "http://"+self.serviceAddr+urllib.parse.quote(path)
            debug('debugRestGet', self.name, "GET", url)
            response = requests.get(url, timeout=restTimeout)
            debug('debugRestGet', self.name, "status", response.status_code)
            if response.status_code == 200:
                debug('debugRestGet', self.name, "response", response.json())
                return response.json()
            else:
                log(self.name, "read state status", response.status_code)
                return {}
        except requests.exceptions.Timeout:
            log(self.name, "read state timeout", path)
            self.disableService()
        except Exception as ex:
            logException(self.name+" read exception", ex)
            self.disableService()

    # write the control state to the specified address
    # addr is the REST path to the specified resource
    def write(self, addr, value):
        debug('debugRestStates', self.name, "write", addr, value)
        if self.enabled:
            if self.cache:
                if self.writeThrough:
                    # update the cache
                    self.states[addr] = value
                    self.notify()
                else:
                    # invalidate the cache
                    self.states[addr] = None
            # create a jsonized dictionary
            data=json.dumps({"state": value})
            # data=json.dumps({addr.split("/")[-1]: value})
            return self.writeRest("/resources/"+addr+"/state", data)
        else:
            return False

    # write json data to the specified path
    def writeRest(self, path, data):
        debug('debugRestStates', self.name, "writeRest", path, data)
        try:
            url = "http://"+self.serviceAddr+urllib.parse.quote(path)
            debug('debugRestPut', self.name, "PUT", url, "data:", data)
            response = requests.put(url,
                             headers={"Content-type":"application/json"},
                             data=data)
            debug('debugRestPut', self.name, "status", response.status_code)
            if response.status_code == 200:
                return True
            else:
                log(self.name, "write state status", response.status_code)
                return False
        except Exception as ex:
            logException(self.name+" write exception", ex)
            self.disableService()
