# Classes related to schedules

from homealone.core import *
from homealone.env import *
from homealone.resources.extraResources import *
from .sunriseset import *

# return today's and tomorrow's dates with the current time
def todaysDate():
    today = datetime.datetime.now().replace(tzinfo=tz.tzlocal())
    tomorrow = today + datetime.timedelta(days=1)
    return (today, tomorrow)

# A Task describes the process of setting a Control to a specified state, waiting a specified length of time,
# and setting the Control to another state.  This may be preceded by an optional delay.
# If the duration is None, then the end state is not set and the Control is left in the start state.
class Task(Object):
    def __init__(self, control=None, duration=None, startState=1, endState=0, delay=0, name=None):
        Object.__init__(self)
        self.control = control
        self.duration = duration
        self.startState = normalState(startState)
        self.endState = normalState(endState)
        self.delay = delay
        self.running = False

    # Run the Task
    def run(self):
        self.running = True
        if self.delay > 0:                              # delay if specified
            debug('debugJob', self.control.name, "delaying", self.delay, "seconds")
            self.wait(self.delay)
            if not self.running:
                return
        if self.duration == None:                       # just set the state
            self.control.setState(self.startState)
        else:
            if isinstance(self.duration, int):          # duration is specified directly
                duration = self.duration
            elif isinstance(self.duration, Sensor):     # duration is the state of a sensor
                duration = self.duration.getState()
            if duration > 0:
                debug('debugJob', self.control.name, "started for", duration, "seconds")
                self.control.setState(self.startState)
                self.wait(duration)
                self.control.setState(self.endState)
        debug('debugJob', self.control.name, "finished")
        self.running = False

    # wait the specified number of seconds
    # break immediately if the job is stopped
    def wait(self, duration):
        for seconds in range(0, duration):
            if not self.running:
                break
            time.sleep(1)

    # attributes to include in the serialized object
    def dict(self, expand=False):
        return {"control": self.control.name,
                "duration": self.duration.getState() if isinstance(self.duration, Sensor) else self.duration,
                "startState": self.startState,
                "endState": self.endState,
                "delay": self.delay}

    # string representation of the object for display in a UI
    def __repr__(self):
        return "control: "+self.control.__str__()+"\n"+ \
                "duration: "+self.duration.__str__()+"\n"+ \
                "startState: "+self.startState.__str__()+"\n"+ \
                "endState: "+self.endState.__str__()+"\n"+ \
                "delay: "+self.delay.__str__()

# a Job is a Control that consists of a list of Tasks or Jobs that are run in the specified order

jobStop = 0
jobStart = 1
jobStopped = 0
jobRunning = 1

class Job(Control):
    def __init__(self, name, taskList=[], **kwargs):
        Control.__init__(self, name, **kwargs)
        self.type = "job"
        self.taskList = listize(taskList)
        self.states = {0:"Stopped", 1:"Running"}
        self.setStates = {0:"Stop", 1:"Run"}
        self.running = False

    def getState(self, missing=None):
        if not self.interface:
            return normalState(self.running)
        else:
            return Control.getState(self)

    def setState(self, state, wait=False):
        if not self.interface:
            debug('debugJob', self.name, "setState ", state, wait)
            if state and not(self.running):
                self.runTasks(wait)
            elif (not state) and self.running:
                self.stopTasks()
            return True
        else:
            return Control.setState(self, state)

    # Run the Tasks in the list
    def runTasks(self, wait=False):
        debug('debugJob', self.name, "runTasks", wait)
        if wait:    # Run it synchronously
            self.taskThread()
        else:       # Run it asynchronously in a separate thread
            startThread("taskThread", self.taskThread)

    # thread that runs the tasks
    def taskThread(self):
        debug('debugJob', self.name, "taskThread started")
        self.running = True
        for task in self.taskList:              # may be a list of tasks and/or jobs
            if not self.running:
                break
            if isinstance(task, Task):          # run the task
                task.run()
            elif isinstance(task, Job):     # run the job
                task.setState(1, wait=True)
        self.running = False
        # self.notify()
        debug('debugJob', self.name, "taskThread finished")

    # Stop all Tasks in the list
    def stopTasks(self):
        self.running = False
        for task in self.taskList:
            task.control.setState(task.endState)
        # self.notify()
        debug('debugJob', self.name, "stopped")

    # attributes to include in the serialized object
    def dict(self, expand=False):
        attrs = Control.dict(self)
        attrs.update({"taskList": [(task.dump() if isinstance(task, Task) else task.name) for task in self.taskList]})
        return attrs

    # string representation of the object for display in a UI
    def __repr__(self):
        msg = ""
        for task in self.taskList:
            if isinstance(task, str):
                msg += task+"\n"
            else:
                msg += task.__repr__()+"\n"
        return msg.rstrip("\n")

# the Scheduler manages a list of Schedules and runs them at the times specified
class Scheduler(Collection):
    def __init__(self, name, schedules=[]):
        Collection.__init__(self, name, resources=schedules)

    def start(self, notify=None):
        self.initControls()
        startThread("scheduleThread", self.scheduleThread, notify=notify)

    # initialize control states in certain cases
    def initControls(self):
        (now, tomorrow) = todaysDate()
        for scheduleName in list(self.keys()):
            schedule = self[scheduleName]
            # schedule must have an end time
            if schedule.endTime:
                # schedule must recur daily at a specific time
                if (schedule.schedTime.year == []) and \
                   (schedule.schedTime.month == []) and \
                   (schedule.schedTime.day == []) and \
                   (schedule.schedTime.weekday == []) and \
                   (schedule.schedTime.event == ""):
                   # schedule must start and end within the same day
                   if schedule.schedTime.hour < schedule.endTime.hour:
                       # set the expected state of the control at the present time
                       # assume it runs once a day, ignore minutes
                       if (now.hour >= schedule.schedTime.hour[0]) and (now.hour < schedule.endTime.hour[0]):
                           self.setControlState(schedule, schedule.controlState)
                       else:
                           self.setControlState(schedule, schedule.endState)

    # Scheduler thread
    def scheduleThread(self):
        debug('debugScheduler', self.name, "started")
        while True:
            # wake up every minute on the 00 second
            (now, tomorrow) = todaysDate()
            sleepTime = 60 - now.second
            debug('debugScheduler', self.name, "sleeping for", sleepTime, "seconds")
            time.sleep(sleepTime)
            (now, tomorrow) = todaysDate()
            debug('debugScheduler', self.name, "waking up",
                    now.year, now.month, now.day, now.hour, now.minute, now.weekday())
            # run through the schedule and check if any tasks should be run
            # need to handle cases where the schedule could be modified while this is running - FIXME
            for scheduleName in list(self.keys()):
                schedule = self[scheduleName]
                if schedule.getState():
                    if self.shouldRun(scheduleName, schedule.schedTime, now):
                        self.setControlState(schedule, schedule.controlState)
                    if schedule.endTime:
                        if self.shouldRun(scheduleName, schedule.endTime, now):
                            self.setControlState(schedule, schedule.endState)
                else:
                    debug('debugScheduler', self.name, "disabled", scheduleName)

    def shouldRun(self, scheduleName, schedTime, now):
        # the schedule should be run if the current date/time matches all specified fields in the SchedTime
        st = copy.copy(schedTime)
        st.eventTime()              # determine the exact time if event specified
        debug('debugScheduler', self.name, "checking", scheduleName,
                st.year, st.month, st.day,
                st.hour, st.minute, st.weekday,
                st.event)
        if (st.year == []) or (now.year in st.year):
            if (st.month == []) or (now.month in st.month):
                if (st.day == []) or (now.day in st.day):
                    if (st.hour == []) or (now.hour in st.hour):
                        if (st.minute == []) or (now.minute in st.minute):
                            if (st.weekday == []) or (now.weekday() in st.weekday):
                                debug('debugSchedule', self.name, "shouldRun", st.year, st.month, st.day,
                                                                            st.hour, st.minute, st.weekday,
                                                                            st.event)
                                return True
        return False

    def setControlState(self, schedule, state):
        # run the schedule
        debug('debugSchedule', self.name, "schedule", schedule.name)
        control = schedule.control
        if control:
            debug('debugSchedule', self.name, "setting", control.name, "state", state)
            try:
                control.setState(state)
            except Exception as ex:
                log(self.name, "exception running schedule", schedule.name, type(ex).__name__, str(ex))

# a Schedule specifies a control to be set to a specified state at a specified time
class Schedule(StateControl):
    def __init__(self, name, schedTime=None, control=None, controlState=1, endTime=None, endState=0,
                 enabled=True, interface=None, **kwargs):
        StateControl.__init__(self, name, interface=interface, initial=normalState(enabled), **kwargs)
        self.type = "schedule"
        self.className = "Schedule"
        self.schedTime = schedTime          # when to run the schedule
        self.control = control              # which control to set, can be a name
        self.controlState = controlState    # the state to set the control to
        self.endTime = endTime              # optional end time
        self.endState = endState            # optional state to set the control to at the end time
        self.enabled = normalState(enabled)
        self.states = {0: "Disabled", 1: "Enabled"}
        self.setStates = {0: "Dis", 1: "Ena"}

    # attributes to include in the serialized object
    def dict(self, expand=False):
        attrs = Control.dict(self)
        attrs.update({"control": str(self.control),
                      "controlState": self.controlState,
                      "schedTime": self.schedTime.dump()})
        if self.endTime:
            attrs.update({"endState": self.endState,
                          "endTime": self.endTime.dump()})
        return attrs

    # string representation of the object for display in a UI
    def __repr__(self, views=None):
        msg = str(self.control)+": "+str(self.controlState)+"\n"+self.schedTime.__str__()
        if self.endTime:
            msg += "\n"+str(self.control)+": "+str(self.endState)+"\n"+self.endTime.__str__()
        return msg

    def __del__(self):
        del(self.schedTime)

# Schedule Time defines a date and time to perform a schedule.
# Year, month, day, hour, minute, and weekday may be specified as a list of zero or more values.
# Events of "sunrise" or "sunset" may also be specified.
# If an event and a time (hours, minutes) are specified, the time is considered to be a delta from the event
# and may contain negative values.

# day of week identifiers
Mon = 0
Tue = 1
Wed = 2
Thu = 3
Fri = 4
Sat = 5
Sun = 6
weekdayTbl = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# month identifiers
Jan = 1
Feb = 2
Mar = 3
Apr = 4
May = 5
Jun = 6
Jul = 7
Aug = 8
Sep = 9
Oct = 10
Nov = 11
Dec = 12
monthTbl = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# event identifiers
eventTbl = {"sunrise": sunrise, "sunset": sunset}

# return the position of a possibly abbreviated item in a list
# position is based starting at 1, a result of 0 means the item wasn't found
def pos(item, itemList):
    for i in range(len(itemList)):
        if item.capitalize() == itemList[i][0:len(item)]:
            return i + 1
    return 0

class SchedTime(Object):
    def __init__(self, timeSpec=None, year=None, month=None, day=None, hour=None, minute=None, weekday=None, event=None):
        Object.__init__(self)
        if year: self.year = listize(year)
        else: self.year = []
        if month: self.month = listize(month)
        else: self.month = []
        if day: self.day = listize(day)
        else: self.day = []
        if hour: self.hour = listize(hour)
        else: self.hour = []
        if minute: self.minute = listize(minute)
        else: self.minute = []
        if weekday: self.weekday = listize(weekday)
        else: self.weekday = []
        if event: self.event = event
        else: self.event = ""
        self.error = False
        if isinstance(timeSpec, str):           # timeSpec string is specified
            self.timeSpec = timeSpec
            self.parseSpec(self.timeSpec)
        elif isinstance(timeSpec, Sensor):      # timeSpec string is contained in the state of a sensor
            self.timeSpec = timeSpec.getState()
            self.parseSpec(self.timeSpec)
        else:                                   # elements are specified
            self.timeSpec = self.formatSpec()
        debug("debugSchedTime", self.__repr__())

    # parse a time specification into component items
    def parseSpec(self, timeSpec):
        self.year = []
        self.month = []
        self.day = []
        self.hour = []
        self.minute = []
        self.weekday = []
        self.event = ""
        tsList = timeSpec.split(" ")      # first, split the string on spaces
        self.parseList(tsList)
        if self.error:
            raise ValueError(self.errorMsg)

    # parse a list of items either space or comma delimited
    def parseList(self, tsList):
        debug("debugSchedTime", "parseList", tsList)
        for ts in tsList:
            rangeItems = ts.split("-")
            if len(rangeItems) == 2:        # item contains a range
                if rangeItems[0] in ["", ":"]:
                    self.parseItem(ts)      # the - is actually a negative sign
                else:
                    self.parseList(self.parseRange(rangeItems))
            elif len(rangeItems) > 2:
                self.error = True
                self.errorMsg = "Invalid range"
            else:
                listItems = ts.split(",")
                if len(listItems) >= 2:     # item contains a comma separated list
                    self.parseList(listItems)
                else:                       # item contains a single value
                    self.parseItem(ts)

    # parse a single item
    def parseItem(self, ts):
        debug("debugSchedTime", "parseItem", ts)
        try:                                        # is it an integer?
            tsInt = int(ts)
            if tsInt > 31:                          # valid year
                self.year.append(tsInt)
            elif (tsInt <= 31) and (tsInt > 0):     # valid day
                self.day.append(tsInt)
            else:
                self.error = True
                self.errorMsg = "Invalid day"
        except ValueError:                          # not an integer
            if ts != "":                            # empty string is valid
                if pos(ts, monthTbl):               # item is a month
                    self.month.append(pos(ts, monthTbl))
                elif pos(ts, weekdayTbl):           # item is a weekday
                    self.weekday.append(pos(ts, weekdayTbl) - 1)
                elif ts.lower() in list(eventTbl.keys()):        # item is an event
                    self.event = ts.lower()
                    # self.event.append(ts.lower())
                else:                               # item is a time
                    tsTime = ts.split(":")          # split hours and minutes
                    if len(tsTime) == 2:            # exactly one colon
                        try:
                            if tsTime[0] != "":     # time contains an hour
                                self.hour.append(int(tsTime[0]))
                            if tsTime[1] != "":     # time contains a minute
                                if int(tsTime[1]) not in self.minute:
                                    self.minute.append(int(tsTime[1]))
                        except ValueError:          # not an integer
                            self.error = True
                            self.errorMsg = "Invalid time"
                    elif len(tsTime) > 2:           # too many colons
                        self.error = True
                        self.errorMsg = "Invalid time"
                    elif len(tsTime) < 2:           # no colon
                        self.error = True
                        self.errorMsg = "Invalid spec"

    # expand a range into a list
    def parseRange(self, rangeItems):
        debug("debugSchedTime", "parseRange", rangeItems)
        pos1 = pos(rangeItems[0], monthTbl)
        pos2 = pos(rangeItems[1], monthTbl)
        if pos1 and pos2 and (pos1 < pos2):         # both items are months
            return monthTbl[pos1-1:pos2]
        else:
            pos1 = pos(rangeItems[0], weekdayTbl)
            pos2 = pos(rangeItems[1], weekdayTbl)
            if pos1 and pos2 and (pos1 < pos2):     # both items are weekdays
                return weekdayTbl[pos1-1:pos2]
            else:                                   # items might be numeric
                if rangeItems[0].isnumeric() and rangeItems[1].isnumeric():
                    if int(rangeItems[0]) < int(rangeItems[1]):
                        return [str(n) for n in range(int(rangeItems[0]), int(rangeItems[1])+1)]
        self.error = True
        self.errorMsg = "Invalid values in range"
        return []

    # format a time specification from component items
    def formatSpec(self):
        msg = ""
        if len(self.year) > 0:
            msg += " "
            for year in self.year:
                msg += str(year)+","
            msg = msg.rstrip(",")
        if len(self.month) > 0:
            msg += " "
            for month in self.month:
                msg += monthTbl[month-1][0:3]+","
            msg = msg.rstrip(",")
        if len(self.day) > 0:
            msg += " "
            for day in self.day:
                msg += str(day)+","
            msg = msg.rstrip(",")
        if len(self.hour) > 0:
            msg += " "
            for hour in self.hour:
                msg += str(hour)+","
            msg = msg.rstrip(",")
        if len(self.minute) > 0:
            msg += " "
            for minute in self.minute:
                msg += ":"+str(minute)+","
            msg = msg.rstrip(",")
        if len(self.weekday) > 0:
            msg += " "
            for weekday in self.weekday:
                msg += weekdayTbl[weekday][0:3]+","
            msg = msg.rstrip(",")
        if len(self.event) > 0:
            msg += " "+self.event
        return msg

    # offset an event time by a delta time if hours or minutes are specified
    def offsetEventTime(self, eventTime):
        deltaMinutes = 0
        if self.hour != []:
            deltaMinutes += self.hour[0]*60
        if self.minute != []:
            deltaMinutes += self.minute[0]
        return eventTime + datetime.timedelta(minutes=deltaMinutes)

    # determine the specific time of the next occurrence of an event, if present
    def eventTime(self):
        if self.event != "":
            (today, tomorrow) = todaysDate()
            if (self.year != []) and (self.month != []) and (self.day != []):   # date is specified
                eventTime = self.offsetEventTime(eventTbl[self.event](datetime.date(self.year[0], self.month[0], self.day[0]), latLong))
            else:
                # use today's event time
                eventTime = self.offsetEventTime(eventTbl[self.event](today, latLong))
            self.hour = [eventTime.hour]
            self.minute = [eventTime.minute]

    # attributes to include in the serialized object
    def dict(self, expand=False):
        return {"timeSpec":self.timeSpec,
                "year":self.year,
                "month":self.month,
                "day":self.day,
                "hour":self.hour,
                "minute":self.minute,
                "weekday":self.weekday,
                "event":self.event
                }

    # string representation of the object for display in a UI
    def __repr__(self):
        return self.timeSpec+"\n"+ \
               str(self.year)+" "+ \
               str(self.month)+" "+ \
               str(self.day)+" "+ \
               str(self.hour)+" "+ \
               str(self.minute)+" "+ \
               str(self.weekday)+" "+ \
               str(self.event)
