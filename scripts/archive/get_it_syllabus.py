import requests
from bs4 import BeautifulSoup
import os
import subprocess
import json
import urllib.parse
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://it.gndec.ac.in/?q=node/19"
output_file = "/home/sharnjeet-singh/Developer/gndec_rag/data/syllabi.json"
temp_dir = "/tmp/syllabi_downloads"
os.makedirs(temp_dir, exist_ok=True)

try:
    with open(output_file, "r") as f:
        existing_data = json.load(f)
except FileNotFoundError:
    existing_data = []

existing_urls = {item.get("url") for item in existing_data if item.get("url")}
new_entries = []

res = requests.get(url, verify=False, timeout=10)
soup = BeautifulSoup(res.text, "html.parser")
base_url = "https://it.gndec.ac.in"
links = soup.find_all("a")

for link in links:
    href = link.get("href")
    text = link.text.strip()
    
    if not href:
        continue
        
    href_lower = href.lower()
    
    if ".pdf" in href_lower:
        full_url = urllib.parse.urljoin(url, href.strip())
        
        if full_url in existing_urls:
            print(f"Skipping already scraped: {full_url}")
            continue
            
        print(f"Downloading: {full_url}")
        try:
            pdf_res = requests.get(full_url, verify=False, timeout=15)
            pdf_path = os.path.join(temp_dir, "temp.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_res.content)
                
            process = subprocess.run(["pdftotext", pdf_path, "-"], capture_output=True, text=True, errors="ignore")
            pdf_text = process.stdout.strip()
            
            if pdf_text:
                chunk_size = 20000
                for i in range(0, len(pdf_text), chunk_size):
                    chunk = pdf_text[i:i+chunk_size]
                    new_entries.append({
                        "title": text if text else "IT Syllabus",
                        "url": full_url,
                        "source": base_url,
                        "content": chunk
                    })
                existing_urls.add(full_url)
                print(f"Extracted {len(pdf_text)} characters.")
            else:
                print(f"No text extracted from {full_url}")
        except Exception as e:
            print(f"Failed to process {full_url}: {e}")

if new_entries:
    print(f"Added {len(new_entries)} new entries.")
    existing_data.extend(new_entries)
    with open(output_file, "w") as f:
        json.dump(existing_data, f, indent=4)
