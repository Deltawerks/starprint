from scdatatools.sc import StarCitizen
from scdatatools.forge.utils import geometry_for_record
from scdatatools.engine.chunkfile import load_chunk_file, ChunkType

sc = StarCitizen(r'C:\Program Files\Roberts Space Industries\StarCitizen\LIVE')
rec = [r for r in sc.datacore.records if 'ccc_medium_armor_helmet_01_01_01' in r.name.lower()][0]

print(f"Record: {rec.name}")

# Get geometry info
geo = geometry_for_record(rec, data_root=sc.p4k)
geo_info = geo.get('tableDisplay') or list(geo.values())[0]
print(f"Geometry File: {geo_info.filename}")

# Load the chunk file
try:
    cf = load_chunk_file(geo_info)
    print(f"Loaded ChunkFile with {len(cf.chunks)} chunks")
    
    # Inspect chunks for Materials
    for chunk in cf.chunks.values():
        if hasattr(chunk, 'name'):
            print(f"Chunk Name: {chunk.name}")
        
        # Check for Material references
        # MtlName chunks usually contain the material path
        if "MtlName" in str(type(chunk)):
            print(f"Material Chunk Found: {chunk.name}")
            
except Exception as e:
    print(f"Failed to load chunk file: {e}")
    import traceback
    traceback.print_exc()
