# 👻 GhostInbox: Secure Temp-Mail Automation

![Project Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)
![Security](https://img.shields.io/badge/Privacy-Focused-red)

**GhostInbox** is a lightweight, high-utility Telegram bot that provides instant, disposable email addresses. Built with privacy in mind, it allows users to receive verification codes and messages without exposing their primary email to potential spam or data breaches.

---

## 🚀 Key Features

- **⚡ Instant Provisioning:** Generate a fresh `@1secmail.com` address with a single tap.
- **🔔 Real-time Notifications:** An automated background watcher monitors the inbox every 10 seconds and alerts you immediately when new mail arrives.
- **🔐 Privacy-Centric:** No email logs, content, or personal user data are stored permanently on our servers.
- **🔄 Session Management:** Easily discard current addresses and cycle to new ones to ensure a clean slate for every signup.
- **🛠️ Robust Architecture:** Engineered with advanced error-handling for API hiccups (`JSONDecodeError`) and network stability.

---

## 📁 Project Structure

```text
GhostInbox/
├── main.py             # Main application logic & background job scheduler
├── .env                # Environment variables (API tokens)
├── requirements.txt    # Project dependencies
├── README.md           # Documentation

Installation & Setup
1. Clone & Install
Ensure you have Python 3.10+ installed. Clone this repository and install the required dependencies:

Bash

pip install -r requirements.txt
2. Configure Environment
Create a .env file in the root directory and add your bot token provided by @BotFather:

Code snippet

BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
3. Run the Bot
Start the application locally:

Bash

python main.py
⚙️ How it Works
User Interaction: The user initiates a request via the /start command or inline buttons.

API Integration: The bot interfaces with the 1secmail API to fetch temporary credentials.

Background Watcher: A background JobQueue is established to poll the API for new incoming messages without interrupting the user experience.

Data Delivery: Once a message is detected, the bot parses the metadata and sends a push notification directly to the user's Telegram chat.