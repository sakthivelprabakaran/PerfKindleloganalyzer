import asyncio
from playwright.async_api import async_playwright, expect

async def main():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Waiting for application to launch...")
        await page.wait_for_timeout(10000)

        print("Taking launcher screenshot...")
        await page.screenshot(path="jules-scratch/verification/01_launcher.png")

        # Launch Kindle Log Analyzer
        print("Launching Kindle Log Analyzer...")
        analyzer_button = page.get_by_role("button", name="Launch Kindle Log Analyzer")
        await expect(analyzer_button).to_be_visible()
        await analyzer_button.click()
        await page.wait_for_timeout(3000)
        print("Taking Kindle Log Analyzer screenshot...")
        await page.screenshot(path="jules-scratch/verification/02_kindle_log_analyzer.png")

        # Go back to the launcher
        print("Going back to launcher...")
        back_button = page.get_by_role("button", name="⬅️ Back to Launcher")
        await expect(back_button).to_be_visible()
        await back_button.click()
        await page.wait_for_timeout(3000)

        # Launch Performance Execution Dashboard
        print("Launching Performance Execution Dashboard...")
        dashboard_button = page.get_by_role("button", name="Launch Performance Execution Dashboard")
        await expect(dashboard_button).to_be_visible()
        await dashboard_button.click()
        await page.wait_for_timeout(3000)
        print("Taking Performance Execution Dashboard screenshot...")
        await page.screenshot(path="jules-scratch/verification/03_performance_dashboard.png")

        print("Closing browser...")
        await browser.close()
        print("Script finished.")

if __name__ == "__main__":
    asyncio.run(main())