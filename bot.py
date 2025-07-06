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
EBAY_APP_ID = "LaptopTr-notifier-PRD-68ea2d757-571ae1d7"
SELLER_NAME = "eliminatethedigitaldivide"
CHECK_INTERVAL = 300  # 5 minutes
MAX_RETRIES = 3

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

def make_ebay_api_request():
    """Make API request with retry logic"""
    endpoint = "https://svcs.ebay.com/services/search/FindingService/v1"
    params = {
        "OPERATION-NAME": "findItemsAdvanced",
        "SERVICE-VERSION": "1.13.0",
        "SECURITY-APPNAME": EBAY_APP_ID,
        "RESPONSE-DATA-FORMAT": "JSON",
        "REST-PAYLOAD": "",
        "paginationInput.entriesPerPage": "100",
        "itemFilter(0).name": "Seller",
        "itemFilter(0).value": SELLER_NAME,
        "sortOrder": "StartTimeNewest"
    }
    
    headers = {
        "X-EBAY-SOA-SECURITY-APPNAME": EBAY_APP_ID,
        "X-EBAY-SOA-REQUEST-DATA-FORMAT": "JSON",
        "X-EBAY-SOA-RESPONSE-DATA-FORMAT": "JSON",
        "User-Agent": "Mozilla/5.0"
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                endpoint,
                params=params,
                headers=headers,
                timeout=15
            )
            
            # Check for eBay API errors
            if response.status_code == 500:
                error_msg = response.json().get('errorMessage', {}).get('error', {}).get('message', 'Unknown error')
                logger.error(f"eBay API error (attempt {attempt + 1}): {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return None
        except Exception as e:
            logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
            return None

def get_ebay_listings():
    """Get listings with proper error handling"""
    try:
        data = make_ebay_api_request()
        if not data:
            return []
        
        items = []
        search_result = data.get("findItemsAdvancedResponse", [{}])[0].get("searchResult", [{}])[0]
        
        if search_result.get("@count", "0") != "0":
            for item in search_result.get("item", []):
                try:
                    items.append((
                        item["viewItemURL"][0],
                        item["title"][0],
                        item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("__value__", "N/A"),
                        item.get("listingInfo", [{}])[0].get("startTime", [""])[0]
                    ))
                except (KeyError, IndexError) as e:
                    logger.warning(f"Error parsing item: {e}")
                    continue
        
        return items
        
    except Exception as e:
        logger.error(f"Error processing API response: {e}")
        return []

async def show_current_inventory():
    listings = get_ebay_listings()
    if not listings:
        await send_message("⚠️ Could not retrieve current listings. Possible issues:\n"
                         "1. eBay API is temporarily unavailable\n"
                         "2. Your App ID may need verification\n"
                         "3. Seller may have no active listings")
        return
    
    await send_message(f"📋 Current Inventory ({len(listings)} items)")
    
    for i, (link, title, price, start_time) in enumerate(listings[:10], 1):
        message = f"{i}. {title}\n💰 ${price} | 🕒 {start_time[:10]}\n🔗 {link}"
        await send_message(message)
        await asyncio.sleep(0.5)
    
    global last_items
    last_items = {item[0] for item in listings}

async def check_new_listings():
    global last_items
    
    listings = get_ebay_listings()
    if not listings:
        logger.info("No listings retrieved")
        return
    
    current_items = {item[0] for item in listings}
    new_items = current_items - last_items
    
    if new_items:
        new_listings = [item for item in listings if item[0] in new_items]
        await send_message(f"🎉 New Listings Found ({len(new_listings)})!")
        
        for link, title, price, start_time in new_listings:
            message = f"🆕 {title}\n💰 ${price} | 🕒 {start_time[:10]}\n🔗 {link}"
            await send_message(message)
            await asyncio.sleep(0.5)
        
        last_items = current_items

async def main():
    await send_message(f"🤖 eBay Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    await show_current_inventory()
    
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
