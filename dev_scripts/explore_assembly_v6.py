import sys
import inspect

try:
    import scdatatools.engine.cryxml as cryxml_mod
    print("Imported scdatatools.engine.cryxml")
    print(f"Dir: {dir(cryxml_mod)}")
    
    # Check for CryXML class
    if hasattr(cryxml_mod, 'CryXML'):
        print("Found CryXML class!")
    else:
        print("CryXML class NOT found in module.")
        
    # Check for functions
    for name, obj in inspect.getmembers(cryxml_mod):
        if inspect.isclass(obj):
            print(f"Class: {name}")
        elif inspect.isfunction(obj):
            print(f"Function: {name}")

except ImportError as e:
    print(f"Import Error: {e}")

try:
    from scdatatools.utils import cryxml_to_xml
    print("Found cryxml_to_xml in utils!")
except ImportError:
    print("Not in utils.")
