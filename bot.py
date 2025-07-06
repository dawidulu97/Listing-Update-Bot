import requests
import re
import time
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
import logging
import asyncio
import random

# Configuration
TELEGRAM_TOKEN = "7900731557:AAH11XcaZXxnax9MrtFPsd_VUBEkT6NJkCo"
CHAT_ID = "6848532238"
SELLER_URLS = [
    "https://www.ebay.com/str/eliminatethedigitaldivide",
    "https://www.ebay.com/sch/i.html?_saslop=1&_sasl=eliminatethedigitaldivide",
    "https://www.ebay.com/sch/eliminatethedigitaldivide/m.html"
]
CHECK_INTERVAL = 600  # 10 minutes
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

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

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def extract_listings_v1(html):
    """Primary extraction method"""
    items = []
    pattern = re.compile(
        r'<li class="s-item.*?<a href="(.*?)".*?<span role="heading".*?>(.*?)</span>.*?<span class="s-item__price">(.*?)</span>',
        re.DOTALL
    )
    for match in pattern.finditer(html):
        link, title, price = match.groups()
        items.append((
            re.sub(r'\\[uU][0-9a-fA-F]{4}', '', link),  # Clean Unicode escapes
            re.sub(r'<.*?>', '', title).strip(),
            re.sub(r'<.*?>', '', price).strip()
        ))
    return items

def extract_listings_v2(html):
    """Fallback extraction method"""
    items = []
    pattern = re.compile(
        r'<div class="s-item__info">.*?<a href="(.*?)".*?>(.*?)</a>.*?<span class="s-item__price">(.*?)</span>',
        re.DOTALL
    )
    for match in pattern.finditer(html):
        link, title, price = match.groups()
        items.append((
            link.split('?')[0],  # Clean URL parameters
            re.sub(r'<.*?>', '', title).strip()[:200],  # Limit title length
            re.sub(r'[^\d\.\$£€]', '', price)  # Clean price
        ))
    return items

async def fetch_listings():
    """Fetch listings with multiple fallback methods"""
    for url in random.sample(SELLER_URLS, len(SELLER_URLS)):
        try:
            headers = {
                'User-Agent': get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.ebay.com/',
                'DNT': '1'
            }
            
            # Random delay to avoid bot detection
            await asyncio.sleep(random.uniform(2, 5))
            
            response = requests.get(
                url,
                headers=headers,
                timeout=20
            )
            response.raise_for_status()
            
            # Try both extraction methods
            items = extract_listings_v1(response.text) or extract_listings_v2(response.text)
            if items:
                return items
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request to {url} failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error with {url}: {e}")
    
    return []

async def show_current_inventory():
    """Display current inventory with better error handling"""
    try:
        listings = await fetch_listings()
        if not listings:
            await send_message("⚠️ Could not retrieve current listings. eBay may be blocking requests.")
            return
        
        # Remove duplicates and limit to 30 items
        unique_listings = []
        seen = set()
        for item in listings:
            if item[0] not in seen:
                seen.add(item[0])
                unique_listings.append(item)
                if len(unique_listings) >= 30:
                    break
        
        await send_message(f"📋 Current Inventory ({len(unique_listings)} items)")
        
        # Send in batches
        for i in range(0, len(unique_listings), 5):
            batch = unique_listings[i:i+5]
            message = "\n\n".join(
                f"{i+j+1}. {title}\n💵 {price}\n🔗 {link}"
                for j, (link, title, price) in enumerate(batch)
            )
            await send_message(message)
            await asyncio.sleep(1)
        
        global last_items
        last_items = {item[0] for item in unique_listings}
        
    except Exception as e:
        logger.error(f"Error showing inventory: {e}")
        await send_message(f"⚠️ Inventory error: {str(e)[:100]}...")

async def monitor_listings():
    """Main monitoring loop with robust error handling"""
    global last_items
    
    while True:
        try:
            listings = await fetch_listings()
            if not listings:
                logger.info("No listings retrieved - will retry after delay")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            current_items = {item[0] for item in listings}
            new_items = current_items - last_items
            
            if new_items:
                new_listings = [item for item in listings if item[0] in new_items]
                await send_message(f"🆕 New Items Found ({len(new_listings)})!")
                
                for link, title, price in new_listings:
                    message = f"📦 {title}\n💵 {price}\n🔗 {link}"
                    await send_message(message)
                    await asyncio.sleep(1)
                
                last_items = current_items
            
            await asyncio.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            await send_message(f"⚠️ Monitoring paused due to error: {str(e)[:100]}...")
            await asyncio.sleep(CHECK_INTERVAL * 2)  # Extended wait after errors

async def main():
    await send_message(f"🤖 eBay Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    await show_current_inventory()
    await monitor_listings()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
