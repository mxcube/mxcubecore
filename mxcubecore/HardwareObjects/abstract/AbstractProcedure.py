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
import logging
import gevent

from HardwareRepository.BaseHardwareObjects import ConfiguredObject
from HardwareRepository.dispatcher import dispatcher

# Using jsonschma for validating the JSCONSchemas
# https://json-schema.org/
# https://github.com/Julian/jsonschema

from jsonschema import (validate, ValidationError)


__credits__ = ["MXCuBE collaboration"]


@unique
class ProcedureState(IntEnum):
    """
    Defines the valid Procedure states
    """
    FAILED = 0
    RUNNING = 1
    SUCCESFUL = 2
    IDLE = 3


class AbstractProcedure(ConfiguredObject):

    __content_roles = []

    _ALLOW_PARALLEL = False

    # JSONSchema used for input and output validation and possibly
    # form generation.
    # https://json-schema.org/
    # Needs to be defined by each subclass
    _ARG_SCHEMA = None
    _RESULT_SCHEMA = None

    def __init__(self, name):
        super(AbstractProcedure, self).__init__(name)

        self._msg=None
        self._results=None
        self._ready_event = gevent.event.Event()
        self._task=None
        self._state = ProcedureState.IDLE

        # YML configuration options
        # Category that the Procedure belongs to, configurable through
        # YAML file and used by for listing and displaying the procedure
        # in the right context.
        self.category=""

    def _init(self):
        pass

    def init(self):
        pass

    def _execute(self, data_model):
        """
        Override to implement main task logic

        Args:
            data_model: Immutable data model, frozen dict in
            Python 2.7 and Data class in Python 3.7. Input validated
            by schema defined in _ARG_SCHEMA

        Returns:
        """
        pass

    def _pre_execute(self, data_model):
        """
        Override to implement pre execute task logic

        Args:
            data_model: Immutable data model, frozen dict in
            Python 2.7 and Data class in Python 3.7. Input validated
            by schema defined in _ARG_SCHEMA

        Returns:
        """
        pass

    def _post_execute(self, data_model):
        """
        Override to implement post execute task logic

        Args:
            data_model: Immutable data model, frozen dict in
            Python 2.7 and Data class in Python 3.7. Input validated
            by schema defined in _ARG_SCHEMA

        Returns:
        """
        pass

    def _set_started(self):
        """
        Emits procedureStarted signal
        Returns:

        """
        self._state = ProcedureState.RUNNING
        dispatcher.send(self, "procedureStarted")

    def _set_successful(self):
        """
        Emits procedureSuccessful signal
        Returns:

        """
        self._state = ProcedureState.SUCCESFUL
        dispatcher.send(self, "procedureSuccessful", self.results)

    def _set_failed(self):
        """
        Emits procedureFailed signal
        Returns:

        """
        self._state = ProcedureState.FAILED
        dispatcher.send(self, "procedureFailed", self.msg)

    def _set_stopped(self):
        """
        Emits procedureStoped signal
        Returns:

        """
        self._state = ProcedureState.FAILED
        dispatcher.send(self, "procedureStopped", self.results)

    def _start(self, data_model):
        """
        Internal start, for the moment executed in greenlet
        """
        try:
            # The _pre_execute have been removed and can be done within
            # execute if needed
            self._pre_execute(data_model)
            self._execute(data_model)
        except Exception as ex:
            self._state = ProcedureState.FAILED
            self._msg = "Procedure execution failed (%s)" % str(ex)
            logging.getLogger("HWR").error(self._msg)
        finally:
            try:
                self._post_execute(data_model)
            except Exception as ex:
                self._state = ProcedureState.FAILED
                self._msg = "Procedure post_execute failed (%s)" % str(ex)
                logging.getLogger("HWR").error(self._msg)

            self.ready_event.set()

            if self._state ==  ProcedureState.FAILED:
                self._set_failed()
            else:
                self._set_successful()

    @property
    def argument_schema(self):
        """
        Schema for argument passed to start
        Returns:
            str (JSONSchema)
        """
        return self._ARG_SCHEMA

    @property
    def result_schema(self):
        """
        Schema for result
        Returns:
            str (JSONSchema)
        """
        return self._RESULT_SCHEMA

    @property
    def msg(self):
        """
        Last message produced by procedure
        Returns:
            str
        """
        return self._msg

    @property
    def state(self):
        """
        Execution state
        Returns:
             ProcedureState: The current state of the procedure
        """
        return self._state

    @property
    def results(self):
        """
        Results from procedure execution validated by RESULT_SCHEMA
        if it is defined

        Returns:
            DataClass or frozendict
        """
        if self._RESULT_SCHEMA:
            validate(self._results, schema=self._RESULT_SCHEMA)

        return self._results

    def start(self, data_model):
        """
        Starts procedure
        Args:
            data_model: Immutable data model, frozen dict in
            Python 2.7 and Data class in Python 3.7. Input validated
            by schema defined in _ARG_SCHEMA

        Returns:
            None
        """
        # This raises a ValidationException if validation fails
        if self._ARG_SCHEMA:
            validate(instance=data_model, schema=self._ARG_SCHEMA)

        if not self._ALLOW_PARALLEL and self.is_running:
            self._msg = "Procedure (%s) is already running" % str(self)
            logging.getLogger("HWR").error(self._msg)
        else:
            self._task = gevent.spawn(self._start, data_model)

    def stop(self):
        """
        Stops the execution of procedure
        Returns:
            None
        """
        gevent.kill(self._task)
        self._set_procedure_stopped()
