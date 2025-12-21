from typing import List, Dict, Optional, Any
import os
import subprocess
from pathlib import Path
import trimesh
import numpy as np
import xml.etree.ElementTree as ET
from scdatatools.engine.cryxml import etree_from_cryxml_file, etree_from_cryxml_string
# from .main import SCManager  # Avoid circular import

class BlueprintAssembler:
    def __init__(self, manager: Any, converter_path: Path):
        self.manager = manager
        self.converter_path = converter_path
        
    def find_blueprint(self, record):
        """Locates the XML definition file for a record."""
        # Try known naming conventions
        candidates = [
            f"Data/Scripts/Entities/Vehicles/Implementations/Xml/{record.name}.xml",
            f"Data/Scripts/Entities/Vehicles/Implementations/Xml/{record.name}.cdf",
        ]
        
        # Check standard path from record if available (scdatatools might expose it)
        # record.path implies property available?
        # Use loose search if strict fails
        
        for path in candidates:
             if self.manager.sc.p4k.search(path):
                 return path
                 
        # Fallback: Search globally
        print(f"Blueprint: Standard paths failed for {record.name}, searching...")
        matches = self.manager.sc.p4k.search(f"Data/**/{record.name}.xml")
        if matches:
            # Filter for Implementations/Xml if possible
            for m in matches:
                if "Implementations/Xml" in m.filename:
                    return m.filename
            return matches[0].filename
            
        return None

    def parse_blueprint(self, file_path: str) -> Optional[ET.Element]:
        """Parses the XML/CDF file."""
        print(f"Assembler: Parsing Blueprint {file_path}")
        try:
            with self.manager.sc.p4k.open(file_path) as f:
                # Use scdatatools CryXML parser
                tree = etree_from_cryxml_file(f)
                if hasattr(tree, 'getroot'):
                    return tree.getroot()
                return tree
        except Exception as e:
            print(f"Assembler: Error parsing blueprint: {e}")
            return None

    def _resolve_geometry_path(self, item_name: str) -> Optional[str]:
        """Finds the geometry file for a named item (e.g. from hardpoint)."""
        # Look up item in cache
        # We need to find the record by NAME
        found_record = None
        # This global search is slow, maybe optimize later?
        # But category_cache is Dict[uid, record].
        # We need Dict[name, record].
        # manager._records_by_guid is populated.
        # But we need by NAME.
        
        # Fast lookup if manager supports it, or specific manufacturer lists
        # For now, iterate cache
        for r in self.manager._records_by_guid.values():
            if r.name == item_name:
                found_record = r
                break
                
        if not found_record:
            return None
            
        # Determine geometry path for record
        # Similar logic to main.py export_item
        # Usually found_record.std_item.geometry or search
        # We can reuse the logic from main.py if we extract it, 
        # or just simple search for CGA/CGF
        match = self.manager.sc.p4k.search(f"Data/**/{item_name}.cga")
        if not match:
             match = self.manager.sc.p4k.search(f"Data/**/{item_name}.cgf")
             
        if match:
            return match[0].filename
        return None

    def _convert_and_load_part(self, cga_path: str, extract_dir: Path) -> Optional[trimesh.Trimesh]:
        """Extracts, converts, and loads a part's geometry."""
        # 1. Extract file
        # Check if already extracted
        local_path = extract_dir / cga_path
        if not local_path.exists():
            # Try to extract
            try:
                # Find in P4K (might need searching if path is relative or fuzzy)
                # match = self.manager.sc.p4k.search(cga_path)
                # For now assume exact path or close to it
                # We need to replicate main.py's extraction logic which extracts WHOLE folder
                # Here we arguably just want one file?
                # But CGF converter needs materials/textures often?
                # Let's verify if main.py extraction covers it.
                # Main.py extracts the SHIP folder. 
                # Attached parts (e.g. Weapons) might be in DIFFERENT folders (Data/Objects/Weapons/...)
                # So we MUST extract them.
                
                # Check P4K
                 entry = self.manager.sc.p4k.get(cga_path)
                 if entry:
                     # Create dir
                     local_path.parent.mkdir(parents=True, exist_ok=True)
                     with entry.open() as src, open(local_path, "wb") as dst:
                         dst.write(src.read())
                 else:
                     print(f"Assembler: Part file not found in P4K: {cga_path}")
                     return None
            except Exception as e:
                print(f"Assembler: Error extracting part {cga_path}: {e}")
                return None

        # 2. Convert to DAE
        dae_path = local_path.with_suffix(".dae")
        
        if not dae_path.exists():
            try:
                subprocess.run([str(self.converter_path), str(local_path), "-o", str(dae_path)], 
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Assembler: Error converting part {local_path}: {e}")
                return None
                
        # 3. Load DAE
        try:
            mesh = trimesh.load(dae_path, force='mesh') # Load as single mesh for simplicity?
            # Or scene?
            return mesh
        except Exception as e:
            print(f"Assembler: Error loading DAE {dae_path}: {e}")
            return None

    def assemble(self, record, main_mesh: trimesh.Scene, extract_root: Path) -> trimesh.Scene:
        """
        Assembles attached parts (Loadouts, Landing Gear) onto the main scene.
        """
        print(f"Assembler: Starting assembly for {record.name}")

        # 1. Processing Landing Gear
        # Naming convention: {ShipName}_LandingSystem
        ls_name = f"{record.name}_LandingSystem"
        print(f"Assembler: Searching for Landing System {ls_name}")
        
        ls_record = None
        for r in self.manager._records_by_guid.values():
            if r.name == ls_name:
                ls_record = r
                break
        
        if ls_record and hasattr(ls_record, 'properties'):
            gears = ls_record.properties.get('gears', [])
            print(f"Assembler: Found {len(gears)} landing gears")
            for i, gear in enumerate(gears):
                if not hasattr(gear, 'properties'): continue
                
                props = gear.properties
                bone_name = props.get('bone', '')
                geom_struct = props.get('geometry')
                
                if not bone_name or not geom_struct:
                    continue

                # geometry path extraction
                geom_path = ""
                if hasattr(geom_struct, 'properties'):
                     geom_path = geom_struct.properties.get('path', '')
                     
                if not geom_path:
                    continue
                    
                print(f"Assembler: Gear {i} Bone='{bone_name}' Path='{geom_path}'")
                self._attach_component(main_mesh, extract_root, bone_name, geom_path)

        # 2. Processing Default Loadout (Weapons, Seats, etc)
        # Inspect main record components
        if hasattr(record, 'properties'):
            comps_container = record.properties.get('Components', [])
            
            # Helper to extract loadout from a component object
            def extract_loadout_entries(comp_obj):
                if not hasattr(comp_obj, 'properties'): return []
                c_props = comp_obj.properties
                if 'loadout' in c_props:
                     l_params = c_props['loadout']
                     if hasattr(l_params, 'properties'):
                         return l_params.properties.get('entries', [])
                return []

            all_entries = []

            # Handle List type (Mantis)
            if isinstance(comps_container, list):
                for comp in comps_container:
                    # Check for DefaultLoadoutParams via name
                    comp_name = getattr(comp, 'name', '')
                    if comp_name == 'SEntityComponentDefaultLoadoutParams':
                         print("Assembler: Found DefaultLoadout via List scan")
                         all_entries.extend(extract_loadout_entries(comp))
            
            # Handle Dict type (Arrow - wrapped by scdatatools?)
            elif hasattr(comps_container, 'items') or isinstance(comps_container, dict):
                 # Try accessing by key if possible, or iterate values
                 # Arrow seemingly had it accessible via key or as a dict-like struct
                 
                 # Check specific key
                 if 'SEntityComponentDefaultLoadoutParams' in comps_container:
                      print("Assembler: Found DefaultLoadout via Dict key")
                      all_entries.extend(extract_loadout_entries(comps_container['SEntityComponentDefaultLoadoutParams']))
                 else:
                      # Iterate values just in case
                      iterable = comps_container.values() if isinstance(comps_container, dict) else comps_container
                      for comp in iterable:
                           comp_name = getattr(comp, 'name', '')
                           if comp_name == 'SEntityComponentDefaultLoadoutParams':
                                all_entries.extend(extract_loadout_entries(comp))

            if all_entries:
                print(f"Assembler: Found Default Loadout with {len(all_entries)} entries")
                
                for entry in all_entries:
                    if not hasattr(entry, 'properties'): continue
                    e_props = entry.properties
                    
                    port_name = e_props.get('itemPortName', '')
                    entity_class = e_props.get('entityClassName', '')
                    
                    if not port_name or not entity_class:
                        continue
                        
                    # Resolve Entity Class to Geometry
                    item_geo_path = self._resolve_item_geometry(entity_class)
                    
                    if item_geo_path:
                        print(f"Assembler: Loadout Item '{entity_class}' -> Port '{port_name}'")
                        self._attach_component(main_mesh, extract_root, port_name, item_geo_path)

        return main_mesh

    def _resolve_item_geometry(self, item_name: str) -> Optional[str]:
        """Finds geometry path for a given item name."""
        if not item_name: return None
        
        # 1. Look for record
        item_record = None
        for r in self.manager._records_by_guid.values():
            if r.name == item_name:
                item_record = r
                break
        
        if not item_record:
            return None
            
        # 2. Try to get geometry from properties (if available) - requires parsing? 
        # Or use manager helper if exists.
        # Fallback to searching for .cga/.cgf with same name
        # Using a heuristic search
        
        # Try direct search first
        patterns = [
            f"Data/**/{item_name}.cga",
            f"Data/**/{item_name}.cgf",
            f"Data/**/{item_name}_lod0.cga" # explicit lod
        ]
        
        for p in patterns:
            matches = self.manager.sc.p4k.search(p)
            if matches:
                # Filter out 'lod1', 'lod2' etc if parsing specifically
                # Prefer exact match
                return matches[0].filename
                
        return None

    def _attach_component(self, scene: trimesh.Scene, extract_root: Path, bone_name: str, geom_path: str):
        """Loads comp geometry, finds bone transform, and adds to scene."""
        
        # Convert path to string if needed
        geom_path = str(geom_path)
        
        # 1. Find Bone Transform
        # Trimesh Scene graph nodes might have names.
        # We need the world transform of the bone node.
        try:
            # scene.graph.get(to_node) returns the matrix from world to node? or node to world?
            # get(frame_to, frame_from) -> 4x4
            # We want transform of bone relative to world
            # frame_from=None (world)
            transform = scene.graph.get(bone_name, frame_from=None)[0]
        except ValueError:
            # Bone not found in graph
            # This happens if DAE didn't export bones or named them differently
            # print(f"Assembler: Bone '{bone_name}' not found in scene graph.")
            # Some bones have "_joint" suffix or similar?
            return

        # 2. Load Geometry
        comp_mesh = self._convert_and_load_part(geom_path, extract_root)
        if not comp_mesh:
            return
            
        # 3. Apply Transform
        # Apply the transform to the vertices directly (since we are merging)
        # OR add as a node in the scene?
        # If we return a merged scene, we should probably add it to the graph.
        
        # Adding to graph:
        # scene.add_geometry(geometry=comp_mesh, node_name=f"{bone_name}_att", parent_node_name=bone_name, transform=np.eye(4))
        # Wait, if we attach to the bone node, we don't need to manually apply the world transform. 
        # The scene graph handles it!
        
        try:
            # Check if geometry is a Scene or Trimesh
            if isinstance(comp_mesh, trimesh.Scene):
                # If it's a scene, we might need to merge it or take its geometry
                # Simply dump all geometries from it?
                # For now take specific geom
               pass
               # If complicated, skip or flatten
               if len(comp_mesh.geometry) > 0:
                   # Take the first one or merge
                   comp_mesh = trimesh.util.concatenate(list(comp_mesh.geometry.values()))
               else:
                   return

            # Add to scene attached to bone
            # Note: attachments are usually identity relative to the bone
            scene.add_geometry(comp_mesh, node_name=f"Attached_{bone_name}", parent_node_name=bone_name)
            print(f"Assembler: Attached {geom_path} to {bone_name}")
            
        except Exception as e:
            print(f"Assembler: Error attaching {geom_path}: {e}")
        
    def rotate_for_export(self, mesh: trimesh.Scene) -> trimesh.Trimesh:
        """Rotates the final mesh -90 degrees X (Upright Y-Forward)."""
        # Create rotation matrix
        # -90 deg X means (x, y, z) -> (x, z, -y)?
        # X axis rotation:
        # 1  0  0
        # 0  c -s
        # 0  s  c
        # -90 deg: c=0, s=-1
        # 1  0  0
        # 0  0  1
        # 0 -1  0
        matrix = np.eye(4)
        matrix[:3, :3] = [
            [1,  0, 0],
            [0,  0, 1],
            [0, -1, 0]
        ]
        
        # Apply to scene
        mesh.apply_transform(matrix)
        return mesh
