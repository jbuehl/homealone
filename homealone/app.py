# application template

from .core import *
from .schedule import *
from .rest.restServer import *
from .rest.restProxy import *
from .logging.logging import *
from .interfaces.fileInterface import *

class Application(object):
    def __init__(self, name, globals,
                 publish=True,
                 state=False, shared=False, changeMonitor=True,
                 # metrics=False,
                 remote=False, watch=[], ignore=[]):
        self.name = name
        self.globals = globals                      # application global variables
        self.publish = publish                      # run REST server if true
        self.state = state                          # create and maintain a state file if true
        self.shared = shared
        self.changeMonitor = changeMonitor
        self.stateInterface = None                  # Interface resource for state file
        # self.metrics = metrics                      # publish metrics if true
        self.event = threading.Event()              # state change event
        self.resources = Collection("resources", event=self.event)    # resources to be published by REST server
        self.globals["resources"] = self.resources
        self.schedule = Schedule("schedule")        # schedule of tasks to run
        self.startList = []                         # resources that need to be started
        self.remote = remote
        self.restProxy = None
        self.remoteResources = None
        self.logger = DataLogger("logger", self.name, self.resources)

        if state:
            if not os.path.exists(stateDir):
                os.mkdir(stateDir)
            self.stateInterface = FileInterface("stateInterface", fileName=stateDir+self.name+".state", shared=shared, changeMonitor=changeMonitor)
            self.stateInterface.start()
            self.globals["stateInterface"] = self.stateInterface
        if remote:
            self.remoteResources = Collection("remoteResources", event=self.event)
            self.globals["remoteResources"] = self.remoteResources
            self.restProxy = RestProxy("restProxy", self.remoteResources, watch=watch, ignore=ignore, event=self.event)

    # start the application processes
    def run(self):
        if self.remote:
            self.restProxy.start()
        if self.logger:
            self.logger.start()
        for resource in self.startList:
            resource.start()
        if list(self.schedule.keys()) != []:
            self.schedule.start()
        if self.publish:
            self.restServer = RestServer(self.name, self.resources, event=self.event, label=self.name)
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
        self.globals[task.name] = self.schedule[task.name]
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
