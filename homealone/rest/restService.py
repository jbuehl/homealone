from homealone import *
from homealone.resources.extraResources import *
from homealone.rest.restConfig import *
from homealone.schedule import *
import threading

messageTimeout = beaconTimeout

# create a Resource from a serialized dict
def loadResource(classDict, globalDict):
    def parseClass(classDict):
        args = classDict["args"]
        argStr = ""
        for arg in list(args.keys()):
            argStr += arg+"="
            if isinstance(args[arg], dict):     # argument is a class
                argStr += parseClass(args[arg])+", "
            elif isinstance(args[arg], str):    # arg is a string
                argStr += "'"+args[arg]+"', "
            elif not arg:                       # arg is None
                argStr += "None"
            else:                               # arg is numeric or other
                argStr += str(args[arg])+", "
        return classDict["class"]+"("+argStr[:-2]+")"
    localDict = {}
    exec("resource = "+parseClass(classDict), globalDict, localDict)
    return localDict["resource"]

# proxy for a REST service
class RestService(Sensor):
    def __init__(self, name, interface, addr=None, version=0, stateTimeStamp=-1, resourceTimeStamp=-1, proxy=None, type="service", **kwargs):
        Sensor.__init__(self, name, interface, addr=addr, type=type, **kwargs)
        debug('debugRestService', "RestService", name, "created")
        self.version = version
        self.stateTimeStamp = stateTimeStamp      # the last time the states were updated
        self.resourceTimeStamp = resourceTimeStamp      # the last time the resources were updated
        self.resources = Collection(self.name+"/Resources")           # resources on this service
        self.proxy = proxy              # RestProxy that is following this service
        self.enabled = False
        self.messageTimer = None
        self.updating = False
        self.lastSeq = 0                # the last message sequence number received
        self.missedSeq = 0              # count of how many missed messages for this service
        self.missedSeqPct = 0.0         # percentage of missed messages
        try:
            serviceName = name.split(".")[1]
        except IndexError:
            serviceName = name
        self.missedSeqSensor = AttributeSensor(serviceName+"-missedSeq", None, None, self, "missedSeq")
        self.missedSeqPctSensor = AttributeSensor(serviceName+"-missedSeqPct", None, None, self, "missedSeqPct")

    def getState(self, missing=None):
        return normalState(self.enabled)

    def setState(self, state, wait=False):
        if state:
            self.enable()
        else:
            self.disable("set")
        return True

    def __repr__(self):
        return "version: "+str(self.version)+"\n"+ \
               "resource time: "+str(self.resourceTimeStamp)+"\n"+ \
               "state time: "+str(self.stateTimeStamp)+"\n"+ \
               "missed seq: "+str(self.missedSeq)+"\n"+ \
               "---------------"

    def enable(self):
        debug('debugRestService', "RestService", self.name, "enabled")
        for resource in list(self.resources.values()):
            resource.enable()
        self.interface.start()
        self.enabled = True
        self.notify(True)

    def disable(self, reason=""):
        debug('debugRestService', "RestService", self.name, "disabled", reason)
        self.enabled = False
        self.interface.stop()
        self.messageTimer = None
        for resource in list(self.resources.values()):
            resource.disable()
        self.notify(False)

    def logSeq(self, seq):
        debug('debugRestSeq', "RestService", self.name, seq, self.lastSeq, self.missedSeq, self.missedSeqPct)
        if seq == 0:
            self.lastSeq = 0    # reset when the service starts
            self.missedSeqPct = 0.0
        if self.lastSeq != 0:   # ignore the first one after this program starts
            self.missedSeq += seq - self.lastSeq - 1
        if seq > 0:
            self.missedSeqPct = float(self.missedSeq) / float(seq)
        self.lastSeq = seq
        self.missedSeqSensor.notify()
        self.missedSeqPctSensor.notify()

    # define a timer to disable the service if the message timer times out
    # can't use a socket timeout because multiple threads are using the same port
    def messageTimeout(self):
        debug('debugMessageTimer', self.name, "timer expired")
        debug('debugRestProxyDisable', self.name, "read message timeout")
        self.disable("timeout")

    # start the message timer
    def startTimer(self):
        if messageTimeout:
            self.messageTimer = threading.Timer(messageTimeout, self.messageTimeout)
            self.messageTimer.start()
            debug('debugMessageTimer', self.name, "timer started", messageTimeout, "seconds")

    # cancel the message timer
    def cancelTimer(self, reason=""):
        if self.messageTimer:
            self.messageTimer.cancel()
            debug('debugMessageTimer', self.name, "timer cancelled", reason)

    # load resources from the specified REST paths
    def load(self, serviceResources):
        debug('debugLoadService', self.name, "load", serviceResources)
        try:
            # self.delResources()
            # self.addResources()
            if not serviceResources or \
                    (isinstance(serviceResources["args"]["resources"], list)):  # if expanded resources not provided, get them
                serviceResources = self.interface.readRest("/resources?expand=true")
            for resource in serviceResources["args"]["resources"]:
                self.loadResource(resource)
        except Exception as ex:
            logException(self.name+" load", ex)

    # instantiate the resource from the specified dictionary
    def loadResource(self, resourceDict):
        debug('debugLoadService', self.name, "loadResource", resourceDict)
        resourceDict["args"]["interface"] = None
        resource = loadResource(resourceDict, globals())
        # replace the resource interface and addr with the REST interface and addr
        resource.interface = self.interface
        resource.addr = resource.name
        resource.interface.addSensor(resource)
        self.resources.addRes(resource)
