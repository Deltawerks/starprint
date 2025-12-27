# StarPrint

**The Star Citizen 3D Print Asset Extractor**

StarPrint is a tool designed to extract clean, printable 3D models from Star Citizen game files. It focuses on **personal items** like armor, weapons, gadgets, and decorations - outputting clean `.obj` files.

> **Status:** Alpha/Testing
> **Focus:** 3D Printing (No textures, no animation, minimal cleaning required)

> ⚠️ **Important:** StarPrint currently only works with **Star Citizen 4.2 and earlier** Data.p4k files. SC 4.5+ introduced new file formats that are not yet supported by upstream tools (cgf-converter, scdatatools). See [cgf-converter #225](https://github.com/Markemp/Cryengine-Converter/issues/225) for updates.

## 🚀 Features

-   **Personal Items:** Armor sets, FPS weapons, melee weapons, gadgets, flair, decorations, and more.
-   **Clean Output:** Automatically strips lights, helpers, and material references.
-   **Visual Library:** Generates 3D-rendered "holographic" thumbnails for your items.
-   **Smart Filtering:** Hides hundreds of duplicate "skins" to show only unique geometries.

## 📋 Requirements

-   **OS:** Windows 10 or 11
-   **Game:** Star Citizen installed (LIVE or PTU)
-   **Python:** generic **Python 3.10** or newer installed. (Make sure to check "Add Python to PATH" during installation)
-   **Git:** **Git for Windows** installed (Required to download core libraries).

## 🛠️ Installation & Setup

1.  **Download** this repository (or `git clone`).
2.  Double-click **`Run-StarPrint.bat`**.
    *   *First run will download required tools and create a Python virtual environment.*
3.  A browser window will open at `http://localhost:8000`.
4.  **First Time Setup:**
    *   Click **Setup** in the top right.
    *   Paste the path to your Star Citizen installation (e.g., `C:\Program Files\Roberts Space Industries\StarCitizen\LIVE`).
    *   Click **Save**. The app will scan your `Data.p4k`.

## 🎮 How to Use

### 1. Browse & Generate Thumbnails
*   Navigate using the sidebar categories (Armor, Weapons, Ships, etc.).
*   **Pro Tip:** Categories start empty/with cube icons. To see what you're looking at:
    *   Click the 👁️ **Eye Icon** next to a category name.
    *   Wait! The server will export and render each item in the background. (Check the terminal window for progress).
    *   Once done, you'll have a permanent visual library of that category.

### 2. Preview
*   Click any item card to load it in the 3D preview panel.
*   Rotate/Zoom to inspect the geometry.
*   *Note: Large ships may take 10-20 seconds to load.*

### 3. Download
*   Click **EXTRACT GEOMETRY**.
*   The system will process the file (converting formats, merging parts).
*   Your browser will download a ZIP containing the `.obj` file.
*   (Alternately, find the raw files in the `exports/` folder inside the project).

## 📄 Documentation for Developers

See [DEVELOPER_NOTES.md](DEVELOPER_NOTES.md) for a deep dive into the architecture, the thumbnail generation pipeline, and the assembly logic.

## ⚠️ Known Issues

*   **SC 4.5+ Not Supported:** Star Citizen 4.5 introduced new file formats (.cgf version changes) that the upstream tools cannot yet parse. Use a pre-4.5 Data.p4k backup.
*   **Disk Space:** The `exports/` folder can grow **very large** (multiple GB) after extracting several items. Each item extracts raw assets before conversion. Clear this folder periodically to reclaim space.
*   **Export Speed:** Complex items can take 30+ seconds to process.
*   **Memory:** Massive ships (Reclaimer, 890 Jump) might crash specifically on 16GB RAM machines during the merge process.
*   **Duplicates:** Some texture variants might still sneak through the filter.

## Acknowledgments

*   **scdatatools** for the core P4K reading capability.
*   **cgf-converter** by Markemp for the geometry conversion.
*   **trimesh** for the mesh processing magic.
