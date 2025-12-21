"""
Test the new export_item_blueprint method with the Arrow.
"""
import sys
import asyncio
sys.path.insert(0, ".")

from backend.main import SCManager
from pathlib import Path

async def test_blueprint_export():
    manager = SCManager()
    sc_path = r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE"
    
    print("Loading SC...")
    await asyncio.to_thread(manager.load_sc, sc_path)
    print(f"SC Loaded: {manager.sc.version_label}")
    
    # Find Arrow GUID
    arrow_name = "ANVL_Arrow"
    arrow_record = None
    for records in manager._records_by_path.values():
        for r in records:
            if r.name == arrow_name:
                arrow_record = r
                break
        if arrow_record:
            break
    
    if not arrow_record:
        print(f"ERROR: Could not find {arrow_name}")
        return
    
    print(f"Found: {arrow_record.name} (GUID: {arrow_record.id})")
    
    # Test the new Blueprint export
    print("\n--- Testing export_item_blueprint ---")
    try:
        result = manager.export_item_blueprint(str(arrow_record.id))
        print(f"\nResult: {result}")
        
        # Check output file
        if result.get("output_file"):
            output_path = Path(result["output_file"])
            if output_path.exists():
                print(f"SUCCESS: {output_path} exists ({output_path.stat().st_size:,} bytes)")
            else:
                print(f"ERROR: Output file does not exist: {output_path}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_blueprint_export())
