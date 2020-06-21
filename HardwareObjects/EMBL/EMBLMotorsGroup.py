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

"""
[Name] EMBLMotorsGroup

[Description]
The MotorsGroup Hardware Object is used to maintain several motors in one
group. Motors group is a lsit of motors which are like a grouped instance
in tine server (a tuple). It allowes to read several motor position,
statuses,... by one read.

[Channels]
- self.chanPositions
- self.chanStatus

[Commands]
- implemented as tine.set

[Emited signals]
- mGroupPosChanged
- mGroupFocModeChanged
- mGroupStatusChanged

[Functions]
- setMotorPosition()
- setMotorFocMode()
- setMotorGroupFocMode()
- stopMotor()
- positionsChanged()
- statusChanged()

[Included Hardware Objects] -

Example Hardware Object XML file :
==================================
<device class="MotorsGroup">
    <username>P14BCU</username>                     - used to identify group
    <serverAddr>/P14/P14BCU</serverAddr>            - tine server address
    <groupAddr>/ShutterTrans</groupAddr>            - motors group address
    <positionAddr>Position</positionAddr>           - position address
    <statusAddr>Status</statusAddr>                 - status address
    <motors>                                        - motors list
        <motor>
          <motorName>ShutterTrans</motorName>       - name
          <motorAddr>ShutterTrans</motorAddr>       - address
          <setCmd>MOVE.start</setCmd>               - set cmd
          <stopCmd>MOVE.stop</stopCmd>              - stop cmd
          <index>0</index>                          - index in the group
          <velocity>None</velocity>                 - velocity
          <updateTolerance>0.005</updateTolerance>  - absolute update tolerance
          <evalTolerance>0.005</evalTolerance>      - absolute tolerance of
					              beam focus mode evaluation
          <statusModes>{'Move': 1, 'Ready': 0}</statusModes>
          <focusingModes>{'Collimated': 0.22, 'Horizontal': 0.22,
          'Vertical': 0.22, 'Double': 0.22}</focusingModes>
        </motor>
    </motors>
</device>
"""


import time
import logging

import gevent

import tine
from HardwareRepository.BaseHardwareObjects import Device


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "Motor"


class EMBLMotorsGroup(Device):
    """
    EMBLMotorsGroup
    """

    def __init__(self, name):

        Device.__init__(self, name)
        self.server_address = None
        self.group_address = None
        self.motors_list = None
        self.motors_group_position_dict = None
        self.motors_group_status_dict = None
        self.motors_group_foc_mode_dict = None

        self.chan_positions = None
        self.chan_status = None

    def init(self):
        self.motors_group_position_dict = {}
        self.motors_group_status_dict = {}
        self.motors_group_foc_mode_dict = {}

        self.server_address = self.serverAddr
        self.group_address = self.groupAddr
        self.motors_list = []

        for motor in self["motors"]:
            temp_dict = {}
            temp_dict["motorName"] = motor.motorName
            temp_dict["motorAddr"] = motor.motorAddr
            temp_dict["setCmd"] = motor.setCmd
            temp_dict["index"] = motor.index
            temp_dict["velocity"] = motor.velocity
            temp_dict["updateTolerance"] = motor.updateTolerance
            temp_dict["evalTolerance"] = motor.evalTolerance
            temp_dict["statusModes"] = eval(motor.statusModes)
            temp_dict["focusingModes"] = eval(motor.focusingModes)
            temp_dict["status"] = None
            temp_dict["position"] = -9999
            temp_dict["focMode"] = []
            self.motors_list.append(temp_dict)

        try:
            self.chan_positions = self.add_channel(
                {
                    "type": "tine",
                    "tinename": self.server_address + self.group_address,
                    "name": self.positionAddr,
                },
                self.positionAddr,
            )
            self.chan_positions.connect_signal("update", self.positions_changed)
            self.positions_changed(self.chan_positions.get_value())
        except BaseException:
            msg = "EMBLMotorsGroup: unable to add channel %s/%s %s" % (
                self.server_address,
                self.group_address,
                self.positionAddr,
            )
            logging.getLogger("HWR").error(msg)

        try:
            self.chan_status = self.add_channel(
                {
                    "type": "tine",
                    "tinename": self.server_address + self.group_address,
                    "name": self.statusAddr,
                },
                self.statusAddr,
            )
            self.chan_status.connect_signal("update", self.status_changed)
            self.status_changed(self.chan_status.get_value())
        except BaseException:
            msg = "EMBLMotorsGroup: unable to add channel %s/%s %s" % (
                self.server_address,
                self.group_address,
                self.statusAddr,
            )
            logging.getLogger("HWR").error(msg)

    def get_motors_dict(self):
        """Returns dict with motors"""
        return self.motors_list

    def set_motor_position(self, motor_name, new_position, timeout=None):
        """Sets motor value. Direct tine.set cmd is used"""
        for motor in self.motors_list:
            if motor["motorName"] == motor_name:
                if motor["velocity"] is not None:
                    tine.set(
                        self.server_address + "/" + motor["motorAddr"],
                        "Velocity",
                        motor["velocity"],
                    )
                motor["status"] = motor["statusModes"]["Move"]
                tine.set(
                    self.server_address + "/" + motor["motorAddr"],
                    motor["setCmd"],
                    new_position,
                )
                logging.getLogger("HWR").debug(
                    "EMBLMotorsGroup: send %s : %.4f"
                    % (motor["motorAddr"], new_position)
                )
                time.sleep(0.2)
                self.wait_motor_ready(motor_name, timeout=10)
                time.sleep(1)
                logging.getLogger("HWR").debug(
                    "EMBLMotorsGroup: motor %s ready" % motor["motorAddr"]
                )
                break

    def set_motor_focus_mode(self, motor_name, focus_mode):
        """Sets a focus mode for an individual motor"""
        for motor in self.motors_list:
            if motor["motorName"] == motor_name:
                if (
                    motor["setCmd"] is not None
                    and focus_mode in motor["focusingModes"].keys()
                ):
                    if motor["velocity"] is not None:
                        tine.set(
                            self.server_address + "/" + motor["motorAddr"],
                            "Velocity",
                            motor["velocity"],
                        )
                    tine.set(
                        self.server_address + "/" + motor["motorAddr"],
                        motor["setCmd"],
                        motor["focusingModes"][focus_mode],
                    )
                    time.sleep(1)
                break

    def set_motor_group_focus_mode(self, focus_mode):
        """Sets a focus mode for the motors group"""
        for motor in self.motors_list:
            if (
                motor["setCmd"] is not None
                and focus_mode in motor["focusingModes"].keys()
            ):
                if motor["velocity"] is not None:
                    tine.set(
                        self.server_address + "/" + motor["motorAddr"],
                        "Velocity",
                        motor["velocity"],
                    )
        time.sleep(0.5)

        for motor in self.motors_list:
            if (
                motor["setCmd"] is not None
                and focus_mode in motor["focusingModes"].keys()
            ):

                motor["status"] = motor["statusModes"]["Move"]
                tine.set(
                    self.server_address + "/" + motor["motorAddr"],
                    motor["setCmd"],
                    motor["focusingModes"][str(focus_mode)],
                )
                logging.getLogger("HWR").debug(
                    "EMBLMotorsGroup: send %s : %.4f"
                    % (motor["motorAddr"], motor["focusingModes"][str(focus_mode)])
                )
                if motor["motorName"] in ("In", "Out", "Top", "But"):
                    self.wait_motor_ready(motor["motorName"], timeout=10)
                    time.sleep(1.1)
                    logging.getLogger("HWR").debug(
                        "EMBLMotorsGroup: motor %s ready" % motor["motorAddr"]
                    )

    def stop_motor(self, motor_name):
        """Stops motor movement"""
        for motor in self.motors_list:
            if motor["motorName"] == motor_name:
                if motor["setCmd"] is not None:
                    tine.set(
                        self.server_address + self.group_address + "/" + motor_name,
                        motor["stopCmd"],
                    )
                break

    def positions_changed(self, positions):
        """Called if one or several motors values has been changed.
           Evaluates if value needs to be updates, if value is
           changed, then evaluates focusing mode. If necessary
           pysignals are emited
        """
        do_emit = False
        # values_to_send = {}
        # foc_mode_to_send = {}
        for motor in self.motors_list:
            old_value = motor["position"]
            if isinstance(positions, (list, tuple)):
                new_value = positions[motor["index"]]
            else:
                new_value = positions
            if abs(old_value - new_value) > motor["updateTolerance"]:
                motor["position"] = new_value
                do_emit = True
            if do_emit:
                self.motors_group_position_dict[motor["motorName"]] = new_value
                motor["focMode"] = []
                for foc_mode in motor["focusingModes"]:
                    diff = abs(motor["focusingModes"][foc_mode] - new_value)
                    if diff < motor["evalTolerance"]:
                        motor["focMode"].append(foc_mode)
                self.motors_group_foc_mode_dict[motor["motorName"]] = motor["focMode"]
        if do_emit:
            self.emit("mGroupPosChanged", self.motors_group_position_dict)
            self.emit("mGroupFocModeChanged", self.motors_group_foc_mode_dict)

    def get_detected_foc_mode(self):
        """
        Returns focus mode
        :return: str
        """
        return self.detected_foc_mode

    def status_changed(self, status):
        """Called if motors status is changed. Pysignal with new
           status has been sent"""
        for motor in self.motors_list:
            old_status = motor["status"]
            if isinstance(status, (list, tuple)):
                new_status = status[motor["index"]]
            else:
                new_status = status
            if old_status != new_status:
                motor["status"] = new_status
                for status_mode in motor["statusModes"]:
                    if motor["statusModes"][status_mode] == new_status:
                        self.motors_group_status_dict[motor["motorName"]] = status_mode
        self.emit("mGroupStatusChanged", self.motors_group_status_dict)

    def wait_motor_ready(self, motor_name, timeout):
        """Waits motor ready"""
        self.status_changed(self.chan_status.get_value())
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self.is_motor_ready(motor_name):
                gevent.sleep(0.01)

    def is_motor_ready(self, motor_name):
        """Returns True if motors is ready"""
        is_ready = False
        for motor in self.motors_list:
            if motor["motorName"] == motor_name:
                is_ready = motor["status"] == motor["statusModes"]["Ready"]
                break
        return is_ready

    def re_emit_values(self):
        """
        Reemits all signals
        :return:
        """
        self.emit("mGroupPosChanged", self.motors_group_position_dict)
        self.emit("mGroupFocModeChanged", self.motors_group_foc_mode_dict)
        self.emit("mGroupStatusChanged", self.motors_group_status_dict)
