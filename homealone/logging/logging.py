# Data logging, archiving, and metrics

import time
import socket
import json
import subprocess
import os
from homealone import *

class DataLogger(object):
    def __init__(self, name, appName, resources, start=False):
        self.name = name
        self.appName = appName
        self.resources = resources
        self.logDir = dataDir
        os.makedirs(self.logDir, exist_ok=True)
        archiveServers = findService(archiveService)
        if archiveServers == []:
            self.archiveServer = None
            log("no archive server found")
        else:
            self.archiveServer = archiveServers[0][0]
        if start:
            self.start()

    def start(self):
        startThread("loggingThread", self.loggingThread)

    def loggingThread(self):
        debug("debugLogging", "logging thread started")
        lastDay = ""
        while True:
            # wait for a new set of states
            states = self.resources.getStates(wait=True)
            today = time.strftime("%Y%m%d")

            # log states to a file
            if logData:
                if today != lastDay:    # start with a new baseline every day
                    lastStates = states
                changedStates = diffStates(lastStates, states, deleted=False)
                if changedStates != {}:
                    logFileName = self.logDir+today+".json"
                    debug("debugLogging", "writing states to", logFileName)
                    with open(logFileName, "a") as logFile:
                        logFile.write(json.dumps([time.time(), (changedStates if logChanged else lastStates)])+"\n")
                lastStates = states

            # send states to the metrics server
            if sendMetrics:
                debug("debugMetrics", "opening socket to", metricsHost, metricsPort)
                try:
                    metricsSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    metricsSocket.connect((metricsHost, metricsPort))
                    debug("debugMetrics", "sending", len(states), "metrics")
                    for (resourceName, state) in states.items():
                        if isinstance(state, (int, float)):     # only send numeric states
                            metricName = formatName(resourceName, ["offgrid", "solar"], ["voltage", "current", "power", "energy", "temp"])
                            msg = metricsPrefix+"."+metricName+" "+str(state)+" "+str(int(time.time()))
                            debug("debugMetricsMsg", "msg:", msg)
                            metricsSocket.send(bytes(msg+"\n", "utf-8"))
                        else:
                            debug("debugMetrics", "skipping", resourceName, state)
                except socket.error as exception:
                    log("sendMetrics", "socket error", str(exception))
                if metricsSocket:
                    debug("debugMetrics", "closing socket to", metricsHost)
                    metricsSocket.close()

            # copy to the archive server once per day
            if archiveData:
                if self.archiveServer:
                    if today != lastDay:
                        startThread("archiveDataThread", self.archiveDataThread)

            # purge logs that have been archived
            if purgeData:
                if self.archiveServer:
                    if today != lastDay:
                        startThread("purgeDataThread", self.purgeDataThread)

            lastDay = today
        debug("debugLogging", "logging thread ended")

    def archiveDataThread(self):
        debug("debugArchiveData", "archiving data logs")
        try:
            debug("debugArchiveData", "archiving "+self.logDir+" to", self.archiveServer+":"+archiveDir+self.appName+"/")
            pid = subprocess.Popen("rsync -a "+self.logDir+"* "+self.archiveServer+":"+archiveDir+self.appName+"/", shell=True)
        except Exception as ex:
            log("metrics", "exception archiving metrics", str(ex))

    def purgeDataThread(self):
        # get list of log files that are eligible to be purged
        debug("debugPurgeData", "purging logs more than", purgeDays, "days old")
        today = time.strftime("%Y%m%d")
        for logFile in sorted(os.listdir(self.logDir))[:-purgeDays]:
            # only purge past files
            debug("debugPurgeData", "checking", logFile)
            if logFile.split(".")[0] < today:
                try:
                    # get sizes of the file and its archive
                    fileSize = int(subprocess.check_output("ls -l "+self.logDir+logFile+"|cut -f5 -d' '", shell=True))
                    archiveSize = int(subprocess.check_output("ssh "+self.archiveServer+" ls -l "+archiveDir+self.appName+"/"+logFile+"|cut -f5 -d' '", shell=True))
                    # only delete if the sizes are the same
                    if archiveSize == fileSize:
                        debug("debugPurgeData", "deleting", logFile)
                        os.remove(self.logDir+logFile)
                    else:
                        log("not deleting", self.logDir+logFile, "fileSize:", fileSize, "archiveSize:", archiveSize)
                except Exception as ex:
                    log("exception purging log file", logFile, str(ex))

# separate some parts of a camel case name by dots for easier parsing by the metrics server
def formatName(name, prefixes=[], suffixes=[]):
    newPrefix = ""
    for prefix in prefixes:
        if name[0:len(prefix)].lower() == prefix:
            newPrefix = prefix+"."
            name = name[len(prefix):]
            break
    newSuffix = ""
    for suffix in suffixes:
        if name[-len(suffix):].lower() == suffix:
            newSuffix = "."+suffix
            name = name[:-len(suffix)]
            break
    return newPrefix+name[0].lower()+name[1:]+newSuffix
# .replace(" ", "_")
