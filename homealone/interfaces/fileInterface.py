filePollInterval = 1
fileRetryInterval = .1

from homealone import *
import json
import os
import threading
import time

class FileInterface(Interface):
    def __init__(self, name, interface=None, event=None, start=False,
                 fileName="", readOnly=False, shared=False, changeMonitor=True,
                 defaultValue=None, initialState={}):
        Interface.__init__(self, name, interface=interface, event=event)
        self.fileName = fileName
        self.readOnly = readOnly            # file cannot be written to
        self.shared = shared                # this file may be written and read by different processes
        self.changeMonitor = changeMonitor  # watch for changes and update the cache
        self.defaultValue = defaultValue    # value to use for undefined elements
        self.initialState = initialState    # values to set if the file doesn't exist
        self.data = {}                      # cached data
        self.mtime = 0                      # last time the file was modified
        self.lock = threading.Lock()
        if start:                           # immediately start the interface
            self.start()

    def start(self):
        try:
            # if the file exists, cache the data
            debug('debugFile', self.name, "reading", self.fileName)
            with open(self.fileName) as dataFile:
                self.data = json.load(dataFile)
        except FileNotFoundError:
            # create a new file
            debug('debugFile', self.name, "creating", self.fileName)
            self.data = self.initialState
            self.writeData()
        except Exception as ex:
            log(self.name, "start exception opening", self.fileName, type(ex).__name__, str(ex))
            self.data = self.initialState
            self.writeData()
        self.mtime = os.stat(self.fileName).st_mtime
        if self.changeMonitor:
            # thread to periodically check for file changes and cache the data
            def readData():
                debug('debugFileThread', self.name, "readData started")
                while True:
                    debug('debugFileThread', self.name, "waiting", filePollInterval)
                    time.sleep(filePollInterval)
                    if self.modified():     # file has changed
                        self.readData()     # read new data
                        for sensor in list(self.sensors.keys()): # notify all sensors
                            if sensor in self.data:
                                self.sensors[sensor].notify(self.data[sensor])
            readStatesThread = LogThread(name="readStatesThread", target=readData)
            readStatesThread.start()

    def read(self, addr):
        if not self.changeMonitor:   # read the file every time
            self.readData()
        with self.lock:
            try:
                value = self.data[addr]
            except KeyError:
                value = self.defaultValue
        debug('debugFileData', self.name, "read", "addr", addr, "value", value)
        return value

    def write(self, addr, value):
        if not self.readOnly:
            debug('debugFileData', self.name, "write", "addr", addr, "value", value)
            with self.lock:
                self.data[addr] = value
            self.notify()
            self.writeData()

    def delete(self, addr):
        if not self.readOnly:
            with self.lock:
                del(self.data[addr])
            self.notify()
            self.writeData()

    def modified(self):
        mtime = os.stat(self.fileName).st_mtime
        if mtime > self.mtime:
            debug('debugFile', self.name, "modified", mtime, "last", self.mtime)
            self.mtime = mtime
            return True
        else:
            return False

    def readData(self):
        try:
            with open(self.fileName) as dataFile:
                jsonData = dataFile.read()
                if (jsonData == "") and (self.shared): # wait until there is valid data
                    debug('debugFile', self.name, "readData", "waiting for data", time.time())
                    while jsonData == "":
                        time.sleep(fileRetryInterval)
                        jsonData = dataFile.read()
                    debug('debugFile', self.name, "readData", "data acquired", time.time())
            with self.lock:
                self.data = json.loads(jsonData)
        except Exception as ex:
            log(self.name, self.fileName, "readData file read error", type(ex).__name__, str(ex), "jsonData", str(jsonData))
        debug('debugFileData', self.name, "readData", self.data)

    def writeData(self):
        debug('debugFileData', self.name, "writeData", self.data)
        with open(self.fileName, "w") as dataFile:
            with self.lock:
                json.dump(self.data, dataFile)
        self.mtime = time.time()
