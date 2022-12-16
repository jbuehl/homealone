# Extra sensors and controls derived from basic classes

from homealone.core import *

# A collection of sensors whose state is on if any one of them is on
class SensorGroup(Sensor):
    def __init__(self, name, sensorList, **kwargs):
        Sensor.__init__(self, name, **kwargs)
        self.sensorList = sensorList

    def getState(self, missing=None):
        if self.interface:
            # This is a cached resource
            return Sensor.getState(self)
        else:
            groupState = 0
            for sensor in self.sensorList:
                sensorState = sensor.getState(missing=0)
                debug("debugSensorGroup", self.name, "sensor:", sensor.name, "state:", sensorState)
                groupState = groupState or sensorState    # group is on if any one sensor is on
            debug("debugSensorGroup", self.name, "groupState:", groupState)
            return groupState

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        attrs = Sensor.dict(self)
        attrs.update({"sensorList": [sensor.__str__() for sensor in self.sensorList]})
        return attrs

    def __repr__(self):
        return "\n".join([sensor.__str__() for sensor in self.sensorList])

# A set of Controls whose state can be changed together
class ControlGroup(SensorGroup, Control):
    def __init__(self, name, controlList, stateList=[], stateMode=False, wait=False, style="controlGroup", **kwargs):
        SensorGroup.__init__(self, name, controlList, style=style, **kwargs)
        Control.__init__(self, name, **kwargs)
        self.stateMode = stateMode  # which state to return: False = SensorGroup, True = groupState
        self.wait = wait
        self.groupState = 0
        if stateList == []:
            self.stateList = [[0,1]]*(len(self.sensorList))
        else:
            self.stateList = stateList

    def getState(self, missing=None):
        if self.interface:
            # This is a cached resource
            return Sensor.getState(self)
        else:
            if self.stateMode:
                return self.groupState
            else:
                return SensorGroup.getState(self)

    def setState(self, state, wait=False):
        if self.interface:
            # This is a cached resource
            return Control.setState(self, state)
        else:
            debug('debugState', self.name, "setState ", state)
            self.groupState = state # int(state)  # use Cycle - FIXME
            # Run it asynchronously in a separate thread.
            def setGroup():
                debug('debugThread', self.name, "started")
                for controlIdx in range(len(self.sensorList)):
                    control = self.sensorList[controlIdx]
                    debug("debugControlGroup", self.name, "control:", control.name, "state:", self.groupState)
                    if isinstance(self.groupState, int):
                        control.setState(self.stateList[controlIdx][self.groupState])
                    else:
                        control.setState(self.groupState)
                debug('debugThread', self.name, "finished")
            if self.wait:
                setGroup()
            else:
                startThread(name="setGroupThread", target=setGroup)
            self.notify(state)
            return True

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        attrs = Control.dict(self)
        attrs.update({"controlList": [sensor.__str__() for sensor in self.sensorList]})
        return attrs

# A Control whose state depends on the states of a group of Sensors
class SensorGroupControl(SensorGroup, Control):
    def __init__(self, name, sensorList, control, **kwargs):
        Control.__init__(self, name, **kwargs)
        SensorGroup.__init__(self, name, sensorList, **kwargs)
        self.type = "sensorGroupControl"
        self.control = control

    def getState(self, missing=None):
        if self.interface:
            # This is a cached resource
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
            # This is a cached resource
            return Control.setState(self, controlState)
        else:
            debug("debugSensorGroupControl", self.name, "control:", self.control.name, "state:", state, "controlState:", controlState)
            self.control.setState(controlState)

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        attrs = Control.dict(self)
        attrs.update({"sensorList": [sensor.__str__() for sensor in self.sensorList],
                      "control": self.control.__str__()})
        return attrs

# Calculate a function of a list of sensor states
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

# Sensor that only reports its state if all the specified resources are in the specified states
class DependentSensor(Sensor):
    def __init__(self, name, interface, sensor, conditions, default=off, **kwargs):
        Sensor.__init__(self, name, **kwargs)
        type = "sensor"
        self.className = "Sensor"
        self.sensor = sensor
        self.conditions = conditions
        self.default = default

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

# Control that can only be turned on if all the specified resources are in the specified states
class DependentControl(Control):
    def __init__(self, name, interface, control, conditions, **kwargs):
        Control.__init__(self, name, **kwargs)
        type = "control"
        self.className = "Control"
        self.control = control
        self.conditions = conditions

    def getState(self, missing=None):
        return self.control.getState()

    def setState(self, state, wait=False):
        debug('debugState', self.name, "setState ", state)
        for (sensor, condition, value) in self.conditions:
            sensorState = sensor.getState()
            sensorName = sensor.name
            if isinstance(value, Sensor):
                value = value.getState()
            debug('debugDependentControl', self.name, sensorName, sensorState, condition, value)
            try:
                if eval(str(sensorState)+condition+str(value)):
                    self.control.setState(state)
            except Exception as ex:
                log(self.name, "exception evaluating condition", str(ex))

# Control that can be set on but reverts to off after a specified time
class MomentaryControl(Control):
    def __init__(self, name, interface, addr=None, duration=1, **kwargs):
        Control.__init__(self, name, interface, addr, **kwargs)
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

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        attrs = Control.dict(self)
        attrs.update({"values": self.values})
        return attrs

# Control that has specified numeric limits on the values it can be set to
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

# Sensor that captures the minimum state value of the specified sensor
class MinSensor(Sensor):
    def __init__(self, name, interface, addr, sensor, **kwargs):
        Sensor.__init__(self, name, interface, addr, **kwargs)
        type = "sensor"
        self.className = "Sensor"
        self.sensor = sensor
        try:
            self.minState = self.interface.read(self.addr)
        except:
            self.minState = 999

    def getState(self, missing=None):
        if self.interface:
            if self.interface.__class__.__name__ == "RestInterface":
                return self.interface.read(self.addr)
            else:
                self.minState = self.interface.read(self.addr)
        sensorState = self.sensor.getState()
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

    # dictionary of pertinent attributes
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
        try:
            self.maxState = self.interface.read(self.addr)
        except:
            self.maxState = 0

    def getState(self, missing=0):
        if self.interface:
            if self.interface.__class__.__name__ == "RestInterface":
                return self.interface.read(self.addr)
            else:
                self.maxState = self.interface.read(self.addr)
        sensorState = self.sensor.getState()
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

    # dictionary of pertinent attributes
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
        try:
            self.accumValue = self.interface.read(self.name)
        except:
            self.accumValue = 0

    def getState(selfmissing=0):
        self.accumValue = self.sensor.getState() * self.multiplier
        if self.interface:
            self.interface.write(self.name, self.accumValue)
        return self.accumValue

    # reset the accumulated value
    def setState(self, value):
        self.accumValue = value
        if self.interface:
            self.interface.write(self.name, self.accumValue)

# sensor that returns the value of an attribute of a specified sensor
class AttributeSensor(Sensor):
    def __init__(self, name, interface, addr, sensor, attr, **kwargs):
        Sensor.__init__(self, name, interface, addr, **kwargs)
        type = "sensor"
        self.sensor = sensor
        self.attr = attr

    def getState(self, missing=None):
        return getattr(self.sensor, self.attr)

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        attrs = Sensor.dict(self)
        attrs.update({"sensor": str(self.sensor),
                      "attr": self.attr})
        return attrs

# a remote sensor that is located on another server
class RemoteSensor(Sensor):
    def __init__(self, name, resources=None, **kwargs):
        Sensor.__init__(self, name, **kwargs)
        self.resources = resources

    def getState(self, missing=None):
        try:
            state = self.resources[self.name].getState(missing=missing)
            self.enable()
            return state
        except KeyError:
            self.disable()
            return missing

# a remote control that is on another another server
class RemoteControl(RemoteSensor):
    def __init__(self, name, resources=None, **kwargs):
        RemoteSensor.__init__(self, name, resources, **kwargs)
        self.resources = resources

    def setState(self, value, **kwargs):
        try:
            return self.resources[self.name].setState(value, **kwargs)
        except KeyError:
            return False
