# Homealone home automation platform remote resource interface

### Overview
Homealone applications can expose their Homealone resources via an interface that is implemented in
rest/remoteServer.py. This allows a client application to access
Homealone objects on other servers.

### Requirements
* Enable distributability of Homealone resource management
* Use a client-server model
* Implement autodiscovery of Homealone services
* Implement notification of resource configuration changes
* Implement notification of resource state changes
* Servers are stateless regarding the interface
* Does not implement a security model

### Terminology
* server - hardware that is running one or more Homealone applications
* hostname - the unique name for a server on the local network
* Homealone service - the implementation of the Homealone remote interface on a server
* Homealone resource - a Homealone object implemented within a Homealone application
* REST resource - an identifier in a the HTTP path that may describe a Homealone resource

### Implementation
The interface consists of two parts:  A periodic UDP message that is periodically broadcast by the server, and an HTTP server that supports a REST interface over TCP.  The UDP message performs the functions of advertising the availability of the server on the network, notifying clients of changes in the configuration or states of the server's Homealone resources, and letting clients know that the server is active.  The REST server allows clients to query details about Homealone resource configuration and states, and to direct a server to change the states of Control resources.

#### Service advertising
The Homealone remote server uses periodic messages sent to a multicast address to advertise itself on the local network.  
The message contains the service name, and port that carries the corresponding REST interface. If multiple Homealone services are running on the same host they must use different ports.

The message contains a service REST resource and optionally a resources REST resource and states REST resource.
If the message only contains a service REST resource, the message serves to notify clients that the server is
still active and there haven't been any resource or state changes since the last message.  The timestamps will be the
same as the previous message and the sequence number will contain the sequence number of the previous message incremented by 1.

A client will create local resources that serve as proxies for the resources on a server.  The states of the resources
are cached in the client and updated when the states of the server resources change.  When a client receives a message
for a service that it hasn't previously seen, it creates a set of proxy resources for the service.

### Notifications
If the state of a resource changes on a server, the next message will include a states REST resource that contains
the current states of all resources on the server and an updated resource timestamp.  The client should update its state cache
for that service with the new values.

If the configuration of the Homealone resources on a service changes, the next message will include both a resources REST resource,
a states REST resource, and an updated state timestamp.  The client will update the proxied Homealone resources for
that service, and update their states.

If a client receives a message from an active server that contains a changed timestamp but no resources or states REST resources,
it will request either the resources or the states from the service and update its cache.

```
{"service": {"name": <service name>},
 "states": {<resource 0 name>: <resource 0 state>,
            <resource 1 name>: <resource 1 state>,
            ...,
            <resource N name>: <resource N state>}}
```

### REST interface
The REST interface follows the conventions for HTTP verb usage and path construction.

#### Verbs
The HTTP following verbs are implemented by the remote server:
- GET - return the value of the specified Homealone resource
- PUT - set the specified Homealone resource attribute to the specified value
- POST - create a new Homealone resource (not implemented)
- DELETE - delete the specified Homealone resource (not implemented)

#### Resource paths
REST resource paths are defined as follows:
```
/
	service/
		service attributes
	resources/
		resource 0/
			resource 0 attributes
		resource 1/
			resource 1 attributes
		...
		resource n/
			resource n attributes
	states/
		resource 0 state/
		resource 1 state/
		...
		resource n state/
```
The /service/ resource contains attributes of the Homealone service.
```
"service":  {"name": <service name>,
			 "hostname": <host name>,
			 "port": <port>,
			 "label": <service display name>,
			 "stateTimestamp": <last update time of the resource states>,
			 "resourceTimestamp": <last update time of the resources and attributes>,
			 "seq": <sequence number of the message>}
```
The /resources/ REST resource contains a JSON representation of the Homealone resource that
the service is exposing.  It may be a single Homealone Resource but typically this is a
Homealone Collection resource that contains a list of Homealone resource names.
```
"resources":{"class": "Collection",
			 "attrs": {"name": <resource collection name>,
			           "type": "collection",
			           "resources": [<resource 0 name>,
			                         <resource 1 name>,
			                         ...,
			                         <resource N name>]}}
```
The /resources/ REST resource may optionally contain the expanded JSON representations of all the
resources rather than just a list of Homealone resource names.
```
"resources":{"class": "Collection",
			 "attrs": {"name": <resource collection name>,
			           "type": "collection",
			           "resources": [<resource 0>,
			                         <resource 1>,
			                         ...,
			                         <resource N>]}}
```

The /states/ resource contains a list of all the names and current states of the Homealone Sensor
resources in the service.
```
{"states": {<resource 0 name>: <resource 0 state>,
            <resource 1 name>: <resource 1 state>,
            ...,
            <resource N name>: <resource N state>}}
```

#### Resource attributes
If an HTTP request is sent to the REST port on a host that is running the remote server the data that is
returned from a GET is the JSON representation of the specified Homealone resource.
Every Homealone Sensor resource has an implied attribute "state" that returns the current state of the sensor. It
is not included in the list of attributes returned for the resource, however it may be queried
in the same way as any other resource attribute.
If an attribute references another resource, the value contains only the name of the referenced resource,
not the JSON representation of that resource.  If an attribute references a class that is not a resource,
the JSON representation of the object is the value of the attribute.
```
{"class": <class name>,
 "attrs": {<attr 0>: <value 0>,
           <attr 1>: <value 1>,
           ...,
           <attr N>: <value N>}}
```

### Examples
Examples 1-6 show messages that are used for discovery of the configuration of resources.  Examples 7-8 show
messages that get the current state of resources.  Example 9 shows changing the state of a resource.  Example 10
shows the notification of state changes of resources.

1. Return the list of resources on the host sprinklers.local.

	   Request:     GET sprinklers.local:7378

	   Response:    ["service",
                     "resources",
                     "states"]

2. Return the attributes of the Homealone service on the host sprinklers.local.

	   Request:     GET sprinklers.local:7378/service

	   Response:    {"name": "sprinklerService",
					 "label": "Sprinklers",
					 "stateTimestamp": 1595529166,
					 "resourceTimestamp": 1595529166,
					 "seq": 666}

3. Return the list of Homealone resources on the host sprinklers.local.

        Request:     GET sprinklers.local:7378/resources

        Response:    {"class": "Collection",
                      "attrs": {"name": "resources",
                                "type": "collection",
                                "resources": ["gardenTemp",
                                              "gardenSprinkler"]}}

4. Return the list of Homealone resources on the host sprinklers.local containing the expanded
	resource representations.

     Request:     GET sprinklers.local:7378/resources?expand=true

     Response:    {"class": "Collection",
                   "attrs": {"name": "resources",
                             "type": "collection",
                             "resources": [{"class": "Sensor",
					                       "attrs": {"name": "gardenTemp",
					                                 "interface": "tempInterface"
					                                 "addr": 1,
					                                 "location": null,
					                                 "type": "tempC",
					                                 "group": "Sprinklers",
					                                 "label": "Garden temperature"}},
											 {"class": "Control",
						                     "attrs": {"name": "gardenSprinkler",
						                               "interface": "sprinklerInterface"
						                               "addr": 17,
						                               "location": null,
						                               "type": "sprinkler",
						                               "group": "Sprinklers",
						                               "label": "Garden sprinkler"}}]}}

5. Return the attributes for the resource "gardenSprinkler".  Note that the attribute
       "state" is not included.

       Request:     GET sprinklers.local:7378/resources/gardenSprinkler

	   Response:    {"class": "Control",
                     "attrs": {"name": "gardenSprinkler",
                               "interface": "sprinklerInterface"
                               "addr": 17,
                               "location": null,
                               "type": "sprinkler",
                               "group": "Sprinklers",
                               "label": "Garden sprinkler"}}

6. Return the value of the attribute "addr" of the resource "gardenSprinkler".

	   Request:     GET sprinklers.local:7378/resources/gardenSprinkler/addr

	   Response:    {"addr": 17}

7. Return the current state of the resource "gardenSprinkler".

       Request:     GET sprinklers.local:7378/resources/gardenSprinkler/state

       Response:    {"state": 0}

8. Return the current states of all resources on the host sprinklers.local.

       Request:     GET sprinklers.local:7378/states

       Response:    {"states": {"gardenTemp": 28.0,
                                "gardenSprinkler": 0}}

9. Set the state of the resource "gardenSprinkler" to 1.  The request body contains
	   the requested state.  The response body returns the resulting state.

       Request:     PUT sprinklers.local:7378/resources/gardenSprinkler/state
                    {"state": 1}

       Response:    {"state": 1}

10. Unsolicited message that is broadcast periodically and whenever one of the states changes
	   that shows the current states of all resources in the service sprinklerService.

       Message:     
                    {"service": {"name": "sprinklerService",
                                 "label": "Sprinklers",
								 "stateTimestamp": 1595529456,
								 "resourceTimestamp": 1595529456,
                                 "seq": 667},
                     "states": {"gardenTemp": 28.0,
                                "gardenSprinkler": 0}}
