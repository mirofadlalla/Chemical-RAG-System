from rdkit import Chem
from rdkit.Chem import AllChem
import numpy as np
import faiss


class ChemicalSearchEngine:
    def __init__(self, bit_size=2048):
        self.bit_size = bit_size
        self.index = faiss.IndexFlatL2(bit_size)
        self.metadata = []
        self.morgan_gen = AllChem.GetMorganGenerator(radius=2, fpSize=bit_size)

    def smiles_to_vector(self, smiles):
        """Convert SMILES string to Morgan fingerprint vector."""
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        fp = self.morgan_gen.GetCountFingerprintAsNumPy(mol)
        return fp.astype('float32')

    def add_compounds(self, smiles_list):
        """Add multiple compounds to the index."""
        vectors = []
        for s in smiles_list:
            v = self.smiles_to_vector(s)
            if v is not None:
                vectors.append(v)
                self.metadata.append(s)

        if vectors:
            self.index.add(np.array(vectors))

    def search(self, query_smiles, k=3):
        """Search for similar compounds."""
        v = self.smiles_to_vector(query_smiles)
        if v is None:
            return []

        distances, indices = self.index.search(np.array([v]), k)

        return [
            {
                "smiles": self.metadata[idx],
                "distance": float(distances[0][i])
            }
            for i, idx in enumerate(indices[0]) if idx != -1
        ]
