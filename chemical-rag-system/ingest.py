# """
# PubChem CID Batch Ingestion Script
# Fetches compounds from PubChem and saves them to JSON
# WITH CHEMICAL FILTERING for quality dataset
# """
# import pubchempy as pcp
# import json
# import os
# from rdkit import Chem


# def is_valid_organic_molecule(smiles: str) -> bool:
#     """
#     Filter to keep only valid, organic drug-like molecules.
    
#     Rules:
#     ✅ Keep: Molecules with ≥4 atoms AND containing Carbon
#     ❌ Skip: Single atoms (N, Br, Cl), ions, small fragments
    
#     Examples:
#     - ✅ CCO (Ethanol) → 3 atoms but has C and O → Actually should be ✅
#     - ✅ CCCO (Propanol) → 4 atoms, has C
#     - ✅ c1ccccc1 (Benzene) → 6 atoms, has C
#     - ❌ N (Nitrogen atom) → Single atom
#     - ❌ [NH4+] (Ammonium ion) → Ion
#     - ❌ Br (Bromine) → Single atom
#     """
#     try:
#         mol = Chem.MolFromSmiles(smiles)
        
#         if mol is None:
#             return False
        
#         # Rule 1: Must have at least 4 atoms (eliminates most noise)
#         num_atoms = mol.GetNumAtoms()
#         if num_atoms < 4:
#             return False
        
#         # Rule 2: Must contain Carbon (C or c)
#         has_carbon = any(atom.GetSymbol() in ['C'] for atom in mol.GetAtoms())
#         if not has_carbon:
#             return False
        
#         # Rule 3: Must be neutral (no charges)
#         total_charge = sum(atom.GetFormalCharge() for atom in mol.GetAtoms())
#         if total_charge != 0:
#             return False
        
#         return True
#     except Exception:
#         return False


# def fetch_compounds(start_id: int, count: int):
#     """
#     Fetch compounds from PubChem using CID range with chemical filtering.
#     """
#     print(f"🔄 Fetching up to {count} compounds starting from CID {start_id}...")
#     print(f"⚗️  Filtering: Must have ≥4 atoms AND contain Carbon AND be neutral")
    
#     cids = list(range(start_id, start_id + count))
#     compounds = pcp.get_compounds(cids, namespace='cid')

#     data = []
#     successful = 0
#     failed = 0
#     filtered_out = 0
    
#     for c in compounds:
#         try:
#             if c:
#                 # Use connectivity_smiles (preferred) or canonical_smiles (fallback)
#                 smiles = getattr(c, 'connectivity_smiles', None) or getattr(c, 'canonical_smiles', None)
                
#                 if smiles:
#                     # ⚗️ CHEMICAL FILTER APPLIED HERE
#                     if not is_valid_organic_molecule(smiles):
#                         filtered_out += 1
#                         continue
                    
#                     # ✅ Passed filter - add to dataset
#                     data.append({
#                         "smiles": smiles,
#                         "cid": c.cid,
#                         "name": c.iupac_name or f"Compound_{c.cid}",
#                         "mw": c.molecular_weight if hasattr(c, 'molecular_weight') else None
#                     })
#                     successful += 1
#         except Exception as e:
#             failed += 1
#             continue

#     print(f"✅ Successfully ingested {successful} compounds")
#     print(f"❌ Failed: {failed}")
#     print(f"⚗️  Filtered out (not valid): {filtered_out}")
#     print(f"📊 Final dataset: {len(data)} high-quality organic molecules")
    
#     return data


# def save_compounds(data, filepath="data/compounds.json"):
#     """Save compounds to JSON file."""
#     os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
#     with open(filepath, "w") as f:
#         json.dump(data, f, indent=2)
    
#     print(f"💾 Saved {len(data)} compounds to {filepath}")


# if __name__ == "__main__":
#     # Fetch first 20000 compounds from PubChem
#     # Due to filtering, final dataset will be smaller (typically 5k-10k valid molecules)
#     data = fetch_compounds(start_id=1, count=20000)
    
#     # Save to file
#     save_compounds(data)
    
#     print("✅ Ingestion pipeline completed!")


import pubchempy as pcp
import json
import os
import time
from rdkit import Chem

def is_valid_organic_molecule(smiles: str) -> bool:
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False
        
        num_atoms = mol.GetNumAtoms()
        if num_atoms < 4:
            return False
        
        has_carbon = any(atom.GetSymbol() in ['C'] for atom in mol.GetAtoms())
        if not has_carbon:
            return False
        
        total_charge = sum(atom.GetFormalCharge() for atom in mol.GetAtoms())
        if total_charge != 0:
            return False
        
        return True
    except Exception:
        return False

def fetch_compounds_batched(start_id: int, total_count: int, batch_size: int = 500):
    """
    جلب المركبات على دفعات صغيرة لتجنب الـ Timeout
    """
    print(f"🔄 Starting ingestion for {total_count} compounds in batches of {batch_size}...")
    
    all_data = []
    successful = 0
    failed = 0
    filtered_out = 0

    # تقسيم العدد الكلي إلى دفعات (مثلاً كل دفعة 500 مركب)
    for i in range(0, total_count, batch_size):
        current_start = start_id + i
        current_end = min(start_id + i + batch_size, start_id + total_count)
        cids = list(range(current_start, current_end))
        
        print(f"📡 Fetching CIDs {current_start} to {current_end-1}...")
        
        try:
            # طلب الدفعة الحالية
            compounds = pcp.get_compounds(cids, namespace='cid')
            
            for c in compounds:
                if c:
                    smiles = getattr(c, 'connectivity_smiles', None) or getattr(c, 'canonical_smiles', None)
                    if smiles:
                        if not is_valid_organic_molecule(smiles):
                            filtered_out += 1
                            continue
                        
                        all_data.append({
                            "smiles": smiles,
                            "cid": c.cid,
                            "name": c.iupac_name or f"Compound_{c.cid}",
                            "mw": c.molecular_weight if hasattr(c, 'molecular_weight') else None
                        })
                        successful += 1
            
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"⚠️ Error fetching batch starting at {current_start}: {e}")
            failed += len(cids)
            continue

    print(f"\n--- Final Report ---")
    print(f"✅ Successfully ingested: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"⚗️  Filtered out: {filtered_out}")
    return all_data

def save_compounds(data, filepath="data/compounds.json"):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved {len(data)} compounds to {filepath}")

if __name__ == "__main__":

    data = fetch_compounds_batched(start_id=1, total_count=50000, batch_size=2000)
    
    save_compounds(data)
    print("✅ Ingestion pipeline completed!")