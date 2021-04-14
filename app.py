from __future__ import print_function

import datetime
from datetime import timezone, timedelta
# Python standard libraries
import json
import os.path
import random
import sqlite3
from datetime import datetime, time
import time

# Third-party libraries
# import base32hex
import flask
import urllib3
import requests
import warnings

from flask import Flask, redirect, request, url_for
from flask_cors import CORS
# from flask_login import (
#     LoginManager,
#     current_user,
#     login_required,
#     login_user,
#     logout_user,
# )
from oauthlib.oauth2 import WebApplicationClient
from apscheduler.schedulers.background import BackgroundScheduler
import Lineder_logging

from quickstart import Quickstart
# Internal imports
from session_managment import SessionManagement, Unauthorized
from db import init_db_command, get_db
from dbUser import MyUser as DbUser
from freebusy_range import Freebusy as Range
from ques import Ques
from refresh_ranges import RefreshRanges

LOCAL_SERVER_ADDRESS = 'https://127.0.0.1:5000/refresh_all'

RANGES_REFRESH_RATE = 10

WAITER_ADDRESS_HTTP_PARAM_NAME = 'waiter_address'
SESSION_ID_HTTP_PARAM_NAME = 'session_id'

warnings.filterwarnings('ignore', message='Unverified HTTPS request')

session = SessionManagement()

my_logger = Lineder_logging.get_logger ("App")
my_logger.debug ("\n--------------------------- NEW "
                 "---------------------------\n")
my_logger.debug ("Starting Logging")


HEX32_MAX = 111111111

# Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Google API Credentials
# The client ID created for the app in the Google Developers Console
# with the google-signin-client_id meta element
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

# Flask app setup
app = Flask(__name__)
app.config['supports_credentials'] = True
print("app config:", app.config)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
unauthorized_resp = None
current_quickstart_instance = Quickstart()

my_logger.debug("Going to initialize DB")
# Naive database setup
try:
    my_logger.debug("creating DB")
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    my_logger.debug("DB already created")

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)


@app.route("/json_test")
def json_test():
    return flask.jsonify(
        redirect_url="hello",
        code=302
    )


@app.route("/")
def index():
    global unauthorized_resp
    message = {'error': 'Unauthorized'}
    unauthorized_resp = flask.jsonify(message)
    unauthorized_resp.status_code = 401
    return redirect(url_for("login_flow"))


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


@app.route("/login")  # arrow 1
def login_flow():
    """
    login_flow starts the login process and then redirects the user to the next stage by sending a 302 redirect
    response with the URL received from quickstart
    :return:
        The redirect response
    """
    global current_quickstart_instance
    params = flask.request.args
    session_id = params.get('session_id')
    if not session_id:
        # TODO:
        # token, creds - not used below
        current_quickstart_instance = Quickstart()
        token, creds, url = current_quickstart_instance.get_auth_url()
        return redirect(url, code=302)
    if session.is_logged_in(session_id):
        return "You are already logged in. You can close this window"
    token, creds, url = current_quickstart_instance.get_auth_url()
    return redirect(url, code=302)  # arrow 4 + 5


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
def after_request(response):
    # my_logger.debug("after request")
    response.headers.add('Access-Control-Allow-Origin', '*')
    # response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Access-Control-Allow-Origin')
    response.headers.add('Access-Control-Allow-Headers', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response
    # return response


# @app.after_request
# def after_request(response):
#     response.headers.add('Access-Control-Allow-Origin', '*')
#     response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
#     response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
#     return response


@app.route("/show_cookie")
def show_cookie():
    # return "hello"
    username = flask.request.cookies.get('user_address')
    res = flask.jsonify(username=username)
    my_logger.debug(username)
    return res


@app.route("/login/new_callback")
def ranges_callback():
    global current_quickstart_instance
    my_logger.debug("ranges callback")
    freebusy, user_address, name, phone, user_credentials = current_quickstart_instance.make_requests()
    cur_user = DbUser(user_address, name, phone, user_credentials)  # current user
    my_logger.debug("cUser after constructor:")
    my_logger.debug(cur_user)
    cur_user.id = DbUser.get_id_by_email(user_address)
    my_logger.debug("user.id in callback: %s", cur_user.id)
    if not cur_user.id:
        cUser_id = DbUser.create(cur_user.email, name, phone, user_credentials)
    else:
        DbUser.update_creds(cur_user.id, user_credentials)
    # logging in the user
    session_id = session.login_user(user_address)
    my_logger.debug(session.users_dict)
    my_logger.debug("LOGGED IN NEW USER!")
    my_logger.debug("email: %s", cur_user.email)
    my_logger.debug("user_id: %s", cur_user.id)
    my_logger.debug("\nUser: %s", user_address)
    my_logger.debug(freebusy)

    # Clear all of the "old" ranges the user currently has
    Range.delete_user_ranges(cur_user.id)

    # Create the new ranges in our database
    for c_range in freebusy:
        Range.create_range(cur_user.id, c_range['start'], c_range['end'])

    # Build the HTTP response
    res = flask.jsonify(freebusy=freebusy, name=name, phone=phone, session_id=session_id)
    my_logger.debug("callback response: %s", res.get_data(as_text=True))
    return res


@app.route("/busy_for")
def busy_for():
    params = flask.request.args
    session_id = params.get(SESSION_ID_HTTP_PARAM_NAME)
    try:
        owner_id = session.handle_user_user_id(session_id)
    except Unauthorized:
        return unauthorized_resp
    hours = int(params.get('hours'))
    mins = int(params.get('mins'))
    success = Range.busy_for(owner_id, hours, mins)
    res = flask.jsonify(success=success)
    return res


# /new_range?start=1985-04-12T23:20:50.52Z&end=1985-05-12T23:20:50.52Z
# from 12.04.1985, 23:20:50.52 until 12.05.1985, 23:20:50.52
@app.route("/new_range")
def new_range():
    params = flask.request.args
    session_id = params.get(SESSION_ID_HTTP_PARAM_NAME)
    try:
        owner_id = session.handle_user_user_id(session_id)
    except Unauthorized:
        return unauthorized_resp
    start: datetime = params.get('start')
    end: datetime = params.get('end')
    # owner_id = DbUser.get_id_by_email(current_user.email)
    # owner_id = DbUser.get_id_by_email("roy.quitt@googlemail.com")
    # owner_id = current_user.id
    # owner_address = session.get_address_by_session_id(session_id)
    # owner_id = DbUser.get_id_by_email(owner_address)
    print(start, end)
    now = datetime.now(tz=timezone(timedelta(hours=2), 'IST'))
    new_start: datetime = datetime.strptime(start, "%H:%M")
    final_start = datetime(now.year, now.month, now.day, new_start.hour, new_start.minute).isoformat() + 'Z'
    new_end: datetime = datetime.strptime(end, "%H:%M")
    final_end = datetime(now.year, now.month, now.day, new_end.hour, new_end.minute).isoformat() + 'Z'
    # final_start: datetime = datetime.strptime(start, "%H:%M %Y-%m-%dT%H:%M:%SZ")
    # final_end: datetime = datetime.strptime(end, "%H:%M %Y-%m-%dT%H:%M:%SZ")
    print(final_start, final_end)
    success = Range.create_range(owner_id, final_start, final_end)
    res = flask.jsonify(success=success)
    return res


@app.route("/get_user_schedule")
def get_user_schedule():
    """
Retrieve the availability of the user
return value is JSON
    @rtype: object
    """
    params = flask.request.args
    user_address = params.get('user_address')
    print("User address in get user schedule:" + user_address)
    # check if 'user_address' is a valid email, if it is - treat it like one,
    # if its not - treat it like a name of a user
    if '@' in user_address:
        print("address")
        try:
            # try to get the ranges of the user with the address given
            user_ranges: list[tuple[datetime, datetime]] = DbUser.get_user_ranges(user_address)
        except TypeError:
            print("type error")
            return flask.jsonify(error="type error")
    else:  # its a name
        print("name")
        try:
            user_name = user_address
            user_name = user_name.title()
            print(user_name)
            user_address = DbUser.get_address_by_name(user_name)
            user_ranges: list[tuple[datetime, datetime]] = DbUser.get_user_ranges(user_address)
        except TypeError:
            print("type error")
            return flask.jsonify(error="type error")
    print("address:", user_address)
    is_available: bool = DbUser.is_available(user_address)
    next_available: datetime = DbUser.next_available(user_address)
    phone = DbUser.get_user_phone(user_address)
    name = DbUser.get_user_name(user_address)
    res = flask.jsonify(
        name=name,
        ranges=user_ranges,
        is_available=is_available,
        next_available=next_available,
        phone=phone
    )
    return res


@app.route("/join_que")
def join():
    params = flask.request.args
    session_id = params.get(SESSION_ID_HTTP_PARAM_NAME)
    try:
        waiter_address = session.handle_user(session_id)
    except Unauthorized:
        return unauthorized_resp
    callee_address = params.get('user_address')
    print("adding", waiter_address, "to", callee_address + "'s que")
    place_in_line = Ques.create_que_item(callee_address, waiter_address)
    success = place_in_line != 0
    res = flask.jsonify(
        success=success,
        place_in_line=place_in_line
    )
    return res


@app.route("/move_to_top")
def move_to_top():
    params = flask.request.args
    session_id = params.get(SESSION_ID_HTTP_PARAM_NAME)
    try:
        callee_address = session.handle_user(session_id)
    except Unauthorized:
        return unauthorized_resp
    waiter_address = params.get(WAITER_ADDRESS_HTTP_PARAM_NAME)
    success = Ques.move_to_top(waiter_address, callee_address)
    res = flask.jsonify(
        success=success
    )
    return res


@app.route("/remove_from_que")
def remove():
    params = flask.request.args
    session_id = params.get(SESSION_ID_HTTP_PARAM_NAME)
    try:
        callee_address = session.handle_user(session_id)
    except Unauthorized:
        return unauthorized_resp
    waiter_address = params.get(WAITER_ADDRESS_HTTP_PARAM_NAME)
    success = Ques.remove_from_que(callee_address, waiter_address)
    res = flask.jsonify(
        success=success
    )
    return res


@app.route("/get_my_que")
def get_my_que():
    params = flask.request.args
    session_id = params.get(SESSION_ID_HTTP_PARAM_NAME)
    try:
        address = session.handle_user(session_id)
    except Unauthorized:
        return unauthorized_resp
    print("getting que of:", address)
    user_que = Ques.get_my_que(address)
    print([waiter.serialize() for waiter in user_que])
    res = flask.jsonify(
        que=[waiter.serialize() for waiter in user_que]
    )
    return res


@app.route("/get_update")
def get_update():
    params = flask.request.args
    session_id = params.get(SESSION_ID_HTTP_PARAM_NAME)
    try:
        user_address = session.handle_user(session_id)
    except Unauthorized:
        return unauthorized_resp
    notifications = Ques.get_notifications(user_address)
    res = flask.jsonify(
        notifications=[notification.serialize() for notification in notifications]
    )
    return res


@app.route("/logout")
def logout():
    """
    Logs the user out erases their session
    :rtype:
        Http Response
    """
    params = flask.request.args
    session_id = params.get(SESSION_ID_HTTP_PARAM_NAME)
    try:
        address = session.handle_user(session_id)
    except Unauthorized:
        return unauthorized_resp
    my_logger.debug("logging user out...")
    my_logger.debug(address)
    session.log_out(session_id)
    success = not session.is_logged_in(session_id)
    res = flask.jsonify(
        success=success
    )
    return res


@app.route("/refresh_all")
def refresh():
    refresh_instance = RefreshRanges()
    refresh_instance.refresh_all_ranges()
    return flask.jsonify(success=True)


@app.route("/call_refresh")
def call_refresh_endpoint():
    my_logger.debug("making HTTP request")
    r = requests.get(LOCAL_SERVER_ADDRESS, verify=False)


if __name__ == "__main__":

    # Build and start our scheduler so that we can refresh the ranges periodically
    scheduler = BackgroundScheduler()
    my_logger.debug("adding job")
    job = scheduler.add_job(call_refresh_endpoint, 'interval', minutes=RANGES_REFRESH_RATE)
    my_logger.debug("starting scheduler")
    scheduler.start()

    print("running")
    port = int(os.environ.get("PORT", 5000))
    my_logger.debug("port: %s", port)
    # app.run(ssl_context="adhoc", host="0.0.0.0", port=port, debug=False)
    # app.run(ssl_context="adhoc")
