import syslog
import os
import time
import threading
import traceback
import json
import copy
import subprocess

from .env import *

# states
off = 0
Off = 0
on = 1
On = 1

# log a message to syslog or stdout
def log(*args):
    message = args[0]+" "   # first argument is the object doing the logging
    for arg in args[1:]:
        message += arg.__str__()+" "
    if sysLogging:
        syslog.syslog(message)
    else:
        print(time.strftime("%b %d %H:%M:%S", time.localtime())+" "+message)

# log the traceback for an exception
def logException(name, ex):
    tracebackLines = traceback.format_exception(None, ex, ex.__traceback__)
    log(name+":")
    for tracebackLine in tracebackLines:
        log(tracebackLine)

# thread object that logs a stack trace if there is an uncaught exception
class LogThread(threading.Thread):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.runTarget = self.run
        self.run = self.logThread

    def logThread(self):
        try:
            self.runTarget()
        except Exception as ex:
            logException("thread "+threading.currentThread().name, ex)

# convenience function to create and start a thread
def startThread(name, target, **kwargs):
    thread = LogThread(name=name, target=target, **kwargs)
    thread.start()

# log a debug message conditioned on a specified global variable
def debug(*args):
    try:
        if debugEnable:   # global debug flag enables debugging
            if globals()[args[0]]:  # only log if the specified debug variable is True
                log(*args[1:])
    except KeyError:
        pass

# log a stack trace conditioned on a specified global variable
def debugTraceback(debugType, debugName):
    try:
        if debugEnable:   # global debug flag enables debugging
            if globals()[debugType]:
                s = inspect.stack()
                for f in s:
                    log(debugName, f[1], f[2], f[3], f[4])
    except KeyError:
        pass

# wait for the network to be available
def waitForDns():
    wasWaiting = False
    while True:
        try:
            metricsHost = socket.gethostbyname(localController)
            if wasWaiting:
                log("DNS is up")
            return
        except:
            log("Waiting for DNS")
            wasWaiting = True
            time.sleep(1)

# create a human friendly label from a camel case or dotted name
def labelize(name):
    label = ""
    for char in name.replace(".", " "):
        if label:
            if label[-1].islower() and (char.isupper() or char.isnumeric()):
                label += " "
        label += char.lower()
    return label.capitalize()

# transform a dotted name into camel case
def camelize(name):
    return "".join([name.split(".")[0]]+[part[0].upper()+part[1:] for part in (name.split(".")[1:])])

# turn an item into a list if it is not already
def listize(x):
    return x if isinstance(x, list) else [x]

# normalize state values from boolean to integers
def normalState(value):
    if value == True: return On
    elif value == False: return Off
    else: return value

# get the value of a variable from a file
def getValue(fileName, item):
    return json.load(open(fileName))[item]

# Compare two state dictionaries and return a dictionary containing the items
# whose values don't match or aren't in the old dict.
# If an item is in the old but not in the new, optionally include the item with value None.
def diffStates(old, new, deleted=True):
    diff = copy.copy(new)
    for key in list(old.keys()):
        try:
            if new[key] == old[key]:
                del diff[key]   # values match
        except KeyError:        # item is missing from the new dict
            if deleted:         # include deleted item in output
                diff[key] = None
    return diff

# find a zeroconf service being advertised on the local network
def findService(serviceName, serviceType="tcp", ipVersion="IPv4"):
    servers = []
    serverList = subprocess.check_output("avahi-browse -tp --resolve _"+serviceName+"._"+serviceType ,shell=True).decode().split("\n")
    for server in serverList:
        serverData = server.split(";")
        if len(serverData) > 6:
            if serverData[2] == ipVersion:
                host = serverData[6]
                port = serverData[8]
                servers.append((host, int(port)))
    return servers

# register a zeroconf service on the local host
def registerService(serviceName, servicePort, serviceType="tcp"):
    serviceDir = "/etc/avahi/services/"
    with open(serviceDir+serviceName+".service", "w") as serviceFile:
        serviceFile.write('<?xml version="1.0" standalone="no"?>\n')
        serviceFile.write('<!DOCTYPE service-group SYSTEM "avahi-service.dtd">\n')
        serviceFile.write('<service-group>\n')
        serviceFile.write('  <name replace-wildcards="yes">%h</name>\n')
        serviceFile.write('  <service>\n')
        serviceFile.write('    <type>_'+serviceName+'._'+serviceType+'</type>\n')
        serviceFile.write('    <port>'+str(servicePort)+'</port>\n')
        serviceFile.write('  </service>\n')
        serviceFile.write('</service-group>\n')

# unregister a zeroconf service on the local host
def unregisterService(serviceName):
    serviceDir = "/etc/avahi/services/"
    os.remove(serviceDir+serviceName+".service")

# format an E.164 phone number for display
def displayNumber(number):
    if number != "":
        return "%s %s-%s" % (number[2:5], number[5:8], number[8:])
    else:
        return ""

# format a phone number as E.164
def e164number(number):
    number = ''.join(ch for ch in number if ch.isdigit())
    if len(number) == 7:
        number = defaultAreaCode+number
    if len(number) == 10:
        number = defaultCountryCode+number
    if len(number) == 11:
        number = "+"+number
    return number
