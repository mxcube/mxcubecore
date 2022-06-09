#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import sys
from importlib import import_module
from pathlib import Path

def import_all_queue_entry_modules():
    modules = {}

    for f in  Path(__file__).parent.glob("*.py"):
        m = import_module(f"{__package__}.{f.stem}")
        cls_name = f.stem.title().replace("_", "") + "QueueEntry"
        cls = getattr(m, cls_name, None)

        if cls:
            modules[cls_name] = cls
            setattr(sys.modules[__name__], cls_name, cls)

    return modules

# Import all queue entries defined in package, using the convention
# that the class name is the camel cased modulename with a QueueEntry
# suffix.
_modules = import_all_queue_entry_modules()
__all__ = _modules.values()

del import_module, Path, import_all_queue_entry_modules


# Import all constants and BaseQueueEntry from base_queue_entry so that
# queue _entry can be imported and used as before.
from mxcubecore.HardwareObjects.queue_entry.base_queue_entry import *

from mxcubecore.HardwareObjects import queue_model_objects
from mxcubecore.HardwareObjects.Gphl import GphlQueueEntry
from mxcubecore.HardwareObjects.EMBL import EMBLQueueEntry

# These two queue entries, for the moment violates the convention above and
# needs to be chnaged
from mxcubecore.HardwareObjects.queue_entry.xrf_spectrum import XRFSpectrumQueueEntry
from mxcubecore.HardwareObjects.queue_entry.characterisation import CharacterisationGroupQueueEntry

# At this stage the QueueEntries are dynamically imported (A linter
# will complain that they are not defined)
MODEL_QUEUE_ENTRY_MAPPINGS = {
    queue_model_objects.DataCollection: _modules["DataCollectionQueueEntry"],
    queue_model_objects.Characterisation: CharacterisationGroupQueueEntry,
    queue_model_objects.EnergyScan: _modules["EnergyScanQueueEntry"],
    queue_model_objects.XRFSpectrum: XRFSpectrumQueueEntry,
    queue_model_objects.SampleCentring: _modules["SampleCentringQueueEntry"],
    queue_model_objects.OpticalCentring: _modules["OpticalCentringQueueEntry"],
    queue_model_objects.Sample: SampleQueueEntry,
    queue_model_objects.Basket: BasketQueueEntry,
    queue_model_objects.TaskGroup: TaskGroupQueueEntry,
    queue_model_objects.Workflow: _modules["GenericWorkflowQueueEntry"],
    queue_model_objects.XrayCentering: _modules["XrayCenteringQueueEntry"],
    queue_model_objects.GphlWorkflow: GphlQueueEntry.GphlWorkflowQueueEntry,
    queue_model_objects.XrayImaging: EMBLQueueEntry.XrayImagingQueueEntry,
}


def get_queue_entry_from_task_name(task_name):
    cls_name = (task_name.title().replace("_", "") + "QueueEntry")
    return  getattr(sys.modules[__name__], cls_name, None)