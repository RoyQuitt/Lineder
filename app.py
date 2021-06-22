from __future__ import print_function

import datetime
import base64
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
from db import get_db, init_db  # init_db_command,
from dbUser import MyUser as DbUser
from freebusy_range import Freebusy as Range
from ques import Ques
from refresh_ranges import RefreshRanges
from request_handler import RequestHandler
from temp_user import TempUser

# LOCAL_SERVER_ADDRESS = 'https://127.0.0.1:5000/refresh_all'
LOCAL_SERVER_ADDRESS = 'https://10.50.1.146:5000/refresh_all'

RANGES_REFRESH_RATE = 10

WAITER_ADDRESS_HTTP_PARAM_NAME = 'waiter_address'
SESSION_ID_HTTP_PARAM_NAME = 'session_id'

warnings.filterwarnings('ignore', message='Unverified HTTPS request')

session = SessionManagement()

my_logger = Lineder_logging.get_logger("App")
my_logger.debug("\n--------------------------- NEW "
                "---------------------------\n")
my_logger.debug("Starting Logging")

HEX32_MAX = 111111111

TIMEZONE_OFFSET = 3

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
current_handler_instance = RequestHandler(None)
temp_user = None


my_logger.debug("Going to initialize DB")
# Naive database setup
try:
    my_logger.debug("creating DB")
    init_db()
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
    # return redirect(url_for("login_flow"))
    return redirect(url_for("login"))


def get_google_provider_cfg():
    cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    print("config:", cfg)
    return cfg


# @app.route("/login")  # arrow 1
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


@app.route("/login")
def login():
    global current_handler_instance
    params = flask.request.args
    session_id = params.get('session_id')
    if not session_id:
        current_handler_instance = RequestHandler(request)
        uri = current_handler_instance.login_request()
        print("uri:", uri)
        return redirect(uri, code=302)
    if session.is_logged_in(session_id):
        return "You are already logged in. You can close this window"
    temp_id = session.generate_temp_id()
    uri = current_handler_instance.login_request()
    temp_id_bytes = temp_id.encode('ascii')
    base64_bytes = base64.b64encode(temp_id_bytes)
    base64_temp_id = base64_bytes.decode('ascii')
    uri += "&state=" + base64_temp_id
    print("uri:", uri)
    return redirect(uri, code=302)
    # res = flask.jsonify(auth_url=uri, temp_id=temp_id)
    # return res


@app.route("/login/callback")
def callback():
    global current_handler_instance
    name, user_address, phone, pic_url, freebusy, headers =\
        current_handler_instance.callback_handler()
    print("user info:", name, user_address, phone, pic_url, len(freebusy))
    cur_user = DbUser(user_address, name, phone, headers)  # current user
    cur_user.id = DbUser.get_id_by_email(user_address)
    if not cur_user.id:
        c_user_id = DbUser.create(cur_user.email, name, phone, headers)
    else:
        DbUser.update_creds(cur_user.id, headers)
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


@app.route("/login/close_window")
def close_window():
    global current_handler_instance
    global temp_user
    print("code:", request.args.get("code"))
    current_handler_instance = RequestHandler(request)
    name, user_address, phone, pic_url, freebusy, headers = \
        current_handler_instance.callback_handler()

    # Save the info as a global variable until the user requests to update his info
    temp_user = TempUser(name, user_address, phone, pic_url, freebusy, headers)
    print("user info:", name, user_address, phone, pic_url, len(freebusy))
    return "Login Complete! You May Close This Window"


@app.route("/get_info")
def get_info():
    global temp_user
    cur_user = DbUser(temp_user.address, temp_user.name,
                      temp_user.phone, temp_user.headers)
    cur_user.id = DbUser.get_id_by_email(temp_user.address)
    if not cur_user.id:
        DbUser.create(cur_user.email, cur_user.name,
                      cur_user.phone, cur_user.creds)
    else:
        DbUser.update_creds(cur_user.id, cur_user.creds)
    session_id = session.login_user(temp_user.address)
    my_logger.debug(session.users_dict)
    my_logger.debug("LOGGED IN NEW USER!")
    my_logger.debug("email: %s", cur_user.email)
    my_logger.debug("user_id: %s", cur_user.id)
    my_logger.debug("\nUser: %s", temp_user.address)
    my_logger.debug(temp_user.freebusy)

    # Clear all of the "old" ranges the user currently has
    Range.delete_user_ranges(cur_user.id)

    # Create the new ranges in our database
    for c_range in temp_user.freebusy:
        Range.create_range(cur_user.id, c_range['start'], c_range['end'])

    # Build the HTTP response
    res = flask.jsonify(freebusy=temp_user.freebusy, name=temp_user.name,
                        phone=temp_user.phone, session_id=session_id)
    my_logger.debug("callback response: %s", res.get_data(as_text=True))
    return res

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


@app.route("/login/my_callback")
def my_callback():
    # Get authorization code Google sent back to me
    code = request.args.get("code")
    # Find out what URL to hit to get tokens that allow me to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))


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
        c_user_id = DbUser.create(cur_user.email, name, phone, user_credentials)
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
    print("next:", next_available)
    new_next_available: datetime = utc_to_local(next_available)  # change TZ to local
    print("new:", new_next_available)
    new_next_available_s = new_next_available.isoformat().split("+")[0].replace("T", " ")
    print("new_s:", new_next_available_s)
    phone = DbUser.get_user_phone(user_address)
    name = DbUser.get_user_name(user_address)
    res = flask.jsonify(
        name=name,
        ranges=user_ranges,
        is_available=is_available,
        next_available=new_next_available_s,
        phone=phone
    )
    return res


def utc_to_local(utc_dt: datetime) -> datetime:
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


def change_timezone(s):
    t = s.split(" ")[-2]
    print(t)
    hour_s = t.split(":")[0]
    hour = int(hour_s)
    new_hour = hour + TIMEZONE_OFFSET
    new_hour_s = str(new_hour)
    new_s = s.replace(hour_s, new_hour_s)
    return new_s


@app.route("/join_que")
def join():
    params = flask.request.args
    session_id = params.get(SESSION_ID_HTTP_PARAM_NAME)
    try:
        waiter_address = session.handle_user(session_id)
    except Unauthorized:
        return unauthorized_resp
    callee_address = params.get('user_address')

    if '@' in callee_address:
        print("address")
        try:
            place_in_line = Ques.create_que_item(callee_address,
                                                 waiter_address)
        except TypeError:
            print("type error")
            return flask.jsonify(error="type error")
    else:  # its a name
        print("name")
        try:
            user_name = callee_address
            user_name = user_name.title()
            print(user_name)
            callee_address = DbUser.get_address_by_name(user_name)
            place_in_line = Ques.create_que_item(callee_address,
                                                 waiter_address)
        except TypeError:
            print("type error")
            return flask.jsonify(error="type error")
    print("address:", callee_address)

    print("adding", waiter_address, "to", callee_address + "'s que")
    # place_in_line = Ques.create_que_item(callee_address, waiter_address)
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
        print("error, unauthorized")
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


# @app.route("/login/close_window")
# def close_window():
#     params = flask.request.args
#     temp_id = params.get('temp_id')
#     code = request.args.get('code')
#     print(temp_id, code)
#     if session.add_code_and_temp_id(temp_id, code) == code:
#         return "<p>Login Completed, You May Close This Window</p>"
#     else:
#         return "<p>Something Went Wrong :(</p>"


# @app.route("/get_info")
# def get_info():
#     global current_handler_instance
#     params = flask.request.args
#     temp_id = params.get('temp_id')
#     code = session.convert_temp_id_to_code(temp_id)


if __name__ == "__main__":
    config = get_google_provider_cfg()
    # Build and start our scheduler so that
    # we can refresh the ranges periodically
    scheduler = BackgroundScheduler()
    my_logger.debug("adding job")
    job = scheduler.add_job(call_refresh_endpoint, 'interval', minutes=RANGES_REFRESH_RATE)
    my_logger.debug("starting scheduler")
    # scheduler.start()

    print("running")
    port = int(os.environ.get("PORT", 5000))
    my_logger.debug("port: %s", port)
    # app.run(ssl_context="adhoc", host="0.0.0.0", port=port, debug=False)
    # print(change_timezone("Mon, 19 Apr 2021 08:00:00 GMT"))
    print(utc_to_local(datetime.utcnow()))
    # app.run(ssl_context="adhoc", host="10.50.1.146")
    # app.run(ssl_context="adhoc", host="10.50.1.170")
    app.run(ssl_context="adhoc", host="192.168.73.7")
