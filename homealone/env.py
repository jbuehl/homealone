# initialize the global variables that define the environment
import os
import socket
import sys
import inspect

# network
hostname = socket.gethostname()
localController = "localhost"
externalUrl = "example.com"

# directory structure
# directory containing this application
appDir = sys.path[0]
# site configuration directory - add to path so config can be imported
siteDir = "/etc/homealone/site"
sys.path.append(siteDir)
keyDir = siteDir+"/keys/"       # external credentials
stateDir = appDir+"/state/"     # app specific states
dataDir = appDir+"/data/"       # data logging

# logging and debugging
sysLogging = True
debugEnable = False

# Localization
latLong = (0.0, 0.0)
elevation = 0 # elevation in feet
tempScale = "F"
defaultCountryCode = "1"
defaultAreaCode = "000"

# Data logging and metrics
metricsPrefix = "com.example.ha"
metricsHost = "metrics.example.com"
metricsPort = 2003
sendMetrics = True
logData = True
archiveData = True
purgeData = True
purgeDays = 5
logChanged = True
archiveService = "archive"
archiveDir = "/archives/"

# REST parameters
restServicePorts = [7378, 7377, 7376, 7375, 7374, 7373, 7372, 7371]
restServicePort = 7378
restAdvertPort = 4244 # 7379
restNotificationPort = 7370
ipv4MulticastAddr = "224.0.0.1"
ipv6MulticastAddr = "ff02::1"
multicastAddr = ipv4MulticastAddr
restAdvertInterval = 10
restAdvertTimeout = 60
restTimeout = 60
restRetryInterval = 10

# Alerts and events
alertConfig = {}
eventConfig = {}

# optionally import site configuration
try:
    from siteConf import *
except ImportError:
    pass

# optionally import app configuration
try:
    from conf import *
except ImportError:
    pass
