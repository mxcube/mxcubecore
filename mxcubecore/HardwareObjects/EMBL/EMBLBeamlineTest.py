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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import ast
import logging
import tempfile
from time import sleep
from datetime import datetime

import tine
import gevent
from scipy.interpolate import interp1d

from HardwareRepository.HardwareObjects import SimpleHTML
from HardwareRepository.BaseHardwareObjects import HardwareObject

__credits__ = ["EMBL Hamburg"]
__category__ = "General"


TEST_DICT = {
    "ppu": "PPU control",
    "focusing": "Focusing modes",
    "aperture": "Aperture",
    "centerbeam": "Beam centering",
    "autocentring": "Auto centring procedure",
    "file_system": "File system",
}

TEST_COLORS_TABLE = {False: "#FFCCCC", True: "#CCFFCC"}
TEST_COLORS_FONT = {False: "#FE0000", True: "#007800"}


class EMBLBeamlineTest(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.ready_event = None
        self.user_clicked_event = None
        self.test_queue_dict = None
        self.current_test_procedure = None
        self.beamline_name = None
        self.test_directory = None
        self.test_filename = None

        self.scale_hor = None
        self.scale_ver = None
        self.scale_double_hor = None
        self.scale_double_ver = None
        self.scan_status = None

        self.available_tests_dict = {}
        self.startup_test_list = []
        self.results_list = None
        self.results_html_list = None

        self.chan_encoder_ar = None
        self.chan_qbpm_ar = None
        self.chan_pitch_position_ar = None
        self.chan_pitch_scan_status = None
        self.cmd_set_pitch_position = None
        self.cmd_set_pitch = None
        self.cmd_start_pitch_scan = None
        self.cmd_set_vmax_pitch = None
        self.cmd_set_qbmp_range = None

        self.bl_hwobj = None
        self.crl_hwobj = None
        self.beam_focusing_hwobj = None
        self.graphics_manager_hwobj = None
        self.horizontal_motor_hwobj = None
        self.vertical_motor_hwobj = None
        self.horizontal_double_mode_motor_hwobj = None
        self.vertical_double_mode_motor_hwobj = None
        self.graphics_manager_hwobj = None

    def init(self):
        """Reads config xml, initiates all necessary hwobj, channels and cmds
        """
        self.ready_event = gevent.event.Event()
        self.scale_hor = self.getProperty("scale_hor")
        self.scale_ver = self.getProperty("scale_ver")
        self.scale_double_hor = self.getProperty("scale_double_hor")
        self.scale_double_ver = self.getProperty("scale_double_ver")
        self.chan_pitch_scan_status = self.getChannelObject("chanPitchScanStatus")
        self.connect(
            self.chan_pitch_scan_status, "update", self.pitch_scan_status_changed
        )
        self.chan_qbpm_ar = self.getChannelObject("chanQBPMAr")
        self.chan_pitch_position_ar = self.getChannelObject("chanPitchPositionAr")
        self.cmd_set_pitch_position = self.getCommandObject("cmdSetPitchPosition")
        self.cmd_set_pitch = self.getCommandObject("cmdSetPitch")
        self.cmd_start_pitch_scan = self.getCommandObject("cmdStartPitchScan")
        self.cmd_set_vmax_pitch = self.getCommandObject("cmdSetVMaxPitch")

        self.horizontal_motor_hwobj = self.getObjectByRole("horizontal_motor")
        self.vertical_motor_hwobj = self.getObjectByRole("vertical_motor")
        self.horizontal_double_mode_motor_hwobj = self.getObjectByRole(
            "horizontal_double_mode_motor"
        )
        self.vertical_double_mode_motor_hwobj = self.getObjectByRole(
            "vertical_double_mode_motor"
        )

        self.bl_hwobj = self.getObjectByRole("beamline_setup")
        self.crl_hwobj = self.getObjectByRole("crl")
        self.graphics_manager_hwobj = self.bl_hwobj.shape_history_hwobj
        self.connect(
            self.graphics_manager_hwobj, "imageDoubleClicked", self.image_double_clicked
        )
        self.connect(
            self.bl_hwobj.energy_hwobj, "beamAlignmentRequested", self.center_beam_test
        )

        if hasattr(self.bl_hwobj.beam_info_hwobj, "beam_focusing_hwobj"):
            self.beam_focusing_hwobj = self.bl_hwobj.beam_info_hwobj.beam_focusing_hwobj
            self.connect(
                self.beam_focusing_hwobj,
                "focusingModeChanged",
                self.focusing_mode_changed,
            )
        else:
            logging.getLogger("HWR").debug(
                "BeamlineTest: Beam focusing hwobj is not defined"
            )

        if hasattr(self.bl_hwobj, "ppu_control_hwobj"):
            self.connect(
                self.bl_hwobj.ppu_control_hwobj,
                "ppuStatusChanged",
                self.ppu_status_changed,
            )
        else:
            logging.getLogger("HWR").warning(
                "BeamlineTest: PPU control hwobj is not defined"
            )

        self.beamline_name = self.bl_hwobj.session_hwobj.beamline_name

        self.test_directory = self.getProperty("results_directory")
        if self.test_directory is None:
            self.test_directory = os.path.join(
                tempfile.gettempdir(), "mxcube", "beamline_test"
            )
            msg = (
                "BeamlineTest: Directory for test reports not defined. Set to: %s"
                % self.test_directory
            )
            logging.getLogger("HWR").debug(msg)

        self.test_filename = "mxcube_test_report"

        try:
            for test in ast.literal_eval(self.getProperty("available_tests", "[]")):
                self.available_tests_dict[test] = TEST_DICT[test]
        except BaseException:
            logging.getLogger("HWR").debug(
                "BeamlineTest: No test define in xml. All tests as available."
            )
        if self.available_tests_dict is None:
            self.available_tests_dict = TEST_DICT

        if self.getProperty("startup_tests"):
            self.startup_test_list = ast.literal_eval(self.getProperty("startup_tests"))

        if self.getProperty("run_tests_at_startup"):
            gevent.spawn_later(5, self.start_test_queue, self.startup_test_list)

        self.cmd_set_qbmp_range = self.getCommandObject("cmdQBPMRangeSet")

    def start_test_queue(self, test_list, create_report=True):
        """Runs a list of tests

        :param test_list: list of tests
        :type test_list: list of str
        :param create_report: create html and pdf reports
        :type create_report: bool
        """
        if create_report:
            try:
                msg = "BeamlineTest: Creating directory %s" % self.test_directory
                logging.getLogger("HWR").debug(msg)

                if not os.path.exists(self.test_directory):
                    os.makedirs(self.test_directory)

            except BaseException:
                logging.getLogger("HWR").warning(
                    "BeamlineTest: Unable to create test directories"
                )
                return

        self.results_list = []
        self.results_html_list = []
        for test_index, test_name in enumerate(test_list):
            test_method_name = "test_" + test_name.lower()
            if hasattr(self, test_method_name):
                if test_name in TEST_DICT:
                    msg = "BeamlineTest: Executing test %s (%s)" % (
                        test_name,
                        TEST_DICT[test_name],
                    )
                    logging.getLogger("HWR").debug(msg)

                    progress_info = {
                        "progress_total": len(test_list),
                        "progress_msg": "executing %s" % TEST_DICT[test_name],
                    }
                    self.emit("testProgress", (test_index, progress_info))

                    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # self.current_test_procedure = gevent.spawn(\
                    test_result = getattr(self, test_method_name)()
                    # test_result = self.current_test_procedure.get()

                    self.ready_event.wait()
                    self.ready_event.clear()
                    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.results_list.append(
                        {
                            "short_name": test_name,
                            "full_name": TEST_DICT[test_name],
                            "result_bit": test_result.get("result_bit", False),
                            "result_short": test_result.get("result_short", ""),
                            "start_time": start_time,
                            "end_time": end_time,
                        }
                    )

                    self.results_html_list.append(
                        "<h2 id=%s>%s</h2>" % (test_name, TEST_DICT[test_name])
                    )
                    self.results_html_list.append("Started: %s<br>" % start_time)
                    self.results_html_list.append("Ended: %s<br>" % end_time)
                    if test_result.get("result_short"):
                        self.results_html_list.append(
                            "<h3><font color=%s>Result : %s</font></h3>"
                            % (
                                TEST_COLORS_FONT[test_result["result_bit"]],
                                test_result["result_short"],
                            )
                        )
                    if test_result.get("result_details", []) > 0:
                        self.results_html_list.append("<h3>Detailed results:</h3>")
                        self.results_html_list.extend(
                            test_result.get("result_details", [])
                        )
                    self.emit("progressStop", ())
            else:
                msg = (
                    "<h2><font color=%s>Execution method %s "
                    + "for the test %s does not exist</font></h3>"
                )
                self.results_html_list.append(
                    msg
                    % (TEST_COLORS_FONT[False], test_method_name, TEST_DICT[test_name])
                )
                msg = "BeamlineTest: Test method %s is not available" % test_method_name
                logging.getLogger("HWR").error(msg)

            self.results_html_list.append("</p>\n<hr>")

        html_filename = None
        if create_report:
            html_filename = (
                os.path.join(self.test_directory, self.test_filename) + ".html"
            )
            self.generate_report()

        self.emit("testFinished", html_filename)

    def image_double_clicked(self, x, y):
        if self.user_clicked_event is not None:
            self.user_clicked_event.set((x, y))

    def focusing_mode_changed(self, focusing_mode, beam_size):
        """Reemits focusing changed signal

        :param focusing_mode: focusing mode
        :type focusing_mode: str
        :param beam_size: beam size in microns
        :type beam_size: list with two int
        """
        self.emit("focusingModeChanged", focusing_mode, beam_size)

    def get_focus_mode_names(self):
        """Returns available focusing mode names"""
        if self.beam_focusing_hwobj:
            return self.beam_focusing_hwobj.get_focus_mode_names()

    def get_focus_motors(self):
        """Returns focusing motor hwobj"""
        if self.beam_focusing_hwobj is not None:
            return self.beam_focusing_hwobj.get_focus_motors()

    def get_focus_mode(self):
        """Returns active focusing mode"""
        if self.beam_focusing_hwobj is not None:
            return self.beam_focusing_hwobj.get_active_focus_mode()
        else:
            return "Collimated", None

    def set_focus_mode(self, mode):
        """Sets focusing mode

        :param mode: selected focusing mode
        :type mode: str
        """
        if self.beam_focusing_hwobj is not None:
            self.beam_focusing_hwobj.set_focus_mode(mode)

    def set_motor_focus_mode(self, motor, mode):
        """Sets focusing mode to a single motor

        :param motor: motor name
        :type motor: str
        :param mode: focusing mode
        :type mode: str
        """
        if self.beam_focusing_hwobj is not None:
            self.beam_focusing_hwobj.set_motor_focus_mode(motor, mode)

    def ppu_status_changed(self, is_error, text):
        """Reemits ppu status changed signal

        :param is_error: is error
        :type is_error: bool
        :param text: error message
        :type text: str
        """
        self.emit("ppuStatusChanged", (is_error, text))

    def ppu_restart_all(self):
        """Restart ppu processes"""
        if self.bl_hwobj.ppu_control_hwobj is not None:
            self.bl_hwobj.ppu_control_hwobj.restart_all()

    def pitch_scan(self):
        """
        Starts pitch scan and returns when status is ready
        :return:
        """
        self.cmd_set_pitch_position(0)
        self.cmd_set_pitch(1)
        sleep(3)
        self.cmd_start_pitch_scan(1)
        # sleep(30.0)
        with gevent.Timeout(10, Exception("Timeout waiting for pitch scan ready")):
            while self.chan_pitch_scan_status.getValue() != 0:
                gevent.sleep(0.1)
        self.cmd_set_vmax_pitch(1)
        sleep(3)

    def test_aperture(self):
        """Test to evaluate beam shape with image processing
           Depending on the parameters apertures, slits and
           focusing modes are tested
        """
        result = {}
        result["result_bit"] = False
        result["result_details"] = []

        # got to centring phase

        # check apertures
        table_header = "<table border='1'>\n<tr>"
        table_values = "<tr>"
        table_result = "<tr>"

        self.bl_hwobj.diffractometer_hwobj.set_phase("BeamLocation", timeout=30)

        aperture_hwobj = self.bl_hwobj.beam_info_hwobj.aperture_hwobj
        aperture_list = aperture_hwobj.get_aperture_list(as_origin=True)
        current_aperture = aperture_hwobj.get_value()

        for index, value in enumerate(aperture_list):
            msg = "Selecting aperture %s " % value
            table_header += "<th>%s</th>" % value
            aperture_hwobj.set_active_position(index)
            gevent.sleep(1)
            beam_image_filename = os.path.join(
                self.test_directory, "aperture_%s.png" % value
            )
            table_values += (
                "<td><img src=%s style=width:700px;></td>" % beam_image_filename
            )
            self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)
            progress_info = {"progress_total": len(aperture_list), "progress_msg": msg}
            self.emit("testProgress", (index, progress_info))

        self.bl_hwobj.diffractometer_hwobj.set_phase(
            self.bl_hwobj.diffractometer_hwobj.PHASE_CENTRING, timeout=30
        )
        aperture_hwobj.set_active_position(current_aperture)
        table_header += "</tr>"
        table_values += "</tr>"

        result["result_details"].append(table_header)
        result["result_details"].append(table_values)
        result["result_details"].append(table_result)
        result["result_details"].append("</table>")
        result["result_bit"] = True
        self.ready_event.set()

        return result

    def start_center_beam_manual(self):
        """Starts manual beam centering procedure"""
        gevent.spawn(self.center_beam_manual_procedure)

    def center_beam_manual_procedure(self):
        """Manual beam centering procedure"""
        self.user_clicked_event = gevent.event.AsyncResult()
        x, y = self.user_clicked_event.get()
        self.user_clicked_event = None

    def test_centerbeam(self):
        """Beam centering procedure"""

        result = {}
        result["result_bit"] = True
        result["result_details"] = []
        result["result_short"] = "Test started"

        result["result_details"].append("Beam profile before centring<br>")
        result["result_details"].append(
            "<img src=%s style=width:300px;>"
            % os.path.join(self.test_directory, "beam_image_before.png")
        )
        result["result_details"].append(
            "<img src=%s style=width:300px;><br><br>"
            % os.path.join(self.test_directory, "beam_profile_before.png")
        )

        self.center_beam_test()

        result["result_details"].append("Beam profile after centring<br>")
        result["result_details"].append(
            "<img src=%s style=width:300px;>"
            % os.path.join(self.test_directory, "beam_image_after.png")
        )
        result["result_details"].append(
            "<img src=%s style=width:300px;><br><br>"
            % os.path.join(self.test_directory, "beam_profile_after.png")
        )

        result["result_short"] = "Beam centering finished"

        self.ready_event.set()
        return result

    def center_beam_test(self):
        """Calls gevent task to center beam"""
        gevent.spawn(self.center_beam_test_task)

    def center_beam_test_task(self):
        """Centers beam in a following procedure:
            1. Store aperture position and take out the aperture
            2. Store slits position and open to max
            3. Do pitch scan if possible
            3. In a loop take snapshot and move motors
            4. Put back aperture and move to original slits positions
        """
        log = logging.getLogger("GUI")

        if not self.bl_hwobj.safety_shutter_hwobj.is_opened():
            log.error(
                "Beam centering failed! Safety shutter is closed! "
                + "Open the shutter to continue."
            )
            self.ready_event.set()
            return

        aperture_hwobj = self.bl_hwobj.beam_info_hwobj.aperture_hwobj
        current_energy = self.bl_hwobj.energy_hwobj.get_current_energy()
        current_transmission = self.bl_hwobj.transmission_hwobj.get_transmission()

        msg = "Starting beam centring"
        progress_info = {"progress_total": 6, "progress_msg": msg}
        log.info("Beam centering: %s" % msg)
        self.emit("testProgress", (1, progress_info))
        self.emit("progressInit", ("Beam centering...", 6, True))

        # 1/6 Diffractometer in BeamLocation phase ---------------------------
        msg = "1/6 : Setting diffractometer in BeamLocation phase"
        progress_info["progress_msg"] = msg
        log.info("Beam centering: %s" % msg)
        self.emit("testProgress", (2, progress_info))
        self.emit("progressStep", 1, "Setting diffractometer in BeamLocation phase")

        self.bl_hwobj.diffractometer_hwobj.wait_device_ready(10)
        self.bl_hwobj.diffractometer_hwobj.set_phase(
            self.bl_hwobj.diffractometer_hwobj.PHASE_BEAM, timeout=45
        )

        self.bl_hwobj.fast_shutter_hwobj.openShutter()
        gevent.sleep(0.1)
        aperture_hwobj.set_out()

        msg = (
            "2/6 : Adjusting transmission to the current energy %.1f keV"
            % current_energy
        )
        progress_info["progress_msg"] = msg
        log.info("Beam centering: %s" % msg)
        self.emit("testProgress", (2, progress_info))
        self.emit("progressStep", 2, "Adjusting transmission")

        if current_energy < 7:
            new_transmission = 100
        else:
            energy_transm = interp1d([6.9, 8.0, 12.7, 19.0], [100.0, 60.0, 15.0, 10])
            new_transmission = round(energy_transm(current_energy), 2)

        if self.bl_hwobj.session_hwobj.beamline_name == "P13":
            self.bl_hwobj.transmission_hwobj.set_transmission(
                new_transmission, timeout=45
            )
            self.bl_hwobj.diffractometer_hwobj.set_zoom("Zoom 4")
            # capillary_position = (
            #    self.bl_hwobj.diffractometer_hwobj.get_capillary_position()
            # )
            self.bl_hwobj.diffractometer_hwobj.set_capillary_position("OFF")

            gevent.sleep(1)
            self.center_beam_task()
        else:
            slits_hwobj = self.bl_hwobj.beam_info_hwobj.slits_hwobj

            active_mode, beam_size = self.get_focus_mode()

            if active_mode in ("Collimated", "Imaging"):
                self.bl_hwobj.transmission_hwobj.set_transmission(
                    new_transmission, timeout=45
                )
                self.bl_hwobj.diffractometer_hwobj.set_zoom("Zoom 4")
            else:
                # 2% transmission for beam centering in double foucused mode
                self.bl_hwobj.transmission_hwobj.set_value(
                    2, timeout=45
                )  # Transmission(2, timeout=45)
                self.bl_hwobj.diffractometer_hwobj.set_zoom("Zoom 8")

            msg = "3/6 : Opening slits to 1 x 1 mm"
            progress_info["progress_msg"] = msg
            log.info("Beam centering: %s" % msg)
            self.emit("testProgress", (2, progress_info))
            self.emit("progressStep", 3, "Opening slits to 1x1 mm")

            # GB: keep standard slits settings for double foucsed mode
            if active_mode in ("Collimated", "Imaging"):
                slits_hwobj.set_vertical_gap(1.0)  # "Hor", 1.0)
                slits_hwobj.set_horizontal_gap(1.0)  # "Ver", 1.0)

            # self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)

            # Actual centring procedure  ---------------

            beam_task_result = self.center_beam_task()
            if not beam_task_result:
                log.error("Beam centering: Failed")
                self.emit("progressStop", ())
                self.ready_event.set()
                return

            # 5/6 For unfocused mode setting slits to 0.1 x 0.1 mm ---------------
            if active_mode in ("Collimated", "Imaging"):
                msg = "5/6 : Setting slits to 0.1 x 0.1 mm"
                progress_info["progress_msg"] = msg
                log.info("Beam centering: %s" % msg)
                self.emit("testProgress", (5, progress_info))

                slits_hwobj.set_horizontal_gap(0.1)  # "Hor", 0.1)
                slits_hwobj.set_vertical_gap(0.1)  # "Ver", 0.1)
                sleep(3)

            # 6/6 Update position of the beam mark position ----------------------
            msg = "6/6 : Updating beam mark position"
            self.emit("progressStep", 6, "Updating beam mark position")
            progress_info["progress_msg"] = msg
            log.info("Beam centering: %s" % msg)
            self.emit("testProgress", (6, progress_info))
            self.graphics_manager_hwobj.move_beam_mark_auto()

        self.bl_hwobj.transmission_hwobj.set_transmission(
            current_transmission
        )  # Transmission(current_transmission)

        self.graphics_manager_hwobj.graphics_beam_item.set_detected_beam_position(
            None, None
        )

        msg = "Done"
        progress_info["progress_msg"] = msg
        log.info("Beam centering: %s" % msg)
        self.emit("testProgress", (6, progress_info))
        self.emit("progressStop", ())
        self.ready_event.set()

    def center_beam_task(self):
        """Calls pitch scan and 3 times detects beam shape and
           moves horizontal and vertical motors.
        """
        log = logging.getLogger("GUI")
        msg = ""
        progress_info = {"progress_total": 6, "progress_msg": msg}

        if self.bl_hwobj.session_hwobj.beamline_name == "P13":
            # Beam centering procedure for P13 ---------------------------------

            msg = "4/6 : Executing pitch scan"
            progress_info["progress_msg"] = msg
            log.info("Beam centering: %s" % msg)
            self.emit("testProgress", (3, progress_info))
            self.emit("progressStep", 3, "Executing pitch scan")

            if self.bl_hwobj._get_energy() <= 8.75:
                self.cmd_set_qbmp_range(0)
            else:
                self.cmd_set_qbmp_range(1)
            gevent.sleep(0.2)
            self.cmd_set_pitch_position(0)
            self.cmd_set_pitch(1)

            gevent.sleep(0.2)
            self.cmd_start_pitch_scan(1)

            gevent.sleep(3)
            with gevent.Timeout(10, Exception("Timeout waiting for pitch scan ready")):
                while self.chan_pitch_scan_status.getValue() == 1:
                    gevent.sleep(0.1)
            gevent.sleep(3)
            self.cmd_set_vmax_pitch(1)

            qbpm_arr = self.chan_qbpm_ar.getValue()
            if max(qbpm_arr) < 10:
                log.error("Beam alignment failed! Pitch scan failed.")
                self.emit("progressStop", ())
                return

            self.emit(
                "progressStep", 4, "Detecting beam position and centering the beam"
            )

            for i in range(3):
                with gevent.Timeout(10, False):
                    beam_pos_displacement = [None, None]
                    while None in beam_pos_displacement:
                        beam_pos_displacement = self.graphics_manager_hwobj.get_beam_displacement(
                            reference="beam"
                        )
                        gevent.sleep(0.1)
                if None in beam_pos_displacement:
                    log.error("Beam alignment failed! Unable to detect beam position.")
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

                msg = "Beam centering: Applying %.4f mm horizontal " % delta_hor
                +"and %.4f mm vertical correction" % delta_ver
                log.info(msg)

                if abs(delta_hor) > 0.0001:
                    log.info("Beam centering: Moving horizontal by %.4f" % delta_hor)
                    self.horizontal_motor_hwobj.move_relative(delta_hor)
                    sleep(5)
                if abs(delta_ver) > 0.0001:
                    log.info("Beam centering: Moving vertical by %.4f" % delta_ver)
                    self.vertical_motor_hwobj.move_relative(delta_ver)
                    sleep(5)

        else:
            # Beam centering procedure for P14 -----------------------------------
            # 3.1/6 If energy < 10: set all lenses in ----------------------------
            active_mode, beam_size = self.get_focus_mode()

            # 4/6 Applying Perp and Roll2nd correction ------------------------
            # if active_mode == "Collimated":
            if True:
                msg = "4/6 : Applying Perp and Roll2nd correction"
                progress_info["progress_msg"] = msg
                log.info("Beam centering: %s" % msg)
                self.emit("testProgress", (4, progress_info))
                self.emit(
                    "progressStep", 4, "Detecting beam position and centering the beam"
                )
                delta_ver = 1.0

                for i in range(5):
                    if abs(delta_ver) > 0.100:
                        self.cmd_set_pitch_position(0)
                        self.cmd_set_pitch(1)
                        gevent.sleep(0.1)

                        if self.bl_hwobj._get_energy() < 10:
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
                            while self.chan_pitch_scan_status.getValue() != 0:
                                gevent.sleep(0.1)
                        self.cmd_set_vmax_pitch(1)

                        # GB : return original lenses only after scan finished
                        if self.bl_hwobj._get_energy() < 10:
                            self.crl_hwobj.set_crl_value(crl_value, timeout=30)
                        sleep(2)

                    with gevent.Timeout(10, False):
                        beam_pos_displacement = [None, None]
                        while None in beam_pos_displacement:
                            beam_pos_displacement = self.graphics_manager_hwobj.get_beam_displacement(
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
                            * self.bl_hwobj._get_energy()
                            / 12.70
                        )
                        delta_ver = beam_pos_displacement[1] * self.scale_ver
                    else:
                        delta_hor = beam_pos_displacement[0] * self.scale_double_hor
                        delta_ver = (
                            beam_pos_displacement[1] * self.scale_double_ver * 0.5
                        )

                    log.info(
                        "Measured beam displacement: Horizontal "
                        + "%.4f mm, Vertical %.4f mm" % beam_pos_displacement
                    )

                    # if abs(delta_ver) > 0.050 :
                    #    delta_ver *= 0.5

                    log.info(
                        "Applying %.4f mm horizontal " % delta_hor
                        + "and %.4f mm vertical motor correction" % delta_ver
                    )

                    if active_mode in ("Collimated", "Imaging"):
                        if abs(delta_hor) > 0.0001:
                            log.info("Moving horizontal by %.4f" % delta_hor)
                            self.horizontal_motor_hwobj.move_relative(
                                delta_hor, timeout=5
                            )
                            sleep(4)
                        if abs(delta_ver) > 0.100:
                            log.info("Moving vertical motor by %.4f" % delta_ver)
                            # self.vertical_motor_hwobj.move_relative(delta_ver, timeout=5)
                            tine.set(
                                "/p14/P14MonoMotor/Perp",
                                "IncrementMove.START",
                                delta_ver * 0.5,
                            )
                            sleep(6)
                        else:
                            log.info("Moving vertical piezo by %.4f" % delta_ver)
                            self.vertical_motor_hwobj.move_relative(
                                -1.0 * delta_ver, timeout=5
                            )
                            sleep(2)
                    elif active_mode == "Double":
                        if abs(delta_hor) > 0.0001:
                            log.info("Moving horizontal by %.4f" % delta_hor)
                            self.horizontal_double_mode_motor_hwobj.move_relative(
                                delta_hor, timeout=5
                            )
                            sleep(2)
                        if abs(delta_ver) > 0.001:
                            log.info("Moving vertical by %.4f" % delta_ver)
                            self.vertical_double_mode_motor_hwobj.move_relative(
                                delta_ver, timeout=5
                            )
                            sleep(2)
        return True

    def pitch_scan_status_changed(self, status):
        """Store pitch scan status"""
        self.scan_status = status

    def test_autocentring(self):
        """Tests autocentring"""
        result = {}
        result["result_bit"] = True
        result["result_details"] = []
        result["result_details"].append("Before autocentring<br>")

        beam_image_filename = os.path.join(
            self.test_directory, "auto_centring_before.png"
        )
        self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)
        gevent.sleep(0.1)
        result["result_details"].append(
            "<img src=%s style=width:300px;><br>" % beam_image_filename
        )

        self.bl_hwobj.diffractometer_hwobj.start_centring_method(
            self.bl_hwobj.diffractometer_hwobj.CENTRING_METHOD_AUTO, wait=True
        )

        result["result_details"].append("After autocentring<br>")
        beam_image_filename = os.path.join(
            self.test_directory, "auto_centring_after.png"
        )
        self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)
        result["result_details"].append(
            "<img src=%s style=width:300px;><br>" % beam_image_filename
        )

        self.ready_event.set()

        return result

    def test_focusing(self):
        """Tests focusing"""
        result = {}
        result["result_details"] = []

        active_mode, beam_size = self.get_focus_mode()
        if active_mode is None:
            result["result_bit"] = False
            result["result_short"] = "No focusing mode detected"
        else:
            result["result_bit"] = True
            result["result_short"] = "%s mode detected" % active_mode

        focus_modes = self.get_focus_mode_names()
        focus_motors_list = self.get_focus_motors()

        table_cells = []
        if focus_motors_list:
            for motor in focus_motors_list:
                table_row = []
                table_row.append(motor["motorName"])
                for focus_mode in focus_modes:
                    res = focus_mode in motor["focMode"]
                    table_row.append(
                        "<td bgcolor=%s>%.3f/%.3f</td>"
                        % (
                            TEST_COLORS_TABLE[res],
                            motor["focusingModes"][focus_mode],
                            motor["position"],
                        )
                    )
                table_cells.append(table_row)

        focus_modes = ["Motors"] + list(focus_modes)
        result["result_details"] = SimpleHTML.create_table(focus_modes, table_cells)

        self.ready_event.set()

        return result

    def measure_flux(self):
        """Measures intesity"""
        self.bl_hwobj.flux_hwobj.measure_flux()

    def test_file_system(self):
        result = {}
        result["result_bit"] = False
        result["result_short"] = "Failed"
        result["result_details"] = []

        self.ready_event.set()

        if result["result_bit"]:
            self.emit("statusMessage", ("file_system", "check", "success"))
        else:
            self.emit("statusMessage", ("file_system", "check", "error"))

        return result

    def get_available_tests(self):
        """Returns a list with available tests"""
        return self.available_tests_dict

    def get_startup_test_list(self):
        """Returns a list with tests defined at startup"""
        test_list = []
        for test in self.startup_test_list:
            if TEST_DICT.get(test):
                test_list.append(TEST_DICT[test])
        return test_list

    def generate_report(self):
        """Generates html and pdf report"""
        html_filename = os.path.join(self.test_directory, self.test_filename) + ".html"

        try:
            output_file = open(html_filename, "w")
            output_file.write(SimpleHTML.create_html_start("Beamline test summary"))
            output_file.write("<h1>Beamline %s Test results</h1>" % self.beamline_name)
            output_file.write("<h2>Executed tests:</h2>")
            table_cells = []
            for test in self.results_list:
                table_cells.append(
                    [
                        "bgcolor=%s" % TEST_COLORS_TABLE[test["result_bit"]],
                        "<a href=#%s>%s</a>" % (test["short_name"], test["full_name"]),
                        test["result_short"],
                        test["start_time"],
                        test["end_time"],
                    ]
                )

            table_rec = SimpleHTML.create_table(
                ["Name", "Result", "Start time", "End time"], table_cells
            )
            for row in table_rec:
                output_file.write(row)
            output_file.write("\n<hr>\n")

            for test_result in self.results_html_list:
                output_file.write(test_result + "\n")

            output_file.write(SimpleHTML.create_html_end())
            output_file.close()

            self.emit("htmlGenerated", html_filename)
            msg = "BeamlineTest: Test result written in file %s" % html_filename
            logging.getLogger("HWR").info(msg)
        except BaseException:
            msg = "BeamlineTest: Unable to generate html report file %s" % html_filename
            logging.getLogger("HWR").error(msg)

        self.emit("testFinished", html_filename)

    def get_result_html(self):
        """Returns html filename"""
        html_filename = os.path.join(self.test_directory, self.test_filename) + ".html"
        if os.path.exists(html_filename):
            return html_filename
        else:
            return
