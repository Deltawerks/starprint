# StarPrint Migration Notes

**Reason for Move**: Star Citizen Patch 4.5 introduced a new DAE file format (or broke `cgf-converter` compatibility) causing `pycollada` crashes due to malformed XML (empty color tags, missing controller accessors).

**Target Machine**: Laptop with older Star Citizen version (Pre-4.5).

## Current Status
We have successfully implemented **Phase 6: Item-First Refactoring** features which are ready to test on the compatible game version:

1.  **Robust Item Detection**: 
    - Uses file paths (`entities/spaceships` vs `entities/scitem`) instead of unreliable properties.
    - Reference: `SCManager.export_item_blueprint` in `backend/main.py`.

2.  **Smart Loadout Clearing**:
    - Automatically clears `bp.loadout` for personal items (Armor/Weapons).
    - **Expected Fix**: Helmets should export *without* storage crates or display stands.

3.  **Enhanced LOD Filtering**:
    - Now filters out `_lodX`, `_proxy`, `_phys`, `_shadow`, `_collision`, `_decal` at the geometry level.
    - **Expected Fix**: Models should look clean without "z-fighting" or "mangled" textures.

4.  **Auto-Centering**:
    - Final mesh is automatically translated to origin `(0,0,0)` before export.
    - **Expected Fix**: Previews should be perfectly centered.

## Setup Instructions for Laptop

1.  **Pull Repository**: `git pull` the latest changes.
2.  **Install Dependencies**: Run `setup_env.bat` (or ensure `scdatatools` and `trimesh` are installed).
3.  **Check SC Path**: Update `SC_PATH` if needed (default looks for standard install).
4.  **Run**: Execute `start_starprint.bat`.

## Verification Steps (On Laptop)
Once running with the older SC version:
1.  Search for "Ruso" or "Exeter" helmet.
2.  Click **Export**.
3.  **Success Criteria**:
    - [ ] No crash!
    - [ ] Helmet appears centered in preview.
    - [ ] No storage box/crate attached.
    - [ ] Textures/Mesh look clean (no mangled geometry).
