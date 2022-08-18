# state values
modeOff = 0
modeHeat = 1
modeCool = 2
modeFan = 3
modeAuto = 4

inhibitDelay = 60
inhibitState = 1
inhibitWatchInterval = 1
defaultTemp = 72

from homealone import *
from homealone.resources.tempControl import *

# thermostat control for heating and cooling
class ThermostatControl(Control):
    def __init__(self, name, heatUnit, coolUnit, fanUnit, tempSensor, heatTempTargetControl, coolTempTargetControl,
                 inhibitSensor=None, persistenceControl=None, hysteresis=[1, 1], **kwargs):
        Control.__init__(self, name, **kwargs)
        self.className = "Control"
        self.heatControl = TempControl(self.name+"HeatControl", None, heatUnit, tempSensor, heatTempTargetControl,
                                       unitType=unitTypeHeater, hysteresis=hysteresis)
        self.coolControl = TempControl(self.name+"CoolControl", None, coolUnit, tempSensor, coolTempTargetControl,
                                       unitType=unitTypeAc, hysteresis=hysteresis)
        self.fanUnit = fanUnit                          # the fan unit
        self.tempSensor = tempSensor                    # the temperature sensor
        self.heatTempTargetControl = heatTempTargetControl
        self.heatTempTargetControl.stateSet=self.tempTargetState
        self.coolTempTargetControl = coolTempTargetControl
        self.coolTempTargetControl.stateSet=self.tempTargetState
        self.inhibitSensor = inhibitSensor              # sensor that inhibits thermostat operation if it is on
        # if self.inhibitSensor:
        #     self.setInhibit(self.inhibitSensor.getState())
        # else:
        #     self.inhibited = False
        self.inhibited = False
        self.persistenceControl = persistenceControl    # persistent storage of the state
        self.hysteresis = hysteresis

    def start(self):
        if self.persistenceControl:
            currentState = self.persistenceControl.getState()
            if currentState == None:
                self.setState(modeOff)
            else:
                self.setState(currentState)
        else:
            self.setState(modeOff)

        # inhibit the tempControl after a delay
        def inhibitTimer():
            debug('debugThermostatEvent', self.name, "inhibitTimer ended")
            self.setInhibit(True)

        # thread to monitor the state of the inhibit sensor
        def inhibitWatch():
            debug('debugThermostatEvent', self.name, "inhibitWatch started")
            inhibitTimerThread = None
            while True:
                if self.inhibitSensor.event:        # wait for inhibitSensor state to change
                    debug('debugThermostatEvent', self.name, "waiting for", self.inhibitSensor.name, "event")
                    self.inhibitSensor.event.wait()
                else:                               # poll inhibitSensor state
                    debug('debugThermostatEvent', self.name, "waiting for", inhibitWatchInterval, "seconds")
                    time.sleep(inhibitWatchInterval)
                if self.inhibitSensor.getState() == inhibitState:
                    if not inhibitTimerThread:      # start the delay timer
                        inhibitTimerThread = threading.Timer(inhibitDelay, inhibitTimer)
                        inhibitTimerThread.start()
                        debug('debugThermostatEvent', self.name, "inhibitTimer started")
                else:
                    if self.inhibited:                               # state changed back, cancel the timer and enable the thermostat
                        self.setInhibit(False)
                    if inhibitTimerThread:
                        inhibitTimerThread.cancel()
                        debug('debugThermostatEvent', self.name, "inhibitTimer cancelled")
                        inhibitTimerThread = None

        self.inhibited = False
        if self.inhibitSensor:                      # start the thread to watch the state of the inhibit sensor
            inhibitWatchThread = LogThread(name="inhibitWatchThread", target=inhibitWatch)
            inhibitWatchThread.start()

    def setInhibit(self, value):
        debug('debugThermostat', self.name, "inhibit", value)
        self.inhibited = value
        self.heatControl.setInhibit(value)
        self.coolControl.setInhibit(value)

    def getState(self, wait=False, missing=None):
        debug('debugState', self.name, "getState ", self.currentState)
        return self.currentState

    def setState(self, state, wait=False):
        debug('debugState', self.name, "setState ", state)
        if state == modeOff:
            self.heatControl.setState(off)
            self.coolControl.setState(off)
            self.fanUnit.setState(off)
        elif state == modeHeat:
            self.heatControl.setState(on)
            self.coolControl.setState(off)
            self.fanUnit.setState(off)
        elif state == modeCool:
            self.heatControl.setState(off)
            self.coolControl.setState(on)
            self.fanUnit.setState(off)
        elif state == modeFan:
            self.heatControl.setState(off)
            self.coolControl.setState(off)
            self.fanUnit.setState(on)
        elif state == modeAuto:
            self.heatControl.setState(on)
            self.coolControl.setState(on)
            self.fanUnit.setState(off)
        else:
            debug('debugThermostat', self.name, "unknown state", state)
            return
        self.currentState = state
        if self.persistenceControl:
            self.persistenceControl.setState(state)
        self.notify()

    # callback for temp target control states
    def tempTargetState(self, control, state):
        debug('debugThermostat', "TempTargetState", control.name, state)
        # prevent the heating and cooling temp targets from overlapping
        tempSeparation = self.hysteresis[0] + self.hysteresis[1]
        minCoolTemp = state + tempSeparation
        maxHeatTemp = state - tempSeparation
        if control == self.heatTempTargetControl:   # heat temp is being set
            if self.coolTempTargetControl.getState() < minCoolTemp:
                self.coolTempTargetControl.setState(minCoolTemp)    # adjust the cool temp
        else:                                               # cool temp is being set
            if self.heatTempTargetControl.getState() > maxHeatTemp:
                self.heatTempTargetControl.setState(maxHeatTemp)    # adjust the heat temp

heatOn = modeHeat
coolOn = modeCool
fanOn = modeFan
hold = 5

# Sensor that returns the thermostat unit control that is currently running
class ThermostatUnitSensor(Sensor):
    def __init__(self, name, thermostatControl, **kwargs):
        Sensor.__init__(self, name, **kwargs)
        self.className = "Sensor"
        self.thermostatControl = thermostatControl

    def getState(self, missing=None):
        # assume only one of them is on
        if self.thermostatControl.getState() == Off:
            return Off
        elif self.thermostatControl.fanUnit.getState() == On:
            return fanOn
        elif self.thermostatControl.inhibited:
            return hold
        elif self.thermostatControl.heatControl.unitControl.getState() == On:
            return heatOn
        elif self.thermostatControl.coolControl.unitControl.getState() == On:
            return coolOn
        else:
            return Off

# Control that sets the target temperature of the active unit control
class ThermostatTempControl(Control):
    def __init__(self, name, thermostatControl, **kwargs):
        Control.__init__(self, name, **kwargs)
        self.className = "Control"
        self.thermostatControl = thermostatControl
        self.temp = defaultTemp

    def getState(self):
        return self.temp

    def setState(self, temp):
        mode = self.thermostatControl.getState()
        roomTemp = self.thermostatControl.tempSensor.getState()
        debug('debugThermostat', self.name, "setState", "temp:", temp, "mode:", mode, "roomTemp:", roomTemp)
        if (mode == modeHeat) or ((mode == modeAuto) and ((temp < defaultTemp) or ((temp == defaultTemp) and (roomTemp < defaultTemp)))):
            debug('debugThermostat', self.name, "setting heat target to", temp)
            self.thermostatControl.heatControl.tempTargetControl.setState(temp)
        elif (mode == modeCool) or ((mode == modeAuto) and ((temp > defaultTemp) or ((temp == defaultTemp) and (roomTemp > defaultTemp)))):
            debug('debugThermostat', self.name, "setting cool target to", temp)
            self.thermostatControl.coolControl.tempTargetControl.setState(temp)
        else: # do nothing
            debug('debugThermostat', self.name, "not setting temp")
            return
        self.temp = temp
