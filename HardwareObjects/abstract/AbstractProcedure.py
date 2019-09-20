#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
AbstractProcedure
"""

import logging
import gevent

from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["MXCuBE collaboration"]


class AbstractProcedure(HardwareObject):

    def __init__(self):
        self.is_running = None
        self.ready_event = None
        self.failed_msg = None
        self.procedure_failed = None
        self.procedure_results = None

    def init(self):
        self.ready_event = gevent.event.Event()

    def start_procedure(self, data_model):
        """
        Starts procedure
        Args:
            data_model: data model defined in the queue_model_objects

        Returns: None

        """
        try:
            self.pre_execute(data_model)
            self.execute(data_model)
        except Exception as ex:
            self.procedure_failed = True
            msg = "Procedure execution failed (%s)" % str(ex)
            logging.getLogger("HWR").error(msg)
        finally:
            self.post_execute(data_model)
            self.ready_event.set()

    def pre_execute(self, data_model):
        """
        Pre execute task
        Args:
            data_model: data model defined in the queue_model_objects

        Returns: None

        """
        self.set_procedure_started()

    def execute(self, data_model):
        """
        Actual exection task
        Args:
            data_model: data model defined in the queue_model_objects

        Returns:

        """
        pass

    def post_execute(self, data_model):
        """
        Post exectute
        Args:
            data_model: data model defined in the queue_model_objects

        Returns:

        """
        if self.procedure_failed:
            self.set_procedure_failed()
        else:
            self.set_procedure_successful()

    def set_procedure_started(self):
        """
        Emits procedureStarted signal
        Returns:

        """
        self.procedure_failed = False
        self.is_running = True
        self.emit("procedureStarted")

    def set_procedure_successful(self):
        """
        Emits procedureSuccessful signal
        Returns:

        """
        self.is_running = False
        self.emit("procedureSuccessful", self.procedure_results)

    def set_procedure_failed(self):
        """
        Emits procedureFailed signal
        Returns:

        """
        self.is_running = False
        self.emit("procedureFailed", self.failed_msg)
