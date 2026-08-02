import asyncio
import json
import re
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            viewport={'width': 1440, 'height': 1200},
            locale='en-US',
            extra_http_headers={'Accept-Language': 'en-US,en;q=0.9'}
        )
        page = await context.new_page()
        url = 'https://www.trustpilot.com/categories/media_publishing?country=IN&page=1'
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)
        html = await page.content()
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        data = json.loads(m.group(1))
        props = data.get('props', {}).get('pageProps', {})
        print('pageProps keys', list(props.keys())[:20])
        business_units = props.get('businessUnits', {})
        print('businessUnits keys', list(business_units.keys())[:20])
        businesses = business_units.get('businesses', [])
        print('business count', len(businesses))
        if businesses:
            b = businesses[0]
            print('first business keys', list(b.keys())[:40])
            print('name', b.get('displayName'))
            print('identifyingName', b.get('identifyingName'))
            print('num reviews', b.get('numberOfReviews'))
            print('categories', b.get('categories', [])[:3])
            print('contact', b.get('contact'))
            print('location', b.get('location'))
        await browser.close()


asyncio.run(main())
