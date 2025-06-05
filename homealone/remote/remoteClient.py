from homealone import *
from homealone.remote.proxyService import *
from homealone.remote.restInterface import *
import json
import threading
import socket
import time

# Client side for remote services

def parseServiceData(data, addr):
    try:
        serviceData = json.loads(data.decode("utf-8"))
        debug('debugRemoteClientData', "data", serviceData)
        try:
            serviceResources = serviceData["resources"]
        except KeyError:
            serviceResources = None
        try:
            serviceStates = serviceData["states"]
        except KeyError:
            serviceStates = None
        serviceData = serviceData["service"]
        serviceName = serviceData["name"]
        serviceAddr = addr[0]+":"+str(serviceData["port"])
        try:
            stateTimeStamp = serviceData["statetimestamp"]
            resourceTimeStamp = serviceData["resourcetimestamp"]
        except KeyError:
            stateTimeStamp = serviceData["timestamp"]
            resourceTimeStamp = serviceData["timestamp"]
        try:
            version = serviceData["version"]
        except KeyError:
            version = 0
        try:
            serviceFault = serviceData["fault"]
        except KeyError:
            serviceFault = False
        serviceLabel = serviceData["label"]
        serviceSeq = serviceData["seq"]
        return (serviceName, serviceAddr, serviceLabel, version, serviceSeq, stateTimeStamp, resourceTimeStamp, serviceFault, serviceStates, serviceResources)
    except Exception as ex:
        logException("parseServiceData", ex)
        return ("", "", "", 0, 0, 0, 0, False, {}, [])

class RemoteClient(LogThread):
    def __init__(self, name, resources, watch=[], ignore=[], event=None, cache=True, resourceChanged=None):
        debug('debugRemoteClient', name, "starting", name)
        LogThread.__init__(self, target=self.restProxyThread)
        self.name = name
        self.services = {}                      # proxied services
        self.resources = resources              # local resources
        self.watch = watch                      # services to watch for
        self.ignore = ignore                    # services to ignore
        self.event = event
        self.cache = cache
        self.resourceChanged = resourceChanged  # callback when resources on a remote service change
        debug('debugRemoteClient', name, "watching", self.watch)    # watch == [] means watch all services
        debug('debugRemoteClient', name, "ignoring", self.ignore)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((multicastAddr, remoteAdvertPort))

    def restProxyThread(self):
        debug('debugThread', self.name, "started")
        while True:
            # wait for a notification message from a service
            (data, addr) = self.socket.recvfrom(32768)  # FIXME - need to handle arbitrarily large data
            if addr[0][0:7] == "169.254":               # ignore messages if the network isn't fully up
                continue
            debug('debugRemoteMessage', self.name, "notification data", data)
            # parse the message
            (serviceName, serviceAddr, serviceLabel, version, serviceSeq, stateTimeStamp, resourceTimeStamp, serviceFault, serviceStates, serviceResources) = \
                parseServiceData(data, addr)
            if serviceName == "":   # message couldn't be parsed
                continue
            # determine if this service should be processed based on watch and ignore lists
            if ((self.watch != []) and (serviceName  in self.watch)) or ((self.watch == []) and (serviceName not in self.ignore)):
                debug('debugRemoteClient', self.name, "processing", serviceName, serviceAddr, stateTimeStamp, resourceTimeStamp)
                if serviceName not in list(self.services.keys()):
                    # service has not been seen before, create a new service proxy
                    debug('debugRemoteClientAdd', self.name, "adding", serviceName, serviceAddr, version, stateTimeStamp, resourceTimeStamp)
                    self.services[serviceName] = ProxyService(serviceName+"Service",
                                                            RestInterface(serviceName+"Interface",
                                                                            serviceAddr=serviceAddr,
                                                                            event=self.event,
                                                                            cache=self.cache),
                                                            version=version,
                                                            remoteClient=self,
                                                            label=serviceLabel,
                                                            group="Services")
                    service = self.services[serviceName]
                    service.enable()
                else:   # service is already known, update its attributes and enable it
                    service = self.services[serviceName]
                    service.cancelTimer("message received")
                    if serviceAddr != service.interface.serviceAddr:
                        debug('debugRemoteClientUpdate', self.name, "updating address", service.name, serviceAddr)
                        service.interface.setServiceAddr(serviceAddr) # update the ipAddr:port in case it changed
                    service.setFault(serviceFault)
                    if not service.enabled:     # the service was previously disabled but it is broadcasting again
                        debug('debugRemoteClientDisable', self.name, "reenabling", serviceName, serviceAddr, version, stateTimeStamp, resourceTimeStamp)
                        service.enable()
                # load the resources or states in a separate thread if there was a change
                if (resourceTimeStamp > service.resourceTimeStamp) or serviceResources or \
                   (stateTimeStamp > service.stateTimeStamp) or serviceStates:
                    if not service.updating:    # prevent multiple updates at the same time
                        service.updating = True
                        startThread(serviceName+"-update", self.updateService, args=(service, resourceTimeStamp, serviceResources,
                                                                                stateTimeStamp, serviceStates,))
                # start the message timer
                service.startTimer()
                service.logSeq(serviceSeq)
            else:
                debug('debugRemoteClient', self.name, "ignoring", serviceName, serviceAddr, stateTimeStamp, resourceTimeStamp)
        debug('debugThread', self.name, "terminated")

    # if resources have changed, update the resources for a service and add them to the local collection
    # if states have changed, update the states of the service resources
    def updateService(self, service, resourceTimeStamp, serviceResources, stateTimeStamp, serviceStates):
        debug('debugThread', threading.currentThread().name, "started")
        try:
            if (resourceTimeStamp > service.resourceTimeStamp) or serviceResources:
                debug('debugRemoteClientUpdate', self.name, "updating resources", service.name, resourceTimeStamp)
                for resource in list(service.resources.values()):
                    debug('debugRemoteClientUpdate', self.name, "updating resources", service.name, "disabling", resource.name)
                    resource.disable()
                service.load(serviceResources)
                service.resourceTimeStamp = resourceTimeStamp
                self.addLocalResources(service)
                if self.resourceChanged:                # resource change callback
                    self.resourceChanged(service.name)
            if (stateTimeStamp > service.stateTimeStamp) or serviceStates:
                debug('debugRemoteClientStates', self.name, "updating states", service.name, stateTimeStamp)
                if not serviceStates:
                    # if state values were not provided, get them from the service
                    serviceStates = service.interface.getStates()
                else:
                    service.interface.setStates(serviceStates)  # load the interface cache
                service.stateTimeStamp = stateTimeStamp
        except Exception as ex:
            logException(self.name+" updateService", ex)
        service.updating = False
        debug('debugThread', threading.currentThread().name, "terminated")

    # add all the resources related to the specified service to the local resource collection
    def addLocalResources(self, service):
        debug('debugRemoteClient', self.name, "adding resources for service", service.name)
        self.resources.addRes(service, 1)                       # the resource of the service proxy
        self.resources.addRes(service.missedSeqSensor)          # missed messages
        self.resources.addRes(service.missedSeqPctSensor)       # percent of missed messages
        for resource in list(service.resources.values()):       # resources from the service
            if resource.enabled:
                debug('debugRemoteClientUpdate', self.name, "updating resources", service.name, "adding", resource.name)
                self.resources.addRes(resource)
        self.event.set()
        debug('debugInterrupt', self.name, "event set")
