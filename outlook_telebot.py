from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler
)
import telegram.ext
# from telegram.ext.filters import EMAIL
import msal
import requests
import json


TOKEN = '<INSERT TOKEN>'

# user state: not logged in, logged in
user_access_tokens = dict()
user_names = dict()

MSAL_CLIENT_ID = '<INSERT ID>'
MSAL_AUTHORITY = 'https://login.microsoftonline.com/common'
MSAL_SCOPE = [
    'IMAP.AccessAsUser.All',
    'Mail.Read',
    'Mail.Send'
]


async def run_login_sequence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_access_tokens
    global user_names
    app = msal.PublicClientApplication(
        client_id=MSAL_CLIENT_ID, authority=MSAL_AUTHORITY)
    flow = app.initiate_device_flow(scopes=MSAL_SCOPE)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=flow['message'])
    result = app.acquire_token_by_device_flow(flow)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Logged in successfully')
    user_access_tokens[update.effective_user.id] = result['access_token']
    user_names[update.effective_user.id] = result['id_token_claims']['name']

# actions (recv): display unread emails, search emails, display one email


async def display_unread_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Retrieving your unread emails...')
    access_token = user_access_tokens[update.effective_user.id]
    response = requests.get(
        "https://graph.microsoft.com/v1.0/me/mailFolders('Inbox')/messages",
        headers=dict(Authorization=access_token))
    data = response.json()['value']
    for item in data:
        if 'from' not in item:
            continue
        if 'subject' not in item:
            continue
        sender = item['from']['emailAddress']['address']
        subject = item['subject']
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'From: {sender}\nSubject: {subject}')


async def search_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


async def display_full_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

# actions (send): to, subject, body
COMPOSE_START, COMPOSE_TO, COMPOSE_SUBJECT, COMPOSE_BODY, COMPOSE_SEND = range(
    5)

user_compose = dict()


async def compose_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_compose[update.effective_user.id] = dict()
    await update.message.reply_text('Enter email to send to:')
    return COMPOSE_TO


async def compose_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_compose[update.effective_user.id]['to'] = update.message.from_user
    await update.message.reply_text('Enter email subject:')
    return COMPOSE_SUBJECT


async def compose_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_compose[update.effective_user.id]['subject'] = update.message.from_user
    await update.message.reply_text('Enter email body:')
    return COMPOSE_BODY


async def compose_body(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_compose[update.effective_user.id]['body'] = update.message.from_user
    await update.message.reply_text(
        f"Your email will be sent to {user_compose[update.effective_user.id]['to']}"
        f"with the subject {user_compose[update.effective_user.id]['subject']}",
        f"with the body:\n\n{user_compose[update.effective_user.id]['body']}",
        reply_markup=ReplyKeyboardMarkup(
            [['send', 'cancel']],
            one_time_keyboard=True,
            input_field_placeholder="Send?"
        ))
    return COMPOSE_SEND


async def compose_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # await update.message.reply_text('Sending an email for you...')
    access_token = user_access_tokens[update.effective_user.id]
    message = {
        'message': {
            'subject': user_compose[update.effective_user.id]['subject'],
            'body': {
                'contentType': 'Text',
                'content': user_compose[update.effective_user.id]['body']
            },
            'toRecipients': [
                {
                    'emailAddress': {
                        'address': user_compose[update.effective_user.id]['to']
                    }
                }
            ]
        }
    }
    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail", json=message, headers=dict(Authorization=access_token))
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Sent successfully! {response.text}'
    )
    return ConversationHandler.END


async def compose_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Compose email cancelled'
    )
    user_compose[update.effective_user.id] = dict()
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in user_access_tokens:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Hi {user_names[update.effective_user.id]}, I'm a bot!")
    else:
        await run_login_sequence(update, context)


def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('unread', display_unread_emails))
    application.add_handler(CommandHandler('send', compose_send))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('compose', compose_start)],
        states={
            COMPOSE_TO: [MessageHandler(
                telegram.ext.filters.TEXT, compose_to)],
            COMPOSE_SUBJECT: [MessageHandler(
                telegram.ext.filters.TEXT, compose_subject)],
            COMPOSE_BODY: [MessageHandler(
                telegram.ext.filters.TEXT, compose_body)],
            COMPOSE_SEND: [MessageHandler(
                telegram.ext.filters.Text(['send']), compose_send)]
        },
        fallbacks=[MessageHandler(
            telegram.ext.filters.Text(['cancel']), compose_cancel)]
    ))
    application.run_polling()


if __name__ == '__main__':
    main()
