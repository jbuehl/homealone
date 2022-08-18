# Classes related to schedules

from homealone.core import *
from .sunriseset import *

# day of week identifiers
Mon = 0
Tue = 1
Wed = 2
Thu = 3
Fri = 4
Sat = 5
Sun = 6
weekdayTbl = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

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
monthTbl = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# return today's and tomorrow's dates
def todaysDate():
    today = datetime.datetime.now().replace(tzinfo=tz.tzlocal())
    tomorrow = today + datetime.timedelta(days=1)
    return (today, tomorrow)

# A Cycle describes the process of setting a Control to a specified state, waiting a specified length of time,
# and setting the Control to another state.  This may be preceded by an optional delay.
# If the duration is None, then the end state is not set and the Control is left in the start state.
class Cycle(Object):
    def __init__(self, control=None, duration=None, delay=0, startState=1, endState=0, name=None):
        Object.__init__(self)
        self.control = control
        self.duration = duration
        self.delay = delay
        self.startState = normalState(startState)
        self.endState = normalState(endState)

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        return {"control": self.control.name,
                "duration": self.duration.getState() if isinstance(self.duration, Sensor) else self.duration,
                "delay": self.delay,
                "startState": self.startState,
                "endState": self.endState}

    def __repr__(self):
        return self.control.__str__()+","+self.duration.__str__()+","+self.delay.__str__()+","+self.startState.__str__()+","+self.endState.__str__()

# a Sequence is a Control that consists of a list of Cycles or Sequences that are run in the specified order

sequenceStop = 0
sequenceStart = 1
sequenceStopped = 0
sequenceRunning = 1

class Sequence(Control):
    def __init__(self, name, cycleList=[], **kwargs):
        Control.__init__(self, name, **kwargs)
        self.cycleList = cycleList
        self.cycleList = self.getCycles()   # convert possible Sequences to Cycles
        self.running = False

    # if the list of Cycles contains Sequences, convert to Cycles
    def getCycles(self):
        cycleList = []
        for obj in self.cycleList:
            if isinstance(obj, Cycle):
                cycleList.append(obj)
            elif isinstance(obj, Sequence):
                cycleList += obj.getCycles()
        return cycleList

    def getState(self, missing=None):
        if not self.interface:
            return normalState(self.running)
        else:
            return Control.getState(self)

    def setState(self, state, wait=False):
        if not self.interface:
            debug('debugState', self.name, "setState ", state, wait)
            if state and not(self.running):
                self.runCycles(wait)
            elif (not state) and self.running:
                self.stopCycles()
            return True
        else:
            return Control.setState(self, state)

    # Run the Cycles in the list
    def runCycles(self, wait=False):
        debug('debugState', self.name, "runCycles", wait)
        # thread that runs the cycles
        def runCycles():
            debug('debugThread', self.name, "started")
            self.running = True
            for cycle in self.cycleList:
                if not self.running:
                    break
                self.runCycle(cycle)
            self.running = False
            self.notify()
            debug('debugThread', self.name, "finished")
        if wait:    # Run it synchronously
            runCycles()
        else:       # Run it asynchronously in a separate thread
            self.cycleThread = LogThread(name="self.cycleThread", target=runCycles)
            self.cycleThread.start()

    # Stop all Cycles in the list
    def stopCycles(self):
        self.running = False
        for cycle in self.cycleList:
            cycle.control.setState(cycle.endState)
        self.notify()
        debug('debugThread', self.name, "stopped")

    # state change notification to all control events since the sequence doesn't have an event
    def notify(self, state=None):
        time.sleep(2)   # short delay to ensure the state change event for the sequence isn't missed
        for cycle in self.cycleList:
            if isinstance(cycle.control, Sensor):
                cycle.control.notify()

    # Run the specified Cycle
    def runCycle(self, cycle):
        if cycle.delay > 0:
            debug('debugThread', self.name, cycle.control.name, "delaying", cycle.delay)
            self.wait(cycle.delay)
            if not self.running:
                return
        if cycle.duration == None:    # just set the state
            debug('debugThread', self.name, cycle.control.name, "started")
            cycle.control.setState(cycle.startState)
        else:
            if isinstance(cycle.duration, int):         # duration is specified directly
                duration = cycle.duration
            elif isinstance(cycle.duration, Sensor):    # duration is a sensor
                duration = cycle.duration.getState()
            if duration > 0:
                debug('debugThread', self.name, cycle.control.name, "started for", duration, "seconds")
                cycle.control.setState(cycle.startState)
                self.wait(duration)
                cycle.control.setState(cycle.endState)
                debug('debugThread', self.name, cycle.control.name, "finished")

    # wait the specified number of seconds
    # break immediately if the sequence is stopped
    def wait(self, duration):
        for seconds in range(0, duration):
            if not self.running:
                break
            time.sleep(1)

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        attrs = Sensor.dict(self)
        attrs.update({"cycleList": [cycle.dump() for cycle in self.cycleList]})
        return attrs

    def __repr__(self):
        msg = ""
        for cycle in self.cycleList:
            msg += cycle.__str__()+"\n"
        return msg.rstrip("\n")

# the Scheduler manages a list of Tasks and runs them at the times specified
class Schedule(Collection):
    def __init__(self, name, tasks=[]):
        Collection.__init__(self, name, resources=tasks)
        self.type = "schedule"
        self.schedThread = LogThread(name="self.schedThread", target=self.doSchedule)

    def start(self):
        self.initControls()
        self.schedThread.start()

    def getState(self, missing=None):
        return 1

    def addRes(self, resource):
        Collection.addRes(self, resource)
        if resource.schedTime.event != "":
            # if an event is specified, add a child task with a specific date and time
            self.addRes(resource.child())
            debug('debugEvent', self.name, "adding", resource.child().__str__())

    # add a task to the scheduler list
    def addTask(self, task):
        self.addRes(task)
        debug('debugEvent', self.name, "adding", task.__str__())

    # delete a task from the scheduler list
    def delTask(self, taskName):
        self.delRes(taskName)
        debug('debugEvent', self.name, "deleting", taskName)

    # initialize control states in certain cases
    def initControls(self):
        (now, tomorrow) = todaysDate()
        for taskName in list(self.keys()):
            task = self[taskName]
            # task must have an end time
            if task.endTime:
                # task must recur daily at a specific time
                if (task.schedTime.year == []) and \
                   (task.schedTime.month == []) and \
                   (task.schedTime.day == []) and \
                   (task.schedTime.weekday == []) and \
                   (task.schedTime.event == ""):
                   # task must start and end within the same day
                   if task.schedTime.hour < task.endTime.hour:
                       # set the expected state of the control at the present time
                       # assume it runs once a day, ignore minutes
                       if (now.hour >= task.schedTime.hour[0]) and (now.hour < task.endTime.hour[0]):
                           self.setControlState(task, task.controlState)
                       else:
                           self.setControlState(task, task.endState)

    # Scheduler thread
    def doSchedule(self):
        debug('debugThread', self.name, "started")
        while True:
            # wake up every minute on the 00 second
            (now, tomorrow) = todaysDate()
            sleepTime = 60 - now.second
            debug('debugSched', self.name, "sleeping ", sleepTime)
            time.sleep(sleepTime)
            (now, tomorrow) = todaysDate()
            debug('debugSched', self.name, "waking up",
                    now.year, now.month, now.day, now.hour, now.minute, now.weekday())
            # run through the schedule and check if any tasks should be run
            # need to handle cases where the schedule could be modified while this is running - FIXME
            for taskName in list(self.keys()):
                task = self[taskName]
                debug('debugSched', self.name, "checking ", taskName,
                        task.schedTime.year, task.schedTime.month, task.schedTime.day,
                        task.schedTime.hour, task.schedTime.minute, task.schedTime.weekday,
                        task.schedTime.event)
                if task.enabled:
                    if self.shouldRun(task.schedTime, now):
                        self.setControlState(task, task.controlState)
                    if task.endTime:
                        if self.shouldRun(task.endTime, now):
                            self.setControlState(task, task.endState)
                # determine if this was the last time the task would run
                if task.schedTime.last:
                    if task.schedTime.last <= now:
                        # delete the task from the schedule if it will never run again
                        self.delTask(taskName)
                        # reschedule the next occurrence if the task was a child of an event task
                        if task.parent:
                            self.addTask(task.parent.child())
                        del(task)

    def shouldRun(self, schedTime, now):
        # the task should be run if the current date/time matches all specified fields in the SchedTime
        if (schedTime.event == ""): # don't run tasks that specify an event
            if (schedTime.year == []) or (now.year in schedTime.year):
                if (schedTime.month == []) or (now.month in schedTime.month):
                    if (schedTime.day == []) or (now.day in schedTime.day):
                        if (schedTime.hour == []) or (now.hour in schedTime.hour):
                            if (schedTime.minute == []) or (now.minute in schedTime.minute):
                                if (schedTime.weekday == []) or (now.weekday() in schedTime.weekday):
                                    return True
        return False

    def setControlState(self, task, state):
        # run the task
        debug('debugEvent', self.name, "task", task.name)
        control = task.control
        if control:
            debug('debugEvent', self.name, "setting", control.name, "state", state)
            try:
                control.setState(state)
            except Exception as ex:
                log(self.name, "exception running task", task.name, type(ex).__name__, str(ex))

# a Task specifies a control to be set to a specified state at a specified time
class Task(Control):
    def __init__(self, name, schedTime=None, control=None, controlState=1, endTime=None, endState=0,
                 parent=None, enabled=True, **kwargs):
        Control.__init__(self, name, **kwargs)
        self.type = "task"
        self.schedTime = schedTime          # when to run the task
        self.control = control              # which control to set, can be a name
        self.controlState = controlState    # the state to set the control to
        self.endTime = endTime              # optional end time
        self.endState = endState            # optional state to set the control to at the end time
        self.parent = parent
        self.enabled = normalState(enabled)

    def getState(self, missing=None):
        if not self.interface:
            return self.enabled
        else:
            return Control.getState(self)

    def setState(self, state):
        if not self.interface:
            self.enabled = state
            self.notify(state)
            return True
        else:
            return Control.setState(self, state)

    # create a child task for the event on a specific date and time
    def child(self):
        schedTime = copy.copy(self.schedTime)
        schedTime.eventTime(latLong)
        schedTime.event = ""
        schedTime.lastTime()
        return Task(self.name+"Event", schedTime, self.control, self.controlState, parent=self)

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        attrs = Control.dict(self)
        attrs.update({"control": str(self.control),
                      "controlState": self.controlState,
                      "schedTime": self.schedTime.dump()})
        if self.endTime:
            attrs.update({"endState": self.endState,
                          "endTime": self.endTime.dump()})
        return attrs

    def __repr__(self, views=None):
        msg = str(self.control)+": "+str(self.controlState)+","+self.schedTime.__str__()
        if self.endTime:
            msg += ","+str(self.control)+": "+str(self.endState)+","+self.endTime.__str__()
        return msg

    def __del__(self):
        del(self.schedTime)

# Schedule Time defines a date and time to perform a task.
# Year, month, day, hour, minute, and weekday may be specified as a list of zero or more values.
# Relative dates of "today" or "tomorrow" and events of "sunrise" or "sunset" may also be specified.
# If an event and a time (hours, minutes) are specified, the time is considered to be a delta from the event
# and may contain negative values.
class SchedTime(Object):
    def __init__(self, year=[], month=[], day=[], hour=[], minute=[], weekday=[], date="", event="", name=""):
        Object.__init__(self)
        self.year = listize(year)
        self.month = listize(month)
        self.day = listize(day)
        self.hour = listize(hour)
        self.minute = listize(minute)
        self.weekday = listize(weekday)
        self.date = date
        self.event = event
        if self.date != "":
            self.specificDate()
        self.lastTime()

    # determine the last specific time this will run
    # the schedule time is considered open-ended if any date or time field is unspecified
    # doesn't account for closed-ended tasks where some fields are specified - FIXME
    def lastTime(self):
        if (self.year != []) and (self.month != []) and (self.day != []) and (self.hour != []) and (self.minute != []):
            # determine the last time a closed-ended task will run so the task can be deleted from the schedule
            self.last = datetime.datetime(max(self.year), max(self.month), max(self.day), max(self.hour), max(self.minute), 0).replace(tzinfo=tz.tzlocal())
        else:
            self.last = None

    # determine the specific date of a relative date
    def specificDate(self):
        (today, tomorrow) = todaysDate()
        if self.date == "today":
            self.year = [today.year]
            self.month = [today.month]
            self.day = [today.day]
        elif self.date == "tomorrow":
            self.year = [tomorrow.year]
            self.month = [tomorrow.month]
            self.day = [tomorrow.day]

    def offsetEventTime(self, eventTime):
        # offset by delta time if hours or minutes are specified
        deltaMinutes = 0
        if self.hour != []:
            deltaMinutes += self.hour[0]*60
        if self.minute != []:
            deltaMinutes += self.minute[0]
        return eventTime + datetime.timedelta(minutes=deltaMinutes)

    # determine the specific time of the next occurrence of an event
    def eventTime(self, latLong):
        eventTbl = {"sunrise": sunrise,
                    "sunset": sunset}
        (today, tomorrow) = todaysDate()
        if (self.year != []) and (self.month != []) and (self.day != []):
            eventTime = self.offsetEventTime(eventTbl[self.event](datetime.date(self.year[0], self.month[0], self.day[0]), latLong))
        else:
            # use today's event time
            eventTime = self.offsetEventTime(eventTbl[self.event](today, latLong))
            if (eventTime <= today) and (self.day == []):
                # use tomorrow's time if today's time was in the past
                eventTime = self.offsetEventTime(eventTbl[self.event](tomorrow, latLong))
            self.year = [eventTime.year]
            self.month = [eventTime.month]
            self.day = [eventTime.day]
        self.hour = [eventTime.hour]
        self.minute = [eventTime.minute]

    # dictionary of pertinent attributes
    def dict(self, expand=False):
        return {"year":self.year,
                "month":self.month,
                "day":self.day,
                "hour":self.hour,
                "minute":self.minute,
                "weekday":self.weekday,
                "event":self.event}

    # return string version of weekdays
    def weekdays(self):
        wds = []
        for wd in self.weekday:
            wds += [weekdayTbl[wd]]
        return wds

    # return string version of months
    def months(self):
        ms = []
        for m in self.month:
            ms += [monthTbl[m-1]]
        return ms

    # return the expanded list of all occurrences of the schedTime
    def enumTimes(self):
        events = [""]
        events = self.enumElem(self.year, events, "", 4, "d")
        events = self.enumElem(self.months(), events, "-", 3, "s")
        events = self.enumElem(self.day, events, "-", 2, "d")
        events = self.enumElem(self.hour, events, " ", 2, "d")
        events = self.enumElem(self.minute, events, ":", 2, "d")
        events = self.enumElem(self.weekdays(), events, " ", 3, "s")
        events = self.enumElem([self.date], events, " ", 0, "s")
        events = self.enumElem([self.event], events, " ", 0, "s")
        return events

    # append a value to the element list for each occurrence of the specified element
    def enumElem(self, elems, events, delim, length, fmt):
        newEvents = []
        format = "%0"+str(length)+fmt
        if elems == []:
            for event in events:
                newEvents += [event+delim+"*"*(length)]
        else:
            for elem in elems:
                for event in events:
                    newEvents += [event+delim+format%elem]
        return newEvents

    def __repr__(self):
        events = self.enumTimes()
        msg = ""
        for event in events:
            msg += event+","
        return msg.rstrip(",")
