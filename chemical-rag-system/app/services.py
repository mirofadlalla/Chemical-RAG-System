import json
import pickle
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

    # Build engine
    engine = ChemicalSearchEngine()
    engine.add_compounds(smiles_list)

    print(f"✅ Engine initialized with {len(smiles_list)} compounds")
    return engine


def _search_internal(smiles: str, top_k: int):
    """Internal search function."""
    if engine is None:
        raise RuntimeError("Engine not initialized. Call initialize_engine() first.")
    
    results = engine.search(smiles, top_k)

    enriched = []
    for r in results:
        enriched.append({
            "smiles": r["smiles"],
            "distance": r["distance"],
            "image": smiles_to_image_url(r["smiles"])
        })

    return enriched


@lru_cache(maxsize=1000)
def cached_search(smiles: str, top_k: int):
    """Cached search results."""
    results = _search_internal(smiles, top_k)
    return tuple([tuple(sorted(r.items())) for r in results])


def get_search_results(smiles: str, top_k: int = 3):
    """Get search results as dictionaries."""
    cached_results = cached_search(smiles, top_k)
    return [dict(r) for r in cached_results]
