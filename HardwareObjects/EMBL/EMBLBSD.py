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

"""EMBLBSD (Beam shaping device) represents a diffractometer without a gonio"""

import time
import logging
import gevent

from HardwareRepository.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer,
)


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLBSD(GenericDiffractometer):
    """EMBLBSD represents a diffractometer without a gonio"""

    def __init__(self, *args):
        """Based on the GenericDiffractometer without centering motors"""

        GenericDiffractometer.__init__(self, *args)

        # Hardware objects ----------------------------------------------------
        self.zoom_motor_hwobj = None
        self.omega_reference_motor = None

        # Channels and commands -----------------------------------------------
        self.chan_beamstop_position = None
        self.chan_calib_x = None
        self.chan_calib_y = None
        self.chan_current_phase = None
        self.chan_fast_shutter_is_open = None
        self.chan_state = None
        self.chan_sync_move_motors = None
        self.chan_scintillator_position = None
        self.chan_capillary_position = None
        self.chan_status = None
        self.cmd_start_set_phase = None
        self.cmd_start_auto_focus = None
        self.cmd_save_centring_positions = None

        # Internal values -----------------------------------------------------
        self.use_sc = False
        self.omega_reference_par = None
        self.omega_reference_pos = [0, 0]
        self.current_state = None
        self.fast_shutter_is_open = None

    def init(self):
        """Initiates variables"""

        GenericDiffractometer.init(self)

        self.chan_state = self.get_channel_object("State")
        self.current_state = self.chan_state.getValue()
        self.chan_state.connect_signal("update", self.state_changed)

        self.chan_status = self.get_channel_object("Status")
        self.chan_status.connect_signal("update", self.status_changed)

        self.chan_calib_x = self.get_channel_object("CoaxCamScaleX")
        self.chan_calib_y = self.get_channel_object("CoaxCamScaleY")
        self.update_pixels_per_mm()

        self.chan_current_phase = self.get_channel_object("CurrentPhase")
        self.connect(self.chan_current_phase, "update", self.current_phase_changed)

        self.chan_fast_shutter_is_open = self.get_channel_object("FastShutterIsOpen")
        self.chan_fast_shutter_is_open.connect_signal(
            "update", self.fast_shutter_state_changed
        )

        self.chan_scintillator_position = self.get_channel_object(
            "ScintillatorPosition"
        )
        self.chan_capillary_position = self.get_channel_object("CapillaryPosition")

        self.cmd_start_set_phase = self.get_command_object("startSetPhase")
        self.cmd_start_auto_focus = self.get_command_object("startAutoFocus")

        self.zoom_motor_hwobj = self.get_object_by_role("zoom")
        self.connect(self.zoom_motor_hwobj, "valueChanged", self.zoom_position_changed)
        self.connect(
            self.zoom_motor_hwobj,
            "predefinedPositionChanged",
            self.zoom_motor_predefined_position_changed,
        )

        self.chan_beamstop_position = self.get_channel_object("BeamstopPosition")

    def use_sample_changer(self):
        """Returns true if sample changer is used

        :return: bool
        """
        return False

    def manual_centring(self):
        """No need to implement"""
        return

    def automatic_centring(self):
        """No need to implement"""
        return

    def get_centred_point_from_coord(self):
        """No need to implement"""
        return

    def state_changed(self, state):
        """Emits state change signal"""
        self.current_state = state
        self.emit("minidiffStateChanged", (self.current_state))
        self.emit("minidiffStatusChanged", (self.current_state))

    def status_changed(self, state):
        """Emits status message"""
        self.emit("statusMessage", ("diffractometer", state, "busy"))

    def zoom_position_changed(self, value):
        """After the zoom change updates pixels per mm"""
        self.update_pixels_per_mm()
        self.current_motor_positions["zoom"] = value

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        """Updates pixels per mm when the zoom has been changed"""
        self.update_pixels_per_mm()
        self.emit("zoomMotorPredefinedPositionChanged", (position_name, offset))

    def fast_shutter_state_changed(self, is_open):
        """Stores fast shutter state"""
        self.fast_shutter_is_open = is_open
        if is_open:
            msg = "Opened"
        else:
            msg = "Closed"
        self.emit("minidiffShutterStateChanged", (self.fast_shutter_is_open, msg))

    def update_pixels_per_mm(self, *args):
        """Updates pixels per mm"""
        if self.chan_calib_x:
            self.pixels_per_mm_x = 1.0 / self.chan_calib_x.getValue()
            self.pixels_per_mm_y = 1.0 / self.chan_calib_y.getValue()
            self.emit(
                "pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y),)
            )

    def set_phase(self, phase, timeout=80):
        """Sets diffractometer to the selected phase.
           In the plate mode before going to or away from
           Transfer or Beam location phase if needed then detector
           is moved to the safe distance to avoid collision.
        """
        # self.wait_device_ready(2)
        logging.getLogger("GUI").warning(
            "Diffractometer: Setting %s phase. Please wait..." % phase
        )

        if timeout is not None:
            _start = time.time()
            self.cmd_start_set_phase(phase)
            gevent.sleep(5)
            with gevent.Timeout(
                timeout, Exception("Timeout waiting for phase %s" % phase)
            ):
                while phase != self.chan_current_phase.getValue():
                    gevent.sleep(0.1)
            self.wait_device_ready(30)
            self.wait_device_ready(30)
            _howlong = time.time() - _start
            if _howlong > 11.0:
                logging.getLogger("GUI").error(
                    "Changing phase to %s took %.1f seconds" % (phase, _howlong)
                )
        else:
            self.cmd_start_set_phase(phase)

    def start_auto_focus(self, timeout=None):
        """Autofocus method"""
        if timeout:
            self.ready_event.clear()
            gevent.spawn(self.execute_server_task, self.cmd_start_auto_focus(), timeout)
            self.ready_event.wait()
            self.ready_event.clear()
        else:
            self.cmd_start_auto_focus()

    def emit_diffractometer_moved(self, *args):
        """Emits diffractometerMoved signal"""
        self.emit("diffractometerMoved", ())

    def re_emit_values(self):
        """Reemits all signals"""
        self.emit("minidiffPhaseChanged", (self.current_phase,))
        self.emit("minidiffShutterStateChanged", (self.fast_shutter_is_open,))
        self.emit("pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y),))

    def move_omega(self, angle):
        """No need to implement"""
        return

    def set_zoom(self, position):
        """Sets zoom"""
        self.zoom_motor_hwobj.move_to_position(position)

    def get_osc_limits(self):
        """Return oscillation limits"""
        return (-1e6, 1e6)

    def get_scintillator_position(self):
        """Returns scintillator position"""
        return self.chan_scintillator_position.getValue()

    def set_scintillator_position(self, position):
        """Sets scintillator position"""
        self.chan_scintillator_position.setValue(position)
        with gevent.Timeout(5, Exception("Timeout waiting for scintillator position")):
            while position != self.get_scintillator_position():
                gevent.sleep(0.01)

    def get_capillary_position(self):
        """Returns capillary position"""
        return self.chan_capillary_position.getValue()

    def set_capillary_position(self, position):
        """Moves capillary to requested position"""
        self.chan_capillary_position.setValue(position)
        with gevent.Timeout(5, Exception("Timeout waiting for capillary position")):
            while position != self.get_capillary_position():
                gevent.sleep(0.01)

    def zoom_in(self):
        """Steps zoom one step in"""
        self.zoom_motor_hwobj.zoom_in()

    def zoom_out(self):
        """Steps zoom one step out"""
        self.zoom_motor_hwobj.zoom_out()

    def set_beamstop_park(self):
        """Sets beamstop to the parking position"""
        self.chan_beamstop_position.setValue("PARK")

    def set_beamstop_beam(self):
        """Sets beamstop in the beam position"""
        self.chan_beamstop_position.setValue("BEAM")
