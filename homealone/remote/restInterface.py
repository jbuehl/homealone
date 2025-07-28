import json
import requests
import urllib.parse
import sys
from homealone import *
# from picohttp.httpClient import *

# Custom hook to convert keys to integers
def numericKeys2Int(pairs):
    result = {}
    for key, value in pairs:
        if key.isnumeric():
            result[int(key)] = value
        else:
            result[key] = value
    return result

class RestInterface(Interface):
    def __init__(self, name, interface=None, event=None, serviceAddr="", cache=True, writeThrough=True):
        Interface.__init__(self, name, interface=interface, event=event)
        self.cache = cache                  # cache the states
        self.writeThrough = writeThrough    # cache is write through
        self.enabled = False
        self.setServiceAddr(serviceAddr)
        debug('debugRest', self.name, "created", self.serviceAddr)

    def start(self, notify=None):
        debug('debugRest', self.name, "starting")
        self.enabled = True

    def stop(self):
        if self.enabled:
            self.enabled = False
            debug('debugRest', self.name, "stopping")
            # invalidate the state cache
            for state in list(self.states.keys()):
                self.states[state] = None

    # update the service address
    def setServiceAddr(self, serviceAddr):
        self.serviceAddr = serviceAddr      # address of the REST service to target (ipAddr:port)
        # (ipAddr, port) = self.serviceAddr.split(":")
        # self.client = HttpClient(ipAddr, int(port))

    # disable the RestService that uses this interface
    def disableService(self):
        debug('debugRemoteClientDisable', self.name, "disabled")
        for sensor in list(self.sensors.values()):
            if sensor.type == "service":    # just disable the service, it will disable the rest
                sensor.disable("REST I/O error")
                break

    # return state values of all sensors on this interface and store them in the cache
    def getStates(self, path="/states"):
        debug('debugRemoteClientStates', self.name, "getStates", "path", path)
        states = self.readRest(path)
        debug('debugRemoteClientStates', self.name, "getStates", "states", states)
        self.setStates(states)
        return states

    # set state values of all sensors into the cache
    def setStates(self, states):
        debug('debugRemoteClientStates', self.name, "setStates", "states", states)
        for sensor in list(states.keys()):
            self.states[sensor] = states[sensor]
        self.notify()

    # return the state value for the specified sensor address
    # addr is the REST path to the specified resource
    def read(self, addr):
        debug('debugRemoteClientRead', self.name, "read", addr, self.states)
        if not self.enabled:
            return None
        # return the state from the cache if it is there, otherwise read it from the service
        if (not self.cache) or (self.states[addr] == None):
            try:
                self.states[addr] = self.readRest("/resources/"+addr+"/state")["state"]
            except KeyError:
                self.states[addr] = None
        return self.states[addr]

    # read the json data from the specified path and return a dictionary
    def readRest(self, path):
        debug('debugRemoteClientRead', self.name, "readRest", path)
        try:
            ####################################################################
            url = "http://"+self.serviceAddr+urllib.parse.quote(path)
            debug('debugRestGet', self.name, "GET", url)
            response = requests.get(url, timeout=restTimeout)
            debug('debugRestGet', self.name, "status", response.status_code)
            if response.status_code == 200:
                debug('debugRestGet', self.name, "response", response.json())
                return json.loads(response.text, object_pairs_hook=numericKeys2Int)
            else:
                log(self.name, "read status", response.status_code, url)
                self.disableService()
                return {}
        except requests.exceptions.Timeout:
            log(self.name, "read state timeout", self.serviceAddr, path)
            self.disableService()
            return {}
        except requests.exceptions.ConnectionError:
            log(self.name, "read state connection error", self.serviceAddr, path)
            self.disableService()
            return {}
            ####################################################################
            # debug('debugRestGet', self.name, "GET", self.serviceAddr+path)
            # response = self.client.get(path)
            # debug('debugRestGet', self.name, "status", response.status)
            # if response.status == 200:
            #     debug('debugRestGet', self.name, "data", response.data)
            #     if response.data:
            #         return json.loads(response.data)
            #     else:
            #         return {}
            # elif response.status == 0:
            #     log(self.name, "read exception", response.data)
            #     self.disableService()
            # else:
            #     log(self.name, "read status", response.status)
            #     return {}
            ####################################################################
        except Exception as ex:
            logException(self.name+" uncaught read exception "+self.serviceAddr, str(ex))
            self.disableService()
            return {}

    # write the control state to the specified address
    # addr is the REST path to the specified resource
    def write(self, addr, value):
        debug('debugRemoteClientWrite', self.name, "write", addr, value)
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
        debug('debugRemoteClientWrite', self.name, "writeRest", path, data)
        try:
            ####################################################################
            url = "http://"+self.serviceAddr+urllib.parse.quote(path)
            debug('debugRestPut', self.name, "PUT", url, "data:", data)
            response = requests.put(url,
                             headers={"Content-type":"application/json"},
                             data=data)
            debug('debugRestPut', self.name, "status", response.status_code)
            if response.status_code == 200:
                return True
            else:
                log(self.name, "write status", response.status_code, url)
                return False
            ####################################################################
            # debug('debugRestPut', self.name, "PUT", self.serviceAddr+path, "data:", data)
            # response = self.client.put(path,
            #                  headers={"Content-type":"application/json"},
            #                  data=data)
            # debug('debugRestPut', self.name, "status", response.status)
            # if response.status == 200:
            #     return True
            # elif response.status == 0:
            #     log(self.name, "write exception", response.data)
            #     self.disableService()
            # else:
            #     log(self.name, "write status", response.status)
            #     return False
            ####################################################################
        except Exception as ex:
            logException(self.name+" uncaught write exception "+self.serviceAddr, ex)
            self.disableService()
