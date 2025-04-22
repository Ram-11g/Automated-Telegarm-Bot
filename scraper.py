import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import config
import random
import time
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EcommerceScraper:
    """Base class for e-commerce scrapers"""
    def __init__(self):
        self.session = None
        self.ua = UserAgent()
        self.products_cache = self.load_product_cache()
        
    async def __aenter__(self):
        await self.setup_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        
    async def setup_session(self) -> None:
        """Initialize aiohttp session with proper headers"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            self.session.headers.update({
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            })
            
    async def get_page(self, url: str, params: Optional[Dict] = None) -> Tuple[str, int]:
        """Get page content with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Random delay between requests
                await asyncio.sleep(random.uniform(1, 3))
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.text(), response.status
                    elif response.status == 429:  # Too Many Requests
                        wait_time = (attempt + 1) * 5
                        logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Failed to fetch {url}. Status: {response.status}")
                        return "", response.status
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep((attempt + 1) * 2)
                else:
                    return "", 500
        return "", 500

    def load_product_cache(self) -> Dict:
        """Load cached products from file"""
        try:
            if os.path.exists(config.CACHE_FILE):
                with open(config.CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    # Check if cache is expired
                    if datetime.fromisoformat(cache['timestamp']) + timedelta(days=config.CACHE_EXPIRY_DAYS) > datetime.now():
                        return cache['products']
        except Exception as e:
            logger.error(f"Error loading cache: {str(e)}")
        return {}

    def save_to_cache(self, products: Dict) -> None:
        """Save products to cache file"""
        try:
            cache = {
                'timestamp': datetime.now().isoformat(),
                'products': products
            }
            with open(config.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving to cache: {str(e)}")

class FlipkartScraper(EcommerceScraper):
    """Scraper for Flipkart products"""
    BASE_URL = "https://www.flipkart.com"
    SEARCH_URL = f"{BASE_URL}/search"
    
    async def get_products(self, category: str) -> Tuple[List[Dict], int]:
        """Fetch products from Flipkart with status code"""
        try:
            await self.setup_session()
            params = {
                'q': category,
                'otracker': 'search',
                'otracker1': 'search',
                'marketplace': 'FLIPKART',
                'as-show': 'on',
                'as': 'off',
                'sort': 'popularity'
            }
            html, status = await self.get_page(self.SEARCH_URL, params=params)
            
            if status != 200:
                logger.error(f"Failed to fetch Flipkart page. Status: {status}")
                return [], status
                
            soup = BeautifulSoup(html, 'html.parser')
            products = []
            
            # Try multiple selectors for product containers
            selectors = [
                'div._1xHGtK._373qXS',  # Grid view
                'div._2kHMtA',  # List view
                'div._1AtVbE',  # Alternative container
                'div._4ddWXP',  # New grid view
                'div._2B099V'   # New list view
            ]
            
            for selector in selectors:
                containers = soup.select(selector)
                if containers:
                    logger.info(f"Found {len(containers)} containers with selector: {selector}")
                    for container in containers:
                        product = self.extract_product_info(container)
                        if product:
                            products.append(product)
                    break
                    
            logger.info(f"Found {len(products)} products for category: {category}")
            return products, status
            
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return [], 500
            
    def extract_product_info(self, container) -> Optional[Dict]:
        """Extract product information from container"""
        try:
            # Try multiple selectors for each field
            title = container.select_one('div._4rR01T, div._2WkVRV, div._2B099V, div._3pLy-c, div._4ddWXP')
            description = container.select_one('a.IRpwTa, a._2UzuFa, a._3Djpdu, div._3pLy-c, div._4ddWXP')
            price = container.select_one('div._30jeq3, div._30jeq3._1_WHN1, div._30jeq3._16Jk6d, div._30jeq3._3qU9Bn')
            rating = container.select_one('div._3LWZlK, span._2_R_DZ, div._3LWZlK._1rdVr6')
            reviews = container.select_one('span._2_R_DZ, span._2_R_DZ span, span._3LWZlK._1rdVr6')
            link = container.select_one('a._1fQZEK, a._2UzuFa, a._3Djpdu, a._2rpwqI')
            image = container.select_one('img._396cs4, img._2r_T1I, img._2r_T1I._2r_T1I, img._396cs4._3exPp9')
            
            if not all([title, price, link]):
                logger.warning("Missing required fields in product container")
                return None
                
            product = {
                'title': title.text.strip(),
                'description': description.text.strip() if description else '',
                'price': price.text.strip(),
                'rating': rating.text.strip() if rating else 'No rating',
                'reviews': reviews.text.strip() if reviews else 'No reviews',
                'link': urljoin(self.BASE_URL, link['href']),
                'image': image['src'] if image else '',
                'timestamp': datetime.now().isoformat(),
                'platform': 'Flipkart'
            }
            return product
        except Exception as e:
            logger.error(f"Error extracting product info: {str(e)}")
            return None

class AmazonScraper(EcommerceScraper):
    """Scraper for Amazon products"""
    BASE_URL = "https://www.amazon.in"
    SEARCH_URL = f"{BASE_URL}/s"
    
    async def get_products(self, category: str) -> Tuple[List[Dict], int]:
        """Fetch products from Amazon with status code"""
        try:
            await self.setup_session()
            params = {
                'k': category,
                'ref': 'nb_sb_noss',
                'sort': 'popularity-rank'
            }
            html, status = await self.get_page(self.SEARCH_URL, params=params)
            
            if status != 200:
                logger.error(f"Failed to fetch Amazon page. Status: {status}")
                return [], status
                
            soup = BeautifulSoup(html, 'html.parser')
            products = []
            
            # Try multiple selectors for product containers
            selectors = [
                'div.s-result-item',  # Search result item
                'div.a-section.a-spacing-base',  # Product container
                'div.a-section.a-spacing-none',  # Alternative container
                'div[data-component-type="s-search-result"]'  # New search result
            ]
            
            for selector in selectors:
                containers = soup.select(selector)
                if containers:
                    logger.info(f"Found {len(containers)} containers with selector: {selector}")
                    for container in containers:
                        product = self.extract_product_info(container)
                        if product:
                            products.append(product)
                    break
                    
            logger.info(f"Found {len(products)} products for category: {category}")
            return products, status
            
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return [], 500
            
    def extract_product_info(self, container) -> Optional[Dict]:
        """Extract product information from container"""
        try:
            # Try multiple selectors for each field
            title = container.select_one('span.a-size-medium, span.a-size-base-plus, h2.a-size-mini')
            description = container.select_one('a.a-link-normal, a.a-text-normal, h2.a-size-mini')
            price = container.select_one('span.a-price-whole, span.a-offscreen, span.a-price')
            rating = container.select_one('span.a-icon-alt, i.a-icon-star')
            reviews = container.select_one('span.a-size-base, span.a-size-base.s-underline-text')
            link = container.select_one('a.a-link-normal, a.a-text-normal')
            image = container.select_one('img.s-image, img.a-dynamic-image')
            
            if not all([title, price, link]):
                logger.warning("Missing required fields in product container")
                return None
                
            product = {
                'title': title.text.strip(),
                'description': description.text.strip() if description else '',
                'price': price.text.strip(),
                'rating': rating.text.strip() if rating else 'No rating',
                'reviews': reviews.text.strip() if reviews else 'No reviews',
                'link': urljoin(self.BASE_URL, link['href']),
                'image': image['src'] if image else '',
                'timestamp': datetime.now().isoformat(),
                'platform': 'Amazon'
            }
            return product
        except Exception as e:
            logger.error(f"Error extracting product info: {str(e)}")
            return None

async def get_scraper(platform: str = 'flipkart') -> EcommerceScraper:
    """Get scraper instance for specified platform"""
    if platform.lower() == 'amazon':
        return AmazonScraper()
    return FlipkartScraper()

async def scrape_products(platform: str = 'flipkart', num_products: int = 5) -> List[Dict]:
    """Scrape products from specified platform"""
    async with await get_scraper(platform) as scraper:
        all_products = []
        
        for category in config.PRODUCT_CATEGORIES:
            logger.info(f"Searching for {category} on {platform}...")
            products, status = await scraper.get_products(category)
            if products:
                logger.info(f"Found {len(products)} products for {category}")
                all_products.extend(products)
                if len(all_products) >= num_products:
                    break
            else:
                logger.warning(f"No products found for {category}")
        
        return all_products[:num_products]

async def main():
    """Main function to test the scraper"""
    # Configure console output to handle Unicode
    import sys
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    
    logger.info("Starting scraper...")
    
    try:
        # Get products from Flipkart
        logger.info("Fetching Flipkart products...")
        flipkart_products = await scrape_products('flipkart', num_products=5)
        logger.info(f"Found {len(flipkart_products)} Flipkart products")
        
        if not flipkart_products:
            logger.warning("No Flipkart products found")
        else:
            print(f"\nFound {len(flipkart_products)} Flipkart products:")
            for product in flipkart_products:
                try:
                    print(f"\nTitle: {product['title']}")
                    print(f"Description: {product['description']}")
                    print(f"Price: {product['price']}")
                    print(f"Rating: {product['rating']}")
                    print(f"Reviews: {product['reviews']}")
                    print(f"Link: {product['link']}")
                except UnicodeEncodeError:
                    logger.warning("Unicode encoding error occurred while printing product")
                    print(f"\nTitle: {product['title'].encode('ascii', 'replace').decode()}")
                    print(f"Description: {product['description'].encode('ascii', 'replace').decode()}")
                    print(f"Price: {product['price'].encode('ascii', 'replace').decode()}")
                    print(f"Rating: {product['rating'].encode('ascii', 'replace').decode()}")
                    print(f"Reviews: {product['reviews'].encode('ascii', 'replace').decode()}")
                    print(f"Link: {product['link']}")
                except Exception as e:
                    logger.error(f"Error printing product: {e}")
        
        # Get products from Amazon
        logger.info("Fetching Amazon products...")
        amazon_products = await scrape_products('amazon', num_products=5)
        logger.info(f"Found {len(amazon_products)} Amazon products")
        
        if not amazon_products:
            logger.warning("No Amazon products found")
        else:
            print(f"\nFound {len(amazon_products)} Amazon products:")
            for product in amazon_products:
                try:
                    print(f"\nTitle: {product['title']}")
                    print(f"Description: {product['description']}")
                    print(f"Price: {product['price']}")
                    print(f"Rating: {product['rating']}")
                    print(f"Reviews: {product['reviews']}")
                    print(f"Link: {product['link']}")
                except UnicodeEncodeError:
                    logger.warning("Unicode encoding error occurred while printing product")
                    print(f"\nTitle: {product['title'].encode('ascii', 'replace').decode()}")
                    print(f"Description: {product['description'].encode('ascii', 'replace').decode()}")
                    print(f"Price: {product['price'].encode('ascii', 'replace').decode()}")
                    print(f"Rating: {product['rating'].encode('ascii', 'replace').decode()}")
                    print(f"Reviews: {product['reviews'].encode('ascii', 'replace').decode()}")
                    print(f"Link: {product['link']}")
                except Exception as e:
                    logger.error(f"Error printing product: {e}")
    
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1) 