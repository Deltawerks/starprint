import sys
import os
from pathlib import Path
from backend.main import SCManager

def explore_v3():
    sc_path = r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE"
    manager = SCManager()
    manager.load_sc(sc_path)
    
    item_name = "ANVL_Arrow"
    print(f"Searching for {item_name}...")
    found_record = None
    for record in manager._records_by_guid.values():
        if record.name == item_name:
            found_record = record
            break
            
    if not found_record:
        print("Record not found.")
        return

    print(f"Found Record: {found_record.name} ({found_record.id})")
    
    # Search for definition files
    def_files = []
    for ext in ['cdf', 'cga', 'xml']:
        search = f"Data/**/{found_record.name}.{ext}" # Assuming Data/ prefix often helps
        print(f"Searching: {search}")
        matches = manager.sc.p4k.search(search)
        if matches:
            print(f"  Found: {matches}")
            def_files.extend(matches)
        else:
            # Try without Data/ prefix?
            search_loose = f"**/{found_record.name}.{ext}"
            matches_loose = manager.sc.p4k.search(search_loose)
            if matches_loose:
                print(f"  Found (Loose): {matches_loose}")
                def_files.extend(matches_loose)

    # List Directory Contents if we found a file
    if def_files:
        primary_def = def_files[0]
        # Get directory (primary_def is P4KInfo)
        if "/" in primary_def.filename:
            parent_dir = primary_def.filename.rsplit("/", 1)[0]
        else:
            parent_dir = str(Path(primary_def.filename).parent).replace("\\", "/")
            
        print(f"\n--- Directory Listing: {parent_dir} ---")
        dir_files = manager.sc.p4k.search(f"{parent_dir}/*")
        for f in dir_files:
            print(f"  {f}")
            
    # Try Import CryXML
    print("\n--- Importing CryXML ---")
    CryXML = None
    try:
        from scdatatools.engine.cryxml import CryXML as CXML
        CryXML = CXML
        print("Success: from scdatatools.engine.cryxml import CryXML")
    except ImportError:
        pass
        
    if not CryXML:
        try:
            from scdatatools.engine import CryXML as CXML
            CryXML = CXML
            print("Success: from scdatatools.engine import CryXML")
        except ImportError:
            pass

    if not CryXML:
        print("FAILED to import CryXML. Checking dir(scdatatools.engine)...")
        try:
            from scdatatools import engine
            print(dir(engine))
        except:
            pass

    # Inspect Content (Force XML text read)
    target = None
    if def_files:
        for f in def_files:
             if f.filename.lower().endswith(".xml"):
                 target = f.filename
                 break
    
    if target:
        print(f"\n--- Inspecting Text XML: {target} ---")
        try:
            with manager.sc.p4k.open(target) as f:
                content = f.read().decode('utf-8', errors='ignore')
                print(f"Content Preview:\n{content[:500]}")
                
                # Try parsing with standard ET
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(content)
                    print(f"Root: {root.tag}")
                    
                    parts = root.findall(".//Part")
                    print(f"Parts: {len(parts)}")
                    for p in parts[:5]:
                        print(f"  {p.attrib}")
                        
                    hps = root.findall(".//ItemPort") # DataForge XML uses ItemPort usually
                    print(f"ItemPorts: {len(hps)}")
                    for hp in hps[:5]:
                        print(f"  {hp.attrib}")

                except Exception as ex:
                    print(f"ET Parse Error: {ex}")
                    
        except Exception as e:
            print(f"Read Error: {e}")

if __name__ == "__main__":
    explore_v3()
