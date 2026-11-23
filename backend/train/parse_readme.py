import urllib.request
import re

url = "https://ieee-dataport.org/documents/bilingual-civic-complaint-classification-dataset-english-and-marathi-public-service"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Search for all mentions of filenames or extensions in HTML
print("--- ALL FILENAMES / ATTACHMENTS IN HTML ---")
matches = re.findall(r'([a-zA-Z0-9_\-\.\/]+\.(?:csv|zip|xlsx|json|txt|md))', html)
print(set(matches))

# Let's see the rest of README.md from S3
s3_links = re.findall(r'https://ieee-dataport\.s3\.amazonaws\.com/[^"\']+', html)
for s in s3_links:
    s_clean = s.replace('&amp;', '&')
    r = urllib.request.urlopen(urllib.request.Request(s_clean, headers={"User-Agent": "Mozilla/5.0"}))
    readme_text = r.read().decode('utf-8', errors='ignore')
    print("--- FULL README ---")
    print(readme_text)
