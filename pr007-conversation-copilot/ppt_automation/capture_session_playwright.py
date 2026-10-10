import asyncio
import os
from playwright.async_api import async_playwright

async def capture():
    output_path = r"C:\Users\psamy\define\pr007-conversation-copilot\ppt_automation\shot_live_copilot_room.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 900})
        page = await context.new_page()
        
        # Navigate to landing page
        print("Navigating to landing page...")
        await page.goto("http://127.0.0.1:8000/")
        await page.wait_for_timeout(2000)
        
        # Click 1-Click Demo button
        demo_btn = page.locator("button:has-text('1-Click Demo'), a:has-text('1-Click Demo')").first
        if await demo_btn.count() > 0:
            print("Clicking 1-Click Demo...")
            await demo_btn.click()
            await page.wait_for_timeout(4000)
        else:
            print("1-Click Demo button not found, checking direct create meeting...")
        
        print("Current URL:", page.url)
        # Wait a moment for session elements or audio visualizers to render
        await page.wait_for_timeout(3000)
        
        await page.screenshot(path=output_path)
        print("Screenshot saved to:", output_path)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture())
