# Homealone home automation applications

### App directory structure

One or more applications run on a server.  Each application and its associated files are contained within a directory.  Installing an application on a server consists of copying the directory structure of the app into a root directory.  The choice of the root directory is arbitrary and it may contain more than one app.  Uninstalling an app consists of removing the app directory and its contents.

An application may be run manually or it may be run at system startup as a systemd service or other method.

An optional configuration file conf.py may be included to set application parameters. This file should consist of value assignments to basic Python type variables that are referenced in the application.  An optional site configuration file may be defined in /etc/homealone/site/ to set parameters used by multiple applications on the server such as localization.  Authorization credentials for external services may also be stored in /etc/homealone/site/keys/.

The optional debugConf.py file allows control of debugging messages to the system log file.

If there are interface definitions or resource definitions or other modules that are specific to the application they should be included in the application directory.

An application may maintain persistent state for one or more resources.  This is implemented as a JSON file in the states/ subdirectory.

If data logging is enabled, the logs are maintained in the data/ subdirectory.

```
root directory/
	app1/
        app1.py - the application
        conf.py - app specific configuration parameters (optional)
        debugConf.py - debug flags (optional)
        interfaces/ - app specific interfaces (optional)
        resources/ - app specific resources (optional)
        states/ - app specific states (optional)
            app1.json
        data/ - data logs (optional)
            yyyymmd1.json
            yyyymmd2.json
    .
    .
    .
	appN/
        appN.py
        conf.py
        interfaces/
        resources/
        states/
        data/

    /etc/
        homealone/
            site/
                siteConf.py - configuration parameters used by all apps
                keys/ - credentials for external services

```

#### Data logging archive directory structure

Data logs may be copied to a backup server from each application server.

```
archive directory/
	app1/
        yyyymmd1.json
        yyyymmd2.json
    .
    .
    .
	appN/
        yyyymmd1.json
        yyyymmd2.json
```

### Sample application

The following sample application illustrates how a service may be implemented.  A temperature sensor and a sprinkler valve are configured as described in the earlier example.

First, the I<sup>2</sup>C and GPIO Interface objects are defined.  The address of the temperature sensor is 0x4b on the I<sup>2</sup>C bus and the sprinkler valve is connected to GPIO pin 17 which is set to output mode.  Then the Sensor object for the temperature sensor and the Control object for the sprinkler valve are defined.  Next, a Task is defined that will run the sprinkler every day at 6PM (18:00) for 10 minutes (600 seconds) every day during the months May through October.

A Python threading.Event object is used to implement real time updates of the temperature sensor state.  

Finally, the task is added to a Schedule object and the Sensor and Control are added to a Collection object that will be exported by the REST server.  When the Schedule is started it will turn on the sprinkler every day as programmed.  The REST server will export the representations of the two resources and their current states.  It will also allow another server to control the sprinkler valve remotely. It must be started last because it will block the application so it will not exit.

```
import threading
from homealone import *
from homealone.interfaces.I2CInterface import *
from homealone.interfaces.gpioInterface import *
from homealone.rest.restServer import *

if __name__ == "__main__":
	stateChangeEvent = threading.Event()

	# Interfaces
	i2cInterface = I2CInterface("i2cInterface")
	gpioInterface = GPIOInterface("gpioInterface", output=[17])

	# Temp sensor and sprinkler control
	gardenTemp = Sensor("gardenTemp", i2cInterface, 0x4b, event=stateChangeEvent, label="Garden temp")
	gardenSprinkler = Control("gardenSprinkler", gpioInterface, 17, label="Garden sprinkler")

	# Sprinkler task
	gardenSprinklerTask = Task("gardenSprinklerTask", SchedTime(hour=18, minute=00, month=[May, Jun, Jul, Aug, Sep, Oct]),
	                    			sequence=Sequence("gardenSequence",
										cycleList=[Cycle(control=gardenSprinkler, duration=600, startState=1)]),
									controlState=1,
									label="Garden sprinkler task")

	# Resources and schedule
	schedule = Schedule("schedule", tasks=[gardenSprinklerTask])
	restServer = RestServer("garden", Collection("resources", event=stateChangeEvent,
				resources=[gardenTemp, gardenSprinkler, gardenSprinklerTask]), label="Garden")

	# Start things up
	gpioInterface.start()
	schedule.start()
	restServer.start()
```
### Application framework

In order to simplify the implementation of applications, Homealone provides a framework that eliminates a lot of the housekeeping and redundancy that sometimes is needed.  Use of the application framework is optional, however it usually reduces the amount of code required to implement a Homealone app.

The application framework provides the following features:

- Eliminate the need to specify identifiers multiple times when creating resources
- Automatically create and maintain a collection of local resources
- Create and maintain other objects if needed
	- Proxy for remote resources
	- Data logger
	- Persistent state file
	- System resources
- Streamline the specification of UI related resource attributes
- Call the start() function for all objects that require it

#### Application object

A single Application object is created for a Homealone application.

    - name
    - globals
    - publish
    - remote
    - logger
    - system
    - state
    - interface(interface, event, start)
    - resource(resource, publish, event, start)
    - remoteResource(resource)
    - task(task, publish, event)
    - style(style, resources)
    - label(label, resources)
    - group(group, resources)
    - run()

#### Sample application using the app framework

The same application in the previous example is implemented here using the Homealone app framework.

The Application object automatically creates a REST server and publishes all the resources.  It also creates the schedule that runs the task.  The REST server, schedule, and GPIO interface are all started when the run() function is called.  An event object is automatically created which can be triggered by the temp sensor.

When the Application object is created, it has a dictionary passed to it.  In this case it is the one containing the global variables for the program.  When an interface, resource, or task is created an entry is added to the dictionary with the name of the created object and a reference to that object.  This allows the object to be referenced later in the program.  In the example above, without the app framework, the name "gardenSprinkler" must be entered into the code a total of 4 times - twice when the object is defined, once when it is referenced in the task definition, and once when it is added to the collection which is published.  Using the app framework the name only has to be entered 2 times - once as the name in the object definition and once as a reference by the task.  Other object such as "gardenTemp" and "gardenSprinklerTask" only need to entered once when they are created.

Because the resource names in this example conform to the camel case convention, the app framework can automatically create human readable labels for them without having to specify the label for each resource.

```
from homealone import *
from homealone.interfaces.I2CInterface import *
from homealone.interfaces.gpioInterface import *

if __name__ == "__main__":
	app = Application("garden", globals())

	# Interfaces
	app.interface(I2CInterface("i2cInterface"))
	app.interface(GPIOInterface("gpioInterface", output=[17]), start=True)

	# Temp sensor and sprinkler control
	app.resource(Sensor("gardenTemp", i2cInterface, 0x4b), event=True)
	app.resource(Control("gardenSprinkler", gpioInterface, 17))

	# Sprinkler task
	app.task(Task("gardenSprinklerTask", SchedTime(hour=18, minute=00, month=[May, Jun, Jul, Aug, Sep, Oct]),
	                    		sequence=Sequence("gardenSequence",
									cycleList=[Cycle(control=gardenSprinkler, duration=600, startState=1)]),
								controlState=1))

	# UI
	app.label()

	# Start things up
	app.run()
```
