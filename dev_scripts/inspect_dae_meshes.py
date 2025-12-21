import trimesh
import sys

# Path to the valid DAE we generated
dae_path = r"e:/Antigravity/Starfab_Agentic/StarPrint/exports_test/Data/Objects/Characters/Human/male_v7/armor/ccc/m_ccc_medium_helmet_01_prop.dae"

print(f"Loading: {dae_path}")
try:
    scene = trimesh.load(dae_path, force='scene')
    
    print("\n--- Geometry Analysis ---")
    if isinstance(scene, trimesh.Scene):
        for name, geom in scene.geometry.items():
            print(f"Name: {name}")
            print(f"  Type: {type(geom)}")
            if hasattr(geom, 'vertices'):
                print(f"  Vertices: {len(geom.vertices)}")
            if hasattr(geom, 'faces'):
                print(f"  Faces: {len(geom.faces)}")
            print("-" * 30)
            
        print("\n--- Node/Graph Analysis (Hierarchy) ---")
        # Trimesh graph node names
        for node in scene.graph.nodes:
            # Check if this node has geometry
            # scene.graph.transforms.edge_data might help, or scene.geometry element lookup
            # scene.graph[node] gives transform
            
            # The map of node_name -> geometry_name is in scene.graph.geometry_nodes if available
            # or we iterate nodes and check if they imply geometry
            pass
            
        # Better approach for trimesh scene graph inspection
        for node_name in scene.graph.nodes:
            # Get geometry attached to this node
            # In trimesh < 4.0 it might be different, but usually:
            geoms = scene.graph.geometry_nodes.get(node_name, [])
            if geoms:
                 print(f"Node: '{node_name}' -> Geometry: {geoms}")
            else:
                 pass
                 # print(f"Node: '{node_name}' (No Geometry)")
                 
        print("\n--- Bounding Box Analysis ---")
        # Collect mesh metadata
        mesh_data = []
        for name, geom in scene.geometry.items():
            if hasattr(geom, 'bounds') and hasattr(geom, 'vertices'):
                center = geom.centroid # or geom.bounds.mean(axis=0)
                extents = geom.extents # size in x,y,z
                mesh_data.append({
                    'name': name, 
                    'vertices': len(geom.vertices),
                    'faces': len(geom.faces),
                    'center': center,
                    'extents': extents,
                    'bounds': geom.bounds
                })

        # Check for overlaps
        import numpy as np
        
        # Sort by vertex count descending (assume highest is LOD0)
        mesh_data.sort(key=lambda x: x['vertices'], reverse=True)
        
        kept_meshes = []
        discarded_meshes = []
        
        for i, m1 in enumerate(mesh_data):
            is_lod = False
            # Compare with already kept meshes
            for m2 in kept_meshes:
                # Check if centers are close and extents are similar
                # This suggests they represent the same object at different details
                dist = np.linalg.norm(m1['center'] - m2['center'])
                
                # Check volume similarity or containment
                # Simple check: identical center and similar size
                if dist < 0.01: # 1cm tolerance
                    # Check if scale is somewhat similar (LODs usually match size)
                    size_diff = np.linalg.norm(m1['extents'] - m2['extents'])
                    if size_diff < 0.1: # 10cm tolerance
                         print(f"  [Overlap] {m1['name']} ({m1['vertices']}v) overlaps {m2['name']} ({m2['vertices']}v) -> Discarding as likely LOD/Proxy")
                         is_lod = True
                         break
            
            if not is_lod:
                if m1['vertices'] < 50:
                     print(f"  [Junk] {m1['name']} ({m1['vertices']}v) -> Discarding (too small)")
                     discarded_meshes.append(m1)
                else:
                     kept_meshes.append(m1)
                     print(f"  [Keep] {m1['name']} ({m1['vertices']}v)")
            else:
                discarded_meshes.append(m1)

        print("\n--- Material Analysis ---")
        material_groups = {}
        
        for name, geom in scene.geometry.items():
            # Get material name attached to this geometry (if available via visuals)
            mat_name = "unknown"
            if hasattr(geom, 'visual'):
                if hasattr(geom.visual, 'material'):
                     mat = geom.visual.material
                     if hasattr(mat, 'name'):
                         mat_name = mat.name
                     elif isinstance(mat, trimesh.visual.material.PBRMaterial):
                         mat_name = mat.name or "PBR"
            
            if mat_name not in material_groups:
                material_groups[mat_name] = []
            
            material_groups[mat_name].append({
                'name': name,
                'vertices': len(geom.vertices)
            })

        kept_meshes_by_mat = []
        for mat, meshes in material_groups.items():
            print(f"Material: {mat}")
            # Sort by vertices descending
            meshes.sort(key=lambda x: x['vertices'], reverse=True)
            
            # Keep top 1 (LOD0) for each material?
            # Warning: A material might be used on multiple distinct parts (e.g. left and right glove)
            # checking bounds is safer combined with this.
            for m in meshes:
                print(f"  - {m['name']} ({m['vertices']}v)")

        # Aggressive LOD filter strategy:
        # If meshes share material AND have significant vertex count difference -> Assume LOD
        # But if vertex counts are similar, might be distinct parts.


             
    else:
        print("Not a Scene object?")
        print(type(scene))

except Exception as e:
    print(f"Error: {e}")
