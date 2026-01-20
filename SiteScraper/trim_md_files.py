import os
import re

SOURCE_DIR = "md_files"
DEST_DIR = "md_files_trimmed"

STOP_HEADERS = [
    "References",
    "Bibliography",
    "Citations",
    "Author Contributions",
    "Authors' contributions",
    "Related Resources",
    "Review Questions",
    "Images",
    "Clinical Trials Accepting Patients",
    "Research Results and Related Resources",
    "Contributor Information",
    "Availability of data and materials",
    "Ethics approval and consent to participate",
    "Consent for publication",
    "Competing interests",
    "Funding",
    "Institutional Review Board Statement",
    "Informed Consent Statement",
    "Data Availability Statement",
    "Conflicts of Interest",
    "Conflict of Interest",
    "Funding Statement",
    "Associated Data",
    "Acknowledgments",
    "Genetic Testing Information",
    "Genetic and Rare Diseases Information Center",
    "Patient Support and Advocacy Resources",
    "Patient Support",
    "Clinical Trials",
    "Catalog of Genes and Diseases from OMIM",
    "Scientific Articles on PubMed",
    "Medical Encyclopedia",
    "Understanding Genetics",
    "Related Health Topics",
    "Disclaimers",
    "Disclaimer",
    "Reuse of NCI Information",
    "Syndication Services"
]

# Phrases that indicate EOF or footer junk (Stop if line starts with these)
STOP_PHRASES = [
    "If you would like to reproduce some or all of this content",
    "Want to use this content on your website"
]

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def should_stop(line):
    # Check headers
    # Matches lines like: "# References", "## References", "###  References "
    line_stripped = line.strip()
    
    # Check for header format
    if line_stripped.startswith('#'):
        # Remove # and whitespace
        header_text = line_stripped.lstrip('#').strip()
        for stop_header in STOP_HEADERS:
            if header_text.lower() == stop_header.lower():
                return True
    
    # Check for footer phrases
    for phrase in STOP_PHRASES:
        if line_stripped.startswith(phrase):
            return True
            
    # flexible check for Updated line (e.g. "- Updated:May 15")
    # Matches "Updated:" or "- Updated:" at start of line
    if re.match(r'^[-*\s]*Updated\s*:', line_stripped, re.IGNORECASE):
        return True

    return False

def process_file(filename):
    source_path = os.path.join(SOURCE_DIR, filename)
    dest_path = os.path.join(DEST_DIR, filename)
    
    with open(source_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    kept_lines = []
    
    for line in lines:
        if should_stop(line):
            print(f"[{filename}] Cutting off at: {line.strip()[:50]}...")
            break
        kept_lines.append(line)
        
    # Write to destination
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.writelines(kept_lines)

def main():
    ensure_dir(DEST_DIR)
    
    files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.md')]
    print(f"Found {len(files)} markdown files.")
    
    for i, file in enumerate(files):
        try:
            process_file(file)
        except Exception as e:
            print(f"Error processing {file}: {e}")
            
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1}/{len(files)} files...")

    print("Done.")

if __name__ == "__main__":
    main()
