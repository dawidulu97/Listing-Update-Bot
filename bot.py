import os
import feedparser
import requests
import time
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler

# Configuration
TELEGRAM_TOKEN = "7900731557:AAH11XcaZXxnax9MrtFPsd_VUBEkT6NJkCo"
CHAT_ID = "6848532238"
EBAY_RSS_URL = "https://www.ebay.com/sch/i.html?_saslop=1&_sasl=eliminatethedigitaldivide&_rss=1"
CHECK_INTERVAL = 300  # 5 minutes
MAX_INITIAL_ITEMS = 5  # Number of current listings to show at startup

# Track last seen items
last_items = set()
bot = Bot(token=TELEGRAM_TOKEN)

def send_message(text):
    """Helper function to send Telegram messages"""
    bot.send_message(chat_id=CHAT_ID, text=text)

def get_feed_items():
    """Fetch and parse RSS feed items"""
    feed = feedparser.parse(EBAY_RSS_URL)
    return [(entry.link, entry.title) for entry in feed.entries]

def format_item(title, link):
    """Format item for Telegram message"""
    return f"🆕 {title}\n🔗 {link}"

def show_current_listings():
    """Display current listings when bot starts"""
    try:
        items = get_feed_items()
        if not items:
            send_message("ℹ️ No current listings found")
            return

        send_message(f"📋 Current Listings (Showing {min(MAX_INITIAL_ITEMS, len(items))} most recent):")
        
        for link, title in items[:MAX_INITIAL_ITEMS]:
            send_message(format_item(title, link))
            time.sleep(0.5)  # Avoid rate limits

        # Initialize last_items with current items
        global last_items
        last_items = {link for link, _ in items}
        
    except Exception as e:
        send_message(f"❌ Error fetching current listings: {str(e)}")

def check_new_listings():
    """Check for and notify about new listings"""
    global last_items
    
    try:
        current_items = get_feed_items()
        if not current_items:
            return

        current_links = {link for link, _ in current_items}
        new_links = current_links - last_items

        if new_links:
            send_message(f"🔔 New Items Found ({len(new_links)})")
            for link, title in current_items:
                if link in new_links:
                    send_message(format_item(title, link))
                    time.sleep(0.5)
            
            last_items = current_links
            
    except Exception as e:
        send_message(f"❌ Error checking new listings: {str(e)}")

def start(update: Update, context):
    """Handle /start command"""
    update.message.reply_text('🔄 Starting eBay Monitor...')
    show_current_listings()

def main():
    """Run the bot"""
    # Send startup notification
    send_message(f"🤖 eBay Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Show current listings
    show_current_listings()
    
    # Set up command handler
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    
    # Start periodic checking
    while True:
        check_new_listings()
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
