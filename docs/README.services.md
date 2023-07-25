# Homealone home automation services

### Message logging
Applications may log messages as a result of unexpected conditions or events.  Debugging messages may also be logged.  Messages are written to the local system log on each server or may optionally be directed to stdout.  Homealone modules use the log() and debug() functions that are implemented in the **rutifu** package.  Homealone applications should use these as well.

### Data logging
Data logging is used to record the state of sensors defined in an application over time.  Any time the state of a sensor changes, an entry may be posted with the current timestamp and a list of sensor names and their states.  The application may choose whether it includes just the sensor(s) whose state has changed, or all sensors.  Data logs are written to a local file on the application server.  There is one file maintained per day that is named YYYYMMDD.json.  Log files are periodically copied to a backup server for archival purposes and purged from the local filesystem.

### Metrics
Metrics may be captured by recording the states of all sensors with a numeric state.  Any time the state of a sensor changes, an entry is posted to a metrics server with the current timestamp, the sensor name, and its state.  If the metrics server is unreachable then metrics are not captured, however they may be recovered at a later time from data logs.

### Notification
The notification service may be used to send messages to users via some external service such as SMS.  A notification may be triggered by an explicit request from an application (deprecated), or it may be triggered by a state change of a particular resource.

### Naming
The naming service implements the ability to define resource names that are aliases of actual resources (not implemented).
