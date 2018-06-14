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

try:
    import pdfkit
except:
    logging.getLogger("HWR").warning("pdfkit not available")

import SimpleHTML
from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


TEST_DICT = {"summary": "Beamline summary",
             "com": "Communication with beamline devices",
             "ppu": "PPU control",
             "focusing": "Focusing modes",
             "aperture": "Aperture",
             "centerbeam": "Beam centering",
             "attenuators": "Attenuators",
             "autocentring": "Auto centring procedure",
             "measure_intensity": "Intensity measurement",
             "sc_stats": "Sample changer statistics",
             "graph": "Graph"}

TEST_COLORS_TABLE = {False : '#FFCCCC', True : '#CCFFCC'}
TEST_COLORS_FONT = {False : '#FE0000', True : '#007800'}


class EMBLBeamlineTest(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.ready_event = None
        self.user_clicked_event = None
        self.devices_list = None
        self.csv_file = None
        self.csv_file_name = None
        self.test_queue_dict = None
        self.comm_test = None
        self.current_test_procedure = None
        self.beamline_name = None
        self.test_directory = None
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
        self.graph_values = [[], []]
        self.intensity_measurements = []
        self.ampl_chan_index = None
        self.intensity_ranges = []
        self.intensity_value = None

        self.chan_encoder_ar = None
        #self.chan_qbpm_ar = None
        self.chan_pitch_position_ar = None
        self.chan_pitch_scan_status = None
        self.chan_intens_range = None
        self.chan_intens_mean = None
        self.cmd_set_pitch_position = None
        self.cmd_set_pitch = None
        self.cmd_start_pitch_scan = None
        self.cmd_set_vmax_pitch = None
        self.cmd_set_intens_acq_time = None
        self.cmd_set_intens_range = None
        self.cmd_set_intens_resolution = None
     
        self.bl_hwobj = None
        self.crl_hwobj = None
        self.beam_focusing_hwobj = None
        self.graphics_manager_hwobj = None
        self.horizontal_motor_hwobj = None
        self.vertical_motor_hwobj = None
        self.horizontal_double_mode_motor_hwobj = None
        self.vertical_double_mode_motor_hwobj = None
        self.graphics_manager_hwobj = None

        self.diode_calibration_amp_per_watt = interp1d(\
              [3.99, 6., 8., 10., 12., 12.5, 15., 16., 20., 30.],
              [0.2267, 0.2116, 0.1405, 0.086, 0.0484, 0.0469,
               0.0289, 0.0240, 0.01248, 0.00388])

        self.air_absorption_coeff_per_meter = interp1d(\
               [3.99, 6.6, 9.2, 11.8, 14.4, 17., 19.6, 22.2, 24.8, 27.4, 30],
               [9.19440446, 2.0317802, 0.73628084, 0.34554261,
                0.19176669, 0.12030697, 0.08331135, 0.06203213,
                0.04926173, 0.04114024, 0.0357374])
        self.carbon_window_transmission = interp1d(\
               [3.99, 6.6, 9.2, 11.8, 14.4, 17., 19.6, 22.2, 24.8, 27.4, 30],
               [0.74141, 0.93863, 0.97775, 0.98946, 0.99396,
                0.99599, 0.99701, 0.99759, 0.99793, 0.99815, 0.99828])
        self.dose_rate_per_10to14_ph_per_mmsq = interp1d(\
               [3.99, 6.6, 9.2, 11.8, 14.4, 17., 19.6, 22.2, 24.8, 27.4, 30.0],
               [459000., 162000., 79000., 45700., 29300., 20200.,
                14600., 11100., 8610., 6870., 5520.])

    def init(self):
        """Reads config xml, initiates all necessary hwobj, channels and cmds
        """
        self.ready_event = gevent.event.Event()

        self.scale_hor = self.getProperty("scale_hor")
        self.scale_ver = self.getProperty("scale_ver")
        self.scale_double_hor = self.getProperty("scale_double_hor")
        self.scale_double_ver = self.getProperty("scale_double_ver")
        self.chan_pitch_scan_status = self.getChannelObject("chanPitchScanStatus")
        self.connect(self.chan_pitch_scan_status,
                     "update",
                     self.pitch_scan_status_changed)

        #self.chan_encoder_ar = self.getChannelObject("chanEncoderAr")
        #self.connect(self.chan_encoder_ar,
        #             "update",
        #             self.encoder_ar_changed)

        #self.chan_qbpm_ar = self.getChannelObject("chanQBPMAr")

        self.chan_pitch_position_ar = self.getChannelObject("chanPitchPositionAr")
        #self.connect(self.chan_pitch_position_ar,
        #             "update",
        #             self.pitch_position_ar_changed)

        self.cmd_set_pitch_position = self.getCommandObject("cmdSetPitchPosition")
        self.cmd_set_pitch = self.getCommandObject("cmdSetPitch")
        self.cmd_start_pitch_scan = self.getCommandObject("cmdStartPitchScan")
        self.cmd_set_vmax_pitch = self.getCommandObject("cmdSetVMaxPitch")

        self.horizontal_motor_hwobj = self.getObjectByRole("horizontal_motor")
        self.vertical_motor_hwobj = self.getObjectByRole("vertical_motor")
        self.horizontal_double_mode_motor_hwobj = self.getObjectByRole("horizontal_double_mode_motor")
        self.vertical_double_mode_motor_hwobj = self.getObjectByRole("vertical_double_mode_motor")
      
        #self.chan_pitch_second = self.getChannelObject("chanPitchSecond")

        self.bl_hwobj = self.getObjectByRole("beamline_setup")
        self.crl_hwobj = self.getObjectByRole("crl")
        self.graphics_manager_hwobj = self.bl_hwobj.shape_history_hwobj
        self.connect(self.graphics_manager_hwobj,
                     "imageDoubleClicked",
                     self.image_double_clicked)

        if hasattr(self.bl_hwobj.beam_info_hwobj, "beam_focusing_hwobj"):
            self.beam_focusing_hwobj = \
              self.bl_hwobj.beam_info_hwobj.beam_focusing_hwobj
            self.connect(self.beam_focusing_hwobj,
                         "focusingModeChanged",
                         self.focusing_mode_changed)
        else:
            logging.getLogger("HWR").debug(\
               "BeamlineTest: Beam focusing hwobj is not defined")

        if hasattr(self.bl_hwobj, "ppu_control_hwobj"):
            self.connect(self.bl_hwobj.ppu_control_hwobj,
                         "ppuStatusChanged",
                          self.ppu_status_changed)
        else:
            logging.getLogger("HWR").warning(\
               "BeamlineTest: PPU control hwobj is not defined")

        self.connect(self.bl_hwobj.energy_hwobj,
                     "beamAlignmentRequested",
                     self.center_beam_report)

        self.beamline_name = self.bl_hwobj.session_hwobj.beamline_name
        self.csv_file_name = self.getProperty("device_list")
        if self.csv_file_name:
            self.init_device_list()

        self.test_directory = self.getProperty("results_directory")
        if self.test_directory is None:
            self.test_directory = os.path.join(\
                tempfile.gettempdir(), "mxcube", "beamline_test")
            logging.getLogger("HWR").debug(\
                "BeamlineTest: directory for test " \
                "reports not defined. Set to: %s" % self.test_directory)
        self.test_filename = "mxcube_test_report"

        try:
            for test in eval(self.getProperty("available_tests", '[]')):
                self.available_tests_dict[test] = TEST_DICT[test]
        except:
            logging.getLogger("HWR").debug(\
                "BeamlineTest: No test define in xml. " +\
                "Setting all tests as available.")
        if self.available_tests_dict is None:
            self.available_tests_dict = TEST_DICT

        if self.getProperty("startup_tests"):
            self.startup_test_list = eval(self.getProperty("startup_tests"))

        if self.getProperty("run_tests_at_startup") == True:
            self.start_test_queue(self.startup_test_list)

        self.intensity_ranges = []
        self.intensity_measurements = []
        if self.getProperty("intensity"):
            for intens_range in self['intensity']['ranges']:
                temp_intens_range = {}
                temp_intens_range['max'] = intens_range.CurMax
                temp_intens_range['index'] = intens_range.CurIndex
                temp_intens_range['offset'] = intens_range.CurOffset
                self.intensity_ranges.append(temp_intens_range)
            self.intensity_ranges = sorted(self.intensity_ranges,
                                           key=lambda item: item['max'])
           
         

        self.chan_intens_mean = self.getChannelObject('intensMean')
        self.chan_intens_range = self.getChannelObject('intensRange')

        self.cmd_set_intens_resolution = \
            self.getCommandObject('setIntensResolution')
        self.cmd_set_intens_acq_time = \
            self.getCommandObject('setIntensAcqTime')
        self.cmd_set_intens_range = \
            self.getCommandObject('setIntensRange')

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
                logging.getLogger("HWR").debug(\
                    "BeamlineTest: Creating directory %s" % \
                    self.test_directory)
                if not os.path.exists(self.test_directory):
                    os.makedirs(self.test_directory)

                logging.getLogger("HWR").debug(\
                    "BeamlineTest: Creating source directory %s" % \
                    self.test_directory)
                if not os.path.exists(self.test_directory):
                    os.makedirs(self.test_directory)
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
                                     "progress_msg": "executing %s" % \
                                     TEST_DICT[test_name]}
                    self.emit("testProgress", (test_index, progress_info))

                    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    #self.current_test_procedure = gevent.spawn(\
                    test_result = getattr(self, test_method_name)()
                    #test_result = self.current_test_procedure.get()

                    self.ready_event.wait()
                    self.ready_event.clear()
                    end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.results_list.append(\
                         {"short_name": test_name,
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
                        self.results_html_list.append(\
                            "<h3>Detailed results:</h3>")
                        self.results_html_list.extend(\
                            test_result.get("result_details", []))
                    self.emit("progressStop", ())
            else:
                msg = "<h2><font color=%s>Execution method %s " + \
                      "for the test %s does not exist</font></h3>"
                self.results_html_list.append(msg %(TEST_COLORS_FONT[False],
                     test_method_name, TEST_DICT[test_name]))
                logging.getLogger("HWR").error(\
                     "BeamlineTest: Test method " +\
                     "%s not available" % test_method_name)
            self.results_html_list.append("</p>\n<hr>")

        html_filename = None
        if create_report:
            html_filename = os.path.join(self.test_directory,
                                         self.test_filename) + \
                                         ".html"        
            self.generate_report()

        self.emit('testFinished', html_filename)

    def init_device_list(self):
        """Initializes a list of device from a csv file"""
        self.devices_list = []
        if os.path.exists(self.csv_file_name):
            with open(self.csv_file_name, 'rb') as csv_file:
                csv_reader = reader(csv_file, delimiter=',')
                for row in csv_reader:
                    if self.valid_ip(row[1]):
                        self.devices_list.append(row)
            return self.devices_list
        else:
            logging.getLogger("HWR").error(\
                "BeamlineTest: Device file " + \
                "%s not found" % self.csv_file_name)

    def get_device_list(self):
        """Returns list of devices"""
        return self.devices_list

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

    def valid_ip(self, address):
        """Returns True if ip address is valid

        :param address: IP address
        :type address: str
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
        """Reemits ppu status changed signal

        :param is_error: is error
        :type is_error: bool
        :param text: error message
        :type text: str
        """
        self.emit('ppuStatusChanged', (is_error, text))

    def ppu_restart_all(self):
        """Restart ppu processes"""
        if self.bl_hwobj.ppu_control_hwobj is not None:
            self.bl_hwobj.ppu_control_hwobj.restart_all()

    def pitch_scan(self):
        self.cmd_set_pitch_position(0)
        self.cmd_set_pitch(1)
        sleep(0.2)
        self.cmd_start_pitch_scan(1)
        sleep(2.0)

        with gevent.Timeout(10, Exception("Timeout waiting for pitch scan ready")):
            while self.chan_pitch_scan_status.getValue() != 0:
                   gevent.sleep(0.1)
        self.cmd_set_vmax_pitch(1)

    def test_sc_stats(self):
        result = {}

        self.emit("progressInit", ("Executing test: sample changer statistics.", 5, True))
        log_filename = self.bl_hwobj.sample_changer_hwobj.get_log_filename()

        if not os.path.exists(log_filename):
            result["result_details"] = []
            result["result_short"] = \
                "Test failed: Sample changer log file: %s " % str(log_filename) + \
                "do not exist."
            result["result_bit"] = False
            self.ready_event.set()
            self.emit("progressStop", ())
            return result

        min_datetime = None
        log_arr = np.array([])
        log_file = open(log_filename, "r")
        read_lines = log_file.readlines()
        first_time = None
        last_time = None

        for line in read_lines:
            line = line.replace("\n","")
            line = line.split(',')
            if first_time is None:
                first_time = line[0]
            log_arr = np.append(log_arr,
                                [np.datetime64(line[0]),
                                 np.datetime64(line[1]),
                                 int(line[2]),
                                 line[3],
                                 line[4],
                                 int(line[5]),
                                 int(line[6]),
                                 line[7],
                                 line[0][:13] + "h"])
        last_time = line[0]
        log_arr = log_arr.reshape(len(read_lines), 9)
        log_file.close()

        result["result_details"] = []
        result["result_details"].append("Sample changer statistics from " + \
            "<b>%s</b> till <b>%s</b>" % (first_time, last_time))
        result["result_details"].append("<br>")
        
        result["result_details"] = []
        result["result_details"].append("Sample changer statistics from " + \
            "<b>%s</b> till <b>%s</b>" % (first_time, last_time))
        result["result_details"].append("<br>")

        self.emit("progressStep", 1)

        # 0 - start time
        # 1 - end time
        # 2 - time delta in sec
        # 3 - user
        # 4 - action
        # 5 - puck
        # 6 - sample
        # 7 if exists Error  

        table_cells = []
        table_cells.append(("Mount",
                            str((log_arr[:,4] == "load").sum()), 
                            "bgcolor=#FFCCCC>%d" %
                            (log_arr[(log_arr[:,4] == "load") & \
                            (log_arr[:,7] == "Error")].size / 8)))
        table_cells.append(("Unmount",
                            str((log_arr[:,4] == "unload").sum()), 
                            "bgcolor=#FFCCCC>%d" %
                            (log_arr[(log_arr[:,4] == "unload") & \
                            (log_arr[:,7] == "Error")].size / 8)))

        result["result_details"].extend(SimpleHTML.create_table(\
             ["Action", "Total", "bgcolor=#FFCCCC>Fails"],
             table_cells))
        result["result_details"].append("<br>")
 
        table_cells = []
        table_cells.append(("Min mount time",
                            str(log_arr[log_arr[:,4] == "load"][:,2].min())))
        table_cells.append(("Max mount time",
                            str(log_arr[log_arr[:,4] == "load"][:,2].max())))
        table_cells.append(("Mean mount time",
                            "%d" %(log_arr[log_arr[:,4] == "load"][:,2].mean())))

        table_cells.append(("Min unmount time",
                            str(log_arr[log_arr[:,4] == "unload"][:,2].min())))
        table_cells.append(("Max unmount time",
                            str(log_arr[log_arr[:,4] == "unload"][:,2].max())))
        table_cells.append(("Mean unmount time", 
                            "%d" %(log_arr[log_arr[:,4] == "unload"][:,2].mean())))

        result["result_details"].extend(SimpleHTML.create_table(\
             ["Mount/unmount time", "sec"],
             table_cells))
        result["result_details"].append("<br>")

        self.emit("progressStep", 2)

        table_cells = []
        user_list = []
        for user in log_arr[:,3]:
            if not user in user_list:
               user_list.append(user)

        for user in user_list:
            load_total = log_arr[(log_arr[:,4] == "load") & \
                                 (log_arr[:,3] == user)].size / 8 
            load_failed = log_arr[(log_arr[:,4] == "load") & \
                                  (log_arr[:,7] == "Error") & \
                                  (log_arr[:,3] == user)].size / 8
            unload_total = log_arr[(log_arr[:,4] == "unload") & \
                                   (log_arr[:,3] == user)].size / 8 
            unload_failed = log_arr[(log_arr[:,4] == "unload") & \
                                    (log_arr[:,7] == "Error") & \
                                    (log_arr[:,3] == user)].size / 8
    
            if load_total == 0:
                info_row = [user,
                            "0",
                            "bgcolor=#FFCCCC>%d (%.1f %%)" % (0, 0)]
            else:
                info_row = [user,
                            str(load_total),
                            "bgcolor=#FFCCCC>%d (%.1f %%)" % (\
                            load_failed, float(load_failed) / load_total * 100.0)]
            if unload_total == 0:
                info_row.extend(("0",
                                 "bgcolor=#FFCCCC>%d (%.1f %%)" % (0, 0)))
            else:
                info_row.extend((str(unload_total),
                                 "bgcolor=#FFCCCC>%d (%.1f %%)" % (\
                                unload_failed, float(unload_failed) / unload_total * 100.0)))
          
            table_cells.append(info_row)
        result["result_details"].extend(SimpleHTML.create_table(\
             ["User", "Mounts", "bgcolor=#FFCCCC>Failed mounts",
              "Unmounts", "bgcolor=#FFCCCC>Failed unmounts"],
             table_cells))
 
        self.emit("progressStep", 3)
        hour_arr = np.array([])
        for hour in np.unique(log_arr[:,8]):
            hour_arr = np.append(hour_arr,
                  [hour,
                   log_arr[(log_arr[:,4] == "load") & \
                   (log_arr[:,8] == hour)].size / 8,
                   log_arr[(log_arr[:,4] == "load") & \
                   (log_arr[:,8] == hour) & \
                   (log_arr[:,7] == "Error")].size / 8,
                   log_arr[(log_arr[:,4] == "unload") & \
                   (log_arr[:,8] == hour)].size / 8,
                   log_arr[(log_arr[:,4] == "unload") & \
                   (log_arr[:,8] == hour) & \
                   (log_arr[:,7] == "Error")].size / 8])
        hour_arr = hour_arr.reshape(hour_arr.size / 5, 5)

        fig = Figure(figsize=(15, 12))
        ax = fig.add_subplot(111)
        ax.bar(np.arange(hour_arr.shape[0]),
               hour_arr[:,1].astype(int))
        ax.bar(np.arange(hour_arr.shape[0]),
               hour_arr[:,2].astype(int), color="red")

        ax.set_xticks(np.arange(hour_arr.shape[0]))
        ax.set_xticklabels(hour_arr[:,0], 
                           rotation="vertical",
                           horizontalalignment="left")
        ax.grid(True)
        ax.set_xlabel("Time")
        ax.set_ylabel("Number of mounts")

        sc_mount_stats_png_filename = os.path.join(\
             self.test_directory,
             "sc_mount_stats.png")
         
        self.emit("progressStep", 4)      
        canvas = FigureCanvasAgg(fig)
        canvas.print_figure(sc_mount_stats_png_filename, dpi = 80)
        result["result_details"].append("<br><b>Mounts and failed mounts / time</b></br>")
        result["result_details"].append(\
               "<img src=%s style=width:700px;><br>" % \
               sc_mount_stats_png_filename)

        fig = Figure(figsize=(15, 12))
        ax = fig.add_subplot(111)
        ax.bar(np.arange(hour_arr.shape[0]),
               hour_arr[:,3].astype(int))
        ax.bar(np.arange(hour_arr.shape[0]),
               hour_arr[:,4].astype(int), color="red")

        ax.set_xticks(np.arange(hour_arr.shape[0]))
        ax.set_xticklabels(hour_arr[:,0],
                           rotation="vertical",
                           horizontalalignment="left")
        ax.grid(True)
        ax.set_xlabel("Time")
        ax.set_ylabel("Number of unmounts")

        sc_unmount_stats_png_filename = os.path.join(\
             self.test_directory,
             "sc_unmount_stats.png")

        canvas = FigureCanvasAgg(fig)
        canvas.print_figure(sc_unmount_stats_png_filename, dpi = 80)
        result["result_details"].append("<br><b>Unmounts and failed unmounts / time</b></br>")
        result["result_details"].append(\
               "<img src=%s style=width:700px;><br>" % \
               sc_unmount_stats_png_filename)

        #result["result_short"] = "Done!"
        result["result_bit"] = True
        self.ready_event.set()

        self.emit("progressStop", ())
        return result

    def test_com(self):
        """Test communication (ping) with beamline devices"""
        self.emit("progressInit", ("Executing test: ping beamline devices.",
                                   len(self.devices_list),
                                   True))

        result = {}
        table_header = ["Replied", "DNS name", "IP address", "Location",
                        "MAC address", "Details"]
        table_cells = []
        failed_count = 0
        for row, device in enumerate(self.devices_list):
            msg = "Pinging device %s (%d/%d) at %s" % (device[0], row, len(self.devices_list), device[1])
            logging.getLogger("HWR").debug("BeamlineTest: %s" % msg)
            device_result = ["bgcolor=#FFCCCC", "False"] + device
            try:
                ping_result = os.system("ping -W 2 -c 2 " + device[1]) == 0
                device_result[0] = "bgcolor=%s" % \
                                   TEST_COLORS_TABLE[ping_result]
                device_result[1] = str(ping_result)
            except:
                ping_result = False
            table_cells.append(device_result)

            if not ping_result:
                failed_count += 1
            progress_info = {"progress_total": len(self.devices_list),
                             "progress_msg": msg}
            self.emit("progressStep", (row, msg))
            

        result["result_details"] = \
            SimpleHTML.create_table(table_header, table_cells)

        if failed_count == 0:
            result["result_short"] = "Test passed (got reply from all devices)"
            result["result_bit"] = True
        else:
            result["result_short"] = \
                "Test failed: %d devices from %d did not replied)" % \
                (failed_count, len(self.devices_list))
            result["result_bit"] = False

        self.ready_event.set()

        return result

    def test_ppu(self):
        """Test ppu"""
        result = {}
        if self.bl_hwobj.ppu_control_hwobj is not None:
            print self.bl_hwobj.ppu_control_hwobj.get_status()
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

    def test_aperture(self):
        """Test to evaluate beam shape with image processing
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

        self.bl_hwobj.diffractometer_hwobj.set_phase("BeamLocation",
                                                     timeout=30)

        aperture_hwobj = self.bl_hwobj.beam_info_hwobj.aperture_hwobj
        aperture_list = aperture_hwobj.get_aperture_list(as_origin=True)
        current_aperture = aperture_hwobj.get_value()

        for index, value in enumerate(aperture_list):
            msg = "Selecting aperture %s " % value
            table_header += "<th>%s</th>" % value
            aperture_hwobj.set_active_position(index)
            gevent.sleep(1)
            beam_image_filename = os.path.join(\
                self.test_directory,
                "aperture_%s.png" % value)
            table_values += "<td><img src=%s style=width:700px;></td>" % \
                            beam_image_filename
            self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)
            progress_info = {"progress_total": len(aperture_list),
                             "progress_msg": msg}
            self.emit("testProgress", (index, progress_info))

        self.bl_hwobj.diffractometer_hwobj.set_phase(\
             self.bl_hwobj.diffractometer_hwobj.PHASE_CENTRING,
             timeout=30)
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

    def test_graph(self):
        """Displays a random generated graph.
           Method used for testing
        """
        result = {}
        self.graph_values[0].insert(0, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.graph_values[1].insert(0, random() * 1e12)
        x_arr = range(0, len(self.graph_values[0]))

        result["result_details"] = []
        result["result_details"].append("Intensity graph:")

        fig = Figure(figsize=(15, 11))
        ax = fig.add_subplot(111)
        ax.grid(True)
        ax.plot(x_arr, self.graph_values[1])
        #ax.xticks(x_arr, self.graph_values[0], rotation='vertical')
        ax.xaxis.set_ticks(self.graph_values[0])
        canvas = FigureCanvasAgg(fig)
        graph_path = "/tmp/mxcube/test_graph.png"
        canvas.print_figure(graph_path)
        result["result_details"].append("<img src=%s style=width:700px;>" % \
                                        graph_path)

        result["result_short"] = "Done!"
        result["result_bit"] = True

        self.ready_event.set()

        return result

    def start_center_beam_manual(self):
        gevent.spawn(self.center_beam_manual_procedure)

    def center_beam_manual_procedure(self): 
        self.user_clicked_event = gevent.event.AsyncResult()
        x, y = self.user_clicked_event.get()
        self.user_clicked_event = None

    def center_beam_report(self):
        self.start_test_queue(["centerbeam"])

    def test_centerbeam(self):
        """Beam centering procedure"""

        result = {} 
        result["result_bit"] = True
        result["result_details"] = []
        result["result_short"] = "Test started"

        result["result_details"].append("Beam profile before centring<br>")
        result["result_details"].append("<img src=%s style=width:300px;>" % \
             os.path.join(self.test_directory, "beam_image_before.png"))
        result["result_details"].append("<img src=%s style=width:300px;><br><br>" % \
             os.path.join(self.test_directory, "beam_profile_before.png"))
      
        self.center_beam_test()

        result["result_details"].append("Beam profile after centring<br>")
        result["result_details"].append("<img src=%s style=width:300px;>" % \
             os.path.join(self.test_directory, "beam_image_after.png"))
        result["result_details"].append("<img src=%s style=width:300px;><br><br>" % \
             os.path.join(self.test_directory, "beam_profile_after.png"))

        result["result_short"] = "Beam centering finished"

        self.ready_event.set()
        return result

    def center_beam_test(self):
        """Calls gevent task to center beam"""
        #TODO rename to center_beam_task
        gevent.spawn(self.center_beam_test_task)

    def center_beam_test_task(self):
        """Centers beam in a following procedure:
            1. Store aperture position and take out the aperture
            2. Store slits position and open to max
            3. Do pitch scan if possible
            3. In a loop take snapshot and move motors
            4. Put back aperture and move to original slits positions
        """
        aperture_hwobj = self.bl_hwobj.beam_info_hwobj.aperture_hwobj
        current_energy = self.bl_hwobj._get_energy() 
        current_transmission = self.bl_hwobj._get_transmission()

        log = logging.getLogger("GUI")
        msg = "Starting beam centring"
        progress_info = {"progress_total": 6,
                         "progress_msg": msg}
        log.info("Beam centering: %s" % msg)
        self.emit("testProgress", (1, progress_info))
        self.emit("progressInit", ("Beam centering...", 6, True))

        # 1. close guillotine and fast shutter -------------------------------
        # TODO
        #self.bl_hwobj.collect_hwobj.close_guillotine(wait=True)

        # 1/6 Diffractometer in BeamLocation phase ---------------------------
        msg = "1/6 : Setting diffractometer in BeamLocation phase"
        progress_info["progress_msg"] = msg
        log.info("Beam centering: %s" % msg)
        self.emit("testProgress", (2, progress_info))
        self.emit("progressStep", 1, "Setting diffractometer in BeamLocation phase")
       
        self.bl_hwobj.diffractometer_hwobj.wait_device_ready(10) 
        self.bl_hwobj.diffractometer_hwobj.set_phase(\
             self.bl_hwobj.diffractometer_hwobj.PHASE_BEAM, timeout=45)

        self.bl_hwobj.fast_shutter_hwobj.openShutter()
        gevent.sleep(0.1)
        aperture_hwobj.set_out()

        msg = "2/6 : Adjusting transmission to the current energy %.1f keV" % current_energy
        progress_info["progress_msg"] = msg
        log.info("Beam centering: %s" % msg)
        self.emit("testProgress", (2, progress_info))
        self.emit("progressStep", 2, "Adjusting transmission")

        if current_energy < 7:
            new_transmission = 100
        else:
            energy_transm = interp1d([6.9, 8., 12.7, 19.],
                                     [100., 60., 15., 10])
            new_transmission = round(energy_transm(current_energy), 2)
        
        if self.bl_hwobj.session_hwobj.beamline_name == "P13":
            self.bl_hwobj.transmission_hwobj.setTransmission(new_transmission, timeout=45)
            self.bl_hwobj.diffractometer_hwobj.set_zoom("Zoom 4")
            capillary_position = self.bl_hwobj.diffractometer_hwobj.get_capillary_position()
            self.bl_hwobj.diffractometer_hwobj.set_capillary_position("OFF")

            gevent.sleep(1)
            self.center_beam_task()

            #self.bl_hwobj.diffractometer_hwobj.set_capillary_position(capillary_position)
        else: 
            slits_hwobj = self.bl_hwobj.beam_info_hwobj.slits_hwobj

            active_mode, beam_size = self.get_focus_mode()
            
            if active_mode == "Collimated":
                self.bl_hwobj.transmission_hwobj.setTransmission(new_transmission, timeout=45)
                self.bl_hwobj.diffractometer_hwobj.set_zoom("Zoom 4")
            else:
                # 2% transmission for beam centering in double foucused mode
                self.bl_hwobj.transmission_hwobj.setTransmission(2, timeout=45)
                self.bl_hwobj.diffractometer_hwobj.set_zoom("Zoom 8")

            msg = "3/6 : Opening slits to 1 x 1 mm"
            progress_info["progress_msg"] = msg
            log.info("Beam centering: %s" % msg)
            self.emit("testProgress", (2, progress_info))
            self.emit("progressStep", 3, "Opening slits to 1x1 mm")

            #GB: keep standard slits settings for double foucsed mode
            if active_mode == "Collimated":
               slits_hwobj.set_gap('Hor', 1.0)
               slits_hwobj.set_gap('Ver', 1.0)

            #self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)

            # Actual centring procedure  ---------------
            
            beam_task_result = self.center_beam_task()
            if not beam_task_result:
                log.error("Beam centering: Failed")
                self.emit("progressStop", ())
                self.ready_event.set()
                return

            # 5/6 For unfocused mode setting slits to 0.1 x 0.1 mm ---------------
            if active_mode == "Collimated":
                msg = "5/6 : Setting slits to 0.1 x 0.1 mm"
                progress_info["progress_msg"] = msg
                log.info("Beam centering: %s" % msg)
                self.emit("testProgress", (5, progress_info))

                slits_hwobj.set_gap('Hor', 0.1)
                slits_hwobj.set_gap('Ver', 0.1)
                sleep(3)
                

            # 6/6 Update position of the beam mark position ----------------------
            msg = "6/6 : Updating beam mark position"
            self.emit("progressStep", 6, "Updating beam mark position")
            progress_info["progress_msg"] = msg
            log.info("Beam centering: %s" % msg)
            self.emit("testProgress", (6, progress_info))
            self.graphics_manager_hwobj.move_beam_mark_auto()

        self.bl_hwobj.transmission_hwobj.setTransmission(current_transmission)

        """
        self.graphics_manager_hwobj.save_scene_snapshot(\
             os.path.join(self.test_directory,
                          "beam_image_after.png"))
        self.graphics_manager_hwobj.save_beam_profile(\
             os.path.join(self.test_directory,
                          "beam_profile_after.png"))
        """

        self.graphics_manager_hwobj.graphics_beam_item.set_detected_beam_position(None, None)

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
        progress_info = {"progress_total": 6,
                         "progress_msg": msg}

        """
        self.graphics_manager_hwobj.save_scene_snapshot(\
             os.path.join(self.test_directory,
                          "beam_image_before.png"))
        self.graphics_manager_hwobj.save_beam_profile(\
             os.path.join(self.test_directory,
                          "beam_profile_before.png"))
        gevent.sleep(1)
        """

        if self.bl_hwobj.session_hwobj.beamline_name == "P13":
            #Beam centering procedure for P13 ---------------------------------

            msg = "4/6 : Starting pitch scan"
            progress_info["progress_msg"] = msg
            log.info("Beam centering: %s" % msg)
            self.emit("testProgress", (3, progress_info))

            if self.bl_hwobj._get_energy() <= 8.75:
                self.cmd_set_qbmp_range(0)
            else:
                self.cmd_set_qbmp_range(1)
            gevent.sleep(0.2)
            self.cmd_set_pitch_position(0)
            self.cmd_set_pitch(1)
            gevent.sleep(0.2)
            self.cmd_start_pitch_scan(1)
            gevent.sleep(2.0)

            with gevent.Timeout(10, Exception("Timeout waiting for pitch scan ready")):
                while self.chan_pitch_scan_status.getValue() != 0:
                       gevent.sleep(0.1)
            self.cmd_set_vmax_pitch(1)

            self.emit("progressStep", 4, "Detecting beam position and centering the beam")
            for i in range(3):
                with gevent.Timeout(10, False):
                    beam_pos_displacement = [None, None]
                    while None in beam_pos_displacement:
                        beam_pos_displacement = self.graphics_manager_hwobj.\
                           get_beam_displacement(reference="beam")
                        gevent.sleep(0.1)
                if None or 0 in beam_pos_displacement:
                    return

                delta_hor = beam_pos_displacement[0] * self.scale_hor
                delta_ver = beam_pos_displacement[1] * self.scale_ver

                if delta_hor > 0.03: delta_hor = 0.03
                if delta_hor < -0.03: delta_hor = -0.03
                if delta_ver > 0.03: delta_ver = 0.03
                if delta_ver < -0.03: delta_ver = -0.03

                log.info("Beam centering: Applying %.4f mm horizontal " % delta_hor + \
                         "and %.4f mm vertical correction" % delta_ver)

                if abs(delta_hor) > 0.001:
                    log.info("Beam centering: Moving horizontal by %.4f" % delta_hor)
                    self.horizontal_motor_hwobj.move_relative(delta_hor, timeout=5)
                    sleep(1)
                if abs(delta_ver) > 0.001:
                    log.info("Beam centering: Moving vertical by %.4f" % delta_ver)
                    self.vertical_motor_hwobj.move_relative(delta_ver, timeout=5)
                    sleep(1)

        else:
            # Beam centering procedure for P14 -----------------------------------
            # 3.1/6 If energy < 10: set all lenses in ----------------------------
            active_mode, beam_size = self.get_focus_mode()

            # 4/6 Applying Perp and Roll2nd correction ------------------------
            #if active_mode == "Collimated":
            if True:
                msg = "4/6 : Applying Perp and Roll2nd correction"
                progress_info["progress_msg"] = msg
                log.info("Beam centering: %s" % msg)
                self.emit("testProgress", (4, progress_info))
                self.emit("progressStep", 4, "Detecting beam position and centering the beam")
                delta_ver = 1.0

                for i in range(5):
                    if abs(delta_ver) > 0.100 :
                        self.cmd_set_pitch_position(0)
                        self.cmd_set_pitch(1)
                        gevent.sleep(0.1)

                        if self.bl_hwobj._get_energy() < 10:
                            crl_value = self.crl_hwobj.get_crl_value()
                            self.crl_hwobj.set_crl_value([1, 1, 1, 1, 1, 1], timeout=30)

                        self.cmd_start_pitch_scan(1)

                        # GB : keep lenses in the beam during the scan 
                        #if self.bl_hwobj._get_energy() < 10:
                        #   self.crl_hwobj.set_crl_value(crl_value, timeout=30)

                        gevent.sleep(2.0)

                        with gevent.Timeout(10, RuntimeError("Timeout waiting for pitch scan ready")):
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
                            beam_pos_displacement = self.graphics_manager_hwobj.\
                               get_beam_displacement(reference="screen")
                            gevent.sleep(0.1)
                    if None in beam_pos_displacement:
                        #log.debug("No beam detected")
                        return

                    if active_mode == "Collimated":
                       delta_hor = beam_pos_displacement[0] * self.scale_hor * self.bl_hwobj._get_energy() / 12.70
                       delta_ver = beam_pos_displacement[1] * self.scale_ver
                    else:
                       delta_hor = beam_pos_displacement[0] * self.scale_double_hor
                       delta_ver = beam_pos_displacement[1] * self.scale_double_ver

                    log.info("Measured beam displacement: Horizontal " + \
                             "%.4f mm, Vertical %.4f mm"%beam_pos_displacement)

                    #if abs(delta_ver) > 0.050 :
                    #    delta_ver *= 0.5
           
                    log.info("Applying %.4f mm horizontal " % delta_hor + \
                             "and %.4f mm vertical motor correction" % delta_ver)

                    if active_mode == "Collimated":
                        if abs(delta_hor) > 0.0001:
                            log.info("Moving horizontal by %.4f" % delta_hor)
                            self.horizontal_motor_hwobj.move_relative(delta_hor, timeout=5)
                            sleep(4)
                        if abs(delta_ver) > 0.100:
                            log.info("Moving vertical motor by %.4f" % delta_ver)
                            #self.vertical_motor_hwobj.move_relative(delta_ver, timeout=5)
                            tine.set("/p14/P14MonoMotor/Perp","IncrementMove.START",delta_ver*0.5)
                            sleep(6)
                        else:
                            log.info("Moving vertical piezo by %.4f" % delta_ver)
                            self.vertical_motor_hwobj.move_relative(-1.0*delta_ver, timeout=5)
                            sleep(2)
                    elif active_mode == "Double":
                        if abs(delta_hor) > 0.0001:
                            log.info("Moving horizontal by %.4f" % delta_hor)
                            self.horizontal_double_mode_motor_hwobj.move_relative(delta_hor, timeout=5) 
                            sleep(2)
                        if abs(delta_ver) > 0.001:
                            log.info("Moving vertical by %.4f" % delta_ver)
                            self.vertical_double_mode_motor_hwobj.move_relative(delta_ver, timeout=5)
                            sleep(2)
        return True

    def pitch_scan_status_changed(self, status):
        """Store pitch scan status"""
        self.scan_status = status

    """
    def encoder_ar_changed(self, position):
        print "encoder_ar_changed: ", position

    def pitch_position_ar_changed(self, position):
        print "pitch_position_ar_changed: ", position
    """

    def test_autocentring(self):
        """Tests autocentring"""
        result = {}
        result["result_bit"] = True
        result["result_details"] = []
        result["result_details"].append("Before autocentring<br>")

        beam_image_filename = os.path.join(\
            self.test_directory,
            "auto_centring_before.png")
        self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)
        gevent.sleep(0.1)
        result["result_details"].append(\
            "<img src=%s style=width:300px;><br>" % \
            beam_image_filename)

        self.bl_hwobj.diffractometer_hwobj.start_centring_method(\
             self.bl_hwobj.diffractometer_hwobj.CENTRING_METHOD_AUTO,
             wait=True)

        result["result_details"].append("After autocentring<br>")
        beam_image_filename = os.path.join(self.test_directory,
                                           "auto_centring_after.png")
        self.graphics_manager_hwobj.save_scene_snapshot(beam_image_filename)
        result["result_details"].append(\
             "<img src=%s style=width:300px;><br>" % \
             beam_image_filename)

        self.ready_event.set()

        return result

    def test_summary(self):
        """Generates a summary of beamline properties"""
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

    def measure_intensity(self):
        """Measures intesity"""
        #self.start_test_queue(["measure_intensity"])
        gevent.spawn(self.test_measure_intensity)

    def test_measure_intensity(self):
        """Measures intensity and generates report"""
        result = {}
        result["result_bit"] = False
        result["result_details"] = []

        self.emit("progressInit", ("Measuring intensity...", 8, True))
        try:
            intens_value = 0
            current_phase = self.bl_hwobj.diffractometer_hwobj.current_phase

            # 1. close guillotine and fast shutter -------------------------------
            if not self.bl_hwobj.detector_hwobj.is_cover_closed():
                logging.getLogger("GUI").error("Unable to measure flux!" + \
                     "Close the detecor cover to continue")
                result["result_short"] = "Measure intensity failed. " + \
                     "Detector cover was open."
                self.ready_event.set()
                return result

            #self.bl_hwobj.detector_hwobj.close_cover(wait=True)
            self.bl_hwobj.fast_shutter_hwobj.closeShutter(wait=True)
            gevent.sleep(0.1)

            #2. move back light in, check beamstop position ----------------------
            logging.getLogger("GUI").info("Measure flux: Moving backlight in")
            self.emit("progressStep", 1, "Moving backlight in")
            self.bl_hwobj.back_light_hwobj.move_in()

            beamstop_position = self.bl_hwobj.beamstop_hwobj.get_position()
            if beamstop_position == "BEAM":
                self.emit("progressStep", 2, "Moving beamstop OFF")
                self.bl_hwobj.beamstop_hwobj.set_position("OFF")
                self.bl_hwobj.diffractometer_hwobj.wait_device_ready(30)

            #3. check scintillator position --------------------------------------
            scintillator_position = self.bl_hwobj.\
                diffractometer_hwobj.get_scintillator_position()
            if scintillator_position == "SCINTILLATOR":
                #TODO add state change when scintillator position changed
                self.emit("progressStep", 3, "Setting the photodiode")
                self.bl_hwobj.diffractometer_hwobj.\
                     set_scintillator_position("PHOTODIODE")
                gevent.sleep(1)
                self.bl_hwobj.diffractometer_hwobj.\
                     wait_device_ready(30)

            #TODO move in the apeture for P13

            #5. open the fast shutter --------------------------------------------
            gevent.sleep(1)
            self.emit("progressStep", 4, "Opening the fast shutter") 
            self.bl_hwobj.fast_shutter_hwobj.openShutter(wait=True)
            gevent.sleep(0.3)

            #6. measure mean intensity
            self.ampl_chan_index = 0

            self.emit("progressStep", 5, "Measuring the intensity")
            intens_value = self.chan_intens_mean.getValue()
            intens_range_now = self.chan_intens_range.getValue()
            
            #TODO: repair this
            #GB 2018-03-30 09:45:25 : following loop that encodes current offset is broken as self.intensity_ranges = []
            #hard coding 

            self.intensity_value = intens_value[0] + 2.780e-6
            
            #for intens_range in self.intensity_ranges:
            #    if intens_range['index'] is intens_range_now:
            #        self.intensity_value = intens_value[self.ampl_chan_index] - \
            #                              intens_range['offset']
            #        break

        except:
            logging.getLogger("GUI").error("Unable to measure flux!") 
        #finally:

        self.emit("progressStep", 6, "Closing fast shutter")
        #7. close the fast shutter -------------------------------------------
        self.bl_hwobj.fast_shutter_hwobj.closeShutter(wait=True)

        # 7/7 set back original phase ----------------------------------------
        self.emit("progressStep", 7, "Restoring diffractometer to %s phase" % current_phase)
        self.bl_hwobj.diffractometer_hwobj.set_phase(current_phase)

        #8. Calculate --------------------------------------------------------
        self.emit("progressStep", 8, "Calculating flux")
        energy = self.bl_hwobj._get_energy()
        detector_distance = self.bl_hwobj.detector_hwobj.get_distance()
        beam_size = self.bl_hwobj.beam_info_hwobj.get_beam_size()
        transmission = self.bl_hwobj.transmission_hwobj.getAttFactor()

        result["result_details"].append("Energy: %.4f keV<br>" % energy)
        result["result_details"].append("Detector distance: %.2f mm<br>" % \
                                        detector_distance)
        result["result_details"].append("Beam size %.2f x %.2f mm<br>" % \
                                        (beam_size[0], beam_size[1]))
        result["result_details"].append("Transmission %.2f%%<br><br>" % \
                                        transmission)

        meas_item = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                     "%.4f" % energy,
                     "%.2f" % detector_distance,
                     "%.2f x %.2f" % (beam_size[0], beam_size[1]),
                     "%.2f" % transmission]

        air_trsm = numpy.exp(-self.air_absorption_coeff_per_meter(energy) * \
             detector_distance / 1000.0)
        carb_trsm = self.carbon_window_transmission(energy)
        flux = 0.624151 * 1e16 * self.intensity_value / \
               self.diode_calibration_amp_per_watt(energy) / \
               energy / air_trsm / carb_trsm

        #GB correcting diode misscalibration!!!
        flux = flux * 1.8

        dose_rate = 1e-3 * 1e-14 * self.dose_rate_per_10to14_ph_per_mmsq(energy) * \
               flux / beam_size[0] / beam_size[1]

        self.bl_hwobj.flux_hwobj.set_flux(flux)

        msg = "Intensity = %1.1e A" % self.intensity_value
        result["result_details"].append(msg + "<br>")
        logging.getLogger("GUI").info(msg)
        result["result_short"] = msg
        meas_item.append("%1.1e" % self.intensity_value)

        msg = "Flux = %1.1e photon/s" % flux
        result["result_details"].append(msg + "<br>")
        logging.getLogger("GUI").info(msg)
        result["result_short"] = msg
        meas_item.append("%1.1e" % flux)

        msg = "Dose rate =  %1.1e KGy/s" % dose_rate
        result["result_details"].append(msg + "<br>")
        logging.getLogger("GUI").info(msg)
        meas_item.append("%1.1e" % dose_rate)

        max_frame_rate = 1 / self.bl_hwobj.detector_hwobj.get_exposure_time_limits()[0]

        msg = "Time to reach 20 MGy = %.1f s = %d frames @ %s Hz " % \
              (20000. / dose_rate, int(max_frame_rate * 20000. / dose_rate),max_frame_rate)
        result["result_details"].append(msg + "<br><br>")
        logging.getLogger("GUI").info(msg)
        meas_item.append("%d, %d frames" % \
              (20000. / dose_rate, int(max_frame_rate * 20000. / dose_rate)))

        self.intensity_measurements.insert(0, meas_item)

        result["result_bit"] = True
        result["result_details"].extend(SimpleHTML.create_table(\
             ["Time", "Energy (keV)", "Detector distance (mm)",
              "Beam size (mm)", "Transmission (%%)", "Intensity (A)",
              "Flux (photons/s)", "Dose rate (KGy/s)",
              "Time to reach 20 MGy (sec, frames)"],
             self.intensity_measurements))

        self.ready_event.set()
        self.emit("progressStop", ())
        return result

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
        html_filename = os.path.join(self.test_directory,
                                     self.test_filename) + ".html"
        pdf_filename = os.path.join(self.test_directory,
                                     self.test_filename) + ".pdf"
        archive_filename = os.path.join(\
           self.test_directory,
           datetime.now().strftime("%Y_%m_%d_%H") + "_" + \
           self.test_filename)

        try:
            output_file = open(html_filename, "w")
            output_file.write(SimpleHTML.create_html_start(\
                "Beamline test summary"))
            output_file.write("<h1>Beamline %s Test results</h1>" % \
                              self.beamline_name)
            output_file.write("<h2>Executed tests:</h2>")
            table_cells = []
            for test in self.results_list:
                table_cells.append(\
                  ["bgcolor=%s" % TEST_COLORS_TABLE[test["result_bit"]],
                   "<a href=#%s>%s</a>" % \
                   (test["short_name"], test["full_name"]),
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
               "BeamlineTest: Test result written in file %s" % \
               html_filename)
        except:
            logging.getLogger("HWR").error(\
               "BeamlineTest: Unable to generate html report file %s" % \
               html_filename)

        try:
            pdfkit.from_url(html_filename, pdf_filename)
            logging.getLogger("GUI").info(\
               "PDF report %s generated" % pdf_filename)
        except:
            logging.getLogger("HWR").error(\
               "BeamlineTest: Unable to generate pdf report file %s" % \
               pdf_filename)

        self.emit('testFinished', html_filename)

    def get_result_html(self):
        """Returns html filename"""
        html_filename = os.path.join(self.test_directory, self.test_filename) + ".html"
        if os.path.exists(html_filename):
            return html_filename
