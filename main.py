import os, requests, logging, asyncio, uuid, sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# 1. WINDOWS STABILITY FIX
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 2. SETUP
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://api.mail.tm"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- MAIL.TM API FUNCTIONS ---
def fetch_messages(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/messages", headers=headers)
        return res.json().get('hydra:member', [])
    except Exception as e:
        logging.error(f"Fetch Error: {e}")
        return []

def get_message_content(message_id, token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/messages/{message_id}", headers=headers)
        data = res.json()
        return data.get('text', data.get('intro', "No content available."))
    except Exception as e:
        logging.error(f"Read Error: {e}")
        return "❌ Error retrieving message content."

def delete_mail(message_id, token):
    """Deletes a specific message from the server."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.delete(f"{BASE_URL}/messages/{message_id}", headers=headers)
        return res.status_code == 204
    except Exception as e:
        logging.error(f"Delete Error: {e}")
        return False

# --- TIMER: CONTINUOUS COUNTDOWN ---
async def update_timer(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    job.data['time_left'] -= 1
    
    if job.data['time_left'] <= 0:
        try:
            await context.bot.edit_message_text(
                chat_id=job.chat_id,
                message_id=job.data['message_id'],
                text=f"❌ **Session Expired!**\nThe inbox for `{job.data['email']}` is now deleted."
            )
        except: pass
        return job.schedule_removal()

    keyboard = [[InlineKeyboardButton("📬 Check Inbox", callback_data='check_mail')]]
    try:
        await context.bot.edit_message_text(
            chat_id=job.chat_id,
            message_id=job.data['message_id'],
            text=f"✅ **Your Temp Email:**\n`{job.data['email']}`\n\n🕒 **Expires in:** {job.data['time_left']} minutes",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except: pass 

# --- BOT COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_url = "https://t.me/ghost_inboxbot"
    share_text = "Get free temp mail with GhostInbox! 👻"
    direct_share_link = f"https://t.me/share/url?url={bot_url}&text={share_text}"

    keyboard = [
        [InlineKeyboardButton("📧 Generate Email", callback_data='new_mail')],
        [InlineKeyboardButton("🚀 Share with Friends", url=direct_share_link)]
    ]
    await update.message.reply_text(
        "👋 **Welcome to GhostInbox**\n\nI provide temporary emails valid for **10 minutes**.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def generate_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    msg = query.message if query else update.message
    status_msg = await msg.reply_text("⏳ Securing your temporary inbox...")
    
    try:
        res_dom = requests.get(f"{BASE_URL}/domains").json()
        domain = res_dom['hydra:member'][0]['domain']
        email = f"{uuid.uuid4().hex[:8]}@{domain}"
        password = "DefaultPassword123"
        
        requests.post(f"{BASE_URL}/accounts", json={"address": email, "password": password})
        token_res = requests.post(f"{BASE_URL}/token", json={"address": email, "password": password}).json()
        
        if 'token' in token_res:
            context.user_data['token'] = token_res['token']
            context.job_queue.run_repeating(
                update_timer, interval=60, first=60,
                chat_id=msg.chat_id,
                data={'message_id': status_msg.message_id, 'time_left': 10, 'email': email}
            )
            
            keyboard = [[InlineKeyboardButton("📬 Check Inbox", callback_data='check_mail')]]
            await status_msg.edit_text(
                f"✅ **Your Temp Email:**\n`{email}`\n\n🕒 **Expires in:** 10 minutes",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    except Exception:
        await status_msg.edit_text("❌ Server busy. Try /start again.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    token = context.user_data.get('token')
    
    if data == "new_mail":
        await generate_email(update, context)
        
    elif data == "check_mail":
        if not token:
            await query.answer("❌ Session expired!", show_alert=True)
            return

        await query.answer("Checking inbox...")
        messages = fetch_messages(token)
        
        if not messages:
            await query.message.reply_text("📭 Inbox is empty.")
        else:
            for m in messages[:3]:
                sender = m['from']['address']
                subject = m['subject']
                msg_id = m['id']
                
                keyboard = [
                    [InlineKeyboardButton("📖 Read", callback_data=f"read_{msg_id}"),
                     InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{msg_id}")]
                ]
                
                await query.message.reply_text(
                    f"👤 **From:** {sender}\n📝 **Sub:** {subject}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )

    elif data.startswith("read_"):
        await query.answer("Fetching content...")
        msg_id = data.split("_")[1]
        content = get_message_content(msg_id, token)
        
        # Add a delete button at the bottom of the email too
        keyboard = [[InlineKeyboardButton("🗑️ Delete this Email", callback_data=f"del_{msg_id}")]]
        
        await query.message.reply_text(
            f"📧 **Full Message Content:**\n\n{content}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif data.startswith("del_"):
        msg_id = data.split("_")[1]
        success = delete_mail(msg_id, token)
        
        if success:
            await query.message.delete()
            await query.answer("✅ Message deleted.", show_alert=False)
        else:
            await query.answer("❌ Failed to delete.", show_alert=True)

# --- EXECUTION ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", generate_email))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 GhostInbox Online with Read/Delete features!")
    app.run_polling()