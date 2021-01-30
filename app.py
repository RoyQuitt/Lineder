from __future__ import print_function

import datetime
# Python standard libraries
import json
import os.path
import random
import sqlite3
from datetime import datetime

# Third-party libraries
# import base32hex
import flask
import requests
from flask import Flask, redirect, request, url_for
from flask_cors import CORS
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
import Lineder_logging

# from quickstart import main as flow_main
import quickstart
from classes.Event import MyEvent as dbEvent
# Internal imports
from db import init_db_command
from dbUser import MyUser as DbUser
from freebusy_range import Freebusy as Range
from user import User

my_logger = Lineder_logging.get_logger ("App")
my_logger.debug ("Starting Logging")

# My custom classes
# from classes.Users import Users
# from classes.User import MyUser
# from classes.Event import MyEvent


# class MyEvent:
#     def __init__(self, title, start, end):
#         self.end = end
#         self.start = start
#         self.title = title
#
#
# class MyUser:
#     def __init__(self, username, event_list):
#         self.username = username
#         self.event_list: List[Event] = event_list
#
#     def insert_new_event(self, new_event: MyEvent):
#         self.event_list.append(new_event)
#
#     def set_event_list(self, new_event_list):
#         self.event_list = new_event_list
#
#     def get_event_by_title(self, title):
#         for event in self.event_list:
#             if event.title == title:
#                 return event
#         return None
#
#
# class Users:
#     def __init__(self, user_list):
#         self.user_list = user_list
#
#     def get_user_by_username(self, username: str) -> MyUser:
#         for user in self.user_list:
#             if user.username == username:
#                 return user
#         return None
#
#     def insert_new_user(self, new_user: MyUser):
#         # if not self.user_list:  # check if first item in the list is '[]'
#         # if so, insert the user into that spot
#         #     self.user_list[0] = new_user
#         if new_user not in self.user_list:
#             self.user_list.append(new_user)
#
#     def update_user_event_list(self, username, new_event_list):  # : List[Event]
#         for user in self.user_list:
#             if user.username == username:
#                 pass
#             else:
#                 return None
#         for user in self.user_list:
#             if user.username == username:
#                 user.event_list = new_event_list

HEX32_MAX = 111111111

# Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Google API Credentials
# The client ID created for the app in the Google Developers Console
# with the google-signin-client_id meta element
# GOOGLE_CLIENT_ID = "701150580333-9lqf3ot4ptha6k80j942km8l5pq5hd2s.apps.googleusercontent.com"
# GOOGLE_CLIENT_SECRET = "CnWxlsvrnLi9Wbmdk2Txb6ES"
GOOGLE_CLIENT_ID = os.environ.get ("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get ("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google"
    ".com/.well-known/openid-configuration"
)

# In memory DB initialization
# users = Users([])


# Flask app setup
app = Flask (__name__)
app.config['supports_credentials'] = True
cors = CORS (app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
app.secret_key = os.environ.get ("SECRET_KEY") or os.urandom (24)

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager ()
login_manager.init_app (app)
# Naive database setup
try:
    init_db_command ()
    # db = get_db()
    # db.execute("DROP TABLE myUser")
    # db.execute("DROP TABLE events")
    # db.execute("DROP TABLE freebusy")
    my_logger.debug ("dropped all")
except sqlite3.OperationalError:
    # Assume it's already been created
    pass

# OAuth 2 client setup
my_logger.debug (GOOGLE_CLIENT_ID)
my_logger.debug (GOOGLE_CLIENT_SECRET)
client = WebApplicationClient (GOOGLE_CLIENT_ID)


class Event:
    def __init__ (self, title, start, end):
        self.start = start
        self.end = end
        self.title = title

    def __repr__ (self):
        return str (self.start) + "  -  " + str (self.end) + "   |   " + str (self.title)

    def make_json (self):
        # return "title:" + str(self.title) + ", \n" + "start:"
        return str (flask.jsonify (
            title=self.title,
            start=self.start,
            end=self.end
        ))

    def serialize (self):
        """
This is where the JSON magic happens.
This is the dictionary that specifies how to serialized the class.
        :return:
        """
        return {
            'title': self.title,
            'start': self.start,
            'end': self.end
        }


class EventsList:
    def __init__ (self, events):
        self.events_list = events
        self.events_list_arranged = []
        self.events_list_json = []

    def __repr__ (self):
        s = ""
        for i, event in enumerate (self.events_list_arranged):
            s += event.__repr__ () + ", "
        return s

    def make_json (self):
        # return json.dumps(self.events_list_arranged)
        for event in self.events_list_arranged:
            self.events_list_json.append (event.make_json ())
        return flask.jsonify (
            events=self.events_list_json
        )

    def arrange_events (self, owner_id):
        if not self.events_list:
            my_logger.debug ('No upcoming events found.')

        for i, event in enumerate (self.events_list):
            event_id = event['id']
            start = event['start'].get ('dateTime', event['start'].get ('date'))
            end = event['end'].get ('dateTime', event['start'].get ('date'))
            title = event['summary']
            new_evnt = dbEvent (event_id, owner_id, title, start, end)
            my_logger.debug ("\nevent number:", i)
            my_logger.debug (new_evnt)
            self.events_list_arranged.append (new_evnt)
            # print(start, " - ", end, " | ", event['summary'])
        my_logger.debug ("\n\nevents list arranged in arrange_events:\n" + self.__repr__ ())


# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user (user_id):  # actually gets email instead of id
    user_address = user_id
    user_id = DbUser.get_id_by_email (user_address)
    return DbUser.get (user_id)


@app.route ("/json_test")
def json_test ():
    return flask.jsonify (
        redirect_url="hello",
        code=302
    )


@app.route ("/")
def index ():
    if current_user.is_authenticated:
        return (
            "<p>Hello, {}! You're logged in! Email: {}</p>"
            "<div><p>Google Profile Picture:</p>"
            '<img src="{}" alt="Google profile pic"></img></div>'
            '<div><a class="button" href="/getEvents">Get Events</a></div>'
            '<div><p></p></div>'
            '<a class="button" href="/logout">Logout</a>'.format (
                current_user.name, current_user.email, current_user.profile_pic
            )
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'


def get_google_provider_cfg ():
    return requests.get (GOOGLE_DISCOVERY_URL).json ()


@app.route ("/getEvents")
@login_required
def get_events ():
    now = datetime.datetime.utcnow ().isoformat () + 'Z'  # 'Z' indicates UTC time
    url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults=5&timeMin=' + now
    req = requests.Session ()
    print (client.token)
    token = client.token.get ("access_token")
    print (token)
    req = requests.get (url, headers={'Authorization': 'Bearer %s' % token}, data=None)
    print ("\nresponse:", req.text)
    with open ("sample.txt", "w", encoding="utf-8") as text_file:
        text_file.write (req.text)
    return redirect (url_for ("index"))


@app.route ("/login")  # arrow 1
def login_flow ():
    """
    login_flow starts the login process and then redirects the user to the next stage by sending a 302 redirect
    response with the URL received from quickstart
    :return:
        The redirect response
    """
    token, creds, url = quickstart.until_url ()  # arrow 2 + 3
    print (url)
    print ("creds in login:", creds)
    # return url
    return redirect (url, code=302)  # arrow 4 + 5


""" Original 'login' code """


def login ():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg ()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri (
        authorization_endpoint,
        redirect_uri=request.base_url + "/new_callback",
        scope=["openid", "email", "profile", 'https://www.googleapis.com/auth/calendar.readonly'],
    )
    return redirect (request_uri)


# @app.route("/login/callback", methods=['OPTIONS'])
# def deal_with_options_request():
#     if request.method == 'OPTIONS':
#         print("sent 200 OK")
#         resp = jsonify(success=True, status_code=200)
#         print(resp)
#         # return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
#         return resp

# @app.route(methods=['OPTIONS'])
# def deal_with_options_request():
#     return 201, {'Access-Control-Allow-Origin': '*'}


@app.after_request
def after_request (response):
    response.headers.add ('Access-Control-Allow-Origin', 'http://localhost:4200')
    # response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Access-Control-Allow-Origin')
    response.headers.add ('Access-Control-Allow-Headers', '*')
    response.headers.add ('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add ('Access-Control-Allow-Credentials', 'true')
    return response
    # return response


# @app.after_request
# def after_request(response):
#     response.headers.add('Access-Control-Allow-Origin', '*')
#     response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
#     response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
#     return response


@app.route ("/login/callback")
def callback ():
    """
    Callback is being called by Google API when the user is authenticated. Once the user is authenticated,
    it arranges the events and created the JSON response with the list of events
    """
    # global users
    print ("CALLBACK")
    after_url_events, user_address = quickstart.after_url ()  # get user events + email address
    events_list = EventsList (after_url_events)  # creds, token
    events_list.arrange_events ()
    # print(len(events_list.events_list_arranged))
    final_events = events_list.events_list_arranged

    print ("\nResponse:\n", final_events)
    user = MyUser (user_address, final_events)

    res = flask.jsonify (
        events=[event.serialize () for event in user.event_list]
    )
    print ("\nuser events:", user.event_list)
    # set a cookie with the username so that we can use it later in the 'new_event' endpoint
    res.set_cookie ('user_address', user.username)
    users.insert_new_user (user)
    # print(res)
    return res


@app.route ("/show_cookie")
def show_cookie ():
    # return "hello"
    username = flask.request.cookies.get ('user_address')
    res = flask.jsonify (username=username)
    print (username)
    return res


# http://127.0.0.1:5000/new_event?title=text&start=1000&end=1100
# @app.route("/new_event")  # , methods=['POST']
def add_new_event ():
    # global users
    username = flask.request.cookies.get ('user_address')
    if not username:
        print ("Username Not Found")
        return flask.jsonify (success=False)
    print (username)
    params = flask.request.args
    title = params.get ('title')
    start = params.get ('start')
    end = params.get ('end')
    new_event = Event (title, start, end)
    print ("\nNEW EVENT ADDED:", new_event)
    my_current_user = users.get_user_by_username (username)
    my_current_user.insert_new_event (new_event)
    # print(users)
    print ("\nmy events:", my_current_user.event_list)
    return flask.jsonify (success=True)


@app.route ("/login/new_callback")
def ranges_callback ():
    freebusy, user_address = quickstart.after_url ()
    cUser = DbUser (user_address)  # current user
    print ("cUser after constructor:")
    print (cUser)
    cUser.id = DbUser.get_id_by_email (user_address)
    print ("user.id in callback:", cUser.id)
    if not cUser.id:
        cUser_id = DbUser.create (cUser.email)
    # Begin user session by logging the user in
    login_user (cUser)
    print ("\nUser:", user_address)
    print (freebusy)
    for range in freebusy:
        Range.create_range (current_user.id, range['start'], range['end'])
    res = flask.jsonify (freebusy=freebusy)
    return res


# @app.route("/login/new_callback")
def new_callback ():
    print ("NEW CALLBACK")
    # Get authorization code Google sent back to you
    code = request.args.get ("code")
    print ("code:", code)
    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg ()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request (
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post (
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )
    # Parse the tokens!
    client.parse_request_body_response (json.dumps (token_response.json ()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token (userinfo_endpoint)
    userinfo_response = requests.get (uri, headers=headers, data=body)
    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json ().get ("email_verified"):
        unique_id = userinfo_response.json ()["sub"]
        users_email = userinfo_response.json ()["email"]
        picture = userinfo_response.json ()["picture"]
        users_name = userinfo_response.json ()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    # Create a user in your db with the information provided
    # by Google
    user = User (
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )
    # Doesn't exist? Add it to the database.
    if not User.get (unique_id):
        User.create (unique_id, users_name, users_email, picture)
    # Begin user session by logging the user in
    login_user (user)

    # Get the user's calendar events (same as the userinfo but with a different endpoint)
    # Get user events + gmail address
    after_url_events, user_address = quickstart.after_url ()
    with open ("sample.txt", "w", encoding="utf-8") as text_file:
        text_file.write (str (after_url_events))
    c_user = DbUser (user_address)  # current user
    if not c_user.get ():
        c_user.create ()
    # Begin user session by logging the user in
    login_user (c_user)
    events = EventsList (after_url_events)
    events.arrange_events (user_address)
    final_events = events.events_list_arranged
    print ("FINAL EVENTS in new:\n", final_events)
    # Insert new events to db
    for event in final_events:
        if not dbEvent.get_event (event.event_id):
            dbEvent.create (event.event_id, current_user.id, event.title, event.start, event.end)
    #  construct response
    res = flask.jsonify (
        events=[event.serialize () for event in final_events]
    )
    return res
    # google_calendar_endpoint = SCOPES
    # uri, headers, body = client.add_token(google_calendar_endpoint)
    # calendar_response = requests.get(uri, headers=headers, data=body)
    # events_list = EventsList(calendar_response)  # creds, token
    # events_list.arrange_events()
    # # print(len(events_list.events_list_arranged))
    # final_events = events_list.events_list_arranged

# /new_range?start=1985-04-12T23:20:50.52Z&end=1985-05-12T23:20:50.52Z
# from 12.04.1985, 23:20:50.52 until 12.05.1985, 23:20:50.52
@app.route ("/new_range")
@login_required
def new_range ():
    params = flask.request.args
    start = params.get ('start')
    end = params.get ('end')
    owner_id = DbUser.get_id_by_email (current_user.email)
    # owner_id = current_user.id
    success = Range.create_range (owner_id, start, end)
    res = flask.jsonify (success=success)
    return res


# def randomize_new_event_id ():
#     # generate a random string in base32hex similar to the google unique event ID
#     s = base32hex.b32encode (random.randint (HEX32_MAX))
#     while dbEvent.get_event (s):
#         s = base32hex.b32encode (random.randint (HEX32_MAX))
#     return s


@app.route ("/get_user_schedule")
def get_user_schedule ():
    """
Retrieve the availability of the user
return value is JSON
    @rtype: object
    """
    params = flask.request.args
    user_address = params.get ('user_address')
    print ("User address in new:", user_address)
    user_ranges = DbUser.get_user_ranges (user_address)
    print ("type of start:", type (user_ranges[1]))
    # final_ranges = (user_ranges[1], user_ranges[2])
    is_available = DbUser.is_available (user_address)
    next_available = DbUser.next_available (user_address)
    res = flask.jsonify (
        ranges=user_ranges,
        is_available=is_available,
        next_available=next_available
    )
    return res


@app.route ("/logout")
@login_required
def logout ():
    logout_user ()
    return redirect (url_for ("index"))


if __name__ == "__main__":
    # app.run(host="10.50.1.146")
    app.run (ssl_context="adhoc", host="10.50.1.149")

# TODO:
#   getting events using browser:
#       flow - start_response = 127
#       flow - host = localhost
#       app - HTTPS, host = none
#   .
#   best android:
#       app - HTTP, host = 10.50.1.146
#       flow - host = localhost
#       flow - start_response = 127 / 10.50.1.146
#   .
#   ERORR
#       app - HTTP, host = 10.50.1.146
#       flow - host = 10.50.1.146
#       flow - start_response = app.wechange.co.uk
