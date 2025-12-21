from backend.main import SCManager
from pathlib import Path
import asyncio
import subprocess

async def test_skin():
    manager = SCManager()
    sc_path = r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE"
    await asyncio.to_thread(manager.load_sc, sc_path)
    
    # Path found in CDF inspection
    cdf_path = "Data/Objects/Spaceships/Ships/ANVL/LandingGear/Arrow/ANVL_Arrow_Landing_Gear_Front.cdf"
    
    print(f"Extracting: {cdf_path}")
    export_dir = Path("test_exports")
    export_dir.mkdir(exist_ok=True)
    
    # Extract CDF
    if manager.sc.p4k.search(cdf_path):
        manager.sc.p4k.extract(cdf_path, str(export_dir))
    
    # Also need the files referenced BY the CDF (SKIN, SKINM, CHR)
    # We could parse it, but for this test we'll just extract the known ones
    skin_path = cdf_path.replace(".cdf", "_SKIN.skin")
    
    # Extract SKIN, SKINM
    if manager.sc.p4k.search(skin_path):
        manager.sc.p4k.extract(skin_path, str(export_dir))
    
    skinm_path = skin_path.replace(".skin", ".skinm")
    if manager.sc.p4k.search(skinm_path):
         manager.sc.p4k.extract(skinm_path, str(export_dir))

    # Extract CHR
    chr_path = cdf_path.replace(".cdf", "_CHR.chr")
    if manager.sc.p4k.search(chr_path):
        manager.sc.p4k.extract(chr_path, str(export_dir))

    # Convert SKIN as CGF?
    local_skin_path = export_dir / skin_path
    
    # RENAME to .cgf
    local_cgf_path = local_skin_path.with_suffix(".cgf")
    if local_skin_path.exists():
        import shutil
        shutil.copy(local_skin_path, local_cgf_path)
        print(f"Copied .skin to .cgf: {local_cgf_path}")
    
    converter_exe = Path(r"e:/Antigravity/Starfab_Agentic/.venv/Lib/site-packages/starfab/contrib/cgf-converter.exe")
    cmd = [
        str(converter_exe),
        str(local_cgf_path),
        "-obj",
        "-object_dir", str(export_dir / "Data")
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    
    # Check output
    obj_path = local_cgf_path.with_suffix(".obj")
    if obj_path.exists():
        print(f"SUCCESS: {obj_path} created. Size: {obj_path.stat().st_size}")
    else:
        print("FAILURE: OBJ not created.")

if __name__ == "__main__":
    asyncio.run(test_skin())
