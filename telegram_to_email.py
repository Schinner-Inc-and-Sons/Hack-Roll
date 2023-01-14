from credentials import *

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import time
from telegram import Bot

from base64 import urlsafe_b64encode
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from telegram.ext import Updater, CommandHandler

# Telegram Bot Token
bot = Bot(token=TELEGRAM_API_KEY)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail']

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

# Build the Gmail service
gmail_service = build('gmail', 'v1', credentials=creds)


def send_email(to, subject, body):
    try:
        # Create the message
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        message.attach(MIMEText(body))
        create_message = {'raw': urlsafe_b64encode(
            message.as_bytes()).decode()}
        send_message = (gmail_service.users().messages().send(
            userId="me", body=create_message).execute())
        print(F'sent message to {to} Message Id: {send_message["id"]}')
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
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_API_KEY, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    # dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("email", handle_messages))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
