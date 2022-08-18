# Limited HTTP server for homealone REST and notification interfaces
import socket
import http.client
from .utils import *

class HttpServer(object):
    def __init__(self, name, port, handler, start=False):
        self.name = name
        self.port = port
        self.handler = handler
        self.socket = None
        if start:
            self.start()

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("", self.port))
        self.socket.listen(1)
        startThread(self.name, self.getRequests)

    # read and parse HTTP requests
    def getRequests(self):
        while True:
            (client, addr) = self.socket.accept()
            clientFile = client.makefile()
            # start a new request
            (verb, uri, protocol) = clientFile.readline().strip("\n").split(" ")
            # read the headers
            headers = {}
            header = clientFile.readline().strip("\n").split(":")
            while header != [""]:
                headers[header[0].strip()] = header[1].strip()
                header = clientFile.readline().strip("\n").split(":")
            # read the data
            try:
                data = clientFile.read(int(headers["Content-Length"]))
            except KeyError:
                data = None
            # send it to the handler
            clientFile.close()
            self.handler(self, client, addr, verb, uri, protocol, headers, data)

    # send an HTTP reply
    def sendReply(self, client, protocol, status, headers={}, data=None):
        client.send(bytes(protocol+" "+str(status)+" "+http.client.responses[status]+"\n", "utf-8"))
        for header in headers:
            client.send(bytes(header+": "+headers[header]+"\n", "utf-8"))
        if data:
            client.send(bytes("Content-Length: "+str(len(data))+"\n\n", "utf-8"))
            client.send(bytes(data, "utf-8"))
        client.close()
