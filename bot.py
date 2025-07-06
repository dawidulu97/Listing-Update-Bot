import os
import feedparser
import requests
import time
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler

# Configuration
TELEGRAM_TOKEN = "7900731557:AAH11XcaZXxnax9MrtFPsd_VUBEkT6NJkCo"
CHAT_ID = "6848532238"
EBAY_RSS_URL = "https://www.ebay.com/sch/i.html?_saslop=1&_sasl=eliminatethedigitaldivide&_rss=1"
CHECK_INTERVAL = 300  # 5 minutes

# Initialize bot
bot = Bot(token=TELEGRAM_TOKEN)
last_checked = time.time()

def start(update: Update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('✅ eBay Monitor Bot Started!')
    check_feed()

def check_feed():
    """Check RSS feed for new items"""
    global last_checked
    
    try:
        feed = feedparser.parse(EBAY_RSS_URL)
        new_items = [item for item in feed.entries if time.mktime(item.published_parsed) > last_checked]
        
        if new_items:
            for item in new_items:
                message = f"🆕 New Listing:\n{item.title}\n🔗 {item.link}"
                bot.send_message(chat_id=CHAT_ID, text=message)
                time.sleep(1)  # Avoid rate limits
        
        last_checked = time.time()
        
    except Exception as e:
        bot.send_message(chat_id=CHAT_ID, text=f"❌ Error: {str(e)}")

def main():
    """Start the bot"""
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    
    # Send startup message
    bot.send_message(chat_id=CHAT_ID, text="🤖 eBay Monitor Bot Started!")
    
    # Check feed periodically
    while True:
        check_feed()
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
