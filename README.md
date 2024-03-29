# Homealone home automation platform

### Overview

This project defines a platform and application framework that enables sensing and control of various devices in a home.

Any device in the home whose state can be sensed or controlled electronically can be connected to a system that can manage that device and allow remote access. Examples of devices include such things as light fixtures, sprinkler valves, temperature sensors, door sensors, etc.  This project does not define specific hardware for these devices, but rather defines the software that allows any device to be interfaced to the system.

At the lowest level, a template is defined that allows a hardware interface to be abstracted to a common API.  The server on which the software is running may physically connect to the device using any hardware interface such as GPIO pins, a serial port, or a network adapter.  An object model is defined that is implemented with an application running on that server that further abstracts the specific functions of the device.  Network protocols are defined that enable the server to advertise itself on the network and allow access to the devices that it is connected to. Other servers may implement human interfaces such as a web server.

### Design goals

The design of the project targets the following goals.

-  Distributed - Functions are distributed across devices in the system.
-  Devices are autonomous - Whenever possible, devices can run independently of the system.  There is no requirement for a centralized controller.
-  Devices are dynamically discoverable - Devices can be added or removed from the system without requiring changes to a system configuration.
-  Connected to the local home network - Devices are connected to the system via the local wired or wireless home network.
-  Not dependent on the internet - The system may be accessed remotely via the internet and use cloud servers for certain functions, however internet connectivity is not required for routine functions.
-  Reasonably secure - The system does not explicitly implement any security features.  It relies on the security of the local network.
-  Not dependent on proprietary systems, interfaces, or devices - Proprietary interfaces and devices may be accessed, but there is no requirement for any particular manufacturer's products.
-  Open source - All code is open source.

### Limitations

-  Does not provide applications - Examples are provided, however they must be tailored for specific installations.
-  Does not provide a user interface - An example web based user interface is provided that may be extended.
-  Operating system specific - Currently only runs on Raspberry Pi OS, however there is no inherent reason it could not be made OS independent.

### Documentation

More detailed documentation and examples may be found in these files.

- [Object Model](docs/README.model.md)
- [Resource naming and attributes](docs/README.naming.md)
- [Remote resources](docs/README.remote.md)
- [Scheduler](docs/README.scheduler.md)
- [Applications](docs/README.apps.md)
- [Services](docs/README.services.md)
- [Specific hardware support](docs/README.resources.md)
