import sys
import ast
import importlib
import operator

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.TaskUtils import task
from mxcubecore.CommandContainer import CommandObject
from mxcubecore.utils.conversion import camel_to_snake
from mxcubecore import HardwareRepository as HWR

from mxcubecore.CommandContainer import (
    CommandObject,
    TWO_STATE_COMMAND_T,
    ARGUMENT_TYPE_LIST,
)

import gevent
import logging


class ControllerCommand(CommandObject):
    def __init__(self, name, cmd=None, username=None, klass=None):
        CommandObject.__init__(self, name, username)

        if not cmd:
            self._cmd = klass()
        else:
            self._cmd = cmd

        self._cmd_execution = None
        self.type = "CONTROLLER"

        if self.name() == "Anneal":
            self.add_argument("Time [s]", "float")
        if self.name() == "Test":
            self.add_argument("combo test", "combo", [{"value1": 0, "value2": 1}])

    def is_connected(self):
        return True

    @task
    def __call__(self, *args, **kwargs):
        """Call the command"""
        self.emit("commandBeginWaitReply", (str(self.name()),))
        self._cmd_execution = gevent.spawn(self._cmd, *args, **kwargs)
        self._cmd_execution.link(self._cmd_done)

    def _cmd_done(self, cmd_execution):
        """Handle the command execution.
        Args:
            (obj): Command execution greenlet.
        """
        try:
            try:
                res = cmd_execution.get()
                res = res if res else ""
            except Exception:
                logging.getLogger("HWR").exception(
                    "%s: execution failed", str(self.name())
                )
                self.emit("commandFailed", (str(self.name()),))
            else:
                if isinstance(res, gevent.GreenletExit):
                    # command aborted
                    self.emit("commandFailed", (str(self.name()),))
                else:
                    self.emit("commandReplyArrived", (str(self.name()), res))
        finally:
            self.emit("commandReady", (str(self.name()), ""))

    def abort(self):
        """Abort the execution."""
        if self._cmd_execution and not self._cmd_execution.ready():
            self._cmd_execution.kill()

    def value(self):
        return None


class HWObjActuatorCommand(CommandObject):
    """Class for two state hardware objects"""

    def __init__(self, name, hwobj):
        super().__init__(name)
        self._hwobj = hwobj
        self.type = TWO_STATE_COMMAND_T
        self.argument_type = ARGUMENT_TYPE_LIST
        self._hwobj.connect("valueChanged", self._cmd_done)
        self._running = False

    def _get_action(self):
        """Return which action has to be executed.
        Return:
            (str): The name of the command
        """
        values = [v.name for v in self._hwobj.VALUES]
        values.remove("UNKNOWN")
        values.remove(self._hwobj.get_value().name)

        return self._hwobj.VALUES[values[0]]

    @task
    def __call__(self, *args, **kwargs):
        """Execute the action.
        Args: None
        Kwargs: None
        """
        self._running = True
        self.emit("commandBeginWaitReply", (str(self.name()),))
        value = self._get_action()
        self._hwobj.set_value(value, timeout=60)

    def _cmd_done(self, state):
        """Handle the command execution.
        Args:
            (obj): Command execution greenlet.
        """
        gevent.sleep(1)
        try:
            res = self._hwobj.get_value().name
        except Exception:
            self.emit("commandFailed", (str(self.name()),))
        else:
            if isinstance(res, gevent.GreenletExit):
                self.emit("commandFailed", (str(self.name()),))
            elif self._running:
                self.emit("commandReplyArrived", (str(self.name()), res))

        self._running = False

    def value(self):
        """Return the current command vaue.
        Return:
            (str): The value as a string
        """
        value = "UNKNOWN"
        if hasattr(self._hwobj, "get_value"):
            value = self._hwobj.get_value()
            try:
                return value.name
            except AttributeError:
                return value
        return value


class AnnotatedCommand(CommandObject):
    def __init__(self, beamline_action_ho, name, cmd_name):
        self._beamline_action_ho = beamline_action_ho
        self._name = name
        self._cmd_name = cmd_name
        self._value = ""
        self._last_result = None
        self._messages = []
        self.task = None

    def get_value(self):
        return self._value

    def set_last_result(self, result):
        self._last_result = result

    @property
    def cmd_name(self):
        return self._cmd_name


class BeamlineActions(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)
        self._annotated_commands = []
        self._annotated_command_dict = {}
        self._command_list = []
        self._current_command = None

    def _get_command_object_class(self, path_str):
        parts = path_str.split(".")

        _module_name = "mxcubecore." + ".".join(parts[:-1])
        _cls_name = parts[-1]
        self._annotated_commands.append(_cls_name)

        # Assume import from current module if only class name givien (no module)
        if len(parts) == 1:
            _cls = getattr(sys.modules[__name__], _cls_name)
        else:
            _mod = importlib.import_module(_module_name)
            _cls = getattr(_mod, _cls_name)

        return _cls

    def init(self):
        command_list = ast.literal_eval(
            self.get_property("commands").strip().replace("\n", "")
        )

        for command in command_list:
            attrname = camel_to_snake(command["command"].split(".")[-1])

            if hasattr(self, attrname):
                msg = (
                    "Command with name %s already exists"
                    % command["command"].split(".")[-1]
                )
                logging.getLogger("HWR").warning(msg)
                continue

            if command["type"] == "annotated":
                _cls = self._get_command_object_class(command["command"])
                fname = camel_to_snake(_cls.__name__)
                _cls_inst = _cls(self, fname.replace("_", " ").title(), fname)

                self._annotated_command_dict[fname] = _cls_inst
                setattr(self, attrname, getattr(_cls_inst, fname))
                self._exports_config_list.append(attrname)
            elif command["type"] == "controller":
                try:
                    cmd = operator.attrgetter(command["command"])(self)
                    _cmd_obj = ControllerCommand(command["name"], cmd, command["name"])
                except AttributeError:
                    _cls = self._get_command_object_class(command["command"])
                    _cmd_obj = ControllerCommand(
                        command["name"], None, command["name"], klass=_cls
                    )

                self._command_list.append(_cmd_obj)
                setattr(self, attrname, _cmd_obj)
            elif command["type"] == "actuator":
                try:
                    cmd = operator.attrgetter(command["command"])
                    _cmd_obj = HWObjActuatorCommand(command["name"], cmd)
                    self._command_list.append(_cmd_obj)
                except AttributeError:
                    pass

        super().init()

    def get_annotated_command(self, name):
        return self._annotated_command_dict[name]

    def get_annotated_commands(self):
        return list(self._annotated_command_dict.values())

    def _execute_annotated_command(self, name, args):
        cmd = getattr(self, name, None)
        self._annotated_command_dict[name].emit("commandBeginWaitReply", name)

        _model = self.pydantic_model[name](**args)
        _all_child_models = []

        for _key in _model.dict().keys():
            _all_child_models.append(getattr(_model, _key))

        _t = gevent.spawn(cmd, *_all_child_models)
        _t.link(self._command_done)

        self._current_command = cmd.__self__
        self._current_command.task = _t

    def get_commands(self):
        return self._command_list

    def _execute_command(self, name, args):
        try:
            cmds = self.get_commands()
        except Exception:
            cmds = []

        for cmd in cmds:
            if cmd.name() == name:
                try:
                    cmd.emit("commandBeginWaitReply", name)
                    logging.getLogger("user_level_log").info(
                        "Starting %s(%s)",
                        cmd.name(),
                        ", ".join(map(str, args)),
                    )
                    cmd(*args)
                except Exception as ex:
                    err = str(sys.exc_info()[1])
                    raise Exception(str(err)) from ex

    def execute_command(self, name, args):
        cmd = getattr(self, name, None)

        if cmd:
            self._execute_annotated_command(name, args)
        else:
            self._execute_command(name, args)

    def _command_done(self, greenlet):
        cmd_obj = self._annotated_command_dict[self._current_command.cmd_name]
        result = ""

        try:
            result = greenlet.get()
        except Exception:
            logging.getLogger("HWR").exception(
                "%s: execution failed", self._current_command.cmd_name
            )
            cmd_obj.emit("commandFailed", (self._current_command.cmd_name,))
        else:
            self._current_command.set_last_result(result)
            if isinstance(result, gevent.GreenletExit):
                # command aborted
                cmd_obj.emit("commandFailed", (self._current_command.cmd_name,))
                result = ""
            else:
                cmd_obj.emit(
                    "commandReplyArrived", (self._current_command.cmd_name, result)
                )
        finally:
            cmd_obj.emit(
                "commandReady",
                (self._current_command.cmd_name, result),
            )

            self._current_command = None

    def abort_command(self, name):
        if (
            self._current_command
            and self._current_command.cmd_name in self._annotated_command_dict
        ):
            self._annotated_command_dict[self._current_command.cmd_name]
            self._current_command.task.kill()
        else:
            for cmd in self.get_commands():
                if cmd.name() == name:
                    cmd.abort()
                    break
