"""
Test scdatatools Blueprint API for Arrow export.
"""
from scdatatools.sc import StarCitizen
from scdatatools.sc.blueprints.generators.datacore_entity import blueprint_from_datacore_entity
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    sc = StarCitizen(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
    print(f"SC Loaded: {sc.version_label}")
    
    # Find Arrow record
    arrow_name = "ANVL_Arrow"
    records = [r for r in sc.datacore.search_filename(f"*/{arrow_name}.xml") if r.type == "EntityClassDefinition"]
    
    if not records:
        print(f"Could not find entity for {arrow_name}")
        return
    
    record = records[0]
    print(f"Found record: {record.name} ({record.id})")
    
    # Generate blueprint
    def monitor(msg, progress=None, total=None, level=None, exc_info=None):
        level = level or logging.INFO
        logger.log(level, msg, exc_info=exc_info)
    
    print("Generating blueprint...")
    bp = blueprint_from_datacore_entity(sc, record, monitor=monitor)
    
    print(f"Blueprint generated: {bp.name}")
    print(f"  Type: {type(bp)}")
    print(f"  Dir: {dir(bp)}")
    
    # Explore properties
    if hasattr(bp, 'hardpoints'):
        print(f"  Hardpoints: {len(bp.hardpoints) if hasattr(bp.hardpoints, '__len__') else 'N/A'}")
    if hasattr(bp, 'geometry'):
        print(f"  Geometry: {bp.geometry}")
    if hasattr(bp, 'loadout'):
        print(f"  Loadout: {bp.loadout}")
    
    # Extract to output dir
    output_dir = Path("blueprint_test_output")
    output_dir.mkdir(exist_ok=True)
    
    print(f"\nExtracting to {output_dir}...")
    bp.extract(
        outdir=output_dir,
        monitor=monitor,
        auto_convert_models=True,
        cgf_converter_bin=r"e:/Antigravity/Starfab_Agentic/.venv/Lib/site-packages/starfab/contrib/cgf-converter.exe",
        convert_dds_fmt="png",
    )
    
    print(f"\nExtraction complete! Check {output_dir}")

if __name__ == "__main__":
    main()
