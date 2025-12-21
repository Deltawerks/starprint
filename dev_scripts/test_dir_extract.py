from scdatatools.sc import StarCitizen
from scdatatools.forge.utils import geometry_for_record
import os
from pathlib import Path
import subprocess

sc = StarCitizen(r'C:\Program Files\Roberts Space Industries\StarCitizen\LIVE')
rec = [r for r in sc.datacore.records if 'ccc_medium_armor_helmet_01_01_01' in r.name.lower()][0]

print(f"Record: {rec.name}")

# Get geometry info
geo = geometry_for_record(rec, data_root=sc.p4k)
geo_info = geo.get('tableDisplay') or list(geo.values())[0]
print(f"Geometry File: {geo_info.filename}")

# Define export root
EXPORT_ROOT = Path("exports_test")
EXPORT_ROOT.mkdir(exist_ok=True)

# Get parent directory of the CGF
cgf_path_obj = Path(geo_info.filename)
parent_dir = cgf_path_obj.parent.as_posix() # e.g. Data/Objects/Characters/Human/male_v7/armor/ccc
print(f"Parent Dir: {parent_dir}")

# Search for ALL files in this directory
print("Listing files in directory...")
files_to_extract = sc.p4k.search(f"{parent_dir}/*")
print(f"Found {len(files_to_extract)} files")

# Extract them maintaining structure
for f in files_to_extract:
    # We want to extract to exports_test/Data/Objects/...
    # So relative path matches
    dest_path = EXPORT_ROOT / f.filename
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        data = sc.p4k.read(f.filename)
        with open(dest_path, 'wb') as out_f:
            out_f.write(data)
    except Exception as e:
        print(f"Failed to extract {f.filename}: {e}")

print("Extraction complete.")

# Run CGF Converter
CGF_CONVERTER = Path(r"e:/Antigravity/Starfab_Agentic/.venv/Lib/site-packages/starfab/contrib/cgf-converter.exe")
cgf_local_path = EXPORT_ROOT / geo_info.filename

print(f"Running cgf-converter on {cgf_local_path}")
print(f"ObjectDir: {EXPORT_ROOT}")

try:
    result = subprocess.run(
        [str(CGF_CONVERTER), str(cgf_local_path), "-dae", "-objectdir", str(EXPORT_ROOT)],
        capture_output=True,
        text=True,
        timeout=120
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
except Exception as e:
    print(f"Converter failed: {e}")
