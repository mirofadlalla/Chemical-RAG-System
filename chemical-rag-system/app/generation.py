"""
LLM-based Generation Layer for Chemical Similarity Explanation
Uses HuggingFace Llama-3.1-8B with few-shot instruction tuning
"""

import os
from typing import Optional
from huggingface_hub import InferenceClient


# Few-shot examples for instruction tuning
FEW_SHOT_EXAMPLES = [
    {
        "query": "CCO",  # Ethanol
        "compound": "CC(C)O",  # Isopropanol
        "similarity": 0.89,
        "explanation": "Both are simple primary alcohols with similar hydroxyl functional groups. Both contain 2-3 carbons and show high structural similarity in their C-O backbone and hydrogen bonding patterns."
    },
    {
        "query": "c1ccccc1",  # Benzene
        "compound": "c1ccccc1C(=O)O",  # Benzoic acid
        "similarity": 0.92,
        "explanation": "Both contain the benzene ring (aromatic core) as the main structural feature. The compound adds a carboxylic acid group to benzene, maintaining the core aromatic structure with additional polar functionality."
    },
    {
        "query": "CC(=O)O",  # Acetic acid
        "compound": "CC(=O)Nc1ccc(O)cc1",  # Acetaminophen
        "similarity": 0.76,
        "explanation": "Both share the acetyl group (CC(=O)-) which is a common functional motif. The similarity is moderate because the compound has a much larger aromatic system, but they share the same carbonyl-carbon backbone feature."
    },
    {
        "query": "C1CCCCC1",  # Cyclohexane  
        "compound": "C1CCCCC1O",  # Cyclohexanol
        "similarity": 0.88,
        "explanation": "Both contain the six-membered saturated ring (cyclohexane core). The compound adds a hydroxyl group, making it more polar, but the underlying ring structure is nearly identical, resulting in high structural similarity."
    },
    {
        "query": "CCN(CC)CC",  # Triethylamine
        "compound": "CCN(CC)CCOC",  # N,N-diethylethanolamine derivative
        "similarity": 0.82,
        "explanation": "Both molecules contain the diethylamino group (CCN(CC)-) which appears in the same position. The main structural difference is that the compound has an additional ether linkage, but the core amine feature ensures high similarity."
    }
]


def build_system_prompt() -> str:
    """Build the system prompt for the LLM with instruction tuning."""
    return """You are a chemistry expert assistant that explains why two chemical compounds are similar.

Your task is to analyze the structural similarity between two compounds and provide a clear, concise explanation focusing on:
1. Shared functional groups (e.g., hydroxyl, carboxyl, amine, aromatic rings)
2. Similar structural motifs (e.g., carbon chains, rings, double bonds)
3. Chemical properties affected by the similarity (e.g., polarity, reactivity)
4. Molecular complexity differences if significant

Keep explanations brief (2-3 sentences), scientific but accessible, and focus on the most important shared features."""


def build_few_shot_context() -> str:
    """Build few-shot examples for the prompt."""
    context = "Here are some examples of compound similarity explanations:\n\n"
    
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        context += f"Example {i}:\n"
        context += f"Query: {example['query']}\n"
        context += f"Similar Compound: {example['compound']}\n"
        context += f"Similarity Score: {example['similarity']:.2f}\n"
        context += f"Explanation: {example['explanation']}\n\n"
    
    return context


def build_user_prompt(query_smiles: str, compound_smiles: str, similarity_score: float) -> str:
    """Build the user prompt for a specific query-compound pair."""
    return f"""Query Compound SMILES: {query_smiles}
Similar Compound SMILES: {compound_smiles}
Tanimoto Similarity Score: {similarity_score:.3f}

Please explain why these compounds are similar and what structural features they share. 
Keep it concise (2-3 sentences) and focus on chemical relevance."""


def generate_explanation(
    query_smiles: str,
    compound_smiles: str,
    similarity_score: float,
    max_retries: int = 2
) -> Optional[str]:
    """
    Generate an LLM-based explanation for compound similarity.
    
    Args:
        query_smiles: SMILES of the query compound
        compound_smiles: SMILES of the similar compound found
        similarity_score: Tanimoto similarity score (0-1)
        max_retries: Maximum number of API retries
    
    Returns:
        Explanation string or None if generation fails
    """
    try:
        # Initialize HF client
        api_key = os.environ.get("HF_TOKEN")
        if not api_key:
            # Fallback to a simple heuristic explanation if token not set
            return _generate_fallback_explanation(similarity_score)
        
        client = InferenceClient(
            provider="auto",
            api_key=api_key,
        )
        
        # Build the complete prompt with few-shot examples
        system_prompt = build_system_prompt()
        few_shot_context = build_few_shot_context()
        user_prompt = build_user_prompt(query_smiles, compound_smiles, similarity_score)
        
        full_prompt = f"{system_prompt}\n\n{few_shot_context}\nNow, analyze this pair:\n{user_prompt}"
        
        # Generate explanation using Llama-3.1-8B
        result = client.text_generation(
            full_prompt,
            model="meta-llama/Llama-3.1-8B-Instruct:latest",
            max_new_tokens=150,
            temperature=0.7,
        )
        
        explanation = result.strip() if result else None
        
        # Validate the explanation is not too short
        if explanation and len(explanation) > 20:
            return explanation
        else:
            return _generate_fallback_explanation(similarity_score)
            
    except Exception as e:
        print(f"⚠️ LLM generation failed: {e}. Using fallback explanation.")
        return _generate_fallback_explanation(similarity_score)


def _generate_fallback_explanation(similarity_score: float) -> str:
    """
    Fallback heuristic explanation when LLM is unavailable.
    
    Args:
        similarity_score: Tanimoto similarity score (0-1)
    
    Returns:
        Heuristic explanation based on similarity score
    """
    if similarity_score >= 0.95:
        return "Extremely high structural similarity - compounds likely differ only in minor substituents or stereochemistry."
    elif similarity_score >= 0.85:
        return "Very high structural similarity - compounds share the same core structure with similar functional groups."
    elif similarity_score >= 0.70:
        return "Strong structural similarity - compounds contain similar aromatic rings or carbon scaffolds with analogous functional groups."
    elif similarity_score >= 0.50:
        return "Moderate structural similarity - compounds share some common functional groups or molecular features but differ in overall architecture."
    else:
        return "Lower similarity - compounds have some shared molecular features but differ significantly in structure and composition."


def generate_explanations_batch(
    query_smiles: str,
    search_results: list
) -> list:
    """
    Generate explanations for multiple search results.
    
    Args:
        query_smiles: SMILES of the query compound
        search_results: List of search result dicts with 'smiles' and 'similarity_score'
    
    Returns:
        Same search_results list with 'explanation' field added to each result
    """
    for result in search_results:
        explanation = generate_explanation(
            query_smiles,
            result["smiles"],
            result["similarity_score"]
        )
        result["explanation"] = explanation
    
    return search_results
