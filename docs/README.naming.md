# Homealone resource naming and attributes

### Resource naming
Every Resource has a name.  A name is an identifier that consists of one or more upper or lower case letters, numerals, and underscores.  They are case sensitive.

The namespace is flat.  Resources that are published to the system via the Remote interface must have system-wide unique names.  There is no mechanism for implementing a hierarchy of names, other than naming conventions that may be adopted by specific applications.

### Publishing and discovery
A service may publish its Resources that derive from Sensors via the Remote interface for access by clients in the system.  The availability of Resources implemented by a service is advertised by periodic messages that are broadcast to a multicast address that a client may listen on in order to discover Resources.

Resolution of a Resource name by a client is inherent in the Remote interface.  The message that advertises Resources by a service includes the IP address and port that the client can use to access the resources published by the service.

There is no centralized component involved in publishing and discovery.  Because each service operates independently there is the possibility of duplication of Resource names in the system.  Duplicate Resource names cannot exist within the Resources published by a given service, but two services could each have a Resource with the same name.  Detection and handling of duplicate names may possibly be done by a client, but this is not implemented.

### Resource attributes
Every object derived from the Sensor class contains the following attributes.

#### state
Every Sensor has an associated state.  A Sensor state is a single integer, floating point number, or string.  True, False, and None are not valid states. A state value of None indicates an undefined state. A state may not be a list, tuple, dict, or other object. A state value may be an arbitrary integer or floating point number, such as a temperature or voltage.  State values may also be numbers or strings that are within a set of enumerated values.  A common example is a control for a light switch that can have a state of 0 (off) or 1 (on).

While most Sensor attributes are normal Python object attributes that are represented as items in a dictionary and are static, the `state` attribute may change over time.  It is accessed via the functions `getState()` and `setState()` that communicate with the hardware via the Interface that is associated with the Sensor.

If a hardware device has multiple attributes or controls, it should be represented as multiple Sensor or Control objects.  A Sensor may implement an event that is set when its state changes that can be used for notification.

#### interface, addr
The link between a Sensor object and the actual hardware is defined by an Interface object which implements the  specific code to access the hardware.  An interface may support multiple sensors that are identified by `addr`.  An `addr` attribute may be any python data type.

#### poll, event
Depending on the characteristics of a hardware device, it may be able to generate an interrupt when its state changes, otherwise devices must be periodically polled to determine their current state.  If an `event` attribute is specified for a Sensor, it is assumed that the `notify()` function will be called whenever the state of the device changes.  If a device must be polled, then the value of the `poll` attribute is used as the polling interval in seconds.

#### factor, offset, resolution
A sensor that has a numeric state may need to routinely transform the value of the state that it reads from the interface.  The optional attributes `factor`, `offset`, and `resolution` enable this.

#### states, setStates
A sensor whose state is contained in a set of enumerated values must define the set of valid values and their symbolic names.  This is done in the `states` attribute which is a dictionary that contains the set of state values as keys, and the symbolic names as values.  A Control may have one or more states that are not directly settable.  In this case, the attribute `setStates` defines the set of states that may be set on the Control.

#### type
The `type` attribute indicates the behavior of the device that is represented by the resource, and how its states should be interpreted and displayed in a UI.  For example, a light switch control and a door sensor both may have valid states of 0 and 1, but the interpretation of the states of the light switch would be "off" and "on", and the door would be "closed" and "open".  In the case of a state value that is numeric, the `type` attribute defines the units that the state value represents, such as temperature, power, wind velocity, air pressure, etc.

#### label
Label is an optional attribute that defines a human readable name associated with a Resource that is used in a UI.  In addition to letters and numbers, labels may contain spaces and special characters.  If a label is not defined for a Resource a UI may assign one, or it may override a defined label.

#### group
A Resource may be optionally associated with one or more arbitrary groups. Groups may be used by a UI for display purposes. Groups are defined on an ad hoc basis and are not managed in any way by the system.

#### location
Location is an optional attribute that contains a tuple that represents the physical location of a resource for use by a UI.
