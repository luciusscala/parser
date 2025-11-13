"""OpenAI LLM extraction logic for structured data parsing."""
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings
from app.preparser import extract_main_content, extract_targeted_content

logger = logging.getLogger(__name__)


class LLMExtractor:
    """Handles LLM-based data extraction from web content."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._prompt_template: Optional[str] = None
    
    def _load_prompt(self) -> str:
        """Load prompt template from file."""
        if self._prompt_template is None:
            prompt_path = Path(settings.PROMPT_FILE)
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            self._prompt_template = prompt_path.read_text(encoding='utf-8')
        return self._prompt_template
    
    async def extract_data(self, html_content: str, text_content: str, url: str) -> Dict[str, Any]:
        """
        Extract structured data from web content using LLM.
        
        Args:
            html_content: Raw HTML content
            text_content: Visible text content
            url: Source URL
            
        Returns:
            Extracted data as dictionary
            
        Raises:
            TimeoutError: If LLM call exceeds timeout
            ValueError: If response is not valid JSON
        """
        # Use targeted extraction: find airport codes, numbers, and flight keywords
        # then extract context around matches. This is much more efficient than processing full content.
        original_html_length = len(html_content)
        original_text_length = len(text_content)
        
        logger.info(
            f"Input sizes - HTML: {original_html_length:,} chars, Text: {original_text_length:,} chars"
        )
        
        # Use targeted extraction on text content (much faster and more focused)
        cleaned_content = extract_targeted_content(text_content, context_window=200)
        
        if not cleaned_content or len(cleaned_content.strip()) < 100:
            # Fallback: if targeted extraction finds nothing, use regular cleaning
            logger.warning("Targeted extraction found little content, falling back to regular cleaning")
            cleaned_content = extract_main_content(html_content, text_content)
        
        final_length = len(cleaned_content)
        logger.info(
            f"Targeted extraction result: {final_length:,} characters "
            f"(reduced from {original_text_length:,} chars, "
            f"{((original_text_length - final_length) / original_text_length * 100):.1f}% reduction)"
        )
        
        # Save the exact content sent to LLM to output2.txt
        try:
            with open("output2.txt", "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write(f"URL: {url}\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Final Content Length: {final_length:,} characters\n")
                f.write(f"Original HTML Length: {original_html_length:,} characters\n")
                f.write(f"Original Text Length: {original_text_length:,} characters\n")
                f.write(f"Extraction Method: Targeted (airport codes, numbers, keywords + context)\n")
                reduction_pct = ((original_text_length - final_length) / original_text_length * 100) if original_text_length > 0 else 0
                f.write(f"Reduction: {original_text_length:,} -> {final_length:,} chars ({reduction_pct:.1f}% reduction)\n")
                f.write("=" * 80 + "\n\n")
                f.write("EXACT CONTENT SENT TO LLM:\n")
                f.write("-" * 80 + "\n")
                f.write(cleaned_content)
                f.write("\n")
            logger.info("Truncated content saved to output2.txt")
        except Exception as e:
            logger.warning(f"Failed to save output2.txt: {e}")
        
        # Load prompt template
        prompt = self._load_prompt()
        
        # Construct message for LLM
        system_message = prompt
        user_message = f"""Extract the requested data from the following web page content.

URL: {url}

Content:
{cleaned_content}

Return the extracted data as valid JSON only, with no additional text or explanation."""
        
        try:
            # Call OpenAI API with timeout
            # Build request parameters
            request_params = {
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "response_format": {"type": "json_object"},
            }
            
            # Only add temperature if model supports it
            # Some models like o1 and gpt-5-nano don't support custom temperature
            model_name = settings.OPENAI_MODEL.lower()
            models_without_temperature = ["o1", "gpt-5-nano"]
            if not any(model_name.startswith(prefix) for prefix in models_without_temperature):
                request_params["temperature"] = 0.1  # Lower temperature for more consistent extraction
            
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**request_params),
                    timeout=settings.LLM_TIMEOUT / 1000.0  # Convert ms to seconds
                )
            except Exception as api_error:
                # If temperature is not supported, retry without it
                error_str = str(api_error).lower()
                if "temperature" in error_str and "unsupported" in error_str:
                    # Remove temperature and retry
                    request_params.pop("temperature", None)
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(**request_params),
                        timeout=settings.LLM_TIMEOUT / 1000.0
                    )
                else:
                    raise
            
            # Extract JSON from response
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")
            
            # Parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                # Try to extract JSON from markdown code blocks if present
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                
                return json.loads(content)
                
        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM extraction timed out after {settings.LLM_TIMEOUT}ms")
        except Exception as e:
            if isinstance(e, (TimeoutError, ValueError)):
                raise
            raise RuntimeError(f"LLM extraction failed: {str(e)}")


# Global extractor instance
extractor = LLMExtractor()

