import feedparser
import requests
import time
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
import logging
import asyncio

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

async def send_message(text):
    """Proper async message sending with error handling"""
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text)
    except TelegramError as e:
        logger.error(f"Failed to send message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")

def get_rss_items():
    """Parse RSS feed with improved error handling"""
    try:
        feed = feedparser.parse(EBAY_RSS_URL)
        if feed.bozo and feed.bozo_exception:
            logger.error(f"RSS feed error: {str(feed.bozo_exception)}")
            return []
            
        items = []
        for entry in feed.entries:
            try:
                link = entry.get('link', '') or entry.get('guid', '')
                title = (entry.get('title', '') or '').strip()
                if link and "prodesk" in title.lower():
                    items.append((link, title))
            except Exception as e:
                logger.error(f"Error processing RSS entry: {e}")
                continue
        
        logger.info(f"Found {len(items)} items in RSS")
        return items
        
    except Exception as e:
        logger.error(f"RSS parsing error: {e}")
        return []

def get_store_items():
    """Fallback to direct store page with better timeout handling"""
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(EBAY_STORE_URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Simple text search as fallback
        if "prodesk" in response.text.lower():
            return [(EBAY_STORE_URL, "HP ProDesk (found via store page)")]
        return []
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Store page error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected store page error: {e}")
        return []

def format_item(title, link):
    return f"🖥️ HP ProDesk Alert!\n{title}\n🔗 {link}"

async def check_listings():
    """Async version of listing checker"""
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
            await send_message("🎉 New HP ProDesk Found!")
            for link, title in current_items:
                if link in new_links:
                    await send_message(format_item(title, link))
                    await asyncio.sleep(1)  # Rate limiting
            
            last_items = current_links
            
    except Exception as e:
        logger.error(f"Check error: {e}")
        await send_message(f"⚠️ Temporary error: {str(e)[:100]}...")

async def main():
    """Async main function"""
    await send_message(f"🤖 HP ProDesk Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Initial check
    initial_items = get_rss_items() or get_store_items()
    if initial_items:
        await send_message(f"📋 Found {len(initial_items)} current listings:")
        for link, title in initial_items:
            await send_message(format_item(title, link))
            await asyncio.sleep(1)
        
        global last_items
        last_items = {item[0] for item in initial_items}
    else:
        await send_message("ℹ️ No current listings found. Monitoring for new items...")

    # Monitoring loop
    while True:
        await check_listings()
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        # Can't send message here since event loop is closing
