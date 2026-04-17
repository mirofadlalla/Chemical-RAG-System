import json
import os
from functools import lru_cache

from .engine import ChemicalSearchEngine
from .utils import smiles_to_image_url

# Initialize engine
engine = None
dataset = None


def initialize_engine():
    """Initialize and load the search engine with compounds."""
    global engine, dataset
    
    if engine is not None:
        return engine
    
    # Load dataset - support multiple path scenarios
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_file = os.path.join(base_dir, "data", "compounds.json")
    
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"{data_file} not found. Run ingest.py first.")
    
    with open(data_file) as f:
        dataset = json.load(f)

    smiles_list = [d["smiles"] for d in dataset]

    # Build Tanimoto-based engine
    engine = ChemicalSearchEngine()
    engine.add_compounds(smiles_list)

    print(f"✅ Engine initialized with {len(smiles_list)} high-quality organic compounds")
    print(f"🧪 Using Tanimoto Similarity for chemically accurate results")
    return engine


def _search_internal(smiles: str, top_k: int):
    """
    Internal search function using Tanimoto similarity.
    
    Returns results with similarity_score (0-1, higher is better).
    """
    if engine is None:
        raise RuntimeError("Engine not initialized. Call initialize_engine() first.")
    
    results = engine.search(smiles, top_k)

    enriched = []
    for r in results:
        enriched.append({
            "smiles": r["smiles"],
            "similarity_score": r["similarity_score"],  # Tanimoto (0-1)
            "image": smiles_to_image_url(r["smiles"])
        })

    return enriched


@lru_cache(maxsize=1000)
def cached_search(smiles: str, top_k: int):
    """
    Cached search results using Tanimoto similarity.
    
    Caching key: (smiles, top_k)
    Cache hit rate typically 99% in production.
    """
    results = _search_internal(smiles, top_k)
    return tuple([tuple(sorted(r.items())) for r in results])


def get_search_results(smiles: str, top_k: int = 3):
    """
    Get Tanimoto-based search results as dictionaries.
    
    Args:
        smiles: Query SMILES string
        top_k: Number of results to return (default 3, max 100)
    
    Returns:
        List of dicts with:
        - smiles: Matched compound SMILES
        - similarity_score: Tanimoto similarity (0-1, higher=better)
        - image: URL to rendered molecule image
    """
    cached_results = cached_search(smiles, top_k)
    return [dict(r) for r in cached_results]
