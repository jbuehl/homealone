# Utility functions

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

# normalize state values from boolean to integers
def normalState(value):
    if value == True: return On
    elif value == False: return Off
    else: return value

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
