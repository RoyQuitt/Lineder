from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json
import threading
import time

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
  
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
    print("creds before while:", creds)
    # print(auth_url)
    creds = results_from_thread[0]
    auth_url = results_from_thread[1]
    while creds is None or auth_url is None:
        creds = results_from_thread[0]
        auth_url = results_from_thread[1]
        time.sleep(0.01)  # delay in order to not overload CPU
    print("out of while")
    print("creds in after_url:", creds)
    print(auth_url)
    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
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
