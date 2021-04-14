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

my_logger = Lineder_logging.get_logger("App")
my_logger.debug("\n--------------------------- NEW ---------------------------\n")
my_logger.debug("Starting Logging")

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


@app.route("/")
def index():
    return "<h1>Test App</h1>"


if __name__ == "__main__":
    # scheduler = BackgroundScheduler()
    # my_logger.debug("adding job")
    # # job = scheduler.add_job(call_refresh_endpoint, 'interval', minutes=RANGES_REFRESH_RATE)
    # my_logger.debug("starting scheduler")
    # scheduler.start()
    print("running")
    port = int(os.environ.get("PORT", 5000))
    my_logger.debug("port: %s", port)
    # app.run(ssl_context="adhoc", host="0.0.0.0", port=port, debug=False)
    app.run(ssl_context="adhoc")
