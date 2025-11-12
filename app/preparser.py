"""Content pre-parsing to remove boilerplate and extract main content."""

try:
    from selectolax.parser import HTMLParser
    SELECTOLAX_AVAILABLE = True
except ImportError:
    SELECTOLAX_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

try:
    import trafilatura
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
    Clean HTML by removing boilerplate elements.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Cleaned HTML with boilerplate removed
    """
    if SELECTOLAX_AVAILABLE:
        tree = HTMLParser(html_content)
        for tag in tree.css('script, style, nav, footer, header, aside, noscript, meta, link'):
            tag.decompose()
        return tree.html
    elif BEAUTIFULSOUP_AVAILABLE:
        soup = BeautifulSoup(html_content, 'html.parser')
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'meta', 'link']):
            tag.decompose()
        return str(soup)
    else:
        # No parser available, return original HTML
        return html_content

