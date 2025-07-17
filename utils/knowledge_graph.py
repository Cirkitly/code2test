# utils/knowledge_graph.py
import faiss
import numpy as np
import os
import requests
import json
from dotenv import load_dotenv

# Load env to get EMBEDDING_MODEL config
load_dotenv()

# In-memory storage for this example.
metadata_store = {}
faiss_index = None

# --- Embedding Generation (Using Local Ollama) ---

async def get_embedding(text: str) -> np.ndarray:
    """
    Generates an embedding for a given text using a local Ollama model.
    This function is now independent of the main LLM_PROVIDER.
    """
    ollama_model = os.getenv("EMBEDDING_MODEL")
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/embeddings")
    
    if not ollama_model:
        raise ValueError("EMBEDDING_MODEL environment variable not set.")
    
    # Adjust URL endpoint for embeddings if using a standard Ollama server
    if ollama_url.endswith("/api/chat"):
        ollama_url = ollama_url.replace("/api/chat", "/api/embeddings")

    try:
        response = requests.post(
            ollama_url,
            json={"model": ollama_model, "prompt": text},
            timeout=60
        )
        response.raise_for_status()
        embedding_data = response.json().get("embedding")
        if not embedding_data:
            raise ValueError("Ollama embedding response did not contain 'embedding' data.")
        return np.array(embedding_data, dtype='float32')

    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama embedding endpoint: {e}")
        # Return a zero vector to avoid crashing the whole batch
        # Dimension for mxbai-embed-large is 1024
        return np.zeros(1024, dtype='float32')
    except Exception as e:
        print(f"An unexpected error occurred during embedding: {e}")
        return np.zeros(1024, dtype='float32')

# --- FAISS Index Management ---

def initialize_index(dimension: int):
    """Initializes a new FAISS index."""
    global faiss_index, metadata_store
    faiss_index = faiss.IndexFlatL2(dimension)
    metadata_store = {}
    print(f"Knowledge graph (FAISS index) initialized with dimension {dimension}.")

async def add_to_index(code_unit_summary: dict):
    """Adds a code unit's summary and embedding to the knowledge graph."""
    if faiss_index is None:
        raise RuntimeError("Index not initialized. Call initialize_index first.")

    text_to_embed = f"Path: {code_unit_summary['file_path']}\nUnit: {code_unit_summary['unit_name']}\nSummary: {code_unit_summary['summary']}"
    embedding = await get_embedding(text_to_embed)

    faiss_index.add(np.array([embedding]))
    
    vector_id = faiss_index.ntotal - 1
    metadata_store[vector_id] = code_unit_summary

async def query_index(query: str, top_k: int = 5) -> list[dict]:
    """Queries the index to find the most relevant code units."""
    if faiss_index is None or faiss_index.ntotal == 0:
        return []

    query_embedding = await get_embedding(query)
    # Ensure query embedding is 2D for FAISS search
    query_embedding_2d = np.array([query_embedding])

    distances, indices = faiss_index.search(query_embedding_2d, top_k)

    results = []
    for i in range(len(indices[0])):
        vector_id = indices[0][i]
        if vector_id != -1:
            result_item = metadata_store[vector_id]
            result_item['relevance_score'] = float(distances[0][i])
            results.append(result_item)
            
    return results

def get_knowledge_graph_data_for_saving() -> dict:
    """Serializes the in-memory knowledge graph for saving to a file."""
    if faiss_index is None:
        return None
    
    # For this demo, we save the metadata. The FAISS index is rebuilt on load.
    return {
        "metadata_store": metadata_store,
        "index_dimension": faiss_index.d,
        "total_vectors": faiss_index.ntotal
    }

# --- Test Block ---
if __name__ == "__main__":
    import asyncio

    async def test_kg():
        # mxbai-embed-large has a dimension of 1024
        dim = 1024
        initialize_index(dim)
        
        summary1 = {"file_path": "a.py", "unit_name": "func_a", "summary": "This function adds two numbers.", "code": "def f(a,b): return a+b"}
        await add_to_index(summary1)
        
        print(f"Index now contains {faiss_index.ntotal} vectors.")
        
        results = await query_index("How to add things?")
        print("Query results:", results)

    # Ensure Ollama server is running and `mxbai-embed-large` is pulled
    print("Testing Knowledge Graph with local Ollama embeddings...")
    print("Ensure Ollama is running and you have run 'ollama pull mxbai-embed-large'.")
    asyncio.run(test_kg())