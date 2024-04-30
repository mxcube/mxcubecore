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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
Harvester Maintenance.
"""
import gevent
import logging
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR


class HarvesterMaintenance(HardwareObject):
    __TYPE__ = "HarvesterMaintenance"

    """
    Actual implementation of the Harvester MAINTENANCE,
    COMMANDS, Actions and Calibration procedure, and Centering.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(self):
        self._harvester = self.get_object_by_role("harvester")

    def _do_trash(self):
        """
        Trash sample

        :returns: None
        """
        return self._harvester.trash_sample()

    def _transfer_sample(self):
        """
        Transfer sample

        :returns: None
        """
        return self._harvester.transfer_sample()

    def _load_plate(self, args):
        """
        Load Plate

        :returns: None
        :args: str
        """
        return self._harvester.load_plate(plate_id=args)

    def _set_room_temperature_mode(self, args):
        """
        Set Harvester temperature mode

        :returns: None
        :args: boolean
        """
        return self._harvester.set_room_temperature_mode(args)

    def _do_abort(self):
        """
        Abort current command

        :returns: None
        """
        return self._harvester.abort()

    def _do_park(self):
        """
        Abort and Park (Homing)

        :returns: None
        """
        self._harvester.do_abort()
        return self._harvester.home()

    def _update_global_state(self):
        """
        update global state
        :returns: True
        """
        state_dict, cmd_state, message = self.get_global_state()
        self.emit("globalStateChanged", (state_dict, cmd_state, message))
        return True

    def get_global_state(self):
        """
        update global state
        :returns: True
        """
        state = self._harvester.get_state()
        # ready = self._harvester._is_device_busy()
        running = state in ["RUNNING", "running"]
        plate_ID = self._harvester.get_plate_id()

        state_dict = {
            "running": running,
            "state": state,
            "plate_barecode": plate_ID or "Null",
        }

        cmd_state = {
            "transfer": True,
            "trash": True,
            "park": True,
            "abort": True,
        }

        message = ""

        return state_dict, cmd_state, message

    def get_cmd_info(self):
        """return information about existing commands for this object"""
        """ [cmd_id, cmd_display_name, nb_args, cmd_category, description ] """

        cmd_list = [
            [
                "Actions",
                [
                    ["transfer", "Transfer sample", "Actions", None],
                    ["trash", "Trash sample", "Actions", None],
                    ["park", "Park", "Actions", None],
                    ["abort", "Abort", "Actions", None],
                ],
            ],
        ]

        return cmd_list

    def send_command(self, cmd_name, args=None):
        if cmd_name in ["park"]:
            self._do_park()
        if cmd_name == "trash":
            self._do_trash()
        if cmd_name == "transfer":
            self._transfer_sample()
        if cmd_name == "abort":
            self._do_abort()
        if cmd_name == "loadPlateWithBarcode":
            self._load_plate(args)
        if cmd_name == "set_room_temperature_mode":
            self._set_room_temperature_mode(args)
        return True

    def calibrate_pin(self) -> bool:
        """
            Pin Calibration Procedure
            In other for the Centring procedure to work on a Harvested Pin
            a Calibration Procedure need to be execute

        Return (bool): whether the calibration procedure goes to end (True)
        or had and exception (False)
        """

        self._harvester.load_calibrated_pin()
        self._harvester._wait_sample_transfer_ready(None)
        print("waiting 40 seconds before mount")
        # For some reason the Harvester return READY too soon
        # approximately 40 Second sooner
        gevent.sleep(40)
        sample_mount_device = HWR.beamline.sample_changer
        mount_current_sample = sample_mount_device.load_a_pin_for_calibration()

        if mount_current_sample:
            try:
                md = HWR.beamline.diffractometer
                md._wait_ready()

                sample_drift_x = float(self._harvester.get_last_sample_drift_offset_x())
                sample_drift_y = float(self._harvester.get_last_sample_drift_offset_y())
                sample_drift_z = float(
                    -self._harvester.get_last_sample_drift_offset_z()
                )

                motor_pos_dict = {
                    "kappa": float(
                        md["HacentringReferencePosition"].get_property("kappa_ref")
                    ),
                    "kappa_phi": float(
                        md["HacentringReferencePosition"].get_property("phi_ref")
                    ),
                    "phi": float(
                        md["HacentringReferencePosition"].get_property("omega_ref")
                    ),
                    "phiy": md.phiyMotor.get_value() + sample_drift_x,
                }

                md.move_motors(motor_pos_dict)
                md._wait_ready()
                md.centringFocus.set_value_relative(sample_drift_z, None)
                md.centringVertical.set_value_relative(sample_drift_y, None)

                md.save_current_motor_position()
                self._harvester.calibration_state(True)

                logging.getLogger("user_level_log").info(
                    "Pin Calibration Step 1 Succeed"
                )
                logging.getLogger("user_level_log").info(
                    "User Need to Perform an  3 click centring"
                )
                return True
            except Exception:
                logging.getLogger("user_level_log").exception("Pin Calibration Failed")
                return False
        else:
            logging.getLogger("user_level_log").error("Pin Calibration Failed")
            logging.getLogger("user_level_log").error(
                "Sample Changer could not mount Pin"
            )
            return False

    def validate_calibration(self) -> bool:
        """
        finish Calibration Procedure step 2
        after user ran a 3 click centering
        Return (bool): whether the step 2 of calibration procedure
        goes to end (True) or had and exception (False)
        """
        try:
            md = HWR.beamline.diffractometer

            motor_pos_dict = {
                "focus": md.focusMotor.get_value(),
                "phiy": md.phiyMotor.get_value(),
                "phiz": md.phizMotor.get_value(),
                "centring_focus": md.centringFocus.get_value(),
                "centring_vertical": md.centringVertical.get_value(),
            }

            saved_position = md.saved_motor_position
            # find offset position based on old and new motor position
            new_motor_offset = {
                "focus": motor_pos_dict["focus"] - saved_position["focus"],
                "phiy": motor_pos_dict["phiy"] - saved_position["phiy"],
                "phiz": motor_pos_dict["phiz"] - saved_position["phiz"],
                "centring_focus": (
                    motor_pos_dict["centring_focus"] - saved_position["centring_focus"]
                ),
                "centring_vertical": (
                    motor_pos_dict["centring_vertical"]
                    - saved_position["centring_vertical"]
                ),
            }

            calibrated_motor_offset = {
                "focus": new_motor_offset["focus"] + new_motor_offset["centring_focus"],
                "phiy": new_motor_offset["phiy"],
                "phiz": (
                    new_motor_offset["phiz"] + new_motor_offset["centring_vertical"]
                ),
            }

            # we store the motor offset in the Harvester, to be used for sample centering
            self._harvester.store_calibrated_pin(
                calibrated_motor_offset["focus"],
                calibrated_motor_offset["phiy"],
                calibrated_motor_offset["phiz"],
            )

            self._harvester.set_calibration_state(False)
        except Exception:
            logging.getLogger("user_level_log").exception(
                "Pin Calibration / validation Failed"
            )
            return False

        return True
