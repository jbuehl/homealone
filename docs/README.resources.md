# Homealone home automation platform resources

### Interfaces
These modules have been developed that map a number of number of hardware devices to Homealone Interface objects.  Many of them are dependent on 3rd party libraries.

#### ADS1x15 interface
Interface to the ADS1x15 family of analog to digital converters.

#### File interface

#### GPIO interface

#### I2C interface

#### MCP23017 interface

#### OS interface

#### OWFS interface
Interface to the One Wire File System that supports 1-wire devices connected in a variety of ways such as serial, USB, I<sup>2</sup>C, and GPIO.

#### Serial interface

#### Shade interface

#### TC74 interface

#### Time interface

#### TPLink interface

#### W1 interface
Interface to the W1 interface that supports 1-wire devices connected directly to GPIO.

### Sensor and Control resources
These modules implement Sensors and Controls that build on the Homealone core classes.

#### Electrical sensors
Sensors related to electrical devices.

#### Extra resources
A collection of generally useful Sensors and Controls.

	+ class SensorGroup(Sensor):
		- class ControlGroup(SensorGroup, Control):
		- class SensorGroupControl(SensorGroup, Control):
	- class CalcSensor(Sensor):
    - class DependentSensor(Sensor):
    - class DependentControl(Control):
	- class MomentaryControl(Control):
    + class StateControl(Control):
    	- class MultiControl(StateControl):
    	- class MinMaxControl(StateControl):
	- class MinSensor(Sensor):
	- class MaxSensor(Sensor):
	- class AccumSensor(Sensor):
	- class AttributeSensor(Sensor):
	+ class RemoteSensor(Sensor):
	 	- class RemoteControl(RemoteSensor):

#### Temp control
A Control that manages a heating or cooling unit.

#### Thermostat control
A control that emulates a device for controlling a heating and cooling system.
