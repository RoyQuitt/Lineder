# Python standard libraries
import json
import os
import sqlite3
import datetime
from datetime import datetime
from datetime import timedelta

from oauthlib.oauth2 import WebApplicationClient
import requests

# Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)
API_KEY = "AIzaSyCJ70N-VMiFFgzpcwkzJvHyeOHgX27KRsM"
UTC_TIMEZONE_INDICATOR = 'Z'
DAYS_LOOK_AHEAD = 7

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


class RequestHandler:
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()

    def __init__(self, request):
        print("\nNEW HANDLER!\n")
        self.user_request = request
        self.headers = {}
        if self.user_request:
            self.user_code = request.args.get("code")
            print(self.user_request)
            print(self.user_request.args.get("code"))
            print(self.user_code)
        else:
            print("no request yet")

    def login_request(self):
        # base_url = request.base_url
        # Find out what URL to hit for Google login
        authorization_endpoint = self.google_provider_cfg["authorization_endpoint"]

        # Use library to construct the request for Google login and provide
        # scopes that let you retrieve user's profile from Google
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=self.user_request.base_url + "/close_window",
            scope=["openid", "email", "profile", 'https://www.googleapis.com/auth/calendar.readonly',
                   'https://www.googleapis.com/auth/user.phonenumbers.read'],
        )
        return request_uri

    def callback_handler(self):
        # self.user_request.args.add('code', self.user_code)
        self.get_user_token()
        name, email, phone_number, pic_url = self.get_user_info()
        freebusy = self.get_user_ranges()
        print("user info:", name, email, phone_number, pic_url, freebusy)

        authorization_dict = {key: self.headers[key] for key in self.headers.keys()
                              & {'Authorization'}}
        print(authorization_dict)
        token_str = authorization_dict['Authorization']

        return name, email, phone_number, pic_url, freebusy, token_str

    def get_user_ranges(self, authorization=None):
        print(authorization)
        if authorization is not None:
            self.headers['Authorization'] = authorization
        now = datetime.utcnow().isoformat() + UTC_TIMEZONE_INDICATOR  # 'Z' indicates UTC time
        time_max = datetime.utcnow() + timedelta(days=DAYS_LOOK_AHEAD)
        time_max_text = time_max.isoformat() + UTC_TIMEZONE_INDICATOR  # 'Z' indicates UTC time
        calendar_ids = self.get_user_calendars()
        body = {
            "timeMin": now,
            "timeMax": time_max_text,
            "items": calendar_ids
        }
        freebusy_endpoint = "https://www.googleapis.com/calendar/v3/freeBusy?key=" + API_KEY
        self.headers['Accept'] = 'application/json'
        self.headers['Content-Type'] = 'application/json'
        response = requests.post(freebusy_endpoint, headers=self.headers, data=str(body).replace("\'", "\""))
        print("response")
        print(response.json())
        freebusy = []
        calendars = response.json()[u'calendars']
        for calendar in calendars:
            if (calendars[calendar])[u'busy']:
                freebusy.extend((calendars[calendar])[u'busy'])
        print("freebusy:")
        print(freebusy)
        return freebusy

    def get_user_calendars(self, authorization=None):
        print(authorization)
        if authorization is not None:
            self.headers['Authorization'] = authorization['Authorization']
        print(self.headers)
        calendars_endpoint = "https://www.googleapis.com/calendar/v3/users/me/calendarList?minAccessRole=writer&key=" + API_KEY
        self.headers['Accept'] = 'application/json'
        body = None
        response = requests.get(calendars_endpoint, headers=self.headers, data=body)
        calendars_list = response.json()['items']
        calendar_id_list = [calendar['id'] for calendar in calendars_list]
        calendars = []
        for calendar_id in calendar_id_list:
            calendars.append({"id": calendar_id})
        print(calendars)
        return calendars

    def get_user_token(self, authorization=None):
        if authorization is not None:
            self.headers['Authorization'] = authorization
        # Get authorization code Google sent back to you
        # code = self.user_request.args.get("code")
        code = self.user_code
        print("\ncode:", code, "\n")

        # Find out what URL to hit to get tokens that allow you to ask for
        # things on behalf of a user
        token_endpoint = self.google_provider_cfg["token_endpoint"]

        # Prepare and send a request to get tokens! Yay tokens!
        client.code = code
        print(client.code)
        self.user_request.url += "?code=" + code
        print(self.user_request.url)
        print(self.user_request.base_url)
        token_url, self.headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=self.user_request.url,
            redirect_url=self.user_request.base_url,
            code=code
        )
        token_response = requests.post(
            token_url,
            headers=self.headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        # Parse the tokens!
        print(json.dumps(token_response.json()))
        client.parse_request_body_response(json.dumps(token_response.json()))

    def get_user_info(self, authorization=None):
        """
        gets user info (name, email & picture)
        :return: name, email & picture
        """
        if authorization is not None:
            self.headers['Authorization'] = authorization
        # Now that you have tokens (yay) let's find and hit the URL
        # from Google that gives you the user's profile information,
        # including their Google profile image and email
        userinfo_endpoint = self.google_provider_cfg["userinfo_endpoint"]
        uri, self.headers, body = client.add_token(userinfo_endpoint)
        # print(uri, self.headers, body)
        userinfo_response = requests.get(uri, headers=self.headers, data=body)

        # You want to make sure their email is verified.
        # The user authenticated with Google, authorized your
        # app, and now you've verified their email through Google!
        if userinfo_response.json().get("email_verified"):
            unique_id = userinfo_response.json()["sub"]
            users_email = userinfo_response.json()["email"]
            picture = userinfo_response.json()["picture"]
            users_name = userinfo_response.json()["given_name"]
            # print(users_email, picture, users_name)
            phone_number = self.get_user_phone_number()
        else:
            return "User email not available or not verified by Google.", 400
        return users_name, users_email, phone_number, picture

    def get_user_phone_number(self, authorization=None):
        if authorization is not None:
            self.headers['Authorization'] = authorization
        # resource_name = 'people/me'
        # person_fields = 'names,emailAddresses,phoneNumbers'
        people_endpoint = "https://people.googleapis.com/v1/people/me?personFields=phoneNumbers&key=" + API_KEY
        self.headers['Accept'] = 'application/json'
        body = None
        response = requests.get(people_endpoint, headers=self.headers, data=body)
        try:
            phone_number = response.json()['phoneNumbers'][0]['value']
        except KeyError:
            print("user has no phone setup")
            phone_number = ""
            pass
        return phone_number
