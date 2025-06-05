# Homealone service fault indication

## Background

Homealone provides the infrastructure to support a dashboard that shows the state of Homealone Services and to send notifications if the state changes.  The Remote Resource interface currently allows a Client to discover the existence of all Homealone Services in the system, and is aware when a Service that was previously advertising itself has stopped doing so.  This results in a change in the state of the Service that is presented on a dashboard UI, and it may also trigger a notification.

There are occasionally situations where a Service is running and broadcasting messages to the system, but something has occurred internally that causes it to stop performing some critical function.  This may be caused by a hardware issue or a bug in the code.  There is usually information in the system log that shows what has happened, but there isn't a mechanism to alert someone that there is a problem.

## Requirements

The service fault indication is a proposed enhancement that enables a Service that is still active to be able to report conditions that may be degrading the performance of the Service.

Three states are defined:
- Up - the Service is active
- Fault - the Service is active but there is an anomaly that potentially degrades the functionality
- Down - the Service is not active

Conditions within a service that cause the "Fault" state:
- a sensor stops reporting state
- unexpected thread termination
- external server not reachable
- other (TBD)

When a Service goes into the "Fault" state, the state may be displayed on a user interface and a notification may be triggered.

## Implementation

### Remote Interface

The service resource in the Homealone Remote Interface messages contains attributes of the Service.  

Add an attribute that indicates when there has been a fault detected to the service resource.  Minimally, this may be as simple as a boolean that indicates there is a fault.  It may eventually become a more complicated structure that conveys additional information, but that is out of scope of the initial requirements.

### Sensor stops reporting state

The state of a Homealone Sensor may be any numeric or string value.  The value **None** is reserved to indicate the lack of a valid state.  Currently the StateCache object is implemented within every Application.  By polling or waiting for events it is aware of the current state of every Sensor defined by the application.  

Add an attribute to the StateCache object that indicates if one or more Sensors has a **None** state.  This attribute is visible to the RemoteService object that sends the service resource attributes to the Remote interface.

### Unexpected thread termination

Applications may start one or more threads.  Threads may be implemented in an Interface object used by its Sensors or they may be implemented by application specific objects.  The current convention is for any object that implements threads to provide a start() function that is called when the Application is started.  Threads are implemented using the StartThread() function in the rutifu package which wraps every thread in a try-except block that writes a stack trace to the system log if there is an uncaught exception that terminates the thread.

Add an optional argument to the start() function of Homealone objects, and to the StartThread() function that defines a callback routine to be invoked if an uncaught exception terminates the thread.  This function sets the fault attribute of the service resource.

### External server not reachable

Communication with external servers, such as the Metrics server or weather server, periodically experience issues.  Sometimes the issue is temporary and retry logic deals with the problem.  The objects that implement these protocols are implemented with start() functions.

Add an optional argument to the start() function of external server objects that defines a callback routine to be invoked if communication with the server isn't possible.  This function sets the fault attribute of the service resource.

### Remote Service

The RemoteService object implements the server side of the Homealone Remote Interface. It is responsible for sending messages that contain the state and service resources.

When creating a state resource, if the attribute in the StateCache is set, set the fault attribute of the service resource.  Add a function to the RemoteService object that sets the fault attribute in the service resource.  It can be invoked when a fault is detected in the application.

### Remote Client

The RemoteClient object creates a ProxyService object to represent each Remote Service it is aware of.  A ProxyService is a Sensor with two state values: "Up" and "Down".

Add a "Fault" state that is set when the fault attribute is set in the service resource.

### Notification

The Homealone notification service implements a RemoteClient that listens for all Remote Services on the network.  Based on configurable rules for certain state changes on certain sensors it can send notifications.  Currently it sends a notification if the state of a remote service changes from "Up" to "Down".

Add a rule to send a notification if the state of a Remote Service changes from "Up" to "Fault".
