import sys
import os
import xml.etree.ElementTree as ET
from pathlib import Path

# Fix path to allow importing backend
sys.path.append(os.path.dirname(__file__))

try:
    from backend.main import SCManager
    from scdatatools.engine.cryxml import etree_from_cryxml_file
except ImportError as e:
    print(f"ImportError: {e}")
    sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
    try:
        from main import SCManager
    except:
        print("Failed to import SCManager")
        sys.exit(1)

def explore_loadout():
    manager = SCManager()
    print("SCManager initialized.")

    item_name = "ANVL_Arrow"
    # Search for Entity Record
    search_pattern = f"Data/Libs/Foundry/Records/**/{item_name}.xml"
    print(f"Searching for Entity Record: {search_pattern}")
    
    matches = manager.sc.p4k.search(search_pattern)
    if not matches:
        print("No Entity Record found.")
        return

    record_path = matches[0].filename
    print(f"Found Entity Record: {record_path}")
    
    # Parse it
    try:
        with manager.sc.p4k.open(record_path) as f:
            tree = etree_from_cryxml_file(f)
            root = tree.getroot() if hasattr(tree, 'getroot') else tree
            
        print(f"Root Tag: {root.tag}")
        
        # Look for Loadout/Components
        # Recursively print all tags to see structure
        # Limit depth/count
        print("--- Structure ---")
        for elem in root.iter():
             print(f"Tag: {elem.tag} Attribs: {elem.attrib}")
             if elem.tag in ['Components', 'Loadout', 'Parts', 'ItemPort']:
                 print("!!! POTENTIAL MATCH !!!")
                 
    except Exception as e:
        print(f"Error parsing {record_path}: {e}")

if __name__ == "__main__":
    explore_loadout()
