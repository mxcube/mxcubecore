#! /usr/bin/env python
# encoding: utf-8
#
# This file is part of MXCuBE.
#
# MXCuBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MXCuBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with MXCuBE.  If not, see <https://www.gnu.org/licenses/>.
""" """

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import logging

from mxcubecore.HardwareObjects.abstract.AbstractXrayCentring import (
    AbstractXrayCentring,
)
from mxcubecore.model import queue_model_objects

__copyright__ = """ Copyright © 2016 - 2022 by MXCuBE Collaboration """
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "25/03/2022"
__category__ = "General"


class XrayCentringMockup(AbstractXrayCentring):
    def execute(self):
        """Dummy execution. Adds new entries to queue, to serve as example."""

        queue_manager = self._queue_entry.get_queue_controller()

        logging.getLogger("HWR").debug("Execute mock Xray centring ")

        # Add Dummy task 1
        dummy = queue_model_objects.DelayTask(delay=1)
        dummy.set_enabled(True)
        dummy.set_name("CentringDelay1")
        self._add_to_queue(self._data_collection_group, dummy)
        dummy_entry = queue_manager.get_entry_with_model(dummy)
        dummy_entry.in_queue = True

        # Add Dummy task 2
        dummy = queue_model_objects.DelayTask(delay=2)
        dummy.set_enabled(True)
        dummy.set_name("CentringDelay2")
        self._add_to_queue(self._data_collection_group, dummy)
        dummy_entry = queue_manager.get_entry_with_model(dummy)
        dummy_entry.in_queue = True

        # Execute
        data_collection_entry = queue_manager.get_entry_with_model(
            self._data_collection_group
        )
        queue_manager.execute_entry(data_collection_entry)
