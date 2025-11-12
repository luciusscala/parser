"""Playwright browser management for rendering JavaScript-heavy websites."""
import asyncio
import logging
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError
from app.config import settings

logger = logging.getLogger(__name__)


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
            logger.info("Browser initialized successfully")
    
    async def close(self) -> None:
        """Close browser and Playwright instances."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser closed")
    
    async def get_page_content(self, url: str) -> Tuple[str, str]:
        """
        Load a URL and extract HTML and visible text with retry logic.
        
        Args:
            url: The URL to load
            
        Returns:
            Tuple of (html_content, text_content)
            
        Raises:
            TimeoutError: If page load exceeds timeout after retries
            ValueError: If URL is unreachable or invalid
            RuntimeError: For other browser errors
        """
        if self._browser is None:
            await self.initialize()
        
        max_attempts = 2
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            page: Optional[Page] = None
            try:
                logger.info(f"Loading page (attempt {attempt}/{max_attempts}): {url}")
                page = await self._browser.new_page()
                
                # Add stealth script to avoid bot detection
                await page.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                
                # Block unnecessary resources to speed up loading
                await page.route("**/*", lambda route: self._should_block_resource(route))
                
                # Set viewport
                await page.set_viewport_size({"width": 1920, "height": 1080})
                
                # Navigate with networkidle for full render completion
                try:
                    await page.goto(
                        url,
                        wait_until="networkidle",
                        timeout=settings.BROWSER_TIMEOUT
                    )
                except PlaywrightTimeoutError as e:
                    raise TimeoutError(
                        f"Page load timed out after {settings.BROWSER_TIMEOUT}ms. "
                        f"URL may be slow or unreachable: {url}"
                    ) from e
                except Exception as e:
                    raise ValueError(f"Failed to navigate to URL: {url}. Error: {str(e)}") from e
                
                # Post-load delay: Wait for body selector to ensure React/Vue hydration
                try:
                    await page.wait_for_selector("body", timeout=2000, state="attached")
                    # Small additional delay for JavaScript frameworks to hydrate
                    await asyncio.sleep(0.5)
                except PlaywrightTimeoutError:
                    logger.warning("Body selector wait timed out, continuing anyway")
                
                # Extract content using Playwright locator for better dynamic DOM handling
                try:
                    html_content = await page.content()
                    # Use locator for better dynamic DOM handling
                    text_content = await page.locator("body").inner_text()
                except Exception as e:
                    raise RuntimeError(f"Failed to extract page content: {str(e)}") from e
                
                # Validate that we got meaningful content
                if not html_content or len(html_content) < 100:
                    raise ValueError(f"Page appears to be empty or incomplete. HTML length: {len(html_content)}")
                
                if not text_content or len(text_content.strip()) < 10:
                    logger.warning(f"Text content is very short ({len(text_content)} chars), but continuing")
                
                logger.info(
                    f"Successfully loaded page. HTML: {len(html_content)} chars, "
                    f"Text: {len(text_content)} chars"
                )
                
                return html_content, text_content
                
            except (TimeoutError, ValueError, RuntimeError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt}/{max_attempts} failed: {str(e)}")
                if attempt < max_attempts:
                    logger.info(f"Retrying in 1 second...")
                    await asyncio.sleep(1)
                else:
                    logger.error(f"All {max_attempts} attempts failed for URL: {url}")
                    
            except Exception as e:
                last_error = RuntimeError(f"Unexpected error loading page: {str(e)}")
                logger.error(f"Unexpected error on attempt {attempt}: {str(e)}", exc_info=True)
                if attempt < max_attempts:
                    await asyncio.sleep(1)
                else:
                    raise last_error
                    
            finally:
                # Always close the page, even on error
                if page:
                    try:
                        await page.close()
                    except Exception as e:
                        logger.warning(f"Error closing page: {str(e)}")
        
        # If we get here, all attempts failed
        if last_error:
            raise last_error
        else:
            raise RuntimeError(f"Failed to load page after {max_attempts} attempts: {url}")
    
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
