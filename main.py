from credentials import *
from OpenAI import *

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from telegram import Bot

import time

from base64 import urlsafe_b64encode
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from telegram.ext import Updater, CommandHandler


def send_email(to, subject, body):
    credentials = update_credentials()
    service = build('gmail', 'v1', credentials=credentials)

    try:
        # Create the message
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        message.attach(MIMEText(body))
        create_message = {'raw': urlsafe_b64encode(
            message.as_bytes()).decode()}
        send_message = (service.users().messages().send(
            userId="me", body=create_message).execute())

        print(
            f"Sent email to {to} with subject {subject} with message {body}")
    except HttpError as error:
        print(F'An error occurred: {error}')
        send_message = None
    return send_message


def handle_messages(update, context):
    # Extract the necessary information from the message
    message = update.message.text
    message_text_list = message.split()
    to = message_text_list[1]
    subject = message_text_list[2]
    body = ' '.join(message_text_list[3:])
    send_email(to, subject, body)
    update.message.reply_text('Email sent successfully!')


def main():
    updater = Updater(TELEGRAM_API_KEY, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("email", handle_messages))

    # Start the Bot
    updater.start_polling()

    try:
        past_email_ids = set()

        while True:
            receive_new_email(past_email_ids)

            # Wait for 10 seconds before checking for new emails again
            time.sleep(10)

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def update_credentials():
    credentials = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        credentials = Credentials.from_authorized_user_file(
            'token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())
    return credentials


def receive_new_email(past_email_ids):
    credentials = update_credentials()
    service = build('gmail', 'v1', credentials=credentials)

    # Fetch new emails
    response = service.users().messages().list(
        userId='me', maxResults=1, labelIds=['INBOX']).execute()

    if 'messages' in response:
        messages = response['messages']

        for message in messages:
            msg_id = message['id']

            if msg_id not in past_email_ids:
                msg = service.users().messages().get(
                    userId='me', id=msg_id).execute()

                headers = msg['payload']['headers']
                from_ = ''
                subject = ''
                for header in headers:
                    if header['name'] == 'From':
                        from_ = header['value']
                    elif header['name'] == 'subject' or header['name'] == 'Subject':
                        subject = header['value']
                snippet = msg["snippet"]

                tele_msg = f'From: {from_}\nSubject: {subject}\nMessage: {snippet}'

                print(tele_msg)

                # Add the message id to the past_email_ids set
                past_email_ids.add(msg_id)

                # Send Telegram message
                bot = Bot(TELEGRAM_API_KEY)
                bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                                 text=tele_msg)


if __name__ == '__main__':
    main()
