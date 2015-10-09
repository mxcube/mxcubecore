"""
[Name] BeamTestTool

[Description]
BeamTestTool HO uses beamfocusing HO, ppucontrol HO and md HO to perform 
beamline tests. 

[Channels]

[Commands]

[Emited signals]

[Functions]
 
[Included Hardware Objects]
-----------------------------------------------------------------------
| name             | signals        | functions
-----------------------------------------------------------------------
| beam_focus_hwobj |  		    |  
| ppu_hwobj        |		    |	
| attenuators_hwobj|		    |
| minidiff_hwobj   |                |
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
import time
import gevent
import logging
from csv import reader
from scipy.misc import imsave
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import HardwareObject

TEST_DICT = {"com": "Communication with beamline devices",
             "ppu": "PPU control",
             "profile" : "Beam profile",
             "focus": "Focusing modes",
             "slits": "Slits",
             "aperture": "Aperture",
             "attenuators": "Attenuators",
             "autocentring": "Auto centring procedure"}

HTML_START = '''<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
  <meta content="text/html; charset=ISO-8859-1"
 http-equiv="content-type">
  <title>Beamline test summary</title>
</head>
<body>'''
HTML_END ='''</body>'''

TEST_COLORS_TABLE = {False : '#FFCCCC', True : '#CCFFCC'}
TEST_COLORS_FONT = {False : '#FE0000', True : '#007800'}


class BeamlineTest(HardwareObject):
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

        self.test_list = None 
        self.results_html_list = None

        self.beamline_setup_hwobj = None
        self.beam_focus_hwobj = None
        self.ppu_control_hwobj = None
        self.diffractometer_hwobj = None
        self.test_directory = None

    def init(self):
        """
        Descrip. :
        """
        self.ready_event = gevent.event.Event()
        self.beamline_setup_hwobj = self.getObjectByRole("beamline_setup")

        if self.beamline_setup_hwobj:
            self.beam_focus_hwobj = self.beamline_setup_hwobj.beam_info_hwobj.beam_definer_hwobj
            if self.beam_focus_hwobj is not None:
                self.connect(self.beam_focus_hwobj, "definerPosChanged", self.focus_mode_changed)
            else:
                logging.getLogger("HWR").debug('BeamlineTest: Beam focusing hwobj is not defined')

            self.ppu_hwobj = self.beamline_setup_hwobj.ppu_control_hwobj
            if self.ppu_hwobj is not None:
                self.connect(self.ppu_hwobj, "ppuStatusChanged", self.ppu_status_changed)
            else:
                logging.getLogger("HWR").debug("BeamlineTest: PPU control hwobj is not defined")

            self.diffractometer_hwobj = self.beamline_setup_hwobj.diffractometer_hwobj
            self.beamline_name = self.beamline_setup_hwobj.session_hwobj.beamline_name 
         
        self.csv_file_name = self.getProperty('defaultCsvFileName')
        self.init_device_list()

        try:
            self.test_list = eval(self.getProperty('testList'))
        except:
            logging.getLogger("HWR").warning('BeamTest: Test list not defined.')            
        self.test_directory = str(self.getProperty("resultsDir"))
        if not self.test_directory:
            logging.getLogger("HWR").warning('BeamTest: Test director not defined.') 

    def start_test_queue(self, test_list):
        """
        Descrip. :
        """
        if len(test_list) > 0:
            try:
                logging.getLogger("HWR").debug('BeamTest: Creating directory %s' % self.test_directory)
                if not os.path.exists(self.test_directory):
                    os.makedirs(self.test_directory)
            except:
                logging.getLogger("HWR").warning('BeamTest: Unable to create directory %s' % self.test_directory)
                return 
        else:
            logging.getLogger("HWR").warning('BeamTest: No test for execution defined')
            return

        self.results_html_list = []
        for test_index, test_name in enumerate(test_list):
            test_method_name = "test_" + test_name.lower()
            if hasattr(self, test_method_name):
                if TEST_DICT.has_key(test_name):
                    logging.getLogger("HWR").debug("BeamTest: Executing test %s" % test_name)
                    start_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    self.current_test_procedure = gevent.spawn(getattr(self, test_method_name))
                    test_result = self.current_test_procedure.get()

                    self.ready_event.wait()
                    self.ready_event.clear()
                    end_time = time.strftime("%Y-%m-%d %H:%M:%S")
                   
                    self.results_html_list.append("<h2>%s</h2>" %TEST_DICT[test_name])
                    self.results_html_list.append("Started: %s<br>" %start_time)
                    self.results_html_list.append("Ended: %s<br>" %end_time)
                    self.results_html_list.append("<h3><font color=%s>Result : %s</font></h3>" % \
                                                  (TEST_COLORS_FONT[test_result["result_bit"]],
                                                  test_result["result_short"]))
                    if len(test_result.get("result_details", [])) > 0:
                        self.results_html_list.append("<h3>Detailed results:</h3>")
                        self.results_html_list.extend(test_result["result_details"])
            else:
                 msg = "<h2><font color=%s>Execution method " + \
                       "for test with name %s does not exist</font></h3>"
                 self.results_html_list.append(msg %(TEST_COLORS_FONT[False], test_method_name))
                 logging.getLogger("HWR").error("BeamTest: Test function %s not available" % test_method_name)
            self.results_html_list.append("</p>\n<hr>")

        html_filename = os.path.join(self.test_directory, "mxcube_test_report.html") 
        self.generate_html_report(html_filename)
        #if pdf_filename:
        #    self.generate_pdf_report(pdf_filename)
        self.emit('testFinished', html_filename) 

    def get_image(self):
        """
        Descrip. :
        """
        return

    def focus_mode_changed(self, name, size):
        """
        Descrip. :
        """
        self.emit('focModeChanged')	

    def ppu_status_changed(self, is_error, text):
        """
        Descrip. :
        """
        self.emit('ppuStatusChanged', (is_error, text))

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
            logging.getLogger("HWR").error("BeamTest: %s Devices csv file not found" %self.csv_file_name)

    def get_device_list(self):
        """
        Descrip. :
        """
        return self.devices_list
    
    def get_focus_mode_names(self):	 
        """
        Descrip. :
        """
        if self.beam_focus_hwobj:
            return self.beam_focus_hwobj.get_focus_mode_names()

    def get_focus_motors(self):
        """
        Descript. :
        """
        if self.beam_focus_hwobj is not None:
            return self.beam_focus_hwobj.get_focus_motors()

    def get_focus_mode(self):
        """
        Descript. :
        """
        if self.beam_focus_hwobj is not None:
            return self.beam_focus_hwobj.get_active_focus_mode()

    def set_focus_mode(self, mode):
        """
        Descript. :
        """
        if self.beam_focus_hwobj is not None:
            self.beam_focus_hwobj.set_focus_mode(mode)

    def set_motor_focus_mode(self, motor, mode):
        """
        Descript. :
        """
        if self.beam_focus_hwobj is not None:
            self.beam_focus_hwobj.set_motor_focus_mode(motor, mode)
 
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

    def get_ppu_status(self):
        """
        Descript. :
        """
        if self.ppu_hwobj is not None:
            self.ppu_hwobj.get_status()

    def ppu_restart_all(self):
        """
        Descript. :
        """
        if self.ppu_hwobj is not None:
            self.ppu_hwobj.restart_all()

    def test_com(self):
        """
        Descript. :
        """
        result = {} 
        result_details = ["<table border='1'>"]
        result_details.append("<tr><th>Replied</th><th>DNS name</th><th>IP" + \
                              "</th><th>Location</th><th>MAC address</th>"  + \
                              "<th>Details</th></tr>")
        failed_count = 0
        for row, device in enumerate(self.devices_list):
            try:
                ping_result = os.system("ping -W 2 -c 2 " + device[1]) == 0
                device_result = "<tr bgcolor=%s><td>%s</td>" %  (TEST_COLORS_TABLE[ping_result], ping_result)
                for info in device:
                    device_result += "<td>%s</td>" % info
                device_result += "</tr>"
                result_details.append(device_result)
            except:
                ping_result = False
            if not ping_result:
                failed_count += 1
            self.emit("deviceCommunicationTested", (row, ping_result))
        result_details.append("</table>")

        if failed_count == 0:
            result["result_short"] = "Test passed (got reply from all devices)"
            result["result_bit"] = True
        else:
            result["result_short"] = "Test failed (%d devices from %d did not replied)" % \
                  (failed_count, len(self.devices_list))
            result["result_bit"] = False
        result["result_details"] = result_details  
        self.ready_event.set()
        return result

    def test_ppu(self):
        result = {}
        result["result_bit"] = False
        if self.ppu_hwobj:
            pass
        else:
            result["result_short"]  = "Test failed (ppu hwobj not define)."
        self.ready_event.set()
        return result

    def test_profile(self):
        """
        Descript. : Test to evaluate beam shape with image processing
                    Depending on the parameters apertures, slits and 
                    focusing modes are tested
        """
        result = {}
        result["result_bit"] = False
        result["result_details"] = [] 

        if self.diffractometer_hwobj:
            #got to centring phase

            #check apertures
            table_header = "<table border='1'>\n<tr>" 
            table_values = "<tr>"

            aperture_hwobj = self.beamline_setup_hwobj.beam_info_hwobj.aperture_hwobj 
            aperture_list = aperture_hwobj.get_aperture_list(as_origin=True)
            for index, value in enumerate(aperture_list):
                table_header += "<th>%s</th>" % value 
                aperture_hwobj.set_active_position(index)
                gevent.sleep(1)
                beam_image_filename = os.path.join(self.test_directory, 
                     "aperture_%s.png" % value)
                table_values += "<td><img src=%s style=width:300px;></td>" % beam_image_filename 
                last_frame = self.diffractometer_hwobj.get_last_video_frame()
                #imsave(beam_image_filename, last_frame)
                last_frame.save(beam_image_filename, 'PNG')
            table_header += "</tr>"
            table_values += "</tr>"

            result["result_details"].append(table_header)
            result["result_details"].append(table_values)
            result["result_bit"] = True
            result["result_short"] = "Test passed"
        else:
            result["result_short"] = "Test failed (diffractometer hwobj not define)." 
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
        return TEST_DICT

    def get_test_list(self):
        """
        Descript. :
        """
        test_list = []
        for test in self.test_list:
            if TEST_DICT.get(test):
                test_list.append(TEST_DICT[test]) 
        return test_list

    def generate_html_report(self, html_filename):
        """
        Descript. :
        """
        html_str = HTML_START 

        html_str +="<h1>Beamline %s Test results</h1>" % self.beamline_name
        html_str += "Report filename: %s\n<hr>\n" % html_filename

        for test_result in self.results_html_list:
            html_str += test_result + "\n"

        html_str += HTML_END

        #try:
        if True: 
           output = open(html_filename, "w")
           output.write(html_str)
           output.close()
           self.emit("htmlGenerated", html_filename)
           logging.getLogger("HWR").info("BeamTest: Test result written in file %s" %html_filename)
        #except:
        #   logging.getLogger("HWR").error("BeamTest: Unable to write html report in file %s" %html_filename)
           

    def generate_pdf_report(self, pdf_filename):
        """
        Descript. :
        """
        return

