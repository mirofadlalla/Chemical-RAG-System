from pydantic import BaseModel
from typing import List, Optional


class SearchRequest(BaseModel):
    smiles: str
    top_k: int = 3


class CompoundResult(BaseModel):
    smiles: str
    distance: float
    image: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[CompoundResult]
