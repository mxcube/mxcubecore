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
"""Execute commands and toggle two state actions
Example xml file:
<object class = "ESRF.ESRFBeamlineActions">
  <object role="controller" href="/bliss"/>
  <object role="hutchtrigger"  href="/hutchtrigger"/>
  <object role="scintillator" href="/udiff_scint"/>
  <object role="detector_cover" href="/detcover"/>
  <object role="aperture" href="/udiff_apertureinout"/>
  <object role="cryostream" href="/udiff_cryo"/>
  <controller_commands>
    <centrebeam>Centre beam</centrebeam>
    <quick_realign>Quick realign</quick_realign>
    <anneal_procedure>Anneal</anneal_procedure>
  </controller_commands>
  <hwobj_commands>
    ["hutchtrigger", "scintillator", "detector_cover", "aperture", "cryostream"]
  </hwobj_commands>
</object>
"""

import ast

import gevent

from mxcubecore.HardwareObjects.BeamlineActions import (
    BeamlineActions,
    ControllerCommand,
    HWObjActuatorCommand,
)
from mxcubecore.TaskUtils import task

__copyright__ = """ Copyright © 2010-2023 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class ESRFBeamlineActions(BeamlineActions):
    """Beam action commands"""

    def __init__(self, *args):
        super().__init__(*args)
        self.ctrl_list = []
        self.hwobj_list = []

    def init(self):
        """Initialise the controller commands and the actuator object
        to be used.
        """
        try:
            ctrl_cmds = self["controller_commands"].get_properties().items()

            if ctrl_cmds:
                controller = self.get_object_by_role("controller")
                for key, name in ctrl_cmds:
                    # name = self.get_property(cmd)
                    action = getattr(controller, key)
                    self.ctrl_list.append(ControllerCommand(name, action))
        except KeyError:
            pass

        try:
            hwobj_cmd_roles = ast.literal_eval(
                self.get_property("hwobj_command_roles").strip()
            )

            if hwobj_cmd_roles:
                for role in hwobj_cmd_roles:
                    try:
                        hwobj_cmd = self.get_object_by_role(role)
                        self.hwobj_list.append(
                            HWObjActuatorCommand(hwobj_cmd.username, hwobj_cmd)
                        )
                    except:
                        pass
        except AttributeError:
            pass

    def get_commands(self):
        """Get which objects to be used in the GUI
        Returns:
            (list): List of object
        """
        return self.ctrl_list + self.hwobj_list
