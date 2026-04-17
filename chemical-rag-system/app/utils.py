import os
from rdkit import Chem
from rdkit.Chem import Draw

STATIC_DIR = "app/static/images"
os.makedirs(STATIC_DIR, exist_ok=True)


def smiles_to_image_url(smiles: str):
    """Convert SMILES to image and return URL."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    filename = f"{abs(hash(smiles))}.png"
    filepath = os.path.join(STATIC_DIR, filename)

    if not os.path.exists(filepath):
        img = Draw.MolToImage(mol, size=(200, 200))
        img.save(filepath)

    return f"/static/images/{filename}"
