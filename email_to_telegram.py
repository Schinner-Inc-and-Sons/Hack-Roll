from credentials import *

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import time
from telegram import Bot

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://mail.google.com/']


def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        processed_messages = set()

        while True:
            # Call the Gmail API
            service = build('gmail', 'v1', credentials=creds)

            # Call the Gmail API to fetch new emails
            response = service.users().messages().list(
                userId='me', maxResults=1, labelIds=['INBOX']).execute()

            if 'messages' in response:
                messages = response['messages']

                for message in messages:
                    msg_id = message['id']

                    if msg_id not in processed_messages:
                        msg = service.users().messages().get(
                            userId='me', id=msg_id).execute()

                        headers = msg['payload']['headers']
                        to = ''
                        from_ = ''
                        for header in headers:
                            if header['name'] == 'To':
                                to = header['value']
                            elif header['name'] == 'From':
                                from_ = header['value']
                        snippet = msg["snippet"]

                        tele_msg = f'To: {to}\nFrom: {from_}\nMessage: {snippet}'
                        print(tele_msg)

                        # Add the message id to the processed_messages set
                        processed_messages.add(msg_id)

                        # Send Telegram message
                        bot = Bot(TELEGRAM_API_KEY)
                        bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                                         text=tele_msg)

            # Wait for 10 seconds before checking for new emails again
            time.sleep(10)

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()

# # Call the Gmail API
# service = build('gmail', 'v1', credentials=creds)
# results = service.users().labels().list(userId='me').execute()
# labels = results.get('labels', [])

# if not labels:
#     print('No labels found.')
#     return
# print('Labels:')
# for label in labels:
#     print(label['name'])
