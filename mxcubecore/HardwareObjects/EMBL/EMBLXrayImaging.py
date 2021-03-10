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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import os
import tine
import json
import time
import Image
import logging
import threading
import collections
from queue import Queue
from copy import deepcopy

import gevent

import cv2 as cv
import numpy as np
from scipy import ndimage, misc

from cStringIO import StringIO
from PIL.ImageQt import ImageQt

from mxcubecore.utils import qt_import, Colors
from mxcubecore.TaskUtils import task
from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect
from mxcubecore.HardwareObjects.QtGraphicsManager import QtGraphicsManager
from mxcubecore.HardwareObjects import queue_model_objects as qmo
from mxcubecore import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__category__ = "Task"


image_processing_queue = Queue()


def read_image(filename, timeout=10):
    if timeout:
        try:
            with gevent.Timeout(timeout):
                while not os.path.isfile(filename):
                    gevent.sleep(0.5)
                return cv.imread(filename, cv.IMREAD_ANYDEPTH)
        except gevent.Timeout:
            return
    else:
        return cv.imread(filename, cv.IMREAD_ANYDEPTH)


class EMBLXrayImaging(QtGraphicsManager, AbstractCollect):
    def __init__(self, *args):
        QtGraphicsManager.__init__(self, *args)
        AbstractCollect.__init__(self, *args)

        self.ff_apply = False
        self.ff_ssim = None
        self.qimage = None
        self.qpixmap = None
        self.image_count = 0
        self.image_reading_thread = None
        self.ff_corrected_list = []
        self.config_dict = {}
        self.collect_omega_start = 0
        self.omega_start = 0
        self.omega_move_enabled = False
        self.reference_distance = None
        self.reference_angle = None
        self.motor_positions = None

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
        self.printed_warnings = []
        self.printed_errors = []

        self.chan_collect_status = None
        self.chan_collect_frame = None
        self.chan_collect_error = None
        self.chan_camera_error = None
        self.chan_camera_warning = None
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

    def init(self):
        AbstractCollect.init(self)
        self.ready_event = gevent.event.Event()
        self.image_dimension = (2048, 2048)
        self.reference_distance = self.get_property("reference_distance")
        self.reference_angle = self.get_property("reference_angle")

        QtGraphicsManager.init(self)

        self.disconnect(
            HWR.beamline.sample_view.camera, "imageReceived", self.camera_image_received
        )

        self.disconnect(
            HWR.beamline.diffractometer,
            "minidiffStateChanged",
            self.diffractometer_state_changed,
        )
        self.disconnect(
            HWR.beamline.diffractometer,
            "centringStarted",
            self.diffractometer_centring_started,
        )
        self.disconnect(
            HWR.beamline.diffractometer, "centringAccepted", self.create_centring_point,
        )
        self.disconnect(
            HWR.beamline.diffractometer,
            "centringSuccessful",
            self.diffractometer_centring_successful,
        )
        self.disconnect(
            HWR.beamline.diffractometer,
            "centringFailed",
            self.diffractometer_centring_failed,
        )
        self.disconnect(
            HWR.beamline.diffractometer,
            "pixelsPerMmChanged",
            self.diffractometer_pixels_per_mm_changed,
        )
        self.disconnect(
            HWR.beamline.diffractometer,
            "omegaReferenceChanged",
            self.diffractometer_omega_reference_changed,
        )
        self.disconnect(
            HWR.beamline.diffractometer,
            "minidiffPhaseChanged",
            self.diffractometer_phase_changed,
        )

        self.diffractometer_pixels_per_mm_changed((20.0, 20.0))
        self.graphics_manager_hwobj = self.get_object_by_role("graphics_manager")

        self.graphics_scale_item.set_start_position(20, self.image_dimension[1] - 20)

        self.graphics_scale_item.set_custom_pen_color(Colors.BLUE)
        self.graphics_omega_reference_item.set_custom_pen_color(Colors.DARK_BLUE)
        self.graphics_measure_distance_item.set_custom_pen_color(Colors.DARK_BLUE)
        self.graphics_beam_item.hide()

        self.graphics_view.scene().measureItemChanged.connect(self.measure_item_changed)
        self.graphics_view.scene().setSceneRect(
            0, 0, self.image_dimension[0], self.image_dimension[1]
        )

        self.qimage = qt_import.QImage()
        self.qpixmap = qt_import.QPixmap()

        self.chan_frame = self.get_channel_object("chanFrame")
        self.chan_frame.connect_signal("update", self.frame_changed)

        self.chan_ff_ssim = self.get_channel_object("chanFFSSIM")
        self.chan_ff_ssim.connect_signal("update", self.ff_ssim_changed)

        self.chan_collect_status = self.get_channel_object("collectStatus")
        # self._actual_collect_status = self.chan_collect_status.get_value()
        self.chan_collect_status.connect_signal("update", self.collect_status_update)

        self.chan_collect_frame = self.get_channel_object("chanFrameCount")
        self.chan_collect_frame.connect_signal("update", self.collect_frame_update)

        self.chan_collect_error = self.get_channel_object("collectError")
        self.chan_collect_error.connect_signal("update", self.collect_error_update)

        self.chan_camera_warning = self.get_channel_object("cameraWarning")
        self.chan_camera_warning.connect_signal("update", self.camera_warning_update)

        self.chan_camera_error = self.get_channel_object("cameraError")
        self.chan_camera_error.connect_signal("update", self.camera_error_update)

        self.cmd_collect_detector = self.get_command_object("collectDetector")
        self.cmd_collect_directory = self.get_command_object("collectDirectory")
        self.cmd_collect_exposure_time = self.get_command_object("collectExposureTime")
        self.cmd_collect_in_queue = self.get_command_object("collectInQueue")
        self.cmd_collect_num_images = self.get_command_object("collectNumImages")
        self.cmd_collect_range = self.get_command_object("collectRange")
        self.cmd_collect_scan_type = self.get_command_object("collectScanType")
        self.cmd_collect_shutter = self.get_command_object("collectShutter")
        self.cmd_collect_shutterless = self.get_command_object("collectShutterless")
        self.cmd_collect_start_angle = self.get_command_object("collectStartAngle")
        self.cmd_collect_template = self.get_command_object("collectTemplate")

        self.cmd_collect_ff_num_images = self.get_command_object("collectFFNumImages")
        self.cmd_collect_ff_offset = self.get_command_object("collectFFOffset")
        self.cmd_collect_ff_pre = self.get_command_object("collectFFPre")
        self.cmd_collect_ff_post = self.get_command_object("collectFFPost")

        self.cmd_camera_trigger = self.get_command_object("cameraTrigger")
        self.cmd_camera_live_view = self.get_command_object("cameraLiveView")
        self.cmd_camera_write_data = self.get_command_object("cameraWriteData")
        self.cmd_camera_ff_ssim = self.get_command_object("cameraFFSSIM")

        self.cmd_collect_start = self.get_command_object("collectStart")
        self.cmd_collect_abort = self.get_command_object("collectAbort")

        self.beam_focusing_hwobj = self.get_object_by_role("beam_focusing")

    def frame_changed(self, data):
        if self._collecting:
            jpgdata = StringIO(data)
            im = Image.open(jpgdata)
            self.qimage = ImageQt(im)
            self.graphics_camera_frame.setPixmap(
                self.qpixmap.fromImage(self.qimage, qt_import.Qt.MonoOnly)
            )

    def ff_ssim_changed(self, value):
        if self._collecting:
            self.ff_ssim = list(value)
            self.ff_ssim.sort()

    def mouse_clicked(self, pos_x, pos_y, left_click):
        QtGraphicsManager.mouse_clicked(self, pos_x, pos_y, left_click)
        if self.centering_started:
            self.motor_positions["phi"] = self.omega_angle
            HWR.beamline.diffractometer.set_static_positions(self.motor_positions)
            HWR.beamline.diffractometer.image_clicked(pos_x, pos_y)
            self.centering_started -= 1
        if not self.centering_started:
            self.set_centring_state(False)

    def mouse_released(self, pos_x, pos_y):
        QtGraphicsManager.mouse_released(self, pos_x, pos_y)
        self.mouse_hold = False

    def mouse_moved(self, pos_x, pos_y):
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
        return self.graphics_view

    def set_repeate_image_play(self, value):
        self.repeat_image_play = value

    def set_graphics_scene_size(self, size, fixed):
        pass

    def stop_move_beam_mark(self):
        """Stops to move beam mark

        :emits: infoMsg as str
        """
        self.set_cursor_busy(False)
        self.in_move_beam_mark_state = False
        self.graphics_move_beam_mark_item.hide()
        self.graphics_view.graphics_scene.update()
        pos_x = self.graphics_move_beam_mark_item.end_coord[0]
        pos_y = self.graphics_move_beam_mark_item.end_coord[1]

        HWR.beamline.diffractometer.set_imaging_beam_position(pos_x, pos_y)
        logging.getLogger("GUI").info(
            "Imaging beam position set to %d, %d" % (pos_x, pos_y)
        )
        self.emit("infoMsg", "")

    def diffractometer_phi_motor_moved(self, position):
        """Method when phi motor changed. Updates omega reference by
           redrawing phi angle

        :param position: phi rotation value
        :type position: float
        """
        QtGraphicsManager.diffractometer_phi_motor_moved(self, position)
        # logging.getLogger("GUI").info(str(position))
        self.display_image_by_angle(position)

    def pre_execute(self, data_model):
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

        if im_params.detector_distance is not None:
            logging.getLogger("GUI").warning(
                "Imaging: Setting detector distance to %d mm"
                % int(im_params.detector_distance)
            )

            delta = (
                im_params.detector_distance - self.reference_distance
            ) * self.reference_angle
            for motor in self.beam_focusing_hwobj.get_focus_motors():
                if motor["motorName"] == "P14DetHor1":
                    target = motor["focusingModes"]["Imaging"] + delta
                    tine.set("/P14/P14DetTrans/P14detHor1", "Move.START", target)
                elif motor["motorName"] == "P14DetHor2":
                    target = motor["focusingModes"]["Imaging"] + delta
                    tine.set("/P14/P14DetTrans/P14detHor2", "Move.START", target)
            # TODO add later wait
            time.sleep(3)
            HWR.beamline.detector.distance.set_value(
                im_params.detector_distance, timeout=30
            )
            logging.getLogger("GUI").info("Imaging: Detector distance set")

        self.cmd_collect_detector("pco")
        self.cmd_collect_directory(str(path_template.directory))
        self.cmd_collect_template(str(path_template.get_image_file_name()))
        self.cmd_collect_scan_type("xrimg")

        self.cmd_collect_exposure_time(acq_params.exp_time)
        self.cmd_collect_num_images(acq_params.num_images)
        self.cmd_collect_start_angle(acq_params.osc_start)
        self.cmd_collect_range(acq_params.osc_range)
        self.cmd_collect_in_queue(acq_params.in_queue != False)
        shutter_name = HWR.beamline.detector.get_shutter_name()
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
            data_model, HWR.beamline.session, qmo.Sample()
        )[0]
        self.current_dc_parameters["status"] = "Running"
        self.current_dc_parameters["comments"] = ""

        self.motor_positions = HWR.beamline.diffractometer.get_positions()
        self.take_crystal_snapshots()

        self.store_data_collection_in_lims()

    def execute(self, data_model):
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
        config_file_path = os.path.join(path_template.directory, config_filename)
        archive_config_path = os.path.join(
            path_template.get_archive_directory(), config_filename
        )

        self.config_dict = {
            "motor_pos": self.motor_positions,
            "collect": self.current_dc_parameters,
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
        except Exception:
            logging.getLogger("GUI").error(
                "Imaging: Unable to save acquisition parameters in %s"
                % archive_config_path
            )

        # self.current_dc_parameters["status"] = "Data collection successful"
        self.update_data_collection_in_lims()

        # Copy first and last image to ispyb
        if data_model.xray_imaging_parameters.camera_write_data:
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
            raw_image = read_image(
                path_template.get_image_path() % path_template.start_num, timeout=3
            )
            if raw_image is not None:
                misc.imsave(image_filename, raw_image)
                # Scale image from 2048x2048 to 256x256
                misc.imsave(
                    image_filename.replace(".jpeg", ".thumb.jpeg"),
                    misc.imresize(raw_image, (256, 256)),
                )
                self.store_image_in_lims(path_template.start_num)

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
                    raw_image = read_image(
                        path_template.get_image_path() % acq_params.num_images,
                        timeout=3,
                    )
                    if raw_image is not None:
                        misc.imsave(image_filename, raw_image)
                        misc.imsave(
                            image_filename.replace(".jpeg", ".thumb.jpeg"),
                            misc.imresize(raw_image, (256, 256)),
                        )
                        self.store_image_in_lims(
                            acq_params.num_images - path_template.start_num
                        )

    @task
    def _take_crystal_snapshot(self, filename):
        """Saves crystal snapshot"""
        self.graphics_manager_hwobj.save_scene_snapshot(filename)

    def data_collection_hook(self):
        pass

    @task
    def move_motors(self, motor_position_dict):
        """Move to centred position"""
        if motor_position_dict:
            HWR.beamline.diffractometer.move_motors(motor_position_dict)

    def trigger_auto_processing(self, process_event, frame_number):
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
                    # self.emit("collectFailed", self._error_msg)
                    error_msg = "Error during the acquisition (%s)" % self._error_msg
                    logging.getLogger("GUI").error("Imaging: %s" % error_msg)
                    self.collection_failed(error_msg)
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
                        # if self.ff_ssim is None:
                        #    self.ff_ssim_changed(self.chan_ff_ssim.get_value())
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
        self.ff_apply = state
        self.display_image(self.current_image_index)

    def display_image_by_angle(self, angle=None):
        if self.config_dict:
            if not angle:
                angle = self.omega_angle
            osc_seq = self.config_dict["collect"]["oscillation_sequence"][0]
            index = int(osc_seq["range"] * (angle - osc_seq["start"]))
            self.display_image(index)

    def display_image(self, index):
        if self.image_reading_thread is None:
            return

        # osc_seq = self.config_dict["collect"]["oscillation_sequence"][0]
        # angle = osc_seq["start"] + index * osc_seq["range"]
        # self.motor_positions["phi"] = angle
        # HWR.beamline.diffractometer.set_static_positions(self.motor_positions)
        # self.graphics_omega_reference_item.set_phi_position(angle)
        self.current_image_index = index

        raw_image = self.image_reading_thread.get_raw_image(index)

        if self.ff_apply:
            if self.ff_corrected_list[index] is None:
                corrected_im_min_max = (
                    self.image_reading_thread.get_corrected_im_min_max()
                )
                ff_image = self.image_reading_thread.get_ff_image(index).astype(float)
                ff_corrected_image = np.divide(
                    raw_image.astype(float),
                    ff_image,
                    out=np.ones_like(raw_image.astype(float)),
                    where=ff_image != 0,
                )
                im = (
                    255.0
                    * (ff_corrected_image - corrected_im_min_max[0])
                    / (corrected_im_min_max[1] - corrected_im_min_max[0])
                )
                self.ff_corrected_list[index] = im.astype(np.uint16)
            else:
                im = self.ff_corrected_list[index]
        else:
            raw_im_min_max = self.image_reading_thread.get_raw_im_min_max()
            im = (
                255.0
                * (raw_image - raw_im_min_max[0])
                / (raw_im_min_max[1] - raw_im_min_max[0])
            )

        if im is not None:
            self.qimage = qt_import.QImage(
                im.astype(np.uint8),
                im.shape[1],
                im.shape[0],
                im.shape[1],
                qt_import.QImage.Format_Indexed8,
            )
            self.graphics_camera_frame.setPixmap(self.qpixmap.fromImage(self.qimage))
            self.emit("imageLoaded", index)

    def display_image_relative(self, relative_index):
        self.display_image(self.current_image_index + relative_index)

    def play_image_relative(self, relative_angle):
        self.play_images(0.04, relative_angle, False)

    def set_osc_start(self, osc_start):
        self.collect_omega_start = osc_start

    def set_omega_move_enabled(self, state):
        self.omega_move_enabled = state

    def get_ff_and_config_path(self, raw_image_path):
        directory = os.path.dirname(raw_image_path)
        filename = os.path.basename(raw_image_path)

        ff_path = os.path.join(directory, "ff_%s_00001.tiff" % filename[:-11])
        if not os.path.exists(ff_path):
            ff_path = None
        config_path = os.path.join(
            directory.replace("mnt/beegfs/P14", "data/ispyb/p14"),
            "%s_00001.json" % filename[:-11],
        )
        if not os.path.exists(config_path):
            config_path = None

        return ff_path, config_path

    def load_images(
        self,
        data_path=None,
        flat_field_path=None,
        config_path=None,
        data_model=None,
        load_all=True,
    ):
        ff_ssim = None
        raw_filename_list = []
        ff_filename_list = []
        self.config_dict = {}
        self.omega_start = HWR.beamline.diffractometer.get_omega_position()
        self.motor_positions = None
        self.image_reading_thread = None

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
                self.motor_positions = deepcopy(self.config_dict["motor_pos"])
                HWR.beamline.diffractometer.set_static_positions(self.motor_positions)
            else:
                logging.getLogger("user_level_log").error(
                    "Imaging: Unable to open config file %s" % config_path
                )

        if data_model:
            if data_model.xray_imaging_parameters.ff_pre:
                acq_params = data_model.acquisitions[0].acquisition_parameters
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
            ff_prefix = base_name_list[0][: -(ext_len + 1)]
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

        self.ff_corrected_list = [None] * self.image_count

        self.image_reading_thread = ImageReadingThread(
            raw_filename_list, ff_filename_list, ff_ssim
        )
        self.image_reading_thread.start()

        self.current_image_index = 0
        self.emit("imageInit", self.image_count)

        gevent.sleep(2)
        self.last_image_index = 0
        self.display_image_by_angle()

    def play_images(self, exp_time=0.04, relative_angle=None, repeat=True):
        self.image_polling = gevent.spawn(
            self.do_image_polling, exp_time, relative_angle, repeat
        )

    def do_image_polling(self, exp_time=0.04, relative_angle=0, repeat=False):
        self.repeat_image_play = repeat

        direction = 1
        if relative_angle < 0:
            direction = -1
        rotate_in_sec = 2
        step = int(self.image_count / (rotate_in_sec / exp_time))
        start_index = self.current_image_index
        index = 0

        while self.current_image_index < self.image_count:
            if relative_angle:
                if index >= abs(self.image_count / 360.0 * relative_angle):
                    break
            logging.getLogger("HWR").debug("display: " + str(self.current_image_index))
            self.display_image(self.current_image_index)
            self.current_image_index += direction * step
            if self.repeat_image_play and self.current_image_index >= self.image_count:
                self.current_image_index = 0
            gevent.sleep(exp_time)
            index += step
        if relative_angle:
            self.display_image(
                int(start_index + self.image_count / 360.0 * relative_angle)
            )

    def stop_image_play(self):
        self.image_polling.kill()

    def stop_collect(self):
        self.cmd_collect_abort()

    def mouse_wheel_scrolled(self, delta):
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
        self.centering_started = 3
        self.set_centring_state(True)

        # osc_seq = self.config_dict["collect"]["oscillation_sequence"][0]
        # angle = osc_seq["start"] + index * osc_seq["range"]
        self.motor_positions["phi"] = self.omega_angle
        HWR.beamline.diffractometer.set_static_positions(self.motor_positions)

        HWR.beamline.diffractometer.start_centring_method(
            HWR.beamline.diffractometer.CENTRING_METHOD_IMAGING
        )

    def start_n_centering(self):
        self.centering_started = 100
        self.set_centring_state(True)
        HWR.beamline.diffractometer.start_centring_method(
            HWR.beamline.diffractometer.CENTRING_METHOD_IMAGING_N
        )


class GraphicsCameraFrame(qt_import.QGraphicsPixmapItem):
    def __init__(self, parent=None):
        super(GraphicsCameraFrame, self).__init__(parent)

    def mousePressEvent(self, event):
        pos = qt_import.QPointF(event.pos())
        self.scene().parent().mouseClickedSignal.emit(
            pos.x(), pos.y(), event.button() == qt_import.Qt.LeftButton
        )
        self.update()

    def mouseMoveEvent(self, event):
        pos = qt_import.QPointF(event.pos())
        self.scene().parent().mouseMovedSignal.emit(pos.x(), pos.y())
        self.update()

    # def mouseDoubleClickEvent(self, event):
    #    position = qt_import.QPointF(event.pos())
    #    self.scene().mouseDoubleClickedSignal.emit(position.x(), position.y())
    #    self.update()

    def mouseReleaseEvent(self, event):
        pos = qt_import.QPointF(event.pos())
        self.scene().parent().mouseReleasedSignal.emit(pos.x(), pos.y())
        self.update()


class GraphicsView(qt_import.QGraphicsView):
    mouseClickedSignal = qt_import.pyqtSignal(int, int, bool)
    mouseReleasedSignal = qt_import.pyqtSignal(int, int)
    mouseMovedSignal = qt_import.pyqtSignal(int, int)
    keyPressedSignal = qt_import.pyqtSignal(str)
    wheelSignal = qt_import.pyqtSignal(int)

    def __init__(self, parent=None):
        super(GraphicsView, self).__init__(parent)

        self.setScene(qt_import.QGraphicsScene(self))
        self.scene().clearSelection()
        self.setMouseTracking(True)
        self.setDragMode(qt_import.QGraphicsView.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(qt_import.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(qt_import.Qt.ScrollBarAlwaysOff)

    def wheelEvent(self, event):
        self.wheelSignal.emit(event.delta())


class ImageReadingThread(threading.Thread):
    def __init__(self, raw_filename_list, ff_filename_list=[], ff_ssim=[]):
        threading.Thread.__init__(self)

        self.stopped = False
        self.failed_to_read_count = 10
        self.raw_filename_list = raw_filename_list
        self.ff_filename_list = ff_filename_list

        self.raw_image_list = [None] * len(self.raw_filename_list)
        self.ff_image_list = [None] * len(self.ff_filename_list)

        self.ff_ssim = None
        self.raw_im_min_max = [pow(2, 16), 0]
        self.corrected_im_min_max = [pow(2, 16), 0]

    def start(self):
        # self.thread_watcher = gevent.get_hub().loop.async()
        self.thread_done = gevent.event.Event()
        threading.Thread.start(self)
        return self.thread_done

    def set_stop(self):
        self.stopped = True
        logging.getLogger("GUI").info("Image reading stopped")

    def set_ff_ssim(self, ff_ssim):
        self.ff_ssim = ff_ssim

    def run(self):
        logging.getLogger("GUI").info("Image reading started...")
        for index, filename in enumerate(self.ff_filename_list):
            if self.stopped:
                # self.thread_watcher.send()
                return
            self.ff_image_list[index] = read_image(filename)

        progress_step = 20

        for index, filename in enumerate(self.raw_filename_list):
            if self.stopped:
                return

            raw_image = read_image(filename)
            self.raw_image_list[index] = raw_image

            if index == 0:
                self.raw_im_min_max[0] = raw_image[8:].min()
                self.raw_im_min_max[1] = raw_image[8:].max()

            if self.ff_filename_list and index == 0:
                ff_image = self.get_ff_image(index)
                ff_applied = np.divide(
                    raw_image.astype(float),
                    ff_image.astype(float),
                    out=np.ones_like(raw_image.astype(float)),
                    where=ff_image.astype(float) != 0,
                )
                ff_applied[ff_image == (pow(2, 16) - 1)] = 1

                self.corrected_im_min_max[0] = ff_applied[8:].min()
                self.corrected_im_min_max[1] = ff_applied[8:].max()

            done_per = int(float(index) / len(self.raw_filename_list) * 100)
            if (
                not index % (len(self.raw_filename_list) / (100 / progress_step))
                and done_per > 0
            ):
                logging.getLogger("GUI").info("Image reading %d%% completed" % done_per)

        logging.getLogger("GUI").info("Image reading finished")
        # self.thread_watcher.send()

    def get_raw_image(self, index):
        return self.raw_image_list[index]

    def get_raw_im_min_max(self):
        return self.raw_im_min_max

    def get_corrected_im_min_max(self):
        return self.corrected_im_min_max

    def get_ff_image(self, raw_image_index):
        print "get_ff_image ", raw_image_index
        if self.ff_ssim:
            ff_index = self.ff_ssim[raw_image_index][2] - 1
        else:
            ff_index = int(
                raw_image_index
                / float(len(self.raw_image_list))
                * len(self.ff_image_list)
            )
        print ff_index
        return self.ff_image_list[ff_index]
