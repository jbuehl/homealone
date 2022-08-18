
from homealone import *
from socketserver import ThreadingMixIn
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import threading
import socket
import time
import struct

# RESTful web services server interface
class RestServer(object):
    def __init__(self, name, resources=None, port=None, advert=True, event=None, label=""):
        debug('debugRestServer', name, "creating RestServer")
        self.name = name
        self.resources = resources
        self.advert = advert
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
            self.server = RestHTTPServer(('', self.port), RestRequestHandler, self)
            self.restAddr = multicastAddr
            self.stateSocket = None
            self.stateSequence = 0
        else:
            log("RestServer", "unable to find an available port")
            self.server = None

    def start(self):
        if not self.server:
            return
        debug('debugRestServer', self.name, "starting RestServer")
        # wait for the network to be available
        waitForDns()
        # start polling the resource states
        self.resources.start()
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
            stateAdvertThread = LogThread(name="stateAdvertThread", target=stateAdvert)
            stateAdvertThread.start()

            # start the thread to trigger the advertisement message periodically
            def stateTrigger():
                debug('debugRestServer', self.name, "REST state trigger started", restAdvertInterval)
                while True:
                    debug('debugInterrupt', self.name, "trigger", "set", self.event)
                    self.event.set()
                    time.sleep(restAdvertInterval)
                debug('debugRestServer', self.name, "REST state trigger ended")
            stateTriggerThread = LogThread(name="stateTriggerThread", target=stateTrigger)
            stateTriggerThread.start()

        # start the HTTP server
        self.server.serve_forever()

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


class RestHTTPServer(ThreadingMixIn, HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, service):
        HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.service = service

class RestRequestHandler(BaseHTTPRequestHandler):
    serverVersion = "HARestHTTP/1.0"

    # return the resource definition or attribute specified in the path
    def do_GET(self):
        debug('debugRestGet', "verb:", "GET")
        debug('debugRestGet', "path:", self.path)
        debug('debugRestGet', "headers:", self.headers.__str__())
        try:
            (type, resName, attr, query) = self.parsePath(urllib.parse.unquote(self.path))
            service = self.server.service
            resources = service.resources
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
                        self.send_error(404)
                else:  # no resource was specified
                    expand = False
                    if query:   # expand resource definitions?
                        if (query[0][0].lower() == "expand") and (query[0][1].lower() == "true"):
                            expand = True
                    data = resources.dump(expand)
            elif type == "states":   # resource states
                data = resources.getStates()
            elif type == "service":  # service data
                data = service.getServiceData()
            else:
                self.send_error(404)
            if data:
                self.send_response(200)     # success
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(json.dumps(data), "utf-8"))
        except Exception as ex:
            logException("restServer do_GET "+self.path, ex)
            self.send_error(500)        # server error
            self.wfile.write(bytes(str(ex), "utf-8"))

    # set the attribute of the resource specified in the path to the value specified in the data
    def do_PUT(self):
        debug('debugRestPut', "verb:", "PUT")
        debug('debugRestPut', "path:", self.path)
        debug('debugRestPut', "headers:", self.headers.__str__())
        try:
            (type, resName, attr, query) = self.parsePath(urllib.parse.unquote(self.path))
            service = self.server.service
            resources = service.resources
            if (type == "resources") and resName and attr:   # resource and attr was specified
                try:
                    resource = resources.getRes(resName, False)
                    data = self.rfile.read(int(self.headers['Content-Length'])).decode("utf-8")
                    debug('debugRestPut', "data:", data)
                    if self.headers['Content-type'] == "application/json":
                        data = json.loads(data)
                    resource.__setattr__(attr, data[attr])
                    self.send_response(200) # success
                    self.end_headers()
                except (KeyError, AttributeError):           # resource or attr not found
                    raise
                    self.send_error(404)
            else:
                self.send_error(404)
        except Exception as ex:
            logException("restServer do_PUT "+self.path, ex)
            self.send_error(500)        # server error
            self.wfile.write(bytes(str(ex), "utf-8"))

    # add a resource to the collection specified in the path using parameters specified in the data
    def do_POST(self):
        self.send_error(501)         # not implemented

    # delete the resource specified in the path from the collection
    def do_DELETE(self):
        self.send_error(501)         # not implemented

    # parse the path string into components
    def parsePath(self, pathStr):
        try:
            (pathStr, queryStr) = pathStr.split("?")
            query = [queryItem.split("=") for queryItem in queryStr.split("&")]
        except ValueError:
            query = None
        segments = pathStr.lstrip("/").rstrip("/").split("/")
        type = segments[0]
        resource = None
        attr = None
        if len(segments) > 1:
            resource = segments[1]
            if len(segments) > 2:
                attr = segments[2]
        debug('debugRestParse', "elements:", type, resource, attr, query)
        return (type, resource, attr, query)

    # this suppresses logging from BaseHTTPServer
    def log_message(self, format, *args):
        return
