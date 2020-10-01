#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.
""" Execute commands and toggle two state actions
Example xml file:
<object class = "ESRF.BeamCmds">
  <object role="controller" href="/bliss"/>
  <object role="hutchtrigger"  href="/hutchtrigger"/>
  <object role="scintilator" href="/udiff_scint"/>
  <object role="detector_cover" href="/detcover"/>
  <object role="aperture" href="/udiff_apertureinout"/>
  <object role="cryostream" href="/udiff_cryo"/>
  <controller_commands>
    <centrebeam>Centre beam</centrebeam>
    <quick_realign>Quick realign</quick_realign>
    <anneal_procedure>Anneal</anneal_procedure>
  </controller_commands>
  <hwobj_commands>
    ["hutchtrigger", "scintilator", "detector_cover", "aperture", "cryostream"]
  </hwobj_commands>
</object>
"""
import ast
import logging
import gevent

from HardwareRepository.TaskUtils import task
from HardwareRepository.CommandContainer import CommandObject
from HardwareRepository.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

PROCEDURE_COMMAND_T = "CONTROLLER"
TWO_STATE_COMMAND_T = "INOUT"

ARGUMENT_TYPE_LIST = "List"
ARGUMENT_TYPE_JSON_SCHEMA = "JSONSchema"


class BaseBeamlineAction(CommandObject):
    """Base command class"""

    def __init__(self, name):
        super(BaseBeamlineAction, self).__init__(name)

        # From CommandObject consider removing
        self._arguments = []
        self._combo_arguments_items = {}


class ControllerCommand(BaseBeamlineAction):
    """Execute commands class"""

    def __init__(self, name, cmd):
        super().__init__(name)
        self._cmd = cmd
        self._cmd_execution = None
        self.type = PROCEDURE_COMMAND_T
        self.argument_type = ARGUMENT_TYPE_LIST

    def is_connected(self):
        """Dummy method"""
        return True

    def set_argument_json_schema(self, json_schema_str):
        """Set the JSON Schema"""
        self.argument_type = ARGUMENT_TYPE_JSON_SCHEMA
        self._arguments = json_schema_str

    def getArguments(self):
        """Get the command object arguments"""
        if self.name() == "Anneal":
            self._arguments.append(("Time [s]", "float"))

        return CommandObject.getArguments(self)

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
            except BaseException:
                self.emit("commandFailed", (str(self.name()),))
            else:
                if isinstance(res, gevent.GreenletExit):
                    self.emit("commandFailed", (str(self.name()),))
                else:
                    self.emit("commandReplyArrived", (str(self.name()), res))
        finally:
            self.emit("commandReady", (str(self.name()), ""))

    def abort(self):
        """Abort the execution.
        """
        if self._cmd_execution and not self._cmd_execution.ready():
            self._cmd_execution.kill()

    def value(self):
        """Return nothing - a command has no return value"""
        return None


class TestCommand(ControllerCommand):
    """Test command class"""

    def __init__(self, name):
        super(TestCommand, self).__init__(name, None)

    def _count(self):
        for i in range(0, 10):
            gevent.sleep(1)
            print(i)
            logging.getLogger("user_level_log").info("%s done.", i)

    @task
    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))
        self._cmd_execution = gevent.spawn(self._count)
        self._cmd_execution.link(self._cmd_done)

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
        except BaseException:
            self.emit("commandFailed", (str(self.name()),))
        else:
            if isinstance(res, gevent.GreenletExit):
                self.emit("commandFailed", (str(self.name()),))
            else:
                self.emit("commandReplyArrived", (str(self.name()), res))

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


class BeamCmds(HardwareObject):
    """Beam action commands"""

    def __init__(self, name):
        super(BeamCmds, self).__init__(name)
        self.ctrl_list = []
        self.hwobj_list = []

    def init(self):
        """Initialise the controller commands and the actuator object
           to be used.
        """
        ctrl_cmds = self["controller_commands"].getProperties().items()

        if ctrl_cmds:
            controller = self.getObjectByRole("controller")
            for key, name in ctrl_cmds:
                # name = self.getProperty(cmd)
                action = getattr(controller, key)
                self.ctrl_list.append(ControllerCommand(name, action))

        hwobj_cmd_roles = ast.literal_eval(
            self.getProperty("hwobj_command_roles").strip()
        )

        if hwobj_cmd_roles:
            for role in hwobj_cmd_roles:
                hwobj_cmd = self.getObjectByRole(role)
                self.hwobj_list.append(
                    HWObjActuatorCommand(hwobj_cmd.username, hwobj_cmd)
                )

    def get_commands(self):
        """Get which objects to be used in the GUI
        Returns:
            (list): List of object
        """
        return self.ctrl_list + self.hwobj_list
