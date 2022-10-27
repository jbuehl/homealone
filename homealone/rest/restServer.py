
from picohttp import *
from homealone import *
import json
import urllib.parse
import threading
import socket
import time
import struct

def requestHandler(request, response, service, resources):
    (type, resName, attr) = fixedList(request.path, 3)
    debug('debugRestServer', "type:", type, "resName:", resName, "attr:", attr)
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
            data = resources.getStates()
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
                debug('debugRestServer', "data:", request.data)
                resource.__setattr__(attr, request.data[attr])
            except (KeyError, AttributeError):           # resource or attr not found
                response.status = 404   # not found
        else:
            response.status = 404   # not found
    else:
        response.status = 501   # not implemented

# RESTful web services server interface
class RestServer(object):
    def __init__(self, name, resources=None, port=None, advert=True, block=True, event=None, label=""):
        debug('debugRestServer', name, "creating RestServer", "advert:", advert)
        self.name = name
        self.resources = resources
        self.advert = advert
        self.block = block
        if event:
            self.event = event
        else:
            self.event = self.resources.event
        self.port = None
        if port:
            self.port = port
        else:
            # look for an available port in the pool
            restSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            for port in restServicePorts:
                try:
                    restSocket.bind(("", port))
                    self.port = port
                    debug('debugRestServer', "using port", port)
                    break
                except OSError:
                    pass
            restSocket.close()
        if self.port:
            if label == "":
                self.label = hostname+":"+str(self.port)
            else:
                self.label = label
            debug('debugInterrupt', self.label, "event", self.event)
            self.server = HttpServer(port=self.port, handler=requestHandler, args=(self, resources,), start=False, block=False)
            self.restAddr = multicastAddr
            self.stateSocket = None
            self.stateSequence = 0
            self.stateTimeStamp = 0
            self.resourceTimeStamp = 0
        else:
            log("RestServer", "unable to find an available port")
            self.server = None

    def start(self):
        if not self.server:
            return
        debug('debugRestServer', self.name, "starting RestServer")
        # wait for the network to be available
        waitForDns(localController)
        # start polling the resource states
        self.resources.start()
        # start the HTTP server
        self.server.start()
        if self.advert:
            # start the thread to send the resource states periodically and also when one changes
            def stateAdvert():
                debug('debugRestServer', self.name, "REST state started")
                resources = self.resources.dump()   # don't send expanded resources
                states = self.resources.getStates()
                lastStates = states
                self.stateTimeStamp = int(time.time())
                self.resourceTimeStamp = int(time.time())
                while True:
                    self.sendStateMessage(resources, states)
                    resources = None
                    states = None
                    # wait for either a state to change or the periodic trigger
                    currentStates = self.resources.getStates(wait=True)
                    # compare the current states to the previous states
                    if diffStates(lastStates, currentStates) != {}:
                        # a state changed
                        states = currentStates
                        self.stateTimeStamp = int(time.time())
                    if sorted(list(currentStates.keys())) != sorted(list(lastStates.keys())):
                        # a resource was either added or removed
                        resources = self.resources.dump()   # don't send expanded resources
                        self.resourceTimeStamp = int(time.time())
                    lastStates = currentStates
                debug('debugRestServer', self.name, "REST state ended")
            startThread(name="stateAdvertThread", target=stateAdvert)

            # start the thread to trigger the advertisement message periodically
            def stateTrigger():
                debug('debugRestServer', self.name, "REST state trigger started", restAdvertInterval)
                while True:
                    debug('debugInterrupt', self.name, "trigger", "set", self.event)
                    self.event.set()
                    time.sleep(restAdvertInterval)
                debug('debugRestServer', self.name, "REST state trigger ended")
            startThread(name="stateTriggerThread", target=stateTrigger)
        #wait forever
        if self.block:
            block()

    def openSocket(self):
        msgSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msgSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return msgSocket

    def getServiceData(self):
        return {"name": self.name,
               "hostname": hostname,
               "port": self.port,
               "label": self.label,
               "statetimestamp": self.stateTimeStamp,
               "resourcetimestamp": self.resourceTimeStamp,
               "seq": self.stateSequence}

    def sendStateMessage(self, resources=None, states=None):
        stateMsg = {"service": self.getServiceData()}
        if resources:
            stateMsg["resources"] = resources
        if states:
            stateMsg["states"] = states
        if not self.stateSocket:
            self.stateSocket = self.openSocket()
        try:
            debug('debugRestState', self.name, str(list(stateMsg.keys())))
            self.stateSocket.sendto(bytes(json.dumps(stateMsg), "utf-8"),
                                                (self.restAddr, restAdvertPort))
        except socket.error as exception:
            log("socket error", str(exception))
            self.stateSocket = None
        self.stateSequence += 1
