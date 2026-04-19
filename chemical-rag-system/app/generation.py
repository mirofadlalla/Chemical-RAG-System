import os
import requests
from typing import Optional, Dict, List
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

"""
LLM-based Generation Layer for Chemical Similarity Explanation
Version 2.0: Optimized with RDKit Grounding & Hallucination Guardrails
"""

# 1. RDKit Metadata Engine - لمنع التخمين الخاطئ
def get_rdkit_metadata(smiles: str) -> Dict:
    """Extracts factual chemical data to anchor the LLM response."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return {}
        return {
            "formula": rdMolDescriptors.CalcMolFormula(mol),
            "mw": round(Descriptors.MolWt(mol), 2),
            "heavy_atoms": mol.GetNumHeavyAtoms(),
            "formal_charge": Chem.GetFormalCharge(mol)
        }
    except Exception:
        return {}

# 2. System Prompt - تحديد قواعد اللعبة
def build_system_prompt() -> str:
    """Build the system prompt with strict chemical constraints."""
    return """Role:
You are an expert Cheminformatics AI Assistant. Your task is to explain the structural similarity between a "Query Compound" and a "Match Compound" based on SMILES notation and provided RDKit metadata.

Strict Guidelines to Prevent Hallucinations:
1. GROUNDING: Use the provided Molecular Formula to verify atom counts. If the formula is C4H9Br, do NOT say it has 4 Bromine atoms.
2. TETRAVALENCY: Carbon is ALWAYS tetravalent (4 bonds). Never describe a carbon atom as "pentavalent" or having more than 4 bonds.
3. SMILES PARSING: Parentheses ( ) denote branches on the same atom. E.g., C(Br)(Br) means two Bromines on the same Carbon.
4. NO GUESSING NAMES: Do not attempt IUPAC naming unless certain. Use descriptive terms like "tri-halogenated methane" or "tert-butyl scaffold".
5. ISOSTERES: Identify isosteric replacements correctly (e.g., swapping Br for Cl or F).
6. CONCISENESS: Keep the explanation to 2-3 precise technical sentences."""

# 3. User Prompt - تمرير البيانات الحقيقية
def build_user_prompt(query_smiles: str, match_smiles: str, similarity: float) -> str:
    """Combines SMILES with RDKit metadata for the LLM context."""
    q_meta = get_rdkit_metadata(query_smiles)
    m_meta = get_rdkit_metadata(match_smiles)
    
    return f"""Analyze the following compound pair:

Query: {query_smiles}
- Formula: {q_meta.get('formula', 'N/A')}
- Heavy Atoms: {q_meta.get('heavy_atoms', 'N/A')}

Match: {match_smiles}
- Formula: {m_meta.get('formula', 'N/A')}
- Heavy Atoms: {m_meta.get('heavy_atoms', 'N/A')}

Similarity Score: {similarity:.3f}

Task: Explain why these compounds are structurally similar. Focus on the core scaffold and atom substitutions. Reference the formulas to ensure accuracy."""

# 4. Generation Core - التواصل مع اللاما
def generate_explanation(
    query_smiles: str,
    compound_smiles: str,
    similarity_score: float
) -> Optional[str]:
    """Generates a fact-checked explanation using Llama-3.1 via HF Router."""
    try:
        api_key = os.environ.get("HF_TOKEN")
        if not api_key:
            return _generate_fallback_explanation(similarity_score)
        
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(query_smiles, compound_smiles, similarity_score)
        
        # HuggingFace Router API
        api_url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "model": "meta-llama/Llama-3.1-8B-Instruct:fastest",
            "temperature": 0.1,  # Low temperature for high factual precision
            "max_tokens": 100
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        explanation = result["choices"][0]["message"]["content"].strip()
        return explanation if len(explanation) > 10 else _generate_fallback_explanation(similarity_score)
            
    except Exception:
        return _generate_fallback_explanation(similarity_score)

def _generate_fallback_explanation(similarity_score: float) -> str:
    """Heuristic fallback in case of API failure."""
    if similarity_score >= 0.95:
        return "Extremely high structural similarity - compounds share an identical core scaffold with minimal substituent variation."
    return "Significant structural similarity based on shared molecular framework and functional group distribution."

# 5. Batch Processing - معالجة النتائج بالكامل
def generate_explanations_batch(query_smiles: str, search_results: List[Dict]) -> List[Dict]:
    """Adds an 'explanation' field to each search result."""
    for result in search_results:
        result["explanation"] = generate_explanation(
            query_smiles,
            result["smiles"],
            result["similarity_score"]
        )
    return search_results

# Example Usage:
if __name__ == "__main__":
    # Mock search results
    query = "C(Br)(Br)(Br)Br"
    results = [
        {"smiles": "C(Cl)(Cl)(Cl)Br", "similarity_score": 0.998},
        {"smiles": "CC(C)(C)Br", "similarity_score": 0.998}
    ]
    
    # You need to set your HF_TOKEN in environment variables
    # os.environ["HF_TOKEN"] = "your_token_here"
    
    updated_results = generate_explanations_batch(query, results)
    for res in updated_results:
        print(f"SMILES: {res['smiles']}\nScore: {res['similarity_score']}\nExplanation: {res['explanation']}\n{'-'*30}")