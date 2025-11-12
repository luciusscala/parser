"""FastAPI application with single endpoint for web parsing."""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import logging

from app.config import settings
from app.browser import browser_manager
from app.extractor import extractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Web Parser API",
    description="Parse websites and extract structured data using LLM",
    version="1.0.0"
)


class ParseRequest(BaseModel):
    """Request model for parse endpoint."""
    url: HttpUrl


@app.on_event("startup")
async def startup_event():
    """Initialize browser on startup."""
    try:
        settings.validate()
        await browser_manager.initialize()
        logger.info("Browser initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize browser: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up browser on shutdown."""
    await browser_manager.close()
    logger.info("Browser closed")


@app.post("/parse")
async def parse_website(request: ParseRequest):
    """
    Parse a website and extract structured data.
    
    Args:
        request: ParseRequest containing the URL to parse
        
    Returns:
        JSON response with extracted data
        
    Raises:
        HTTPException: For various error conditions
    """
    url_str = str(request.url)
    logger.info(f"Parsing URL: {url_str}")
    
    try:
        # Step 1: Load and render the page
        logger.info("Loading page with browser...")
        html_content, text_content = await browser_manager.get_page_content(url_str)
        logger.info(f"Page loaded. HTML size: {len(html_content)} chars, Text size: {len(text_content)} chars")
        
        # Step 2: Extract data using LLM
        logger.info("Extracting data with LLM...")
        extracted_data = await extractor.extract_data(html_content, text_content, url_str)
        logger.info("Data extraction completed")
        
        return JSONResponse(content=extracted_data)
        
    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")
        raise HTTPException(status_code=504, detail=f"Request timed out: {str(e)}")
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

