# Homealone home automation platform

### Overview

Home automation involves connecting and remotely controlling various devices in a home. This project offers a software platform and framework for managing home devices. It allows any electronically controllable or sensor-equipped device to be linked to a system, enabling remote control and monitoring. Examples of such devices include lights, sprinklers, temperature sensors, and door sensors.

The project focuses on software, defining how devices can be connected and controlled. It establishes a template for abstracting hardware interfaces to a common API, enabling the software on a server to connect to devices using various hardware interfaces like GPIO pins, serial ports, or network adapters. An object model further abstracts device functions, and network protocols are defined to allow the server to advertise itself on the network and provide access to connected devices. Other servers can implement interfaces, like a web server, for human interaction.

Unlike typical open-source home automation projects, such as Home Assistant, OpenHAB, or Domoticz, which offer a ready-to-use system, HomeAlone is designed for hardware and software developers. It provides a platform for developing custom hardware devices and integrating them into a system. While it offers an application framework for developing user interfaces, it does not provide a specific user interface out of the box.

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
