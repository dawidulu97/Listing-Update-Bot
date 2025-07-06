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
    "https://www.ebay.com/sch/i.html?_saslop=1&_sasl=eliminatethedigitaldivide"
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

def extract_listings(html):
    """Improved listing extraction with multiple patterns"""
    items = []
    patterns = [
        r'<li class="s-item.*?<a href="(.*?)".*?<span role="heading".*?>(.*?)</span>.*?<span class="s-item__price">(.*?)</span>',
        r'<div class="s-item__wrapper".*?<a href="(.*?)".*?<span class="s-item__title".*?>(.*?)</span>.*?<span class="s-item__price".*?>(.*?)</span>'
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, html, re.DOTALL):
            link, title, price = match.groups()
            title = re.sub(r'<.*?>', '', title).strip()
            price = re.sub(r'<.*?>', '', price).strip()
            items.append((link, title, price))
    
    return items

async def get_listings_with_retry():
    """Try multiple URLs with retries and random delays"""
    for _ in range(3):  # Retry up to 3 times
        try:
            url = random.choice(SELLER_URLS)
            headers = {
                'User-Agent': get_random_user_agent(),
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            # Random delay between 2-5 seconds
            await asyncio.sleep(random.uniform(2, 5))
            
            response = requests.get(
                url,
                headers=headers,
                timeout=20
            )
            response.raise_for_status()
            
            return extract_listings(response.text)
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt failed for {url}: {e}")
            await asyncio.sleep(5)  # Wait before retry
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
    
    return []

async def show_current_inventory():
    """Display all current listings with better formatting"""
    listings = await get_listings_with_retry()
    if not listings:
        await send_message("⚠️ Could not retrieve current listings. Will keep trying...")
        return
    
    # Remove duplicates
    unique_listings = []
    seen_links = set()
    for item in listings:
        if item[0] not in seen_links:
            seen_links.add(item[0])
            unique_listings.append(item)
    
    await send_message(f"📋 Current Inventory ({len(unique_listings)} items)")
    
    # Send in batches of 5 items
    for i in range(0, min(50, len(unique_listings)), 5):
        batch = unique_listings[i:i+5]
        message = "\n\n".join(
            f"{i+j+1}. {title}\n💵 {price}\n🔗 {link}"
            for j, (link, title, price) in enumerate(batch)
        )
        await send_message(message)
        await asyncio.sleep(1)  # Rate limiting
    
    global last_items
    last_items = {item[0] for item in unique_listings}

async def monitor_new_items():
    """Monitor for new listings with improved reliability"""
    global last_items
    
    while True:
        try:
            listings = await get_listings_with_retry()
            if not listings:
                logger.info("No listings retrieved in this check")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            current_items = {item[0] for item in listings}
            new_items = current_items - last_items
            
            if new_items:
                new_listings = [item for item in listings if item[0] in new_items]
                await send_message(f"🆕 New Listings Found ({len(new_listings)})!")
                
                for link, title, price in new_listings:
                    message = f"📦 {title}\n💵 {price}\n🔗 {link}"
                    await send_message(message)
                    await asyncio.sleep(1)
                
                last_items = current_items
            
            await asyncio.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            await send_message(f"⚠️ Temporary monitoring error: {str(e)[:100]}...")
            await asyncio.sleep(CHECK_INTERVAL * 2)  # Longer wait after errors

async def main():
    await send_message(f"🤖 eBay Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Initial inventory check
    await show_current_inventory()
    
    # Start continuous monitoring
    await monitor_new_items()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        # Can't send message here since event loop is closed
