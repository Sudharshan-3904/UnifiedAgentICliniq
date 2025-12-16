"""
PubMed Article Fetcher Module
Comprehensive tool for fetching, processing, and ranking PubMed articles.
"""
import os
import json
import logging
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dotenv import load_dotenv
from Bio import Entrez
import numpy as np
import faiss
from ..utils.embed import get_embedding
from ..utils.logger import logger

# Load environment variables
load_dotenv()
NCBI_API_KEY = os.getenv("NCBI_API_KEY")
NCBI_EMAIL = os.getenv("NCBI_EMAIL")

if not NCBI_API_KEY:
    logger.warning("NCBI API key not found in .env file. Rate limits will be lower.")

# Set Entrez email and API key
Entrez.email = NCBI_EMAIL
Entrez.api_key = NCBI_API_KEY

# Base URL for NCBI E-utilities (for requests fallback)
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def fetch_pmc_ids(pmids: List[str], batch_size: int = 100) -> List[Dict[str, Optional[str]]]:
    """
    Fetch PMC IDs for a list of PMIDs in batches.
    
    Args:
        pmids (list): List of PMIDs.
        batch_size (int): Number of PMIDs per batch.
    
    Returns:
        list: List of dictionaries with PMID and PMCID (or None).
    """
    all_results = []

    for i in range(0, len(pmids), batch_size):
        batch_pmids = pmids[i:i + batch_size]
        logger.info(f"Fetching PMC IDs for batch {i // batch_size + 1}/{(len(pmids) - 1) // batch_size + 1}...")

        try:
            # First try using elink to get PMC IDs
            handle = Entrez.elink(
                dbfrom="pubmed",
                db="pmc",
                id=batch_pmids,
                retmode="json"
            )
            
            # Parse the JSON response
            response = json.load(handle)
            handle.close()

            # Process each PMID in the batch
            for pmid in batch_pmids:
                pmcid = None
                
                # Look for the corresponding link set
                for linkset in response.get("linksets", []):
                    if str(linkset.get("ids", [None])[0]) == str(pmid):
                        # Look for PMC ID in the links
                        for link in linkset.get("linksetdbs", []):
                            if link.get("links"):
                                pmcid = f"PMC{link['links'][0]}"
                                break
                
                # If no PMC ID found through elink, try esummary
                if not pmcid:
                    try:
                        handle = Entrez.esummary(db="pubmed", id=pmid, retmode="json")
                        summary = json.load(handle)
                        handle.close()
                        
                        if "result" in summary and pmid in summary["result"]:
                            article = summary["result"][pmid]
                            if "articleids" in article:
                                for aid in article["articleids"]:
                                    if aid.get("idtype") == "pmc":
                                        pmcid = f"PMC{aid['value']}"
                                        break
                    except Exception as e:
                        logger.debug(f"Error fetching PMC ID for PMID {pmid} through esummary: {e}")
                
                all_results.append({
                    "pmid": pmid,
                    "pmcid": pmcid
                })

            # Delay between batches to respect rate limits
            time.sleep(0.34)  # ~3 requests per second

        except Exception as e:
            logger.error(f"Error fetching PMC IDs for batch starting at {i}: {e}")
            # Try alternative method for this batch
            for pmid in batch_pmids:
                try:
                    # Try direct esearch to PMC
                    handle = Entrez.esearch(
                        db="pmc",
                        term=f"{pmid}[pmid]",
                        retmode="json"
                    )
                    result = json.load(handle)
                    handle.close()
                    
                    pmcid = None
                    if result.get("esearchresult", {}).get("idlist"):
                        pmcid = f"PMC{result['esearchresult']['idlist'][0]}"
                except Exception as e:
                    logger.debug(f"Error fetching PMC ID for PMID {pmid} through esearch: {e}")
                    pmcid = None
                
                all_results.append({
                    "pmid": pmid,
                    "pmcid": pmcid
                })
                
                # Small delay between individual requests
                time.sleep(0.1)

    return all_results


def fetch_article_details(pmid: str) -> Dict[str, Any]:
    """
    Fetch detailed document information for a given PMID.
    
    Args:
        pmid (str): PubMed ID
    
    Returns:
        dict: Article details including title, abstract, authors, full text, and artifacts
    """
    result = {
        "pmid": pmid,
        "title": None,
        "abstract": None,
        "authors": [],
        "journal": None,
        "pubdate": None,
        "pmcid": None,
        "full_text": None,
        "artifacts": {"supplementary": [], "tables": [], "figures": []}
    }
    
    try:
        # Step 1: Get PMCID
        link_handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc")
        link_record = Entrez.read(link_handle)
        link_handle.close()
        
        if link_record and link_record[0]["LinkSetDb"]:
            result["pmcid"] = f"PMC{link_record[0]['LinkSetDb'][0]['Link'][0]['Id']}"
        
        # Step 2: Fetch metadata
        summary_handle = Entrez.esummary(db="pubmed", id=pmid)
        summary_record = Entrez.read(summary_handle)
        summary_handle.close()
        
        if summary_record and len(summary_record) > 0:
            doc = summary_record[0]
            result["title"] = doc.get("Title", "No title available")
            author_list = doc.get("AuthorList", [])
            if isinstance(author_list, list):
                result["authors"] = [author["Name"] for author in author_list if isinstance(author, dict) and "Name" in author]
            result["journal"] = doc.get("Source", "No journal available")
            result["pubdate"] = doc.get("PubDate", "No publication date")
        
        # Step 3: Fetch abstract
        fetch_handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="xml")
        xml_data = fetch_handle.read()
        fetch_handle.close()
        
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_data)
            abstract_texts = root.findall(".//AbstractText")
            if abstract_texts:
                result["abstract"] = " ".join([text.text for text in abstract_texts if text.text])
            else:
                result["abstract"] = "No abstract available"
        except ET.ParseError:
            result["abstract"] = "Error parsing abstract"
        
        # Step 4: Fetch full text and artifacts if PMCID exists
        if result["pmcid"]:
            try:
                fulltext_handle = Entrez.efetch(
                    db="pmc", 
                    id=result["pmcid"].replace("PMC", ""), 
                    rettype="xml", 
                    retmode="xml"
                )
                fulltext_xml = fulltext_handle.read()
                fulltext_handle.close()
                
                import xml.etree.ElementTree as ET
                fulltext_root = ET.fromstring(fulltext_xml)
                
                # Extract full text
                paragraphs = fulltext_root.findall(".//p")
                result["full_text"] = " ".join([p.text for p in paragraphs if p.text]) if paragraphs else "Full text not available"
                
                # Extract supplementary materials
                suppl_links = fulltext_root.findall(".//supplementary-material")
                for suppl in suppl_links:
                    href = suppl.find(".//media")
                    if href is not None and "xlink:href" in href.attrib:
                        result["artifacts"]["supplementary"].append({
                            "id": suppl.get("id", "N/A"),
                            "url": href.attrib["xlink:href"],
                            "caption": suppl.find(".//caption/p").text if suppl.find(".//caption/p") is not None else "N/A"
                        })
                
                # Extract tables
                tables = fulltext_root.findall(".//table-wrap")
                for table in tables:
                    caption = table.find(".//caption/p")
                    result["artifacts"]["tables"].append({
                        "id": table.get("id", "N/A"),
                        "caption": caption.text if caption is not None else "N/A",
                        "content": ET.tostring(table, encoding="unicode")
                    })
                
                # Extract figures
                figures = fulltext_root.findall(".//fig")
                for fig in figures:
                    graphic = fig.find(".//graphic")
                    if graphic is not None and "xlink:href" in graphic.attrib:
                        result["artifacts"]["figures"].append({
                            "id": fig.get("id", "N/A"),
                            "url": graphic.attrib["xlink:href"],
                            "caption": fig.find(".//caption/p").text if fig.find(".//caption/p") is not None else "N/A"
                        })
            except Exception as e:
                logger.error(f"Error fetching full text/artifacts: {e}")
                result["full_text"] = "Error fetching full text"
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching document details for PMID {pmid}: {e}")
        return result


def chunk_text(text: str, max_chars: int = 8000, chunk_overlap: int = 200) -> List[str]:
    """
    Chunk text into smaller pieces for embedding.
    
    Args:
        text (str): Text to chunk
        max_chars (int): Maximum characters per chunk
        chunk_overlap (int): Overlap between chunks
    
    Returns:
        List[str]: List of text chunks
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chars
        
        # Try to break at a sentence boundary
        if end < len(text):
            # Look for sentence endings near the end
            for punct in ['. ', '! ', '? ', '\n\n']:
                last_punct = text[start:end].rfind(punct)
                if last_punct != -1:
                    end = start + last_punct + len(punct)
                    break
        
        chunks.append(text[start:end])
        start = end - chunk_overlap
    
    return chunks


def embed_article_with_chunks(article: Dict[str, Any]) -> List[float]:
    """
    Generate embeddings for an article by chunking and averaging.
    
    Args:
        article (dict): Article data
    
    Returns:
        List[float]: Average embedding vector
    """
    # Combine title, abstract, full text
    content = f"Title: {article.get('title', '')}\nAbstract: {article.get('abstract', '')}\nFull text: {article.get('full_text', '') or ''}"
    
    chunks = chunk_text(content)
    chunk_embeddings = []
    
    for chunk in chunks:
        try:
            emb = get_embedding(chunk)
            chunk_embeddings.append(emb)
        except Exception as e:
            logger.error(f"Error embedding chunk: {e}")
    
    if not chunk_embeddings:
        return [0.0] * 768  # fallback dimension
    
    # Average embeddings
    return np.mean(np.array(chunk_embeddings), axis=0).tolist()


def sanitize_dirname(name: str) -> str:
    """
    Sanitize a string to be used as a directory name.
    
    Args:
        name (str): Original name
    
    Returns:
        str: Sanitized name
    """
    return re.sub(r'[^\w\-_ ]', '', name)[:50].strip().replace(' ', '_')


def search_and_fetch_pubmed_articles(
    query: str,
    num_articles: int = 10,
    date_from: str = "2024/04/18",
    date_to: str = "3000",
    top_n: int = 3,
    save_to_disk: bool = False,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search PubMed, fetch articles, rank them by relevance using embeddings.
    
    Args:
        query (str): Search query
        num_articles (int): Number of articles to fetch
        date_from (str): Start date for publication filter
        date_to (str): End date for publication filter
        top_n (int): Number of top articles to return
        save_to_disk (bool): Whether to save results to disk
        output_dir (str): Directory to save results (optional)
    
    Returns:
        dict: Results containing best articles and metadata
    """
    logger.info(f"Searching PubMed for: {query}")
    
    # Build query with date criteria
    date_criteria = f"{date_from}[Date - Publication] : {date_to}[Date - Publication]"
    full_query = f"({query}) AND {date_criteria}"
    
    try:
        # Search PubMed
        handle = Entrez.esearch(
            db="pubmed",
            term=full_query,
            retmax=num_articles,
            sort="relevance",
            retmode="json"
        )
        response = json.load(handle)
        handle.close()
        
        pmids = response["esearchresult"].get("idlist", [])
        
        if not pmids:
            logger.warning("No articles found for your query.")
            return {
                "status": "no_results",
                "query": query,
                "articles": [],
                "message": "No articles found for your query."
            }
        
        logger.info(f"Found {len(pmids)} articles. Fetching details...")
        
        # Fetch article details
        articles = []
        for idx, pmid in enumerate(pmids, 1):
            logger.info(f"[{idx}/{len(pmids)}] Fetching details for PMID {pmid}...")
            details = fetch_article_details(pmid)
            articles.append(details)
            time.sleep(0.34)  # Rate limiting
        
        # Embed articles and build FAISS index
        logger.info("Embedding articles with Gemini API and building FAISS index...")
        article_embeddings = []
        
        for idx, art in enumerate(articles):
            logger.info(f"Embedding article {idx+1}/{len(articles)}...")
            emb = embed_article_with_chunks(art)
            article_embeddings.append(emb)
        
        # Build FAISS index
        emb_dim = len(article_embeddings[0])
        index = faiss.IndexFlatL2(emb_dim)
        emb_matrix = np.array(article_embeddings).astype('float32')
        index.add(emb_matrix)
        
        # Embed user query
        query_emb = get_embedding(query)
        query_emb = np.array(query_emb).astype('float32').reshape(1, -1)
        
        # Search for top N similar articles
        D, I = index.search(query_emb, min(top_n, len(articles)))
        
        best_articles = [articles[idx] for idx in I[0]]
        
        logger.info(f"Found {len(best_articles)} best matching articles")
        
        # Save to disk if requested
        if save_to_disk:
            if output_dir is None:
                from ..config.settings import settings
                output_dir = os.path.join(settings.BASE_DIR, "output", sanitize_dirname(query))
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            for i, art in enumerate(best_articles, 1):
                fname = output_path / f"best_article_{i}_pmid_{art['pmid']}.json"
                with open(fname, "w", encoding="utf-8") as f:
                    json.dump(art, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved: {fname}")
        
        return {
            "status": "success",
            "query": query,
            "total_found": len(pmids),
            "total_fetched": len(articles),
            "top_n": top_n,
            "best_articles": best_articles,
            "message": f"Successfully fetched and ranked {len(best_articles)} articles"
        }
        
    except Exception as e:
        logger.error(f"Error searching PubMed: {e}")
        return {
            "status": "error",
            "query": query,
            "articles": [],
            "message": f"Error: {str(e)}"
        }
