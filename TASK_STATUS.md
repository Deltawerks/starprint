- [x] Create `Run-StarFab.ps1` automation script
- [ ] **Implement Assembly System**
    - [ ] Create `backend/assembler.py` (BlueprintAssembler class)
    - [x] Build export: Main Mesh + Attachments
  - [x] Create basic `BlueprintAssembler`
  - [x] Implement geometry path resolution (Data-Driven: Entity Record)
  - [x] Implement `cgf-converter` pipeline for parts
  - [x] Implement attachment logic (Trimesh Scene Graph)
  - [x] Verify Missing attachments (Arrow Gear, Guns, Doors)
  - [x] Bug: "No geometry found" for Fire Extinguisher (Likely resolved by Loadout logic)
  - [x] Bug: Broken Landing Gear (Resolved by `LandingSystem` logic)
  - [x] Bug: RSI Mantis missing parts (Resolved by supporting List-type Components)
- [x] **Verify Assembly**
    - [x] Run `verify_export.py` on Arrow (Check logs for attachments)
    - [x] Validate OBJ in external viewer (Rotation + Parts)
- [x] Verify script functionality (dry run/review)
- [x] Guide user on running the script
- [x] Fix Python 3.10 detection in script
- [x] Fix virtual environment execution path
- [x] Guide user to retry

# Phase 2: Enhancements & Usability
- [x] Create `improvement_plan.md` for distribution and UX
- [ ] Research `briefcase` or `pyinstaller` for creating a standalone EXE
- [ ] Design "Asset Browser" workflow (Search by name -> Auto-select High LOD)
- [ ] Design "3D Print Export" pipeline (Blender cleanup scripts)
- [ ] **New Feature: 3D Thumbnail Snapshots** (Capture view from `<model-viewer>`)
- [ ] **New Feature: Batch Thumbnail Generation** (Script to generate all icons)
- [ ] **Investigate: Odd Colors in Preview** (Likely material stripped for OBJ)
- [x] **Refactor: Use scdatatools Blueprint API**
    - [x] Explore `blueprint_from_datacore_entity` function
    - [x] Understand Blueprint object structure (hardpoints, geometry)
    - [x] Verified: Landing gear extracted and converted to DAE
    - [x] Integrate Blueprint API into StarPrint backend
        - [x] Added `export_item_blueprint` method to `SCManager`
        - [x] Tested: Arrow exports with 354K vertices, 402K faces (55.9MB OBJ)
    - [x] Wire up API endpoint to use new method
    - [x] Added progress reporting with timestamps (Step 1/5 - 5/5)
    - [x] Test with RSI Mantis: 362K vertices, 388K faces (53.7MB OBJ)
    - [x] **Refinement: Filter Interior & Duplicates**
        - [x] Filter out `_CHR` skeleton files (fixes duplicate geometry)
        - [x] **Fix: Smart Loadout Filtering**
            - [x] Ships: Keep loadout (needed for panels/doors)
            - [x] Items: Clear loadout (removes crates/stands)
        - [x] Verified filter logic is safe (reverted aggressive interior filtering)

# Phase 1: Publish "Easy Installer" Patch
- [x] Create README.md with proper attribution
- [x] Add LICENSE file (MIT)
- [x] Clean up repo (remove source folders, keep only installer)
- [x] Push to GitHub (Deltawerks/starfab-easy-installer)
- [x] Add .bat launcher for easier use

# Phase 3: Fix Blender Export Pipeline (Fork)
- [x] Research cgf-converter.exe and texconv.exe
- [x] Understand why exports show only bounding boxes/lights
- [ ] Create fork for "StarFab Fixed" version
- [x] Auto-bundle or auto-download converter tools
- [x] Test full pipeline: Extract → Convert → Blender import

# Phase 5: StarPrint - New 3D Print Focused Tool
- [x] Create implementation plan
- [x] Set up new repository (Deltawerks/starprint)
- [/] Build core: Backend Implementation
    - [x] Implement `SCManager` wrapper for `scdatatools`
    - [x] Integrate `StarCitizen` object initialization
    - [x] Connect Frontend to Backend (API operational)
- [x] Build export: LOD0 → OBJ pipeline
    - [x] Implement robust dependency extraction (textures/materials)
    - [x] Implement "Smart Merge" filter (removes LODs/Proxies)
    - [x] Convert CGF -> DAE -> OBJ automatically
- [x] **Implement Frontend Enhancements**
    - [x] Backend: Update Search/List to include `icon` path
    - [x] Backend: Create `/api/thumbnail/{id}` endpoint (Convert TIF/DDS -> PNG)
    - [x] Frontend: Update `app.js` to fetching thumbnails
    - [x] Frontend: Integrate `<model-viewer>` for 3D Preview
- [ ] Build UI: Thumbnail grid + 3D preview

# Phase 6: Item-First Refactoring (Armor, Weapons, Flair)
- [x] Planning Phase (Pivot to personal items)
- [x] Implement robust item type detection (path-based)
- [/] Refine Loadout Filtering (Keep functional parts, strip crates/stands) <!-- id: 6 -->
- [x] Implement strict LOD filtering at the geometry node level
- [x] Add automatic centering logic for preview meshes
- [/] **Robust Geometry Cleanup** <!-- id: 7 -->
    - [ ] Post-process OBJ to strip all material/texture references
    - [ ] Remove residual .mtl files
- [ ] **Implementation Verification**
    - [ ] Test Medgun (ensure canisters/parts are included)
    - [ ] Test Armor (ensure no crates/stands)
    - [ ] Test Flair (ensure clean trophies/decorations)

# Phase 7: Advanced Ship Handling (Coming Soon)
- [ ] Research selective sub-component extraction for complex ships 
- [ ] Fine-tune interior vs exterior hull detection
- [ ] Explore material/texture preservation without `pycollada` crashes

