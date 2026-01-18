import os, requests, logging, asyncio, uuid, sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# 1. WINDOWS STABILITY FIX
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://api.mail.tm"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- MAIL API FUNCTIONS ---
def fetch_messages(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/messages", headers=headers)
        return res.json().get('hydra:member', [])
    except: return []

# --- TIMER: DYNAMIC COUNTDOWN ---
async def update_timer(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    job.data['time_left'] -= 1
    
    if job.data['time_left'] <= 0:
        try:
            await context.bot.edit_message_text(
                chat_id=job.chat_id,
                message_id=job.data['message_id'],
                text="⚠️ **Session Expired!**\nThis inbox has been deleted. Click /start to get a new one."
            )
        except: pass
        return job.schedule_removal()

    # Update message text with remaining time
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
    keyboard = [
        [InlineKeyboardButton("📧 Generate Email", callback_data='new_mail')],
        [InlineKeyboardButton("🚀 Share with Friends", switch_inline_query="Get free temp mail here! 👻")]
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
        # API Logic
        res_dom = requests.get(f"{BASE_URL}/domains").json()
        domain = res_dom['hydra:member'][0]['domain']
        email = f"{uuid.uuid4().hex[:8]}@{domain}"
        password = "DefaultPassword123"
        
        requests.post(f"{BASE_URL}/accounts", json={"address": email, "password": password})
        token_res = requests.post(f"{BASE_URL}/token", json={"address": email, "password": password}).json()
        
        if 'token' in token_res:
            context.user_data['token'] = token_res['token']
            
            # Start Countdown Timer
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
    except Exception as e:
        await status_msg.edit_text("❌ API Error. Try again in a moment.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "new_mail":
        await generate_email(update, context)
    elif data == "check_mail":
        token = context.user_data.get('token')
        if not token:
            await query.message.reply_text("❌ Session expired. Start again.")
            return
        
        messages = fetch_messages(token)
        if not messages:
            await query.answer("Empty inbox.", show_alert=False)
            await query.message.reply_text("📭 No messages yet.")
        else:
            text = "📬 **Recent Messages:**\n\n"
            for m in messages[:3]:
                text += f"From: {m['from']['address']}\nSub: {m['subject']}\n---\n"
            await query.message.reply_text(text, parse_mode='Markdown')

# --- EXECUTION ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 GhostInbox is Online!")
    app.run_polling()