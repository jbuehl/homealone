
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
        if event:       # use specified event
            self.event = event
        else:           # use the event of the resources
            self.event = self.resources.event
        if port:        # use the specified port
            self.ports = [port]
        else:           # use an available port from the pool
            self.ports = restServicePorts
        self.label = label
        debug('debugInterrupt', self.label, "event", self.event)
        self.advertSocket = None
        self.advertSequence = 0
        self.stateTimeStamp = 0
        self.resourceTimeStamp = 0
        self.restServer = None

    def start(self):
        # start polling the resource states
        self.resources.start()
        # start the HTTP server
        debug('debugRestServer', self.name, "starting RestServer")
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
            debug('debugRestServer', self.name, "sleeping for", restRetryInterval)
            time.sleep(restRetryInterval)
        debug('debugRestServer', self.name, "RestServer started on port", self.port)
        if self.advert:
            if self.label == "":
                self.label = hostname+":"+str(self.port)
            # start the thread to send the resource states periodically and also when one changes
            def stateAdvert():
                debug('debugRestServer', self.name, "Advert thread started")
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
                debug('debugRestServer', self.name, "Advert thread ended")
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
               "seq": self.advertSequence}

    def sendStateMessage(self, resources=None, states=None):
        stateMsg = {"service": self.getServiceData()}
        if resources:
            stateMsg["resources"] = resources
        if states:
            stateMsg["states"] = states
        if not self.advertSocket:
            self.advertSocket = self.openSocket()
        try:
            debug('debugRestState', self.name, str(list(stateMsg.keys())))
            self.advertSocket.sendto(bytes(json.dumps(stateMsg), "utf-8"),
                                                (multicastAddr, restAdvertPort))
        except socket.error as exception:
            log("socket error", str(exception))
            self.advertSocket = None
        self.advertSequence += 1
