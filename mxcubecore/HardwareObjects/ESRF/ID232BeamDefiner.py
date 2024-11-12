# encoding: utf-8
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
"""
ID23-2 Beam Definer.

Example xml configuration:

.. code-block:: xml

 <object class="ESRF.ESRFBeamDefiner"
   <username>Beam Definer</username>
   <object href="/bliss" role="controller"/>
   # bliss tranfocator object names
   <tf1>tf</tf1>
   <tf2>tf2</tf2>
   <beam_config>
      <name>4x4 um</name>
      <beam_size>0.004, 0.004</beam_size>
      <tf1>0 0 0 0 0 0 0 0 0</tf1>
      <tf2>0 0 1 1 0 0 0 0 0</tf2>
   </beam_config>
   <beam_config>
      <name>4x8 um</name>
      <beam_size>0.004, 0.008</beam_size>
      <tf1>0 0 0 0 0 0 0 0 0</tf1>
      <tf2>0 0 1 0 1 0 0 0 0</tf2>
   </beam_config>
   <default_size_name>4x4 um</default_size_name>
 </object>
"""

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


from enum import Enum

from gevent import (
    Timeout,
    sleep,
)

from mxcubecore.HardwareObjects.ESRF.ESRFBeamDefiner import ESRFBeamDefiner


class ID232BeamDefiner(ESRFBeamDefiner):
    """ID23-2 beam definer implementattion"""

    def __init__(self, *args):
        super().__init__(*args)
        self.tf_cfg = {}
        self.controller = None
        self.tf1 = None
        self.tf2 = None

    def init(self):
        """Initialisation"""
        super().init()

        self.controller = self.get_object_by_role("controller")
        self.tf1 = self.controller.config.get(self.get_property("tf1"))
        self.tf2 = self.controller.config.get(self.get_property("tf2"))
        for beam_cfg in self.config:
            name = beam_cfg.get_property("name")
            tf1 = [int(x) for x in beam_cfg.get_property("tf1").split()]
            tf2 = [int(x) for x in beam_cfg.get_property("tf2").split()]
            self.tf_cfg[name] = {"tf1": tf1, "tf2": tf2}

        self.connect(self.tf1, "state", self._tf_update_state)
        self.connect(self.tf2, "state", self._tf_update_state)

        if self.get_value() == self.VALUES.UNKNOWN and self._default_name:
            # set default beam value
            self.set_value(self._default_name)

    def get_state(self):
        """Get the device state.
        Returns:
            (enum 'HardwareObjectState'): Device state.
        """
        return self.STATES.READY

    def _tf_update_state(self, state=None):
        """Update the value"""
        name = self.get_current_position_name()
        self.emit("valueChanged", name)

    def get_current_status(self):
        """Get the status of the transfocators.
        Returns:
            (tuple): Tuple of two lists, giving the state for each lense
        """
        tf1_status = self.tf1.wago.get("stat")[::2]
        tf2_status = self.tf2.wago.get("stat")[::2]
        return tf1_status, tf2_status

    def get_current_position_name(self):
        """Get the current beam size name.
        Returns:
            (str): Current beam size name.
        """
        try:
            tf1_state, tf2_state = self.get_current_status()
        except ValueError:
            return "UNKNOWN"

        for name in self.beam_config:
            if (
                self.tf_cfg[name]["tf1"] == tf1_state
                and self.tf_cfg[name]["tf2"] == tf2_state
            ):
                return name
        return "UNKNOWN"

    def set_value(self, value, timeout=None):
        """Set the beam size.
        Args:
            value(str): name of the beam size to set.
            timeout(float): Timeout to wait for the execution to finish [s].
        Raises:
            RuntimeError: Cannot change beam size.
        """
        if isinstance(value, Enum):
            value = value.name

        tf1_cfg  = self.tf_cfg[value]["tf1"]
        tf2_cfg = self.tf_cfg[value]["tf2"]
        self.tf1.set(*tf1_cfg)
        self.tf2.set(*tf2_cfg)

        try:
            self.wait_status((tf1_cfg, tf2_cfg), timeout)
        except RuntimeError as err:
            raise RuntimeError("Cannot change beam size") from err

    def wait_status(self, status, timeout=None):
        """Wait timeout seconds until status reached
        Args:
            status (tuple): Transfocator status to be reached.
            timeout (float): Timeout [s]. Defaults to None.
        """
        with Timeout(timeout, RuntimeError("Execution timeout")):
            while status != self.get_current_status():
                sleep(0.5)
