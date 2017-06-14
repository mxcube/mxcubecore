#
#  Project: MXCuBE
#  https://github.com/mxcube.
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

"""
[Name] EMBLBeamlineTest

[Description]
EMBLBeamlineTest HO uses beamfocusing HO, ppucontrol HO and md HO to perform 
beamline tests. 

[Channels]

[Commands]

[Emited signals]

[Functions]
 
[Included Hardware Objects]
-----------------------------------------------------------------------
| name                 | signals        | functions
-----------------------------------------------------------------------
| beamline_setup_hwobj |                |  
-----------------------------------------------------------------------

Example Hardware Object XML file :
==================================
<procedure class="BeamTestTool">
    <defaultCsvFileName>/home/karpics/beamlinesw/trunk/beamline/p14/app/
             beamline-test-tool/p14devicesList.csv</defaultCsvFileName>
    <focusing>/beamFocusing</focusing>
    <ppu>/PPUControl</ppu>
    <md>/minidiffdummy</md>
</procedure>
"""

import os
import tine
import gevent
import logging
import tempfile
from csv import reader
from datetime import datetime

import SimpleHTML
from HardwareRepository.BaseHardwareObjects import HardwareObject


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


TEST_DICT = {"summary": "Beamline summary",
             "com": "Communication with beamline devices",
             "ppu": "PPU control",
             "focusing": "Focusing modes",
             "aperture": "Aperture",
             "alignbeam": "Align beam position",
             "attenuators": "Attenuators",
             "autocentring": "Auto centring procedure"}

TEST_COLORS_TABLE = {False : '#FFCCCC', True : '#CCFFCC'}
TEST_COLORS_FONT = {False : '#FE0000', True : '#007800'}


class EMBLBeamlineTest(HardwareObject):
    """
    Description:
    """

    def __init__(self, name):
        """
        Descrip. :
        """
        HardwareObject.__init__(self, name)

        self.ready_event = None
        self.devices_list = None
        self.csv_file = None
        self.csv_file_name = None
        self.test_queue_dict = None
        self.comm_test = None
        self.current_test_procedure = None
        self.beamline_name = None

        self.available_tests_dict = {}
        self.startup_test_list = []
        self.results_list = None
        self.results_html_list = None
        self.arhive_results = None

        self.bl_hwobj = None
        self.beam_focusing_hwobj = None
        self.graphics_manager_hwobj = None
        self.test_directory = None
        self.test_source_directory = None
        self.test_filename = None

    def init(self):
        """
        Descrip. :
        """
        self.ready_event = gevent.event.Event()
        self.bl_hwobj = self.getObjectByRole("beamline_setup")
        self.graphics_manager_hwobj = self.bl_hwobj.shape_history_hwobj
        self.beam_align_hwobj = self.getObjectByRole("beam_align")

        self.beam_focusing_hwobj = self.bl_hwobj.beam_info_hwobj.beam_focusing_hwobj
        if self.beam_focusing_hwobj:
            self.connect(self.beam_focusing_hwobj, "focusingModeChanged", self.focusing_mode_changed)

        if hasattr(self.bl_hwobj, "ppu_control_hwobj"):
            self.connect(self.bl_hwobj.ppu_control_hwobj, "ppuStatusChanged", self.ppu_status_changed)
        else:
            logging.getLogger("HWR").debug("BeamlineTest: PPU control hwobj is not defined")

        self.beamline_name = self.bl_hwobj.session_hwobj.beamline_name 
        self.csv_file_name = self.getProperty("device_list")
        self.init_device_list()  

        self.test_directory = self.getProperty("results_directory")
        if self.test_directory is None:
            self.test_directory = os.path.join(\
                tempfile.gettempdir(), "mxcube", "beamline_test")
            logging.getLogger("HWR").debug("BeamlineTest: directory for test " \
                "reports not defined. Set to: %s" % self.test_directory)
        self.test_source_directory = os.path.join(\
             self.test_directory,
             datetime.now().strftime("%Y_%m_%d_%H") + "_source")

        self.test_filename = "mxcube_test_report.html"

        try:
            for test in eval(self.getProperty("available_tests")):
                self.available_tests_dict[test] = TEST_DICT[test]
        except:
            logging.getLogger("HWR").debug("BeamlineTest: Available tests are " +\
                "not defined in xml. Setting all tests as available.")
        if self.available_tests_dict is None:
            self.available_tests_dict = TEST_DICT

        try:
            self.startup_test_list = eval(self.getProperty("startup_tests"))
        except:
            logging.getLogger("HWR").debug('BeamlineTest: Test list not defined.')

        if self.getProperty("run_tests_at_startup") == True:
            self.start_test_queue(self.startup_test_list)

        self.arhive_results = self.getProperty("arhive_results")

    def start_test_queue(self, test_list, create_report=True):
        """
        Descrip. :
        """
        if create_report:
            try:
                logging.getLogger("HWR").debug(\
                    "BeamlineTest: Creating directory %s" % \
                    self.test_directory)
                if not os.path.exists(self.test_directory):
                    os.makedirs(self.test_directory)
                
                logging.getLogger("HWR").debug(\
                    "BeamlineTest: Creating source directory %s" % \
                    self.test_source_directory)
                if not os.path.exists(self.test_source_directory):
                    os.makedirs(self.test_source_directory)
            except:
                logging.getLogger("HWR").warning(\
                   "BeamlineTest: Unable to create test directories")
                return 

        self.results_list = []
        self.results_html_list = []
        for test_index, test_name in enumerate(test_list):
            test_method_name = "test_" + test_name.lower()
            if hasattr(self, test_method_name):
                if TEST_DICT.has_key(test_name):
                    logging.getLogger("HWR").debug(\
                         "BeamlineTest: Executing test %s (%s)" \
                         % (test_name, TEST_DICT[test_name]))

                    progress_info = {"progress_total": len(test_list),
                                     "progress_msg": "executing %s" % TEST_DICT[test_name]}
                    self.emit("testProgress", (test_index, progress_info))

                    start_time =  datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.current_test_procedure = gevent.spawn(\
                         getattr(self, test_method_name))
                    test_result = self.current_test_procedure.get()

                    #self.ready_event.wait()
                    #self.ready_event.clear()
                    end_time =  datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.results_list.append({"short_name": test_name,
                                              "full_name": TEST_DICT[test_name],
                                              "result_bit": test_result.get("result_bit", False),
                                              "result_short": test_result.get("result_short", ""),
                                              "start_time": start_time,
                                              "end_time": end_time})
                  
                    self.results_html_list.append("<h2 id=%s>%s</h2>" % \
                         (test_name, TEST_DICT[test_name]))
                    self.results_html_list.append("Started: %s<br>" % \
                         start_time)
                    self.results_html_list.append("Ended: %s<br>" % \
                         end_time)
                    if test_result.get("result_short"):
                        self.results_html_list.append(\
                            "<h3><font color=%s>Result : %s</font></h3>" % \
                            (TEST_COLORS_FONT[test_result["result_bit"]],
                            test_result["result_short"]))
                    if len(test_result.get("result_details", [])) > 0:
                        self.results_html_list.append("<h3>Detailed results:</h3>")
                        self.results_html_list.extend(test_result.get("result_details", []))
            else:
                msg = "<h2><font color=%s>Execution method %s " + \
                      "for the test %s does not exist</font></h3>"
                self.results_html_list.append(msg %(TEST_COLORS_FONT[False], 
                     test_method_name, TEST_DICT[test_name]))
                logging.getLogger("HWR").error("BeamlineTest: Test method %s not available" % test_method_name)
            self.results_html_list.append("</p>\n<hr>")

        html_filename = None
        if create_report: 
            html_filename = os.path.join(self.test_directory, 
                                         self.test_filename)
            self.generate_html_report()

        self.emit('testFinished', html_filename) 

    def init_device_list(self):
        """
        Descrip. :
        """
        self.devices_list = []
        if os.path.exists(self.csv_file_name): 
            with open(self.csv_file_name, 'rb') as csv_file:
                csv_reader = reader(csv_file, delimiter = ',')
                for row in csv_reader:
                    if self.valid_ip(row[1]):
                        self.devices_list.append(row)
            return self.devices_list
        else:
            logging.getLogger("HWR").error("BeamlineTest: Device file %s not found" %self.csv_file_name)

    def get_device_list(self):
        """
        Descrip. :
        """
        return self.devices_list

    def focusing_mode_changed(self, focusing_mode, beam_size):
        """
        Descrip. :
        """
        self.emit("focusingModeChanged", focusing_mode, beam_size)
    
    def get_focus_mode_names(self):	 
        """
        Descrip. :
        """
        if self.beam_focusing_hwobj:
            return self.beam_focusing_hwobj.get_focus_mode_names()

    def get_focus_motors(self):
        """
        Descript. :
        """
        if self.beam_focusing_hwobj is not None:
            return self.beam_focusing_hwobj.get_focus_motors()

    def get_focus_mode(self):
        """
        Descript. :
        """
        if self.beam_focusing_hwobj is not None:
            return self.beam_focusing_hwobj.get_active_focus_mode()
        else:
            return None, None

    def set_focus_mode(self, mode):
        """
        Descript. :
        """
        if self.beam_focusing_hwobj is not None:
            self.beam_focusing_hwobj.set_focus_mode(mode)

    def set_motor_focus_mode(self, motor, mode):
        """
        Descript. :
        """
        if self.beam_focusing_hwobj is not None:
            self.beam_focusing_hwobj.set_motor_focus_mode(motor, mode)
 
    def valid_ip(self, address):
        """
        Descript. :
        """
        parts = address.split(".")
        if len(parts) != 4:
            return False
        for item in parts:
            try:
                if not 0 <= int(item) <= 255:
                    return False
            except:
                return False
        return True

    def ppu_status_changed(self, is_error, text):
        """
        Descrip. :
        """
        self.emit('ppuStatusChanged', (is_error, text))

    def ppu_restart_all(self):
        """
        Descript. :
        """
        if self.bl_hwobj.ppu_control_hwobj is not None:
            self.bl_hwobj.ppu_control_hwobj.restart_all()

    def test_com(self):
        """
        Descript. :
        """
        result = {} 
        table_header = ["Replied", "DNS name", "IP address", "Location",
                        "MAC address", "Details"] 
        table_cells = []
        failed_count = 0
        for row, device in enumerate(self.devices_list):
            msg = "Pinging %s at %s" % (device[0], device[1])
            logging.getLogger("HWR").debug("BeamlineTest: %s" % msg)
            device_result = ["bgcolor=#FFCCCC" , "False"] + device
            try:
                ping_result = os.system("ping -W 2 -c 2 " + device[1]) == 0
                device_result[0] = "bgcolor=%s" % TEST_COLORS_TABLE[ping_result]
                device_result[1] = str(ping_result)
            except:
                ping_result = False
            table_cells.append(device_result) 

            if not ping_result:
                failed_count += 1
            progress_info = {"progress_total": len(self.devices_list),
                             "progress_msg": msg}
            self.emit("testProgress", (row, progress_info))

        result["result_details"] = SimpleHTML.create_table(table_header, table_cells)

        if failed_count == 0:
            result["result_short"] = "Test passed (got reply from all devices)"
            result["result_bit"] = True
        else:
            result["result_short"] = "Test failed (%d devices from %d did not replied)" % \
                  (failed_count, len(self.devices_list))
            result["result_bit"] = False
        self.ready_event.set()
        return result

    def test_ppu(self):
        """
        Descript. :
        """
        result = {}
        if self.bl_hwobj.ppu_control_hwobj:
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
            result["result_short"]  = "Test failed (ppu hwobj not define)."

        self.ready_event.set()
        return result

    def test_aperture(self):
        """
        Descript. : Test to evaluate beam shape with image processing
                    Depending on the parameters apertures, slits and 
                    focusing modes are tested
        """
        result = {}
        result["result_bit"] = False
        result["result_details"] = [] 

        #got to centring phase

        #check apertures
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
            beam_image_filename = os.path.join(\
                self.test_source_directory, 
                "aperture_%s.png" % value)
            table_values += "<td><img src=%s style=width:700px;></td>" % beam_image_filename 
            self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)
            progress_info = {"progress_total": len(aperture_list),
                             "progress_msg": msg}
            self.emit("testProgress", (index, progress_info))

        self.bl_hwobj.diffractometer_hwobj.set_phase(\
             self.bl_hwobj.diffractometer_hwobj.PHASE_CENTRING, timeout = 30)
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

    def test_alignbeam(self):
        """
        Descript. :
        """
        result = {}
        result["result_bit"] = False
        result["result_details"] = []
        result["result_short"] = "Test started"

        self.bl_hwobj.diffractometer_hwobj.set_phase(\
             self.bl_hwobj.diffractometer_hwobj.PHASE_BEAM, timeout = 30)

        result["result_details"].append("Beam shape before alignment<br><br>")
        beam_image_filename = os.path.join(self.test_source_directory,
                                           "align_beam_before.png")
        self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)
        result["result_details"].append("<img src=%s style=width:300px;><br>" % beam_image_filename)

        self.align_beam()
      
        result["result_details"].append("Beam shape after alignment<br><br>") 
        beam_image_filename = os.path.join(self.test_source_directory,
                                           "align_beam_after.png")
        result["result_details"].append("<img src=%s style=width:300px;><br>" % beam_image_filename)
        self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)

        self.bl_hwobj.diffractometer_hwobj.set_phase(\
             self.bl_hwobj.diffractometer_hwobj.PHASE_CENTRING, timeout = 30)

        self.ready_event.set()
        return result

    def align_beam(self):
        """
        Align beam procedure:
        1. Store aperture position and take out the aperture
        2. Store slits position and open to max
        3. In a loop take snapshot and move motors
        4. Put back aperture
        """
        aperture_hwobj = self.bl_hwobj.beam_info_hwobj.aperture_hwobj
        slits_hwobj = self.bl_hwobj.beam_info_hwobj.slits_hwobj 

        #1. Store aperture position and take out the aperture
        progress_info = {"progress_total": 6,
                         "progress_msg": "Setting aperture out"}

        self.emit("testProgress", (1, progress_info))
        aperture_hwobj.set_out() 
        gevent.sleep(5)
    
        #2. Store slits position and open to max
        if slits_hwobj:
            progress_info["progress_msg"] = "Setting slits to the maximum"
            self.emit("testProgress", (2, progress_info))
            hor_gap, ver_gap = slits_hwobj.get_gaps()
            (hor_gap_max, ver_gap_max) = slits_hwobj.get_max_gaps() 

        #3. In a loop take snapshot and move motors


        #4. Put back aperture
        progress_info["progress_msg"] = "Setting aperture in"
        self.emit("testProgress", (6, progress_info))
        aperture_hwobj.set_in()
        gevent.sleep(5)

    def test_autocentring(self):
        """
        Descript. :
        """
        result = {}
        result["result_bit"] = True
        result["result_details"] = []
        result["result_details"].append("Before autocentring<br>")

        beam_image_filename = os.path.join(self.test_source_directory,
                                           "auto_centring_before.png")
        self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)
        result["result_details"].append("<img src=%s style=width:300px;><br>" % beam_image_filename)

        self.bl_hwobj.diffractometer_hwobj.start_centring_method(\
             self.bl_hwobj.diffractometer_hwobj.CENTRING_METHOD_AUTO, wait=True)

        result["result_details"].append("After autocentring<br>")
        beam_image_filename = os.path.join(self.test_source_directory,
                                           "auto_centring_after.png")
        self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)
        result["result_details"].append("<img src=%s style=width:300px;><br>" % beam_image_filename)

        self.ready_event.set()
        return result
 

    def test_summary(self):
        """
        Descript. :
        """
        result = {}
        result["result_bit"] = True
        result["result_details"] = []
        table_cells = []

        for tine_prop in self['tine_props']:
            prop_names = eval(tine_prop.getProperty("prop_names"))
            if isinstance(prop_names, str):
                cell_str_list = []
                cell_str_list.append(tine_prop.getProperty("prop_device"))
                cell_str_list.append(prop_names)
                cell_str_list.append(str(tine.get(tine_prop.getProperty("prop_device"), prop_names)))
                table_cells.append(cell_str_list)
            else:
                for index, property_name in enumerate(prop_names):
                    cell_str_list = []
                    if index == 0:
                        cell_str_list.append(tine_prop.getProperty("prop_device"))
                    else:
                        cell_str_list.append("")
                    cell_str_list.append(property_name)
                    cell_str_list.append(str(tine.get(tine_prop.getProperty("prop_device"), property_name)))
                    table_cells.append(cell_str_list)                    
 
        result["result_details"] = SimpleHTML.create_table(\
             ["Context/Server/Device", "Property", "Value"],
             table_cells)
        self.ready_event.set()
        return result

    def test_focusing(self): 
        """
        Descript. :
        """
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
                table_row.append(motor['motorName'])
                for focus_mode in focus_modes:
                    res = (focus_mode in motor['focMode'])
                    table_row.append("<td bgcolor=%s>%.3f/%.3f</td>" % (\
                         TEST_COLORS_TABLE[res],
                         motor['focusingModes'][focus_mode], 
                         motor['position']))                        
                table_cells.append(table_row)
        
        focus_modes = ["Motors"] + list(focus_modes)
        result["result_details"] = SimpleHTML.create_table(\
              focus_modes, table_cells)
        self.ready_event.set()
        return result
        
    def stop_comm_process(self):
        """
        Descript. :
        """
        if self.current_test_procedure:
            self.current_test_procedure.kill()  
            self.ready_event.set()

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
        html_filename = os.path.join(\
           self.test_directory,
           self.test_filename)
        archive_filename = os.path.join(\
           self.test_directory,
           datetime.now().strftime("%Y_%m_%d_%H") + "_" + \
           self.test_filename)

        try:
            output_file = open(html_filename, "w") 
            output_file.write(SimpleHTML.create_html_start("Beamline test summary"))
            output_file.write("<h1>Beamline %s Test results</h1>" % self.beamline_name)

            output_file.write("<h2>Executed tests:</h2>")
            table_cells = []
            for test in self.results_list:
                table_cells.append(["bgcolor=%s" % TEST_COLORS_TABLE[test["result_bit"]],
                                   "<a href=#%s>%s</a>" % (test["short_name"], test["full_name"]), 
                                   test["result_short"],
                                   test["start_time"],
                                   test["end_time"]])
           
            table_rec = SimpleHTML.create_table(\
                ["Name", "Result", "Start time", "End time"], 
                table_cells)
            for row in table_rec:
                output_file.write(row)
            output_file.write("\n<hr>\n")
         
            for test_result in self.results_html_list:
                output_file.write(test_result + "\n")
      
            output_file.write(SimpleHTML.create_html_end())
            output_file.close()
 
            self.emit("htmlGenerated", html_filename)
            logging.getLogger("HWR").info(\
               "BeamlineTest: Test result written in file %s" % html_filename)
        except:
            logging.getLogger("HWR").error(\
               "BeamlineTest: Unable to generate html report file %s" % html_filename)

        if self.arhive_results:
            try: 
                output_file = open(html_filename, "r")
                archive_file = open(archive_filename, "w")

                for line in output_file.readlines():
                    archive_file.write(line)
                output_file.close()
                archive_file.close()

                logging.getLogger("HWR").info("Archive file :%s generated" % \
                       archive_filename)
            except:
                logging.getLogger("HWR").error("BeamlineTest: Unable to " +\
                       "generate html report file %s" % archive_filename)
           
    def get_result_html(self):
        """
        Descript. :
        """
        html_filename = os.path.join(self.test_directory, self.test_filename)
        if os.path.exists(html_filename):
            return html_filename
 
    def generate_pdf_report(self, pdf_filename):
        """
        Descript. :
        """
        return
