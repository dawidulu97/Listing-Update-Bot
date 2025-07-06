from datetime import datetime, timedelta
import time
import pytz
import json
import logging
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
import telegram
from telegram.ext import Updater

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configuration - Directly embedded in the code
CONFIG = {
    'TelegramBotConfig': {
        'token': '7900731557:AAH11XcaZXxnax9MrtFPsd_VUBEkT6NJkCo',
        'my_user_id': 6848532238,
        'dest_channel_id': 4719054372
    },
    'EbayConfig': {
        'appid': 'LaptopTr-notifier-SBX-0c5701265-0f157037'
    },
    'EbayFilters': {
        'seller_name': 'eliminatethedigitaldivide'
    }
}

def get_updated_listings(seller_name, last_checked):
    """Fetch updated listings from eBay for the specified seller since last_checked"""
    all_items = []
    try:
        api = Finding(appid=CONFIG['EbayConfig']['appid'], config_file=None)
        response = api.execute('findItemsAdvanced', {
            'itemFilter': [
                {'name': 'Seller', 'value': seller_name},
                {'name': 'StartTimeFrom', 'value': last_checked.strftime('%Y-%m-%dT%H:%M:%S')}
            ]
        })
        response_dict = response.dict()
        if response_dict.get('searchResult', {}).get('_count', '0') != '0':
            items = response_dict['searchResult']['item']
            all_items.extend(items)
    except ConnectionError as e:
        logging.error(f"eBay API Error: {e}")
        logging.error(e.response.dict())
    return all_items

def main():
    """Main function to run the bot"""
    # Initialize time tracking
    gmt = pytz.timezone('GMT')
    last_checked = datetime.now(gmt).replace(microsecond=0) - timedelta(days=1)
    
    # Setup Telegram bot
    updater = Updater(CONFIG['TelegramBotConfig']['token'], use_context=True)
    seller_name = CONFIG['EbayFilters']['seller_name']
    
    logging.info("Starting eBay listing monitor...")
    
    while True:
        updated_listings = get_updated_listings(seller_name, last_checked)
        current_time = datetime.now(gmt).replace(microsecond=0)
        
        if updated_listings:
            logging.info(f"Found {len(updated_listings)} new listings.")
            for item in updated_listings:
                message = f"New item: {item['title']}\n{item['viewItemURL']}"
                try:
                    updater.bot.send_message(
                        chat_id=CONFIG['TelegramBotConfig']['dest_channel_id'],
                        text=message
                    )
                    time.sleep(1)  # Short pause to prevent rate limiting
                except telegram.error.RetryAfter as e:
                    logging.warning(f"Rate limit exceeded. Waiting {e.retry_after} seconds.")
                    time.sleep(e.retry_after)
                    updater.bot.send_message(
                        chat_id=CONFIG['TelegramBotConfig']['dest_channel_id'],
                        text=message
                    )
        else:
            logging.info("No new listings found.")
        
        logging.info(f"Updating last_checked to {current_time}")
        last_checked = current_time
        time.sleep(60)  # Wait 1 minute before checking again

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
