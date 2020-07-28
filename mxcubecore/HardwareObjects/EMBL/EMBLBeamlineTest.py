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

import os
import tine
import numpy
import gevent
import logging
import tempfile

import numpy as np


from csv import reader
from time import sleep
from datetime import datetime
from random import random
from scipy.interpolate import interp1d
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

# try:
#    import pdfkit
# except BaseException:
#    logging.getLogger("HWR").warning("pdfkit not available")

from HardwareRepository.HardwareObjects import SimpleHTML
from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


TEST_DICT = {
    "ppu": "PPU control",
    "focusing": "Focusing modes",
    "centerbeam": "Beam centering",
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

        self.available_tests_dict = {}
        self.startup_test_list = []
        self.results_list = None
        self.results_html_list = None

        self.bl_hwobj = None
        self.beam_focusing_hwobj = None

    def init(self):
        """Reads config xml, initiates all necessary hwobj, channels and cmds
        """
        self.ready_event = gevent.event.Event()

        self.bl_hwobj = self.get_object_by_role("beamline_setup")
        self.test_filename = "mxcube_test_report"

        try:
            for test in eval(self.get_property("available_tests", "[]")):
                self.available_tests_dict[test] = TEST_DICT[test]
        except BaseException:
            logging.getLogger("HWR").debug(
                "BeamlineTest: No test define in xml. "
                + "Setting all tests as available."
            )
        if self.available_tests_dict is None:
            self.available_tests_dict = TEST_DICT

        if self.get_property("startup_tests"):
            self.startup_test_list = eval(self.get_property("startup_tests"))

        if self.get_property("run_tests_at_startup") == True:
            gevent.spawn_later(5, self.start_test_queue, self.startup_test_list)

    def start_test_queue(self, test_list, create_report=True):
        """Runs a list of tests

        :param test_list: list of tests
        :type test_list: list of str
        :param create_report: create html and pdf reports
        :type create_report: bool
        """
        if create_report:
            try:
                logging.getLogger("HWR").debug(
                    "BeamlineTest: Creating directory %s" % self.test_directory
                )
                if not os.path.exists(self.test_directory):
                    os.makedirs(self.test_directory)

                logging.getLogger("HWR").debug(
                    "BeamlineTest: Creating source directory %s" % self.test_directory
                )
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
                    logging.getLogger("HWR").debug(
                        "BeamlineTest: Executing test %s (%s)"
                        % (test_name, TEST_DICT[test_name])
                    )

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
                    if len(test_result.get("result_details", [])) > 0:
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
                logging.getLogger("HWR").error(
                    "BeamlineTest: Test method " + "%s not available" % test_method_name
                )
            self.results_html_list.append("</p>\n<hr>")

        html_filename = None
        if create_report:
            html_filename = (
                os.path.join(self.test_directory, self.test_filename) + ".html"
            )
            self.generate_report()

        self.emit("testFinished", html_filename)

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

    def test_ppu(self):
        """Test ppu"""
        result = {}
        if self.bl_hwobj.ppu_control_hwobj is not None:
            is_error, msg = self.bl_hwobj.ppu_control_hwobj.get_status()
            result["result_bit"] = not is_error
            if result["result_bit"]:
                result["result_short"] = "Test passed"
            else:
                result["result_short"] = "Test failed"

            msg = msg.replace("\n", "\n<br>")
            result["result_details"] = msg.split("\n")
        else:
            result["result_bit"] = False
            result["result_short"] = "Test failed (ppu hwobj not define)."

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

    def stop_comm_process(self):
        """Stops pinging"""
        if self.current_test_procedure:
            self.current_test_procedure.kill()
            self.ready_event.set()

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
        pdf_filename = os.path.join(self.test_directory, self.test_filename) + ".pdf"
        archive_filename = os.path.join(
            self.test_directory,
            datetime.now().strftime("%Y_%m_%d_%H") + "_" + self.test_filename,
        )

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
            logging.getLogger("HWR").info(
                "BeamlineTest: Test result written in file %s" % html_filename
            )
        except BaseException:
            logging.getLogger("HWR").error(
                "BeamlineTest: Unable to generate html report file %s" % html_filename
            )

        # try:
        #    pdfkit.from_url(html_filename, pdf_filename)
        #    logging.getLogger("GUI").info("PDF report %s generated" % pdf_filename)
        # except BaseException:
        #    logging.getLogger("HWR").error(
        #        "BeamlineTest: Unable to generate pdf report file %s" % pdf_filename
        #    )

        self.emit("testFinished", html_filename)

    def get_result_html(self):
        """Returns html filename"""
        html_filename = os.path.join(self.test_directory, self.test_filename) + ".html"
        if os.path.exists(html_filename):
            return html_filename

    def test_method(self):
        print("Test")
