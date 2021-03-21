from __future__ import print_function

import datetime
from datetime import timezone, timedelta
# Python standard libraries
import json
import os.path
import random
import sqlite3
from datetime import datetime, time

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
from session_managment import SessionManagement, Unauthorized
import OneSignalConfig
from db import init_db_command, get_db
from dbUser import MyUser as DbUser
from freebusy_range import Freebusy as Range
from freebusy_range import TZ_DELTA, LOCAL_TIME_ZONE
from user import User
from ques import Ques

WAITER_ADDRESS_HTTP_PARAM_NAME = 'waiter_address'
SESSION_ID_HTTP_PARAM_NAME = 'session_id'

session = SessionManagement ()

my_logger = Lineder_logging.get_logger ("App")
my_logger.debug ("\n--------------------------- NEW ---------------------------\n")
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
    "https://accounts.google.com/.well-known/openid-configuration"
)

# In memory DB initialization
# users = Users([])


# Flask app setup
app = Flask (__name__)
app.config['supports_credentials'] = True
# app.config['SESSION_COOKIE_HTTPONLY'] = False
print ("app config:", app.config)
cors = CORS (app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
app.secret_key = os.environ.get ("SECRET_KEY") or os.urandom (24)
unauthorized_resp = None

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager ()
login_manager.init_app (app)
my_logger.debug("Going to initialize DB")
# Naive database setup
try:
    my_logger.debug("creating DB")
    init_db_command ()
    # db = get_db()
    #
    # db.execute("DROP TABLE MyUser")
    # db.execute("DROP TABLE Ques")
    # db.execute("DROP TABLE freebusy")
    # print("dropped all")
except sqlite3.OperationalError:
    # Assume it's already been created
    my_logger.debug("DB already created")

# OAuth 2 client setup
# print(GOOGLE_CLIENT_ID)
# print(GOOGLE_CLIENT_SECRET)
client = WebApplicationClient (GOOGLE_CLIENT_ID)


class Event:
    def __init__ (self, title, start, end):
        self.start = start
        self.end = end
        self.title = title

    def __repr__ (self):
        return str (self.start) + "  -  " + str (self.end) + "   |   " + str (self.title)

    def make_json (self):
        """
        Serializes the event as a JSON
        :return: the JSON in a string
        """
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
        """
        Represent the class as a string
        :return: 
        A string with a list of events
        """
        events_string: str = ""
        for i, event in enumerate (self.events_list_arranged):
            events_string += event.__repr__ () + ", "
        return events_string

    def make_json (self):
        # return json.dumps(self.events_list_arranged)
        for event in self.events_list_arranged:
            self.events_list_json.append (event.make_json ())
        return flask.jsonify (
            events=self.events_list_json
        )

    def arrange_events (self, owner_id):
        if not self.events_list:
            my_logger.debug('No upcoming events found.')

        for i, event in enumerate (self.events_list):
            event_id = event['id']
            start = event['start'].get ('dateTime', event['start'].get ('date'))
            end = event['end'].get ('dateTime', event['start'].get ('date'))
            title = event['summary']
            new_event = dbEvent (event_id, owner_id, title, start, end)
            print ("\nevent number:", i)
            print (new_event)
            self.events_list_arranged.append (new_event)
            # print(start, " - ", end, " | ", event['summary'])
        print ("\n\nevents list arranged in arrange_events:\n" + self.__repr__ ())


# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user (user_id):  # actually gets email instead of id
    # user_id = DbUser.get_id_by_email(user_address)
    my_logger.debug ("\nLOAD USER %s", DbUser.get (user_id))
    return DbUser.get (user_id)


@app.route ("/json_test")
def json_test ():
    return flask.jsonify (
        redirect_url="hello",
        code=302
    )


@app.route ("/")
def index ():
    global unauthorized_resp
    message = {'error': 'Unauthorized'}
    unauthorized_resp = flask.jsonify (message)
    unauthorized_resp.status_code = 401
    # if current_user.is_authenticated:
    #     return (
    #         "<p>Hello, {}! You're logged in! Email: {}</p>"
    #         "<div><p>Google Profile Picture:</p>"
    #         '<img src="{}" alt="Google profile pic"></img></div>'
    #         '<div><a class="button" href="/getEvents">Get Events</a></div>'
    #         '<div><p></p></div>'
    #         '<a class="button" href="/logout">Logout</a>'.format(
    #             current_user.name, current_user.email, current_user.profile_pic
    #         )
    #     )
    # else:
    #     return '<a class="button" href="/login">Google Login</a>'
    return redirect (url_for ("login_flow"))


def get_google_provider_cfg ():
    return requests.get (GOOGLE_DISCOVERY_URL).json ()


@app.route ("/getEvents")
@login_required
def get_events ():
    now = datetime.datetime.utcnow ().isoformat () + 'Z'  # 'Z' indicates UTC time
    url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults=5&timeMin=' + now
    req = requests.Session ()
    my_logger.debug (client.token)
    token = client.token.get ("access_token")
    my_logger.debug (token)
    req = requests.get (url, headers={'Authorization': 'Bearer %s' % token}, data=None)
    my_logger.debug ("\nresponse: %s", req.text)
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
    params = flask.request.args
    session_id = params.get (SESSION_ID_HTTP_PARAM_NAME)
    if not session_id:
        # TODO:
        # token, creds - not used below
        token, creds, url = quickstart.until_url ()
        return redirect (url, code=302)
    if session.is_logged_in (session_id):
        return "You are already logged in. You can close this window"
    token, creds, url = quickstart.until_url ()
    return redirect (url, code=302)  # arrow 4 + 5


# Original 'login' code
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
    my_logger.debug ("after request")
    response.headers.add ('Access-Control-Allow-Origin', '*')
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


# @app.route("/login/callback")
# def callback():
#     """
#     Callback is being called by Google API when the user is authenticated. Once the user is authenticated,
#     it arranges the events and created the JSON response with the list of events
#     """
#     global users
#     print("CALLBACK")
#     after_url_events, user_address = quickstart.after_url()  # get user events + email address
#     events_list = EventsList(after_url_events)  # creds, token
#     events_list.arrange_events()
#     # print(len(events_list.events_list_arranged))
#     final_events = events_list.events_list_arranged
#
#     print("\nResponse:\n", final_events)
#     user = MyUser(user_address, final_events)
#
#     res = flask.jsonify(
#         events=[event.serialize() for event in user.event_list]
#     )
#     print("\nuser events:", user.event_list)
#     # set a cookie with the username so that we can use it later in the 'new_event' endpoint
#     res.set_cookie('user_address', user.username)
#     users.insert_new_user(user)
#     # print(res)
#     return res


@app.route ("/show_cookie")
def show_cookie ():
    # return "hello"
    username = flask.request.cookies.get ('user_address')
    res = flask.jsonify (username=username)
    my_logger.debug (username)
    return res


# http://127.0.0.1:5000/new_event?title=text&start=1000&end=1100
# @app.route("/new_event")  # , methods=['POST']
# def add_new_event ():
#     # global users
#     username = flask.request.cookies.get ('user_address')
#     if not username:
#         print("Username Not Found")
#         return flask.jsonify(success=False)
#     print(username)
#     params = flask.request.args
#     title = params.get('title')
#     start = params.get('start')
#     end = params.get('end')
#     new_event = Event(title, start, end)
#     print("\nNEW EVENT ADDED:", new_event)
#     my_current_user = users.get_user_by_username(username)
#     my_current_user.insert_new_event(new_event)
#     # print(users)
#     print("\nmy events:", my_current_user.event_list)
#     return flask.jsonify(success=True)


@app.route ("/login/new_callback")
def ranges_callback ():
    # print("headers:", flask.request.headers)
    # phone = flask.request.args.get('phone')
    my_logger.debug ("ranges callback")
    freebusy, user_address, name, phone = quickstart.after_url ()
    cur_user = DbUser (user_address, name, phone)  # current user
    my_logger.debug ("cUser after constructor:")
    my_logger.debug (cur_user)
    cur_user.id = DbUser.get_id_by_email (user_address)
    my_logger.debug ("user.id in callback: %s", cur_user.id)
    if not cur_user.id:
        # TODO:
        # We are missing two parameters here for create: name and phone
        cUser_id = DbUser.create (cur_user.email)

    # Begin user session by logging the user in
    # login_user(cur_user)
    # logging in the user
    session_id = session.login_user (user_address)
    my_logger.debug (session.users_dict)
    my_logger.debug ("LOGGED IN NEW USER!")
    my_logger.debug ("email: %s", cur_user.email)
    my_logger.debug ("user_id: %s", cur_user.id)
    my_logger.debug ("\nUser: %s", user_address)
    my_logger.debug (freebusy)

    # Create the ranges in our database
    for c_range in freebusy:
        Range.create_range (cur_user.id, c_range['start'], c_range['end'])

    # Build the HTTP response
    res = flask.jsonify (freebusy=freebusy, name=name, phone=phone, session_id=session_id)
    my_logger.debug ("callback response: %s", res.get_data (as_text=True))
    return res


# @app.route("/login/og_callback")
# def og_callback():
#     my_logger.debug("OG CALLBACK")
#
#     # Get authorization code Google sent back to you
#     code = request.args.get("code")
#     my_logger.debug("code:", code)
#
#     # Find out what URL to hit to get tokens that allow you to ask for
#     # things on behalf of a user
#     google_provider_cfg = get_google_provider_cfg()
#     token_endpoint = google_provider_cfg["token_endpoint"]
#
#     # Prepare and send a request to get tokens! Yay tokens!
#     token_url, headers, body = client.prepare_token_request(
#         token_endpoint,
#         authorization_response=request.url,
#         redirect_url=request.base_url,
#         code=code
#     )
#     token_response = requests.post(
#         token_url,
#         headers=headers,
#         data=body,
#         auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
#     )
#     # Parse the tokens!
#     client.parse_request_body_response(json.dumps(token_response.json()))
#
#     # Now that you have tokens (yay) let's find and hit the URL
#     # from Google that gives you the user's profile information,
#     # including their Google profile image and email
#     userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
#     uri, headers, body = client.add_token (userinfo_endpoint)
#     userinfo_response = requests.get (uri, headers=headers, data=body)
#     # You want to make sure their email is verified.
#     # The user authenticated with Google, authorized your
#     # app, and now you've verified their email through Google!
#     if userinfo_response.json ().get ("email_verified"):
#         unique_id = userinfo_response.json ()["sub"]
#         users_email = userinfo_response.json ()["email"]
#         picture = userinfo_response.json ()["picture"]
#         users_name = userinfo_response.json ()["given_name"]
#     else:
#         return "User email not available or not verified by Google.", 400
#
#     # Create a user in your db with the information provided
#     # by Google
#     user = User(
#         id_=unique_id, name=users_name, email=users_email, profile_pic=picture
#     )
#     # Doesn't exist? Add it to the database.
#     if not User.get(unique_id):
#         User.create(unique_id, users_name, users_email, picture)
#     # Begin user session by logging the user in
#     login_user(user)
#
#     """ Get the user's calendar events (same as the userinfo but with a different endpoint) """
#     # Get user events + gmail address
#     after_url_events, user_address = quickstart.after_url ()
#     with open ("sample.txt", "w", encoding="utf-8") as text_file:
#         text_file.write (str (after_url_events))
#     c_user = DbUser (user_address)  # current user
#     if not c_user.get ():
#         c_user.create ()
#     # Begin user session by logging the user in
#     login_user (c_user)
#     events = EventsList (after_url_events)
#     events.arrange_events (user_address)
#     final_events = events.events_list_arranged
#     print("FINAL EVENTS in new:\n", final_events)
#     """ Insert new events to db """
#     for event in final_events:
#         if not dbEvent.get_event(event.event_id):
#             dbEvent.create(event.event_id, current_user.id, event.title, event.start, event.end)
#     #  construct response
#     res = flask.jsonify(
#         events=[event.serialize() for event in final_events]
#     )
#     return res
#     # google_calendar_endpoint = SCOPES
#     # uri, headers, body = client.add_token(google_calendar_endpoint)
#     # calendar_response = requests.get(uri, headers=headers, data=body)
#     # events_list = EventsList(calendar_response)  # creds, token
#     # events_list.arrange_events()
#     # # print(len(events_list.events_list_arranged))
#     # final_events = events_list.events_list_arranged


# @app.route("/new_event")
# # @login_required
# def new_event():
#     new_event_id = randomize_new_event_id()
#     params = flask.request.args
#     new_event = dbEvent(new_event_id, current_user.id, params.get('title'),
#                         params.get('start'), params.get('end'))
#     if not dbEvent.get_event(new_event.event_id):
#         dbEvent.create(new_event.event_id, current_user.id, new_event.title,
#                        new_event.start, new_event.end)
#     success = dbEvent.get_event(new_event.event_id)
#     res = flask.jsonify(success=success)
#     return res


@app.route ("/busy_for")
def busy_for ():
    params = flask.request.args
    session_id = params.get (SESSION_ID_HTTP_PARAM_NAME)
    try:
        owner_id = session.handle_user_user_id (session_id)
    except Unauthorized:
        return unauthorized_resp
    hours = int (params.get ('hours'))
    mins = int (params.get ('mins'))
    success = Range.busy_for (owner_id, hours, mins)
    res = flask.jsonify (success=success)
    return res


# /new_range?start=1985-04-12T23:20:50.52Z&end=1985-05-12T23:20:50.52Z
# from 12.04.1985, 23:20:50.52 until 12.05.1985, 23:20:50.52
@app.route ("/new_range")
# @login_required
def new_range ():
    params = flask.request.args
    session_id = params.get (SESSION_ID_HTTP_PARAM_NAME)
    try:
        owner_id = session.handle_user_user_id (session_id)
    except Unauthorized:
        return unauthorized_resp
    start: datetime = params.get ('start')
    end: datetime = params.get ('end')
    # owner_id = DbUser.get_id_by_email(current_user.email)
    # owner_id = DbUser.get_id_by_email("roy.quitt@googlemail.com")
    # owner_id = current_user.id
    # owner_address = session.get_address_by_session_id(session_id)
    # owner_id = DbUser.get_id_by_email(owner_address)
    print (start, end)
    now = datetime.now (tz=timezone (timedelta (hours=TZ_DELTA), LOCAL_TIME_ZONE))
    new_start: datetime = datetime.strptime (start, "%H:%M")
    final_start = datetime (now.year, now.month, now.day, new_start.hour, new_start.minute).isoformat () + 'Z'
    new_end: datetime = datetime.strptime (end, "%H:%M")
    final_end = datetime (now.year, now.month, now.day, new_end.hour, new_end.minute).isoformat () + 'Z'
    # final_start: datetime = datetime.strptime(start, "%H:%M %Y-%m-%dT%H:%M:%SZ")
    # final_end: datetime = datetime.strptime(end, "%H:%M %Y-%m-%dT%H:%M:%SZ")
    print (final_start, final_end)
    success = Range.create_range (owner_id, final_start, final_end)
    res = flask.jsonify (success=success)
    return res


# def randomize_new_event_id():
#     # generate a random string in base32hex similar to the google unique event ID
#     s = base32hex.b32encode(random.randint(HEX32_MAX))
#     while dbEvent.get_event(s):
#         s = base32hex.b32encode(random.randint(HEX32_MAX))
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
    print ("User address in get user schedule:" + user_address)
    try:
        user_ranges: list[tuple[datetime, datetime]] = DbUser.get_user_ranges (user_address)
    except TypeError:
        print ("type error")
        return flask.jsonify (error="type error")
    # print("type of start:", type(user_ranges[1]))
    is_available: bool = DbUser.is_available (user_address)
    next_available: datetime = DbUser.next_available (user_address)
    phone = DbUser.get_user_phone (user_address)
    name = DbUser.get_user_name (user_address)
    res = flask.jsonify (
        name=name,
        ranges=user_ranges,
        is_available=is_available,
        next_available=next_available,
        phone=phone
    )
    # Range.clean_db()
    # Range.print_table()
    return res


@app.route ("/join_que")
# @login_required
def join ():
    params = flask.request.args
    session_id = params.get (SESSION_ID_HTTP_PARAM_NAME)
    try:
        waiter_address = session.handle_user (session_id)
    except Unauthorized:
        return unauthorized_resp
    callee_address = params.get ('user_address')
    print ("adding", waiter_address, "to", callee_address + "'s que")
    place_in_line = Ques.create_que_item (callee_address, waiter_address)
    success = place_in_line != 0
    res = flask.jsonify (
        success=success,
        place_in_line=place_in_line
    )
    return res


@app.route ("/move_to_top")
# @login_required
def move_to_top ():
    params = flask.request.args
    session_id = params.get (SESSION_ID_HTTP_PARAM_NAME)
    try:
        callee_address = session.handle_user (session_id)
    except Unauthorized:
        return unauthorized_resp
    # callee_address = current_user.email
    waiter_address = params.get (WAITER_ADDRESS_HTTP_PARAM_NAME)
    # waiter_address = "roy.quitt@googlemail.com"
    # waiter_address = "maibasis@gmail.com"
    # waiter_address = "R0586868610@gmail.com"
    success = Ques.move_to_top (waiter_address, callee_address)
    res = flask.jsonify (
        success=success
    )
    return res


@app.route ("/remove_from_que")
def remove ():
    params = flask.request.args
    session_id = params.get (SESSION_ID_HTTP_PARAM_NAME)
    try:
        callee_address = session.handle_user (session_id)
    except Unauthorized:
        return unauthorized_resp
    waiter_address = params.get (WAITER_ADDRESS_HTTP_PARAM_NAME)
    success = Ques.remove_from_que (callee_address, waiter_address)
    res = flask.jsonify (
        success=success
    )
    return res


@app.route ("/get_my_que")
# @login_required
def get_my_que ():
    params = flask.request.args
    session_id = params.get (SESSION_ID_HTTP_PARAM_NAME)
    try:
        address = session.handle_user (session_id)
    except Unauthorized:
        return unauthorized_resp
    # address = current_user.email
    print ("getting que of:", address)
    # address = "roy.quitt@googlemail.com"
    # address = "maibasis@gmail.com"
    # address = "R0586868610@gmail.com"
    user_que = Ques.get_my_que (address)
    print ([waiter.serialize () for waiter in user_que])
    res = flask.jsonify (
        que=[waiter.serialize () for waiter in user_que]
    )
    return res


@app.route ("/get_update")
# @login_required
def get_update ():
    params = flask.request.args
    session_id = params.get (SESSION_ID_HTTP_PARAM_NAME)
    try:
        user_address = session.handle_user (session_id)
    except Unauthorized:
        return unauthorized_resp
    # user_address = current_user.email
    notifications = Ques.get_notifications (user_address)
    res = flask.jsonify (
        notifications=[notification.serialize () for notification in notifications]
    )
    return res


@app.route ("/logout")
# @login_required
def logout ():
    """
    Logs the user out erases their session
    :rtype:
        Http Response
    """
    params = flask.request.args
    session_id = params.get (SESSION_ID_HTTP_PARAM_NAME)
    try:
        address = session.handle_user (session_id)
    except Unauthorized:
        return unauthorized_resp
    my_logger.debug ("logging user out...")
    my_logger.debug (address)
    session.log_out (session_id)
    # TODO:
    # You are supposed to call is_logged_in with session_id
    success = not session.is_logged_in ()
    res = flask.jsonify (
        success=success
    )
    return res

if __name__ == "__main__":
     # app.run(host="10.50.1.146")
     app.run (ssl_context="adhoc")

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
