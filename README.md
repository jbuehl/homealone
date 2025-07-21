# Homealone home automation platform

### Overview

Home automation refers to the use of various devices and systems within a home that are interconnected and can be controlled remotely. This project provides a software platform and application framework for controlling and monitoring devices in a home. It allows any device in the home that can be electronically controlled or sensed to be connected to a system, enabling remote access and management. Examples of such devices include lights, sprinklers, temperature sensors, and door sensors.

This project focuses on the software, defining how devices can be connected and controlled. It establishes a template for abstracting hardware interfaces to a common API, allowing the software running on a server to connect to devices using various hardware interfaces like GPIO pins, serial ports, or network adapters. An object model is used to further abstract device functions, and network protocols are defined to enable the server to advertise itself on the network and provide access to connected devices. Other servers can then implement interfaces, such as a web server, for human interaction.

The typical open source home automation project, such as Home Assistant, OpenHAB, or Domoticz, implements a system where devices are connected to a central hub or gateway that allows for control via a smartphone, tablet, or computer using a customizable user interface that is provided.  The package is installed on hub device and is then configured to access the devices in the home via supported interfaces.  There is no software development required on the part of the user.

HomeAlone is quite different.  It is fundamentally a project that is intended for use by hardware and software developers and not a turnkey project that is usable by non-developers.  It provides a software platform that can be used to develop custom hardware devices and integrate them into a system.  It provides an application framework that can be used to develop user interfaces, but it does not provide a specific user interface.

### Design goals

The design of the project targets the following goals.

-  Distributed - Functions are distributed across the system.
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

- [Core Object Model](docs/README.model.md)
- [Resource naming and attributes](docs/README.naming.md)
- [Remote resources](docs/README.remote.md)
- [Scheduler](docs/README.scheduler.md)
- [Interfaces and Resources](docs/README.resources.md)
- [Applications](docs/README.apps.md)
- [Services](docs/README.services.md)
- [Specific hardware support](docs/README.resources.md)
