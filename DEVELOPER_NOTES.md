# StarPrint Developer Notes

**Date:** December 20, 2024
**Status:** Alpha / Functional Prototype

## Project Overview

StarPrint is a specialized asset extractor for Star Citizen, focused on creating **clean, 3D-printable meshes**. Unlike general-purpose extractors, it prioritizes:
1.  **Single Mesh Output:** It merges multi-part assets (like ships with landing gear or helmets with visors) into a single `.obj` file.
2.  **Clean Geometry:** It strips lights, helpers, proxies, and materials to ensure the output is ready for slicers.
3.  **Visual Browsing:** It generates 3D thumbnails on-demand to make browsing the massive library easier.

## Architecture

### Backend (`backend/`)
-   **Framework:** FastAPI (Python)
-   **Core Library:** `scdatatools` (User-modified version) for reading `Data.p4k`.
-   **3D Processing:** `trimesh` + `numpy` for mesh manipulation, merging, and rendering.
-   **Conversion:** `cgf-converter.exe` (External tool in `tools/`) handles CryEngine `.cgf`/`.cga` to `.glb`/`.obj`.

### Frontend (`frontend/`)
-   **Tech:** Vanilla JavaScript + HTML + CSS.
-   **Styling:** Custom "Futuristic Utility" theme (CSS variables, no framework).
-   **3D Viewer:** `<model-viewer>` web component for interactive previews.

## Key Subsystems

### 1. Thumbnail System (`backend/thumbnails.py`)
*Refactored Dec 20, 2024*

The thumbnail system transforms the browsing experience from a list of names to a visual catalog.

*   **Generation Flow:**
    1.  User clicks the 📷 **Camera Button** on a category.
    2.  Backend iterates through items in that category.
    3.  **Export:** Each item is exported to `.glb` (using the same pipeline as the download feature).
    4.  **Render:** The `.glb` is loaded into a headless renderer.
    5.  **Silhouette Processing:** We use a custom **2D projection renderer** (using `PIL` and `numpy`) instead of OpenGL/pyrender. This projects the 3D mesh faces onto a 2D plane, creating a cyan-colored, shaded "holographic" silhouette. This avoids complex OpenGL dependencies on the server.
    6.  **Caching:** Resulting PNGs are saved to `cache/` by GUID.
*   **Deduplication:** The system identifies duplicative items (texture variants sharing the same 3D geometry) and only displays/generates one thumbnail per unique geometry.

### 2. Export Pipeline (`backend/assembler.py`)
*Refactored Dec 19, 2024*

Star Citizen assets are complex. A "ship" is often just a hull file (`.cga`) with attachment points for landing gear, turrets, and doors defined in an XML file.

*   **Legacy Path:** Simple items (helmets, food, knives) are single `.cgf` files. These are converted directly.
*   **Blueprint Path:** Complex items (ships, assembled weapons) use the `BlueprintAssembler`.
    1.  **Parse:** Reads the Entity Class Definition (XML) to find hardpoints.
    2.  **Fetch:** Locates the geometry for attached parts (e.g., `Anvil_Arrow_LandingGear.cga`).
    3.  **Merge:** Loads all parts into a `trimesh.Scene`, applies the correct offset/rotation (from the hardpoint transform), and merges them into a single mesh.
    4.  **Clean:** Strips all `usemtl` lines from the final `.obj` to prevent slicers from looking for missing textures.

## Setup & configuration

### Prerequisites
*   Python 3.10+
*   Star Citizen installed (LIVE or PTU)

### Installation
The `Run-StarPrint.bat` script handles everything:
1.  Creates a Python virtual environment (`.venv`).
2.  Installs dependencies from `requirements.txt`.
3.  Launches the server.

### Configuration
*   **Game Path:** Stored by `scdatatools` in its own config (typically `~/.scdatatools/config.json` or similar). The app exposes a setup screen (`/api/set-path`) to configure this.
*   **Cache:** Thumbnails are stored in `cache/`.
*   **Exports:** User exports go to `exports/`.

## Recent Modifications (Context for Handoff)

*   **Deduplication Logic:** Added to `SCManager.get_items_by_path`. It groups items by **Base Name** (e.g., `Helmet_01`, `Helmet_02` -> `Helmet`). It filters out numbered variants to declutter the UI.
*   **Thumbnail Reliability:** The endpoint `/api/thumbnail/{id}` was simplified to strictly serve cached files (returning 404 if missing). It no longer attempts unstable "on-the-fly" generation. Generation is now exclusively triggered via the batch endpoint (`/api/generate-thumbnails`).
*   **Bug Fix (AttributeError):** Fixed a crash where `geo_info` was sometimes a string path instead of an object property in the export logic.

## Known Issues

1.  **Export Speed:** Complex keys/assemblies can take 10-30 seconds to export because `cgf-converter` runs on every sub-part.
2.  **Missing Parts:** Some strict hierarchies (like specific turret gimbals) might not attach if the XML structure varies from the standard "Hardpoint" definition.
3.  **Memory:** Processing massive ships (e.g., Reclaimer) might hit memory limits during `trimesh` merge.

## Future To-Do

*   **Optimization:** Cache converted `.glb` files of common parts (like landing gear) to speed up subsequent ship exports.
*   **UI:** Add a progress bar for the thumbnail generation (currently just a loading spinner/console logs).
*   **Portability:** Dockerize the application to remove local Python dependency issues.
