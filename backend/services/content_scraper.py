"""
Enhanced Content Scraper Service

This service provides improved content extraction using requests + BeautifulSoup
with better article detection, content cleaning, and metadata extraction.
"""

import requests
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentScraper:
    """Enhanced content scraper using requests + BeautifulSoup"""
    
    def __init__(self, timeout: int = 15, max_content_length: int = 10000):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.session = requests.Session()
        
        # Enhanced headers to mimic real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
    
    def scrape_content(self, url: str) -> Dict:
        """
        Scrape content from URL with enhanced extraction
        
        Returns:
            Dict with keys: success, content, title, metadata, error
        """
        try:
            logger.info(f"🌐 Scraping content from: {url}")
            
            # Add respectful delay
            time.sleep(0.5)
            
            # Fetch the page
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract content using multiple strategies
            content_result = self._extract_content(soup, url)
            
            if not content_result['content']:
                return {
                    'success': False,
                    'content': None,
                    'title': None,
                    'metadata': {},
                    'error': 'No content could be extracted from the page'
                }
            
            # Clean and limit content
            cleaned_content = self._clean_content(content_result['content'])
            
            return {
                'success': True,
                'content': cleaned_content,
                'title': content_result['title'],
                'metadata': content_result['metadata'],
                'error': None
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error {e.response.status_code}: {e.response.reason}"
            if e.response.status_code == 403:
                error_msg = "403 Forbidden: Website blocked the request (likely anti-bot protection)"
            elif e.response.status_code == 404:
                error_msg = "404 Not Found: Page does not exist"
            
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'content': None,
                'title': None,
                'metadata': {},
                'error': error_msg
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {self.timeout} seconds"
            logger.error(f"⏰ {error_msg}")
            return {
                'success': False,
                'content': None,
                'title': None,
                'metadata': {},
                'error': error_msg
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return {
                'success': False,
                'content': None,
                'title': None,
                'metadata': {},
                'error': error_msg
            }
    
    def _extract_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract content using multiple strategies"""
        
        # Strategy 1: Look for article-specific tags
        article_content = self._extract_article_content(soup)
        if article_content:
            return article_content
        
        # Strategy 2: Look for main content areas
        main_content = self._extract_main_content(soup)
        if main_content:
            return main_content
        
        # Strategy 3: Fallback to body content
        return self._extract_body_content(soup, url)
    
    def _extract_article_content(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract content from article-specific tags"""
        
        # Look for common article containers
        article_selectors = [
            'article',
            '[role="main"]',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content',
            '.main-content',
            '#content',
            '#main'
        ]
        
        for selector in article_selectors:
            elements = soup.select(selector)
            if elements:
                # Get the largest element (likely main content)
                largest_element = max(elements, key=lambda x: len(x.get_text()))
                
                # Extract title
                title = self._extract_title(soup, largest_element)
                
                # Clean and extract text
                content = self._clean_element_text(largest_element)
                
                if content and len(content.strip()) > 100:  # Minimum content length
                    return {
                        'content': content,
                        'title': title,
                        'metadata': {
                            'extraction_method': 'article_tags',
                            'selector_used': selector
                        }
                    }
        
        return None
    
    def _extract_main_content(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract content from main content areas"""
        
        # Look for main content containers
        main_selectors = [
            'main',
            '.main',
            '#main',
            '.content-wrapper',
            '.page-content',
            '.post-body',
            '.entry-body'
        ]
        
        for selector in main_selectors:
            elements = soup.select(selector)
            if elements:
                largest_element = max(elements, key=lambda x: len(x.get_text()))
                content = self._clean_element_text(largest_element)
                
                if content and len(content.strip()) > 100:
                    return {
                        'content': content,
                        'title': self._extract_title(soup, largest_element),
                        'metadata': {
                            'extraction_method': 'main_content',
                            'selector_used': selector
                        }
                    }
        
        return None
    
    def _extract_body_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """Fallback: extract from body tag"""
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
            element.decompose()
        
        # Get body content
        body = soup.find('body')
        if body:
            content = self._clean_element_text(body)
        else:
            content = soup.get_text()
        
        return {
            'content': content,
            'title': self._extract_title(soup, soup),
            'metadata': {
                'extraction_method': 'body_fallback',
                'url': url
            }
        }
    
    def _extract_title(self, soup: BeautifulSoup, context_element=None) -> str:
        """Extract page title"""
        
        # Try different title sources
        title_selectors = [
            'h1',
            'title',
            '.title',
            '.headline',
            '.post-title',
            '.entry-title'
        ]
        
        if context_element:
            for selector in title_selectors:
                title_elem = context_element.select_one(selector)
                if title_elem and title_elem.get_text().strip():
                    return title_elem.get_text().strip()
        
        # Fallback to page title
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        return "Untitled"
    
    def _clean_element_text(self, element) -> str:
        """Clean text from a BeautifulSoup element"""
        
        # Remove unwanted elements
        for unwanted in element.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            unwanted.decompose()
        
        # Get text content
        text = element.get_text()
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _clean_content(self, content: str) -> str:
        """Final content cleaning and length limiting"""
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # Limit content length
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length]
            # Try to end at a sentence boundary
            last_period = content.rfind('.')
            if last_period > self.max_content_length * 0.8:  # If we can find a good break point
                content = content[:last_period + 1]
        
        return content


def scrape_url_content(url: str, timeout: int = 15, max_content_length: int = 10000) -> Dict:
    """
    Convenience function to scrape content from a URL
    
    Args:
        url: URL to scrape
        timeout: Request timeout in seconds
        max_content_length: Maximum content length to return
    
    Returns:
        Dict with scraping results
    """
    scraper = ContentScraper(timeout=timeout, max_content_length=max_content_length)
    return scraper.scrape_content(url)
