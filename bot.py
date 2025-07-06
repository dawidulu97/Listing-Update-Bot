import requests
import re
import time
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
import logging
import asyncio

# Configuration
TELEGRAM_TOKEN = "7900731557:AAH11XcaZXxnax9MrtFPsd_VUBEkT6NJkCo"
CHAT_ID = "6848532238"
SELLER_URL = "https://www.ebay.com/str/eliminatethedigitaldivide"
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
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text)
    except TelegramError as e:
        logger.error(f"Failed to send message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")

def extract_listings(html):
    """Extract all listings from HTML"""
    items = []
    pattern = re.compile(
        r'<li class="s-item.*?<a href="(.*?)".*?<span role="heading".*?>(.*?)</span>.*?<span class="s-item__price">(.*?)</span>',
        re.DOTALL
    )
    
    for match in pattern.finditer(html):
        link, title, price = match.groups()
        title = re.sub(r'<.*?>', '', title).strip()
        price = re.sub(r'<.*?>', '', price).strip()
        items.append((link, title, price))
    
    return items

def get_current_listings():
    """Get all current listings from seller page"""
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(SELLER_URL, headers=headers, timeout=15)
        response.raise_for_status()
        return extract_listings(response.text)
    except Exception as e:
        logger.error(f"Error getting listings: {e}")
        return []

async def show_all_listings():
    """Display all current listings at startup"""
    listings = get_current_listings()
    if not listings:
        await send_message("ℹ️ No current listings found")
        return
    
    await send_message(f"📋 Current Inventory ({len(listings)} items):")
    
    for i, (link, title, price) in enumerate(listings[:50], 1):  # Limit to first 50 items
        message = f"{i}. {title}\n💵 {price}\n🔗 {link}"
        await send_message(message)
        await asyncio.sleep(0.3)  # Rate limiting
    
    global last_items
    last_items = {item[0] for item in listings}

async def check_new_listings():
    """Check for any new listings"""
    global last_items
    
    listings = get_current_listings()
    if not listings:
        return
    
    current_items = {item[0] for item in listings}
    new_items = current_items - last_items
    
    if new_items:
        await send_message(f"🆕 New Listings Found ({len(new_items)})!")
        for link, title, price in listings:
            if link in new_items:
                message = f"📦 {title}\n💵 {price}\n🔗 {link}"
                await send_message(message)
                await asyncio.sleep(0.5)
        
        last_items = current_items

async def main():
    await send_message(f"🤖 eBay Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Show all current listings
    await show_all_listings()
    
    # Start monitoring for new items
    while True:
        await check_new_listings()
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
