import sys
import logging
from importlib import import_module
from pathlib import Path


class ImportHelper():
    MODULES = {}

    def import_all_queue_entry_modules(name):
        if not ImportHelper.MODULES:
            for f in  Path(__file__).parent.glob("*.py"):
                m = import_module(f"{__package__}.{f.stem}")
                cls_name = f.stem.title().replace("_", "") + "QueueEntry"

                # Skipp BaseQueueEntry, it is explcicitly imported below as the module 
                # contains several essential calsses and helper functions
                # Skipp xrf_spectrum to preserve casing (XRF) so that we are backwards
                # compatible (for the time being)
                if f.stem in ["import_helper", "base_queue_entry", "xrf_spectrum", "__init__"]:
                    continue

                cls = getattr(m, cls_name, None)

                if cls:
                    ImportHelper.MODULES[cls_name] = cls
                    setattr(sys.modules[name], cls_name, cls)
                    logging.getLogger("HWR").info(f"Imported queue entry: {cls_name} from {f}")
                else:
                    logging.getLogger("HWR").warning(f"Could not find queue entry: {cls_name} in {f}")
    
        return ImportHelper.MODULES