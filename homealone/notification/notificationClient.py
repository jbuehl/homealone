
import requests
import urllib.parse
from homealone import *

def sendNotification(notificationType, message):
    servers = findService("notification")
    if servers == []:
        log("notificationClient", "notification server not found")
    else:
        (host, port) = servers[0]
        url = "http://"+host+":"+port+"/notify?eventType="+notificationType+"&message="+urllib.parse.quote(message)
        request = requests.post(url)
        if request.status_code != 200:
            log("notificationClient", "error", url, request.status_code)
