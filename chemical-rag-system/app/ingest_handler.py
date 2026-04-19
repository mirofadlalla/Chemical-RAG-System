"""
Ingestion handler - checks for data and runs ingest.py if needed
"""

import os
import json
import sys


def run_ingestion():
    """
    Run the ingestion pipeline if compounds.json doesn't exist.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ingest_script = os.path.join(base_dir, "ingest.py")
    data_file = os.path.join(base_dir, "data", "compounds.json")
    
    if os.path.exists(data_file):
        try:
            with open(data_file) as f:
                data = json.load(f)
            if len(data) > 0:
                print(f"✅ Data already exists: {len(data)} compounds")
                return True
        except:
            pass
    
    print("🔄 Running ingest.py...")
    if os.path.exists(ingest_script):
        os.system(f"{sys.executable} {ingest_script}")
        return True
    else:
        print(f"❌ ingest.py not found at {ingest_script}")
        return False
