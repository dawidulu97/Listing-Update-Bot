import base64
import requests
from datetime import datetime, timedelta
from telegram import Bot
import logging
import asyncio

# Configuration - Use your exact credentials
TELEGRAM_TOKEN = "7900731557:AAH11XcaZXxnax9MrtFPsd_VUBEkT6NJkCo"
CHAT_ID = "6848532238"
EBAY_CLIENT_ID = "LaptopTr-notifier-PRD-68ea2d757-571ae1d7"
EBAY_CLIENT_SECRET = "PRD-cb354b2deba3-875d-4019-b3f2-2365"
SELLER_USERNAME = "eliminatethedigitaldivide"
CHECK_INTERVAL = 600  # 10 minutes (safe for 5,000 daily calls)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
last_items = set()
oauth_token = None
token_expiry = None

async def send_message(text):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        logger.error(f"Error sending message: {e}")

async def refresh_oauth_token():
    """Get new OAuth token using your Client ID/Secret"""
    global oauth_token, token_expiry
    try:
        # Base64 encode the client credentials
        auth_string = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
        basic_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic_auth}"
        }
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        }
        
        response = requests.post(
            "https://api.ebay.com/identity/v1/oauth2/token",
            headers=headers,
            data=data,
            timeout=10
        )
        response.raise_for_status()
        
        token_data = response.json()
        oauth_token = token_data['access_token']
        token_expiry = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)  # 1 min buffer
        logger.info("Successfully refreshed OAuth token")
        
    except Exception as e:
        logger.error(f"Failed to refresh OAuth token: {e}")
        await send_message("⚠️ Failed to authenticate with eBay API. Check your credentials.")

async def get_ebay_listings():
    """Get seller listings using eBay Browse API"""
    global oauth_token
    
    # Refresh token if expired or missing
    if not oauth_token or datetime.now() >= token_expiry:
        await refresh_oauth_token()
        if not oauth_token:
            return []
    
    try:
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
        }
        params = {
            "filter": f"seller:{SELLER_USERNAME}",
            "sort": "-startTime",  # Newest first
            "limit": "100"  # Max items per request
        }
        
        response = requests.get(
            "https://api.ebay.com/buy/browse/v1/item_summary/search",
            headers=headers,
            params=params,
            timeout=15
        )
        
        # Handle token expiration
        if response.status_code == 401:
            await refresh_oauth_token()
            return await get_ebay_listings()
        
        response.raise_for_status()
        
        items = []
        for item in response.json().get('itemSummaries', []):
            try:
                items.append((
                    item['itemWebUrl'],
                    item['title'],
                    item['price']['value'],
                    item['itemCreationDate']
                ))
            except KeyError as e:
                logger.warning(f"Missing field in item: {e}")
                continue
                
        return items
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    return []

async def show_current_inventory():
    """Display current inventory"""
    listings = await get_ebay_listings()
    if not listings:
        await send_message("⚠️ Could not retrieve current listings. The seller may have no items or API is unavailable.")
        return
    
    await send_message(f"📋 Current Inventory ({len(listings)} items)")
    
    # Send in batches of 5
    for i in range(0, min(20, len(listings)), 5):
        batch = listings[i:i+5]
        message = "\n\n".join(
            f"{i+j+1}. {title}\n💰 ${price} | 🕒 {date[:10]}\n🔗 {url}"
            for j, (url, title, price, date) in enumerate(batch)
        )
        await send_message(message)
        await asyncio.sleep(1)  # Rate limiting
    
    global last_items
    last_items = {item[0] for item in listings}

async def check_new_listings():
    """Check for new listings"""
    global last_items
    
    listings = await get_ebay_listings()
    if not listings:
        return
    
    current_items = {item[0] for item in listings}
    new_items = current_items - last_items
    
    if new_items:
        new_listings = [item for item in listings if item[0] in new_items]
        await send_message(f"🎉 New Listings Found ({len(new_listings)})!")
        
        for url, title, price, date in new_listings:
            message = f"🆕 {title}\n💰 ${price} | 🕒 {date[:10]}\n🔗 {url}"
            await send_message(message)
            await asyncio.sleep(1)  # Rate limiting
        
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
