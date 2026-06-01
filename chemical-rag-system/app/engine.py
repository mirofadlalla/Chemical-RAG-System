"""
Hybrid Enterprise Chemical Search Engine 
Includes: FAISS Retrieval, Multi-Fingerprint Fusion, Chemical-Aware Reranking, 
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
    Advanced Hybrid Chemical Similarity Search Engine (Drug-Discovery Grade).
    
    Pipeline Steps:
    1. FAISS Binary Retrieval: Rapid screen over Morgan fingerprints (Top 200).
    2. Multi-Fingerprint Fusion: Combines Morgan, MACCS, Atom Pairs, and Torsion.
    3. Chemical-Aware Reranking: Applies strict domain constraints (Aromaticity, Rings, Charge, Fragments).
    4. Similarity Calibration: Z-score normalization to probabilities.
    5. Diversity Control (MMR): Maximizes scaffold diversity.
    """

    def __init__(self, bit_size=2048):
        self.bit_size = bit_size
        self.index = None
        self.index_built = False
        self.total_compounds = 0
        
        self.metadata = []
        self.morgan_fps = []          
        self.maccs_fps = []           
        self.atom_pair_fps = []       
        self.torsion_fps = []         
        self.faiss_fingerprints = []  

    def _mol_to_all_fingerprints(self, mol):
        """Generates all 4 distinct tactical chemical fingerprints."""
        if mol is None:
            return None, None, None, None
        try:
            morgan = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=self.bit_size)
            maccs = MACCSkeys.GenMACCSKeys(mol)
            atom_pairs = rdMolDescriptors.GetHashedAtomPairFingerprintAsBitVect(mol, nBits=self.bit_size)
            torsions = rdMolDescriptors.GetHashedTopologicalTorsionFingerprintAsBitVect(mol, nBits=self.bit_size)
            return morgan, maccs, atom_pairs, torsions
        except Exception:
            return None, None, None, None

    def _extract_chemical_features(self, mol):
        """
        Extracts structural semantics for the Chemical-Aware Reranking Layer.
        Pre-computed during ingestion for zero overhead during search.
        """
        if mol is None:
            return 0, 0, 0, 1
        try:
            arom = sum(1 for atom in mol.GetAtoms() if atom.GetIsAromatic())
            rings = mol.GetRingInfo().NumRings()
            charge = sum(atom.GetFormalCharge() for atom in mol.GetAtoms())
            frags = len(Chem.GetMolFrags(mol))
            return arom, rings, charge, frags
        except Exception:
            return 0, 0, 0, 1

    def _bitvect_to_numpy(self, bv):
        """Converts an RDKit bit vector to a NumPy uint8 array."""
        arr = np.zeros((len(bv),), dtype=np.uint8)
        DataStructs.ConvertToNumpyArray(bv, arr)
        return arr

    def add_compounds(self, smiles_list, metadata_list=None):
        """Processes compounds, pre-computes chemical semantics, and builds engine."""
        print(f"[START] Processing {len(smiles_list)} compounds for Hybrid Engine...")
        
        for i, smiles in enumerate(smiles_list):
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                continue
                
            morgan, maccs, atom_pairs, torsions = self._mol_to_all_fingerprints(mol)
            if morgan is None:
                continue
                
            # Extract and cache chemical features (Aromaticity, Rings, Charge, Fragments)
            arom, rings, charge, frags = self._extract_chemical_features(mol)
                
            meta = metadata_list[i] if metadata_list else {"smiles": smiles}
            meta["smiles"] = smiles
            # Cache semantic features directly in metadata
            meta["chem_features"] = {"arom": arom, "rings": rings, "charge": charge, "frags": frags}
            self.metadata.append(meta)
            
            self.morgan_fps.append(morgan)
            self.maccs_fps.append(maccs)
            self.atom_pair_fps.append(atom_pairs)
            self.torsion_fps.append(torsions)
            self.faiss_fingerprints.append(self._bitvect_to_numpy(morgan))

        self.total_compounds = len(self.metadata)
        print(f"[SUCCESS] Feature extraction complete: {self.total_compounds} compounds")
        self._build_faiss_index()

    def _build_faiss_index(self):
        """Builds FAISS index with proper byte packing."""
        if len(self.faiss_fingerprints) == 0:
            return

        self.index = faiss.IndexBinaryFlat(self.bit_size)
        np_fps = np.array(self.faiss_fingerprints, dtype=np.uint8)
        packed_fps = np.packbits(np_fps, axis=1)
        
        self.index.add(packed_fps)
        self.index_built = True
        print(f"[SUCCESS] FAISS Binary index successfully built.")

    def search(self, query_smiles, k=3, lambda_param=0.6):
        """Executes the complete Drug-Discovery Grade Search Pipeline."""
        query_mol = Chem.MolFromSmiles(query_smiles)
        if query_mol is None or not self.index_built:
            return []

        # 1. Query fingerprints & Semantic features
        q_morgan, q_maccs, q_atom_pairs, q_torsions = self._mol_to_all_fingerprints(query_mol)
        q_arom, q_rings, q_charge, q_frags = self._extract_chemical_features(query_mol)
        
        if q_morgan is None:
            return []

        # 2. FAISS Fast Retrieval
        k_search = min(max(k * 20, 200), self.total_compounds)
        q_packed = np.packbits(self._bitvect_to_numpy(q_morgan).reshape(1, -1), axis=1)
        _, indices = self.index.search(q_packed, k_search)
        candidate_indices = [int(idx) for idx in indices[0] if idx >= 0]

        if not candidate_indices:
            return []

        # 3. Multi-FP & Chemical-Aware Scoring
        candidate_pool = []
        for idx in candidate_indices:
            # 3a. Multi-Fingerprint Fusion (Base Structural Score)
            score_morgan = DataStructs.FingerprintSimilarity(q_morgan, self.morgan_fps[idx])
            score_maccs = DataStructs.FingerprintSimilarity(q_maccs, self.maccs_fps[idx])
            score_atom_pairs = DataStructs.FingerprintSimilarity(q_atom_pairs, self.atom_pair_fps[idx])
            score_torsions = DataStructs.FingerprintSimilarity(q_torsions, self.torsion_fps[idx])
            
            base_score = (0.50 * score_morgan + 0.20 * score_maccs + 
                          0.20 * score_atom_pairs + 0.10 * score_torsions)

            # 3b. Chemical-Aware Penalties & Bonuses (O(1) lookup, ultra-fast)
            c_feats = self.metadata[idx]["chem_features"]
            c_arom, c_rings, c_charge, c_frags = c_feats["arom"], c_feats["rings"], c_feats["charge"], c_feats["frags"]

            # Aromaticity Bonus
            max_arom = max(q_arom, c_arom)
            arom_score = 1.0 if max_arom == 0 else 1.0 - (abs(q_arom - c_arom) / max_arom)

            # Ring System Bonus
            max_rings = max(q_rings, c_rings)
            ring_score = 1.0 if max_rings == 0 else 1.0 - (abs(q_rings - c_rings) / max_rings)

            # Strict Domain Penalties
            charge_pen = min(abs(c_charge) / 3.0, 1.0)
            frag_pen = 0.0 if c_frags <= 1 else min((c_frags - 1) * 0.3, 1.0)

            # 3c. Final Hybrid Score
            chem_aware_score = (
                0.70 * base_score +
                0.15 * arom_score +
                0.10 * ring_score -
                0.15 * charge_pen -
                0.10 * frag_pen
            )
            
            candidate_pool.append({
                "index": idx,
                "smiles": self.metadata[idx]["smiles"],
                "metadata": self.metadata[idx],
                "chem_aware_score": chem_aware_score,
                "base_structural_score": base_score
            })

        # 4. Calibration Layer (Z-Score)
        scores = [c["chem_aware_score"] for c in candidate_pool]
        mean_score = np.mean(scores)
        std_score = np.std(scores) if np.std(scores) > 0 else 1.0
        
        for c in candidate_pool:
            z = (c["chem_aware_score"] - mean_score) / std_score
            c["calibrated_score"] = 1.0 / (1.0 + np.exp(-z))

        # 5. Diversity Control (MMR)
        selected_results = []
        remaining_candidates = list(candidate_pool)
        
        remaining_candidates.sort(key=lambda x: x["calibrated_score"], reverse=True)
        selected_results.append(remaining_candidates.pop(0))
        
        while len(selected_results) < k and remaining_candidates:
            best_mmr = -float('inf')
            best_idx = -1
            
            for idx, cand in enumerate(remaining_candidates):
                max_sim = -float('inf')
                cand_fp = self.morgan_fps[cand["index"]]
                
                for sel in selected_results:
                    sim = DataStructs.FingerprintSimilarity(cand_fp, self.morgan_fps[sel["index"]])
                    if sim > max_sim: max_sim = sim
                
                mmr_val = (lambda_param * cand["calibrated_score"]) - ((1.0 - lambda_param) * max_sim)
                if mmr_val > best_mmr:
                    best_mmr = mmr_val
                    best_idx = idx
            
            if best_idx != -1:
                selected_results.append(remaining_candidates.pop(best_idx))
            else:
                break

        # Output formatting
        return [{
            "smiles": res["smiles"],
            "similarity_score": round(float(res["chem_aware_score"]), 4), 
            "calibrated_score": round(float(res["calibrated_score"]), 4),
            "metadata": res["metadata"],
            "index": res["index"]
        } for res in selected_results]

    def save_index(self, filepath):
        """Serializes the multi-fingerprint infrastructure and metadata safely."""
        if not self.index_built:
            return
        try:
            faiss_file = filepath.replace(".pkl", ".faiss")
            faiss.write_index_binary(self.index, faiss_file)
            
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
            print(f"[SAVE] Engine saved at: {filepath}")
        except Exception as e:
            print(f"[ERROR] Serialization failed: {e}")

    def load_index(self, filepath):
        """Loads and provisions the full hybrid matrix and FAISS architecture."""
        if not os.path.exists(filepath):
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
            
            faiss_file = filepath.replace(".pkl", ".faiss")
            self.index = faiss.read_index_binary(faiss_file)
            self.index_built = True
            
            print(f"[LOAD] Engine loaded completely: {self.total_compounds} compounds.")
            return True
        except Exception as e:
            print(f"[ERROR] Loading error: {e}")
            return False