from scdatatools.sc import StarCitizen
import sys

sc = StarCitizen(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
print("SC Loaded")

# Find a known item
keywords = ["Arrow", "Pistol", "Helmet"]
for kw in keywords:
    for record in sc.datacore.records:
        if kw in record.name and "Skin" not in record.name:
            print(f"Record: {record.name}")
            # print all attributes
            print(dir(record))
            # try to find icon
            if hasattr(record, 'icon'):
                print(f"  Icon: {record.icon}")
            if hasattr(record, 'thumbnail'):
                print(f"  Thumbnail: {record.thumbnail}")
            if hasattr(record, 'properties'):
                props = record.properties
                # Search props for icon/ui
                print(f"  Props keys: {list(props.keys())}")
            break
