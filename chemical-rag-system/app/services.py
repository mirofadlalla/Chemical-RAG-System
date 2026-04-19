import json
import os
from functools import lru_cache

from .engine import ChemicalSearchEngine
from .utils import smiles_to_image_url
from .generation import generate_explanations_batch

# Global variables
engine = None
dataset = None
index_path = None
data_path = None


def get_data_paths():
    """Get paths for data and index files."""
    global data_path, index_path
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, "data", "compounds.json")
    index_path = os.path.join(base_dir, "data", "compounds_index.pkl")
    
    return data_path, index_path


def data_exists():
    """Check if compounds.json exists and has data."""
    data_path, _ = get_data_paths()
    
    if not os.path.exists(data_path):
        return False
    
    try:
        with open(data_path) as f:
            data = json.load(f)
        return len(data) > 0
    except:
        return False


def index_exists():
    """Check if FAISS index exists."""
    _, index_path = get_data_paths()
    return os.path.exists(index_path)


def initialize_engine():
    """
    Centralized initialization:
    1. Check if compounds.json exists → use it
    2. If not → run ingest.py
    3. Check if FAISS index exists → load it
    4. If not → build it
    """
    global engine, dataset
    
    if engine is not None:
        return engine
    
    data_path, index_path = get_data_paths()
    
    print("\n" + "="*60)
    print("[STARTUP] Initializing Chemical RAG System (Centralized)")
    print("="*60 + "\n")
    
    # Step 1: Check for compounds.json
    if not data_exists():
        print("[WARNING] compounds.json not found or empty")
        print("[INFO] Running ingestion pipeline...")
        from . import ingest_handler
        ingest_handler.run_ingestion()
    
    # Step 2: Load compounds.json
    print(f"[LOAD] Loading compounds from {data_path}...")
    try:
        with open(data_path) as f:
            dataset = json.load(f)
        print(f"[SUCCESS] Loaded {len(dataset)} compounds")
    except Exception as e:
        raise RuntimeError(f"Failed to load compounds: {e}")
    
    # Step 3: Initialize engine
    smiles_list = [d["smiles"] for d in dataset]
    engine = ChemicalSearchEngine(bit_size=2048, n_lists=200)
    
    # Step 4: Check for FAISS index
    if index_exists():
        print(f"[LOAD] FAISS index found at {index_path}")
        if engine.load_index(index_path):
            print("[SUCCESS] FAISS-IVF index loaded successfully")
            print(f"[SUCCESS] Generation layer enabled with Llama-3.1-8B")
            print("="*60 + "\n")
            return engine
    
    # Step 5: Build and save FAISS index
    print("[BUILD] Building FAISS-IVF index (this may take a few minutes)...")
    engine.add_compounds(smiles_list, metadata_list=dataset)
    engine.save_index(index_path)
    
    print(f"[SUCCESS] Generation layer enabled with Llama-3.1-8B")
    print("="*60 + "\n")
    return engine


def _search_internal(smiles: str, top_k: int, include_explanation: bool = True):
    """
    Internal search using FAISS-IVF with optional LLM explanation.
    
    Args:
        smiles: Query SMILES string
        top_k: Number of results (1-100)
        include_explanation: Whether to generate LLM explanations
    
    Returns:
        List of enriched results with metadata and optional explanations
    """
    if engine is None:
        raise RuntimeError("Engine not initialized. Call initialize_engine() first.")
    
    if dataset is None:
        raise RuntimeError("Dataset not loaded. Call initialize_engine() first.")
    
    # FAISS-IVF search
    results = engine.search(smiles, top_k)
    
    enriched = []
    for r in results:
        cid = r["metadata"].get("cid")
        enriched.append({
            "smiles": r["smiles"],
            "similarity_score": r["similarity_score"],
            "image": smiles_to_image_url(r["smiles"]),
            "cid": str(cid) if cid is not None else None,  # Convert to string for schema
            "name": r["metadata"].get("name"),
            "mw": r["metadata"].get("mw"),
            "explanation": None
        })
    
    # Generate LLM explanations if requested
    if include_explanation:
        enriched = generate_explanations_batch(smiles, enriched)
    
    return enriched


@lru_cache(maxsize=1000)
def cached_search(smiles: str, top_k: int, explain: bool = True):
    """
    Cached search results using FAISS-IVF with optional explanations.
    """
    results = _search_internal(smiles, top_k, include_explanation=explain)
    return tuple([tuple(sorted(r.items())) for r in results])


def get_search_results(smiles: str, top_k: int = 3, explain: bool = True):
    """
    Main search function: FAISS-IVF retrieval with optional LLM generation.
    
    Args:
        smiles: Query SMILES string
        top_k: Number of results to return (default 3, max 100)
        explain: Whether to generate LLM explanations (default True)
    
    Returns:
        Tuple of (results_list, query_smiles)
    """
    results = _search_internal(smiles, top_k, include_explanation=explain)
    return results, smiles


def get_search_results_retrieval_only(smiles: str, top_k: int = 3):
    """
    Fast retrieval-only search (no LLM generation).
    
    Args:
        smiles: Query SMILES string
        top_k: Number of results to return (default 3, max 100)
    
    Returns:
        Tuple of (results_list, query_smiles)
    """
    results = _search_internal(smiles, top_k, include_explanation=False)
    return results, smiles


def get_system_stats():
    """Get system statistics and status."""
    global dataset, engine
    
    if engine is None or dataset is None:
        return {
            "status": "uninitialized",
            "compounds": 0,
            "index_type": "FAISS-IVF",
            "index_exists": False
        }
    
    return {
        "status": "ready",
        "compounds": len(dataset),
        "index_type": "FAISS-IVF (Inverted File)",
        "index_exists": engine.index_built,
        "fingerprint_bits": engine.bit_size,
        "n_lists": engine.n_lists,
        "generation_model": "Llama-3.1-8B-Instruct",
        "generation_enabled": True,
        "endpoints": [
            "/search/retrieval-only - Fast retrieval only",
            "/search/full-rag - Retrieval + LLM explanation"
        ]
    }


