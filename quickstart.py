from __future__ import print_function

import datetime
import json
import os.path
import pickle
import threading
import time
from datetime import datetime
from datetime import timedelta

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

UTC_TIMEZONE_INDICATOR = 'Z'
PEOPLE_API_VERSION = 'v1'
DAYS_LOOK_AHEAD = 7

DEBUG = False

CREDENTIALS_FILE_PATH = r"C:\Users\royqu\PycharmProjects\Lineder\credentials_flow.json"
TOCKEN_FILE_NAME = 'token.pickle'
CREDENTIALS_FLOW_JSON = 'credentials_flow.json'

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/userinfo.profile',
          'https://www.googleapis.com/auth/user.emails.read', 'https://www.googleapis.com/auth/user.phonenumbers.read']
token = None
creds = None
results_from_thread = [None] * 2  # index 0 = creds, index 1 = url


class Quickstart:
    def __init__(self):
        self.token = None
        self.creds = None
        self.results_from_thread = [None] * 2  # index 0 = creds, index 1 = url

    def get_auth_url(self):
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(TOCKEN_FILE_NAME):
            with open(TOCKEN_FILE_NAME, 'rb') as self.token:
                self.creds = pickle.load(self.token)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                auth_url = "!"
                self.creds.refresh(Request())
            else:
                """
                ADD TRY EXCEPT TO HANDLE BOTH PC AND LAPTOP CREDENTIALS FILE LOCATION
                """
                try:
                    print("trying to run on PC")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_FLOW_JSON, SCOPES)
                except FileNotFoundError:
                    print("running on laptop")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        r"%s" % CREDENTIALS_FILE_PATH, SCOPES)
                auth_url, local_server, wsgi_app = flow.run_local_server_1(port=0)
                # auth_url.replace("localhost", "10.50.1.149")
                print("URL:", auth_url)

                # Create a new thread to wait on for the Google response
                new_thread = threading.Thread(target=flow.run_local_server_2,
                                              args=(auth_url, local_server, wsgi_app, self.results_from_thread))  # , port=0
                new_thread.start()
                # creds, auth_response = flow.run_local_server_2(auth_url, local_server, wsgi_app, port=0)
                # return auth_url

            # Save the credentials for the next run
            # print("Token")

            # with open('token.pickle', 'wb') as token:
            #     pickle.dump(creds, token)
        else:
            auth_url = "!"
        if auth_url is None:
            # TODO:
            # Note the you return less return values in case auth_url is none. This is very unhealthy.
            # Better return an empty auth_url here
            # or return a list [] instead of tuple
            return self.token, self.creds
        else:
            return self.token, self.creds, auth_url

    def make_requests(self, given_creds=None):
        if given_creds is not None:
            self.creds = given_creds
            auth_url = "not None"
        else:
            self.creds = self.results_from_thread[0]
            auth_url = self.results_from_thread[1]
        while self.creds is None or auth_url is None:
            self.creds = self.results_from_thread[0]
            auth_url = self.results_from_thread[1]
            time.sleep(0.01)  # delay in order to not overload CPU
        print(datetime.now(), "self.creds after while:", self.creds)

        # build service for google calendar API
        print(datetime.now(), "building calendar")
        service = build('calendar', 'v3', credentials=self.creds)

        # build service for people API in order to get user phone number and email address
        print(datetime.now(), "building people")
        people_service = build('people', PEOPLE_API_VERSION, credentials=self.creds)
        print(datetime.now(), "finished building")

        # Call the Calendar API
        now = datetime.utcnow().isoformat() + UTC_TIMEZONE_INDICATOR  # 'Z' indicates UTC time
        time_max = datetime.utcnow() + timedelta(days=DAYS_LOOK_AHEAD)
        time_max_text = time_max.isoformat() + UTC_TIMEZONE_INDICATOR  # 'Z' indicates UTC time

        # events_result = {}

        print("getting user's name, email and phone")
        user_name, user_address, user_phone = Quickstart.call_people_api(people_service)
        calendars = Quickstart.get_all_calendars(service)
        body = {
            "timeMin": now,
            "timeMax": time_max_text,
            "items": calendars
        }
        print("Getting This Week's Events From All Calendars")
        freebusy_result = service.freebusy().query(body=body).execute()
        freebusy = []
        calendars = freebusy_result[u'calendars']
        for calendar in calendars:
            if (calendars[calendar])[u'busy']:
                freebusy.extend((calendars[calendar])[u'busy'])
        return freebusy, user_address, user_name, user_phone, self.creds

    @staticmethod
    def call_people_api(people_service):
        result = people_service.people().get(
            resourceName='people/me',
            personFields='names,emailAddresses,phoneNumbers').execute(),

        print("result:\n", result)
        name = result[0]['names'][0]['displayName']
        print("name:", name)
        email_address = result[0]['emailAddresses'][0]['value']
        print("email_address:", email_address)
        try:
            phone_number = result[0]['phoneNumbers'][0]['value']
            print("phone_number:", phone_number)
        except KeyError:
            print("user has no phone setup")
            phone_number = ""
            pass

        return name, email_address, phone_number

    @staticmethod
    def get_all_calendars(service):
        calendar_list = service.calendarList().list(minAccessRole="writer").execute()
        if DEBUG:  # check for the 'DEBUG' flag
            for calendar_list_entry in calendar_list['items']:
                print(calendar_list_entry['summary'], calendar_list_entry['id'])
        calendar_id_list = [calendar['id'] for calendar in calendar_list['items']]
        calendars = []
        for calendar_id in calendar_id_list:
            calendars.append({"id": calendar_id})
        return calendars


def until_url():
    global token
    global creds

    global results_from_thread
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOCKEN_FILE_NAME):
        with open(TOCKEN_FILE_NAME, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            auth_url = "!"
            creds.refresh(Request())
        else:
            """
            ADD TRY EXCEPT TO HANDLE BOTH PC AND LAPTOP CREDENTIALS FILE LOCATION
            """
            try:
                print("trying to run on PC")
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FLOW_JSON, SCOPES)
            except FileNotFoundError:
                print("running on laptop")
                flow = InstalledAppFlow.from_client_secrets_file(
                    r"%s" % CREDENTIALS_FILE_PATH, SCOPES)
            auth_url, local_server, wsgi_app = flow.run_local_server_1(port=0)
            # auth_url.replace("localhost", "10.50.1.149")
            print("URL:", auth_url)

            # Create a new thread to wait on for the Google response
            new_thread = threading.Thread(target=flow.run_local_server_2,
                                          args=(auth_url, local_server, wsgi_app, results_from_thread))  # , port=0
            new_thread.start()
            # creds, auth_response = flow.run_local_server_2(auth_url, local_server, wsgi_app, port=0)
            # return auth_url

        # Save the credentials for the next run
        # print("Token")


        # with open('token.pickle', 'wb') as token:
        #     pickle.dump(creds, token)
    else:
        auth_url = "!"
    if auth_url is None:
        # TODO:
        # Note the you return less return values in case auth_url is none. This is very unhealthy.
        # Better return an empty auth_url here
        # or return a list [] instead of tuple
        return token, creds
    else:
        return token, creds, auth_url


def after_url(given_creds=None):
    global token
    global creds
    global results_from_thread
    if given_creds is not None:
        creds = given_creds
    # print(str(datetime.now()) + " creds before while: ", creds)
    # print(auth_url)
    creds = results_from_thread[0]
    auth_url = results_from_thread[1]
    while creds is None or auth_url is None:
        creds = results_from_thread[0]
        auth_url = results_from_thread[1]
        time.sleep(0.01)  # delay in order to not overload CPU
    # print("out of while")
    print(datetime.now(), "creds after while:", creds)
    # print(auth_url)
    # build service for google calendar API
    print(datetime.now(), "building calendar")
    service = build('calendar', 'v3', credentials=creds)
    # build service for gmail API in order to get user email address
    # print(datetime.now(), "building gmail")
    # service_gmail = build('gmail', 'v1', credentials=creds)
    # build service for people API in order to get user phone number and email address
    print(datetime.now(), "building people")
    people_service = build('people', PEOPLE_API_VERSION, credentials=creds)
    print(datetime.now(), "finished building")
    # Call the Calendar API
    now = datetime.utcnow().isoformat() + UTC_TIMEZONE_INDICATOR  # 'Z' indicates UTC time
    time_max = datetime.utcnow() + timedelta(days=DAYS_LOOK_AHEAD)
    time_max_text = time_max.isoformat() + UTC_TIMEZONE_INDICATOR  # 'Z' indicates UTC time
    # all_calendars = get_all_calendars(service)
    events_result = {}
    # all_calendars_events_list = []

    # user_address = call_gmail_api(service_gmail)
    print("getting user's name, email and phone")
    user_name, user_address, user_phone = call_people_api(people_service)
    # return events, user_address
    calendars = get_all_calendars(service)
    body = {
        "timeMin": now,
        "timeMax": time_max_text,
        "items": calendars
    }
    print("Getting This Week's Events From All Calendars")
    freebusy_result = service.freebusy().query(body=body).execute()
    # print("result", freebusy_result)
    freebusy = []
    # calendars = freebusy_result['calendars']
    calendars = freebusy_result[u'calendars']
    for calendar in calendars:
        # print(calendar)
        if (calendars[calendar])[u'busy']:
            freebusy.extend((calendars[calendar])[u'busy'])
        # print(freebusy)
    return freebusy, user_address, user_name, user_phone, creds


def get_all_calendars(service):
    calendar_list = service.calendarList().list(minAccessRole="writer").execute()

    if DEBUG:
        for calendar_list_entry in calendar_list['items']:
            print(calendar_list_entry['summary'], calendar_list_entry['id'])
    calendar_id_list = [calendar['id'] for calendar in calendar_list['items']]
    calendars = []
    for calendar_id in calendar_id_list:
        calendars.append({"id": calendar_id})
    return calendars


def call_gmail_api(service_gmail):
    # Call the Gmail API
    # results = service_gmail.users().labels().list(userId='me').execute()
    profile = service_gmail.users().getProfile(userId='me').execute()
    address = profile['emailAddress']
    # labels = results.get('labels', [])
    # print("EMAIL ADDRESS IS:", address)
    return address


def call_people_api(people_service):
    result = people_service.people().get(
        resourceName='people/me',
        personFields='names,emailAddresses,phoneNumbers').execute(),

    print("result:\n", result)
    name = result[0]['names'][0]['displayName']
    print("name:", name)
    email_address = result[0]['emailAddresses'][0]['value']
    print("email_address:", email_address)
    try:
        phone_number = result[0]['phoneNumbers'][0]['value']
        print("phone_number:", phone_number)
    except KeyError:
        print("user has no phone setup")
        phone_number = ""
        pass
    # print("\nRESULTS:")

    return name, email_address, phone_number

