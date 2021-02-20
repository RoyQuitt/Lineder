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
# from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from Override_Files.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/userinfo.profile',
          'https://www.googleapis.com/auth/gmail.readonly']
  
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
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials_flow.json', SCOPES)
            auth_url, local_server, wsgi_app = flow.run_local_server_1(port=0)
            # auth_url.replace("localhost", "10.50.1.149")
            print("MSG:", auth_url)
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


def after_url():  # creds, token
    global token
    global creds
    global results_from_thread
    print(str(datetime.now()) + " creds before while: ", creds)
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
    print(datetime.now(), "building gmail")
    # people_service = build('people', 'v1', credentials=creds)
    service_gmail = build('gmail', 'v1', credentials=creds)
    print(datetime.now(), "finished building")
    # Call the Calendar API
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    time_max = datetime.utcnow() + timedelta(days=7)
    time_max_text = time_max.isoformat() + 'Z' # 'Z' indicates UTC time
    # all_calendars = get_all_calendars(service)
    events_result = {}
    # all_calendars_events_list = []


    print("Getting This Week's Events From All Calendars")
    # events_result = (service.events().list(calendarId='otfnarbn0008p8cnthk9976gtsgp1auc@import.calendar.google.com', timeMin=now,  # calendarId='primary' / otfnarbn0008p8cnthk9976gtsgp1auc@import.calendar.google.com
    #                                        timeMax=time_max_text, singleEvents=True,
    #                                        orderBy='startTime').execute())
    #
    # events_result_json = json.dumps(events_result, indent=4)
    # # with open("sample.txt", "w", encoding="utf-8") as text_file:
    # #     text_file.write(events_result_json)
    # events = events_result.get('items', [])
    # # events[]
    # print("\nevents:", events)
    user_address = call_gmail_api(service_gmail)
    # # user_address, user_id, user_name = call_people_api(people_service)
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

    freebusy_result = service.freebusy().query(body=body).execute()
    print(freebusy_result)
    freebusy = []
    # calendars = freebusy_result['calendars']
    calendars = freebusy_result[u'calendars']
    for calendar in calendars:
        print(calendar)
        if (calendars[calendar])[u'busy']:
            freebusy.extend((calendars[calendar])[u'busy'])
        print(freebusy)
    return freebusy, user_address


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
    print("EMAIL ADDRESS IS:", address)
    return address

    # if not labels:
    #     print('No labels found.')
    # else:
    #     print('Labels:')
    #     for label in labels:
    #         print(label['name'])


# def call_people_api(people_service):
#     profile = people_service.people().get('people/me', personFields='names,emailAddresses')
#     # profile = json.dumps(profile_result, indent=4)
#     # profile = people_service.people().get('people/me') #, personFields='names,emailAddresses,resourceName'
#     # p_id = profile['resourceName']
#     print(profile.resourceName)
#     print("PROFILE:")
#     print(type(profile))
#     print(profile)
#
#     p_id = profile.get('resourceName')
#     # p_name = profile['names'][0]['givenName']
#     p_name = (profile.get('names', [])[0]).get('givenName')
#     # p_address = profile['emailAddresses'][0]
#     p_address = (profile.get('emailAddresses', [])[0]).get('value')
#     print("PROFILE:")
#     print(p_id)
#     print(p_name)
#     print(p_address)
#     return p_address, p_id, p_name


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

