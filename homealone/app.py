# application template

from .core import *
from .schedule import *
from .rest.restServer import *
from .rest.restProxy import *
from .logging.logging import *
from .interfaces.fileInterface import *
from homealone.interfaces.osInterface import *

class Application(object):
    def __init__(self, name, globals,
                 publish=True, advert=True,                                 # resource publishing parameters
                 remote=False, watch=[], ignore=[], remoteResources=True,   # remote resource proxy parameters
                    remoteEvent=False,
                 logger=True,                                               # data logger
                 system=False,                                              # system resources
                 state=False, shared=False, changeMonitor=True):            # persistent state parameters
        self.name = name
        self.globals = globals                                              # application global variables
        self.event = threading.Event()                                      # state change event
        self.resources = Collection("resources", event=self.event)          # application resources
        self.globals["resources"] = self.resources
        self.schedule = Schedule("schedule")                                # schedule of tasks to run
        self.startList = []                                                 # resources that need to be started
        # publish resources via REST server
        if publish:
            self.restServer = RestServer(self.name, self.resources, event=self.event, label=self.name, advert=advert)
        else:
            self.restServer = None
        # remote resource proxy
        if remote:
            if remoteResources:     # separate collection for remote resources
                if remoteEvent:     # separate event for remote resources
                    self.remoteEvent = threading.Event()
                else:
                    self.remoteEvent = self.event
                self.remoteResources = Collection("remoteResources", event=self.remoteEvent)
                self.globals["remoteResources"] = self.remoteResources
            else:                   # use the same collection for remote and local resources
                self.remoteResources = self.resources
            self.restProxy = RestProxy("restProxy", self.remoteResources, watch=watch, ignore=ignore, event=self.event)
        else:
            self.restProxy = None
            self.remoteResources = None
        # data logger
        if logger:
            self.logger = DataLogger("logger", self.name, self.resources)
        else:
            self.logger = None
        # system resources
        if system:
            self.osInterface = OSInterface("osInterface")
            self.globals["osInterface"] = self.osInterface
            self.resource(Sensor(hostname+"CpuTemp", self.osInterface, "cpuTemp", style="tempC"))
            self.resource(Sensor(hostname+"CpuLoad", self.osInterface, "cpuLoad", style="pct"))
            self.resource(Sensor(hostname+"Uptime", self.osInterface, "uptime"))
            self.resource(Sensor(hostname+"IpAddr", self.osInterface, "ipAddr eth0"))
            self.resource(Sensor(hostname+"DiskUsage", self.osInterface, "diskUse /", style="pct"))
            self.group("System")
            self.label()
        # persistent state
        if state:
            os.makedirs(stateDir, exist_ok=True)
            self.stateInterface = FileInterface("stateInterface", fileName=stateDir+self.name+".state", shared=shared, changeMonitor=changeMonitor)
            self.stateInterface.start()
            self.globals["stateInterface"] = self.stateInterface
        else:
            self.stateInterface = None                  # Interface resource for state file

    # run the application processes
    def run(self):
        if self.restProxy:                      # remote resource proxy
            self.restProxy.start()
        if self.logger:                         # data logger
            self.logger.start()
        for resource in self.startList:         # other resources
            resource.start()
        if list(self.schedule.keys()) != []:    # task schedule
            self.schedule.start()
        if self.restServer:                     # resource publication
            self.restServer.start()

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
        self.schedule.addTask(task)
        self.globals[task.name] = task
        if event:
            task.event = self.event
        if publish:
            self.resources.addRes(task)

    # apply a UI style to one or more resources
    def style(self, style, resources=[]):
        if resources == []:     # default is all resources
            resources = list(self.resources.values())
        for resource in listize(resources):
            resource.type = style

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
