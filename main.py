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


STATUS = [
    {"name": "Shrinivas.Mira", "id": 1, "reserved": False, "reserver": None, "reserved_at": None,
     "afk_timer": Timer(0, lambda x: x), "notification_afk_timer": Timer(0, lambda x: x)},
    {"name": "Sachin.Tripathi", "id": 2, "reserved": False, "reserver": None, "reserved_at": None,
     "afk_timer": Timer(0, lambda x: x), "notification_afk_timer": Timer(0, lambda x: x)}
]

APP = Flask(__name__)
BOT_TOKEN = None

AFK_TIMEOUT = 60 * 60 # 1hour
NOTIFICATION_AFK_TIMEOUT = 5 * 60 # 5 min

def main():
    global BOT_TOKEN
    BOT_TOKEN = os.environ.get("BOT_TOKEN", None)
    if BOT_TOKEN is None:
        exit(1)

    http_server = WSGIServer(('', 5000), APP)
    http_server.serve_forever()

@APP.route("/bot", methods=['POST'])
def endpoint():
    print (request.form)
    if "payload" in request.form:
        # handling form responses
        payload = json.loads(request.form["payload"])
        answer = payload["actions"][0]["value"]
        user_id = payload["user"]["id"]
        if answer == "ack":
            return ack_usage(user_id)
        if answer == "deny":
            return deny_usage(user_id)
        if "reserve" in answer:
            acc_id = answer[:len("reserve_")]
            return reserve(user_id, acc_id)


    # simple requests
    if request.form['text'] == "check":
        return check()
    if request.form['text'] == "reserve":
        return request_reservation()
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
    body = {"text": "", "response_type": "in_channel"}

    for acc in STATUS:
        if acc["reserved"]:
            acc_status = "Citrix %s is reserved now by <@%s>. Please wait!" % (acc["name"], acc["reserver"])
        else:
            acc_status = "Citrix %s is free. Please reserve before using!" % acc["name"]
        body["text"] += acc_status
        body["text"] += "\n"

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def reserve(who, what):
    body = {"text": None, "response_type": "in_channel"}

    if STATUS["reserved"]:
        body["text"] = "Citrix is reserved now by <@%s>. Please wait!" % STATUS["reserver"]
    else:
        STATUS["reserved"] = True
        STATUS["reserver"] = who
        body["text"] = "Citrix is yours. Please dont forget to free it when you are done!"

        global AFK_TIMER
        AFK_TIMER = Timer(AFK_TIMEOUT, notify)
        AFK_TIMER.start()

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def free(who, what):
    body = {"text": None, "response_type": "in_channel"}

    if not STATUS["reserved"]:
        body["text"] = "Citrix is free. Please reserve before using!"

    if who != STATUS["reserver"]:
        body["text"] = "Citrix is reserved now by <@%s>. Ask him to free it!" % STATUS["reserver"]
    else:
        STATUS["reserved"] = False
        STATUS["reserver"] = None
        body["text"] = "Citrix is free now!"

        if AFK_TIMER.is_alive():
            AFK_TIMER.cancel()
        if NOTIFICATION_AFK_TIMER.is_alive():
             NOTIFICATION_AFK_TIMER.cancel()

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def force_free(what):
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
            "channel": STATUS["reserver"],
            "token": BOT_TOKEN}
    url = "https://slack.com/api/chat.postMessage"

    resp = requests.post(url, data=body, headers={"acccept": "application/json"})

    global NOTIFICATION_AFK_TIMER
    NOTIFICATION_AFK_TIMER = Timer(NOTIFICATION_AFK_TIMEOUT, force_free)
    NOTIFICATION_AFK_TIMER.start()

def request_reservation():

    body = {"text": "Choose which one whould you like to take.",
            "attachments": ""}

    attachments = [{
        "text": {
            "type": "plain_text",
            "text": "Select account"
        },
        "accessory": {
            "action_id": "reservaion_request",
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": "..."
            },
            "options": []
        }
    }]

    for acc in STATUS:
        option = {
            "text": {
                "type": "plain_text",
                "text": acc["name"]
            },
            "value": "reserve_%s" % acc["id"]
        }
        attachments[0]["accessory"]["options"].append(option)
    body["attachments"] = json.dumps(attachments)


    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp


def ack_usage(who, what):
    if NOTIFICATION_AFK_TIMER.is_alive() and STATUS["reserver"] == who:
        NOTIFICATION_AFK_TIMER.cancel()

        global AFK_TIMER
        AFK_TIMER = Timer(AFK_TIMEOUT, notify)
        AFK_TIMER.start()

        body = {"text": "OK! It's yours!", "response_type": "in_channel"}

    else:
        body = {"text": "Sorry, too late. Reserve again if it's free.", "response_type": "in_channel"}

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def deny_usage(who, what):
    if NOTIFICATION_AFK_TIMER.is_alive() and STATUS["reserver"] == who:
        force_free()
        NOTIFICATION_AFK_TIMER.cancel()

        body = {"text": "OK! It's free now!", "response_type": "in_channel"}
    else:
        body = {"text": "OK! But too late :)", "response_type": "in_channel"}

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp


if __name__ == "__main__":
    main()
