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
        print('len', len(html))
        print('NEXT_DATA', '__NEXT_DATA__' in html)
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        print('match', bool(m))
        print('title', await page.title())
        print(html[:1000])
        await browser.close()


asyncio.run(main())
