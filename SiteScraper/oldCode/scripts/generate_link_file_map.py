#!/usr/bin/env python3
import csv
import json
import os
import re
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(__file__))
MD_DIR = os.path.join(ROOT, 'md_files')
IN_CSV = os.path.join(ROOT, 'data', 'url_status_classified.csv')
OUT_CSV = os.path.join(ROOT, 'data', 'link_file_status_map.csv')
OUT_JSON = os.path.join(ROOT, 'data', 'link_file_status_map.json')

md_files = os.listdir(MD_DIR)
# lowercase lookup for easier matching
md_lower = {f.lower(): f for f in md_files}

results = []

def infer_system(netloc, path):
    net = netloc.lower()
    if 'pmc.' in net:
        return 'PMC'
    if 'ncbi.nlm.nih.gov' in net and path.startswith('/books'):
        return 'NCBI Books'
    if 'pubmed' in net or 'pubmed.ncbi.nlm.nih.gov' in net:
        return 'PubMed'
    if 'medlineplus.gov' in net:
        return 'MedlinePlus'
    if 'rarediseases.info.nih.gov' in net:
        return 'NIH RareDiseases'
    if 'nhs.uk' in net:
        return 'NHS'
    if 'cdc.gov' in net:
        return 'CDC'
    return netloc


def find_matches(url):
    parsed = urlparse(url)
    path = parsed.path
    last = path.rstrip('/').split('/')[-1]
    # extract PMC or NBK id
    m_pmc = re.search(r'(PMC\d+)', url, re.IGNORECASE)
    m_nbk = re.search(r'(NBK\d+)', url, re.IGNORECASE)
    candidates = set()
    if m_pmc:
        token = m_pmc.group(1).lower()
        for f in md_files:
            if token in f.lower():
                candidates.add(f)
    if m_nbk:
        token = m_nbk.group(1).lower()
        for f in md_files:
            if token in f.lower():
                candidates.add(f)
    # match exact last segment
    if last:
        # strip file extension if present
        seg = last.lower()
        # for .html names in md files, they are stored as e.g. '18_triglycerides.html.md'
        for f in md_files:
            if seg in f.lower():
                candidates.add(f)
        # also check slug replacement: replace non-alnum with -
        slug = re.sub(r'[^0-9a-z]+', '-', seg)
        for f in md_files:
            if slug in f.lower():
                candidates.add(f)
    # fallback: look for any number from url in filename
    nums = re.findall(r"\d{3,}", url)
    for n in nums:
        for f in md_files:
            if n in f:
                candidates.add(f)
    return sorted(candidates)

with open(IN_CSV, newline='', encoding='utf-8') as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        link = row.get('link','').strip()
        working = row.get('working','').strip()
        status_abbr = row.get('status_abbreviation', '') or row.get('status','')
        status_code = row.get('status_code','')
        parsed = urlparse(link) if link else None
        system = infer_system(parsed.netloc, parsed.path) if parsed else ''
        # define success
        success = False
        if working.lower() == 'extracted' or status_abbr.upper() == 'OK' or status_code == '200':
            success = True
        status = 'successful' if success else 'failed'
        matches = find_matches(link) if link else []
        if not matches:
            matches = []
        results.append({
            'link': link,
            'filenames': ';'.join(matches) if matches else '',
            'system': system,
            'status': status,
            'working': working,
            'status_code': status_code,
            'status_abbreviation': status_abbr,
        })

# detect duplicate files used for multiple links and links mapped to multiple files
file_to_links = {}
for r in results:
    for f in (r['filenames'] or '').split(';'):
        if not f: continue
        file_to_links.setdefault(f, set()).add(r['link'])

duplicates = {f: list(links) for f, links in file_to_links.items() if len(links) > 1}

# write CSV
keys = ['link','filenames','system','status','working','status_code','status_abbreviation']
with open(OUT_CSV, 'w', newline='', encoding='utf-8') as fh:
    writer = csv.DictWriter(fh, fieldnames=keys)
    writer.writeheader()
    for r in results:
        writer.writerow({k: r.get(k,'') for k in keys})

# write JSON
out = {'mappings': results, 'duplicate_files': duplicates}
with open(OUT_JSON, 'w', encoding='utf-8') as fh:
    json.dump(out, fh, indent=2)

print(f"Wrote {OUT_CSV} and {OUT_JSON} ({len(results)} mappings, {len(duplicates)} duplicate files found)")
