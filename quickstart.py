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
# from Override_Files.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/userinfo.profile',
          'https://www.googleapis.com/auth/user.emails.read', 'https://www.googleapis.com/auth/user.phonenumbers.read']
#   'https://www.googleapis.com/auth/gmail.readonly',
token = None
creds = None
results_from_thread = [None] * 2  # index 0 = creds, index 1 = url


def until_url():
    global token
    global creds
    # creds = None
    global results_from_thread

    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
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
            # flow = InstalledAppFlow.from_client_secrets_file(
            #     'credentials_flow.json', SCOPES)
            flow = InstalledAppFlow.from_client_secrets_file(
                r"C:\Users\royqu\PycharmProjects\Lineder\credentials_flow.json", SCOPES)
            auth_url, local_server, wsgi_app = flow.run_local_server_1(port=0)
            # auth_url.replace("localhost", "10.50.1.149")
            print("URL:", auth_url)
            new_thread = threading.Thread(target=flow.run_local_server_2, args=(auth_url, local_server, wsgi_app, results_from_thread))  # , port=0
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
        return token, creds
    else:
        return token, creds, auth_url


def after_url():
    global token
    global creds
    global results_from_thread
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
    people_service = build('people', 'v1', credentials=creds)
    print(datetime.now(), "finished building")
    # Call the Calendar API
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    time_max = datetime.utcnow() + timedelta(days=7)
    time_max_text = time_max.isoformat() + 'Z' # 'Z' indicates UTC time
    # all_calendars = get_all_calendars(service)
    events_result = {}
    # all_calendars_events_list = []

    # user_address = call_gmail_api(service_gmail)
    print("getting user's name, email and phone")
    user_name, user_address, user_phone = call_people_api(people_service)
    # return events, user_address
    calendars = [
        {
            "id": 'primary'
        },
        {
            "id": 'otfnarbn0008p8cnthk9976gtsgp1auc'
        }
        ]
    body = {
        "timeMin": now,
        "timeMax": time_max_text,
        "items": calendars
    }
    print("Getting This Week's Events From All Calendars")
    freebusy_result = service.freebusy().query(body=body).execute()
    # print(freebusy_result)
    freebusy = []
    # calendars = freebusy_result['calendars']
    calendars = freebusy_result[u'calendars']
    for calendar in calendars:
        # print(calendar)
        if (calendars[calendar])[u'busy']:
            freebusy.extend((calendars[calendar])[u'busy'])
        # print(freebusy)
    return freebusy, user_address, user_name, user_phone


def get_all_calendars(service):
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token, minAccessRole="writer").execute()
        for calendar_list_entry in calendar_list['items']:
            print(calendar_list_entry['summary'])
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    return calendar_list['items']


def call_gmail_api(service_gmail):
    # Call the Gmail API

    # results = service_gmail.users().labels().list(userId='me').execute()
    profile = service_gmail.users().getProfile(userId='me').execute()
    address = profile['emailAddress']
    # labels = results.get('labels', [])
    # print("EMAIL ADDRESS IS:", address)
    return address

    # if not labels:
    #     print('No labels found.')
    # else:
    #     print('Labels:')
    #     for label in labels:
    #         print(label['name'])


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


def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    token, creds, url = until_url()
    print(token)
    print(creds)
    after_url(creds, token)


def original_quickstart():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds, msg = flow.run_local_server(port=0)
            print("MSG:", msg)
        # Save the credentials for the next run
        print("Token")
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    print(token)
    print(creds)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                        maxResults=10, singleEvents=True,
                                        orderBy='startTime').execute()
    print(type(events_result))
    events_result_json = json.dumps(events_result, indent=4)
    print(type(events_result_json))
    print("JSON:\n", events_result_json)
    print("RES: ", events_result)
    with open("sample.txt", "w", encoding="utf-8") as text_file:
        text_file.write(events_result_json)
    # print("HELLO: ", events_result.get('items', []))
    events = events_result.get('items', [])
    for event in events:
        print("\nNEW EVENT")
        print(event)

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])


if __name__ == '__main__':
    main()

