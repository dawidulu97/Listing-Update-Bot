import requests
import time
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
import logging
import asyncio
import re

# Configuration
TELEGRAM_TOKEN = "7900731557:AAH11XcaZXxnax9MrtFPsd_VUBEkT6NJkCo"
CHAT_ID = "6848532238"
EBAY_SEARCH_URL = "https://www.ebay.com/sch/i.html?_nkw=hp+prodesk&_saslop=1&_sasl=eliminatethedigitaldivide"
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

def get_listings():
    """Get listings through direct HTML scraping with robust error handling"""
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(
            EBAY_SEARCH_URL,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        # Basic HTML parsing with regex (no BeautifulSoup dependency)
        items = []
        item_pattern = re.compile(r'<li class="s-item.*?<a href="(.*?)".*?<span role="heading".*?>(.*?)</span>', re.DOTALL)
        
        for match in item_pattern.finditer(response.text):
            link, title = match.groups()
            title = re.sub(r'<.*?>', '', title).strip()  # Remove HTML tags
            if "prodesk" in title.lower():
                items.append((link, title))
        
        logger.info(f"Found {len(items)} HP ProDesk listings")
        return items
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected parsing error: {e}")
        return []

def format_item(title, link):
    return f"🖥️ HP ProDesk Alert!\n{title}\n🔗 {link}"

async def check_listings():
    """Check for new listings and notify"""
    global last_items
    
    try:
        current_items = get_listings()
        if not current_items:
            logger.info("No items found in current check")
            return

        current_links = {item[0] for item in current_items}
        new_links = current_links - last_items

        if new_links:
            await send_message(f"🎉 Found {len(new_links)} new HP ProDesk listing(s)!")
            for link, title in current_items:
                if link in new_links:
                    await send_message(format_item(title, link))
                    await asyncio.sleep(1)  # Rate limiting
            
            last_items = current_links
            
    except Exception as e:
        logger.error(f"Check error: {e}")
        await send_message(f"⚠️ Temporary error: {str(e)[:100]}...")

async def main():
    """Main async function"""
    await send_message(f"🤖 HP ProDesk Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Initial check
    initial_items = get_listings()
    if initial_items:
        await send_message(f"📋 Found {len(initial_items)} current HP ProDesk listings:")
        for link, title in initial_items:
            await send_message(format_item(title, link))
            await asyncio.sleep(1)
        
        global last_items
        last_items = {item[0] for item in initial_items}
    else:
        await send_message("ℹ️ No current HP ProDesk listings found. Monitoring for new items...")

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
