tcpTimeout = 10.0
pollInterval = 1
disabledPollInterval = 10
maxRetries = 3

import socket
import json
import struct
import threading
import time
from homealone import *

# TP-Link device control

port = 9999

# Encryption and Decryption of TP-Link Smart Home Protocol
# XOR Autokey Cipher with starting key = 171
def encrypt(string):
    msg = bytes(string, "utf-8")
    result = struct.pack('>I', len(msg))
    key = 171
    for i in msg:
        a = key ^ int(i)
        key = a
        result += bytes([a])
    return result

def decrypt(msg):
    result = b""
    key = 171
    for i in msg[4:]:
        a = key ^ int(i)
        key = i
        result += bytes([a])
    return result.decode("utf-8")

class TplinkInterface(Interface):
    def __init__(self, name, ipAddr, model=None, interface=None, event=None):
        Interface.__init__(self, name, interface, event=event)
        self.ipAddr = ipAddr            # IP address of TPLink device
        self.model = model              # TPLink model number
        self.sysInfo = {}               # TPLink device information
        self.sleepTime = pollInterval   # how often to poll for state data
        self.errorCount = 0             # number of consecutive read errors
        # poll the device every second to generate state change notifications
        # cached state is the dictionary that is returned
        def getInfo():
            debug("debugTplink", self.name, "getInfo starting")
            while True:
                try:
                    sysInfo = self.readSysInfo()
                    if sysInfo:
                        debug("debugTplink", self.name, "sysInfo:", sysInfo)
                        self.sysInfo = sysInfo
                        if not self.model:
                            self.model = sysInfo["model"][0:5]
                        for sensor in list(self.sensors.values()):
                            if isinstance(sensor.addr, int):    # sensor is the device that is controlled
                                if self.model in ["KP200"]:      # TPLink device controls multiple devices
                                    sensorState = self.sysInfo["children"][sensor.addr]["state"]
                                else:                           # TPLink device controls a single device
                                    sensorState = self.sysInfo["relay_state"]
                            else:                               # sensor is some other attribute of the TPLink device
                                sensorState = self.sysInfo[sensor.addr]
                            if sensorState != self.states[sensor.addr]: # state has changed
                                self.states[sensor.addr] = sensorState
                                sensor.notify()
                except Exception as ex:
                    log("tplink state exception", self.sensorAddrs[ipAddr].name, ipAddr)
                    logException(self.name, ex)
                time.sleep(self.sleepTime)
            debug("debugTplink", self.name, "getInfo terminated")
        stateThread = LogThread(name=self.name+" getInfo", target=getInfo)
        stateThread.start()

    def readSysInfo(self):
        debug("debugTplink", self.name, "readSysInfo", self.ipAddr)
        try:
            tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcpSocket.connect((self.ipAddr, port))
            tcpSocket.settimeout(tcpTimeout)
            tcpSocket.send(encrypt('{"system":{"get_sysinfo":{}}}'))
            data = tcpSocket.recv(2048)
            tcpSocket.close()
            if not self.enabled:
                log(self.name, "enabling after", self.errorCount, "retries")
                self.enable()
                self.sleepTime = pollInterval
                self.errorCount = 0
            sysInfo = json.loads(decrypt(data))["system"]["get_sysinfo"]
            return sysInfo
        except Exception as ex:
            self.errorCount += 1
            if self.enabled:
                log(self.name, "read exception", str(ex), self.ipAddr)
                if self.errorCount == maxRetries:
                    log(self.name, "disabling after", maxRetries, "retries")
                    self.disable()
                    self.sleepTime = disabledPollInterval
            return None

    def read(self, addr):
        debug("debugTplink", self.name, "read", addr)
        try:
            return self.states[addr]
        except Exception as ex:
            logException(self.name, ex)
            debug("debugTplink", self.name, "state", self.sysInfo)
            return None

    def write(self, addr, state):
        debug("debugTplink", self.name, "write", addr, state)
        if not self.enabled:
            return None
        try:
            # only relay_state can be written
            if isinstance(addr, int):
                if self.model in ["KP200"]:      # TPLink device controls multiple devices
                    deviceContext = ',"context":{"child_ids":["'+self.sysInfo["deviceId"]+'%02d'%addr+'"]}'
                else:
                    deviceContext = ''
                stateMsg = '{"system":{"set_relay_state":{"state":'+str(state)+'}}'+deviceContext+'}'
                debug("debugTplink", self.name, "stateMsg:", stateMsg)
                tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcpSocket.connect((self.ipAddr, port))
                tcpSocket.settimeout(tcpTimeout)
                tcpSocket.send(encrypt(stateMsg))
                statusMsg = decrypt(tcpSocket.recv(2048))
                debug("debugTplink", self.name, "statusMsg:", statusMsg)
                status = int(json.loads(statusMsg)["system"]["set_relay_state"]["err_code"])
                tcpSocket.close()
                if status == 0:
                    # update the cached state
                    self.states[addr] = state
                    self.sensorAddrs[addr].notify()
                    return state
                else:
                    return None
            else:
                return None
        except Exception as ex:
            log("tplink write exception", self.sensorAddrs[ipAddr].name, ipAddr)
            logException(self.name, ex)
            return None
