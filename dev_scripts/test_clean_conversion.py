import trimesh
import traceback

dae_path = r"e:/Antigravity/Starfab_Agentic/StarPrint/exports_test/Data/Objects/Characters/Human/male_v7/armor/ccc/m_ccc_medium_helmet_01_prop.dae"
obj_path = r"e:/Antigravity/Starfab_Agentic/StarPrint/exports_test/test_conversion.obj"

print(f"Loading DAE: {dae_path}")
try:
    scene = trimesh.load(dae_path, force='scene')
    print("DAE loaded successfully.")
    print(f"Geometry count: {len(scene.geometry)}")
    
    # Combine meshes
    if isinstance(scene, trimesh.Scene):
        meshes = [g for g in scene.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if meshes:
            combined = trimesh.util.concatenate(meshes)
            print(f"Combined into single mesh with {len(combined.vertices)} vertices")
            
            combined.export(obj_path, file_type='obj')
            print(f"Exported to OBJ: {obj_path}")
        else:
            print("No trimeshes found in scene.")
    else:
        scene.export(obj_path, file_type='obj')
        print(f"Exported scene to OBJ: {obj_path}")

except Exception as e:
    print(f"Conversion failed: {e}")
    traceback.print_exc()
