# Homealone home automation platform resources

### Interfaces
These modules have been developed that map a number of number of hardware devices to Homealone Interface objects.  Many of them are dependent on 3rd party libraries.

#### ADS1x15 interface
Interface to the ADS1x15 family of analog to digital converters.  It includes code from the Adafruit_ADS1x15 library.

#### File interface
An interface that provides persistent state.  Key value pairs are maintained as JSON in the OS filesystem.

#### GPIO interface
Interface to the GPIO pins of the hardware device.  It uses the RPi.GPIO library.

#### I2C interface
Interface to I<sup>2</sup>C devices using the smbus library.

#### MCP23017 interface
This interface allows use of the MCP23017 GPIO extender to provide additional GPIO pins.

#### OS interface
AN interface that provides access to a few key OS metrics.

#### OWFS interface
Interface to the One Wire File System that supports 1-wire devices connected in a variety of ways such as serial, USB, I<sup>2</sup>C, and GPIO.

#### Serial interface
An interface that provides access to serial devices.

#### TC74 interface
Interface to the TC74 temperature sensor.

#### Time interface
Provides an interface for various time functions.

#### TPLink interface
A proxy to TPLink devices using the TP-Link Smart Home Protocol.

#### W1 interface
Interface to the W1 interface that supports 1-wire temperature sensors connected directly to GPIO.  It uses the w1thermsensor interface.

### Sensor and Control resources
These modules implement Sensors and Controls for more complex functions that build on the Homealone core classes.

#### Electrical sensors
Sensors related to electrical devices.

    - class PowerSensor(Sensor):
    - class EnergySensor(Sensor):
    - class BatterySensor(Sensor):

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
