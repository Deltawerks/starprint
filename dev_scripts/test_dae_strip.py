import trimesh
import re
from pathlib import Path

dae_path = Path(r"e:\Antigravity\Starfab_Agentic\StarPrint\exports\cds_armor_heavy_helmet_01_01_opaque\Data\Objects\Characters\Human\male_v7\armor\cds\m_cds_heavy_helmet_01_prop.dae")
stripped_path = dae_path.with_name("stripped.dae")
obj_path = dae_path.with_name("final.obj")

print(f"Reading {dae_path}...")
content = dae_path.read_text(errors='ignore')

# Brutally strip material libraries to avoid pycollada errors
print("Stripping material libraries...")
content = re.sub(r'<library_images>.*?</library_images>', '<library_images/>', content, flags=re.DOTALL)
content = re.sub(r'<library_materials>.*?</library_materials>', '<library_materials/>', content, flags=re.DOTALL)
content = re.sub(r'<library_effects>.*?</library_effects>', '<library_effects/>', content, flags=re.DOTALL)

# Also need to remove material bindings in instance_geometry?
# <bind_material>...</bind_material>
content = re.sub(r'<bind_material>.*?</bind_material>', '', content, flags=re.DOTALL)

stripped_path.write_text(content)
print(f"Saved stripped DAE to {stripped_path}")

print("Attempting to load with trimesh...")
try:
    mesh = trimesh.load(stripped_path)
    print(f"Loaded mesh: {mesh}")
    
    if isinstance(mesh, trimesh.Scene):
        # Merge if scene
        if len(mesh.geometry) > 0:
            print(f"Scene has {len(mesh.geometry)} geometries. Merging...")
            # concat
            mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
        else:
            print("Scene has no geometry!")
            exit(1)
            
    print(f"Exporting to OBJ: {obj_path}")
    mesh.export(str(obj_path))
    
    if obj_path.exists() and obj_path.stat().st_size > 0:
        print(f"SUCCESS! OBJ created: {obj_path.stat().st_size} bytes")
    else:
        print("FAIL: OBJ file empty or not created")

except Exception as e:
    print(f"Trimesh failed: {e}")
    import traceback
    traceback.print_exc()
