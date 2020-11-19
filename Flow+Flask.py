from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def main():
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
                'credentials_flow.json', SCOPES)
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
