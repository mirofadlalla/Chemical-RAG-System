# # from rdkit import Chem
# # from rdkit.Chem import AllChem
# # from rdkit import DataStructs

# # mol1 = Chem.MolFromSmiles("c1ccccc1")
# # mol2 = Chem.MolFromSmiles("c1ccncc1")

# # fp1 = AllChem.GetMorganFingerprintAsBitVect(mol1, 2, nBits=2048)
# # fp2 = AllChem.GetMorganFingerprintAsBitVect(mol2, 2, nBits=2048)

# # print(DataStructs.TanimotoSimilarity(fp1, fp2))

# # from rdkit import Chem
# # from rdkit.Chem import MACCSkeys, DataStructs

# # mol1 = Chem.MolFromSmiles("c1ccccc1")
# # mol2 = Chem.MolFromSmiles("c1ccncc1")

# # fp1 = MACCSkeys.GenMACCSKeys(mol1)
# # fp2 = MACCSkeys.GenMACCSKeys(mol2)

# # print("MACCS:", DataStructs.TanimotoSimilarity(fp1, fp2))

# # (.venv) PS C:\Users\omary\Desktop\CS_1\chemical-rag-system> & c:/Users/omary/Desktop/CS_1/.venv/Scripts/python.exe c:/Users/omary/Desktop/CS_1/chemical-rag-system/app/x.py
# # MACCS: 0.375
# # (.venv) PS C:\Users\omary\Desktop\CS_1\chemical-rag-system> 

# # from rdkit import Chem
# # from rdkit.Chem import rdMolDescriptors
# # from rdkit import DataStructs

# # mol1 = Chem.MolFromSmiles("c1ccccc1")
# # mol2 = Chem.MolFromSmiles("c1ccncc1")

# # fp1 = rdMolDescriptors.GetHashedAtomPairFingerprintAsBitVect(mol1, nBits=2048)
# # fp2 = rdMolDescriptors.GetHashedAtomPairFingerprintAsBitVect(mol2, nBits=2048)

# # print("AtomPair:", DataStructs.TanimotoSimilarity(fp1, fp2))

# # (.venv) PS C:\Users\omary\Desktop\CS_1\chemical-rag-system> & c:/Users/omary/Desktop/CS_1/.venv/Scripts/python.exe c:/Users/omary/Desktop/CS_1/chemical-rag-system/app/x.py
# # [07:23:55] DEPRECATION WARNING: please use AtomPairGenerator
# # [07:23:55] DEPRECATION WARNING: please use AtomPairGenerator
# # AtomPair: 0.6153846153846154
# # (.venv) PS C:\Users\omary\Desktop\CS_1\chemical-rag-system> 


# from rdkit import Chem
# from rdkit.Chem import rdMolDescriptors
# from rdkit import DataStructs

# mol1 = Chem.MolFromSmiles("c1ccccc1")
# mol2 = Chem.MolFromSmiles("c1ccncc1")

# fp1 = rdMolDescriptors.GetHashedTopologicalTorsionFingerprintAsBitVect(mol1, nBits=2048)
# fp2 = rdMolDescriptors.GetHashedTopologicalTorsionFingerprintAsBitVect(mol2, nBits=2048)

# print("Torsion:", DataStructs.TanimotoSimilarity(fp1, fp2))

# (.venv) PS C:\Users\omary\Desktop\CS_1\chemical-rag-system> & c:/Users/omary/Desktop/CS_1/.venv/Scripts/python.exe c:/Users/omary/Desktop/CS_1/chemical-rag-system/app/x.py
# [07:24:25] DEPRECATION WARNING: please use TopologicalTorsionGenerator
# [07:24:25] DEPRECATION WARNING: please use TopologicalTorsionGenerator
# Torsion: 0.2857142857142857
# (.venv) PS C:\Users\omary\Desktop\CS_1\chemical-rag-system> 