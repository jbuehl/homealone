
import subprocess
import time
from homealone import *

# Interface to various OS parameters
class OSInterface(Interface):
    def __init__(self, name, interface=None, event=None):
        Interface.__init__(self, name, interface=interface, event=event)

    def read(self, addr):
        addrParts = addr.split()
        if addrParts[0] == "cpuTemp":
            return float(subprocess.check_output("vcgencmd measure_temp", shell=True)[5:-3])
        elif addrParts[0] == "cpuLoad":
            with open('/proc/stat') as f:
                fields = [float(column) for column in f.readline().strip().split()[1:]]
            last_idle, last_total = fields[3], sum(fields)
            time.sleep(1)
            with open('/proc/stat') as f:
                fields = [float(column) for column in f.readline().strip().split()[1:]]
            idle, total = fields[3], sum(fields)
            idle_delta, total_delta = idle - last_idle, total - last_total
            last_idle, last_total = idle, total
            return 100.0 * (1.0 - idle_delta / total_delta)
        elif addrParts[0] == "diskUse":
            useParts = subprocess.check_output("df "+addrParts[1], shell=True).decode().split("\n")[1].split()
            return 100 * int(useParts[2]) / (int(useParts[2]) + int(useParts[3]))
        elif addrParts[0] == "ssid":
            try:
                return subprocess.check_output("iwconfig "+addrParts[1]+"|grep ESSID", shell=True).decode().strip("\n").split(":")[-1].split("/")[0].strip().strip('"')
            except subprocess.CalledProcessError:
                return ""
        elif addrParts[0] == "ipAddr":
            try:
                return subprocess.check_output("ifconfig "+addrParts[1]+"|grep inet\ ", shell=True).decode().strip("\n").split()[1]
            except subprocess.CalledProcessError:
                return ""
        elif addrParts[0] == "uptime":
            return " ".join(c for c in subprocess.check_output("uptime", shell=True).decode().strip("\n").split(",")[0].split()[2:])
        else:
            return None
