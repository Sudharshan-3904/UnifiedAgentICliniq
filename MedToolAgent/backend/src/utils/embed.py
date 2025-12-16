"""
Embedding utilities using Google Generative AI (Gemini) for text embeddings.
"""
import os
import logging
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    logging.warning("GOOGLE_API_KEY not found in .env file. Embedding functionality will not work.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

def get_embedding(text: str, model: str = "models/embedding-001") -> List[float]:
    """
    Generate embeddings for the given text using Google's Generative AI.
    
    Args:
        text (str): The text to embed
        model (str): The embedding model to use (default: models/embedding-001)
    
    Returns:
        List[float]: The embedding vector
    """
    try:
        result = genai.embed_content(
            model=model,
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        logging.error(f"Error generating embedding: {e}")
        # Return a zero vector as fallback (768 dimensions for embedding-001)
        return [0.0] * 768
