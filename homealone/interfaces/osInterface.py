
import subprocess
import time
from homealone import *

# Interface to various OS parameters
class OSInterface(Interface):
    def __init__(self, name, interface=None, event=None):
        Interface.__init__(self, name, interface=interface, event=event)

    def start(self, notify=None):
        startThread(name="readStateThread", target=self.readStates, notify=notify)

    # thread to constantly read and cache values
    def readStates(self):
        while True:
            # CPU temp
            self.states["cpuTemp"] = float(subprocess.check_output("vcgencmd measure_temp", shell=True)[5:-3])
            # CPU load
            with open('/proc/stat') as f:
                fields = [float(column) for column in f.readline().strip().split()[1:]]
            last_idle, last_total = fields[3], sum(fields)
            time.sleep(1)
            with open('/proc/stat') as f:
                fields = [float(column) for column in f.readline().strip().split()[1:]]
            idle, total = fields[3], sum(fields)
            idle_delta, total_delta = idle - last_idle, total - last_total
            last_idle, last_total = idle, total
            self.states["cpuLoad"] = 100.0 * (1.0 - idle_delta / total_delta)
            # disk usage of the root filesystem
            useParts = subprocess.check_output("df /", shell=True).decode().split("\n")[1].split()
            self.states["diskUse"] = 100 * int(useParts[2]) / (int(useParts[2]) + int(useParts[3]))
            # IP address
            try:
                self.states["ipAddr"] = subprocess.check_output("ifconfig|grep inet\ |grep -v 127", shell=True).decode().strip("\n").split()[1]
            except subprocess.CalledProcessError:
                self.states["ipAddr"] = ""
            # uptime
            self.states["uptime"] = " ".join(c for c in subprocess.check_output("uptime", shell=True).decode().strip("\n").split(",")[0].split()[2:])

            time.sleep(10)

    def read(self, addr):
        try:
            return self.states[addr]
        except KeyError:
            return None
