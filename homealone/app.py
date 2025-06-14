# application template

from .core import *
from .schedule import *
from .remote.remoteService import *
from .remote.remoteClient import *
from .logging.logging import *
from .interfaces.fileInterface import *
from homealone.interfaces.osInterface import *

class Application(object):
    def __init__(self, name, globals,
                 publish=True, advert=True,                                 # resource publishing parameters
                 remote=False, watch=[], ignore=[], separateRemote=True,    # remote resource proxy parameters
                    resourceChanged=None,
                 logger=True,                                               # data logger
                 system=False,                                              # system resources
                 state=False, shared=False, changeMonitor=True):            # persistent state parameters
        self.name = name
        self.globals = globals                                              # application global variables
        self.event = threading.Event()                                      # state change event
        self.resources = Collection("resources")                            # application resources
        self.separateRemote = separateRemote
        self.globals["resources"] = self.resources
        self.states = StateCache("states", self.resources, self.event)      # resource state cache
        self.globals["states"] = self.states
        self.schedule = Schedule("schedule")                                # schedule manager
        self.startList = []                                                 # resources that need to be started
        # publish resources via remote service
        if publish:
            self.remoteService = RemoteService(self.name, self.resources, states=self.states, label=labelize(self.name), advert=advert)
        else:
            self.remoteService = None
        # remote resource proxy
        if remote:
            if separateRemote:     # separate collection for remote resources
                self.remoteEvent = threading.Event()
                self.remoteResources = Collection("remoteResources")
                self.globals["remoteResources"] = self.remoteResources
                self.remoteStates = StateCache("remoteStates", self.remoteResources, self.remoteEvent)      # resource state cache
                self.globals["remoteStates"] = self.remoteStates
            else:                   # use the same collection for remote and local resources
                self.remoteResources = self.resources
                self.remoteEvent = self.event
            self.remoteClient = RemoteClient("remoteClient", self.remoteResources, watch=watch, ignore=ignore,
                    resourceChanged=resourceChanged, event=self.remoteEvent)
        else:
            self.remoteClient = None
            self.remoteResources = None
        # data logger
        if logger:
            self.logger = DataLogger("logger", self.name, self.resources, self.states)
        else:
            self.logger = None
        # system resources
        if system:
            self.osInterface = OSInterface("osInterface")
            self.globals["osInterface"] = self.osInterface
            self.resource(Sensor(hostname+"CpuTemp", self.osInterface, "cpuTemp", type="tempC"))
            self.resource(Sensor(hostname+"CpuLoad", self.osInterface, "cpuLoad", type="%"))
            self.resource(Sensor(hostname+"Uptime", self.osInterface, "uptime"))
            self.resource(Sensor(hostname+"IpAddr", self.osInterface, "ipAddr"))
            self.resource(Sensor(hostname+"DiskUsage", self.osInterface, "diskUse /", type="%"))
            self.group("System")
            self.label()
        # persistent state
        if state:
            os.makedirs(stateDir, exist_ok=True)
            self.stateInterface = FileInterface("stateInterface", fileName=stateDir+self.name+".state", shared=shared, changeMonitor=changeMonitor)
            self.stateInterface.start(notify=self.fault)
            self.globals["stateInterface"] = self.stateInterface
        else:
            self.stateInterface = None                  # Interface resource for state file

    # run the application processes
    def run(self, block=True):
        # wait for the network to be available
        waitForNetwork(localController)
        if self.remoteClient:                   # remote resource proxy
            self.remoteClient.start()
            if self.separateRemote:
                self.remoteStates.start(notify=self.fault)       # remote resource state polling and monitoring
        self.states.start(notify=self.fault)                     # resource state polling and monitoring
        if self.logger:                         # data logger
            self.logger.start(notify=self.fault)
        for resource in self.startList:         # other resources
            resource.start(notify=self.fault)
        if list(self.schedule.keys()) != []:    # task scheduler
            self.schedule.start(notify=self.fault)
        if self.remoteService:                  # resource publication
            self.remoteService.start(block=block)
        else:
            if block:
                block()

    # define an Interface resource
    def interface(self, interface, event=False, start=False):
        self.globals[interface.name] = interface
        if event:
            interface.event = self.event
        if start:
            self.startList.append(interface)

    # define a Sensor or Control resource
    def resource(self, resource, event=False, publish=True, start=False):
        self.globals[resource.name] = resource
        if event:
            resource.event = self.event
        if publish:
            self.resources.addRes(resource)
        if start:
            self.startList.append(resource)

    # define a Sensor or Control resource that is remote on another server
    def remoteResource(self, resource):
        self.globals[resource.name] = resource
        resource.resources = self.remoteResources

    # define a Task resource
    def task(self, task, event=True, publish=True):
        self.schedule.addRes(task)
        self.globals[task.name] = task
        if event:
            task.event = self.event
        if publish:
            self.resources.addRes(task)

    # apply a UI type to one or more resources
    def type(self, type, resources=[]):
        if resources == []:     # default is all resources
            resources = list(self.resources.values())
        for resource in listize(resources):
            resource.type = type

    # associate one or more resources with one or more UI groups
    def group(self, group, resources=[]):
        if resources == []:     # default is all resources
            resources = list(self.resources.values())
        for resource in listize(resources):
            if resource.group == [""]:    # don't override if already set
                resource.group = group

    # add a UI label to one or more resources
    def label(self, label=None, resources=[]):
        if resources == []:     # default is all resources
            resources = list(self.resources.values())
        for resource in listize(resources):
            if not resource.label:      # don't override if already set
                if label:
                    resource.label = label
                else:               # create a label from the name
                    resource.label = labelize(resource.name)

    # callback for faults
    def fault(self, module, ex):
        log(self.name, module, str(ex))
        if self.remoteService:
            self.remoteService.setFault(True)
