from homealone import *
from homealone.rest.restService import *
from homealone.rest.restInterface import *
import json
import threading
import socket
import time

# Proxy for the resources exposed by one or more REST services

# Usecases:
#     proxy detects new service
#     service states updated
#     service resources updated
#     rest i/o error
#     notify message timeout
#     service restarts

# set default service port if not specified
def setServicePorts(serviceList):
    newServiceList = []
    for service in serviceList:
        if len(service.split(".")) < 2:
            service = "services."+service
        newServiceList.append(service)
    return newServiceList

def parseServiceData(data, addr):
    try:
        serviceData = json.loads(data.decode("utf-8"))
        debug('debugRestProxyData', "data", serviceData)
        try:
            serviceResources = serviceData["resources"]
        except KeyError:
            serviceResources = None
        try:
            serviceStates = serviceData["states"]
        except:
            serviceStates = None
        serviceData = serviceData["service"]
        serviceName = "services."+serviceData["name"]
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
        serviceLabel = serviceData["label"]
        serviceSeq = serviceData["seq"]
        return (serviceName, serviceAddr, serviceLabel, version, serviceSeq, stateTimeStamp, resourceTimeStamp, serviceStates, serviceResources)
    except Exception as ex:
        logException("parseServiceData", ex)
        return ("", "", "", 0, 0, 0, 0, {}, [])

# Autodiscover services and resources
# Detect changes in resource configuration on each service
# Remove resources on services that don't respond

class RestProxy(LogThread):
    def __init__(self, name, resources, watch=[], ignore=[], event=None, cache=True):
        debug('debugRestProxy', name, "starting", name)
        LogThread.__init__(self, target=self.restProxyThread)
        self.name = name
        self.services = {}                      # cached services
        self.resources = resources              # resource cache
        self.event = event
        self.cache = cache
        self.cacheTime = 0                      # time of the last update to the cache
        self.watch = setServicePorts(watch)     # services to watch for
        self.ignore = setServicePorts(ignore)   # services to ignore
        # self.ignore.append("services."+socket.gethostname()+":"+str(restServicePort))   # always ignore services on this host
        debug('debugRestProxy', name, "watching", self.watch)    # watch == [] means watch all services
        debug('debugRestProxy', name, "ignoring", self.ignore)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((multicastAddr, restAdvertPort))

    def restProxyThread(self):
        debug('debugThread', self.name, "started")
        while True:
            # wait for a notification message from a service
            (data, addr) = self.socket.recvfrom(32768)   # FIXME - need to handle arbitrarily large data
            debug('debugRestMessage', self.name, "notification data", data)
            # parse the message
            (serviceName, serviceAddr, serviceLabel, version, serviceSeq, stateTimeStamp, resourceTimeStamp, serviceStates, serviceResources) = \
                parseServiceData(data, addr)
            if serviceName == "":   # message couldn't be parsed
                continue
            # rename it if there is an alias
            if serviceName in list(self.resources.aliases.keys()):
                newServiceName = self.resources.aliases[serviceName]["name"]
                newServiceLabel = self.resources.aliases[serviceName]["label"]
                debug('debugRestProxy', self.name, "renaming", serviceName, "to", newServiceName)
                serviceName = newServiceName
                serviceLabel = newServiceLabel
            # determine if this service should be processed based on watch and ignore lists
            if ((self.watch != []) and (serviceName  in self.watch)) or ((self.watch == []) and (serviceName not in self.ignore)):
                debug('debugRestProxy', self.name, "processing", serviceName, serviceAddr, stateTimeStamp, resourceTimeStamp)
                if serviceName not in list(self.services.keys()):
                    # this is one not seen before, create a new service proxy
                    debug('debugRestProxyAdd', self.name, "adding", serviceName, serviceAddr, version, stateTimeStamp, resourceTimeStamp)
                    self.services[serviceName] = RestService(serviceName,
                                                            RestInterface(serviceName+"Interface",
                                                                            serviceAddr=serviceAddr,
                                                                            event=self.event,
                                                                            cache=self.cache),
                                                            version=version,
                                                            proxy=self,
                                                            label=serviceLabel,
                                                            group="Services")
                    service = self.services[serviceName]
                    service.enable()
                else:   # service is already in the cache
                    service = self.services[serviceName]
                    service.cancelTimer("message received")
                    if serviceAddr != service.interface.serviceAddr:
                        debug('debugRestProxyUpdate', self.name, "updating address", service.name, serviceAddr)
                        service.interface.setServiceAddr(serviceAddr) # update the ipAddr:port in case it changed
                    if not service.enabled:     # the service was previously disabled but it is broadcasting again
                        # re-enable it
                        debug('debugRestProxyDisable', self.name, "reenabling", serviceName, serviceAddr, version, stateTimeStamp, resourceTimeStamp)
                        # update the resource cache
                        # self.addResources(service)
                        service.enable()
                # load the resources or states in a separate thread if there was a change
                if (resourceTimeStamp > service.resourceTimeStamp) or serviceResources or \
                   (stateTimeStamp > service.stateTimeStamp) or serviceStates:
                    if not service.updating:    # prevent multiple updates at the same time
                        service.updating = True
                        startThread(serviceName+"-update", self.loadService, args=(service, resourceTimeStamp, serviceResources,
                                                                                stateTimeStamp, serviceStates,))
                # start the message timer
                service.startTimer()
                service.logSeq(serviceSeq)
            else:
                debug('debugRestProxy', self.name, "ignoring", serviceName, serviceAddr, stateTimeStamp, resourceTimeStamp)
        debug('debugThread', self.name, "terminated")

    # optionally load the resources for a service and add them to the proxy cache
    # optionally load the states of the service resources
    def loadService(self, service, resourceTimeStamp, serviceResources, stateTimeStamp, serviceStates):
        debug('debugThread', threading.currentThread().name, "started")
        try:
            if (resourceTimeStamp > service.resourceTimeStamp) or serviceResources:
                debug('debugRestProxyUpdate', self.name, "updating resources", service.name, resourceTimeStamp)
                service.load(serviceResources)
                service.resourceTimeStamp = resourceTimeStamp
                self.addResources(service)
            if (stateTimeStamp > service.stateTimeStamp) or serviceStates:
                debug('debugRestProxyStates', self.name, "updating states", service.name, stateTimeStamp)
                if not serviceStates:
                    # if states not provided, get them from the service
                    serviceStates = service.interface.getStates()
                else:
                    service.interface.setStates(serviceStates)     # load the interface cache
                self.resources.setStates(serviceStates)        # update the resource collection cache
                service.stateTimeStamp = stateTimeStamp
                self.resources.notify()
        except Exception as ex:
            logException(self.name+" loadService", ex)
        service.updating = False
        debug('debugThread', threading.currentThread().name, "terminated")

    # add the resource of the service as well as
    # all the resources from the specified service to the cache
    def addResources(self, service):
        debug('debugRestProxy', self.name, "adding resources for service", service.name)
        self.resources.addRes(service, 1)                       # the resource of the service
        self.resources.addRes(service.missedSeqSensor)          # missed messages
        self.resources.addRes(service.missedSeqPctSensor)       # percent of missed messages
        for resource in list(service.resources.values()):       # resources from the service
            self.resources.addRes(resource)
        self.cacheTime = service.resourceTimeStamp # FIXME
        self.event.set()
        debug('debugInterrupt', self.name, "event set")

    # disable all the resources from the specified service from the cache
    # don't delete the resource of the service
    # def disableResources(self, service):
    #     debug('debugRestProxyDisable', self.name, "disabling resources for service", service.name)
    #     for resourceName in list(service.resources.keys()):
    #         try:
    #             self.resources.getRes(resourceName).enabled = False
    #         except KeyError:
    #             debug('debugRestProxyDisable', service.name, "error disabling", resourceName)
    #     self.event.set()
    #     debug('debugInterrupt', self.name, "event set")
