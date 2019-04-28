from datetime import datetime
from flask import Flask
from flask import make_response
from flask import request
import json
from gevent.pywsgi import WSGIServer
import requests
import time
from threading import Timer
import os


STATUS = {"reserved": False, "reserver": None, "reserved_at": None}
APP = Flask(__name__)
BOT_TOKEN = None

AFK_TIMER = None
NOTIFICATION_AFK_TIMER = None

def main():
    global BOT_TOKEN
    BOT_TOKEN = os.environ.get("BOT_TOKEN", None)
    if BOT_TOKEN is None:
        exit(1)

    http_server = WSGIServer(('', 5000), APP)
    http_server.serve_forever()

@APP.route("/bot", methods=['POST'])
def endpoint():
    if "payload" in request.form:
        payload = request.form["payload"]
        answer = payload["actions"][0]["value"]
        if answer == "ack":
            return ack_usage()
        if answer == "deny":
            return deny_usage()

    if request.form['text'] == "check":
        return check()
    if request.form['text'] == "reserve":
        return reserve(request.form['user_id'])
    if request.form['text'] == "free":
        return free(request.form['user_id'])
    if request.form['text'] == "test_notify":
        return notify()

    return help()

def help():
    body = {"text": """
check - Check if Citrix is free now
reserve - Reserve for yourself
free - Cancel your reservation
"""}

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def check():
    body = {"text": None, "response_type": "in_channel"}

    if STATUS["reserved"]:
        body["text"] = "Citrix is reserved now by <@%s>. Please wait!" % STATUS["reserver"]
    else:
        body["text"] = "Citrix is free. Please reserve before using!"

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def reserve(who):
    body = {"text": None, "response_type": "in_channel"}

    if STATUS["reserved"]:
        body["text"] = "Citrix is reserved now by <@%s>. Please wait!" % STATUS["reserver"]
    else:
        STATUS["reserved"] = True
        STATUS["reserver"] = who
        body["text"] = "Citrix is yours. Please dont forget to free it when you are done!"

        global AFK_TIMER
        AFK_TIMER = Timer(10, notify)
        AFK_TIMER.start()

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def free(who):
    body = {"text": None, "response_type": "in_channel"}

    if not STATUS["reserved"]:
        body["text"] = "Citrix is free. Please reserve before using!"

    if who != STATUS["reserver"]:
        body["text"] = "Citrix is reserved now by <@%s>. Ask him to free it!" % STATUS["reserver"]
    else:
        STATUS["reserved"] = False
        STATUS["reserver"] = None
        body["text"] = "Citrix is free now!"

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def force_free():
    STATUS["reserved"] = False
    STATUS["reserver"] = None

def notify():
    body = {"text": "You have reserved RIL access 1 hour ago.",
            "attachments": json.dumps([{
                "attachment_type": "default",
                "callback_id": "usage_check",
                "text": "Do you need it still?",
                "actions":[
                    {"name": "ack",
                     "type": "button",
                     "text": "I still need it!",
                     "value": "ack"},
                    {"name": "deny",
                     "type": "button",
                     "text": "I don't need it anymore!",
                     "value": "deny"}
                ]
            }]),
            "as_user": "true",
            "response_type": "in_channel",
            "channel": "U03MW7287",
            "token": BOT_TOKEN}
    url = "https://slack.com/api/chat.postMessage"

    resp = requests.post(url, data=body, headers={"acccept": "application/json"})

    global NOTIFICATION_AFK_TIMER
    NOTIFICATION_AFK_TIMER = Timer(10, force_free)
    NOTIFICATION_AFK_TIMER.start()


def ack_usage():
    pass


def deny_usage():
    force_free()
    NOTIFICATION_AFK_TIMER.cancell()


if __name__ == "__main__":
    main()
