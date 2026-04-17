from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
import os

from .schemas import SearchRequest, SearchResponse, CompoundResult
from .services import initialize_engine, get_search_results

app = FastAPI(title="Chemical RAG System", version="1.0.0")

# Mount static files
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize the engine on startup."""
    try:
        initialize_engine()
        print("✅ API startup successful")
    except FileNotFoundError as e:
        print(f"⚠️ {e}")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "running", "service": "Chemical RAG System"}


@app.get("/health")
async def health():
    """Health check with detailed status."""
    return {
        "status": "healthy",
        "service": "Chemical RAG System",
        "version": "1.0.0"
    }


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search for similar compounds."""
    
    # Validate SMILES
    if not request.smiles or len(request.smiles.strip()) == 0:
        raise HTTPException(status_code=400, detail="SMILES string cannot be empty")
    
    if request.top_k < 1 or request.top_k > 100:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 100")

    try:
        # Run search in threadpool to avoid blocking
        results = await run_in_threadpool(
            get_search_results,
            request.smiles.strip(),
            request.top_k
        )

        if not results:
            raise HTTPException(status_code=400, detail="Invalid SMILES string")

        # Convert to response model
        compound_results = [
            CompoundResult(
                smiles=r["smiles"],
                similarity_score=r["similarity_score"],  # Tanimoto (0-1)
                image=r.get("image")
            )
            for r in results
        ]

        return SearchResponse(results=compound_results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def stats():
    """Get system statistics."""
    from .services import dataset, engine
    
    if engine is None or dataset is None:
        return {
            "compounds": 0,
            "index_size": 0,
            "fingerprint_bits": 2048,
            "similarity_metric": "Tanimoto"
        }
    
    return {
        "compounds": len(dataset),
        "index_size": len(engine.fingerprints),
        "fingerprint_bits": engine.bit_size,
        "similarity_metric": "Tanimoto",
        "method": "RDKit (Binary fingerprints)"
    }
