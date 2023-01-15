from credentials import *

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update

import time

from base64 import urlsafe_b64encode
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes, ApplicationBuilder

import openai

import asyncio
import time

def getSummary(prompt, maxlimit=50, randomness=0, model="text-davinci-003"):
    openai.api_key = OPENAI_API_KEY
    if (len(prompt) < maxlimit):
        return prompt
    response = openai.Completion.create(
        model=model, prompt='Summarise this "'+prompt+'"', temperature=randomness, max_tokens=maxlimit)

    return response.choices[0].text.strip()

def main():
    past_email_ids = set()

    while True:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.create_task(receive_new_email(past_email_ids)),
        ]
        loop.run_until_complete(asyncio.wait(tasks))
        # loop.close()


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


async def receive_new_email(past_email_ids):
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
                snippet = getSummary(msg["snippet"])

                tele_msg = f'From: {from_}\nSubject: {subject}\nMessage: {snippet}'

                print(tele_msg)

                # Add the message id to the past_email_ids set
                past_email_ids.add(msg_id)

                # Send Telegram message
                bot = Bot(TELEGRAM_API_KEY)
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                                 text=tele_msg)
                await asyncio.sleep(1)


if __name__ == '__main__':
    main()
