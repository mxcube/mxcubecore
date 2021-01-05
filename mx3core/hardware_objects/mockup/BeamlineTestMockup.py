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
BeamlineTestMockup

"""

import os
import logging
import tempfile
from datetime import datetime

import gevent

from mx3core.hardware_objects import SimpleHTML
from mx3core.BaseHardwareObjects import HardwareObject
from mx3core import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]


TEST_DICT = {
    "example_one": "Beamline test example no 1.",
    "example_two": "Beamline test example no 2.",
    "file_system": "File system",
}

TEST_COLORS_TABLE = {False: "#FFCCCC", True: "#CCFFCC"}
TEST_COLORS_FONT = {False: "#FE0000", True: "#007800"}


class BeamlineTestMockup(HardwareObject):
    """BeamlineTestMockup"""

    def __init__(self, name):
        """init"""

        HardwareObject.__init__(self, name)

        self.ready_event = None
        self.test_queue_dict = None
        self.current_test_procedure = None
        self.beamline_name = None
        self.test_directory = None
        self.test_source_directory = None
        self.test_filename = None

        self.available_tests_dict = {}
        self.startup_test_list = []
        self.results_list = None
        self.results_html_list = None

    def init(self):
        """init"""

        self.ready_event = gevent.event.Event()

        self.beamline_name = HWR.beamline.session.beamline_name

        self.test_directory = self.get_property("results_directory")
        if self.test_directory is None:
            self.test_directory = os.path.join(
                tempfile.gettempdir(), "mxcube", "beamline_test"
            )
            logging.getLogger("HWR").debug(
                "BeamlineTest: directory for test "
                "reports not defined. Set to: %s" % self.test_directory
            )
        self.test_source_directory = os.path.join(
            self.test_directory, datetime.now().strftime("%Y_%m_%d_%H") + "_source"
        )

        self.test_filename = "mxcube_test_report"

        try:
            for test in eval(self.get_property("available_tests")):
                self.available_tests_dict[test] = TEST_DICT[test]
        except Exception:
            logging.getLogger("HWR").debug(
                "BeamlineTest: Available tests are "
                + "not defined in xml. Setting all tests as available."
            )
        if self.available_tests_dict is None:
            self.available_tests_dict = TEST_DICT

        try:
            self.startup_test_list = eval(self.get_property("startup_tests"))
        except Exception:
            logging.getLogger("HWR").debug("BeamlineTest: Test list not defined.")

        if self.get_property("run_tests_at_startup") is True:
            self.start_test_queue(self.startup_test_list)

    def start_test_queue(self, test_list, create_report=True):
        """
        Descrip. :
        """
        if create_report:
            try:
                logging.getLogger("HWR").debug(
                    "BeamlineTest: Creating directory %s" % self.test_directory
                )
                if not os.path.exists(self.test_directory):
                    os.makedirs(self.test_directory)

                logging.getLogger("HWR").debug(
                    "BeamlineTest: Creating source directory %s"
                    % self.test_source_directory
                )
                if not os.path.exists(self.test_source_directory):
                    os.makedirs(self.test_source_directory)
            except Exception:
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
                    self.current_test_procedure = gevent.spawn(
                        getattr(self, test_method_name)
                    )
                    test_result = self.current_test_procedure.get()

                    # self.ready_event.wait()
                    # self.ready_event.clear()
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
                    "BeamlineTest: Test method %s not available" % test_method_name
                )
            self.results_html_list.append("</p>\n<hr>")

        # html_filename = None
        if create_report:
            self.generate_html_report()

        # self.emit('testFinished', html_filename)

    def test_example_one(self):
        """Text one"""
        result = {}

        current_energy = HWR.beamline.energy.get_value()

        result["result_bit"] = current_energy < 12
        result["result_short"] = "Test passed (energy = %.2f)" % current_energy
        result["result_details"] = ["An example test that was successful"]
        self.ready_event.set()
        return result

    def test_example_two(self):
        """Text one"""

        result = {}
        result["result_bit"] = False
        result["result_short"] = "Test failed"
        result["result_details"] = ["An example test that failed"]
        self.ready_event.set()
        return result

    def get_available_tests(self):
        """
        Descript. :
        """
        return self.available_tests_dict

    def get_startup_test_list(self):
        """
        Descript. :
        """
        test_list = []
        for test in self.startup_test_list:
            if TEST_DICT.get(test):
                test_list.append(TEST_DICT[test])
        return test_list

    def generate_html_report(self):
        """
        Descript. :
        """
        html_filename = os.path.join(self.test_directory, self.test_filename + ".html")
        # pdf_filename = os.path.join(self.test_directory, self.test_filename + ".pdf")
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
        except Exception:
            logging.getLogger("HWR").error(
                "BeamlineTest: Unable to generate html report file %s" % html_filename
            )

        # try:
        #    pdfkit.from_url(html_filename, pdf_filename)
        #    logging.getLogger("GUI").info("PDF report %s generated" % pdf_filename)
        # except Exception:
        #    logging.getLogger("GUI").info(
        #        "Unable to generate PDF report %s" % pdf_filename
        #    )

        self.emit("testFinished", html_filename)

    def get_result_html(self):
        """
        Descript. :
        """
        html_filename = os.path.join(self.test_directory, self.test_filename + ".html")
        if os.path.exists(html_filename):
            return html_filename
