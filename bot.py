import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from telegram import Bot
import logging
import feedparser

# Configuration
TELEGRAM_TOKEN = "7900731557:AAH11XcaZXxnax9MrtFPsd_VUBEkT6NJkCo"
CHAT_ID = "6848532238"
EBAY_URL = "https://www.ebay.com/str/eliminatethedigitaldivide"
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

def get_html_items():
    """Parse items directly from HTML as fallback"""
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(EBAY_URL, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        items = []
        
        # Try different selectors for eBay listings
        for selector in ['.s-item', '.srp-results .s-item']:
            listings = soup.select(selector)
            if listings:
                break
                
        for item in listings:
            try:
                title_elem = item.select_one('.s-item__title')
                link_elem = item.select_one('.s-item__link')
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link = link_elem['href']
                    
                    # Skip "Shop on eBay" and similar non-item links
                    if "ebay.com" in link and "prodesk" in title.lower():
                        items.append((link, title))
            except Exception as e:
                logger.error(f"Error parsing item: {e}")
        
        logger.info(f"Found {len(items)} items in HTML")
        return items
        
    except Exception as e:
        logger.error(f"HTML parsing error: {e}")
        return []

def get_rss_items():
    """Try RSS feed first, fallback to HTML"""
    try:
        feed = feedparser.parse(EBAY_RSS_URL)
        if feed.entries:
            items = []
            for entry in feed.entries:
                link = entry.get('link', '') or entry.get('guid', '')
                title = entry.get('title', 'No Title')
                if link:
                    items.append((link, title))
            logger.info(f"Found {len(items)} items in RSS")
            return items
    except Exception as e:
        logger.error(f"RSS parsing error: {e}")
    
    return get_html_items()

def format_item(title, link):
    return f"🖥️ {title}\n🔗 {link}"

def check_listings():
    global last_items
    
    try:
        current_items = get_rss_items()
        if not current_items:
            logger.warning("No items found in either RSS or HTML")
            send_message("⚠️ Couldn't find any listings. Checking HTML directly...")
            current_items = get_html_items()
            if not current_items:
                send_message("❌ Still no items found. Please check the seller's page manually.")
                return

        current_links = {item[0] for item in current_items}
        new_links = current_links - last_items

        if new_links:
            send_message(f"🎉 Found {len(new_links)} new items!")
            for link, title in current_items:
                if link in new_links:
                    send_message(format_item(title, link))
                    time.sleep(1)
            
            last_items = current_links
        else:
            logger.info("No new items detected")

    except Exception as e:
        logger.error(f"Error in check_listings: {e}")
        send_message(f"❌ Error: {str(e)}")

def main():
    send_message(f"🤖 HP ProDesk Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Initial check
    initial_items = get_rss_items() or get_html_items()
    if initial_items:
        send_message(f"📋 Found {len(initial_items)} current listings:")
        for link, title in initial_items[:5]:
            if "prodesk" in title.lower():
                send_message(format_item(title, link))
                time.sleep(1)
        
        global last_items
        last_items = {item[0] for item in initial_items}
    else:
        send_message("ℹ️ No current listings found. Will keep checking...")

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
