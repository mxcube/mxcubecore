# encoding: utf-8

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
"""
Utility class for importing queue entries
"""

import sys
import os
import logging
from importlib import import_module
from pathlib import Path


class ImportHelper:
    """
    Utility class for importing queue entries
    """

    MODULES = {}

    @staticmethod
    def import_queue_entry_modules(name, site_name=""):
        """
        Import all queue entries, using the convention that the class name
        is the camel cased modulename with a QueueEntry suffix.

        Args:
            name (str): Moudle name to attach queue entries to
            site_name (str): Site name, for looking up site specific
                             queue_entries

        Returns:
            dict: ImportHelper.MODULES (<str,class>)
        """

        package = f"mxcubecore.HardwareObjects.{site_name}.queue_entry"
        site_path = f"HardwareObjects/{site_name}/queue_entry"
        path = os.path.dirname(__file__).replace("queue_entry", site_path)

        package = package if site_name else __package__
        path = path if site_name else os.path.dirname(__file__)

        for f in Path(path).glob("*.py"):
            # Skipp BaseQueueEntry, it is explcicitly imported below as
            # the module contains several essential calsses and helper
            # functions Skipp xrf_spectrum to preserve casing (XRF) so that
            # we are backwards compatible (for the time being)
            if f.stem in [
                "import_helper",
                "base_queue_entry",
                "xrf_spectrum",
                "__init__",
            ]:
                continue
            m = import_module(f"{package}.{f.stem}")
            cls_name = f.stem.title().replace("_", "") + "QueueEntry"

            cls = getattr(m, cls_name, None)

            if cls:
                ImportHelper.MODULES[cls_name] = cls
                if not hasattr(sys.modules[name], cls_name):
                    setattr(sys.modules[name], cls_name, cls)
                    logging.getLogger("HWR").info(
                        f"Imported queue entry: {cls_name} from {f}"
                    )
                else:
                    logging.getLogger("HWR").warning(
                        f"Queue entry with name: {cls_name} already exists {f}"
                    )
            else:
                logging.getLogger("HWR").warning(
                    f"Could not find queue entry: {cls_name} in {f}"
                )

        return ImportHelper.MODULES
