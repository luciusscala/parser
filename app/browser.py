"""Playwright browser management for rendering JavaScript-heavy websites."""
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from app.config import settings


class BrowserManager:
    """Manages Playwright browser instance with singleton pattern."""
    
    _instance: Optional['BrowserManager'] = None
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self) -> None:
        """Initialize Playwright and browser instance."""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
    
    async def close(self) -> None:
        """Close browser and Playwright instances."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    async def get_page_content(self, url: str) -> tuple[str, str]:
        """
        Load a URL and extract HTML and visible text.
        
        Args:
            url: The URL to load
            
        Returns:
            Tuple of (html_content, text_content)
            
        Raises:
            TimeoutError: If page load exceeds timeout
            Exception: For other browser errors
        """
        if self._browser is None:
            await self.initialize()
        
        page: Page = await self._browser.new_page()
        
        try:
            # Block unnecessary resources to speed up loading
            await page.route("**/*", lambda route: self._should_block_resource(route))
            
            # Set viewport
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Navigate with timeout
            await page.goto(
                url,
                wait_until="domcontentloaded",  # Don't wait for all resources
                timeout=settings.BROWSER_TIMEOUT
            )
            
            # Wait a bit for JavaScript to render (but not too long)
            try:
                await page.wait_for_load_state("networkidle", timeout=2000)
            except Exception:
                # If networkidle times out, continue anyway
                pass
            
            # Extract content
            html_content = await page.content()
            text_content = await page.evaluate("() => document.body.innerText")
            
            return html_content, text_content
            
        finally:
            await page.close()
    
    @staticmethod
    async def _should_block_resource(route) -> None:
        """Block unnecessary resources to speed up page loading."""
        resource_type = route.request.resource_type
        if resource_type in ["image", "font", "stylesheet", "media"]:
            await route.abort()
        else:
            await route.continue_()


# Global browser manager instance
browser_manager = BrowserManager()

