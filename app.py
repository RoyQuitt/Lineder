from __future__ import print_function

# Python standard libraries
import json
import os
import sqlite3
import flask
from flask_cors import CORS

# Third-party libraries
from flask import Flask, redirect, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
import requests

# Internal imports
from db import init_db_command
from user import User

from googleapiclient.discovery import build
import google_auth_oauthlib.helpers


import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import base64

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# from quickstart import main as flow_main
import quickstart


# Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

GOOGLE_CLIENT_ID = "701150580333-9lqf3ot4ptha6k80j942km8l5pq5hd2s.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "CnWxlsvrnLi9Wbmdk2Txb6ES"
# GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
# GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)


# Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)

# Naive database setup
try:
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    pass

# OAuth 2 client setup
print(GOOGLE_CLIENT_ID)
print(GOOGLE_CLIENT_SECRET)
client = WebApplicationClient(GOOGLE_CLIENT_ID)


class Event:
    def __init__(self, start, end, title):
        self.start = start
        self.end = end
        self.title = title

    def __repr__(self):
        return str(self.start) + "  -  " + str(self.end) + "   |   " + str(self.title)

    def make_json(self):
        # return "title:" + str(self.title) + ", \n" + "start:"
        return str(flask.jsonify(
            title=self.title,
            start=self.start,
            end=self.end
        ))

    def serialize(self):
        return {
            'title':self.title,
            'start':self.start,
            'end':self.end
        }


class EventsList:
    def __init__(self, events):
        self.events_list = events
        self.events_list_arranged = []
        self.events_list_json = []

    def __repr__(self):
        s = ""
        for i, event in enumerate(self.events_list_arranged):
            s += event.__repr__() + ", "
        return s

    def make_json(self):
        # return json.dumps(self.events_list_arranged)
        for event in self.events_list_arranged:
            self.events_list_json.append(event.make_json())
        return flask.jsonify(
            events=self.events_list_json
        )





    def arrange_events(self):
        if not self.events_list:
            print('No upcoming events found.')
        for i, event in enumerate(self.events_list):
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['start'].get('date'))
            title = event['summary']
            new_event = Event(start, end, title)
            print("\nevent number:", i)
            print(new_event)
            self.events_list_arranged.append(new_event)
            # print(start, " - ", end, " | ", event['summary'])
        print("\n\nevents list arranged in arrange_events:\n" + self.__repr__())


# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)



@app.route("/json_test")
def json_test():
    return flask.jsonify(

    )


@app.route("/")
def index():
    # return flask.jsonify(
    #     name="Roy Quitt",
    #     email="roy.quitt@gmail.com",
    #     pic="https://lh3.googleusercontent.com/a-/AOh14GhoZiEKa6_e6IN1qiK9MUJWXRyFvQp-QUEIjl6BDA"
    # )
    if current_user.is_authenticated:
        # return flask.jsonify(
        #     name=current_user.name,
        #     email=current_user.email,
        #     pic=current_user.profile_pic
        # )
        return (
            "<p>Hello, {}! You're logged in! Email: {}</p>"
            "<div><p>Google Profile Picture:</p>"
            '<img src="{}" alt="Google profile pic"></img></div>'
            '<div><a class="button" href="/getEvents">Get Events</a></div>'
            '<div><p></p></div>'
            '<a class="button" href="/logout">Logout</a>'.format(
                current_user.name, current_user.email, current_user.profile_pic
            )
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


@app.route("/getEvents")
@login_required
def get_events():
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults=5&timeMin=' + now
    req = requests.Session()
    print(client.token)
    token = client.token.get("access_token")
    print(token)
    req = requests.get(url, headers={'Authorization': 'Bearer %s' % token}, data=None)
    print("\nresponse:", req.text)
    with open("sample.txt", "w", encoding="utf-8") as text_file:
        text_file.write(req.text)
    return redirect(url_for("index"))


@app.route("/login")  # arrow 1
def login_flow():
    # global token
    # global creds
    token, creds, url = quickstart.until_url()  # arrow 2 + 3
    print(url)
    print("creds in login:", creds)
    return redirect(url, code=302)  # arrow 4 + 5
    # quickstart.after_url(creds, token)


# def login():
#     # Find out what URL to hit for Google login
#     google_provider_cfg = get_google_provider_cfg()
#     authorization_endpoint = google_provider_cfg["authorization_endpoint"]
#     # Use library to construct the request for Google login and provide
#     # scopes that let you retrieve user's profile from Google
#     request_uri = client.prepare_request_uri(
#         authorization_endpoint,
#         redirect_uri=request.base_url + "/callback",
#         scope=["openid", "email", "profile", 'https://www.googleapis.com/auth/calendar.readonly'],
#     )
#     return redirect(request_uri)


@app.route("/login/callback")
def callback():
    # global token
    # global creds
    print("CALLBACK")
    events_list = EventsList(quickstart.after_url())  # creds, token
    events_list.arrange_events()
    print("\n\nevents list arranged in callback:\n" + events_list.__repr__())
    print(events_list.make_json())
    # print("events:\n", events_list)
    # if not events:
    #     print('No upcoming events found.')
    # for event in events:
    #     start = event['start'].get('dateTime', event['start'].get('date'))
    #     end = event['end'].get('dateTime', event['start'].get('date'))
    #     print(start, " - ", end, " | ", event['summary'])
    # # Get authorization code Google sent back to you
    # code = request.args.get("code")
    #
    # # Find out what URL to hit to get tokens that allow you to ask for
    # # things on behalf of a user
    # google_provider_cfg = get_google_provider_cfg()
    # token_endpoint = google_provider_cfg["token_endpoint"]
    #
    # # Prepare and send a request to get tokens! Yay tokens!
    # token_url, headers, body = client.prepare_token_request(
    #     token_endpoint,
    #     authorization_response=request.url,
    #     redirect_url=request.base_url,
    #     code=code
    # )
    # token_response = requests.post(
    #     token_url,
    #     headers=headers,
    #     data=body,
    #     auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    # )
    # print("token type:", type(token_response))
    # # Parse the tokens!
    # print(token_response)
    # client.parse_request_body_response(json.dumps(token_response.json()))
    # # client.token
    # print(token_response)
    # # Now that you have tokens (yay) let's find and hit the URL
    # # from Google that gives you the user's profile information,
    # # including their Google profile image and email
    # userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    # uri, headers, body = client.add_token(userinfo_endpoint)
    # print("headers:", headers, "\nbody:", body)
    # userinfo_response = requests.get(uri, headers=headers, data=body)
    # # url = 'https://www.googleapis.com/calendar/v3/users/me/calendarList'
    # # events_response = requests.post(url, headers={"authorization":})
    #
    # # You want to make sure their email is verified.
    # # The user authenticated with Google, authorized your
    # # app, and now you've verified their email through Google!
    # print("test:\n")
    # print(type(userinfo_response))
    # print(userinfo_response.json())
    # if userinfo_response.json().get("email_verified"):
    #     unique_id = userinfo_response.json()["sub"]
    #     users_email = userinfo_response.json()["email"]
    #     picture = userinfo_response.json()["picture"]
    #     users_name = userinfo_response.json()["given_name"]
    # else:
    #     return "User email not available or not verified by Google.", 400
    # ------------- start Get Events -------------



    # Create a user in your db with the information provided
    # by Google
    # user = User(
    #     id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    # )
    #
    # # Doesn't exist? Add it to the database.
    # if not User.get(unique_id):
    #     User.create(unique_id, users_name, users_email, picture)
    #
    # # Begin user session by logging the user in
    # login_user(user)

    # Send user back to homepage
    # return (events_list.events_list_arranged[0]).make_json()
    # return events_list.make_json()
    # return redirect(url_for("index"))
    return flask.jsonify(
        events=[event.serialize() for event in events_list.events_list_arranged]
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


if __name__ == "__main__":
    # app.run(host="10.50.1.146")
    # app.run()
    app.run(ssl_context="adhoc")
