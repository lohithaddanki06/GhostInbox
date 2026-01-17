import os, requests, random, string, logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TimedOut, NetworkError

# Set up logging to see errors in VS Code terminal
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

def generate_email():
    """Generates a random username for 1secmail."""
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return user, f"{user}@1secmail.com"

async def check_email_api(user):
    """Safely fetches email list from API to prevent JSONDecodeError."""
    url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={user}&domain=1secmail.com"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and response.text.strip():
            return response.json()
    except Exception as e:
        logging.error(f"API Fetch Error: {e}")
    return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Standard welcome message."""
    keyboard = [[InlineKeyboardButton("👻 Generate Ghost Inbox", callback_data='gen_mail')]]
    await update.message.reply_text(
        "Welcome to **GhostInbox**! 👻\n\nI provide temporary emails and notify you instantly when mail arrives.",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def auto_check_job(context: ContextTypes.DEFAULT_TYPE):
    """Background task: Notifies user of new mail."""
    job = context.job
    user = job.data['user']
    last_count = job.data.get('last_count', 0)
    
    msgs = await check_email_api(user)
    
    if len(msgs) > last_count:
        job.data['last_count'] = len(msgs)
        new_mail = msgs[0]
        text = (f"🔔 **GhostInbox Alert!**\n\n"
                f"📬 New mail from: `{new_mail['from']}`\n"
                f"📝 Subject: {new_mail['subject']}\n\n"
                f"Click Refresh below to see the count.")
        await context.bot.send_message(chat_id=job.chat_id, text=text, parse_mode='Markdown')

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all button interactions."""
    query = update.callback_query
    await query.answer()
    
    # 1. GENERATE OR RESET EMAIL
    if query.data in ['gen_mail', 'reset_mail']:
        # Clear existing background watchers for this user
        current_jobs = context.job_queue.get_jobs_by_name(str(query.message.chat_id))
        for job in current_jobs: job.schedule_removal()

        user, email = generate_email()
        context.user_data['email_user'] = user
        
        # Start a new 10-second watcher
        context.job_queue.run_repeating(
            auto_check_job, interval=10, first=10, 
            chat_id=query.message.chat_id, name=str(query.message.chat_id),
            data={'user': user, 'last_count': 0}
        )

        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Inbox", callback_data='check_mail')],
            [InlineKeyboardButton("🗑️ Delete & New Email", callback_data='reset_mail')]
        ]
        await query.edit_message_text(
            f"✅ **Your Ghost Email is Live!**\n\n`{email}`\n\nWatcher active: I will 'ding' you when mail arrives.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )

    # 2. REFRESH / CHECK STATUS
    elif query.data == 'check_mail':
        user = context.user_data.get('email_user')
        msgs = await check_email_api(user)
        if not msgs:
            await query.answer("Inbox is empty. Waiting...", show_alert=True)
        else:
            msg_list = "\n".join([f"📩 {m['from']} - {m['subject']}" for m in msgs[:5]])
            await query.message.reply_text(f"📬 **Recent Messages:**\n{msg_list}\n\nTo read full text, wait for the notification!", parse_mode='Markdown')

if __name__ == '__main__':
    # Build with increased timeouts to prevent 'TimedOut' errors
    app = (Application.builder()
           .token(TOKEN)
           .connect_timeout(30).read_timeout(30).write_timeout(30)
           .build())
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    
    print("GhostInbox 2026 Edition is running...")
    app.run_polling(drop_pending_updates=True)