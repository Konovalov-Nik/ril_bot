from flask import Flask
from flask import make_response
from flask import request
import json
from gevent.pywsgi import WSGIServer
import requests

STATUS = {"reserved": False, "reserver": None, "expires_at": None}
APP = Flask(__name__)

def main():
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

    return help()

def help():
    body = {"text": """
check - Check if Citrix is free now
reseve - Reserve for yourself
free - Cancel your reservation
"""}

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def check():
    body = {"text": None}

    if STATUS["reserved"]:
        body["text"] = "Citrix is reserved now by <@%s>. Please wait!" % STATUS["reserver"]
    else:
        body["text"] = "Citrix is free. Please reserve before using!"

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def reserve(who):
    body = {"text": None}

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
    body = {"text": None}

    if !STATUS["reserved"]:
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


if __name__ == "__main__":
    main()
