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
EBAY_STORE_URL = "https://www.ebay.com/str/eliminatethedigitaldivide"
CHECK_INTERVAL = 300  # 5 minutes
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
last_items = set()

def send_message(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")

def get_rss_items():
    """Parse RSS feed with proper error handling"""
    try:
        feed = feedparser.parse(EBAY_RSS_URL)
        if feed.bozo:  # Check for feed parsing errors
            logger.error(f"RSS feed error: {feed.bozo_exception}")
            return []
            
        items = []
        for entry in feed.entries:
            link = entry.get('link', '') or entry.get('guid', '')
            title = (entry.get('title', '') or '').strip()
            if link and "prodesk" in title.lower():
                items.append((link, title))
        
        logger.info(f"Found {len(items)} items in RSS")
        return items
        
    except Exception as e:
        logger.error(f"RSS parsing error: {e}")
        return []

def get_store_items():
    """Fallback to direct store page scraping"""
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(EBAY_STORE_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Simple text search as fallback
        if "prodesk" in response.text.lower():
            return [(EBAY_STORE_URL, "HP ProDesk (found via store page)")]
        return []
        
    except Exception as e:
        logger.error(f"Store page error: {e}")
        return []

def format_item(title, link):
    return f"🖥️ HP ProDesk Alert!\n{title}\n🔗 {link}"

def check_listings():
    global last_items
    
    try:
        # Try RSS first
        current_items = get_rss_items()
        
        # Fallback to store page if RSS fails
        if not current_items:
            current_items = get_store_items()
        
        if not current_items:
            logger.info("No items found in either source")
            return

        current_links = {item[0] for item in current_items}
        new_links = current_links - last_items

        if new_links:
            send_message("🎉 New HP ProDesk Found!")
            for link, title in current_items:
                if link in new_links:
                    send_message(format_item(title, link))
                    time.sleep(1)
            
            last_items = current_links
            
    except Exception as e:
        logger.error(f"Check error: {e}")
        send_message(f"⚠️ Temporary error: {str(e)[:100]}...")

def main():
    send_message(f"🤖 HP ProDesk Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Initial check
    initial_items = get_rss_items() or get_store_items()
    if initial_items:
        send_message(f"📋 Found {len(initial_items)} current listings:")
        for link, title in initial_items:
            send_message(format_item(title, link))
            time.sleep(1)
        
        global last_items
        last_items = {item[0] for item in initial_items}
    else:
        send_message("ℹ️ No current listings found. Monitoring for new items...")

    # Monitoring loop
    while True:
        check_listings()
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        send_message(f"🆘 Bot crashed: {str(e)}")
        raise
