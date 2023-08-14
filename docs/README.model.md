# Homealone object model

### Terminology

First, let's define the terminology used in this project.

##### HARDWARE
These describe the physical hardware that the system is built from.

- device - a hardware component that makes up the system
- sensor - a device that has a state that can be read
- control - a device that has a state that can be read and also changed
- server - a device that may be connected to one or more sensors and communicates with one or more clients
- client - a device that communicates with one or more servers
- interface - the connection over which two devices communicate

##### OBJECT MODEL
These are the core Python classes that are used to describe the system.

- Object - the base class for everything
- Resource - base class for resources
- Sensor - a resource that is a representation of a physical sensor
- Control - a resource that is a representation of a physical control
- Interface - a resource that is a representation of a physical interface
- Collection - a resource that is an ordered list of resources

##### IMPLEMENTATION
These terms describe the roles played by the software components in the system.

- application - the implementation of a collection of resources and interfaces that runs on a server
- service - an application that implements the server side of the Remote interface to a client device or server device
- client - an application that implements the client side of the Remote interface to a server device


### Object model
The object model is defined by the following core classes:

```mermaid
classDiagram
	Object <|-- Resource
	Resource <|--Interface
	Resource <|--Sensor
	Sensor <|-- Control
	Resource <|--Collection
	Object: className
	Object: dump()
	Resource: name
	Resource: type
	Resource: enable()
	Resource: disable()
	Interface : interface
	Interface : sensors
	Interface : event
	Interface : start()
	Interface : stop()
	Interface : read(addr)
	Interface : write(addr, value)
	Interface : notify()
	Sensor : interface
	Sensor : addr
	Sensor : event
	Sensor : label
	Sensor : group
	Sensor : location
	Sensor : getState()
	Sensor : notify()
	Control : setState(value)
	Collection : addRes()
	Collection : getRes()
	Collection : delRes()
```

	+ class Object(object):
		+ class Resource(Object):
		    - class Interface(Resource):
		    + class Sensor(Resource):
		        - class Control(Sensor):
		    + class Collection(Resource, OrderedDict):

##### Object
The base class for Homealone objects.  It implements the dump() function which is used to serialize objects as JSON.  Deserialization is implemented by the static loadResource() function.

	- className
	- dump()

##### Resource
The base class for all Homealone resources.

    - name
	- type
	- enable()
	- disable()

##### Interface
Defines the abstract class for interface implementations.

    - interface
    - sensors
    - event
    - start()
    - stop()
    - read(addr)
    - write(addr, value)
    - notify()

##### Sensor
Defines the model for the base Homealone sensor.

    - interface
    - addr
    - event
    - label
    - group
    - location
    - notify()
    - getState()

##### Control
Defines the model for a sensor whose state can be changed.

    - setState(value)

##### Collection
Defines an ordered collection of Resources.

	- addRes()
	- delRes()
	- getRes()

### Time related classes
These classes are inherited from the core classes and implement time based functions:

	- class Schedule(Collection):
    - class Cycle(Object):
	- class Sequence(Control):
	- class Task(Control):
    - class SchedTime(Object):

### Example
A simple example is a temperature sensor that may be in a room, outside the house, or immersed in a swimming pool.  All it does is to report the ambient temperature of the air or water it is in.  Let's consider a digital temperature sensor that uses the I<sup>2</sup>C hardware interface.  When a read command is sent to the address of the device it returns a byte that represents the temperature in degrees Celsius.  Two software objects defined by this project are required: a Sensor and an Interface.  The Sensor can be just the base object because all it needs to do is to implement the get state function that reads the state of the sensor from the interface it is associated with.  The Interface object must be specific to the I<sup>2</sup>C interface so it is a I2CInterface object that is derived from the base Interface object.  It can use the Python SMBus library that performs all the low level I<sup>2</sup>C protocol functions to read a byte and implement the read function.

Another example is a sprinkler valve.  The state of the valve is either open or closed, and it is operated remotely from the network.  The voltage to the valve is switched using a relay or semiconductor that is controlled by a GPIO pin on the controller.  A Control object and an Interface object are needed to implement this.  The Control object inherits the get state function from the Sensor object, but it also defines a set state function that changes the state of the device.  The GPIOInterface object implements the read and write functions that get and set a GPIO pin.
