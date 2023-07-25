# Homealone resource naming and attributes

### Resource naming
Every resource has a name.  A name is an identifier that consists of one or more upper or lower case letters, numerals, and underscores.  They are case sensitive.

The namespace is flat.  Resources that are published to the system via the Remote interface must have system-wide unique names.  There is no mechanism for implementing a hierarchy of names, other than naming conventions that may be adopted by specific applications.

### Publishing and discovery
A service may publish its resources via the Remote interface for access by clients in the system.  The availability of resources implemented by a service is advertised by periodic messages that are broadcast to a multicast address that a client may listen on in order to discover resources.

Resolution of a resource name by a client is inherent in the Remote interface.  The message that advertises resources by a service includes the IP address and port that the client can use to access the resources published by the service.

There is no centralized component involved in publishing and discovery.  Because each service operates independently there is the possibility of duplication of resource names in the system.  Duplicate resource names cannot exist within the resources published by a given service, but two services could each have a resource with the same name.  Detection and handling of duplicate names is done by the client (not implemented).

### Resource attributes
Every object derived from the Sensor class contains the following attributes.

#### state
Every Sensor has an associated state.  A Sensor state is a single integer or floating point number, or a string.  True, False, and None are not valid states. A state value of None indicates an undefined state. A state may not be a list, tuple, dict, or other object.

If a hardware device has multiple attributes or controls, it should be represented as multiple Sensor or Control objects.  The state of a Sensor is obtained by an explicit call.  A Sensor may implement an event that is set when its state changes that can be used for notification.

#### type
This attribute indicates the behavior of the device that is represented by the resource, and how its states should be interpreted and displayed in a UI.  For example, a door sensor and a light switch control both may have valid states of 0 and 1, but the interpretation of the states of the light switch would be "off" and "on", and the door would be "closed" and "open".

#### label
Label is an optional attribute that defines a human readable name associated with a resource that is used in a UI.  In addition to letters and numbers, labels may contain spaces and special characters.  If a label is not defined for a resource a UI may assign one, or it may override a defined label.

#### group
A resource may be optionally associated with one or more arbitrary groups. Groups may be used by a UI for display purposes. Groups are defined on an ad hoc basis and are not managed in any way by the system.

#### location
Location is an optional attribute that contains a tuple that represents the physical location of a resource for use by a UI.
