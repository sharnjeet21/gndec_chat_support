import os
import re
import json
import logging
import requests
import warnings
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote

try:
    import pdfplumber
except ImportError:
    raise ImportError("Please install pdfplumber (pip install pdfplumber) to run this scraper.")

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEPARTMENTS = [
    "https://cse.gndec.ac.in/",
    "https://it.gndec.ac.in/",
    "https://ee.gndec.ac.in/",
    "https://ece.gndec.ac.in/",
    "https://me.gndec.ac.in/",
    "https://ce.gndec.ac.in/",
    "https://mba.gndec.ac.in/",
    "https://mca.gndec.ac.in/",
]

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def extract_pdf_text(pdf_path):
    text_content = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract words and attempt to preserve layout/tables where possible
                text = page.extract_text(x_tolerance=2, y_tolerance=3)
                if text:
                    text_content.append(text)
    except Exception as e:
        logger.error(f"Error parsing PDF {pdf_path}: {e}")
    return "\n\n".join(text_content)

def fetch_syllabus_links(base_url, max_depth=2):
    logger.info(f"Scanning {base_url} (up to depth {max_depth}) for syllabus links...")
    
    visited = set()
    queue = [(base_url, 0)]
    pdf_links = []
    
    while queue:
        current_url, depth = queue.pop(0)
        
        if current_url in visited:
            continue
        visited.add(current_url)
        
        try:
            resp = requests.get(current_url, timeout=10, verify=False)
            if 'text/html' not in resp.headers.get('Content-Type', ''):
                continue
            resp.raise_for_status()
        except Exception as e:
            continue
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        for a in soup.find_all('a'):
            href = a.get('href', '')
            link_text = a.text.strip().lower()
            if not href or href.startswith('javascript:'):
                continue
                
            abs_url = urljoin(current_url, href)
            # Remove fragments
            abs_url = abs_url.split('#')[0]
            
            href_lower = abs_url.lower()
            
            # Is it a PDF?
            if href_lower.endswith('.pdf') or href_lower.endswith('.docx') or href_lower.endswith('.doc'):
                if 'syllabus' in link_text or 'scheme' in link_text or 'syllabus' in href_lower or 'scheme' in href_lower:
                    if abs_url not in [l['url'] for l in pdf_links]:
                        title = a.text.strip()
                        if not title:
                            title = unquote(href.split('/')[-1].replace('.pdf', '').replace('.docx', '').replace('_', ' '))
                        pdf_links.append({"title": title, "url": abs_url, "source": current_url})
            
            # Is it an internal HTML page to crawl?
            elif depth < max_depth:
                if abs_url.startswith(base_url) and abs_url not in visited:
                    # Ignore obvious non-html files
                    if not any(abs_url.lower().endswith(ext) for ext in ['.jpg', '.png', '.zip', '.rar']):
                        queue.append((abs_url, depth + 1))
                        
    logger.info(f"Found {len(pdf_links)} syllabus documents on {base_url}")
    return pdf_links

def run_scraper():
    all_links = []
    for dept in DEPARTMENTS:
        links = fetch_syllabus_links(dept)
        all_links.extend(links)
        
    logger.info(f"Total syllabus links found across all departments: {len(all_links)}")
    
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    temp_dir = os.path.join(out_dir, "temp_syllabi")
    os.makedirs(temp_dir, exist_ok=True)
    
    syllabi_data = []
    
    for link_obj in all_links:
        url = link_obj['url']
        title = link_obj['title']
        source = link_obj['source']
        
        if not url.endswith('.pdf'):
            continue # We only handle PDFs for now to ensure quality
            
        filename = unquote(url.split('/')[-1])
        filepath = os.path.join(temp_dir, filename)
        
        logger.info(f"Downloading {filename}...")
        try:
            r = requests.get(url, stream=True, timeout=20, verify=False)
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                        
                logger.info(f"Extracting text from {filename}...")
                raw_text = extract_pdf_text(filepath)
                cleaned_text = clean_text(raw_text)
                
                if len(cleaned_text) > 100:
                    syllabi_data.append({
                        "title": title,
                        "url": url,
                        "source": source,
                        "content": cleaned_text
                    })
                else:
                    logger.warning(f"Extracted text too short for {filename}. Skipping.")
                    
                # Delete temp file
                os.remove(filepath)
            else:
                logger.error(f"Failed to download {url} (Status: {r.status_code})")
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            
    # Save the JSON
    out_path = os.path.join(out_dir, "syllabi.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(syllabi_data, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Successfully processed {len(syllabi_data)} syllabi and saved to {out_path}")
    
    # Cleanup temp dir
    try:
        os.rmdir(temp_dir)
    except:
        pass

if __name__ == "__main__":
    run_scraper()
