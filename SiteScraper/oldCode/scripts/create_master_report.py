import pandas as pd
import os
import re

def create_report():
    status_df = pd.read_csv('data/url_status.csv')
    #status_df = pd.read_csv('data/failed.csv')
    mapping_df = pd.read_csv('data/link_file_status_map.csv')
    updates_df = pd.read_csv('data/url_status_updates.csv')
    
    # Merge status and mapping
    report_df = status_df.merge(mapping_df, on='link', how='left')
    
    # Merge updates for notes/comments
    # We want the latest update for each link
    updates_latest = updates_df.sort_values('id').groupby('link').tail(1)
    report_df = report_df.merge(updates_latest[['link', 'status_code', 'status_abbreviation', 'note']], on='link', how='left')
    
    md_files = os.listdir('md_files')
    id_to_file = {}
    for f in md_files:
        if f.endswith('.md'):
            match = re.match(r'(\d+)_', f)
            if match:
                id_to_file[int(match.group(1))] = f

    def get_system(source_file):
        if pd.isna(source_file): return "Unknown"
        if "Cardiovascular System" in source_file: return "Cardiovascular System"
        if "Knowledge Source" in source_file: return "Knowledge Source"
        return "General"

    report_df['filename'] = report_df['id'].map(id_to_file).fillna('')
    report_df['system'] = report_df['source_file'].apply(get_system)
    
    # Construct comments
    def get_comment(row):
        comments = []
        if row['status'] == 'failed':
            if row['status_code'] == 404:
                comments.append("Link Invalid (404)")
            if row['note'] == 'extraction_failed':
                comments.append("Extraction Failed")
            if pd.notna(row['note']) and "NameResolutionError" in str(row['note']):
                comments.append("DNS Error / Truncated URL")
            if not comments:
                comments.append(str(row['note']) if pd.notna(row['note']) else "Unknown Failure")
        
        # Check for truncation heuristic
        if str(row['link']).endswith('-'):
            comments.append("Heuristic: Likely Truncated Link")
            
        return " | ".join(comments)

    report_df['comments'] = report_df.apply(get_comment, axis=1)
    
    # Check for repeats
    link_counts = report_df['link'].value_counts()
    report_df['is_repeated'] = report_df['link'].map(lambda x: link_counts[x] > 1)
    
    # Select final columns
    final_report = report_df[['link', 'filename', 'system', 'status', 'comments']]
    
    # Save to CSV
    final_report.to_csv('data/master_data_report.csv', index=False)
    print(f"Master report saved to data/master_data_report.csv with {len(final_report)} rows.")
    
    # Print summary of issues
    print("\nSummary of Issues:")
    print(f"Total Links: {len(report_df)}")
    print(f"Failed Links: {len(report_df[report_df['status'] == 'failed'])}")
    print(f"Repeated Links (Unique): {len(link_counts[link_counts > 1])}")
    print(f"Likely Truncated Links: {len(report_df[report_df['comments'].str.contains('Truncated', na=False)])}")

if __name__ == "__main__":
    create_report()
