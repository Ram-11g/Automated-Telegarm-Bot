import os

# Bot Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_ID = "YOUR_CHANNEL_ID"

# EarnKaro Configuration
EARNKARO_USERNAME = "YOUR USERNAME"
EARNKARO_PASSWORD ="PASSWORD"
EARNKARO_TRACKING_ID = "YOUR_REFERAL_CODE"

# Cache Configuration
CACHE_FILE = "products_cache.json"
CACHE_EXPIRY_DAYS = 1

# Product Categories
PRODUCT_CATEGORIES = [
    'laptops',
    'smartphones',
    'headphones',
    'smartwatches',
    'tablets'
]

# Default Settings
DEFAULT_PRODUCTS_COUNT = 5
MAX_PRODUCTS_COUNT = 10

# Request settings
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 5

# Logging settings
LOG_FILE = 'scraper.log'
LOG_LEVEL = 'INFO'

# Create cache directory if it doesn't exist
CACHE_DIR = os.path.dirname(os.path.abspath(CACHE_FILE))
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR) 
