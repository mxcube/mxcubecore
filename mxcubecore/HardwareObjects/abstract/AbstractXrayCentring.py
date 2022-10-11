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
"""
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

__copyright__ = """ Copyright © 2016 - 2022 by MXCuBE Collaboration """
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "25/03/2022"
import abc

from mxcubecore.BaseHardwareObjects import HardwareObjectYaml
from mxcubecore import HardwareRepository as HWR
from mxcubecore.model import queue_model_objects


class AbstractXrayCentring(HardwareObjectYaml):
    """Xray Centring Hardware Object. Set to Yaml configuration.
    """

    def __init__(self, name):
        super(AbstractXrayCentring, self).__init__(name)

        # Needed to allow methods to put new actions on the queue
        # And as a place to get hold of other objects, like the QMO
        self._queue_entry = None

        # Current data collection task group. For adding tasks to queue. if needed
        self._data_collection_group = None

    def _init(self):
        # This function is superfluous, but left in as a reminder in case you need to override it
        super(AbstractXrayCentring, self)._init()

    def init(self):
        super(AbstractXrayCentring, self).init()
        self.update_state(self.STATES.READY)

    def shutdown(self):
        """Shut down Xray centring. Triggered on program quit."""
        pass

    def pre_execute(self, queue_entry):
        """
        :param queue_entry: (XrayCentring2QueueEntry) For access to queue and data model
        :return:
        """

        self._queue_entry = queue_entry
        if self.is_ready():
            self.update_state(self.STATES.BUSY)
        else:
            raise RuntimeError(
                "Cannot execute Xray centring - HardwareObject is not ready"
            )
        new_dcg_model = queue_model_objects.TaskGroup()
        new_dcg_model.set_enabled(True)
        new_dcg_model.set_name("CentringTaskGroup")
        self._data_collection_group = new_dcg_model
        self._add_to_queue(self._queue_entry.get_data_model(), new_dcg_model)

    @abc.abstractmethod
    def execute(self):
        """Contains the actual X-ray centring code
        taking parameters from the data model as needed"""

        pass

    def post_execute(self):
        """
        The workflow has finished, sets the state to 'READY'
        """

        self._queue_entry = None
        self._data_collection_group = None
        self.update_state(self.STATES.READY)

    def _add_to_queue(self, parent_model_obj, child_model_obj):
        """Used to add entries to queue while centring process is running (if needed)"""
        HWR.beamline.queue_model.add_child(parent_model_obj, child_model_obj)

