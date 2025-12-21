import sys
from backend.main import manager, _extract_thumbnail
from backend.main import CACHE_DIR
import asyncio

async def test():
    print("Initializing SC...")
    manager.load_sc(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
    
    # 1. Test Thumbnail Extraction
    print("\n--- Testing Thumbnail Extraction ---")
    # Find Arrow
    arrow = None
    for r in manager._records_by_guid.values():
        if r.name == "ANVL_Arrow":
            arrow = r
            break
            
    if arrow:
        print(f"Found Arrow: {arrow.id}")
        thumb_path = _extract_thumbnail(manager, str(arrow.id))
        if thumb_path:
            print(f"Thumbnail extracted: {thumb_path}")
            if thumb_path.exists():
                print(f"File exists, size: {thumb_path.stat().st_size} bytes")
                # Verify it is a PNG? (Header check)
                with open(thumb_path, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b'\x89PNG\r\n\x1a\n'):
                        print("File is valid PNG.")
                    else:
                        print("File is NOT PNG.")
            else:
                print("Error: File does not exist.")
        else:
            print("Thumbnail extraction returned None (No icon found?)")
            
    # 2. Test GLB Export Return
    print("\n--- Testing GLB Export Return ---")
    # We won't run full export again if we can avoid it, but let's do it for the Arrow since it's cached/easy
    # Or just check the logic?
    # We'll run it, it confirms GLB creation.
    if arrow:
        try:
            print("Running export...")
            res = manager.export_item(str(arrow.id))
            print(f"Export Result: {res}")
            
            if 'preview_url' in res:
                print(f"Preview URL: {res['preview_url']}")
                if res['preview_url']:
                    print("Preview URL is present (Success).")
                else:
                    print("Preview URL is None (Failed).")
            else:
                print("Preview URL key missing from response.")
                
            # Verify file
            if res.get('preview_url'):
                # Extract filename from url
                fname = res['preview_url'].split('/')[-1]
                fpath = CACHE_DIR.parent / "exports" / "anvl_arrow" / fname
                if fpath.exists():
                     print(f"GLB File exists: {fpath}")
                     print(f"Size: {fpath.stat().st_size} bytes")
                else:
                     print(f"GLB File NOT found at {fpath}")

        except Exception as e:
            print(f"Export failed: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test())
