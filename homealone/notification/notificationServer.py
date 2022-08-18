# Notification

import requests
import urllib.parse
import json
from twilio.rest import Client
from homealone import *

twilioKey = keyDir+"twilio.key"
iftttKey = keyDir+"ifttt.key"

# send notifications
def sendNotification(resources, notificationType, message):
    debug("debugNotification", "notification", notificationType, message)
    # send notifications via all active alert channels
    if resources.getRes(notificationType).getState():
        # SMS alerts
        if resources.getRes("smsAlerts").getState():
            try:
                fromNumber = alertConfig[notificationType]["fromNumber"]
                toNumbers = alertConfig[notificationType]["toNumbers"]
                smsNotify(fromNumber, toNumbers, message)
            except KeyError:
                log("notification", "notificationType", notificationType, "not configured")
        # app alerts
        if resources.getRes("appAlerts").getState():
            appNotify("", message)
        # IFTTT alerts
        if resources.getRes("iftttAlerts").getState():
            iftttNotify(message)
    else:
        debug("debugNotification", "notification", notificationType, "not enabled")

# send an sms notification
def smsNotify(fromNumber, toNumbers, message):
    smsClient = Client(getValue(twilioKey, "sid"), getValue(twilioKey, "token"))
    for toNumber in toNumbers:
        debug("debugNotification", "SMS notify from", fromNumber, "to", toNumber)
        smsClient.messages.create(to=e164number(toNumber), from_=e164number(fromNumber), body=message)

# send an app notification
def appNotify(app, message):
    if app != "":
        debug("debugNotification", "app notify to", app)
        requests.get("http://"+app+".appspot.com/notify?message="+urllib.parse.quote(message))

# send an IFTTT notification
def iftttNotify(message):
    key = getValue(iftttKey, "key")
    debug("debugNotification", "IFTTT notify")
    url = "https://maker.ifttt.com/trigger/haEvent/with/key/"+key
    headers = {"Content-Type": "application/json"}
    value2 = ""
    value3 = ""
    data = json.dumps({"value1": message, "value2": value2, "value3": value3})
    req = requests.post(url, data=data, headers=headers)
