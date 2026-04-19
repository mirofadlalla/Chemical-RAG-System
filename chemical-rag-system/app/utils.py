import os
from rdkit import Chem
from rdkit.Chem import Draw

STATIC_DIR = "app/static/images"
os.makedirs(STATIC_DIR, exist_ok=True)


def smiles_to_image_url(smiles: str, base_url: str = None):
    """Convert SMILES to image and return full URL.
    
    Args:
        smiles: SMILES string
        base_url: Base URL for the image (e.g. https://example.com). 
                 If None, uses BASE_URL env var or defaults to https://test.com
    
    Returns:
        Full image URL
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    filename = f"{abs(hash(smiles))}.png"
    filepath = os.path.join(STATIC_DIR, filename)

    if not os.path.exists(filepath):
        img = Draw.MolToImage(mol, size=(200, 200))
        img.save(filepath)

    # Use provided base_url, or fall back to env var or default
    if not base_url:
        base_url = os.environ.get("BASE_URL", "https://test.com")
    
    return f"{base_url}/static/images/{filename}"
