"""
Standalone CLI for testing PubMed Article Fetcher
Run this script to test the PubMed fetching functionality independently.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.pubmed_fetcher import search_and_fetch_pubmed_articles, sanitize_dirname
from src.utils.logger import logger
import json


def cli_main():
    """Main CLI function for interactive PubMed article fetching."""
    print("\n" + "="*60)
    print("PubMed Article Fetcher CLI")
    print("="*60)
    
    query = input("\nEnter your PubMed search query: ").strip()
    if not query:
        print("No query entered. Exiting.")
        return
    
    # Get number of articles to fetch
    num_input = input("Number of articles to fetch (default: 10): ").strip()
    num_articles = int(num_input) if num_input.isdigit() else 10
    
    # Get number of top articles to return
    top_input = input("Number of top articles to return (default: 3): ").strip()
    top_n = int(top_input) if top_input.isdigit() else 3
    
    print(f"\n🔍 Searching PubMed for: '{query}'")
    print(f"📊 Fetching {num_articles} articles, returning top {top_n}...")
    print("-" * 60)
    
    # Fetch articles
    result = search_and_fetch_pubmed_articles(
        query=query,
        num_articles=num_articles,
        top_n=top_n,
        save_to_disk=False
    )
    
    if result["status"] == "error":
        print(f"\n❌ Error: {result['message']}")
        return
    
    if result["status"] == "no_results":
        print(f"\n⚠️  No articles found for query: {query}")
        return
    
    # Display results
    print(f"\n✅ Found {result['total_found']} articles")
    print(f"📥 Fetched and analyzed {result['total_fetched']} articles")
    print(f"\n🏆 Top {len(result['best_articles'])} Most Relevant Articles:")
    print("=" * 60)
    
    best_articles = result['best_articles']
    
    for idx, article in enumerate(best_articles, 1):
        print(f"\n{'─' * 60}")
        print(f"📄 Article #{idx}")
        print(f"{'─' * 60}")
        print(f"Title: {article.get('title', 'N/A')}")
        print(f"Authors: {', '.join(article.get('authors', [])[:5])}")
        if len(article.get('authors', [])) > 5:
            print(f"         ... and {len(article['authors']) - 5} more")
        print(f"Journal: {article.get('journal', 'N/A')}")
        print(f"Publication Date: {article.get('pubdate', 'N/A')}")
        print(f"PMID: {article.get('pmid', 'N/A')}")
        print(f"PMCID: {article.get('pmcid', 'N/A')}")
        
        # Show abstract preview
        abstract = article.get('abstract', 'No abstract available')
        if len(abstract) > 300:
            abstract = abstract[:300] + "..."
        print(f"\nAbstract Preview:")
        print(f"  {abstract}")
        
        # Show availability info
        if article.get('full_text'):
            print(f"\n✓ Full text available")
        if article.get('artifacts', {}).get('figures'):
            print(f"✓ {len(article['artifacts']['figures'])} figure(s) available")
        if article.get('artifacts', {}).get('tables'):
            print(f"✓ {len(article['artifacts']['tables'])} table(s) available")
    
    # Ask to save
    print("\n" + "=" * 60)
    save = input("\n💾 Save these articles to disk? (y/n): ").strip().lower()
    
    if save == 'y':
        # Re-run with save enabled
        output_dir = Path(__file__).parent / "output" / sanitize_dirname(query)
        
        result = search_and_fetch_pubmed_articles(
            query=query,
            num_articles=num_articles,
            top_n=top_n,
            save_to_disk=True,
            output_dir=str(output_dir)
        )
        
        print(f"\n✅ Articles saved to: {output_dir}")
        for i in range(1, len(best_articles) + 1):
            print(f"   - best_article_{i}_pmid_{best_articles[i-1]['pmid']}.json")
    else:
        print("\n📝 Articles not saved.")
    
    # Ask to view full text
    while True:
        print("\n" + "=" * 60)
        sel = input(f"\nEnter 1-{len(best_articles)} to view full text, or press Enter to exit: ").strip()
        
        if not sel:
            break
        
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(best_articles):
                art = best_articles[idx]
                print(f"\n{'═' * 60}")
                print(f"Full Text of Article #{sel}")
                print(f"{'═' * 60}")
                print(f"Title: {art['title']}\n")
                
                full_text = art.get('full_text', 'No full text available.')
                
                # Display in chunks for readability
                if len(full_text) > 2000:
                    print(full_text[:2000])
                    more = input("\n... [Press Enter to see more, or 'q' to stop] ").strip().lower()
                    if more != 'q':
                        print(full_text[2000:])
                else:
                    print(full_text)
            else:
                print("❌ Invalid selection.")
        except ValueError:
            print("❌ Please enter a valid number.")
    
    print("\n" + "=" * 60)
    print("Thank you for using PubMed Article Fetcher!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        cli_main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ An error occurred: {e}")
