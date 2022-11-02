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

from mxcubecore.queue_entry.import_helper import ImportHelper

# Import all constants and BaseQueueEntry from base_queue_entry so that
# queue _entry can be imported and used as before.
from mxcubecore.queue_entry.base_queue_entry import *

from mxcubecore.model import queue_model_objects
from mxcubecore.HardwareObjects.Gphl import GphlQueueEntry
from mxcubecore.HardwareObjects.EMBL import EMBLQueueEntry

# These two queue entries, for the moment violates the convention above and
# should eventually be changed
from mxcubecore.queue_entry.xrf_spectrum import XRFSpectrumQueueEntry
from mxcubecore.queue_entry.characterisation import (
    CharacterisationGroupQueueEntry,
)

__all__ = []
MODEL_QUEUE_ENTRY_MAPPINGS = {}


def get_queue_entry_from_task_name(task_name):
    """
    Converts a snake cased task name to a camel cased class name, stripping
    all the "_" (underscores) and adding the suffix QueueEntry.

    Args:
        task_name (str): The task name

    Returns:
        str: The class name

    """
    cls_name = task_name.title().replace("_", "") + "QueueEntry"
    return getattr(sys.modules[__name__], cls_name, None)


def import_queue_entries(site_name_list):
    """
    Imports queue entries; imports all the native queue entries first and
    then the queue entries in site_name

    NBNB: Sets the globals __all__ and MODEL_QUEUE_ENTRY_MAPPINGS

    Args:
        site_name_list (list): List with sites to import from

    Returns:
        None

    """
    global __all__, MODEL_QUEUE_ENTRY_MAPPINGS

    # Import all queue entries, using the convention that the class name
    # is the camel cased modulename with a QueueEntry suffix.
    _modules = ImportHelper.import_queue_entry_modules(__name__)

    for site_name in site_name_list:
        _modules = ImportHelper.import_queue_entry_modules(__name__, site_name)

    __all__ = [*_modules]

    MODEL_QUEUE_ENTRY_MAPPINGS = {
        queue_model_objects.DataCollection: _modules["DataCollectionQueueEntry"],
        queue_model_objects.Characterisation: CharacterisationGroupQueueEntry,
        queue_model_objects.EnergyScan: _modules["EnergyScanQueueEntry"],
        queue_model_objects.XRFSpectrum: XRFSpectrumQueueEntry,
        queue_model_objects.SampleCentring: _modules["SampleCentringQueueEntry"],
        queue_model_objects.OpticalCentring: _modules["OpticalCentringQueueEntry"],
        queue_model_objects.DelayTask: DelayQueueEntry,
        queue_model_objects.Sample: SampleQueueEntry,
        queue_model_objects.Basket: BasketQueueEntry,
        queue_model_objects.TaskGroup: TaskGroupQueueEntry,
        queue_model_objects.Workflow: _modules["GenericWorkflowQueueEntry"],
        queue_model_objects.XrayCentering: _modules["XrayCenteringQueueEntry"],
        queue_model_objects.XrayCentring2: _modules["XrayCentering2QueueEntry"],
        queue_model_objects.GphlWorkflow: GphlQueueEntry.GphlWorkflowQueueEntry,
        queue_model_objects.XrayImaging: EMBLQueueEntry.XrayImagingQueueEntry,
    }

    # NBNB This is added for the queue models using pydantic (task_data
    # attribute) objects to define the data, to be able to use
    # MODEL_QUEUE_ENTRY_MAPPINGS for creating queue entries given a model.
    for _m in _modules.values():
        if hasattr(_m, "QMO"):
            MODEL_QUEUE_ENTRY_MAPPINGS[_m.QMO] = _m
