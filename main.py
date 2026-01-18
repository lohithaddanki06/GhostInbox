import os
import requests
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest
from dotenv import load_dotenv

import sys
import asyncio

# This fix specifically targets the "GetQueuedCompletionStatus" error on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
# REPLACE WITH YOUR CHANNEL ID (Starts with -100) OR USERNAME (e.g., '@MyChannel')
CHANNEL_ID = "@@ghost_inboxbot" 
CHANNEL_LINK = ""

# Logging setup
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- MAIL.TM API FUNCTIONS (Ultra Reliable) ---
BASE_URL = "https://api.mail.tm"

def get_mail_domain():
    try:
        res = requests.get(f"{BASE_URL}/domains")
        return res.json()['hydra:member'][0]['domain']
    except: return "ez-mail.ws"

def create_temp_account():
    domain = get_mail_domain()
    # Generate random string for login
    import uuid
    username = str(uuid.uuid4())[:8]
    email = f"{username}@{domain}"
    password = "DefaultPassword123"
    
    payload = {"address": email, "password": password}
    res = requests.post(f"{BASE_URL}/accounts", json=payload)
    if res.status_code == 201:
        # Get Token
        token_res = requests.post(f"{BASE_URL}/token", json=payload)
        return email, token_res.json()['token']
    return None, None

def fetch_messages(token):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/messages", headers=headers)
    return res.json().get('hydra:member', [])

# --- MIDDLEWARE: FORCE JOIN CHECK ---
async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except BadRequest:
        return True # If bot isn't admin in channel, don't block users

# --- BOT COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This is the keyboard the user sees when they first start the bot
    keyboard = [
        [InlineKeyboardButton("📧 Generate Email", callback_data='gen_mail')],
        [
            # This button opens the user's contact list and prepares a message
            InlineKeyboardButton(
                "🚀 Share with Friends", 
                switch_inline_query="Check out this cool Temp Mail bot for students! 👻"
            )
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 **Welcome to GhostInbox**\n\nProtect your privacy with instant temporary emails. "
        "I'll notify you automatically when you receive a message!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def generate_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Determine if this is from a button or a command
    msg = update.callback_query.message if update.callback_query else update.message
    
    await msg.reply_text("⏳ Generating secure inbox...")
    email, token = create_temp_account()
    
    if email:
        context.user_data['email'] = email
        context.user_data['token'] = token
        keyboard = [[InlineKeyboardButton("📬 Check Messages", callback_data='check_mail')]]
        await msg.reply_text(
            f"✅ **Your Temp Email:**\n`{email}`\n\nI will notify you here when you get mail!",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
    else:
        await msg.reply_text("❌ Server busy. Please try again.")

async def check_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = context.user_data.get('token')
    msg = update.callback_query.message if update.callback_query else update.message

    if not token:
        await msg.reply_text("❌ No active inbox. Use /new first.")
        return

    messages = fetch_messages(token)
    if not messages:
        await msg.reply_text("📭 Inbox is empty. (Wait 10-30 seconds after sender hits send)")
    else:
        text = "📬 **Incoming Mail:**\n\n"
        for m in messages[:3]:
            text += f"From: {m['from']['address']}\nSub: {m['subject']}\n---\n"
        await msg.reply_text(text, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_sub":
        await start(update, context)
    elif query.data == "new_mail":
        await generate_email(update, context)
    elif query.data == "check_mail":
        await check_inbox(update, context)

# --- EXECUTION ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", generate_email))
    app.add_handler(CommandHandler("check", check_inbox))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 GhostInbox is Online!")
    app.run_polling()