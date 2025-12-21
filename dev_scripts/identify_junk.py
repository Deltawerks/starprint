import sys
import os
from pathlib import Path
# Insert backend dir to path
sys.path.insert(0, os.path.abspath("backend"))
from main import SCManager

import asyncio

async def analyze():
    print("Initializing SC Manager...")
    try:
        manager = SCManager()
        # Mock load if SC_PATH isn't set in env, but we know it from previous runs
        # or we just rely on SCManager's defaults if it saved state?
        # SCManager doesn't save state. We need to pass the path.
        # I'll hardcode the path I know works:
        sc_live_path = r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE"
        
        manager.load_sc(sc_live_path)
        print("SC Loaded.")
        
        # 1. Search for "P4" to see junk types
        print("\n--- Searching 'P4' ---")
        results = manager.search_items("P4")
        
        types_found = set()
        for r in results:
             # r is a dictionary 'id', 'name', 'type', ...
             types_found.add(r['type'])
             if "Dialogue" in r['type'] or "NPC" in r['name']:
                 print(f"JUNK: {r['name']} ({r['type']})")
        
        print(f"\nTypes found: {types_found}")

        # 2. Check Localization
        print("\n--- Checking Localization API ---")
        dc = manager.sc.datacore
        print(f"Datacore attributes: {dir(dc)}")
        
        # Try to find a localization method
        if hasattr(dc, 'localizations'):
             print(f"Found 'localizations' attr, type: {type(dc.localizations)}")
             # accessible like a dict?
             # properties in records usually have '@' prefix for loc keys
             # e.g. '@item_NameP4AR'
             
             # Let's find a record that might have a label
             # The Behring P4-AR is likely 'behr_rifle_ballistic_01'
             # Let's find it in records
             p4ar = manager.get_record_by_guid("174067d1-1438-4a8e-b74d-70cc2500bd35") # I don't know GUID, search it
             # Wait, I can search for it
             
             print("\nLooking for 'behr_rifle_ballistic_01'...")
             matches = [r for r in manager.sc.datacore.records if 'behr_rifle_ballistic_01' in r.name.lower()]
             for m in matches[:5]:
                 print(f"Record: {m.name}")
                 print(f"  Properties keys: {m.properties.keys() if hasattr(m, 'properties') else 'None'}")
                 # Check for 'Name' or 'Display'
                 # Often it's in properties['Name'] which is '@loc_key'
                 
             # Check how to resolve '@loc_key'

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(analyze())
