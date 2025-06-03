# Extra sensors and controls derived from basic classes

from homealone.core import *

# Typical devices #############################################################

# A control for a generic device with two states.
class DeviceControl(Control):
    def __init__(self, name, interface, addr, type="control", **kwargs):
        Control.__init__(self, name, interface, addr,
                         type=type, states={0: "Off", 1: "On"}, **kwargs)
        self.className = "Control"

# A Control for a light switch
class LightControl(Control):
    def __init__(self, name, interface, addr, type="light", **kwargs):
        Control.__init__(self, name, interface, addr,
                         type=type, states={0: "Off", 1: "On"}, **kwargs)
        self.className = "Control"

# A Control for an electrical outlet
class OutletControl(Control):
    def __init__(self, name, interface, addr, type="outlet", **kwargs):
        Control.__init__(self, name, interface, addr,
                         type=type, states={0: "Off", 1: "On"}, **kwargs)
        self.className = "Control"

# A Sensor for a door
class DoorSensor(Sensor):
    def __init__(self, name, interface, addr, type="door", **kwargs):
        Sensor.__init__(self, name, interface, addr,
                        type=type, states={0: "Closed", 1: "Open"}, **kwargs)
        self.className = "Sensor"

# A Sensor for a window
class WindowSensor(Sensor):
    def __init__(self, name, interface, addr, type="window", **kwargs):
        Sensor.__init__(self, name, interface, addr,
                        type=type, states={0: "Closed", 1: "Open"}, **kwargs)
        self.className = "Sensor"

# Collections of devices ######################################################

# A collection of sensors whose state is on if any one of them is on
class SensorGroup(Sensor):
    def __init__(self, name, sensorList, states=None, **kwargs):
        if states is None:
            try:
                states = sensorList[0].states   # inherit states from sensors
            except (AttributeError, IndexError):
                pass        # this is a remote resource, ignore it
        Sensor.__init__(self, name, states=states, **kwargs)
        self.sensorList = sensorList

    def getState(self, missing=None):
        if self.interface:
            # This is a remote resource
            return Sensor.getState(self)
        else:
            groupState = 0
            for sensor in self.sensorList:
                sensorState = sensor.getState(missing=0)
                debug("debugSensorGroup", self.name, "sensor:", sensor.name, "state:", sensorState)
                groupState = groupState or sensorState    # group is on if any one sensor is on
            debug("debugSensorGroup", self.name, "groupState:", groupState)
            return groupState

    # attributes to include in the serialized object
    def dict(self, expand=False):
        attrs = Sensor.dict(self)
        attrs.update({"sensorList": [sensor.__str__() for sensor in self.sensorList]})
        return attrs

    # string representation of the object for display in a UI
    def __repr__(self):
        return "\n".join([sensor.__str__() for sensor in self.sensorList])

# A set of Controls whose state can be changed together
class ControlGroup(SensorGroup):
    def __init__(self, name, controlList, stateList=[], stateMode=False, wait=False, follow=False,
                 states=None, setStates=None, type="controlGroup", **kwargs):
        SensorGroup.__init__(self, name, controlList, type=type, states=states, **kwargs)
        self.stateMode = stateMode  # which state to return: False = SensorGroup, True = groupState
        self.setStates = setStates
        self.stateSet = None
        if self.setStates is None:
            if self.states is None:
                try:
                    self.setStates = controlList[0].setStates   # inherit setStates from controls
                except (AttributeError, IndexError):
                    pass        # this is a remote resource, ignore it
            else:
                self.setStates = self.states
        self.wait = wait
        self.follow = follow
        if follow:                  # state of all controls follows any change
            for sensor in self.sensorList:
                sensor.stateSet = self.stateWasSet
        self.groupState = 0
        if stateList == []:
            self.stateList = [[0,1]]*(len(self.sensorList))
        else:
            self.stateList = stateList

    def getState(self, missing=None):
        if self.interface:
            # This is a remote resource
            return Sensor.getState(self)
        else:
            if self.stateMode:
                return self.groupState
            else:
                return SensorGroup.getState(self)

    def setState(self, state, wait=False):
        if self.interface:
            # This is a remote resource
            return Control.setState(self, state)
        else:
            debug('debugState', self.name, "setState ", state)
            self.groupState = state # int(state)  # use Cycle - FIXME
            if self.wait:           # wait for it to run
                self.setGroup()
            else:                   # Run it asynchronously in a separate thread.
                startThread(name="setGroupThread", target=self.setGroup)
            self.notify(state)
            return True

    def setGroup(self):
        debug('debugThread', self.name, "started")
        for controlIdx in range(len(self.sensorList)):
            control = self.sensorList[controlIdx]
            debug("debugControlGroup", "setGroup", self.name, "control:", control.name, "state:", self.groupState)
            if isinstance(self.groupState, int):
                control.setState(self.stateList[controlIdx][self.groupState])
            else:
                control.setState(self.groupState)
        debug('debugThread', self.name, "finished")

    def stateWasSet(self, control, state):
        debug('debugState', "stateWasSet", control.name, "state:", state)
        for sensor in self.sensorList:
            if sensor != control:
                sensor.setState(state, notify=False)

    def notify(self, state=None):
        debug('debugState', "notify", self.name, "state:", state)
        Control.notify(self, state)

    # attributes to include in the serialized object
    def dict(self, expand=False):
        attrs = Control.dict(self)
        attrs.update({"controlList": [sensor.__str__() for sensor in self.sensorList]})
        return attrs

# A Control whose state depends on the states of a group of Sensors
class SensorGroupControl(SensorGroup):
    def __init__(self, name, sensorList, control,
                states=None, setStates=None, **kwargs):
        SensorGroup.__init__(self, name, sensorList, states=states, **kwargs)
        self.type = "sensorGroupControl"
        self.control = control
        self.setStates = setStates
        self.stateSet = None

    def getState(self, missing=None):
        if self.interface:
            # This is a remote resource
            return Sensor.getState(self)
        else:
            return self.control.getState()

    def setState(self, state):
        # set the control on if any of the sensors is on
        # set the control off only if all the sensors are off
        controlState = state
        for sensor in self.sensorList:
            controlState = controlState or sensor.getState()
        if self.interface:
            # This is a remote resource
            return Control.setState(self, controlState)
        else:
            debug("debugSensorGroupControl", self.name, "control:", self.control.name, "state:", state, "controlState:", controlState)
            self.control.setState(controlState)

    # attributes to include in the serialized object
    def dict(self, expand=False):
        attrs = Control.dict(self)
        attrs.update({"sensorList": [sensor.__str__() for sensor in self.sensorList],
                      "control": self.control.__str__()})
        return attrs

# A Sensor that only reports its state if all the specified resources are in the specified states
class DependentSensor(Sensor):
    def __init__(self, name, interface, sensor, conditions, **kwargs):
        Sensor.__init__(self, name, **kwargs)
        type = "sensor"
        self.className = "Sensor"
        self.sensor = sensor
        self.conditions = conditions

    def getState(self, missing=0.0):
        debug('debugState', self.name, "getState")
        for (sensor, condition, value) in self.conditions:
            sensorState = sensor.getState()
            sensorName = sensor.name
            if isinstance(value, Sensor):
                value = value.getState()
            debug('debugDependentControl', self.name, sensorName, sensorState, condition, value)
            try:
                if eval(str(sensorState)+condition+str(value)):
                    return self.sensor.getState()
                else:
                    return missing
            except Exception as ex:
                log(self.name, "exception evaluating condition", str(ex))
                return missing

# A Control that can only be turned on if all the specified resources are in the specified states
class DependentControl(Control):
    def __init__(self, name, interface, control, conditions, stateMode=False, states=None, setStates=None, **kwargs):
        if states is None:
            states = {0:"Off", 1:"On"}
        Control.__init__(self, name, states=states, setStates=setStates, **kwargs)
        type = "control"
        self.className = "Control"
        self.control = control
        self.conditions = conditions
        self.stateMode = stateMode  # which state to return: False = control state, True = current state
        self.curState = 0

    def getState(self, missing=None):
        if self.stateMode:
            return self.curState
        else:
            return self.control.getState()

    def setState(self, state, wait=False):
        self.curState = state
        debug('debugState', self.name, "setState ", state)
        for (sensor, condition, value) in self.conditions:
            sensorState = sensor.getState()
            sensorName = sensor.name
            if isinstance(value, Sensor):
                value = value.getState()
            debug('debugDependentControl', self.name, sensorName, sensorState, condition, value)
            try:
                condition = str(sensorState)+condition+str(value)
                if eval(condition):
                    self.control.setState(state)
            except Exception as ex:
                log(self.name, "exception evaluating condition", str(ex), condition)

# A Sensor that reports constant predefined values depending on the state of a specified sensor
class ConstSensor(Sensor):
    def __init__(self, name, interface, sensor, onValue, offValue=0, **kwargs):
        Sensor.__init__(self, name, **kwargs)
        type = "sensor"
        self.className = "Sensor"
        self.sensor = sensor
        self.onValue = onValue
        self.offValue = offValue

    def getState(self, missing=0.0):
        debug('debugState', self.name, "getState")
        if self.sensor.getState():
            return self.onValue
        else:
            return self.offValue

# Special devices #############################################################

# Devices that involve math ###################################################

# A Sensor that calculates a specified function using a list of sensor states
class CalcSensor(Sensor):
    def __init__(self, name, sensors=[], function="", **kwargs):
        Sensor.__init__(self, name, **kwargs)
        type = "sensor"
        self.sensors = sensors
        self.function = function.lower()
        self.className = "Sensor"

    def getState(self, missing=0):
        value = 0
        try:
            if self.function in ["sum", "avg", "+"]:
                for sensor in self.sensors:
                    value += sensor.getState(missing=0)
                if self.function == "avg":
                    value /+ len(self.sensors)
            elif self.function in ["*"]:
                for sensor in self.sensors:
                    value *= sensor.getState(missing=0)
            elif self.function in ["diff", "-"]:
                value = self.sensors[0].getState(missing=0) - self.sensors[1].getState(missing=0)
        except Exception as ex:
            logException(self.name, ex)
        return value

# Sensor that captures the minimum state value of the specified sensor
class MinSensor(Sensor):
    def __init__(self, name, interface, addr, sensor, **kwargs):
        Sensor.__init__(self, name, interface, addr, **kwargs)
        type = "sensor"
        self.className = "Sensor"
        self.sensor = sensor
        minState = self.interface.read(self.addr)
        if minState is not None:    # start with previous value
            self.minState = minState
        else:                       # initialize
            self.minState = 999

    def getState(self, missing=None):
        if self.interface:
            if self.interface.__class__.__name__ == "RestInterface":
                return self.interface.read(self.addr)
            else:
                self.minState = self.interface.read(self.addr)
        sensorState = self.sensor.getState()
        if sensorState is not None:
            if sensorState < self.minState:
                if sensorState != 0:    # FIXME
                    self.minState = sensorState
                    if self.interface:
                        self.interface.write(self.addr, self.minState)
        return self.minState

    # reset the min value
    def setState(self, value):
        self.minState = value
        if self.interface:
            self.interface.write(self.addr, self.minState)

    # attributes to include in the serialized object
    # def dict(self, expand=False):
    #     attrs = Control.dict(self)
    #     attrs.update({"sensor": str(self.sensor)})
    #     return attrs

# Sensor that captures the maximum state value of the specified sensor
class MaxSensor(Sensor):
    def __init__(self, name, interface, addr, sensor, **kwargs):
        Sensor.__init__(self, name, interface, addr, **kwargs)
        type = "sensor"
        self.className = "Sensor"
        self.sensor = sensor
        maxState = self.interface.read(self.addr)
        if maxState is not None:    # start with previous value
            self.maxState = maxState
        else:                       # initialize
            self.maxState = 0

    def getState(self, missing=0):
        if self.interface:
            if self.interface.__class__.__name__ == "RestInterface":
                return self.interface.read(self.addr)
            else:
                self.maxState = self.interface.read(self.addr)
        sensorState = self.sensor.getState()
        if sensorState is not None:
            if sensorState > self.maxState:
                self.maxState = sensorState
                if self.interface:
                    self.interface.write(self.addr, self.maxState)
        return self.maxState

    # reset the max value
    def setState(self, value):
        self.maxState = value
        if self.interface:
            self.interface.write(self.addr, self.maxState)

    # attributes to include in the serialized object
    # def dict(self, expand=False):
    #     attrs = Control.dict(self)
    #     attrs.update({"sensor": str(self.sensor)})
    #     return attrs

# Sensor that captures the accumulated state values of the specified sensor
class AccumSensor(Sensor):
    def __init__(self, name, interface, sensor, multiplier=1, **kwargs):
        Sensor.__init__(self, name, interface, addr, **kwargs)
        type = "sensor"
        self.className = "Sensor"
        self.sensor = sensor
        self.multiplier = multiplier
        accumValue = self.interface.read(self.name)
        if accumValue is not None:      # start with previous value
            self.accumValue = accumValue
        else:                           # initialize
            self.accumValue = 0

    def getState(self, missing=0):
        sensorState = self.sensor.getState()
        if sensorState is not None:
            self.accumValue = sensorState * self.multiplier
            if self.interface:
                self.interface.write(self.name, self.accumValue)
        return self.accumValue

    # reset the accumulated value
    def setState(self, value):
        self.accumValue = value
        if self.interface:
            self.interface.write(self.name, self.accumValue)

# Control that can be set on but reverts to off after a specified time
class MomentaryControl(Control):
    def __init__(self, name, interface, addr=None, duration=1, states=None, setStates=None, **kwargs):
        if states is None:
            states = {0:"Off", 1:"On"}
        Control.__init__(self, name, interface, addr, states=states, setStates=setStates, **kwargs)
        type="control"
        self.className = "Control"
        self.duration = duration
        self.timedState = 0
        self.timer = None

    def setState(self, state, wait=False):
        # timeout is the length of time the control will stay on
        debug("debugState", "MomentaryControl", self.name, "setState", state)
        if not self.timedState:
            self.timedState = state
            if self.interface:
                self.interface.write(self.addr, self.timedState)
            self.timer = threading.Timer(self.duration, self.timeout)
            self.timer.start()
            debug("debugState", "MomentaryControl", self.name, "timer", self.timedState)
            self.notify()

    def timeout(self):
        self.timedState = 0
        debug("debugState", "MomentaryControl", self.name, "timeout", self.duration)
        debug("debugState", "MomentaryControl", self.name, "setState", self.timedState)
        if self.interface:
            self.interface.write(self.addr, self.timedState)
        self.notify()

    def getState(self, missing=None):
        return self.timedState

# a control that has a persistent state
# the interface must be one that supports persistence such as FileInterface
class StateControl(Control):
    def __init__(self, name, interface, addr=None, initial=0, **kwargs):
        Control.__init__(self, name, interface, addr, **kwargs)
        self.className = "Control"
        if not self.addr:
            self.addr = self.name
        self.initial = initial

    def getState(self, **kwargs):
        state = Control.getState(self, **kwargs)
        if state != None:
            return state
        else:
            Control.setState(self, self.initial)
            return self.initial

    def setState(self, value, **kwargs):
        Control.setState(self, value)

# A Control that has specified numeric limits on the values it can be set to
# the interface must be one that supports persistence such as FileInterface
class MinMaxControl(StateControl):
    def __init__(self, name, interface, addr=None, min=0, max=1, **kwargs):
        StateControl.__init__(self, name, interface, addr, **kwargs)
        type = "control"
        self.className = "Control"
        self.min = min
        self.max = max

    def setState(self, state, wait=False):
        state = int(state)
        debug("debugState", "MinMaxControl", self.name, "setState", state, self.min, self.max)
        if state < self.min:
            value = self.min
        elif state > self.max:
            value = self.max
        else:
            value = state
        Control.setState(self, value)

# Control that has a specified list of values it can be set to
# the interface must be one that supports persistence such as FileInterface
class MultiControl(StateControl):
    def __init__(self, name, interface, addr=None, values=[], **kwargs):
        StateControl.__init__(self, name, interface, addr, **kwargs)
        type = "control"
        self.className = "MultiControl"
        self.values = values

    def setState(self, state, wait=False):
        debug("debugState", "MultiControl", self.name, "setState", state, self.values)
        if state in self.values:
            return Control.setState(self, state)
        else:
            return False

    # attributes to include in the serialized object
    def dict(self, expand=False):
        attrs = Control.dict(self)
        attrs.update({"values": self.values})
        return attrs

# sensor that returns the value of an attribute of a specified sensor
class AttributeSensor(Sensor):
    def __init__(self, name, interface, addr, sensor, attr, **kwargs):
        Sensor.__init__(self, name, interface, addr, **kwargs)
        type = "sensor"
        self.sensor = sensor
        self.attr = attr

    def getState(self, missing=None):
        return getattr(self.sensor, self.attr)

    # attributes to include in the serialized object
    def dict(self, expand=False):
        attrs = Sensor.dict(self)
        attrs.update({"sensor": str(self.sensor),
                      "attr": self.attr})
        return attrs

# sensor that is an alias for another sensor
class AliasSensor(Sensor):
    def __init__(self, name, interface, addr, sensor, **kwargs):
        Sensor.__init__(self, name, interface, addr, **kwargs)
        type = "sensor"
        self.className = "Sensor"
        self.sensor = sensor

    def getState(self, missing=None):
        return self.sensor.getState()

# Remote devices ##############################################################

# a sensor that is located on another server
class RemoteSensor(Sensor):
    def __init__(self, name, resources=None, states=None, **kwargs):
        Sensor.__init__(self, name, states=states, **kwargs)
        self.resources = resources

    def getState(self, missing=None):
        try:
            state = self.resources[self.name].getState(missing=missing)
            self.enable()
            return state
        except (KeyError, TypeError):
            self.disable()
            return missing

# a control that is on another another server
class RemoteControl(RemoteSensor):
    def __init__(self, name, resources=None, states=None, setStates=None, **kwargs):
        RemoteSensor.__init__(self, name, resources, states=states, **kwargs)
        self.resources = resources
        self.setStates = setStates

    def setState(self, value, **kwargs):
        try:
            return self.resources[self.name].setState(value, **kwargs)
        except KeyError:
            return False
