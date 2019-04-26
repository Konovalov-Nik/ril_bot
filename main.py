from datetime import datetime
from flask import Flask
from flask import make_response
from flask import request
import json
from gevent.pywsgi import WSGIServer
import requests
import os


STATUS = {"reserved": False, "reserver": None, "reserved_at": None}
APP = Flask(__name__)
BOT_TOKEN = None


def main():
    global BOT_TOKEN
    BOT_TOKEN = os.environ.get("BOT_TOKEN", None)
    if BOT_TOKEN is None:
        exit(1)

    http_server = WSGIServer(('', 5000), APP)
    http_server.serve_forever()

@APP.route("/bot", methods=['POST'])
def endpoint():
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

def notify():
    body = {"text": "You have reserved RIL access 1 hour ago.",
            "attachemnts":[{
                "attachment_type": "default",
                "callback_id": "usage_check",
                "actions":[
                    {"name": "ack",
                     "tesxt": "I still need it!",
                     "value": "ack"},
                    {"name": "deny",
                     "tesxt": "I don't need it anymore!",
                     "value": "deny"},
                ]
            }],
            "as_user": "true",
            "channel": "U03MW7287",
            "token": BOT_TOKEN}
    url = "https://slack.com/api/chat.postMessage"

    resp = requests.post(url, data=body, headers={"acccept": "application/json"})

    return make_response("OK", 200)


def ack_usage():
    pass


def deny_usage():
    pass


if __name__ == "__main__":
    main()
