from scdatatools.sc import StarCitizen
import sys

sc = StarCitizen(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
print("SC Loaded")

from scdatatools.engine.cryxml import etree_from_cryxml_file
from io import BytesIO
import xml.etree.ElementTree as ET

# Found via log: Data/Objects/Spaceships/Ships/ANVL/LandingGear/Arrow/ANVL_Arrow_Landing_Gear_Front.cdf
cdf_path = "Data/Objects/Spaceships/Ships/ANVL/LandingGear/Arrow/ANVL_Arrow_Landing_Gear_Front.cdf"

print(f"Reading: {cdf_path}")
try:
    # Use sc.p4k.open to read directly
    with sc.p4k.open(cdf_path) as f:
        content = f.read()
        
    print(f"Size: {len(content)} bytes")
    
    # Parse CryXml (BytesIO wrapper needed?)
    # scdatatools might expect a file-like object
    root = etree_from_cryxml_file(BytesIO(content))
    print("--- CONTENT (Parsed XML) ---")
    ET.dump(root)
        
except Exception as e:
    print(f"Error reading file: {e}")
    import traceback
    traceback.print_exc()
