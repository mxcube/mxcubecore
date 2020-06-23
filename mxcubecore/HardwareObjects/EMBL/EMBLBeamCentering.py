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
from time import sleep
import gevent
from scipy.interpolate import interp1d
import tine

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__category__ = "General"


class EMBLBeamCentering(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.ready_event = None
        self.scale_hor = None
        self.scale_ver = None
        self.scale_double_hor = None
        self.scale_double_ver = None
        self.scan_status = None

        self.chan_pitch_scan_status = None
        # self.chan_qbpm_ar = None
        self.chan_pitch_position_ar = None
        self.cmd_set_pitch_position = None
        self.cmd_set_pitch = None
        self.cmd_start_pitch_scan = None
        self.cmd_set_vmax_pitch = None
        self.cmd_set_qbmp_range = None

        self.crl_hwobj = None
        self.beam_focusing_hwobj = None
        self.horizontal_motor_hwobj = None
        self.vertical_motor_hwobj = None
        self.horizontal_double_mode_motor_hwobj = None
        self.vertical_double_mode_motor_hwobj = None

    def init(self):
        """Reads config xml, initiates all necessary hwobj, channels and cmds
        """
        self.ready_event = gevent.event.Event()

        self.scale_hor = self.get_property("scale_hor")
        self.scale_ver = self.get_property("scale_ver")
        self.scale_double_hor = self.get_property("scale_double_hor")
        self.scale_double_ver = self.get_property("scale_double_ver")
        self.chan_pitch_scan_status = self.get_channel_object("chanPitchScanStatus")
        self.connect(
            self.chan_pitch_scan_status, "update", self.pitch_scan_status_changed
        )

        # self.chan_qbpm_ar = self.get_channel_object("chanQBPMAr")

        self.chan_pitch_position_ar = self.get_channel_object("chanPitchPositionAr")
        self.cmd_set_pitch_position = self.get_command_object("cmdSetPitchPosition")
        self.cmd_set_pitch = self.get_command_object("cmdSetPitch")
        self.cmd_start_pitch_scan = self.get_command_object("cmdStartPitchScan")
        self.cmd_set_vmax_pitch = self.get_command_object("cmdSetVMaxPitch")
        self.cmd_set_qbmp_range = self.get_command_object("cmdQBPMRangeSet")

        self.horizontal_motor_hwobj = self.get_object_by_role("horizontal_motor")
        self.vertical_motor_hwobj = self.get_object_by_role("vertical_motor")
        self.horizontal_double_mode_motor_hwobj = self.get_object_by_role(
            "horizontal_double_mode_motor"
        )
        self.vertical_double_mode_motor_hwobj = self.get_object_by_role(
            "vertical_double_mode_motor"
        )

        # self.chan_pitch_second = self.get_channel_object("chanPitchSecond")
        self.crl_hwobj = self.get_object_by_role("crl")
        self.connect(HWR.beamline.energy, "beamAlignmentRequested", self.center_beam)

        if hasattr(HWR.beamline.beam, "beam_focusing_hwobj"):
            self.beam_focusing_hwobj = HWR.beamline.beam.beam_focusing_hwobj
            self.connect(
                self.beam_focusing_hwobj,
                "focusingModeChanged",
                self.focusing_mode_changed,
            )
        else:
            logging.getLogger("HWR").debug(
                "BeamlineTest: Beam focusing hwobj is not defined"
            )

    def focusing_mode_changed(self, focusing_mode, beam_size):
        """Reemits focusing changed signal

        :param focusing_mode: focusing mode
        :type focusing_mode: str
        :param beam_size: beam size in microns
        :type beam_size: list with two int
        """
        self.emit("focusingModeChanged", focusing_mode, beam_size)

    def get_focus_mode(self):
        """Returns active focusing mode"""
        if self.beam_focusing_hwobj is not None:
            return self.beam_focusing_hwobj.get_active_focus_mode()
        else:
            return "Collimated", None

    def pitch_scan(self):
        self.cmd_start_pitch_scan(1)
        sleep(3)
        with gevent.Timeout(20, Exception("Timeout waiting for pitch scan ready")):
            while self.scan_status != 0:  # chan_pitch_scan_status.get_value() != 0:
                gevent.sleep(0.1)
                logging.getLogger("HWR").error("scan status %s" % self.scan_status)
        self.cmd_set_vmax_pitch(1)
        sleep(3)

    def center_beam(self):
        """Calls gevent task to center beam"""
        gevent.spawn(self.center_beam_task)

    def center_beam_task(self):
        """Centers beam in a following procedure:
            1. Store aperture position and take out the aperture
            2. Store slits position and open to max
            3. Do pitch scan if possible
            3. In a loop take snapshot and move motors
            4. Put back aperture and move to original slits positions
        """
        gui_log = logging.getLogger("GUI")
        log_msg = ""

        if not HWR.beamline.safety_shutter.is_opened():
            log_msg = "Beam centering failed! Safety shutter is closed! Open the shutter to continue."

            gui_log.error(log_msg)
            self.ready_event.set()
            return

        aperture_hwobj = HWR.beamline.beam.aperture
        current_energy = HWR.beamline.energy.get_value()
        current_transmission = HWR.transmission.get_value()
        active_mode, beam_size = self.get_focus_mode()

        log_msg = "Beam centering: Active mode %s" % active_mode
        gui_log.info(log_msg)

        if active_mode in ("Imaging", "TREXX"):

            log_msg = "Beam centering: doing pitch scan only"
            gui_log.info(log_msg)

            if current_energy < 10:
                crl_value = self.crl_hwobj.get_crl_value()
                self.crl_hwobj.set_crl_value([1, 1, 1, 1, 1, 1], timeout=30)

            self.cmd_start_pitch_scan(1)
            gevent.sleep(2.0)

            with gevent.Timeout(
                10, RuntimeError("Timeout waiting for pitch scan ready")
            ):
                while self.chan_pitch_scan_status.get_value() != 0:
                    gevent.sleep(0.1)
            self.cmd_set_vmax_pitch(1)

            if current_energy < 10:
                self.crl_hwobj.set_crl_value(crl_value, timeout=30)
                sleep(2)
            gui_log.info("Beam centering: done")
            self.ready_event.set()
            return

        try:
            step = 1
            log_msg = "Starting beam centring"
            gui_log.info("Beam centering: %s" % log_msg)
            self.emit("progressInit", ("Beam centering...", 20, True))

            # Diffractometer in BeamLocation phase ---------------------------
            msg = "Setting diffractometer in BeamLocation phase"
            gui_log.info("Beam centering: %s" % msg)
            self.emit("progressStep", step, msg)

            HWR.beamline.diffractometer.wait_device_ready(10)
            HWR.beamline.diffractometer.set_phase(
                HWR.beamline.diffractometer.PHASE_BEAM, timeout=45
            )

            # Open the fast shutter and set aperture out  --------------------

            step += 1
            log_msg = "Opening fast shutter and setting aperture out"
            gui_log.info("Beam centering: %s" % log_msg)
            self.emit("progressStep", step, log_msg)

            HWR.beamline.fast_shutter.openShutter()
            gevent.sleep(0.1)
            aperture_hwobj.set_out()

            # Adjust transmission ---------------------------------------------
            step += 1
            log_msg = (
                "Adjusting transmission to the current energy %.1f keV" % current_energy
            )
            gui_log.info("Beam centering: %s" % log_msg)
            self.emit("progressStep", step, log_msg)

            if current_energy < 7:
                new_transmission = 100
            else:
                energy_transm = interp1d(
                    [6.9, 8.0, 12.7, 19.0], [100.0, 60.0, 15.0, 10]
                )
                new_transmission = round(energy_transm(current_energy), 2)

            if HWR.beamline.session.beamline_name == "P13":
                HWR.beamline.transmission.set_value(  # Transmission(
                    new_transmission, timeout=45
                )
                HWR.beamline.diffractometer.set_zoom(
                    "Zoom 4"
                )  # was 4, use 1 with broken zoom motor
                # capillary_position = (
                #    HWR.beamline.diffractometer.get_capillary_position()
                # )
                HWR.beamline.diffractometer.set_capillary_position("OFF")

                gevent.sleep(1)
                self.move_beam_to_center()
            else:
                slits_hwobj = HWR.beamline.beam.slits

                if active_mode in ("Collimated", "Imaging", "TREXX"):
                    HWR.beamline.transmission.set_value(  # Transmission(
                        new_transmission, timeout=45
                    )
                    HWR.beamline.diffractometer.set_zoom("Zoom 4")
                else:
                    # 2% transmission for beam centering in double foucused mode
                    HWR.beamline.transmission.set_value(2, timeout=45)
                    HWR.beamline.diffractometer.set_zoom("Zoom 8")

                step += 1
                log_msg = "Opening slits to 1 x 1 mm"
                gui_log.info("Beam centering: %s" % log_msg)
                self.emit("progressStep", step, log_msg)

                # GB: keep standard slits settings for double foucsed mode
                if active_mode in ("Collimated", "Imaging", "TREXX"):
                    slits_hwobj.set_vertical_gap(1.0)  # "Hor", 1.0)
                    slits_hwobj.set_horizontal_gap(1.0)  # "Ver", 1.0)

                # Actual centring procedure  ---------------

                result = self.move_beam_to_center()
                if not result:
                    gui_log.error("Beam centering: Failed")
                    self.emit("progressStop", ())
                    self.ready_event.set()
                    return

                # For unfocused mode setting slits to 0.1 x 0.1 mm ---------------
                if active_mode in ("Collimated", "Imaging", "TREXX"):
                    step += 1
                    log_msg = "Setting slits to 0.1 x 0.1 mm"
                    gui_log.info("Beam centering: %s" % log_msg)
                    self.emit("progressStep", step, log_msg)

                    slits_hwobj.set_horizontal_gap(0.1)  # "Hor", 0.1)
                    slits_hwobj.set_vertical_gap(0.1)  # "Ver", 0.1)
                    sleep(3)

                # Update position of the beam mark position ----------------------
                step += 1
                log_msg = "Updating beam mark position"
                self.emit("progressStep", step, log_msg)
                gui_log.info("Beam centering: %s" % log_msg)

                HWR.beamline.sample_view.move_beam_mark_auto()

            HWR.beamline.transmission.set_value(current_transmission)
            HWR.beamline.sample_view.graphics_beam_item.set_detected_beam_position(
                None, None
            )

            log_msg = "Done"
            gui_log.info("Beam centering: %s" % log_msg)
            self.emit("progressStop", ())
            self.ready_event.set()

        except Exception as ex:
            log_msg = "Beam centering failed in the step: %s (%s)" % (log_msg, str(ex))
            gui_log.error(log_msg)
            self.emit("progressStop", ())
            self.ready_event.set()
            return False

        finally:
            HWR.beamline.fast_shutter.closeShutter(wait=False)

    def move_beam_to_center(self):
        """Calls pitch scan and 3 times detects beam shape and
           moves horizontal and vertical motors.
        """
        gui_log = logging.getLogger("GUI")
        gui_msg = ""
        step = 10
        finished = False

        try:
            if HWR.beamline.session.beamline_name == "P13":
                # Beam centering procedure for P13 ---------------------------------

                log_msg = "Executing pitch scan"
                gui_log.info("Beam centering: %s" % log_msg)
                self.emit("progressStep", step, log_msg)

                if HWR.beamline.energy.get_value() <= 8.75:
                    self.cmd_set_qbmp_range(0)
                else:
                    self.cmd_set_qbmp_range(1)

                gevent.sleep(0.2)
                self.cmd_start_pitch_scan(1)
                gevent.sleep(3)

                with gevent.Timeout(
                    20, Exception("Timeout waiting for pitch scan ready")
                ):
                    while self.chan_pitch_scan_status.get_value() == 1:
                        gevent.sleep(0.1)
                gevent.sleep(3)
                self.cmd_set_vmax_pitch(1)

                """
                qbpm_arr = self.chan_qbpm_ar.get_value()
                if max(qbpm_arr) < 10:
                    gui_log.error("Beam alignment failed! Pitch scan failed.")
                    self.emit("progressStop", ())
                    return
                """

                step += 1
                log_msg = "Detecting beam position and centering the beam"
                gui_log.info("Beam centering: %s" % log_msg)
                self.emit("progressStep", step, log_msg)

                for i in range(3):
                    with gevent.Timeout(10, False):
                        beam_pos_displacement = [None, None]
                        while None in beam_pos_displacement:
                            beam_pos_displacement = HWR.beamline.sample_view.get_beam_displacement(
                                reference="beam"
                            )
                            gevent.sleep(0.1)
                    if None in beam_pos_displacement:
                        log_msg = (
                            "Beam alignment failed! Unable to detect beam position."
                        )
                        gui_log.error(log_msg)
                        self.emit("progressStop", ())
                        return

                    delta_hor = beam_pos_displacement[0] * self.scale_hor
                    delta_ver = beam_pos_displacement[1] * self.scale_ver

                    if delta_hor > 0.03:
                        delta_hor = 0.03
                    if delta_hor < -0.03:
                        delta_hor = -0.03
                    if delta_ver > 0.03:
                        delta_ver = 0.03
                    if delta_ver < -0.03:
                        delta_ver = -0.03

                    log_msg = (
                        "Beam centering: Applying %.4f mm horizontal " % delta_hor
                        + "and %.4f mm vertical correction" % delta_ver
                    )
                    gui_log.info(log_msg)

                    if abs(delta_hor) > 0.0001:
                        log_msg = (
                            "Beam centering: Moving horizontal by %.4f" % delta_hor
                        )
                        gui_log.info(log_msg)
                        self.horizontal_motor_hwobj.set_value_relative(delta_hor)
                        sleep(5)
                    if abs(delta_ver) > 0.0001:
                        log_msg = "Beam centering: Moving vertical by %.4f" % delta_ver
                        gui_log.info(log_msg)
                        self.vertical_motor_hwobj.set_value_relative(delta_ver)
                        sleep(5)

            else:
                # Beam centering procedure for P14 -----------------------------------
                # If energy < 10: set all lenses in ----------------------------
                active_mode, beam_size = self.get_focus_mode()
                log_msg = "Applying Perp and Roll2nd correction"
                gui_log.info("Beam centering: %s" % log_msg)
                self.emit("progressStep", step, log_msg)
                delta_ver = 1.0

                for i in range(5):
                    if abs(delta_ver) > 0.100:
                        self.cmd_set_pitch_position(0)
                        self.cmd_set_pitch(1)
                        gevent.sleep(0.1)

                        if HWR.beamline.energy.get_value() < 10:
                            crl_value = self.crl_hwobj.get_crl_value()
                            self.crl_hwobj.set_crl_value([1, 1, 1, 1, 1, 1], timeout=30)

                        self.cmd_start_pitch_scan(1)

                        # GB : keep lenses in the beam during the scan
                        # if self.bl_hwobj._get_energy() < 10:
                        #   self.crl_hwobj.set_crl_value(crl_value, timeout=30)

                        gevent.sleep(2.0)

                        with gevent.Timeout(
                            10, RuntimeError("Timeout waiting for pitch scan ready")
                        ):
                            while self.chan_pitch_scan_status.get_value() != 0:
                                gevent.sleep(0.1)
                        self.cmd_set_vmax_pitch(1)

                        # GB : return original lenses only after scan finished
                        if HWR.beamline.energy.get_value() < 10:
                            self.crl_hwobj.set_crl_value(crl_value, timeout=30)
                        sleep(2)

                    with gevent.Timeout(10, False):
                        beam_pos_displacement = [None, None]
                        while None in beam_pos_displacement:
                            beam_pos_displacement = HWR.beamline.sample_view.get_beam_displacement(
                                reference="screen"
                            )
                            gevent.sleep(0.1)
                    if None in beam_pos_displacement:
                        # log.debug("No beam detected")
                        return
                    if active_mode in ("Collimated", "Imaging"):
                        delta_hor = (
                            beam_pos_displacement[0]
                            * self.scale_hor
                            * HWR.beamline.energy.get_value()
                            / 12.70
                        )
                        delta_ver = beam_pos_displacement[1] * self.scale_ver
                    else:
                        delta_hor = beam_pos_displacement[0] * self.scale_double_hor
                        delta_ver = (
                            beam_pos_displacement[1] * self.scale_double_ver * 0.5
                        )

                    log_msg = (
                        "Measured beam displacement: Horizontal "
                        + "%.4f mm, Vertical %.4f mm" % beam_pos_displacement
                    )
                    gui_log.info(log_msg)

                    # if abs(delta_ver) > 0.050 :
                    #    delta_ver *= 0.5

                    log_msg = (
                        "Applying %.4f mm horizontal " % delta_hor
                        + "and %.4f mm vertical motor correction" % delta_ver
                    )
                    gui_log.info(log_msg)

                    if active_mode in ("Collimated", "Imaging"):
                        if abs(delta_hor) > 0.0001:
                            log_msg = "Moving horizontal by %.4f" % delta_hor
                            gui_log.info(log_msg)
                            self.horizontal_motor_hwobj.set_value_relative(
                                delta_hor, timeout=5
                            )
                            sleep(4)
                        if abs(delta_ver) > 0.100:
                            log_msg = "Moving vertical motor by %.4f" % delta_ver
                            gui_log.info(log_msg)
                            # self.vertical_motor_hwobj.set_value_relative(delta_ver, timeout=5)
                            tine.set(
                                "/p14/P14MonoMotor/Perp",
                                "IncrementMove.START",
                                delta_ver * 0.5,
                            )
                            sleep(6)
                        else:
                            log_msg = "Moving vertical piezo by %.4f" % delta_ver
                            gui_log.info(log_msg)
                            self.vertical_motor_hwobj.set_value_relative(
                                -1.0 * delta_ver, timeout=5
                            )
                            sleep(2)

                    elif active_mode == "Double":
                        if abs(delta_hor) > 0.0001:
                            log_msg = "Moving horizontal by %.4f" % delta_hor
                            gui_log.info(log_msg)
                            self.horizontal_double_mode_motor_hwobj.set_value_relative(
                                delta_hor, timeout=5
                            )
                            sleep(2)
                        if abs(delta_ver) > 0.001:
                            log_msg = "Moving vertical by %.4f" % delta_ver
                            gui_log.info(log_msg)
                            self.vertical_double_mode_motor_hwobj.set_value_relative(
                                delta_ver, timeout=5
                            )
                            sleep(2)
            finished = True
        except BaseException:
            gui_log.error("Beam centering failed")
            finished = False
        finally:
            return finished

    def pitch_scan_status_changed(self, status):
        """Store pitch scan status"""
        self.scan_status = status
