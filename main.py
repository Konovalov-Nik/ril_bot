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
        action = payload["actions"][0]
        action_id = action.get("action_id")
        user_id = payload["user"]["id"]

        if action_id == "account_reservation":
            raw_value = action["selected_option"]["value"]
            acc_id = int(raw_value[len("reserve_"):])
            channel_id = payload["container"]["channel_id"]

            return reserve(user_id, acc_id, channel_id)

        if "value" in action:
            ack_answer = action["value"]
            if ack_answer == "ack":
                return ack_usage(user_id)
            if ack_answer == "deny":
                return deny_usage(user_id)


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

def reserve(who, what, where):

    resp_text = "placeholder"

    user_has_reserved = False
    for acc in STATUS:
        if acc["reserver"] == who:
            user_has_reserved = True

    acc = get_acc_by_id(what)
    if user_has_reserved:
        resp_text = "You have already reserved an account."
    elif acc["reserved"]:
        resp_text = "Citrix %s is reserved now by <@%s>. Please wait!" % (acc["name"], acc["reserver"])
    else:
        acc["reserved"] = True
        acc["reserver"] = who
        resp_text = "Citrix %s is yours. Please dont forget to free it when you are done!" % acc["name"]

        acc["afk_timer"] = Timer(AFK_TIMEOUT, notify, args=(who, what))
        acc["afk_timer"].start()


    url = "https://slack.com/api/chat.postMessage"
    body = {
        "blocks":json.dumps([{
            "type": "section",
            "block_id": "reservation_response",
            "text": {
                "type": "mrkdwn",
                "text": resp_text
            }
        }]),
        "text": "",
        "as_user": "true",
        "response_type": "in_channel",
        "channel": where,
        "token": BOT_TOKEN
    }
    bot_response = requests.post(url, data=body, headers={"acccept": "application/json"})
    print(bot_response.text)

    resp = make_response("OK", 200)
    return resp

def free(who):
    body = {"text": None, "response_type": "in_channel"}

    found = False

    for acc in STATUS:
        if acc["reserver"] == who:
            acc["reserved"] = False
            acc["reserver"] = None
            body["text"] = "Citrix is free now!"

            if acc["afk_timer"].is_alive():
                acc["afk_timer"].cancel()
            if acc["notification_afk_timer"].is_alive():
                 acc["notification_afk_timer"].cancel()

            found = True
            break

    if not found:
        body["text"] = "You have no reservations"

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def force_free(what):
    acc = get_acc_by_id(what)

    acc["reserved"] = False
    acc["reserver"] = None

def notify(who, what):
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
            "channel": who,
            "token": BOT_TOKEN}
    url = "https://slack.com/api/chat.postMessage"

    resp = requests.post(url, data=body, headers={"acccept": "application/json"})

    acc = get_acc_by_id(what)
    acc["notification_afk_timer"] = Timer(NOTIFICATION_AFK_TIMEOUT, force_free, args=(what,))
    acc["notification_afk_timer"].start()

def request_reservation():

    body = {"blocks":[
    {
        "type": "section",
        "block_id": "header",
        "text": {
            "type": "plain_text",
            "text": "Choose account"
        }
    },
    {
        "type": "section",
        "block_id": "acc_pick_section",
        "text": {
            "type": "plain_text",
            "text": "There are %s accounts in the pool" % len(STATUS)
        },
        "accessory": {
            "action_id": "account_reservation",
            "type": "static_select",
            "confirm": {
                "title": {
                    "type": "plain_text",
                    "text": "Confirm"
                    },
                "text": {
                    "type": "plain_text",
                    "text": "Plese confirm"
                },
                "confirm": {
                    "type": "plain_text",
                    "text": "OK"
                },
                "deny": {
                    "type": "plain_text",
                    "text": "I've changed my mind!"
                }
            },
            "placeholder": {
                "type": "plain_text",
                "text": "..."
            },
            "options": []
        }
    }]}

    for acc in STATUS:
        option = {
            "text": {
                "type": "plain_text",
                "text": acc["name"]
            },
            "value": "reserve_%s" % acc["id"]
        }
        body["blocks"][1]["accessory"]["options"].append(option)


    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp


def ack_usage(who):
    acc = get_acc_by_reserver(who)

    if acc["notification_afk_timer"].is_alive() and acc["reserver"] == who:
        acc["notification_afk_timer"].cancel()

        acc["afk_timer"] = Timer(AFK_TIMEOUT, notify, args=(who, acc["id"]))
        acc["afk_timer"].start()

        body = {"text": "OK! It's yours!", "response_type": "in_channel"}

    else:
        body = {"text": "Sorry, too late. Reserve again if it's free.", "response_type": "in_channel"}

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def deny_usage(who):
    acc = get_acc_by_reserver(who)
    if acc["notification_afk_timer"].is_alive() and acc["reserver"] == who:
        force_free(acc["id"])
        acc["notification_afk_timer"].cancel()

        body = {"text": "OK! It's free now!", "response_type": "in_channel"}
    else:
        body = {"text": "OK! But too late :)", "response_type": "in_channel"}

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp


def get_acc_by_id(_id):
    for acc in STATUS:
        if acc["id"] == _id:
            return acc


def get_acc_by_reserver(who):
    for acc in STATUS:
        if acc["reserver"] == who:
            return acc


if __name__ == "__main__":
    main()
