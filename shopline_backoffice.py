import asyncio
from playwright.async_api import async_playwright, TimeoutError
from loguru import logger
from src.gmail_fetch import GmailConnect
from src.config.config import SettingsManager, ConfigManager

SETTINGS = SettingsManager()
CONFIG = ConfigManager()


class ShoplineBackoffice:
    def __init__(self):
        self.browser = None
        self.page = None
        self.official_email = CONFIG.shopline_sender_email
        self.login_url = "https://sso.shoplineapp.com/users/sign_in"
        self.username = "bagelshop2025@gmail.com"
        self.password = "!Bagel2025Shop"

    async def fetch_verification_code(self):
        script = GmailConnect(email=SETTINGS.bot_gmail, password=SETTINGS.bot_app_password)
        code = script.get_shopline_verification_code(self.official_email)
        if code:
            logger.info(f"Shopline 驗證碼: {code}")
        else:
            logger.error("無法獲取 Shopline 驗證碼")
        return code

    async def wait_for_2fa_or_dashboard(self):
        """等待並處理可能出現的二步驟驗證或直接進入dashboard"""
        try:
            await self.page.wait_for_selector("#code", timeout=5000)
            logger.info("需要輸入驗證碼...")
            await asyncio.sleep(10)
            code = await self.fetch_verification_code()
            await self.page.fill("#code", code)
            await self.page.click("//input[@type='submit']")
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.query_selector("//*[@data-e2e-id='nav_top_nav']")
            logger.success("驗證碼驗證成功！")
        except TimeoutError:
            try:
                await self.page.wait_for_selector("text=Dashboard", timeout=5000)
                logger.success("無需驗證碼，直接登入成功！")
            except TimeoutError:
                current_url = self.page.url
                logger.error(f"無法找到驗證碼輸入框或Dashboard，當前頁面: {current_url}")
                raise Exception("登入流程異常")

    async def login(self):
        try:
            async with async_playwright() as p:
                self.browser = await p.chromium.launch(headless=False, args=["--disable-dev-shm-usage"])
                context = await self.browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                )
                self.page = await context.new_page()
                self.page.set_default_timeout(30000)
                self.page.set_default_navigation_timeout(30000)

                logger.info("正在導航到登入頁面...")
                await self.page.goto(self.login_url, wait_until="domcontentloaded")

                logger.info("等待登入表單載入...")
                await self.page.wait_for_selector("#staff_email", state="visible", timeout=10000)
                await self.page.wait_for_selector("#staff_password", state="visible", timeout=10000)
                await asyncio.sleep(2)

                logger.info("輸入帳號密碼...")
                await self.page.fill("#staff_email", self.username)
                await self.page.fill("#staff_password", self.password)

                logger.info("點擊登入按鈕...")
                await self.page.click("#reg-submit-button")

                logger.info("等待登入流程完成...")
                await self.wait_for_2fa_or_dashboard()

        except Exception as e:
            logger.error(f"登入過程發生錯誤: {str(e)}")


async def main():
    shopline_backoffice = ShoplineBackoffice()
    await shopline_backoffice.login()


if __name__ == "__main__":
    asyncio.run(main())
