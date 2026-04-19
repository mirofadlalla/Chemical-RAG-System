from pydantic import BaseModel
from typing import List, Optional


class SearchRequest(BaseModel):
    """API request for chemical similarity search."""
    smiles: str
    top_k: int = 3
    explain: bool = True  # Generate explanation for why compounds are similar


class CompoundResult(BaseModel):
    """Individual search result with Tanimoto similarity score and LLM explanation."""
    smiles: str
    similarity_score: float  # Tanimoto similarity (0.0 to 1.0)
    image: Optional[str] = None
    explanation: Optional[str] = None  # LLM-generated explanation of similarity
    cid: Optional[str] = None  # PubChem CID identifier
    name: Optional[str] = None  # Compound name


class SearchResponse(BaseModel):
    """API response containing search results with explanations."""
    results: List[CompoundResult]
    query_smiles: str  # Query compound SMILES
    total_results: int  # Total number of results
