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

from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes, ApplicationBuilder

import openai

defaultMessage = "To: \nSubject: \nBody: \n"
defaultToMessage = "To: "
defaultSubjectMessage = "Subject: "
defaultBodyMessage = "Body: "
toComponent = "To: "
subjectComponent = "Subject: "
bodyComponent = "Body: "
emailComponent = defaultMessage
prevId = 0
keyboard = [
    [InlineKeyboardButton("/To: ", switch_inline_query_current_chat="/To: ")],
    [InlineKeyboardButton("/Subject: ", switch_inline_query_current_chat="/Subject: ")],
    [InlineKeyboardButton("/Body: ", switch_inline_query_current_chat="/Body: ")]
]
completedKeyboard = keyboard.copy()
completedKeyboard.append([InlineKeyboardButton("/Send", switch_inline_query_current_chat="Send")])

def returnEmail():
    return toComponent + "\n" + subjectComponent + "\n" + bodyComponent + "\n"

async def email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global toComponent
    global subjectComponent
    global bodyComponent
    toComponent = defaultToMessage
    subjectComponent = defaultSubjectMessage
    bodyComponent = defaultBodyMessage
    global emailComponent
    emailComponent = returnEmail()
    global keyboard
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=emailComponent, reply_markup=reply_markup)
    global prevId
    prevId = msg.message_id


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    botName = "@schinner_inc_and_sons_bot /"
    if not update.message.text.startswith(botName):
        return
    botNameLength = len(botName)
    textContent = update.message.text[botNameLength:]
    if (textContent.startswith("To:")):
        global toComponent
        toComponent = textContent
    elif (textContent.startswith("Subject:")):
        global subjectComponent
        subjectComponent = textContent
    elif (textContent.startswith("Body:")):
        global bodyComponent
        bodyComponent = textContent
    global emailComponent
    emailComponent = returnEmail()
    global prevId
    global keyboard
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.editMessageText(text=emailComponent,chat_id=update.effective_chat.id, message_id=prevId, reply_markup=reply_markup)
    await update.message.delete()

async def keyboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("hi")

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


def getSummary(prompt, maxlimit=50, randomness=0, model="text-davinci-003"):
    openai.api_key = OPENAI_API_KEY

    response = openai.Completion.create(
        model=model, prompt='Summarise this "'+prompt+'"', temperature=randomness, max_tokens=maxlimit)

    return response.choices[0].text.strip()


def main():
    dp = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    dp.add_handler(CommandHandler("eemail", handle_messages))
    dp.add_handler(CommandHandler('email', email))
    
    #application.add_handler(InlineQueryHandler(callback=inline_query))
    dp.add_handler(MessageHandler(callback=inline_query, filters=None)) 
    dp.add_handler(CallbackQueryHandler(keyboard_callback)) 

    # Start the Bot
    dp.run_polling()

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
                snippet = getSummary(msg["snippet"])

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
