# pylint: disable=E
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import tine
import json

import Image
import gevent
import logging
import threading
from queue import Queue

import cv2 as cv
import numpy as np
from scipy import ndimage, misc

from cStringIO import StringIO
from PIL.ImageQt import ImageQt

# from pathos import multiprocessing as mp

from gui.utils import QtImport, Colors

from HardwareRepository.TaskUtils import task
from HardwareRepository.HardwareObjects.abstract.AbstractCollect import AbstractCollect
from HardwareRepository.HardwareObjects.QtGraphicsManager import QtGraphicsManager
from HardwareRepository.HardwareObjects import queue_model_objects as qmo

__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "Task"


image_processing_queue = Queue()


class EMBLXrayImaging(QtGraphicsManager, AbstractCollect):
    """
    Based on the collection and graphics
    """

    def __init__(self, *args):
        """
        Init
        :param args:
        """
        QtGraphicsManager.__init__(self, *args)
        AbstractCollect.__init__(self, *args)

        self.ff_apply = False
        self.ff_ssim = None
        self.qimage = None
        self.qpixmap = None
        self.image_count = 0
        self.image_reading_thread = None
        self.image_processing_thread = None
        self.ff_corrected_list = []
        self.config_dict = {}
        self.collect_omega_start = 0
        self.omega_start = 0
        self.omega_move_enabled = False
        self.last_image_index = None

        self.image_dimension = (0, 0)
        self.graphics_camera_frame = None
        self.image_polling = None
        self.repeat_image_play = None
        self.current_image_index = None
        self.mouse_hold = False
        self.mouse_coord = [0, 0]
        self.centering_started = 0

        self._previous_collect_status = None
        self._actual_collect_status = None
        self._failed = False
        self._number_of_images = 0
        self._collect_frame = 0
        self.printed_warnings = []
        self.printed_errors = []

        self.chan_collect_status = None
        self.chan_collect_frame = None
        self.chan_collect_error = None
        self.chan_camera_error = None
        self.chan_camera_warning = None
        self.chan_frame = None
        self.chan_ff_ssim = None

        self.cmd_collect_compression = None
        self.cmd_collect_detector = None
        self.cmd_collect_directory = None
        self.cmd_collect_exposure_time = None
        self.cmd_collect_in_queue = None
        self.cmd_collect_num_images = None
        self.cmd_collect_overlap = None
        self.cmd_collect_range = None
        self.cmd_collect_scan_type = None
        self.cmd_collect_shutter = None
        self.cmd_collect_start_angle = None
        self.cmd_collect_template = None
        self.cmd_collect_start = None
        self.cmd_collect_shutterless = None
        self.cmd_collect_abort = None

        self.cmd_collect_ff_num_images = None
        self.cmd_collect_ff_offset = None
        self.cmd_collect_ff_pre = None
        self.cmd_collect_ff_post = None

        self.cmd_camera_trigger = None
        self.cmd_camera_live_view = None
        self.cmd_camera_write_data = None
        self.cmd_camera_ff_ssim = None

        self.beam_focusing_hwobj = None
        self.session_hwobj = None

    def init(self):
        """
        Init
        :return:
        """
        AbstractCollect.init(self)
        self.ready_event = gevent.event.Event()
        self.image_dimension = (2048, 2048)

        QtGraphicsManager.init(self)

        self.disconnect(self.camera_hwobj, "imageReceived", self.camera_image_received)

        self.disconnect(
            self.diffractometer_hwobj,
            "minidiffStateChanged",
            self.diffractometer_state_changed,
        )
        self.disconnect(
            self.diffractometer_hwobj,
            "centringStarted",
            self.diffractometer_centring_started,
        )
        self.disconnect(
            self.diffractometer_hwobj, "centringAccepted", self.create_centring_point
        )
        self.disconnect(
            self.diffractometer_hwobj,
            "centringSuccessful",
            self.diffractometer_centring_successful,
        )
        self.disconnect(
            self.diffractometer_hwobj,
            "centringFailed",
            self.diffractometer_centring_failed,
        )
        self.disconnect(
            self.diffractometer_hwobj,
            "pixelsPerMmChanged",
            self.diffractometer_pixels_per_mm_changed,
        )
        self.disconnect(
            self.diffractometer_hwobj,
            "omegaReferenceChanged",
            self.diffractometer_omega_reference_changed,
        )
        self.disconnect(
            self.diffractometer_hwobj,
            "minidiffPhaseChanged",
            self.diffractometer_phase_changed,
        )

        self.diffractometer_pixels_per_mm_changed((20.0, 20.0))

        self.camera_hwobj = None

        self.graphics_scale_item.set_start_position(20, self.image_dimension[1] - 20)

        self.graphics_scale_item.set_custom_pen_color(Colors.BLUE)
        self.graphics_omega_reference_item.set_custom_pen_color(Colors.DARK_BLUE)
        self.graphics_measure_distance_item.set_custom_pen_color(Colors.DARK_BLUE)
        self.graphics_beam_item.hide()

        self.graphics_view.scene().measureItemChanged.connect(self.measure_item_changed)
        self.graphics_view.scene().setSceneRect(
            0, 0, self.image_dimension[0], self.image_dimension[1]
        )

        self.qimage = QtImport.QImage()
        self.qpixmap = QtImport.QPixmap()

        self.chan_frame = self.getChannelObject("chanFrame")
        self.chan_frame.connectSignal("update", self.frame_changed)

        self.chan_ff_ssim = self.getChannelObject("chanFFSSIM")
        self.chan_ff_ssim.connectSignal("update", self.ff_ssim_changed)

        self.chan_collect_status = self.getChannelObject("collectStatus")
        self._actual_collect_status = self.chan_collect_status.getValue()
        self.chan_collect_status.connectSignal("update", self.collect_status_update)

        self.chan_collect_frame = self.getChannelObject("chanFrameCount")
        self.chan_collect_frame.connectSignal("update", self.collect_frame_update)

        self.chan_collect_error = self.getChannelObject("collectError")
        self.chan_collect_error.connectSignal("update", self.collect_error_update)

        self.chan_camera_warning = self.getChannelObject("cameraWarning")
        self.chan_camera_warning.connectSignal("update", self.camera_warning_update)

        self.chan_camera_error = self.getChannelObject("cameraError")
        self.chan_camera_error.connectSignal("update", self.camera_error_update)

        self.cmd_collect_detector = self.getCommandObject("collectDetector")
        self.cmd_collect_directory = self.getCommandObject("collectDirectory")
        self.cmd_collect_exposure_time = self.getCommandObject("collectExposureTime")
        self.cmd_collect_in_queue = self.getCommandObject("collectInQueue")
        self.cmd_collect_num_images = self.getCommandObject("collectNumImages")
        self.cmd_collect_range = self.getCommandObject("collectRange")
        self.cmd_collect_scan_type = self.getCommandObject("collectScanType")
        self.cmd_collect_shutter = self.getCommandObject("collectShutter")
        self.cmd_collect_shutterless = self.getCommandObject("collectShutterless")
        self.cmd_collect_start_angle = self.getCommandObject("collectStartAngle")
        self.cmd_collect_template = self.getCommandObject("collectTemplate")

        self.cmd_collect_ff_num_images = self.getCommandObject("collectFFNumImages")
        self.cmd_collect_ff_offset = self.getCommandObject("collectFFOffset")
        self.cmd_collect_ff_pre = self.getCommandObject("collectFFPre")
        self.cmd_collect_ff_post = self.getCommandObject("collectFFPost")

        self.cmd_camera_trigger = self.getCommandObject("cameraTrigger")
        self.cmd_camera_live_view = self.getCommandObject("cameraLiveView")
        self.cmd_camera_write_data = self.getCommandObject("cameraWriteData")
        self.cmd_camera_ff_ssim = self.getCommandObject("cameraFFSSIM")

        self.cmd_collect_start = self.getCommandObject("collectStart")
        self.cmd_collect_abort = self.getCommandObject("collectAbort")

        self.beam_focusing_hwobj = self.getObjectByRole("beam_focusing")
        self.session_hwobj = self.getObjectByRole("session")

    def frame_changed(self, data):
        """
        Displays frame comming from camera
        :param data:
        :return:
        """
        if self._collecting:
            jpgdata = StringIO(data)
            im = Image.open(jpgdata)
            self.qimage = ImageQt(im)
            self.graphics_camera_frame.setPixmap(
                self.qpixmap.fromImage(self.qimage, QtImport.Qt.MonoOnly)
            )

    def ff_ssim_changed(self, value):
        """
        Updates ff ssim
        :param value: list of lists
        :return:
        """
        if self._collecting:
            self.ff_ssim = list(value)
            self.ff_ssim.sort()

    def mouse_clicked(self, pos_x, pos_y, left_click):
        """
        Mouse click event for centering
        :param pos_x: int
        :param pos_y: int
        :param left_click: boolean
        :return:
        """
        QtGraphicsManager.mouse_clicked(self, pos_x, pos_y, left_click)
        # self.mouse_hold = True
        # self.mouse_coord = [pos_x, pos_y]
        if self.centering_started:
            self.diffractometer_hwobj.image_clicked(pos_x, pos_y)
            self.play_image_relative(90)
            # self.diffractometer_hwobj.move_omega_relative(90, timeout=5)
            self.centering_started -= 1

    def mouse_released(self, pos_x, pos_y):
        """
        Mouse release event
        :param pos_x:
        :param pos_y:
        :return:
        """
        QtGraphicsManager.mouse_released(self, pos_x, pos_y)
        self.mouse_hold = False

    def mouse_moved(self, pos_x, pos_y):
        """
        Mouse move event
        :param pos_x:
        :param pos_y:
        :return:
        """
        QtGraphicsManager.mouse_moved(self, pos_x, pos_y)
        if self.mouse_hold:
            if self.mouse_coord[0] - pos_x > 0:
                index = self.current_image_index + 1
            elif self.mouse_coord[0] - pos_x < 0:
                index = self.current_image_index - 1
            else:
                return

            if index < 0:
                index = self.image_count - 1
            elif index >= self.image_count:
                index = 0
            self.mouse_coord[0] = pos_x
            self.display_image(index)

    def measure_item_changed(self, measured_points, measured_pix_num):
        """
        Updates image measurement item
        :param measured_points:
        :param measured_pix_num:
        :return:
        """
        start_x = measured_points[0].x()
        start_y = measured_points[0].y()
        end_x = measured_points[1].x()
        end_y = measured_points[1].y()

        if self.image_reading_thread is None:
            im = np.array(self.qimage.bits()).reshape(
                self.qimage.width(), self.qimage.height()
            )
        else:
            im = self.image_reading_thread.get_raw_image(self.current_image_index)
        # im_slice = im[start_x:start_y,end_x,end_y]
        # print im_slice.size, im_slice
        x = np.linspace(start_x, end_x, measured_pix_num)
        y = np.linspace(start_y, end_y, measured_pix_num)

        zi = ndimage.map_coordinates(im, np.vstack((x, y)))

        self.emit("measureItemChanged", zi)

    def get_graphics_view(self):
        """
        Returns graphics view
        :return:
        """
        return self.graphics_view

    def set_repeate_image_play(self, value):
        """
        Sets repeat the image play
        :param value:
        :return:
        """
        self.repeat_image_play = value

    def set_graphics_scene_size(self, size, fixed):
        pass

    def pre_execute(self, data_model):
        """
        Pre execute method
        :param data_model:
        :return:
        """
        self._failed = False

        """
        if self.beam_focusing_hwobj.get_focus_mode() != "imaging":
            self._error_msg = "Beamline is not in Imaging mode"
            self.emit("collectFailed", self._error_msg)
            logging.getLogger("GUI").error("Imaging: Error during acquisition (%s)" % self._error_msg)
            self.ready_event.set()
            self._collecting = False
            self._failed = True
            return
        """

        self.emit("progressInit", ("Image acquisition", 100, False))
        self._collect_frame = 0
        self.printed_warnings = []
        self.printed_errors = []
        self.ff_ssim = None
        self.config_dict = {}

        path_template = data_model.acquisitions[0].path_template
        acq_params = data_model.acquisitions[0].acquisition_parameters
        im_params = data_model.xray_imaging_parameters

        self._number_of_images = acq_params.num_images

        if im_params.detector_distance:
            delta = im_params.detector_distance - self.detector_hwobj.get_distance()
            if abs(delta) > 0.0001:
                tine.set(
                    "/P14/P14DetTrans/ComHorTrans",
                    "IncrementMove.START",
                    -0.003482 * delta,
                )
                self.detector_hwobj.set_distance(
                    im_params.detector_distance, wait=True, timeout=30
                )

        self.cmd_collect_detector("pco")
        self.cmd_collect_directory(str(path_template.directory))
        self.cmd_collect_template(str(path_template.get_image_file_name()))
        self.cmd_collect_scan_type("xrimg")

        self.cmd_collect_exposure_time(acq_params.exp_time)
        self.cmd_collect_num_images(acq_params.num_images)
        self.cmd_collect_start_angle(acq_params.osc_start)
        self.cmd_collect_range(acq_params.osc_range)
        self.cmd_collect_in_queue(acq_params.in_queue != False)
        shutter_name = self.detector_hwobj.get_shutter_name()
        self.cmd_collect_shutter(shutter_name)

        self.cmd_collect_ff_num_images(im_params.ff_num_images)
        self.cmd_collect_ff_offset(
            [
                im_params.sample_offset_a,
                im_params.sample_offset_b,
                im_params.sample_offset_c,
            ]
        )
        self.cmd_collect_ff_pre(im_params.ff_pre)
        self.cmd_collect_ff_post(im_params.ff_post)

        if acq_params.osc_range == 0:
            self.cmd_camera_trigger(False)
        else:
            self.cmd_camera_trigger(True)
        self.cmd_camera_live_view(im_params.ff_apply)
        self.cmd_camera_write_data(im_params.camera_write_data)
        self.cmd_camera_ff_ssim(im_params.ff_ssim_enabled)

        self.set_osc_start(acq_params.osc_start)

        self.current_dc_parameters = qmo.to_collect_dict(
            data_model, self.session_hwobj, qmo.Sample()
        )[0]
        self.current_dc_parameters["status"] = "Running"
        self.current_dc_parameters["comments"] = ""

        self.store_data_collection_in_lims()

    def execute(self, data_model):
        """
        Main execute method
        :param data_model:
        :return:
        """
        if not self._failed:
            self._collecting = True
            self.ready_event.clear()
            gevent.spawn(self.cmd_collect_start)
            # self.cmd_collect_start()
            # if data_model.xray_imaging_parameters.camera_write_data:
            #    self.read_images_task = gevent.spawn(self.load_images, None, None, None, data_model)
            self.ready_event.wait()
            self.ready_event.clear()

    def post_execute(self, data_model):
        """
        Stores results in ispyb
        :param data_model:
        :return:
        """
        self.emit("progressStop", ())
        self._collecting = False

        acq_params = data_model.acquisitions[0].acquisition_parameters
        path_template = data_model.acquisitions[0].path_template

        filename_template = "%s_%d_%" + str(path_template.precision) + "d"
        config_filename = (
            filename_template
            % (
                path_template.base_prefix,
                path_template.run_number,
                path_template.start_num,
            )
            + ".json"
        )
        #config_file_path = os.path.join(path_template.directory, config_filename)
        archive_config_path = os.path.join(
            path_template.get_archive_directory(), config_filename
        )

        self.config_dict = {
            "collect": acq_params.as_dict(),
            "path": path_template.as_dict(),
            "imaging": data_model.xray_imaging_parameters.as_dict(),
            "ff_ssim": None,
        }

        if data_model.xray_imaging_parameters.ff_pre:
            self.config_dict["ff_ssim"] = self.ff_ssim

        try:
            if not os.path.exists(path_template.get_archive_directory()):
                os.makedirs(path_template.get_archive_directory())
            with open(archive_config_path, "w") as outfile:
                json.dump(self.config_dict, outfile)
            logging.getLogger("GUI").info(
                "Imaging: Acquisition parameters saved in %s" % archive_config_path
            )
        except BaseException:
            logging.getLogger("GUI").error(
                "Imaging: Unable to save acquisition parameters in %s"
                % archive_config_path
            )

        self.current_dc_parameters["status"] = "Data collection successful"
        self.update_data_collection_in_lims()

        # Copy first and last image to ispyb
        if self.image_reading_thread is not None:
            image_filename = (
                filename_template
                % (
                    path_template.base_prefix,
                    path_template.run_number,
                    path_template.start_num,
                )
                + ".jpeg"
            )
            image_filename = os.path.join(
                path_template.get_archive_directory(), image_filename
            )
            # misc.imsave(image_filename, self.image_reading_thread.get_raw_image(0))
            self.store_image_in_lims(0)
        if acq_params.num_images > 1:
            image_filename = (
                filename_template
                % (
                    path_template.base_prefix,
                    path_template.run_number,
                    acq_params.num_images - 1,
                )
                + ".jpeg"
            )
            image_filename = os.path.join(
                path_template.get_archive_directory(), image_filename
            )
            # misc.imsave(image_filename, self.image_reading_thread.get_raw_image(0))
            self.store_image_in_lims(acq_params.num_images - 1)

    @task
    def _take_crystal_snapshot(self, filename):
        """Saves crystal snapshot"""
        self.graphics_manager_hwobj.save_scene_snapshot(filename)

    def data_collection_hook(self):
        """
        Not implemented
        :return:
        """
        pass

    def move_motors(self, motor_position_dict):
        """
        Not implemented
        :param motor_position_dict:
        :return:
        """
        pass

    def trigger_auto_processing(self, process_event, frame_number):
        """
        Not implemented
        :param process_event:
        :param frame_number:
        :return:
        """
        pass

    def collect_status_update(self, status):
        """Status event that controls execution

        :param status: collection status
        :type status: string
        """
        if status != self._actual_collect_status:
            self._previous_collect_status = self._actual_collect_status
            self._actual_collect_status = status
            if self._collecting:
                if self._actual_collect_status == "error":
                    self.emit("collectFailed", self._error_msg)
                    logging.getLogger("GUI").error(
                        "Imaging: Error during the acquisition (%s)" % self._error_msg
                    )
                    self.ready_event.set()
                    self._collecting = False
                if self._previous_collect_status is None:
                    if self._actual_collect_status == "busy":
                        self.print_log(
                            "GUI", "info", "Imaging: Preparing acquisition..."
                        )
                elif self._previous_collect_status == "busy":
                    if self._actual_collect_status == "collecting":
                        self.emit("collectStarted", (None, 1))
                        self.print_log("GUI", "info", "Imaging: Acquisition started")
                    elif self._actual_collect_status == "ready":
                        self.ready_event.set()
                        self._collecting = False
                elif self._previous_collect_status == "collecting":
                    if self._actual_collect_status == "ready":
                        self.ready_event.set()
                        self._collecting = False
                        if self.ff_ssim is None:
                            self.ff_ssim_changed(self.chan_ff_ssim.getValue())
                        logging.getLogger("GUI").info("Imaging: Acquisition done")
                    elif self._actual_collect_status == "aborting":
                        self.print_log("HWR", "info", "Imaging: Aborting...")
                        self.ready_event.set()
                        self._collecting = False

    def collect_error_update(self, error_msg):
        """Collect error behaviour

        :param error_msg: error message
        :type error_msg: string
        """

        if self._collecting and len(error_msg) > 0:
            self._error_msg = error_msg.replace("\n", "")
            logging.getLogger("GUI").error(
                "Imaging: Error from detector server: %s" % error_msg
            )

    def collect_frame_update(self, frame):
        """Image frame update

        :param frame: frame num
        :type frame: int
        """
        if self._collecting:
            if self._collect_frame != frame:
                self._collect_frame = frame
                self.emit(
                    "progressStep", (int(float(frame) / self._number_of_images * 100))
                )
                self.emit("collectImageTaken", frame)

    def camera_warning_update(self, warning_str):
        """
        Displays camera warnings
        :param warning_str:
        :return:
        """
        if self._collecting:
            if warning_str.endswith("\n"):
                warning_str = warning_str[:-1]
            if warning_str.startswith("\n"):
                warning_str = warning_str[1:]
            warning_list = warning_str.split("\n")

            for warning in warning_list:
                if warning and warning not in self.printed_warnings:
                    logging.getLogger("GUI").warning(
                        "Imaging: PCO camera warning: %s" % warning
                    )
                    self.printed_warnings.append(warning)

    def camera_error_update(self, error_str):
        """
        Displays camera errors
        :param error_str:
        :return:
        """
        if self._collecting:
            if error_str.endswith("\n"):
                error_str = error_str[:-1]
            if error_str.startswith("\n"):
                error_str = error_str[1:]
            error_list = error_str.split("\n")

            for error in error_list:
                if error and error not in self.printed_errors:
                    logging.getLogger("GUI").error(
                        "Imaging: PCO camera error: %s" % error
                    )
                    self.printed_errors.append(error)

    def set_ff_apply(self, state):
        """
        Apply ff to live view
        :param state:
        :return:
        """
        self.ff_apply = state
        self.display_image(self.current_image_index)

    def display_image(self, index):
        """
        Displays image on the canvas
        :param index: int
        :return:
        """
        angle = self.collect_omega_start + index * self.image_count / 360.0
        if angle > 360:
            angle -= 360
        elif angle < 0:
            angle += 360

        self.graphics_omega_reference_item.set_phi_position(angle)
        self.current_image_index = index

        im = self.image_reading_thread.get_raw_image(index)

        if self.ff_apply and self.image_processing_thread:
            if self.ff_corrected_list[index] is None:
                im_min, im_max = self.image_processing_thread.get_im_min_max()
                im = self.image_reading_thread.get_raw_image(index).astype(float)
                ff_image = self.image_reading_thread.get_ff_image(index).astype(float)
                ff_corrected_image = np.divide(
                    im, ff_image, out=np.ones_like(im), where=ff_image != 0
                )
                im = 255.0 * (ff_corrected_image - im_min) / (im_max - im_min)
                self.ff_corrected_list[index] = im.astype(np.uint16)
            else:
                im = self.ff_corrected_list[index]

        # sx = ndimage.sobel(im, axis=0, mode='constant')
        # sy = ndimage.sobel(im, axis=1, mode='constant')
        # im = np.hypot(sx, sy)

        if im is not None:
            self.qimage = QtImport.QImage(
                im.astype(np.uint8),
                im.shape[1],
                im.shape[0],
                im.shape[1],
                QtImport.QImage.Format_Indexed8,
            )
            self.graphics_camera_frame.setPixmap(self.qpixmap.fromImage(self.qimage))
            self.emit("imageLoaded", index)

    def display_image_relative(self, relative_index):
        """
        Displays relative image
        :param relative_index:
        :return:
        """
        self.display_image(self.current_image_index + relative_index)

    def play_image_relative(self, relative_angle):
        """
        Starts image video
        :param relative_angle:
        :return:
        """
        self.play_images(0.04, relative_angle, False)

    def set_osc_start(self, osc_start):
        """
        Defines osc start
        :param osc_start: float
        :return:
        """
        self.collect_omega_start = osc_start

    def set_omega_move_enabled(self, state):
        """
        Move omega if the image has been displayed
        :param state:
        :return:
        """
        self.omega_move_enabled = state

    def load_images(
        self,
        data_path=None,
        flat_field_path=None,
        config_path=None,
        data_model=None,
        load_all=True,
    ):
        """
        Load and process images via threads
        :param data_path: str
        :param flat_field_path: str
        :param config_path: str
        :param data_model:
        :param load_all: boolean
        :return:
        """

        ff_ssim = None
        self.config_dict = {}
        self.omega_start = self.diffractometer_hwobj.get_omega_position()

        self.image_reading_thread = None
        self.image_processing_thread = None

        ff_filename_list = []
        raw_filename_list = []

        if not data_model:
            if data_path.endswith("tiff"):
                ext_len = 4
            else:
                ext_len = 3

            base_name_list = os.path.splitext(os.path.basename(data_path))
            prefix = base_name_list[0][: -(ext_len + 1)]

            # Reading config json --------------------------------------------
            if config_path is None:
                config_path = data_path[:-ext_len] + "json"
            if os.path.exists(config_path):
                with open(config_path) as f:
                    self.config_dict = json.load(f)
                ff_ssim = self.config_dict["ff_ssim"]
                self.set_osc_start(self.config_dict["collect"]["osc_start"])
            else:
                logging.getLogger("user_level_log").error(
                    "Imaging: Unable to open config file %s" % config_path
                )

        if data_model:
            if data_model.xray_imaging_parameters.ff_pre:
                path_template = data_model.acquisitions[0].path_template
                for index in range(data_model.xray_imaging_parameters.ff_num_images):
                    ff_filename_list.append(
                        os.path.join(
                            path_template.directory,
                            "ff_" + path_template.get_image_file_name() % (index + 1),
                        )
                    )
        elif os.path.exists(flat_field_path):

            base_name_list = os.path.splitext(os.path.basename(data_path))
            os.chdir(os.path.dirname(flat_field_path))
            ff_filename_list = sorted(
                [
                    os.path.join(os.path.dirname(flat_field_path), f)
                    for f in os.listdir(os.path.dirname(flat_field_path))
                    if f.startswith("ff_" + prefix)
                ]
            )

        # Reading raw images -------------------------------------------------
        if data_model:
            acq_params = data_model.acquisitions[0].acquisition_parameters
            path_template = data_model.acquisitions[0].path_template
            for index in range(acq_params.num_images):
                raw_filename_list.append(
                    os.path.join(
                        path_template.directory,
                        path_template.get_image_file_name() % (index + 1),
                    )
                )
        elif os.path.exists(data_path):
            os.chdir(os.path.dirname(data_path))
            raw_filename_list = sorted(
                [
                    os.path.join(os.path.dirname(data_path), f)
                    for f in os.listdir(os.path.dirname(data_path))
                    if f.startswith(prefix)
                ]
            )
        else:
            acq_params = data_model.acquisitions[0].acquisition_parameters
            path_template = data_model.acquisitions[0].path_template
            for index in range(acq_params.num_images):
                raw_filename_list.append(
                    os.path.join(
                        path_template.directory,
                        path_template.get_image_file_name() % (index + 1),
                    )
                )

        self.image_count = len(raw_filename_list)
        if self.image_reading_thread is not None:
            self.image_reading_thread.set_stop()
        if self.image_processing_thread is not None:
            image_processing_queue.queue.clear()
            self.image_processing_thread.set_stop()

        self.ff_corrected_list = [None] * self.image_count

        self.image_reading_thread = ImageReadingThread(
            raw_filename_list, ff_filename_list, ff_ssim
        )
        self.image_reading_thread.start()

        if ff_filename_list:
            self.image_processing_thread = ImageProcessingThread(self.image_count)
            self.image_processing_thread.start()

        self.current_image_index = 0
        self.emit("imageInit", self.image_count)

        # gevent.sleep(5)
        self.last_image_index = 0
        # self.display_image(0)

    def play_images(self, exp_time=0.04, relative_index=None, repeat=True):
        """
        Play image video
        :param exp_time:
        :param relative_index:
        :param repeat:
        :return:
        """
        self.image_polling = gevent.spawn(
            self.do_image_polling, exp_time, relative_index, repeat
        )

    def do_image_polling(self, exp_time=0.04, relative_index=1, repeat=False):
        """
        Image polling task
        :param exp_time:
        :param relative_index:
        :param repeat:
        :return:
        """
        self.repeat_image_play = repeat

        direction = 1 if relative_index > 0 else -1
        rotate_in_sec = 10

        step = int(self.image_count / (rotate_in_sec / exp_time))
        index = 0

        while self.current_image_index < self.image_count:
            if index >= abs(relative_index):
                break

            self.display_image(self.current_image_index)
            self.current_image_index += direction * step
            if self.repeat_image_play and self.current_image_index >= self.image_count:
                self.current_image_index -= self.image_count
            gevent.sleep(exp_time)
            index += step

    def stop_image_play(self):
        """
        Stop image video
        :return:
        """
        self.image_polling.kill()

    def stop_collect(self):
        """
        Stops image collection
        :return:
        """
        self.cmd_collect_abort()

    def mouse_wheel_scrolled(self, delta):
        """
        Handles mouse scroll
        :param delta:
        :return:
        """
        if (
            self.image_reading_thread is None
            or self.image_reading_thread.get_raw_image(self.current_image_index) is None
        ):
            return

        if delta > 0:
            self.current_image_index -= 1
            if self.current_image_index < 0:
                self.current_image_index = self.image_count - 1
        else:
            self.current_image_index += 1
            if self.current_image_index == self.image_count:
                self.current_image_index = 0
        self.display_image(self.current_image_index)

    def start_centering(self):
        """
        Starts 3 click centering
        :return:
        """
        self.centering_started = 3
        self.diffractometer_hwobj.start_centring_method(
            self.diffractometer_hwobj.CENTRING_METHOD_IMAGING
        )

    def start_n_centering(self):
        """
        Starts n click centering
        :return:
        """
        self.centering_started = 100
        self.diffractometer_hwobj.start_centring_method(
            self.diffractometer_hwobj.CENTRING_METHOD_IMAGING_N
        )

    def move_omega(self, image_index):
        """
        Rotates omega
        :param image_index:
        :return:
        """
        if image_index != self.last_image_index:
            if self.config_dict:
                omega_relative = self.config_dict["collect"]["osc_range"] * image_index
            else:
                omega_relative = self.image_count / 360.0 * image_index
            if self.last_image_index > image_index:
                omega_relative *= -1

            self.diffractometer_hwobj.move_omega_relative(omega_relative)
            self.last_image_index = image_index

    def move_omega_relative(self, relative_index):
        """
        Rotates omega relative
        :param relative_index:
        :return:
        """
        self.move_omega(self.last_image_index + relative_index)


class GraphicsCameraFrame(QtImport.QGraphicsPixmapItem):
    """
    Custom QGraphicsPixmapItem
    """

    def __init__(self, parent=None):
        """
        init
        :param parent:
        """
        super(GraphicsCameraFrame, self).__init__(parent)

    def mousePressEvent(self, event):
        """
        Sends mouseClickedSignal
        :param event:
        :return:
        """
        pos = QtImport.QPointF(event.pos())
        self.scene().parent().mouseClickedSignal.emit(
            pos.x(), pos.y(), event.button() == QtImport.Qt.LeftButton
        )
        self.update()

    def mouseMoveEvent(self, event):
        """
        Sends mouseMovedSignal
        :param event:
        :return:
        """
        pos = QtImport.QPointF(event.pos())
        self.scene().parent().mouseMovedSignal.emit(pos.x(), pos.y())
        self.update()

    # def mouseDoubleClickEvent(self, event):
    #    position = QtImport.QPointF(event.pos())
    #    self.scene().mouseDoubleClickedSignal.emit(position.x(), position.y())
    #    self.update()

    def mouseReleaseEvent(self, event):
        """
        Sends mouseReleasedSignal
        :param event:
        :return:
        """
        pos = QtImport.QPointF(event.pos())
        self.scene().parent().mouseReleasedSignal.emit(pos.x(), pos.y())
        self.update()


class GraphicsView(QtImport.QGraphicsView):
    """
    Custom QGraphicsView
    """
    mouseClickedSignal = QtImport.pyqtSignal(int, int, bool)
    mouseReleasedSignal = QtImport.pyqtSignal(int, int)
    mouseMovedSignal = QtImport.pyqtSignal(int, int)
    keyPressedSignal = QtImport.pyqtSignal(str)
    wheelSignal = QtImport.pyqtSignal(int)

    def __init__(self, parent=None):
        """
        init
        :param parent:
        """
        super(GraphicsView, self).__init__(parent)

        self.setScene(QtImport.QGraphicsScene(self))
        self.scene().clearSelection()
        self.setMouseTracking(True)
        self.setDragMode(QtImport.QGraphicsView.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(QtImport.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtImport.Qt.ScrollBarAlwaysOff)

    def wheelEvent(self, event):
        """
        Sends wheelSignal
        :param event:
        :return:
        """
        self.wheelSignal.emit(event.delta())


class ImageProcessingThread(threading.Thread):
    """
    Image processing thread applies flat field correction
    """
    def __init__(self, image_count):
        threading.Thread.__init__(self)

        self.thread_done = None
        self.stopped = False

        self.image_count = image_count
        self.im_min = pow(2, 16)
        self.im_max = 0

        self.ff_applied = None

    def start(self):
        """
        Starts processing thread
        :return:
        """
        self.thread_done = gevent.event.Event()
        threading.Thread.start(self)
        return self.thread_done

    def set_stop(self):
        """
        Stops processing thread
        :return:
        """
        self.stopped = True
        logging.getLogger("GUI").info("Image processing stopped")

    def get_im_min_max(self):
        """
        Returns min and max pixel values
        :return:
        """
        return self.im_min, self.im_max

    def run(self):
        """
        Processing task
        :return:
        """
        logging.getLogger("GUI").info("Image processing started...")
        progress_step = 20

        while not self.stopped:
            (raw_image, ff_image, index) = image_processing_queue.get()

            self.ff_applied = np.divide(
                raw_image.astype(float),
                ff_image.astype(float),
                out=np.ones_like(raw_image.astype(float)),
                where=ff_image.astype(float) != 0,
            )
            self.ff_applied[ff_image == (pow(2, 16) - 1)] = 1

            if (
                self.ff_applied[8:].min() < self.im_min
                and self.ff_applied[8:].max() > self.im_max
            ):
                self.im_min = self.ff_applied[8:].min()
                self.im_max = self.ff_applied[8:].max()

            image_processing_queue.task_done()

            done_per = int(float(index) / self.image_count * 100)
            if not index % (self.image_count / (100 / progress_step)) and done_per > 0:
                logging.getLogger("GUI").info(
                    "Image processing %d%% completed" % done_per
                )
            if index == self.image_count - 1:
                logging.getLogger("GUI").info("Image processing finished")
                break


class ImageReadingThread(threading.Thread):
    """
    Image reading thread reads image and adds it to queue for image processing thread
    """

    def __init__(self, raw_filename_list, ff_filename_list=[], ff_ssim=[]):
        """
        init
        :param raw_filename_list:
        :param ff_filename_list:
        :param ff_ssim:
        """
        threading.Thread.__init__(self)

        self.thread_done = None
        self.stopped = False
        self.failed_to_read_count = 10
        self.raw_filename_list = raw_filename_list
        self.ff_filename_list = ff_filename_list

        self.raw_image_list = [None] * len(self.raw_filename_list)
        self.ff_image_list = [None] * len(self.ff_filename_list)

        self.ff_ssim = None

    def start(self):
        """
        Starts the thread
        :return:
        """
        self.thread_done = gevent.event.Event()
        threading.Thread.start(self)
        return self.thread_done

    def set_stop(self):
        """
        Stops the thread
        :return:
        """
        self.stopped = True
        logging.getLogger("GUI").info("Image reading stopped")

    def set_ff_ssim(self, ff_ssim):
        """
        Sets ff ssim list
        :param ff_ssim: list of lists
        :return:
        """
        self.ff_ssim = ff_ssim

    def read_image(self, filename, timeout=10):
        """
        Image reading method
        :param filename:
        :param timeout:
        :return:
        """
        if timeout:
            try:
                with gevent.Timeout(
                    timeout, Exception("Timeout waiting for image %s" % filename)
                ):
                    while not os.path.isfile(filename):
                        gevent.sleep(0.5)
                    return cv.imread(filename, cv.IMREAD_ANYDEPTH)
            except gevent.Timeout:
                # Skip the image or
                self.failed_to_read_count -= 1
                if self.failed_to_read_count == 0:
                    self.set_stop()
        else:
            return cv.imread(filename, cv.IMREAD_ANYDEPTH)

    def run(self):
        """
        Main run method
        :return:
        """
        # GB: 20190303: dumping to avoid endless waiting for image reading
        return

        logging.getLogger("GUI").info("Image reading started...")
        for index, filename in enumerate(self.ff_filename_list):
            if self.stopped:
                # self.thread_watcher.send()
                return
            self.ff_image_list[index] = self.read_image(filename)

        progress_step = 20

        for index, filename in enumerate(self.raw_filename_list):
            if self.stopped:
                # self.thread_watcher.send()
                return
            self.raw_image_list[index] = self.read_image(filename)
            done_per = int(float(index) / len(self.raw_filename_list) * 100)
            if (
                not index % (len(self.raw_filename_list) / (100 / progress_step))
                and done_per > 0
            ):
                logging.getLogger("GUI").info("Image reading %d%% completed" % done_per)

            if self.ff_filename_list:
                ff_index = 0
                image_processing_queue.put(
                    (self.raw_image_list[index], self.ff_image_list[ff_index], index)
                )
        logging.getLogger("GUI").info("Image reading finished")
        # self.thread_watcher.send()

    def get_raw_image(self, index):
        """
        Returns raw image based on index
        :param index: int
        :return:
        """
        return self.raw_image_list[index]

    def get_ff_image(self, raw_image_index):
        """
        Returns flat field corrected image
        :param raw_image_index: int
        :return:
        """
        if self.ff_ssim:
            ff_index = self.ff_ssim[raw_image_index][2] - 1
        else:
            ff_index = int(
                raw_image_index
                / float(len(self.raw_image_list))
                * len(self.ff_image_list)
            )
        return self.ff_image_list[ff_index]
