"""OpenAI LLM extraction logic for structured data parsing."""
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings
from app.preparser import extract_main_content


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
        # Pre-parse content to remove boilerplate
        cleaned_content = extract_main_content(html_content, text_content)
        
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

