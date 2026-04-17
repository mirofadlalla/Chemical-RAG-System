from pydantic import BaseModel
from typing import List, Optional


class SearchRequest(BaseModel):
    """API request for chemical similarity search."""
    smiles: str
    top_k: int = 3


class CompoundResult(BaseModel):
    """Individual search result with Tanimoto similarity score."""
    smiles: str
    similarity_score: float  # Tanimoto similarity (0.0 to 1.0)
    image: Optional[str] = None


class SearchResponse(BaseModel):
    """API response containing search results."""
    results: List[CompoundResult]
