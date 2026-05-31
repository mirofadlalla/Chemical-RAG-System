"""
Hybrid Enterprise Chemical Search Engine with Multi-Fingerprint Reranking, 
Z-Score Calibration, and MMR Diversity Control.
============================================================================
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
import pickle
import numpy as np
import faiss

from rdkit import Chem
from rdkit.Chem import AllChem, MACCSkeys, rdMolDescriptors
from rdkit import DataStructs


class ChemicalSearchEngine:
    """
    Advanced Hybrid Chemical Similarity Search Engine.
    
    Pipeline Steps:
    1. FAISS Binary Retrieval: Rapid screen over Morgan fingerprints (Retrieves top 200).
    2. Multi-Fingerprint Reranking: Computes exact Tanimoto across Morgan, MACCS, 
       Atom Pairs, and Topological Torsion.
    3. Similarity Calibration: Applies Z-score normalization followed by logistic 
       sigmoid mapping.
    4. Diversity Control (MMR): Maximizes chemical space diversity to eliminate redundancy.
    """

    def __init__(self, bit_size=2048):
        self.bit_size = bit_size
        self.index = None
        self.index_built = False
        self.total_compounds = 0
        
        # Data storage for Reranking and Diversity Layers
        self.metadata = []
        self.morgan_fps = []          # RDKit ExplicitBitVect objects for fast exact Tanimoto
        self.maccs_fps = []           # RDKit ExplicitBitVect objects
        self.atom_pair_fps = []       # RDKit ExplicitBitVect objects
        self.torsion_fps = []         # RDKit ExplicitBitVect objects
        self.faiss_fingerprints = []  # Unpacked uint8 matrix for FAISS construction

    def _mol_to_all_fingerprints(self, mol):
        """Generates all 4 distinct tactical chemical fingerprints."""
        if mol is None:
            return None, None, None, None
        try:
            # 1. Morgan Fingerprint (Circular/Structural topology)
            morgan = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=self.bit_size)
            # 2. MACCS Keys (Functional groups / Substructure keys)
            maccs = MACCSkeys.GenMACCSKeys(mol)
            # 3. Atom Pairs (Long-range geometric atom relations)
            atom_pairs = rdMolDescriptors.GetHashedAtomPairFingerprintAsBitVect(mol, nBits=self.bit_size)
            # 4. Topological Torsions (4-atom path sequences)
            torsions = rdMolDescriptors.GetHashedTopologicalTorsionFingerprintAsBitVect(mol, nBits=self.bit_size)
            
            return morgan, maccs, atom_pairs, torsions
        except Exception:
            return None, None, None, None

    def _bitvect_to_numpy(self, bv):
        """Converts an RDKit bit vector to a NumPy uint8 array."""
        arr = np.zeros((len(bv),), dtype=np.uint8)
        DataStructs.ConvertToNumpyArray(bv, arr)
        return arr

    def add_compounds(self, smiles_list, metadata_list=None):
        """Processes and registers chemical compounds into the engine data matrix."""
        print(f"[START] Processing {len(smiles_list)} compounds for Hybrid Engine...")
        
        for i, smiles in enumerate(smiles_list):
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                continue
                
            morgan, maccs, atom_pairs, torsions = self._mol_to_all_fingerprints(mol)
            if morgan is None:
                continue
                
            # Store structural metadata
            meta = metadata_list[i] if metadata_list else {"smiles": smiles}
            meta["smiles"] = smiles
            self.metadata.append(meta)
            
            # Store RDKit fingerprints for the ultra-fast C++ calculation layer
            self.morgan_fps.append(morgan)
            self.maccs_fps.append(maccs)
            self.atom_pair_fps.append(atom_pairs)
            self.torsion_fps.append(torsions)
            
            # Extract unpacked binary vector for FAISS compatibility
            self.faiss_fingerprints.append(self._bitvect_to_numpy(morgan))

        self.total_compounds = len(self.metadata)
        print(f"[SUCCESS] Fingerprints generated: {self.total_compounds} compounds")
        self._build_faiss_index()

    def _build_faiss_index(self):
        """Builds a FAISS binary flat index safely incorporating packed byte logic."""
        if len(self.faiss_fingerprints) == 0:
            print("[ERROR] No fingerprints available to index.")
            return

        print("[INDEX] Initializing FAISS IndexBinaryFlat...")
        self.index = faiss.IndexBinaryFlat(self.bit_size)
        
        # Pack bits (N, 2048) -> (N, 256) to adhere to FAISS requirements
        np_fps = np.array(self.faiss_fingerprints, dtype=np.uint8)
        packed_fps = np.packbits(np_fps, axis=1)
        
        self.index.add(packed_fps)
        self.index_built = True
        print(f"[SUCCESS] FAISS Binary index successfully built: {self.total_compounds} compounds")

    def search(self, query_smiles, k=3, lambda_param=0.6):
        """
        Executes the fully advanced Hybrid Search Pipeline.
        
        Args:
            query_smiles (str): Target SMILES structure query.
            k (int): Desired final size of diverse results.
            lambda_param (float): MMR balance parameter (1.0 = Relevance only, 0.0 = Diversity only).
        """
        query_mol = Chem.MolFromSmiles(query_smiles)
        if query_mol is None or not self.index_built:
            return []

        # Generate query fingerprints
        q_morgan, q_maccs, q_atom_pairs, q_torsions = self._mol_to_all_fingerprints(query_mol)
        if q_morgan is None:
            return []

        # ---------------------------------------------------------------------
        # STEP 1: FAISS High-Speed Retrieval (Wide Net Generation)
        # ---------------------------------------------------------------------
        # Dynamic Candidate Generation Pool (Targeting Top 200 candidates)
        k_search = min(max(k * 20, 200), self.total_compounds)
        if k_search <= 0:
            return []

        q_numpy = self._bitvect_to_numpy(q_morgan).reshape(1, -1)
        q_packed = np.packbits(q_numpy, axis=1)
        
        _, indices = self.index.search(q_packed, k_search)
        candidate_indices = [int(idx) for idx in indices[0] if idx >= 0]

        if not candidate_indices:
            return []

        # ---------------------------------------------------------------------
        # STEP 2: Multi-Fingerprint Reranking Layer
        # ---------------------------------------------------------------------
        candidate_pool = []
        for idx in candidate_indices:
            # Multi-FP Exact Tanimoto calculation using fast C++ bindings
            score_morgan = DataStructs.FingerprintSimilarity(q_morgan, self.morgan_fps[idx])
            score_maccs = DataStructs.FingerprintSimilarity(q_maccs, self.maccs_fps[idx])
            score_atom_pairs = DataStructs.FingerprintSimilarity(q_atom_pairs, self.atom_pair_fps[idx])
            score_torsions = DataStructs.FingerprintSimilarity(q_torsions, self.torsion_fps[idx])
            
            # Enterprise Weighted Score Fusion
            hybrid_score = (
                0.50 * score_morgan +
                0.20 * score_maccs +
                0.20 * score_atom_pairs +
                0.10 * score_torsions
            )
            
            candidate_pool.append({
                "index": idx,
                "smiles": self.metadata[idx]["smiles"],
                "metadata": self.metadata[idx],
                "hybrid_score": hybrid_score,
                "individual_scores": {
                    "morgan": score_morgan,
                    "maccs": score_maccs,
                    "atom_pair": score_atom_pairs,
                    "torsion": score_torsions
                }
            })

        # ---------------------------------------------------------------------
        # STEP 3: Similarity Calibration Layer (Z-Score + Sigmoid Transformation)
        # ---------------------------------------------------------------------
        hybrid_scores = [c["hybrid_score"] for c in candidate_pool]
        mean_score = np.mean(hybrid_scores)
        std_score = np.std(hybrid_scores) if np.std(hybrid_scores) > 0 else 1.0
        
        for c in candidate_pool:
            # Compute statistical Z-Score
            z = (c["hybrid_score"] - mean_score) / std_score
            # Map through a Logistic Sigmoid to yield a probability-like distribution [0.0, 1.0]
            c["calibrated_score"] = 1.0 / (1.0 + np.exp(-z))

        # ---------------------------------------------------------------------
        # STEP 4: Diversity Control Layer (Maximal Marginal Relevance)
        # ---------------------------------------------------------------------
        selected_results = []
        remaining_candidates = list(candidate_pool)
        
        # Always pick the absolute highest relevance match first
        remaining_candidates.sort(key=lambda x: x["calibrated_score"], reverse=True)
        first_pick = remaining_candidates.pop(0)
        selected_results.append(first_pick)
        
        while len(selected_results) < k and remaining_candidates:
            best_mmr_value = -float('inf')
            best_cand_idx = -1
            
            for idx, cand in enumerate(remaining_candidates):
                # Measure highest structural overlap with already selected items to penalize redundancy
                max_similarity_to_selected = -float('inf')
                cand_fp = self.morgan_fps[cand["index"]]
                
                for sel in selected_results:
                    sel_fp = self.morgan_fps[sel["index"]]
                    sim = DataStructs.FingerprintSimilarity(cand_fp, sel_fp)
                    if sim > max_similarity_to_selected:
                        max_similarity_to_selected = sim
                
                # Execution of the mathematical MMR Optimization Function
                relevance = cand["calibrated_score"]
                diversity = max_similarity_to_selected
                mmr_val = (lambda_param * relevance) - ((1.0 - lambda_param) * diversity)
                
                if mmr_val > best_mmr_value:
                    best_mmr_value = mmr_val
                    best_cand_idx = idx
            
            if best_cand_idx != -1:
                selected_results.append(remaining_candidates.pop(best_cand_idx))
            else:
                break

        # Final Formatting mapping for API compatibility
        final_output = []
        for res in selected_results:
            final_output.append({
                "smiles": res["smiles"],
                "similarity_score": round(float(res["hybrid_score"]), 4),  # Standardized Tanimoto presentation
                "calibrated_score": round(float(res["calibrated_score"]), 4),
                "metadata": res["metadata"],
                "index": res["index"],
                "individual_scores": res["individual_scores"]
            })
            
        return final_output[:k]

    def save_index(self, filepath):
        """Serializes the multi-fingerprint infrastructure and saves the index safely."""
        if not self.index_built:
            print("[ERROR] Index is unbuilt. Aborting save.")
            return
            
        try:
            # Separate save for FAISS binary asset
            faiss_file = filepath.replace(".pkl", ".faiss")
            faiss.write_index_binary(self.index, faiss_file)
            
            # Serialize chemical matrix
            data = {
                "metadata": self.metadata,
                "morgan_fps": self.morgan_fps,
                "maccs_fps": self.maccs_fps,
                "atom_pair_fps": self.atom_pair_fps,
                "torsion_fps": self.torsion_fps,
                "faiss_fingerprints": self.faiss_fingerprints,
                "bit_size": self.bit_size,
                "total_compounds": self.total_compounds
            }
            with open(filepath, "wb") as f:
                pickle.dump(data, f)
            print(f"[SUCCESS] Full Hybrid Engine database saved at: {filepath}")
        except Exception as e:
            print(f"[ERROR] Serialization failed: {e}")

    def load_index(self, filepath):
        """Loads and provisions the full hybrid matrix and FAISS architecture."""
        if not os.path.exists(filepath):
            print(f"[ERROR] Asset path not found: {filepath}")
            return False
            
        try:
            with open(filepath, "rb") as f:
                data = pickle.load(f)
                
            self.metadata = data["metadata"]
            self.morgan_fps = data["morgan_fps"]
            self.maccs_fps = data["maccs_fps"]
            self.atom_pair_fps = data["atom_pair_fps"]
            self.torsion_fps = data["torsion_fps"]
            self.faiss_fingerprints = data["faiss_fingerprints"]
            self.bit_size = data.get("bit_size", 2048)
            self.total_compounds = data.get("total_compounds", len(self.metadata))
            
            # Read compiled FAISS binary index
            faiss_file = filepath.replace(".pkl", ".faiss")
            self.index = faiss.read_index_binary(faiss_file)
            self.index_built = True
            
            print(f"[SUCCESS] Hybrid Engine loaded completely: {self.total_compounds} compounds running.")
            return True
        except Exception as e:
            print(f"[ERROR] Infrastructure loading error: {e}")
            return False