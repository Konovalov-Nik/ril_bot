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

@APP.route("/check")
def check():
    body = {"text": None}

    if STATUS["reserved"]:
        body["text"] = "Room is reserved now. Please wait!"
    else:
        body["text"] = "Room is free. Please reserve before using!"

    resp = make_response(json.dumps(body), 200)
    resp.headers["Content-type"] = "application/json"

    return resp

def reserve(reserver):
    pass

if __name__ == "__main__":
    main()
