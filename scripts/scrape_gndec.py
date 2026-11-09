import requests
from bs4 import BeautifulSoup
import json
import os
import re
from urllib.parse import urljoin, urlparse
import logging
from collections import deque
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

START_URL = "https://gndec.ac.in/"
MAX_PAGES = 2000
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "gndec_facts.json")

def is_valid_url(url, base_domain="gndec.ac.in"):
    """Check if the URL belongs to the target domain and is not a static/media file."""
    try:
        parsed = urlparse(url)
        # Check if it belongs to gndec.ac.in (or its subdomains)
        if not parsed.netloc.endswith(base_domain) and parsed.netloc != base_domain:
            return False
        
        # Exclude obvious non-text files
        invalid_extensions = (
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.zip', '.doc', '.docx',
            '.xls', '.xlsx', '.ppt', '.pptx', '.rar', '.exe', '.css', '.js'
        )
        if parsed.path.lower().endswith(invalid_extensions):
            return False
            
        return True
    except:
        return False

def clean_text(text):
    """Remove extra whitespace and newlines from text."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_content(soup, url):
    """Extract main text content and title from a BeautifulSoup object."""
    title = soup.title.string if soup.title else "GNDEC Page"
    title = clean_text(title)
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.extract()
        
    # Get text
    text = soup.get_text(separator=' ', strip=True)
    text = clean_text(text)
    
    # We create a pseudo question using the title
    # For example: "Information about Guru Nanak Dev Engineering College, Ludhiana"
    question = f"What is the information about {title}?"
    
    return {
        "question": question,
        "answer": text,
        "section": title,
        "source_file": url
    }

def scrape_gndec():
    # Load existing scraped data to avoid duplicates
    results = []
    already_scraped = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                results = json.load(f)
                for item in results:
                    already_scraped.add(item.get('source_file', '').split('#')[0].rstrip('/'))
        except Exception as e:
            logging.error(f"Could not read existing {OUTPUT_FILE}: {e}")

    visited = set()
    queue = deque([START_URL])
    
    new_scrapes = 0
    logging.info(f"Starting deep crawl at {START_URL}. Loaded {len(already_scraped)} existing records.")
    
    while queue and len(visited) < MAX_PAGES:
        url = queue.popleft()
        
        # Normalize URL to prevent duplicates (remove fragments, trailing slashes)
        normalized_url = url.split('#')[0].rstrip('/')
        if normalized_url in visited:
            continue
            
        visited.add(normalized_url)
        
        try:
            # We use a slight timeout and standard user agent
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            response = requests.get(normalized_url, headers=headers, timeout=10)
            
            # Skip if not HTML
            if 'text/html' not in response.headers.get('Content-Type', ''):
                continue
                
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract and store data ONLY if we haven't scraped it before
            if normalized_url not in already_scraped:
                content_obj = extract_content(soup, normalized_url)
                # Only save if we got meaningful text (e.g. > 100 chars)
                if len(content_obj['answer']) > 100:
                    results.append(content_obj)
                    already_scraped.add(normalized_url)
                    new_scrapes += 1
                    logging.info(f"[{len(visited)}/{MAX_PAGES}] NEW Scraped: {normalized_url} (Length: {len(content_obj['answer'])} chars)")
            else:
                logging.info(f"[{len(visited)}/{MAX_PAGES}] Skipped (Already saved): {normalized_url}")
            
            # Find new links
            for link in soup.find_all('a', href=True):
                absolute_link = urljoin(normalized_url, link['href'])
                normalized_link = absolute_link.split('#')[0].rstrip('/')
                
                if is_valid_url(normalized_link) and normalized_link not in visited and normalized_link not in queue:
                    queue.append(normalized_link)
                    
            time.sleep(0.5) # Polite delay
            
        except Exception as e:
            logging.warning(f"Failed to scrape {normalized_url}: {e}")
            
    # Save to JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    logging.info(f"Finished! Visited {len(visited)} pages. Appended {new_scrapes} new facts. Total facts: {len(results)} in {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape_gndec()
