"""Content pre-parsing to remove boilerplate and extract main content."""
import re
import logging

logger = logging.getLogger(__name__)

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


def optimize_html_for_flights(html_content: str) -> str:
    """
    Optimize HTML by keeping only flight-relevant elements based on Google Flights structure.
    Keeps elements with data-slice-index, flight-related classes, and price elements.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Optimized HTML with only flight-relevant elements
    """
    if not html_content:
        return ""
    
    # Google Flights specific selectors identified by LLM
    flight_selectors = [
        '[data-slice-index]',  # Outbound/return slices
        '.oPtD1',  # Price
        '.MX5RWe',  # Flight details
        '.Xsgmwe',  # Airline
        '.dPzsIb',  # Flight info
        '.G2WY5c',  # Flight details
        '.SWFQlc',  # Flight details
        'span.price',  # Price elements
        '[class*="flight"]',  # Any class containing "flight"
        '[class*="segment"]',  # Any class containing "segment"
        '[class*="airline"]',  # Any class containing "airline"
        '[class*="price"]',  # Any class containing "price"
        '[data-flight-number]',  # Flight number data attributes
        '[data-airline]',  # Airline data attributes
    ]
    
    if SELECTOLAX_AVAILABLE:
        tree = HTMLParser(html_content)
        
        # First, remove obvious non-content
        for tag in tree.css('script, style, img, svg, image, noscript, link, meta'):
            tag.decompose()
        
        # Find all elements that match flight selectors
        relevant_elements = set()
        for selector in flight_selectors:
            try:
                for elem in tree.css(selector):
                    # Add element and all its ancestors
                    current = elem
                    while current and current.tag != 'html':
                        relevant_elements.add(id(current))
                        current = current.parent
            except Exception:
                continue
        
        # Remove elements that aren't relevant (but keep their text if they contain relevant children)
        def should_keep(elem):
            if id(elem) in relevant_elements:
                return True
            # Keep if it has relevant children
            for child in elem.iter():
                if id(child) in relevant_elements:
                    return True
            return False
        
        # Create new tree with only relevant elements
        body = tree.css_first('body')
        if body:
            # Extract only relevant parts
            result_parts = []
            for selector in flight_selectors:
                try:
                    for elem in tree.css(selector):
                        result_parts.append(elem.html)
                except Exception:
                    continue
            
            if result_parts:
                return '<div>' + ''.join(result_parts) + '</div>'
        
        # Fallback: return cleaned version
        return tree.html
        
    elif BEAUTIFULSOUP_AVAILABLE:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove obvious non-content
        for tag in soup.find_all(['script', 'style', 'img', 'svg', 'image', 'noscript', 'link', 'meta']):
            tag.decompose()
        
        # Find all relevant elements
        relevant_elements = set()
        
        # Find elements with data-slice-index (most important for Google Flights)
        for elem in soup.find_all(attrs={'data-slice-index': True}):
            relevant_elements.add(elem)
            # Include all descendants
            for desc in elem.descendants:
                if hasattr(desc, 'name') and desc.name:
                    relevant_elements.add(desc)
        
        # Find elements by class names
        class_names = ['oPtD1', 'MX5RWe', 'Xsgmwe', 'dPzsIb', 'G2WY5c', 'SWFQlc']
        for class_name in class_names:
            for elem in soup.find_all(class_=class_name):
                relevant_elements.add(elem)
                # Include parent containers
                parent = elem.parent
                while parent and parent.name and parent.name != 'body' and parent.name != 'html':
                    relevant_elements.add(parent)
                    parent = parent.parent
        
        # Find price elements
        for elem in soup.find_all('span', class_='price'):
            relevant_elements.add(elem)
            parent = elem.parent
            while parent and parent.name and parent.name != 'body':
                relevant_elements.add(parent)
                parent = parent.parent
        
        # Find elements with flight/segment/airline/price in class name
        for elem in soup.find_all(class_=lambda x: x and any(
            keyword in str(x).lower() for keyword in ['flight', 'segment', 'airline', 'price']
        )):
            relevant_elements.add(elem)
            parent = elem.parent
            while parent and parent.name and parent.name != 'body':
                relevant_elements.add(parent)
                parent = parent.parent
        
        # Find data attributes
        for elem in soup.find_all(attrs={'data-flight-number': True}):
            relevant_elements.add(elem)
        for elem in soup.find_all(attrs={'data-airline': True}):
            relevant_elements.add(elem)
        
        # Build result: keep only relevant elements and their structure
        if relevant_elements:
            # Create a new soup with only relevant elements
            result_soup = BeautifulSoup('<div></div>', 'html.parser')
            result_div = result_soup.div
            
            # Add all relevant elements (BeautifulSoup will handle duplicates)
            for elem in relevant_elements:
                if elem.name and elem not in result_div:
                    try:
                        result_div.append(elem)
                    except Exception:
                        # If element is already part of another, clone it
                        result_div.append(elem.__copy__())
            
            return str(result_soup)
        
        # Fallback: return cleaned version
        return str(soup)
    else:
        # Fallback: basic cleaning
        return clean_html_for_llm(html_content)

