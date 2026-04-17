"""
PubChem CID Batch Ingestion Script
Fetches compounds from PubChem and saves them to JSON
"""
import pubchempy as pcp
import json
import os


def fetch_compounds(start_id: int, count: int):
    """Fetch compounds from PubChem using CID range."""
    print(f"🔄 Fetching {count} compounds starting from CID {start_id}...")
    
    cids = list(range(start_id, start_id + count))
    compounds = pcp.get_compounds(cids, namespace='cid')

    data = []
    successful = 0
    failed = 0
    
    for c in compounds:
        try:
            if c:
                # Use connectivity_smiles (preferred) or canonical_smiles (fallback)
                smiles = getattr(c, 'connectivity_smiles', None) or getattr(c, 'canonical_smiles', None)
                if smiles:
                    data.append({
                        "smiles": smiles,
                        "cid": c.cid,
                        "name": c.iupac_name or f"Compound_{c.cid}",
                        "mw": c.molecular_weight if hasattr(c, 'molecular_weight') else None
                    })
                    successful += 1
        except Exception as e:
            failed += 1
            continue

    print(f"✅ Successfully ingested {successful} compounds (Failed: {failed})")
    return data


def save_compounds(data, filepath="data/compounds.json"):
    """Save compounds to JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"💾 Saved {len(data)} compounds to {filepath}")


if __name__ == "__main__":
    # Fetch first 20000 compounds from PubChem
    data = fetch_compounds(start_id=1, count=20000)
    
    # Save to file
    save_compounds(data)
    
    print("✅ Ingestion pipeline completed!")
