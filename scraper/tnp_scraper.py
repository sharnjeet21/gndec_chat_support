import os
import json
import logging
import requests
import urllib3
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
TNP_URL = "https://www.tnpgndec.com"

import fitz # PyMuPDF
import io

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text: str, source_url: str, title: str, chunk_size=800) -> list:
    words = text.split()
    chunks = []
    current_chunk = []
    current_len = 0
    
    for word in words:
        current_chunk.append(word)
        current_len += len(word) + 1
        if current_len >= chunk_size:
            chunk_str = " ".join(current_chunk)
            q = f"What is the information regarding {title}?"
            chunks.append({
                "question": q,
                "answer": chunk_str,
                "section": "Training & Placement",
                "source_file": "tnp_scraper",
                "doc_url": source_url
            })
            current_chunk = []
            current_len = 0
            
    if current_chunk:
        chunk_str = " ".join(current_chunk)
        q = f"What is the information regarding {title}?"
        chunks.append({
            "question": q,
            "answer": chunk_str,
            "section": "Training & Placement",
            "source_file": "tnp_scraper",
            "doc_url": source_url
        })
        
    return chunks

def scrape_tnp():
    logger.info("Starting TNP scrape...")
    visited = set()
    queue = [(TNP_URL, 0)]
    all_chunks = []
    
    while queue:
        current_url, depth = queue.pop(0)
        
        if current_url in visited:
            continue
        visited.add(current_url)
        
        logger.info(f"Visiting: {current_url} (Depth {depth})")
        import time
        time.sleep(1)
        
        try:
            resp = requests.get(current_url, timeout=15, verify=False)
            content_type = resp.headers.get('Content-Type', '').lower()
            
            if 'pdf' in content_type or current_url.lower().endswith('.pdf'):
                logger.info(f" Parsing PDF: {current_url}")
                try:
                    with fitz.open(stream=resp.content, filetype="pdf") as doc:
                        full_text = ""
                        for page in doc:
                            text = page.get_text()
                            if text:
                                full_text += text + "\n"
                        title = unquote(current_url.split('/')[-1].replace('.pdf', '').replace('_', ' '))
                        if not title:
                            title = "TNP Placement Document"
                        cleaned = clean_text(full_text)
                        if cleaned:
                            all_chunks.extend(chunk_text(cleaned, current_url, title))
                except Exception as e:
                    logger.error(f" Failed to parse PDF {current_url}: {e}")
                continue
            elif 'text/html' not in content_type:
                continue
                
        except Exception as e:
            logger.error(f" Failed to fetch {current_url}: {e}")
            continue
            
        # Parse HTML
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        page_title = soup.title.string.strip() if soup.title and soup.title.string else "TNP Page"
        
        # Extract HTML text content
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        
        page_text = clean_text(soup.get_text(separator=' '))
        if page_text:
             all_chunks.extend(chunk_text(page_text, current_url, page_title))
        
        # Enqueue links (up to depth 3)
        if depth < 3:
            for a in soup.find_all('a'):
                href = a.get('href', '')
                if not href or href.startswith('javascript:'):
                    continue
                abs_url = urljoin(current_url, href).split('#')[0]
                
                # Only crawl tnpgndec.com
                if abs_url.startswith(TNP_URL) and abs_url not in visited:
                    if not any(abs_url.lower().endswith(ext) for ext in ['.jpg', '.png', '.zip', '.rar']):
                        queue.append((abs_url, depth + 1))
                        
    out_path = os.path.join(DATA_DIR, "tnp_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)
        
    logger.info(f"Done! Saved {len(all_chunks)} chunks to {out_path}")

if __name__ == "__main__":
    scrape_tnp()
