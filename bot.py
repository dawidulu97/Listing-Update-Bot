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
EBAY_APP_ID = "LaptopTr-notifier-PRD-68ea2d757-571ae1d7"  # Your Production App ID
SELLER_NAME = "eliminatethedigitaldivide"
CHECK_INTERVAL = 300  # 5 minutes (eBay recommends no more than 10 calls/minute)

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

def get_ebay_listings():
    """Fetch listings using eBay Finding API with proper error handling"""
    try:
        endpoint = "https://svcs.ebay.com/services/search/FindingService/v1"
        params = {
            "OPERATION-NAME": "findItemsAdvanced",
            "SERVICE-VERSION": "1.13.0",
            "SECURITY-APPNAME": EBAY_APP_ID,
            "RESPONSE-DATA-FORMAT": "JSON",
            "REST-PAYLOAD": "",
            "paginationInput.entriesPerPage": "100",  # Max allowed per call
            "itemFilter(0).name": "Seller",
            "itemFilter(0).value": SELLER_NAME,
            "sortOrder": "StartTimeNewest",  # Get newest items first
            "outputSelector(0)": "SellerInfo"  # Include seller details
        }
        
        # Add headers to mimic browser request
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Accept-Language": "en-US"
        }
        
        response = requests.get(
            endpoint,
            params=params,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        # Parse API response with error checking
        items = []
        try:
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
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing API response: {e}")
            return []
        
        return items
        
    except requests.exceptions.RequestException as e:
        logger.error(f"eBay API request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected eBay API error: {e}")
    
    return []

async def show_current_inventory():
    """Display all current listings with proper formatting"""
    listings = get_ebay_listings()
    if not listings:
        await send_message("⚠️ Could not retrieve current listings from eBay API. Please check your App ID and network connection.")
        return
    
    await send_message(f"📋 Current Inventory ({len(listings)} items)")
    
    # Send in batches of 5 items
    for i in range(0, min(20, len(listings)), 5):  # Limit to first 20 items
        batch = listings[i:i+5]
        message = "\n\n".join(
            f"{i+j+1}. {title}\n💰 ${price} | 🕒 {start_time[:10]}\n🔗 {link}"
            for j, (link, title, price, start_time) in enumerate(batch)
        )
        await send_message(message)
        await asyncio.sleep(1)  # Rate limiting
    
    global last_items
    last_items = {item[0] for item in listings}

async def check_new_listings():
    """Check for new listings with error handling"""
    global last_items
    
    try:
        listings = get_ebay_listings()
        if not listings:
            logger.info("No listings retrieved from API")
            return
        
        current_items = {item[0] for item in listings}
        new_items = current_items - last_items
        
        if new_items:
            new_listings = [item for item in listings if item[0] in new_items]
            await send_message(f"🎉 New Listings Found ({len(new_listings)})!")
            
            for link, title, price, start_time in new_listings:
                message = f"🆕 {title}\n💰 ${price} | 🕒 {start_time[:10]}\n🔗 {link}"
                await send_message(message)
                await asyncio.sleep(1)  # Rate limiting
            
            last_items = current_items
    
    except Exception as e:
        logger.error(f"Error checking new listings: {e}")
        await send_message(f"⚠️ Temporary error checking listings: {str(e)[:100]}...")

async def main():
    await send_message(f"🤖 eBay API Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
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
