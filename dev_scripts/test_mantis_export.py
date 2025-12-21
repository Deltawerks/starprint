"""
Test the Blueprint export with RSI Mantis (medium ship).
This verifies the system works across different ship types.
"""
import sys
import asyncio
sys.path.insert(0, ".")

from backend.main import SCManager
from pathlib import Path

async def test_mantis_export():
    manager = SCManager()
    sc_path = r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE"
    
    print("Loading SC...")
    await asyncio.to_thread(manager.load_sc, sc_path)
    print(f"SC Loaded: {manager.sc.version_label}")
    
    # Find Mantis
    test_ship = "RSI_Mantis"
    ship_record = None
    for records in manager._records_by_path.values():
        for r in records:
            if r.name == test_ship:
                ship_record = r
                break
        if ship_record:
            break
    
    if not ship_record:
        # Try searching
        print(f"Exact match not found, searching for Mantis...")
        for records in manager._records_by_path.values():
            for r in records:
                if "mantis" in r.name.lower():
                    print(f"  Found: {r.name}")
                    ship_record = r
                    break
            if ship_record:
                break
    
    if not ship_record:
        print(f"ERROR: Could not find Mantis")
        return
    
    print(f"\nFound: {ship_record.name} (GUID: {ship_record.id})")
    
    # Test the Blueprint export
    print("\n" + "="*60)
    print("Testing export_item_blueprint with Mantis")
    print("="*60 + "\n")
    
    try:
        result = manager.export_item_blueprint(str(ship_record.id))
        print(f"\n{'='*60}")
        print(f"RESULT: {result['status']}")
        print(f"{'='*60}")
        
        # Check output file
        if result.get("output_file"):
            output_path = Path(result["output_file"])
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024*1024)
                print(f"SUCCESS: {output_path.name} ({size_mb:.1f} MB)")
            else:
                print(f"ERROR: Output file does not exist: {output_path}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mantis_export())
