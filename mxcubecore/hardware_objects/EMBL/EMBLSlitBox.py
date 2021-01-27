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
The BeamSlitBox Hardware Object is used to operate slits.

Example Hardware Object XML file :
==================================
<equipment class="BeamSlitBox">
    <focModeEq>/beamFocusing</focModeEq>             - focusing mode equipment
    <focModes>['Collimated', 'Horizontal', 'Vertical', 'Double']</focModes>
                                                     - used focusing modes
    <gapH>
       <modesAllowed>['Collimated', 'Vertical']</modesAllowed> - used modes
       <stepSize>0.0050</stepSize>                   - step size
       <minGap>0.010</minGap>                        - min gap
       <maxGap>1.10</maxGap>                         - max max gap
       <updateTolerance>0.0005</updateTolerance>     - gap update tolerance
       <motors>                                      - motors used to define gap
          <motor>
            <motorName>Out</motorName>               - name
            <motorsGroup>attocubeMotors</motorsGroup>- motors group name
            <reference>407154</reference>            - reference value
          </motor>
          <motor>
            <motorName>In</motorName>
            <motorsGroup>attocubeMotors</motorsGroup>
            <reference>-68579</reference>
          </motor>
       </motors>
    </gapH>
    <gapV>
       <modesAllowed>['Collimated', 'Horizontal']</modesAllowed>
       <stepSize>0.0050</stepSize>
       <minGap>0.010</minGap>
       <maxGap>1.10</maxGap>
       <updateTolerance>0.0005</updateTolerance>
       <motors>
          <motor>
            <motorName>Top</motorName>
            <motorsGroup>attocubeMotors</motorsGroup>
            <reference>66114</reference>
          </motor>
          <motor>
            <motorName>But</motorName>
            <motorsGroup>attocubeMotors</motorsGroup>
            <reference>4391</reference>
          </motor>
       </motors>
    </gapV>
    <device hwrid="/attocubeMotors/attoGroup" role="attocubeMotors"/>
</equipment>
"""

import logging

from mxcubecore.hardware_objects.abstract.AbstractSlits import AbstractSlits


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "Motor"


class EMBLSlitBox(AbstractSlits):
    """User can define sizes of horizontal and verstical slits by
       entering direct size and pressing Enter or by using up and
       down buttons. Slits operations are enabled accordingly to
       the detected focusing mode.
          - Collimated beam (both enabled)
          - Horizontally focused (hor. disabled and ver. enabled)
          - Vertically focused (hor. enabled and ver. disabled)
          - Double focused (both disabled)
       User can stop slit movement by pressing stop button
       (enabled if slits moves).
    """

    def __init__(self, *args):
        AbstractSlits.__init__(self, *args)

        self.decimal_places = None
        self.active_focus_mode = None
        self.beam_focus_hwobj = None
        self.gaps_dict = None
        self.motors_dict = None
        self.init_max_gaps = None
        self.motors_groups = None
        self.hor_gap_enabled = False
        self.ver_gap_enabled = False

    def init(self):
        self.decimal_places = 6
        self.gaps_dict = {}
        # WARNING modifying self.gaps_dict["Hor"] and ["Ver"}
        # modifies the GLOBAL properties, not just the local copy
        # Maybe do self["gapH"].get_properties().copy()?
        self.gaps_dict["Hor"] = self["gapH"].get_properties()
        self.gaps_dict["Ver"] = self["gapV"].get_properties()
        self.gaps_dict["Hor"]["value"] = 0.10
        self.gaps_dict["Ver"]["value"] = 0.10
        self.gaps_dict["Hor"]["status"] = ""
        self.gaps_dict["Ver"]["status"] = ""
        self.init_max_gaps = self.get_max_limits()

        self.motors_dict = {}
        for motor in self["gapH"]["motors"]:
            self.motors_dict[motor.motorName] = {}
            self.motors_dict[motor.motorName]["motorsGroup"] = motor.motorsGroup
            self.motors_dict[motor.motorName]["gap"] = "Hor"
            self.motors_dict[motor.motorName]["reference"] = motor.reference
            self.motors_dict[motor.motorName]["position"] = 0
            self.motors_dict[motor.motorName]["status"] = None
            self.motors_dict[motor.motorName]["focMode"] = []

        for motor in self["gapV"]["motors"]:
            self.motors_dict[motor.motorName] = {}
            self.motors_dict[motor.motorName]["motorsGroup"] = motor.motorsGroup
            self.motors_dict[motor.motorName]["gap"] = "Ver"
            self.motors_dict[motor.motorName]["reference"] = motor.reference
            self.motors_dict[motor.motorName]["position"] = 0
            self.motors_dict[motor.motorName]["status"] = None
            self.motors_dict[motor.motorName]["focMode"] = []

        self.motors_groups = [self.get_object_by_role("slitsMotors")]
        if self.motors_groups is not None:
            for motor_group in self.motors_groups:
                self.connect(
                    motor_group, "mGroupPosChanged", self.motors_group_position_changed
                )
                self.connect(
                    motor_group, "mGroupStatusChanged", self.motors_group_status_changed
                )
                motor_group.re_emit_values()

        self.beam_focus_hwobj = self.get_object_by_role("focusing")
        if self.beam_focus_hwobj:
            self.connect(
                self.beam_focus_hwobj, "focusingModeChanged", self.focus_mode_changed
            )
            self.beam_focus_hwobj.re_emit_values()
        else:
            logging.getLogger("HWR").debug("EMBLSlitBox: beamFocus HO not defined")

    def get_step_sizes(self):
        """Returns Hor and Ver step sizes (list of two values)
        """
        return [self.gaps_dict["Hor"]["stepSize"], self.gaps_dict["Ver"]["stepSize"]]

    def get_min_limits(self):
        """Returns min Hor and Ver gaps values (list of two values)
        """
        return [self.gaps_dict["Hor"]["minGap"], self.gaps_dict["Ver"]["minGap"]]

    def get_max_limits(self):
        """Returns max Hor and Ver gaps values (list of two values)
        """
        return [self.gaps_dict["Hor"]["maxGap"], self.gaps_dict["Ver"]["maxGap"]]

    def get_gap_limits(self, gap_name):
        """Returns gap min and max limits (list of two values)
        """
        return [self.gaps_dict[gap_name]["minGap"], self.gaps_dict[gap_name]["maxGap"]]

    def change_motor_position(self, motor_name, position):
        """Cmd to set motor position

        :param motor_name: motor name
        :type motor_name: str
        :param position: new position
        :type position: float
        """
        for motors_group in self.motors_groups:
            if self.motors_dict[motor_name]["motorsGroup"] == motors_group.username:
                motors_group.set_motor_position(motor_name, position)
                return

    def motors_group_status_changed(self, new_status_dict):
        """Method called if motors group status is changed"""
        for motor in new_status_dict:
            if motor in self.motors_dict:
                self.motors_dict[motor]["status"] = new_status_dict[motor]
                self.gaps_dict[self.motors_dict[motor]["gap"]][
                    "status"
                ] = new_status_dict[motor]
        self.emit(
            "statusChanged",
            ((self.gaps_dict["Hor"]["status"], self.gaps_dict["Ver"]["status"]),),
        )

    def motors_group_position_changed(self, new_positions_dict):
        """Method called if one or sever motors value/s are changed"""
        do_update = False
        for motor in new_positions_dict:
            if motor in self.motors_dict.keys():
                if (
                    abs(self.motors_dict[motor]["position"] - new_positions_dict[motor])
                    > 0.001
                ):
                    self.motors_dict[motor]["position"] = new_positions_dict[motor]
                    do_update = True

        if do_update:
            self.gaps_dict["Hor"]["value"] = self.get_horizontal_gap()
            self.gaps_dict["Ver"]["value"] = self.get_vertical_gap()
            self.emit(
                "valueChanged",
                ([self.gaps_dict["Hor"]["value"], self.gaps_dict["Ver"]["value"]],),
            )

    def get_horizontal_gap(self):
        """Evaluates Horizontal gap"""
        gap = (
            self.motors_dict["In"]["position"]
            - self.motors_dict["In"]["reference"]
            + self.motors_dict["Out"]["position"]
            - self.motors_dict["Out"]["reference"]
        )
        return -gap / (10 ** self.decimal_places)

    def get_vertical_gap(self):
        """Evaluates Vertical gap"""
        gap = (
            self.motors_dict["Top"]["position"]
            - self.motors_dict["Top"]["reference"]
            + self.motors_dict["But"]["position"]
            - self.motors_dict["But"]["reference"]
        )
        return -gap / (10 ** self.decimal_places)

    def get_gaps(self):
        """Returns horizontala and vertical gap values"""
        return self.get_horizontal_gap(), self.get_vertical_gap()

    def set_horizontal_gap(self, new_gap, timeout=None):
        """Sets new gap value"""
        self.set_gap_by_name("Hor", new_gap, timeout)

    def set_vertical_gap(self, new_gap, timeout=None):
        """
        Sets vertical gap
        :param new_gap: float
        :param timeout: int
        :return:
        """
        self.set_gap_by_name("Ver", new_gap, timeout)

    def set_gap_by_name(self, gap_name, new_gap, timeout=None):
        """
        Sets gap by its name
        :param gap_name: Hor or Ver
        :param new_gap: float
        :param timeout: int
        :return:
        """
        old_gap = self.gaps_dict[gap_name]["value"]
        if abs(old_gap - new_gap) > self.gaps_dict[gap_name]["updateTolerance"]:
            for motor in self.motors_dict:
                if self.motors_dict[motor]["gap"] == gap_name:
                    if new_gap > old_gap:
                        new_position = self.motors_dict[motor]["position"] - float(
                            (new_gap - old_gap) / 2 * (10 ** self.decimal_places)
                        )
                    else:
                        new_position = self.motors_dict[motor]["position"] + float(
                            (old_gap - new_gap) / 2 * (10 ** self.decimal_places)
                        )
                    for motor_group in self.motors_groups:
                        if (
                            self.motors_dict[motor]["motorsGroup"]
                            == motor_group.username
                        ):
                            motor_group.set_motor_position(
                                motor, new_position, timeout=timeout
                            )
                            break

    def stop_horizontal_gap_move(self):
        """
        Stops the movement of horizontal gap
        :return:
        """
        self.stop_gap_move("Hor")

    def stop_vertical_gap_move(self):
        """
        Stops the movement of vertical gap
        :return:
        """
        self.stop_gap_move("Ver")

    def stop_gap_move(self, gap_name):
        """Stops motors movements"""
        for motor in self.motors_dict:
            for motors_group in self.motors_groups:
                if motor["motorsGroup"] == motors_group.username:
                    if motor["gap"] == gap_name:
                        motors_group.stop_motor(motor["motorName"])

    def set_focus_mode(self, focus_mode):
        """Sets motors in possitions according to focusing mode"""
        self.active_focus_mode = focus_mode
        for motor in self.motors_dict:
            for motors_group in self.motors_groups_devices:
                if self.motors_dict[motor]["motorsGroup"] == motors_group.username:
                    motors_group.set_motor_focus_mode(motor, focus_mode)

    def focus_mode_changed(self, new_focus_mode, size):
        """Called if focusing mode is changed"""
        if self.active_focus_mode != new_focus_mode:
            self.active_focus_mode = new_focus_mode
            if self.active_focus_mode is not None:
                self.hor_gap_enabled = (
                    self.active_focus_mode in self.gaps_dict["Hor"]["modesAllowed"]
                )
                self.ver_gap_enabled = (
                    self.active_focus_mode in self.gaps_dict["Ver"]["modesAllowed"]
                )
            self.emit(
                "focusModeChanged", ((self.hor_gap_enabled, self.ver_gap_enabled),)
            )

    def set_gaps_limits(self, new_gaps_limits):
        """Sets max gap Limits"""
        if new_gaps_limits is not None:
            self.gaps_dict["Hor"]["maxGap"] = min(
                self.init_max_gaps[0], new_gaps_limits[0]
            )
            self.gaps_dict["Ver"]["maxGap"] = min(
                self.init_max_gaps[1], new_gaps_limits[1]
            )
            self.emit(
                "maxLimitsChanged",
                ([self.gaps_dict["Hor"]["maxGap"], self.gaps_dict["Ver"]["maxGap"]],),
            )

    def re_emit_values(self):
        """Reemits signals"""
        self.emit("focusModeChanged", ((self.hor_gap_enabled, self.ver_gap_enabled),))
        self.emit(
            "valueChanged",
            ([self.gaps_dict["Hor"]["value"], self.gaps_dict["Ver"]["value"]],),
        )
        self.emit(
            "statusChanged",
            ([self.gaps_dict["Hor"]["status"], self.gaps_dict["Ver"]["status"]],),
        )
