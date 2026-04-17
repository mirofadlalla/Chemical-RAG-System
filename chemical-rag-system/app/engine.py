from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import DataStructs
import numpy as np


class ChemicalSearchEngine:
    """
    Tanimoto-based Chemical Similarity Search Engine
    
    Uses RDKit's Tanimoto similarity for chemically accurate results.
    For small datasets (< 100k), pure RDKit Tanimoto is more accurate than FAISS L2.
    
    Reference: https://en.wikipedia.org/wiki/Jaccard_index
    Tanimoto(A,B) = |A ∩ B| / |A ∪ B|  (for binary fingerprints)
    """
    
    def __init__(self, bit_size=2048):
        self.bit_size = bit_size
        self.fingerprints = []  # Store ExplicitBitVect fingerprints
        self.metadata = []      # Store SMILES for results
        # Initialize MorganGenerator (modern RDKit API)
        # Note: Use fpSize parameter (not nBits) for GetMorganGenerator
        self.morgan_gen = AllChem.GetMorganGenerator(radius=2, fpSize=bit_size)
    
    def smiles_to_fingerprint(self, smiles):
        """
        Convert SMILES string to Morgan fingerprint (BitVect).
        
        Uses MorganGenerator (modern RDKit API) for proper Tanimoto calculation.
        Each fingerprint is a binary vector of size 2048.
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        # Generate Morgan fingerprint using MorganGenerator (Radius=2, 2048 bits)
        # Returns ExplicitBitVect (binary vector) for Tanimoto similarity
        try:
            fp = self.morgan_gen.GetFingerprintAsBitVect(mol)
        except:
            # Fallback for older RDKit versions
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=self.bit_size)
        return fp
    
    def add_compounds(self, smiles_list):
        """
        Add multiple compounds to the index.
        
        Stores fingerprints in memory. For 20k compounds, memory usage ~50MB.
        """
        for smiles in smiles_list:
            fp = self.smiles_to_fingerprint(smiles)
            if fp is not None:
                self.fingerprints.append(fp)
                self.metadata.append(smiles)
        
        print(f"📊 Index built: {len(self.fingerprints)} compounds")
    
    def search(self, query_smiles, k=3):
        """
        Search for similar compounds using Tanimoto Similarity.
        
        Returns:
            List of dicts with 'smiles' and 'similarity_score' (0-1, higher is better)
        """
        query_fp = self.smiles_to_fingerprint(query_smiles)
        if query_fp is None:
            return []
        
        if not self.fingerprints:
            return []
        
        # Use RDKit's optimized Tanimoto similarity calculation
        similarities = DataStructs.BulkTanimotoSimilarity(query_fp, self.fingerprints)
        
        # Get top k by similarity (highest first)
        # Note: similarity_score is between 0 and 1 (1 = perfect match)
        results = [
            {
                "smiles": self.metadata[i],
                "similarity_score": float(similarity),
                "index": i
            }
            for i, similarity in enumerate(similarities)
        ]
        
        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Return top k
        return results[:k]
