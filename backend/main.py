from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import asyncio
import subprocess
import shutil
from pathlib import Path
from collections import defaultdict
import tempfile
import re
import trimesh
import numpy as np

# Import thumbnail rendering
try:
    from .thumbnails import generate_thumbnail, thumbnail_exists, get_thumbnail_path, THUMBNAIL_DIR
except ImportError:
    from thumbnails import generate_thumbnail, thumbnail_exists, get_thumbnail_path, THUMBNAIL_DIR

# scdatatools integration
try:
    from scdatatools.sc import StarCitizen
    from scdatatools.forge.utils import geometry_for_record
    from scdatatools.sc.blueprints.generators.datacore_entity import blueprint_from_datacore_entity
except ImportError:
    StarCitizen = None
    geometry_for_record = None
    blueprint_from_datacore_entity = None
    print("WARNING: scdatatools not installed.")

# Assembler import (separate try block to avoid breaking scdatatools import)
try:
    from .assembler import BlueprintAssembler
except ImportError:
    try:
        from assembler import BlueprintAssembler
    except ImportError:
        BlueprintAssembler = None

app = FastAPI()

# Configuration
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)

# Path to cgf-converter (downloaded from https://github.com/Markemp/Cryengine-Converter)
CGF_CONVERTER = Path(__file__).parent.parent / "tools" / "cgf-converter.exe"

# Interesting paths to include in navigation
INTERESTING_PATHS = {
    "entities/scitem/characters/human/armor": "Armor",
    "entities/scitem/weapons/fps_weapons": "FPS Weapons",
    "entities/scitem/weapons/melee": "Melee Weapons",
    "entities/scitem/gadgets": "Gadgets",
    "entities/scitem/mining": "Mining",
    "entities/scitem/food": "Food & Drinks",
    "entities/scitem/flair": "Flair",
    "entities/scitem/decorations": "Decorations",
}

# Paths that should be grouped by manufacturer (from item name prefix)
MANUFACTURER_GROUPED_PATHS = {
    "entities/scitem/weapons/fps_weapons",
    "entities/scitem/weapons/melee",
}

# Manufacturer name mapping
MANUFACTURER_NAMES = {
    # Ship/Vehicle Manufacturers
    "aegs": "Aegis Dynamics",
    "anvl": "Anvil Aerospace",
    "argo": "ARGO Astronautics",
    "banu": "Banu",
    "cnou": "Consolidated Outland",
    "crus": "Crusader Industries",
    "drak": "Drake Interplanetary",
    "espr": "Esperia",
    "gama": "Gatac",
    "grin": "Greycat Industrial",
    "krig": "Kruger Intergalactic",
    "misc": "MISC",
    "mrai": "Mirai",
    "orig": "Origin Jumpworks",
    "rsi": "RSI",
    "tmbl": "Tumbril",
    "vncl": "Vanduul",
    "xnaa": "Xi'An",
    # Weapon Manufacturers
    "apar": "Apocalypse Arms",
    "behr": "Behring",
    "crlf": "CureLife",
    "glsn": "Gallenson Tactical",
    "gmni": "Gemini",
    "hrst": "Hurston Dynamics",
    "klwe": "Klaus & Werner",
    "ksar": "Kastak Arms",
    "lbco": "Lightning Bolt Co.",
    "volt": "Volt", 
}

BLACKLIST_TYPES = [
    "Dialogue", "Process", "Audio", "Particle", "Animation", "Light", 
    "Mannequin", "Prefab", "Procedural", "Loadout", "SLoadout", 
    "Archetype", "Token", "Character", "AI"
]

# Categories to hide (junk items nobody wants to print)
BLACKLIST_CATEGORIES = {
    "appearance_modifier", "turret_unmanned", "turretunmanned",
    "batteries", "cargogrid", "cooler", "jump_drive", "jumpdrive",
    "power_plant", "powerplant", "quantum_drive", "quantumdrive",
    "self_destruct", "selfdestruct", "shield_generator", "shieldgenerator",
    "fuel_intake", "fuel_tank", "parts", "mounts",
}

# Suffixes to filter out from ship/vehicle/weapon names (AI variants, skins, etc.)
BLACKLIST_SUFFIXES = {
    # AI/NPC variants
    "_ai_", "_pu_", "_override", "_template", "_variant", "_test",
    "_crim", "_sec", "_uee", "_pirate", "_outlaw", "_hostile",
    "_nocrimesagainst", "_civilian", "_npc", "_spawner",
    # Skin/color variants
    "_tint0", "_tint1", "_tint2", "_tint3",
    "_grey0", "_gray0", "_black0", "_white0", "_tan0",
    "_red0", "_blue0", "_green0", "_yellow0", "_purple0", "_orange0", "_pink0",
    "_collector0", "_firerats", "_colortest", "_renegade",
    "_mal0", "_prop", "_iae",
}

# --- 3D PRINT EXTRACTION CONFIG ---
# Parts to KEEP even in personal item loadouts
LOADOUT_WHITELIST = {
    "mag", "canister", "battery", "scope", "attachment", "magazine", 
    "fuel", "utility", "part", "barrel", "grip", "stock", "sight",
}

# Parts to STRIP (junk/stands/crates)
LOADOUT_BLACKLIST = {
    "crate", "stand", "mannequin", "pod", "display", "box", "case", 
    "hanger", "table", "prop_display", "storage", "pallet",
}
# ----------------------------------

# Global Manager
class SCManager:
    def __init__(self):
        self.sc = None
        self.sc_path = None
        self.loading = False
        self._category_cache = None
        self._records_by_path = {}
        self._records_by_manufacturer = defaultdict(lambda: defaultdict(list))
        self._records_by_guid = {}

    def load_sc(self, path: str):
        if self.loading:
            raise HTTPException(status_code=409, detail="Already loading")
        
        self.loading = True
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Path does not exist: {path}")
            
            p4k_path = Path(path) / "Data.p4k"
            if not p4k_path.exists():
                raise FileNotFoundError("Data.p4k not found in path")

            self.sc_path = path
            if StarCitizen:
                self.sc = StarCitizen(path)
                # Initialize Datacore and Localization
                _ = self.sc.datacore
                _ = self.sc.localization 
                print(f"StarCitizen initialized: {self.sc.version_label}")
                self._build_category_cache()
            else:
                print("WARNING: scdatatools not installed, running in MOCK mode.")
                
        except Exception as e:
            print(f"Error loading SC: {e}")
            self.sc = None
            self.sc_path = None
            raise e
        finally:
            self.loading = False

    def _build_category_cache(self):
        """Build category tree from DataCore file paths"""
        print("Building category cache...")
        self._records_by_path = defaultdict(list)
        self._records_by_manufacturer = defaultdict(lambda: defaultdict(list))
        self._records_by_guid = {}
        
        base = "libs/foundry/records/"
        
        for record in self.sc.datacore.records:
            rel_path = record.filename.replace(base, "")
            dir_path = "/".join(rel_path.split("/")[:-1])
            self._records_by_path[dir_path].append(record)
            
            # Index by GUID for export lookup
            self._records_by_guid[str(record.id)] = record
            
            # Group by manufacturer for spaceships/vehicles
            for mfg_path in MANUFACTURER_GROUPED_PATHS:
                if dir_path.startswith(mfg_path) or dir_path == mfg_path:
                    # Filter out AI variants, test units, etc.
                    name_lower = record.name.lower()
                    is_variant = any(suffix in name_lower for suffix in BLACKLIST_SUFFIXES)
                    if is_variant:
                        continue
                    
                    # Extract manufacturer from item name (first part before _)
                    name_parts = name_lower.split("_")
                    if name_parts:
                        mfg = name_parts[0]
                        self._records_by_manufacturer[mfg_path][mfg].append(record)
        
        # Build tree for interesting paths
        tree = []
        for path_prefix, display_name in INTERESTING_PATHS.items():
            if path_prefix in MANUFACTURER_GROUPED_PATHS:
                node = self._build_manufacturer_tree(path_prefix, display_name)
            else:
                node = self._build_tree_node(path_prefix, display_name)
            if node:
                tree.append(node)
        
        self._category_cache = tree
        print(f"Category cache built: {len(tree)} top-level categories, {len(self._records_by_guid)} records indexed")

    def _build_manufacturer_tree(self, path_prefix: str, display_name: str) -> Optional[Dict]:
        """Build tree grouped by manufacturer"""
        manufacturers = self._records_by_manufacturer.get(path_prefix, {})
        if not manufacturers:
            return None
        
        children = []
        for mfg_code in sorted(manufacturers.keys()):
            mfg_name = MANUFACTURER_NAMES.get(mfg_code, mfg_code.upper())
            count = len(manufacturers[mfg_code])
            if count > 0:
                children.append({
                    "name": f"{mfg_name} ({count})",
                    "path": f"{path_prefix}::{mfg_code}",
                    "leaf": True
                })
        
        if children:
            return {"name": display_name, "path": path_prefix, "children": children}
        return None

    def _build_tree_node(self, path_prefix: str, display_name: str, max_depth: int = 4) -> Optional[Dict]:
        """Recursively build a tree node from path prefix"""
        children_dirs = set()
        has_direct_items = False
        
        for dir_path in self._records_by_path.keys():
            if dir_path.startswith(path_prefix) and dir_path != path_prefix:
                # Exclude unwanted flair subcategories
                if "flair" in path_prefix and any(x in dir_path for x in ["/ship", "/origin", "/aegis", "/anvil"]):
                     # Keep specific ones? User said "remove ship subcategory".
                     # If dir_path contains "/ship", skip it, UNLESS it's "vehicle" (bobbleheads are in vehicle)
                     # Wait, user said "vehicle subfolder in flair is fine".
                     # So blacklist "ship" folder under flair.
                     if "/ship" in dir_path and "flair" in dir_path:
                         continue
                
                remainder = dir_path[len(path_prefix):].lstrip("/")
                if remainder:
                    next_level = remainder.split("/")[0]
                    if not next_level.endswith(".xml") and next_level.lower() not in BLACKLIST_CATEGORIES:
                        children_dirs.add(next_level)
            elif dir_path == path_prefix:
                has_direct_items = True
        
        if not children_dirs and not has_direct_items:
            return None
        
        if children_dirs and max_depth > 0:
            children = []
            for child_dir in sorted(children_dirs):
                child_path = f"{path_prefix}/{child_dir}"
                child_display = child_dir.replace("_", " ").title()
                child_node = self._build_tree_node(child_path, child_display, max_depth - 1)
                if child_node:
                    children.append(child_node)
            
            if children:
                return {"name": display_name, "path": path_prefix, "children": children}
            elif has_direct_items:
                return {"name": display_name, "path": path_prefix, "leaf": True}
        elif has_direct_items or children_dirs:
            return {"name": display_name, "path": path_prefix, "leaf": True}
        
        return None

    def is_ready(self):
        return self.sc is not None

    def get_categories(self):
        return self._category_cache or []

    def search_items(self, query: str):
        if not self.sc:
            return []
        
        results = []
        query = query.lower()
        count = 0
        
        
        # Suffixes that indicate a variant
        variant_suffixes = [
            "_tint", "_red", "_blue", "_green", "_yellow", "_black", 
            "_white", "_grey", "_gray", "_purple", "_orange", "_pink",
            "_tan", "_gold", "_silver", "_chrome", "_copper",
            "_wood", "_camo", "_polar", "_desert", "_forest",
            "_executive", "_concierge", "_subscriber", "_dazzle",
            "_digital", "_klibre"
        ]
        
        limit = 200 # Increased limit
        
        
        # Debug introspection counters
        print(f"DEBUG: Searching for '{query}'")

        for record in self.sc.datacore.records:
            name_lower = record.name.lower()
            
            # 1. Filter by Name (Case-insensitive)
            # Must match name OR filename
            match = query in name_lower or query in record.filename.lower()
            if not match:
                continue
                
            # 2. Filter by Type (Junk Removal)
            rec_type = str(record.type)
            if any(junk in rec_type for junk in BLACKLIST_TYPES):
                continue
                
            # 3. Filter by Name Patterns (Junk Removal)
            if "NPC_" in record.name or "Dialogue" in record.name:
                continue

            # 4. Filter Variants (unless query explicitly requests them)
            # If query matches the base name but not the variant suffix, hide it
            is_variant = False
            for suffix in variant_suffixes:
                 if suffix in name_lower and suffix not in query:
                     is_variant = True
                     break
            if is_variant:
                continue

            # 5. Localization (Get Real Name)
            display_name = record.name # Default to internal name
            label = ""
            
            if hasattr(self.sc, 'localization'):
                # Try properties for localization key
                # Common keys: Name, Display, Item Name
                loc_key = ""
                if hasattr(record, 'properties'):
                    props = record.properties
                    loc_key = props.get('Name') or props.get('Display') or props.get('Item Name') or props.get('@Name')
                
                # If key starts with @, localize it
                if loc_key and isinstance(loc_key, str) and loc_key.startswith('@'):
                    label = self.sc.localization.gettext(loc_key)
            
            # If we found a localized label, use it as primary name
            # But keep internal name for reference
            if label and label != loc_key:
                final_name = label
                subtitle = record.name
            else:
                final_name = record.name
                subtitle = record.filename

            results.append({
                "id": str(record.id),
                "name": final_name,           # Localized "Behring P4-AR"
                "internal_name": record.name, # "behr_rifle_ballistic_01"
                "type": rec_type,
                "thumbnail": None
            })
            count += 1
            if count >= limit:
                break
        
        return results

    def get_items_by_path(self, category_path: str):
        """Get items for a specific category path, deduplicated by base name"""
        if not self.sc:
            return []
        
        # Check for manufacturer-grouped path
        if "::" in category_path:
            base_path, mfg_code = category_path.split("::", 1)
            records = self._records_by_manufacturer.get(base_path, {}).get(mfg_code, [])
            return [
                {"id": str(r.id), "name": r.name, "thumbnail": None, "type": r.type, "filename": r.filename}
                for r in records[:200]
            ]
        
        results = []
        count = 0
        seen_base_names = set()  # Track unique base names for deduplication
        
        # Suffixes that indicate a variant/skin (won't affect geometry)
        variant_suffixes = [
            "_tint", "_red", "_blue", "_green", "_yellow", "_black", 
            "_white", "_grey", "_gray", "_purple", "_orange", "_pink",
            "_tan", "_gold", "_silver", "_chrome", "_copper",
            "_wood", "_camo", "_polar", "_desert", "_forest",
            "_executive", "_concierge", "_subscriber", "_dazzle",
            "_digital", "_klibre"
        ]
        
        import re

        for dir_path, records in self._records_by_path.items():
            if dir_path.startswith(category_path) or dir_path == category_path:
                for record in records:
                    # Variant Filter by color suffix
                    name_lower = record.name.lower()
                    is_variant = any(s in name_lower for s in variant_suffixes)
                    if is_variant:
                        continue
                    
                    # Name-based deduplication: strip trailing _01, _02, etc.
                    # Pattern: NAME_XX where XX is 2 digits at end
                    base_name = re.sub(r'_\d{2}$', '', record.name)
                    
                    # Also strip common texture variant suffixes like _a, _b, _c
                    base_name = re.sub(r'_[a-c]$', '', base_name, flags=re.IGNORECASE)
                    
                    if base_name in seen_base_names:
                        # Already have an item with this base name, skip
                        continue
                    seen_base_names.add(base_name)
                        
                    results.append({
                        "id": str(record.id),
                        "name": record.name,
                        "thumbnail": None,
                        "type": record.type,
                        "filename": record.filename
                    })
                    count += 1
                    if count >= 200:
                        break
            if count >= 200:
                break
        
        return results

    def get_record_by_guid(self, guid: str):
        """Get a record by its GUID"""
        return self._records_by_guid.get(guid)

    def export_item(self, guid: str) -> Dict[str, Any]:
        """Export an item to OBJ/DAE format"""
        if not self.sc or not geometry_for_record:
            raise Exception("SC not loaded or scdatatools not available")
        
        record = self.get_record_by_guid(guid)
        if not record:
            raise Exception(f"Record not found: {guid}")
        
        print(f"Exporting: {record.name}")
        
        # Get geometry info
        try:
            geo_dict = geometry_for_record(record, data_root=self.sc.p4k)
        except Exception as e:
            raise Exception(f"Failed to get geometry: {e}")
            
        if not geo_dict:
             raise Exception("No geometry found for this item")

        # Get the best geometry - prefer actual model geometry over display props
        # Priority: Male > Female > heldEntity > '' (base) > others > tableDisplay (worst)
        # Avoid anything with 'crate' in the path!
        
        # Debug: show all available geometries
        print(f"Available geometry tags: {list(geo_dict.keys())}")
        for tag, geo in geo_dict.items():
            path = geo.filename if hasattr(geo, 'filename') else str(geo)
            print(f"  '{tag}': {path}")
        
        # Robust Geometry Selection
        # We want a static mesh (CGF/CGA) that represents the item itself.
        # We want to avoid:
        # 1. Crates/Boxes (often in '' or tableDisplay)
        # 2. Skinned meshes (.skin) which compile to empty OBJs without a skeleton
        # 3. Mannequins
        
        # Priority tags generally containing the 'prop' version
        PRIORITY_TAGS = ['inventoryStoredEntity', 'tableDisplay', 'heldEntity']
        FALLBACK_TAGS = ['Male', 'Female', '']
        all_tags = PRIORITY_TAGS + FALLBACK_TAGS
        
        def get_geo_score(tag, path_str):
            score = 0
            path_lower = path_str.lower()
            
            # Penalties
            if '_display' in path_lower: score -= 500  # Display files are placeholders, not full models
            if 'crate' in path_lower: score -= 100   # Crates are not the item
            if 'mannequin' in path_lower: score -= 100
            
            # Bonuses
            if tag in PRIORITY_TAGS: score += 100
            if '_prop' in path_lower: score += 50    # Explicit "prop" files are usually good
            if '.skin' in path_lower: score += 30    # SKIN files have full animated mesh (cgf-converter v2.0 supports these)
            if '.cga' in path_lower: score += 20     # CGA is usually high quality
            if '.cgf' in path_lower: score += 10     # CGF is standard static mesh
            if '.cdf' in path_lower: score += 5      # CDF is complex but often correct (we handle it now)
            
            return score

        # Score all options
        scored_geos = []
        print(f"Geometry candidates:")
        for tag, geo in geo_dict.items():
            if hasattr(geo, 'filename'):
                path_str = geo.filename
            else:
                path_str = str(geo)
            
            s = get_geo_score(tag, path_str)
            scored_geos.append((s, tag, geo))
            print(f"  [{s:>4}] {tag}: {path_str}")
            
        # Select best
        scored_geos.sort(key=lambda x: x[0], reverse=True)
        
        if scored_geos:
            selected_geo = scored_geos[0][2]
            print(f"Selected geometry: {selected_geo.filename if hasattr(selected_geo, 'filename') else selected_geo} (Score: {scored_geos[0][0]})")
        
        geo_info = selected_geo
        if not geo_info:
            raise Exception("No valid geometry info found")
        
        geo_filename = geo_info.filename if hasattr(geo_info, 'filename') else geo_info
        print(f"Final geometry file: {geo_filename}")
        # Create output directory for this export
        safe_name = record.name.replace("/", "_").replace("\\", "_")
        safe_name_clean = "".join(c for c in safe_name if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_name_clean = safe_name_clean.replace(" ", "_").lower()
        
        export_path = EXPORT_DIR / safe_name_clean
        export_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # --- ROBUST EXTRACTION STRATEGY ---
            # 1. Identify parent directory of the geometry file
            cgf_path_obj = Path(geo_filename)
            
            # 2. Handle CDF files (Character Definition Files) - they are XML containers!
            #    CDF files reference actual CGF geometry via Model/@File attribute
            actual_geom_path = cgf_path_obj
            if cgf_path_obj.suffix.lower() == ".cdf":
                print(f"Detected CDF file, parsing to find actual geometry...")
                try:
                    # Read the CDF from P4K and parse as XML
                    cdf_content = self.sc.p4k.read(geo_info.filename)
                    
                    # Parse XML - CDF files are CryXML (binary) or plain XML
                    import xml.etree.ElementTree as ET
                    try:
                        root = ET.fromstring(cdf_content)
                    except ET.ParseError:
                        # CryXML binary format - use scdatatools to parse
                        from scdatatools.engine.cryxml import etree_from_cryxml_file
                        from io import BytesIO
                        root = etree_from_cryxml_file(BytesIO(cdf_content))
                        model_elem = root.find(".//Model")
                        if model_elem is not None:
                            model_file = model_elem.get("File", "")
                            if model_file:
                                actual_geom_path = Path(model_file)
                                # Fix path prefix: Ensure it starts with Data/ if it's Objects/
                                if actual_geom_path.parts[0].lower() == 'objects':
                                    actual_geom_path = Path("Data") / actual_geom_path
                                print(f"CDF resolved to: {actual_geom_path}")
                    else:
                        # Plain XML - find Model element
                        model_elem = root.find(".//Model")
                        if model_elem is not None:
                            model_file = model_elem.get("File", "")
                            if model_file:
                                actual_geom_path = Path(model_file)
                                # Fix path prefix
                                if actual_geom_path.parts[0].lower() == 'objects':
                                    actual_geom_path = Path("Data") / actual_geom_path
                                print(f"CDF resolved to: {actual_geom_path}")
                except Exception as e:
                    print(f"Warning: Failed to parse CDF, using original path: {e}")
            
            # 2b. If resolved path is a Skeleton (.chr), looks for geometry instead
            if actual_geom_path.suffix.lower() == ".chr":
                 print(f"CDF pointed to skeleton (.chr), searching for geometry in {actual_geom_path.parent}...")
                 # Ensure we search in the right P4K path
                 parent_search = actual_geom_path.parent.as_posix()
                 candidates = self.sc.p4k.search(f"{parent_search}/*")
                 
                 # Look for geometry files: .skin (animated mesh), .cga, .cgf
                 # IMPORTANT: Exclude _display files (placeholders) and _lod files
                 geom_candidates = []
                 for f in candidates:
                     fname = f.filename.lower()
                     # Skip display/lod/proxy files
                     if '_display' in fname or '_lod' in fname or '_proxy' in fname:
                         continue
                     if fname.endswith(('.skin', '.cga', '.cgf')):
                         geom_candidates.append(f)
                 
                 # Priority order: .skin > .cga > .cgf (skins have the actual animated mesh)
                 skin_cands = [f for f in geom_candidates if f.filename.lower().endswith('.skin')]
                 cga_cands = [f for f in geom_candidates if f.filename.lower().endswith('.cga')]
                 cgf_cands = [f for f in geom_candidates if f.filename.lower().endswith('.cgf')]
                 
                 if skin_cands:
                     actual_geom_path = Path(skin_cands[0].filename)
                     print(f"Found substitute geometry (SKIN): {actual_geom_path}")
                 elif cga_cands:
                     actual_geom_path = Path(cga_cands[0].filename)
                     print(f"Found substitute geometry (CGA): {actual_geom_path}")
                 elif cgf_cands:
                     actual_geom_path = Path(cgf_cands[0].filename)
                     print(f"Found substitute geometry (CGF): {actual_geom_path}")
                 else:
                     print("Warning: CDF pointed to CHR and no valid geometry found in folder.")

            
            # 3. If it's a .cgf, check if there's a higher quality .cga version
            if actual_geom_path.suffix.lower() == ".cgf":
                cga_path = actual_geom_path.with_suffix(".cga")
                if f"Data/{cga_path.as_posix()}".lower() in [f.filename.lower() for f in self.sc.p4k.search(f"{cga_path.parent.as_posix()}/*")]:
                    print(f"Found CGA version, using: {cga_path}")
                    actual_geom_path = cga_path
            
            parent_dir = actual_geom_path.parent.as_posix()
            
            # 4. Extract ALL relevant files in that directory (textures, materials, CGFs)
            print(f"Extracting all files from: {parent_dir}")
            files_to_extract = self.sc.p4k.search(f"{parent_dir}/*")
            print(f"Found {len(files_to_extract)} dependent files")
            
            for f in files_to_extract:
                # Extract maintaining relative structure inside export_path
                dest = export_path / f.filename
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    dest.write_bytes(self.sc.p4k.read(f.filename))
                except Exception as e:
                    print(f"Warning: Failed to extract {f.filename}: {e}")

            # 5. Path to the extracted CGF (use actual_geom_path, not original)
            cgf_local_path = export_path / f"Data/{actual_geom_path.as_posix()}"
            
            # If the actual geom path doesn't include 'Data/', adjust
            if not cgf_local_path.exists():
                cgf_local_path = export_path / actual_geom_path
            
        except Exception as e:
             raise Exception(f"Failed to extract item files: {e}")

        # Convert using cgf-converter (DAE mode for reliable geometry)
        if not CGF_CONVERTER.exists():
            raise Exception(f"cgf-converter not found at {CGF_CONVERTER}")
        
        print(f"Running cgf-converter (DAE mode) on {cgf_local_path}")
        
        try:
            # Use -dae flag for Collada output (more reliable than direct -obj)
            # Use the export path as objectdir to resolve materials correctly
            obj_dir = export_path
            
            result = subprocess.run(
                [str(CGF_CONVERTER), str(cgf_local_path), "-dae", "-objectdir", str(obj_dir), "-notex"],
                capture_output=True,
                text=True,
                timeout=300, # Give it time
                check=False
            )
            print(f"cgf-converter output: {result.stdout}")
            if result.returncode != 0:
                print(f"cgf-converter error output: {result.stderr}")
                raise Exception(f"Converter failed with code {result.returncode}")

        except subprocess.TimeoutExpired:
            raise Exception("Conversion timed out")
        except Exception as e:
            raise Exception(f"Conversion failed: {e}")
        
        # Locate the generated DAE file (using DAE format for SC 4.5 compatibility)
        dae_file = cgf_local_path.with_suffix('.dae')
        
        # If not found, search recursively in export path
        if not dae_file.exists():
            print(f"DAE not found at expected path {dae_file}, scanning...")
            daes = list(export_path.rglob("*.dae"))
            if daes:
                dae_file = daes[0]
                print(f"Found DAE: {dae_file}")
            else:
                raise Exception("No DAE file generated by converter")
        
        print(f"DAE generated at: {dae_file} (Size: {dae_file.stat().st_size} bytes)")
        
        # Post-Processing: Load DAE (Collada) file
        try:
            print("Loading DAE mesh...")
            
            # Load DAE with Trimesh
            mesh = trimesh.load(dae_file, force='scene')
            
            # --- ASSEMBLY SYSTEM ---
            try:
                print("Running Assembly System...")
                assembler = BlueprintAssembler(self, CGF_CONVERTER)
                mesh = assembler.assemble(record, mesh, export_path)
                mesh = assembler.rotate_for_export(mesh)
            except Exception as e:
                print(f"Assembly System Warning: {e}")
            # -----------------------

            # Smart Merge / LOD Filtering
            # The exported DAE often contains multiple LODs (Level of Detail) superimposed.
            # CRITICAL FIX: We must respect the scene transforms!
            # Previously we just grabbed geometries, which collapsed everything to (0,0,0).
            # This caused "jumbled" ships and false-positive LOD filtering (because everything overlapped).
            
            if isinstance(mesh, trimesh.Scene):
                # Apply transforms and flatten the scene, but keep individual geometries for analysis if possible?
                # trimesh.scenes.scene.Scene.dump(concatenate=False) returns a list of meshes with transforms applied!
                # This is perfect for our LOD filtering.
                
                # Use dump to get consistent meshes with transforms applied
                meshes_with_transforms = mesh.dump(concatenate=False)
                
                candidates = []
                for idx, m in enumerate(meshes_with_transforms):
                    if isinstance(m, trimesh.Trimesh):
                        # Skip empty meshes
                        if len(m.vertices) == 0:
                            continue
                        
                        # Try to get name from metadata
                        name = m.metadata.get('name', f'Mesh_{idx}') if m.metadata else f'Mesh_{idx}'
                            
                        candidates.append({
                            'name': name,
                            'geom': m,
                            'vertices': len(m.vertices),
                            # Use bounding box center of the TRANSFORMED mesh
                            'center': m.bounds.mean(axis=0), 
                            'extents': m.extents
                        })
                
                # Sort by vertex count descending (High detail first)
                candidates.sort(key=lambda x: x['vertices'], reverse=True)
                
                print(f"LOD Processing: {len(candidates)} candidate meshes")
                
                final_meshes = []
                for i, c1 in enumerate(candidates):
                    # Filter tiny junk (physics proxies, locators)
                    # Lowered threshold to 10 to clear buttons/switches but keep small detail
                    if c1['vertices'] < 10:
                        print(f"  [Drop] Mesh {i} ({c1['vertices']} verts): Too small (<10)")
                        continue
                        
                    is_lod = False
                    reason = ""
                    
                    # Calculate characteristic size (diagonal of bounding box)
                    size_c1 = np.linalg.norm(c1['extents'])
                    
                    name_lower = c1['name'].lower()
                    
                    # 1. Negative Filter: Explicit Logic/Physics/Proxy meshes
                    if "proxy" in name_lower or "$physics" in name_lower or "_lod" in name_lower:
                        print(f"  [Drop] Mesh {i} '{c1['name']}': Name indicates Proxy/LOD")
                        continue
                        
                    # 2. Positive Filter: Always keep Glass, Guts (Interiors), Details, Doors
                    if "glass" in name_lower or "guts" in name_lower or "interior" in name_lower or "door" in name_lower and "proxy" not in name_lower:
                         final_meshes.append(c1)
                         print(f"  [Keep] Mesh {i} '{c1['name']}' ({c1['vertices']} verts, Size: {size_c1:.2f}) [Keyword Kept]")
                         continue

                    # Check against already kept meshes for overlapping LODs
                    for c2 in final_meshes:
                        size_c2 = np.linalg.norm(c2['extents'])
                        
                        # Distance between centers
                        dist = np.linalg.norm(c1['center'] - c2['center'])
                        
                        # Relative Tolerance: 1% of the LARGER object's size
                        # If centers are this close, they share origin/position.
                        max_size = max(size_c1, size_c2, 0.1) # Avoid div/0
                        rel_dist = dist / max_size
                        
                        # Size Similarity: Are they roughly the same scale? (within 2%)
                        # LODs are usually almost identical in box size (<1.5% diff).
                        # Distinct parts (like Canopy Glass vs Frame) are often >3% different.
                        size_diff = abs(size_c1 - size_c2)
                        rel_size_diff = size_diff / max_size
                        
                        if rel_dist < 0.01: # Centers are very close (relative to size)
                             if rel_size_diff < 0.02: # Sizes are within 2% (Very strict)
                                 is_lod = True
                                 reason = f"Overlaps with Mesh {final_meshes.index(c2)} '{c2['name']}' (Dist: {dist:.3f}, SizeDiff: {size_diff:.3f})"
                                 break
                    
                    if not is_lod:
                        final_meshes.append(c1)
                        print(f"  [Keep] Mesh {i} '{c1['name']}' ({c1['vertices']} verts, Size: {size_c1:.2f})")
                    else:
                        print(f"  [Drop] Mesh {i} '{c1['name']}' ({c1['vertices']} verts): {reason}")
                
                if final_meshes:
                    print(f"LOD Filter: Kept {len(final_meshes)}/{len(candidates)} meshes")
                    # Concatenate the kept meshes (they already have transforms applied from dump())
                    mesh = trimesh.util.concatenate([c['geom'] for c in final_meshes])
                else:
                    # Fallback: If we filtered everything (e.g. everything was < 10 verts?), keep the largest one at least
                    if candidates:
                        print("Warning: LOD Filter removed all geometry. Forcing keep of largest mesh.")
                        mesh = candidates[0]['geom']
                    else:
                         raise Exception("LOD Filter: Input DAE contained no valid meshes.")
            
            # Align: User asked for centered axis (Center the final result)
            mesh.apply_translation(-mesh.centroid)
            
            # Rotate to face viewer: Z-up to Y-up (+90° X), then 180° Y to face front
            rotation_x = trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0])
            rotation_y = trimesh.transformations.rotation_matrix(np.radians(180), [0, 1, 0])
            mesh.apply_transform(rotation_x)
            mesh.apply_transform(rotation_y)
            
            # Force matte white material for clean 3D print preview
            mesh.visual = trimesh.visual.ColorVisuals(mesh, face_colors=[200, 200, 200, 255])
            
            # Export clean OBJ
            final_obj_path = export_path / f"{safe_name_clean}.obj"
            mesh.export(str(final_obj_path))
            
            # Export GLB for Web Preview
            final_glb_path = export_path / f"{safe_name_clean}.glb"
            try:
                # Trimesh exports GLB easily
                mesh.export(str(final_glb_path))
            except Exception as e:
                print(f"GLB Export failed (Preview will be unavailable): {e}")
            
            print(f"OBJ export complete: {final_obj_path} (Size: {final_obj_path.stat().st_size} bytes)")
            

            # Optional: delete original DAE? User might want it, but we promised OBJ
            # dae_file.unlink(missing_ok=True) 
            
            final_output = final_obj_path
            
        except Exception as e:
            print(f"Conversion to OBJ failed: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"OBJ Conversion failed: {e}")
            
        return {
            "status": "success",
            "name": record.name,
            "output_file": str(final_output),
            "preview_url": f"/api/download/{safe_name_clean}/{final_glb_path.name}" if final_glb_path.exists() else None,
            "download_url": f"/api/download/{safe_name_clean}/{final_output.name}"
        }

    def export_item_blueprint(self, guid: str) -> Dict[str, Any]:
        """
        Export an item using the scdatatools Blueprint API.
        This properly handles complex assets like ships with landing gear.
        """
        import time
        start_time = time.time()
        
        def log_progress(step: int, total_steps: int, message: str):
            elapsed = time.time() - start_time
            print(f"[Blueprint Export] [{elapsed:6.1f}s] Step {step}/{total_steps}: {message}")
        
        if not self.sc or not blueprint_from_datacore_entity:
            raise Exception("SC not loaded or Blueprint API not available")
        
        record = self.get_record_by_guid(guid)
        if not record:
            raise Exception(f"Record not found: {guid}")
        
        log_progress(1, 5, f"Starting export of {record.name}")
        
        # Create output directory
        safe_name = record.name.replace("/", "_").replace("\\", "_")
        safe_name_clean = "".join(c for c in safe_name if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_name_clean = safe_name_clean.replace(" ", "_").lower()
        
        export_path = EXPORT_DIR / safe_name_clean
        export_path.mkdir(parents=True, exist_ok=True)
        
        # 1. Generate Blueprint from record
        log_progress(1, 5, "Generating blueprint (analyzing ship components)...")
        
        file_count = [0]  # Use list to allow modification in nested function
        def monitor(msg, progress=None, total=None, level=None, exc_info=None):
            import logging
            level = level or logging.INFO
            if "file ex:" in str(msg).lower() or "+ file" in str(msg).lower():
                file_count[0] += 1
                if file_count[0] % 100 == 0:
                    elapsed = time.time() - start_time
                    print(f"[Blueprint Export] [{elapsed:6.1f}s]   ...processed {file_count[0]} files")
            elif level >= logging.WARNING:
                print(f"  [BP] {msg}")
        
        try:
            bp = blueprint_from_datacore_entity(self.sc, record, monitor=monitor)
            
            # Detect item type from file path (more reliable than property checks)
            # Ships/Vehicles: entities/spaceships/... or entities/groundvehicles/...
            # Personal Items: entities/scitem/... (armor, weapons, gadgets, etc.)
            record_path = record.filename.lower()
            is_vehicle = 'entities/spaceships' in record_path or 'entities/groundvehicles' in record_path
            
            # CATEGORY-BASED ROUTING:
            # Simple items use the legacy export (single mesh file) - Armor, Melee, Flair, Gadgets, etc.
            # Only FPS Weapons (complex multi-part) use the new assembly pipeline
            is_armor = '/armor/' in record_path or '/characters/human/armor' in record_path
            is_melee = '/melee/' in record_path
            is_flair = '/flair/' in record_path
            is_gadget = '/gadgets/' in record_path
            is_mining = '/mining/' in record_path
            is_food = '/food/' in record_path
            is_decor = '/decorations/' in record_path
            
            is_simple_item = is_armor or is_melee or is_flair or is_gadget or is_mining or is_food or is_decor
            
            if is_simple_item:
                print(f"[Blueprint Export] Detected simple item (armor/food/decor). Proceeding with blueprint auto-conversion.")
            
            # Let scdatatools handle extraction - it knows what parts belong to this item
            # No manual loadout filtering needed
                
            log_progress(2, 5, f"Blueprint generated: {len(bp.hardpoints)} hardpoints, {len(bp.geometry)} geometry entries")
            
            # DEBUG: Inspect Blueprint Geometry structure
            if len(bp.geometry) > 0:
                print(f"[DEBUG] bp.geometry keys: {list(bp.geometry.keys())}")
                first_key = list(bp.geometry.keys())[0]
                sample = bp.geometry[first_key]
                print(f"[DEBUG] Sample geom '{first_key}': {sample}")
                # Check for standard attributes
                for attr in ['transform', 'local_transform', 'world_transform', 'pos', 'rot', 'position', 'rotation', 'scale']:
                     if hasattr(sample, attr):
                         print(f"[DEBUG] Has attr '{attr}': {getattr(sample, attr)}")
                     elif isinstance(sample, dict) and attr in sample:
                         print(f"[DEBUG] Has dict key '{attr}': {sample[attr]}")
                         
        except Exception as e:
            print(f"[Blueprint Export] Blueprint generation failed: {e}")
            # Fall back to legacy method
            return self.export_item(guid)
        
        # 2. Extract assets WITH auto-conversion (like StarFab does)
        # scdatatools' built-in conversion works with SC 4.5
        log_progress(2, 5, "Extraction & Conversion (scdatatools)...")
        try:
            # Let scdatatools handle the conversion - it works with SC 4.5
            bp.extract(
                outdir=export_path,
                monitor=monitor,
                auto_convert_models=True,  # Enable scdatatools' internal conversion
                cgf_converter_bin=str(CGF_CONVERTER),  # Provide path to converter
                skip_lods=True,
            )
            
        except Exception as e:
            print(f"[Blueprint Export] Extraction failed: {e}")
            return self.export_item(guid)
        
        # 3. Manual Batch Conversion & Assembly
        merged_meshes = []
        
        # Check if blueprint has geometry
        if not bp.geometry:
            print("[Blueprint Export] No geometry in blueprint. Falling back to legacy.")
            return self.export_item(guid)

        # Helper to convert single file (using DAE for SC 4.5 compatibility)
        def convert_to_dae(rel_path):
            # Try multiple path variations
            # bp.geometry keys are like "objects/..." but extraction puts files in "Data/Objects/..."
            candidates = [
                export_path / rel_path,
                export_path / "Data" / rel_path,
                export_path / rel_path.replace("objects/", "Objects/"),
                export_path / "Data" / rel_path.replace("objects/", "Objects/"),
            ]
            
            src_file = None
            for c in candidates:
                if c.exists():
                    src_file = c
                    break
            
            if not src_file:
                return None
                
            dae_file = src_file.with_suffix(".dae")
            if dae_file.exists():
                return dae_file
            
            # Convert using DAE format (works with SC 4.5)
            cmd = [str(CGF_CONVERTER), str(src_file), "-dae", "-objectdir", str(export_path), "-notex"]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                if dae_file.exists():
                    return dae_file
            except:
                pass
            return None

        print(f"[Blueprint Export] Processing {len(bp.geometry)} geometry entries...")
        
        for geom_key, geom_data in bp.geometry.items():
            # Filter unwanted types
            key_lower = geom_key.lower()
            if any(x in key_lower for x in ["proxy", "physics", "$helper", "_lod"]):
                continue
                
            # Convert to DAE (using Collada format for SC 4.5 compatibility)
            dae_path = convert_to_dae(geom_key)
            if not dae_path:
                print(f"  [Warning] Missing or failed conversion: {geom_key}")
                continue
                
            try:
                # Load DAE
                mesh = trimesh.load(dae_path, force='scene')
                
                # Apply Transform
                # Use world_transform if available, else local? map to identity?
                # Usually we want the relative transform to the root
                # geom_data in scdatatools usually has 'transform' matrix
                transform = np.eye(4)
                if hasattr(geom_data, 'transform'):
                    transform = np.array(geom_data.transform).reshape(4,4)
                
                # Convert Scene to single Trimesh if needed
                if isinstance(mesh, trimesh.Scene):
                    # Apply transform to scene, then convert to single mesh
                    mesh.apply_transform(transform)
                    # Dump all geometry and concatenate into single mesh
                    geometries = list(mesh.geometry.values())
                    if geometries:
                        mesh = trimesh.util.concatenate(geometries)
                    else:
                        print(f"  [Warning] Scene has no geometry: {geom_key}")
                        continue
                elif isinstance(mesh, trimesh.Trimesh):
                    mesh.apply_transform(transform)
                else:
                    print(f"  [Warning] Unknown mesh type: {type(mesh)}")
                    continue
                    
                merged_meshes.append(mesh)
            except Exception as e:
                print(f"  [Error] Failed to load/transform {geom_key}: {e}")

        log_progress(4, 5, f"Assembled {len(merged_meshes)} meshes. Merging...")

        if not merged_meshes:
            raise Exception("Assembly resulted in 0 meshes. No valid parts found.")
        
        # 5. Concatenate meshes
        log_progress(4, 5, f"Combining {len(merged_meshes)} sub-meshes into single model...")
        if len(merged_meshes) == 1:
            final_mesh = merged_meshes[0]
        else:
            final_mesh = trimesh.util.concatenate(merged_meshes)
        
        # 5b. Auto-center the mesh (translate so bounding box center is at origin)
        bounds = final_mesh.bounds  # [[min_x, min_y, min_z], [max_x, max_y, max_z]]
        center = (bounds[0] + bounds[1]) / 2
        final_mesh.apply_translation(-center)
        
        # 6. Apply rotation for export (Z-up to Y-up)
        rotation = trimesh.transformations.rotation_matrix(
            angle=np.radians(-90),
            direction=[1, 0, 0],
            point=[0, 0, 0]
        )
        final_mesh.apply_transform(rotation)
        
        # Force matte white material for clean 3D print preview
        final_mesh.visual = trimesh.visual.ColorVisuals(final_mesh, face_colors=[200, 200, 200, 255])
        
        log_progress(5, 5, f"Exporting final mesh ({len(final_mesh.vertices):,} vertices, {len(final_mesh.faces):,} faces)...")
        
        # 7. Export OBJ and GLB
        final_obj_path = export_path / f"{safe_name_clean}.obj"
        final_glb_path = export_path / f"{safe_name_clean}.glb"
        
        final_mesh.export(str(final_obj_path))
        
        # --- POST-PROCESS: Force Strip Materials for 3D Printing ---
        try:
            if final_obj_path.exists():
                lines = final_obj_path.read_text().splitlines()
                # Remove mtllib and usemtl lines
                clean_lines = [l for l in lines if not l.startswith(('mtllib', 'usemtl'))]
                final_obj_path.write_text('\n'.join(clean_lines))
                # Delete the .mtl file if it was created
                mtl_path = final_obj_path.with_suffix('.mtl')
                if mtl_path.exists():
                    mtl_path.unlink()
                print(f"[Blueprint Export] Cleaned OBJ: Stripped material/texture references.")
        except Exception as e:
            print(f"  Warning: Failed to clean OBJ materials: {e}")
        # ------------------------------------------------------------
        
        try:
            final_mesh.export(str(final_glb_path))
        except Exception as e:
            print(f"[Blueprint Export] GLB export failed: {e}")
        
        elapsed = time.time() - start_time
        print(f"[Blueprint Export] [{elapsed:6.1f}s] COMPLETE! OBJ: {final_obj_path.stat().st_size:,} bytes")
        
        return {
            "status": "success",
            "name": record.name,
            "output_file": str(final_obj_path),
            "preview_url": f"/api/download/{safe_name_clean}/{final_glb_path.name}" if final_glb_path.exists() else None,
            "download_url": f"/api/download/{safe_name_clean}/{final_obj_path.name}"
        }

manager = SCManager()

# Data Models
class PathRequest(BaseModel):
    path: str

# API Endpoints

@app.get("/api/status")
async def get_status():
    return {
        "configured": manager.is_ready(),
        "sc_path": manager.sc_path,
        "version": manager.sc.version_label if manager.sc else None,
        "loading": manager.loading
    }

@app.post("/api/set-path")
async def set_path(request: PathRequest):
    print(f"Setting path to: {request.path}")
    try:
        await asyncio.to_thread(manager.load_sc, request.path)
        return {"status": "ok", "sc_path": manager.sc_path}
    except Exception as e:
        print(f"Failed to set path: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/categories")
async def get_categories():
    return {"categories": manager.get_categories()}

# ... (Imports at top)
from PIL import Image
import io

# ... (Existing code)

# Helper for thumbnail extraction
def _extract_thumbnail(manager, record_id: str) -> Optional[Path]:
    """Extracts and converts thumbnail for a record."""
    if not manager.sc: return None
    
    # Check cache first
    cache_path = CACHE_DIR / f"{record_id}.png"
    if cache_path.exists():
        return cache_path

    record = manager.get_record_by_guid(record_id)
    if not record: return None
    
    # Try to find icon path from P4K
    icon_path_str = None
    if hasattr(record, 'properties'):
        # Check explicit Icon property (common in NPCs/Armor)
        if 'Icon' in record.properties:
            icon_path_str = record.properties['Icon']
        # Check UI property (Ships)
        elif 'UI' in record.properties and 'icon' in record.properties['UI']:
            icon_path_str = record.properties['UI']['icon']
    
    # Open from P4K if icon path exists
    if icon_path_str:
        try:
            # P4K paths often don't have extension in property, or differ
            # icon_path_str might be "UI/Textures/Icons/..."
            # We need to find the actual file.
            # Often TIF or DDS.
            
            # Search for exact match or roughly match
            # If path has no extension, assume .tif or .dds
            candidates = []
            if "." not in icon_path_str.split("/")[-1]:
                 candidates = [f"{icon_path_str}.tif", f"{icon_path_str}.dds"]
            else:
                 candidates = [icon_path_str]
                 
            # Add Data/ prefix if missing? 
            # SC paths are often relative to Data/
            final_candidates = []
            for c in candidates:
                final_candidates.append(c)
                if not c.lower().startswith("data/"):
                    final_candidates.append(f"Data/{c}")
            
            image_data = None
            for path in final_candidates:
                 try:
                     image_data = manager.sc.p4k.read(path)
                     if image_data: break
                 except:
                     pass
                     
            if image_data:
                # Convert using PIL
                img = Image.open(io.BytesIO(image_data))
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(cache_path, "PNG")
                return cache_path
                
        except Exception as e:
            print(f"Thumbnail P4K extraction failed for {record.name}: {e}")
    
    # Fallback: Try to render from exported GLB
    try:
        # Check if there's an exported GLB for this item
        safe_name = record.name.replace("/", "_").replace("\\", "_")
        safe_name_clean = "".join(c for c in safe_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(" ", "_").lower()
        glb_path = EXPORT_DIR / safe_name_clean / f"{safe_name_clean}.glb"
        
        if glb_path.exists():
            thumb = generate_thumbnail(glb_path, record_id)
            if thumb:
                return thumb
    except Exception as glb_e:
        print(f"Thumbnail GLB render failed for {record.name}: {glb_e}")
    
    # Final fallback: Create a placeholder thumbnail
    try:
        from PIL import Image, ImageDraw, ImageFont
        cache_path = CACHE_DIR / f"{record_id}.png"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a dark placeholder image with item name
        img = Image.new('RGB', (256, 256), color=(30, 41, 59))  # Slate-800
        draw = ImageDraw.Draw(img)
        
        # Draw a simple cube icon
        cx, cy = 128, 100
        size = 30
        
        # Front face
        draw.rectangle([cx - size, cy - size//2, cx + size//2, cy + size], outline=(100, 116, 139), width=2)
        # Top edges  
        draw.line([(cx - size, cy - size//2), (cx - size//2, cy - size)], fill=(100, 116, 139), width=2)
        draw.line([(cx + size//2, cy - size//2), (cx + size, cy - size)], fill=(100, 116, 139), width=2)
        draw.line([(cx - size//2, cy - size), (cx + size, cy - size)], fill=(100, 116, 139), width=2)
        # Right edges
        draw.line([(cx + size//2, cy + size), (cx + size, cy + size//2)], fill=(100, 116, 139), width=2)
        draw.line([(cx + size, cy - size), (cx + size, cy + size//2)], fill=(100, 116, 139), width=2)
        
        # Draw item name at bottom (truncated)
        name = record.name[:20] + "..." if len(record.name) > 20 else record.name
        try:
            # Try to center text
            bbox = draw.textbbox((0, 0), name)
            text_width = bbox[2] - bbox[0]
            draw.text(((256 - text_width) // 2, 180), name, fill=(148, 163, 184))  # Slate-400
        except:
            draw.text((20, 180), name, fill=(148, 163, 184))
        
        img.save(cache_path, 'PNG')
        print(f"[Thumbnail] Created placeholder for: {record.name}")
        return cache_path
    except Exception as placeholder_e:
        print(f"Thumbnail placeholder failed for {record.name}: {placeholder_e}")
    
    return None


@app.get("/api/thumbnail/{item_id}")
async def get_thumbnail(item_id: str):
    """Serve cached thumbnail or return 404. Thumbnails are only generated via the generate-thumbnails endpoint."""
    # Simply check if thumbnail exists in cache and serve it
    thumb_path = CACHE_DIR / f"{item_id}.png"
    
    if thumb_path.exists():
        return FileResponse(thumb_path, media_type="image/png")
    else:
        # No thumbnail exists - return 404, let frontend show placeholder icon
        raise HTTPException(status_code=404, detail="No thumbnail")

class ThumbnailGenerateRequest(BaseModel):
    path: str  # Category path like "entities/scitem/characters/human/armor"

@app.post("/api/generate-thumbnails")
async def generate_thumbnails_for_category(request: ThumbnailGenerateRequest):
    """Generate thumbnails for all items in a category by exporting then rendering."""
    if not manager.is_ready():
        raise HTTPException(status_code=400, detail="SC not loaded")
    
    path = request.path
    items = manager.get_items_by_path(path)
    
    generated = 0
    failed = 0
    skipped = 0
    
    for item in items:
        item_id = item.get('id')
        if not item_id:
            continue
        
        # Check if we already have a REAL thumbnail (not just placeholder)
        thumb_path = CACHE_DIR / f"{item_id}.png"
        
        # Check if a real GLB-based thumbnail exists (skip if it does)
        # We mark real thumbnails by size > 5KB (placeholders are ~2KB)
        if thumb_path.exists() and thumb_path.stat().st_size > 5000:
            skipped += 1
            continue
        
        # Step 1: Export the item to GLB
        print(f"[Thumbnail] Exporting: {item.get('name', item_id)}")
        try:
            # Use export_item_blueprint which handles routing to correct export method
            export_result = await asyncio.to_thread(manager.export_item_blueprint, item_id)
            
            if export_result.get('status') != 'success':
                print(f"  Export failed: {export_result.get('message', 'Unknown error')}")
                failed += 1
                continue
            
            # Step 2: Find the GLB file
            output_file = export_result.get('output_file', '')
            if output_file:
                glb_path = Path(output_file).with_suffix('.glb')
                if not glb_path.exists():
                    # Try finding it in the export directory
                    export_dir = Path(output_file).parent
                    glb_files = list(export_dir.glob('*.glb'))
                    if glb_files:
                        glb_path = glb_files[0]
            
            if not glb_path or not glb_path.exists():
                print(f"  No GLB found after export")
                failed += 1
                continue
            
            # Step 3: Render GLB to thumbnail
            print(f"  Rendering thumbnail from: {glb_path.name}")
            thumb = generate_thumbnail(glb_path, item_id)
            
            if thumb and thumb.exists():
                generated += 1
                print(f"  ✓ Thumbnail created: {thumb.name}")
            else:
                failed += 1
                print(f"  ✗ Thumbnail render failed")
                
        except Exception as e:
            print(f"  Exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    return {
        "status": "complete",
        "generated": generated,
        "failed": failed,
        "skipped": skipped,
        "total": len(items)
    }

@app.get("/api/thumbnail-status/{category_path:path}")
async def get_thumbnail_status(category_path: str):
    """Check how many items in a category have thumbnails."""
    if not manager.is_ready():
        return {"has_thumbnails": False, "count": 0, "total": 0}
    
    items = manager.get_items_by_path(category_path)
    total = len(items)
    with_thumbnails = 0
    
    for item in items:
        item_id = item.get('id')
        if item_id and (CACHE_DIR / f"{item_id}.png").exists():
            with_thumbnails += 1
    
    return {
        "has_thumbnails": with_thumbnails > 0,
        "count": with_thumbnails,
        "total": total
    }

# (Update search/list to include thumbnail link)

@app.get("/api/items/{category_path:path}")
async def get_items(category_path: str):
    if not manager.is_ready():
        return {"items": []}
    
    items = await asyncio.to_thread(manager.get_items_by_path, category_path)
    # Post-process to add thumbnail URL if icon exists
    for item in items:
        # We don't want to check file existence here (too slow), just check if valid
        # But we don't return 'thumbnail' URL unless we think it exists?
        # Actually, let's just assume we return the URL and let the frontend fetch result in 404 -> Default
        item['thumbnail'] = f"/api/thumbnail/{item['id']}"
        
    return {"items": items}

@app.get("/api/search")
async def search(q: str):
    if not manager.is_ready():
        return {"results": []}
    items = await asyncio.to_thread(manager.search_items, q)
    for item in items:
        item['thumbnail'] = f"/api/thumbnail/{item['id']}"
    return {"results": items}


@app.get("/api/export/{item_id}")
async def export_item(item_id: str):
    if not manager.is_ready():
        raise HTTPException(status_code=400, detail="SC not loaded")
    
    try:
        # Use the new Blueprint API method for complete exports (including landing gear)
        result = await asyncio.to_thread(manager.export_item_blueprint, item_id)
        return result
    except Exception as e:
        print(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{folder}/{filename}")
async def download_file(folder: str, filename: str):
    file_path = EXPORT_DIR / folder / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename, media_type="application/octet-stream")



# Serve Frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')
