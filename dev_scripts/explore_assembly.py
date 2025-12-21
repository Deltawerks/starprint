import sys
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from backend.main import SCManager, StarCitizen

def inspect_item(item_name):
    sc_path = r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE"
    manager = SCManager()
    manager.load_sc(sc_path)

    print(f"Searching for {item_name}...")
    found_record = None
    for record in manager._records_by_guid.values():
        if record.name == item_name:
            found_record = record
            break
            
    if not found_record:
        print("Item not found.")
        return

    print(f"Found: {found_record.name} ({found_record.id})")
    print(f"Record Attributes: {dir(found_record)}")
    
    # 1. Inspect the main file path (usually a .cga or .cdf)
    # The record typically has a 'std_item' path or we infer it from the name/manufacturer
    # scdatatools doesn't expose the 'path' directly on the record easily, 
    # but we can search for files matching the name in the p4k.
    
    # Let's try to find the CDF or CGA
    # List all files in the directory of the found CGA
    cga_dir = str(Path(def_file).parent).replace("\\", "/")
    print(f"Listing files in: {cga_dir}")
    # scdatatools search is purely pattern based
    dir_files = manager.sc.p4k.search(f"{cga_dir}/*")
    for f in dir_files:
        print(f"  {f}")
        
    try:
        from scdatatools import engine
        print(f"scdatatools.engine contents: {dir(engine)}")
        # Check if cryxml is in there
        if 'cryxml' in dir(engine):
            from scdatatools.engine import cryxml
            print("Imported cryxml from engine")
    except ImportError as e:
         print(f"Import Error: {e}")
                     
    except Exception as e:
        print(f"Error parsing XML: {e}")

if __name__ == "__main__":
    inspect_item("ANVL_Arrow")
