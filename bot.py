import feedparser
import requests
import time
from datetime import datetime
from telegram import Bot
import logging

# Configuration
TELEGRAM_TOKEN = "7900731557:AAH11XcaZXxnax9MrtFPsd_VUBEkT6NJkCo"
CHAT_ID = "6848532238"
EBAY_RSS_URL = "https://www.ebay.com/sch/i.html?_saslop=1&_sasl=eliminatethedigitaldivide&_rss=1"
CHECK_INTERVAL = 300  # 5 minutes
MAX_INITIAL_ITEMS = 5

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
last_items = set()

def send_message(text):
    """Send message with error handling"""
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")

def get_feed_items():
    """Improved RSS feed parser with better item detection"""
    try:
        feed = feedparser.parse(EBAY_RSS_URL)
        if not feed.entries:
            logger.warning(f"No entries found in feed. Feed status: {feed.get('status')}")
            return []

        items = []
        for entry in feed.entries:
            # Extract item ID from link or guid
            link = entry.get('link', '')
            if not link:
                link = entry.get('guid', '')
            
            # Some eBay feeds put title in description
            title = entry.get('title', '') or entry.get('description', 'No Title')
            
            # Clean up title
            title = ' '.join(title.split())  # Remove extra whitespace
            
            # Get publication date
            pub_date = entry.get('published', '')
            
            if link:
                items.append((link, title, pub_date))
        
        logger.info(f"Found {len(items)} items in feed")
        return items

    except Exception as e:
        logger.error(f"Error parsing feed: {e}")
        send_message(f"⚠️ Feed parsing error: {str(e)}")
        return []

def format_item(title, link, pub_date=""):
    """Format item message with emoji"""
    date_str = f"\n⌚ {pub_date}" if pub_date else ""
    return f"🛍️ {title}{date_str}\n🔗 {link}"

def check_new_listings():
    """Check for new listings and notify"""
    global last_items
    
    try:
        current_items = get_feed_items()
        if not current_items:
            logger.info("No items found in current check")
            return

        current_links = {item[0] for item in current_items}
        new_links = current_links - last_items

        if new_links:
            send_message(f"🎉 New Item Found!")
            for link, title, pub_date in current_items:
                if link in new_links:
                    send_message(format_item(title, link, pub_date))
                    time.sleep(1)  # Rate limiting
            
            last_items = current_links
        else:
            logger.info("No new items detected")

    except Exception as e:
        logger.error(f"Error in check_new_listings: {e}")
        send_message(f"❌ Error checking listings: {str(e)}")

def main():
    """Main bot function"""
    send_message(f"🤖 eBay Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Initial check
    initial_items = get_feed_items()
    if initial_items:
        send_message(f"📋 Found {len(initial_items)} current listings:")
        for link, title, pub_date in initial_items[:MAX_INITIAL_ITEMS]:
            send_message(format_item(title, link, pub_date))
            time.sleep(1)
        
        global last_items
        last_items = {item[0] for item in initial_items}
    else:
        send_message("ℹ️ No current listings found")
        # Send debug info
        feed = feedparser.parse(EBAY_RSS_URL)
        send_message(f"Feed status: {feed.get('status', 'Unknown')}\nEntries: {len(feed.entries)}")

    # Start monitoring loop
    while True:
        check_new_listings()
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        send_message(f"🆘 Bot crashed: {str(e)}")
        raise
