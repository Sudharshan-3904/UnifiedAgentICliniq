"""
Test script for PubMed fetcher functionality
Run this to verify the implementation is working correctly.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.tools.base import search_pubmed
from src.utils.logger import logger


def test_search_pubmed_tool():
    """Test the search_pubmed LangChain tool."""
    print("\n" + "="*60)
    print("Testing search_pubmed Tool")
    print("="*60)
    
    # Test with a simple query
    query = "diabetes treatment"
    print(f"\nQuery: {query}")
    print("Fetching 5 articles, returning top 2...")
    
    try:
        result = search_pubmed.invoke({
            "query": query,
            "num_articles": 5,
            "top_n": 2
        })
        
        print("\n" + "-"*60)
        print("RESULT:")
        print("-"*60)
        print(result)
        print("\n✅ Test passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test error: {e}", exc_info=True)


def test_direct_function():
    """Test the direct pubmed_fetcher function."""
    print("\n" + "="*60)
    print("Testing Direct Function")
    print("="*60)
    
    from src.tools.pubmed_fetcher import search_and_fetch_pubmed_articles
    
    query = "COVID-19 vaccine"
    print(f"\nQuery: {query}")
    print("Fetching 3 articles, returning top 2...")
    
    try:
        result = search_and_fetch_pubmed_articles(
            query=query,
            num_articles=3,
            top_n=2,
            save_to_disk=False
        )
        
        print("\n" + "-"*60)
        print("RESULT:")
        print("-"*60)
        print(f"Status: {result['status']}")
        print(f"Total found: {result.get('total_found', 'N/A')}")
        print(f"Total fetched: {result.get('total_fetched', 'N/A')}")
        print(f"Number of best articles: {len(result.get('best_articles', []))}")
        
        if result.get('best_articles'):
            print("\nFirst article:")
            article = result['best_articles'][0]
            print(f"  Title: {article.get('title', 'N/A')}")
            print(f"  PMID: {article.get('pmid', 'N/A')}")
            print(f"  Authors: {', '.join(article.get('authors', [])[:3])}")
        
        print("\n✅ Test passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test error: {e}", exc_info=True)


def test_embedding():
    """Test the embedding functionality."""
    print("\n" + "="*60)
    print("Testing Embedding Function")
    print("="*60)
    
    from src.utils.embed import get_embedding
    
    text = "This is a test sentence for embedding."
    print(f"\nText: {text}")
    
    try:
        embedding = get_embedding(text)
        print(f"\nEmbedding dimension: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
        print("\n✅ Test passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test error: {e}", exc_info=True)


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PubMed Fetcher Test Suite")
    print("="*60)
    
    print("\nThis will test the PubMed fetcher implementation.")
    print("Make sure you have set up your .env file with API keys.")
    
    input("\nPress Enter to start tests...")
    
    # Test 1: Embedding
    test_embedding()
    
    input("\nPress Enter to continue to next test...")
    
    # Test 2: Direct function
    test_direct_function()
    
    input("\nPress Enter to continue to next test...")
    
    # Test 3: LangChain tool
    test_search_pubmed_tool()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests cancelled by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")
