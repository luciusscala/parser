"""Content pre-parsing to remove boilerplate and extract main content."""
import re
import logging

logger = logging.getLogger(__name__)

# Common IATA airport codes (major airports)
COMMON_AIRPORT_CODES = {
    'JFK', 'LAX', 'SFO', 'ORD', 'DFW', 'DEN', 'SEA', 'LAS', 'MIA', 'ATL',
    'BOS', 'EWR', 'LGA', 'PHX', 'IAH', 'MSP', 'DTW', 'PHL', 'CLT', 'LHR',
    'CDG', 'FRA', 'AMS', 'MAD', 'FCO', 'BCN', 'ZUR', 'GVA', 'VIE', 'BRU',
    'DUB', 'LIS', 'ATH', 'ARN', 'CPH', 'OSL', 'HEL', 'STO', 'WAW', 'PRG',
    'BUD', 'WAR', 'IST', 'DXB', 'DOH', 'AUH', 'SIN', 'HKG', 'NRT', 'ICN',
    'SYD', 'MEL', 'BNE', 'AKL', 'YVR', 'YYZ', 'YUL', 'MEX', 'GRU', 'EZE',
    'SCL', 'LIM', 'BOG', 'PTY', 'SJO', 'HAV', 'NAS', 'SJU', 'IAD', 'DCA',
    'BWI', 'SAN', 'PDX', 'AUS', 'SLC', 'MCI', 'STL', 'IND', 'CMH', 'CVG',
    'BNA', 'RDU', 'TPA', 'MCO', 'FLL', 'PBI', 'JAX', 'MSY', 'HOU', 'SAT',
    'OKC', 'TUL', 'MEM', 'BHM', 'CHS', 'SAV', 'TLH', 'PNS', 'MOB',
    'BTR', 'SHV', 'LIT', 'LFT', 'BPT', 'CRP', 'BRO', 'MFE', 'HRL',
    'ELP', 'ABQ', 'TUS', 'YUM', 'RNO', 'BOI', 'GEG',
    'EUG', 'RDM', 'MFR', 'ACV', 'CEC', 'OAK', 'SJC', 'SMF',
    'FAT', 'VIS', 'BFL', 'SBA', 'SBP', 'MRY', 'STS', 'SMX', 'PRB',
    'ZRH', 'GVA', 'BSL', 'BRN', 'LUG', 'ALR', 'ACH'
}

try:
    from selectolax.parser import HTMLParser  # type: ignore
    SELECTOLAX_AVAILABLE = True
except ImportError:
    SELECTOLAX_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

try:
    import trafilatura  # type: ignore
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False


def extract_main_content(html_content: str, text_content: str) -> str:
    """
    Extract main content from HTML by removing boilerplate.
    
    Uses trafilatura if available (best for main content extraction),
    otherwise falls back to selectolax/BeautifulSoup for cleanup.
    
    Args:
        html_content: Raw HTML content
        text_content: Visible text content
        
    Returns:
        Cleaned main content text
    """
    # Try trafilatura first (best for main content extraction)
    if TRAFILATURA_AVAILABLE:
        try:
            extracted = trafilatura.extract(html_content)
            if extracted:
                return extracted.strip()
        except Exception:
            # Fall back to manual parsing if trafilatura fails
            pass
    
    # Fallback: Use selectolax or BeautifulSoup to remove boilerplate
    if SELECTOLAX_AVAILABLE:
        tree = HTMLParser(html_content)
    elif BEAUTIFULSOUP_AVAILABLE:
        soup = BeautifulSoup(html_content, 'html.parser')
    else:
        # No parser available, return text content
        return text_content.strip()
    
    # Remove script, style, nav, footer, header elements
    if SELECTOLAX_AVAILABLE:
        for tag in tree.css('script, style, nav, footer, header, aside, noscript'):
            tag.decompose()
        
        # Try to find main content area
        main_content = tree.css_first('main, article, [role="main"], .content, #content')
        if main_content:
            return main_content.text(separator=' ', strip=True)
        
        # Fallback to body text
        body = tree.css_first('body')
        if body:
            return body.text(separator=' ', strip=True)
    elif BEAUTIFULSOUP_AVAILABLE:
        # BeautifulSoup approach
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
            tag.decompose()
        
        # Try to find main content area
        main_content = soup.find(['main', 'article']) or soup.find(attrs={'role': 'main'}) or \
                      soup.find(class_='content') or soup.find(id='content')
        if main_content:
            return main_content.get_text(separator=' ', strip=True)
        
        # Fallback to body text
        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)
    
    # Ultimate fallback: return original text content
    return text_content.strip()


def extract_targeted_content(text_content: str, context_window: int = 200) -> str:
    """
    Extract only relevant content by finding airport codes, numbers, and flight-related keywords,
    then keeping context around these matches.
    
    This is much more targeted than full content extraction and significantly reduces token usage.
    
    Args:
        text_content: The text content to search
        context_window: Number of characters to keep before/after each match
        
    Returns:
        Focused content string with only relevant snippets
    """
    if not text_content:
        return ""
    
    # Normalize text - remove extra whitespace but keep structure
    text = re.sub(r'\s+', ' ', text_content)
    
    # Find all matches and their positions
    matches = []
    
    # 1. Find airport codes (3-letter uppercase, possibly with word boundaries)
    airport_pattern = r'\b([A-Z]{3})\b'
    for match in re.finditer(airport_pattern, text):
        code = match.group(1)
        # Check if it's a known airport code (or assume common 3-letter codes are airports)
        if code in COMMON_AIRPORT_CODES or (len(code) == 3 and code.isupper()):
            matches.append((match.start(), match.end(), f"AIRPORT:{code}"))
    
    # 2. Find numbers (prices, times, flight numbers, durations)
    # Prices: $123, 123.45, 1,234.56
    price_pattern = r'\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
    for match in re.finditer(price_pattern, text):
        matches.append((match.start(), match.end(), "PRICE"))
    
    # Times: HH:MM format
    time_pattern = r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b'
    for match in re.finditer(time_pattern, text):
        matches.append((match.start(), match.end(), "TIME"))
    
    # Flight numbers: 1-2 letters followed by 1-4 digits (e.g., UA1234, AA567)
    flight_num_pattern = r'\b([A-Z]{1,2}\d{1,4})\b'
    for match in re.finditer(flight_num_pattern, text):
        matches.append((match.start(), match.end(), f"FLIGHT:{match.group(1)}"))
    
    # Durations: Xh Ym, X hours Y minutes, etc.
    duration_pattern = r'\b\d+\s*(?:h|hr|hour|hours)\s*\d*\s*(?:m|min|minute|minutes)?\b'
    for match in re.finditer(duration_pattern, text, re.IGNORECASE):
        matches.append((match.start(), match.end(), "DURATION"))
    
    # Dates: Nov 15, 2024, 11/15/2024, etc.
    date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'
    for match in re.finditer(date_pattern, text, re.IGNORECASE):
        matches.append((match.start(), match.end(), "DATE"))
    
    # 3. Find flight-related keywords
    keywords = [
        'airline', 'flight', 'departure', 'arrival', 'layover', 'connection',
        'depart', 'arrive', 'duration', 'price', 'total', 'segment',
        'United', 'American', 'Delta', 'Southwest', 'JetBlue', 'Alaska',
        'Lufthansa', 'British Airways', 'Air France', 'KLM', 'Swiss',
        'outbound', 'return', 'round trip', 'one way'
    ]
    keyword_pattern = r'\b(?:' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
    for match in re.finditer(keyword_pattern, text, re.IGNORECASE):
        matches.append((match.start(), match.end(), "KEYWORD"))
    
    if not matches:
        logger.warning("No targeted matches found, returning empty string")
        return ""
    
    # Sort matches by position
    matches.sort(key=lambda x: x[0])
    
    # Extract context around each match and merge overlapping regions
    regions = []
    for start, end, label in matches:
        region_start = max(0, start - context_window)
        region_end = min(len(text), end + context_window)
        regions.append((region_start, region_end, label))
    
    # Merge overlapping regions
    if not regions:
        return ""
    
    merged_regions = []
    current_start, current_end, labels = regions[0]
    label_set = {labels}
    
    for start, end, label in regions[1:]:
        if start <= current_end:  # Overlapping
            current_end = max(current_end, end)
            label_set.add(label)
        else:  # New region
            merged_regions.append((current_start, current_end, label_set))
            current_start, current_end = start, end
            label_set = {label}
    
    # Add last region
    merged_regions.append((current_start, current_end, label_set))
    
    # Extract text from merged regions
    snippets = []
    for start, end, labels in merged_regions:
        snippet = text[start:end].strip()
        if snippet:
            # Add a marker showing what was found in this region
            labels_str = ', '.join(sorted(labels))
            snippets.append(f"[{labels_str}] {snippet}")
    
    result = "\n\n".join(snippets)
    logger.info(
        f"Targeted extraction: {len(text):,} chars -> {len(result):,} chars "
        f"({len(matches)} matches, {len(merged_regions)} regions)"
    )
    
    return result


def clean_html_for_llm(html_content: str) -> str:
    """
    Clean HTML by removing only obvious non-content elements (images, svg, scripts).
    Keeps most of the HTML structure for LLM analysis.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Cleaned HTML with only obvious non-content elements removed
    """
    if SELECTOLAX_AVAILABLE:
        tree = HTMLParser(html_content)
        # Only remove obvious non-content: images, svg, scripts, styles
        for tag in tree.css('script, style, img, svg, image, noscript'):
            tag.decompose()
        return tree.html
    elif BEAUTIFULSOUP_AVAILABLE:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Only remove obvious non-content: images, svg, scripts, styles
        for tag in soup.find_all(['script', 'style', 'img', 'svg', 'image', 'noscript']):
            tag.decompose()
        return str(soup)
    else:
        # No parser available, use regex to remove script and style tags
        # Remove script tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        # Remove style tags
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        # Remove img tags
        html_content = re.sub(r'<img[^>]*>', '', html_content, flags=re.IGNORECASE)
        # Remove svg tags
        html_content = re.sub(r'<svg[^>]*>.*?</svg>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        return html_content

