from urllib.parse import quote
from config import EARNKARO_TRACKING_ID

def format_product_message(product):
    """Format product information into a message"""
    message = f"*{product['name']}*\n\n"
    
    if product['price']:
        message += f"💰 *Price:* {product['price']}\n"
    
    if product['discount']:
        message += f"🎯 *Discount:* {product['discount']}\n"
    
    if product['rating']:
        message += f"⭐ *Rating:* {product['rating']}\n"
    
    message += f"\n🛍️ *Available on:* {product['site']}\n"
    message += f"\n🔗 [Buy Now]({product['url']})"
    
    return message

async def generate_affiliate_link(product_url):
    """Generate an EarnKaro affiliate link"""
    try:
        if not product_url.startswith('http'):
            product_url = 'https://www.flipkart.com' + product_url
        earnkaro_link = f"https://earnkaro.com/flipkart?url={quote(product_url)}&subid={EARNKARO_TRACKING_ID}"
        return earnkaro_link
    except Exception as e:
        return product_url 