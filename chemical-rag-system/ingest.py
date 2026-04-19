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

def fetch_compounds_batched(start_id: int, total_count: int, batch_size: int = 250, max_retries: int = 3):
    """
    Fetch compounds in small batches with retry logic to avoid API timeouts.
    
    Reduced batch size (250) and progressive delays for reliability.
    Saves progress incrementally to avoid losing data on failure.
    """
    print(f"🔄 Starting ingestion for {total_count} compounds in batches of {batch_size}...")
    print(f"⚠️  Note: Smaller batches (250) for better reliability with PubChem API\n")
    
    all_data = []
    successful = 0
    failed = 0
    filtered_out = 0
    skipped = 0

    for i in range(0, total_count, batch_size):
        current_start = start_id + i
        current_end = min(start_id + i + batch_size, start_id + total_count)
        cids = list(range(current_start, current_end))
        batch_num = (i // batch_size) + 1
        total_batches = (total_count + batch_size - 1) // batch_size
        
        print(f"[{batch_num}/{total_batches}] 📡 Fetching CIDs {current_start} to {current_end-1}...")
        
        # Retry logic for failed batches
        retry_count = 0
        batch_success = False
        
        while retry_count < max_retries and not batch_success:
            try:
                # Fetch batch with timeout handling
                compounds = pcp.get_compounds(cids, namespace='cid')
                
                batch_successful = 0
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
                            batch_successful += 1
                    else:
                        skipped += 1
                
                print(f"    ✅ Batch complete: {batch_successful} valid compounds added")
                batch_success = True
                
                # Progressive delay: 0.5s for first batch, 1s for later batches
                delay = 0.5 + (batch_num * 0.1)  # Increases delay for later batches
                time.sleep(min(delay, 2.0))  # Cap at 2 seconds
                
            except (json.JSONDecodeError, ConnectionError, TimeoutError, Exception) as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff: 2s, 4s, 8s
                    print(f"    ⚠️  Attempt {retry_count} failed: {type(e).__name__}")
                    print(f"    ⏳ Retrying in {wait_time}s... (attempt {retry_count+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"    ❌ Batch failed after {max_retries} retries: {type(e).__name__}")
                    failed += len(cids)
                    batch_success = True  # Exit retry loop

    print(f"\n{'='*60}")
    print(f"✅ Successfully ingested: {successful}")
    print(f"❌ Failed compounds: {failed}")
    print(f"⚗️  Filtered out (invalid): {filtered_out}")
    print(f"⏭️  Skipped/Missing: {skipped}")
    print(f"📊 Total valid compounds: {len(all_data)}")
    print(f"{'='*60}\n")
    
    return all_data

def save_compounds(data, filepath="data/compounds.json"):
    """Save compounds to JSON file with pretty formatting."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved {len(data)} compounds to {filepath}")


if __name__ == "__main__":
    # Fetch 50,000 compounds with reliable batching
    # Using batch_size=250 (down from 2000) to avoid PubChem API timeouts
    # With retries and exponential backoff for failed batches
    data = fetch_compounds_batched(
        start_id=1, 
        total_count=50000, 
        batch_size=500,  # Reduced from 2000 for better reliability
        max_retries=3    # Retry failed batches up to 3 times
    )
    
    # Only save if we have data
    if data:
        save_compounds(data)
        print("✅ Ingestion pipeline completed!")
    else:
        print("❌ No compounds ingested. Please check your internet connection and try again.")