#
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
import logging
from enum import (
    IntEnum,
    unique,
)

import gevent.event

# Using jsonschma for validating the JSCONSchemas
# https://json-schema.org/
# https://github.com/Julian/jsonschema
from jsonschema import (
    ValidationError,
    validate,
)

from mxcubecore.BaseHardwareObjects import ConfiguredObject
from mxcubecore.dispatcher import dispatcher

# import mxcubecore.model.procedure_model


__credits__ = ["MXCuBE collaboration"]


# Temporary definition should use common denfinition from
# HardwareObject
@unique
class ProcedureState(IntEnum):
    """
    Defines the valid Procedure states
    """

    ERROR = 0
    BUSY = 1
    READY = 3


class AbstractProcedure(ConfiguredObject):
    __content_roles = []

    _ARGS_CLASS = ()
    _KWARGS_CLASS = {}
    _RESULT_CLASS = ()

    @staticmethod
    def set_args_class(args_class, kwargs_class):
        """
        Sets the types of the data models used as arguments, cane be used to
        set the argument classes runtime if the models are built dynamically,
        i.e based on configuration not known before

        Args:
            args_class (tuple[BaseModel]) tuple of classes for args
            kwargs_class (dict[[str]: [BaseModel]]) dictionary containing BaseModels
        """
        AbstractProcedure._ARGS_CLASS = args_class
        AbstractProcedure._KWARGS_CLASS = kwargs_class

    @staticmethod
    def set_result_class(_result_class):
        """
        Sets the types of the data models returned by the Procedure, can
        be used to set the result model runtime of the data model is built
        dynamically, i.e based on configuration not known before

        Returns:
            (tuple[BaseModel]) tuple of classes for args
        """
        AbstractProcedure._RESULT_CLASS = _result_class

    def __init__(self, name):
        super(AbstractProcedure, self).__init__(name)
        self._msg = None
        self._results = None
        self._ready_event = gevent.event.Event()
        self._task = None
        self._state = ProcedureState.READY

        # YML configuration options
        # Category that the Procedure belongs to, configurable through
        # YAML file and used by for listing and displaying the procedure
        # in the right context.
        self.category = ""

    def _init(self):
        pass

    def init(self):
        pass

    def _execute(self, data_model):
        """
        Override to implement main task logic

        Args:
            data_model: sub class of mxcubecore.model.procedure_model
            dict in Python 2.7 and Data class in Python 3.7. Data is validated
            by the data_model object

        Returns:
        """
        pass

    def _pre_execute(self, data_model):
        """
        Override to implement pre execute task logic

        Args:
            data_model: sub class of mxcubecore.model.procedure_model
            Data is validated by the data_model object

        Returns:
        """
        pass

    def _post_execute(self, data_model):
        """
        Override to implement post execute task logic

        Args:
            data_model: sub class of mxcubecore.model.procedure_model
            Data is validated by the data_model object

        Returns:
        """
        pass

    def _set_started(self):
        """
        Emits procedureStarted signal
        Returns:

        """
        self._state = ProcedureState.BUSY
        dispatcher.send(self, "procedureStarted")

    def _set_successful(self):
        """
        Emits procedureSuccessful signal
        Returns:

        """
        self._state = ProcedureState.READY
        dispatcher.send(self, "procedureSuccessful", self.results)

    def _set_error(self):
        """
        Emits procedure error signal
        Returns:

        """
        self._state = ProcedureState.ERROR
        dispatcher.send(self, "procedureError", self.msg)

    def _set_stopped(self):
        """
        Emits procedureStoped signal
        Returns:

        """
        self._state = ProcedureState.READY
        dispatcher.send(self, "procedureStopped", self.results)

    def _start(self, data_model):
        """
        Internal start, for the moment executed in greenlet
        """
        try:
            self._set_started()
            self._pre_execute(data_model)
            self._execute(data_model)
        except Exception as ex:
            self._state = ProcedureState.ERROR
            self._msg = "Procedure execution error (%s)" % str(ex)
            logging.getLogger("HWR").exception(self._msg)
        finally:
            try:
                self._post_execute(data_model)
            except Exception as ex:
                self._state = ProcedureState.ERROR
                self._msg = "Procedure post_execute error (%s)" % str(ex)
                logging.getLogger("HWR").exception(self._msg)

            self._ready_event.set()

            if self._state == ProcedureState.ERROR:
                self._set_error()
            else:
                self._set_successful()

    @property
    def argument_schema(self):
        """
        Schema for arguments passed to start
        Returns:
            dict{"args": tuple[JSONSchema], "kwargs": key: [JSONSchema]}
        """
        return {
            "args": tuple([s.schema_json() for s in self._ARGS_CLASS]),
            "kwargs": {
                key: value.schema_json() for (key, value) in self._KWARGS_CLASS.items()
            },
        }

    @property
    def result_schema(self):
        """
        Schema for result
        Returns:
            tuple[JSONSchema]
        """
        return (s.schema_json() for s in self._RESULT_CLASS)

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

        return self._results

    def start(self, data_model):
        """
        Starts procedure
        Args:
            data_model: sub class of mxcubecore.model.procedure_model.
            Data is validated by the data_model object

        Returns:
            (Greenlet) The gevent task
        """
        if self._state != ProcedureState.READY:
            self._msg = "Procedure (%s) is already running" % str(self)
            logging.getLogger("HWR").error(self._msg)
        else:
            self._task = gevent.spawn(self._start, data_model)

        return self._task

    def stop(self):
        """
        Stops the execution of procedure
        Returns:
            None
        """
        gevent.kill(self._task)
        self._set_stopped()

    def wait(self):
        """
        Waits for procedure to finish execution

        Returns:
            None
        """
        self._ready_event.wait()
