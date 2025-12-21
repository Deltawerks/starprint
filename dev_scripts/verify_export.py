import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.dirname(__file__))

try:
    from backend.main import SCManager
    from scdatatools.engine.cryxml import etree_from_cryxml_file
except ImportError:
    pass

if __name__ == "__main__":
    manager = SCManager()
    print("SCManager initialized.")
    manager.load_sc(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")

    print("Starting Universal Export Verification...")
    
    print("Listing Candidates for Verification...")
    
    match_count = 0
    for r in manager._records_by_guid.values():
        name_lower = r.name.lower()
        if "rifle" in name_lower and "behr" in name_lower and match_count < 10:
            print(f"Rifle Candidate: {r.name}")
            match_count += 1
            
    match_count = 0
    for r in manager._records_by_guid.values():
        name_lower = r.name.lower()
        if "helmet" in name_lower and "cds" in name_lower and match_count < 10:
             print(f"Helmet Candidate: {r.name}")
             match_count += 1
             
    sys.exit(0)
                 
    sys.exit(0)
            
    # Also search for 'Default Loadout' XMLs if possible?
    # Usually 'Data/Libs/Foundry/Records/Loadouts/...'
