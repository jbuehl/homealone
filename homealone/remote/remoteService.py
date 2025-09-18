
from picohttp import *
from homealone import *
import json
import urllib.parse
import threading
import socket
import time
import struct

# handle REST requests
def requestHandler(request, response, service, resources):
    (type, resName, attr) = fixedList(request.path, 3)
    debug('debugRemoteService', "type:", type, "resName:", resName, "attr:", attr)
    if request.method == "GET":
        data = None
        if type == "":              # no path specified
            data = ["service", "resources", "states"]
        elif type == "resources":   # resource definitions
            if resName:
                try:                # resource was specified
                    resource = resources.getRes(resName, False)
                    if attr:        # attribute was specified
                         data = {attr: resource.__getattribute__(attr)}
                    else:           # no attribute, send resource definition
                         data = resource.dump()
                except (KeyError, AttributeError):           # resource or attr not found
                    response.status = 404   # not found
            else:                   # no resource was specified
                if "expand" in request.query:   # expand the resources
                    expand = True
                else:                           # just return resource names
                    expand = False
                data = resources.dump(expand)
        elif type == "states":   # resource states
            data = service.states.getStates(wait=False)
        elif type == "service":  # service data
            data = service.getServiceData()
        else:
            response.status = 404   # not found
        if response.status == 200:
            response.headers["Content-Type"] = "application/json"
            response.data = json.dumps(data)
    elif request.method == "PUT":
        if (type == "resources") and resName and attr:   # resource and attr was specified
            try:
                resource = resources.getRes(resName, False)
                if request.headers['Content-type'] == "application/json":
                    request.data = json.loads(request.data)
                debug('debugRemoteService', "data:", request.data)
                resource.__setattr__(attr, request.data[attr])
            except (KeyError, AttributeError):           # resource or attr not found
                response.status = 404   # not found
        else:
            response.status = 404   # not found
    else:
        response.status = 501   # not implemented

# Remote service interface
class RemoteService(object):
    def __init__(self, name, resources, states, port=None, advert=True, label=""):
        debug('debugRemoteService', name, "creating RemoteService", "advert:", advert)
        self.name = name
        self.resources = resources
        self.states = states
        if port:        # use the specified port
            self.ports = [port]
        else:           # use an available port from the pool
            self.ports = restServicePortPool
        self.advert = advert
        self.label = label
        self.advertSocket = None
        self.advertSequence = 0
        self.stateTimeStamp = int(time.time())
        self.resourceTimeStamp = int(time.time())
        self.restServer = None
        self.faults = {}

    def start(self, block=True):
        # start the HTTP server
        debug('debugRemoteService', self.name, "starting RemoteService")
        self.port = 0
        while not self.port:
            try:
                self.restServer = HttpServer(port=self.ports, handler=requestHandler, args=(self, self.resources,),
                                             reuse=False, start=False, block=False)
                self.port = self.restServer.start()
                if self.port:
                    break
            except Exception as ex:
                log(self.name, "Unable to start RestServer", str(ex))
            debug('debugRemoteService', self.name, "sleeping for", restRetryInterval)
            time.sleep(restRetryInterval)
        debug('debugRemoteService', self.name, "RestServer started on port", self.port)
        if self.advert:
            if self.label == "":
                self.label = hostname+":"+str(self.port)
            # start the thread to send the resources or states when there is a change
            startThread(name="stateAdvertThread", target=self.stateAdvert)
            # start the thread to trigger the advertisement message periodically
            startThread(name="stateTriggerThread", target=self.stateTrigger)
        #wait forever
        if block:
            while True:
                time.sleep(1)

    def setFault(self, id, fault, logFault=True):
        debug('debugRemoteService', self.name, "setFault", id, fault, self.faults)
        if id not in self.faults:
            self.faults[id] = fault
            if logFault:
                log(self.name, id, str(fault))

    def clearFault(self, id):
        debug('debugRemoteService', self.name, "clearFault", id, self.faults)
        if id in self.faults:
            del(self.faults[id])

    # periodically send the advert message as a heartbeat
    def stateTrigger(self):
        debug('debugRemoteService', self.name, "Remote state trigger started", remoteAdvertInterval)
        while True:
            time.sleep(remoteAdvertInterval)
            self.sendAdvertMessage(None, None)
        debug('debugRemoteService', self.name, "Remote state trigger ended")

    # send the advert message with states and/or resources if there was a change
    def stateAdvert(self):
        debug('debugRemoteService', self.name, "Advert thread started")
        resources = self.resources.dump()   # don't send expanded resources
        states = self.states.getStates(wait=False)
        self.sendAdvertMessage(resources, states)
        lastStates = states
        while True:
            resources = None
            states = None
            # wait for a state to change
            states = self.states.getStates(wait=True)
            # a state changed
            self.stateTimeStamp = int(time.time())
            # fault if there is an invalid state
            for resourceName in list(states.keys()):
                if states[resourceName] is None:
                    debug('debugRemoteService', resourceName, "Missing state")
                    self.setFault(resourceName, "missing state")
                else:
                    self.clearFault(resourceName)
            if sorted(list(states.keys())) != sorted(list(lastStates.keys())):
                # a resource was either added or removed
                resources = self.resources.dump()   # don't send expanded resources
                self.resourceTimeStamp = int(time.time())
            self.sendAdvertMessage(resources, states)
            lastStates = states
        debug('debugRemoteService', self.name, "Advert thread ended")

    def getServiceData(self):
        return {"name": self.name,
               "hostname": hostname,
               "port": self.port,
               "label": self.label,
               "statetimestamp": self.stateTimeStamp,
               "resourcetimestamp": self.resourceTimeStamp,
               "seq": self.advertSequence,
               "faults": self.faults}

    def sendAdvertMessage(self, resources=None, states=None):
        stateMsg = {"service": self.getServiceData()}
        if resources:
            stateMsg["resources"] = resources
        if states:
            stateMsg["states"] = states
        if not self.advertSocket:
            self.advertSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.advertSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            debug('debugRemoteAdvert', self.name, str(list(stateMsg.keys())))
            self.advertSocket.sendto(bytes(json.dumps(stateMsg), "utf-8"),
                                                (multicastAddr, remoteAdvertPort))
        except socket.error as exception:
            log("socket error", str(exception))
            self.advertSocket = None
        self.advertSequence += 1
