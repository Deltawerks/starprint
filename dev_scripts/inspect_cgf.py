from scdatatools.sc import StarCitizen
from scdatatools.forge.utils import geometry_for_record
import re

sc = StarCitizen(r'C:\Program Files\Roberts Space Industries\StarCitizen\LIVE')
rec = [r for r in sc.datacore.records if 'ccc_medium_armor_helmet_01_01_01' in r.name.lower()][0]

print(f"Record: {rec.name}")

# Get geometry info
geo = geometry_for_record(rec, data_root=sc.p4k)
geo_info = geo.get('tableDisplay') or list(geo.values())[0]
print(f"Geometry File: {geo_info.filename}")

# Read the file content
content = sc.p4k.read(geo_info.filename)

# Look for file paths in the binary content
# Pattern: text characters ending with extension
valid_chars = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_/-."
paths = set()

# Simple string extraction
current_string = b""
for byte in content:
    if byte in valid_chars:
        current_string += bytes([byte])
    else:
        if len(current_string) > 4:
            s = current_string.decode('utf-8', errors='ignore')
            if '.' in s and '/' in s: # Likely a path
                paths.add(s)
        current_string = b""

print("\nPossible Dependencies Found:")
for p in sorted(paths):
    if any(p.lower().endswith(ext) for ext in ['.mtl', '.dds', '.tif', '.cgf', '.cga', '.skin', '.chr']):
        print(f" - {p}")
