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
import Image
from cStringIO import StringIO
from PIL.ImageQt import ImageQt

import gevent
import QtImport
import cv2 as cv
import numpy as np

import multiprocessing
from multiprocessing import Pool as ThreadPool

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects import Qt4_GraphicsLib as GraphicsLib


__credits__ = ["EMBL Hamburg"]
__category__ = "Task"



#def append_image(filename):
#    base_name = filename.replace(".tiff", "")
#    index = int(base_name[-4:]) - 1
#    self.raw_image_arr[index] = (cv.imread(filename, 0))

class EMBLXrayImaging(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.raw_image_arr = []
        self.live_view_state = None
        self.ff_image_arr = None
        self.ff_corrected_image_arr = None
        self.ff_apply = False
        self.norm_min_max = [255, 0]
        self.qimage = None
        self.qpixmap = None

        self.image_dimension = (0, 0)
        self.graphics_camera_frame = None
        self.image_polling = None
        self.repeat_image_play = None
        self.current_image_index = None
        self.mouse_hold = False
        self.mouse_coord = [0, 0]
        self.osc_start = 0
        self.centering_started = 0

        self._collecting = False
        self._actual_collect_status = None
        self._previous_collect_status = None
        self._collect_frame = 0
        self._number_of_images = 0
        self._error_msg = ""
        self.ready_event = None

        self.graphics_view = None
        self.graphics_camera_frame = None
        self.graphics_scale_item = None
        self.graphics_omega_reference_item = None

        self.chan_collect_status = None
        self.chan_collect_frame = None
        self.chan_collect_error = None
        self.chan_camera_error = None
        self.chan_camera_warning = None

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

        self.detector_distance_hwobj = None
        self.diffractometer_hwobj = None

    def init(self):
        self.ready_event = gevent.event.Event()
        self.live_view_state = True
        self.pixels_per_mm = (1666, 1666)
        self.image_dimension = (2048, 2048)

        self.graphics_view = GraphicsLib.GraphicsView()
        self.graphics_camera_frame = GraphicsLib.GraphicsCameraFrame()
        self.graphics_scale_item = GraphicsLib.GraphicsItemScale(self)
        self.graphics_omega_reference_item = GraphicsLib.GraphicsItemOmegaReference(self)

        self.graphics_view.scene().addItem(self.graphics_camera_frame)
        self.graphics_view.scene().addItem(self.graphics_scale_item)
        self.graphics_view.scene().addItem(self.graphics_omega_reference_item)

        self.graphics_view.scene().setSceneRect(
            0, 0, self.image_dimension[0], self.image_dimension[1]
        )
        self.graphics_scale_item.set_start_position(0, 1600)
        self.graphics_scale_item.set_pixels_per_mm(self.pixels_per_mm)
        self.graphics_omega_reference_item.set_reference(
            (self.image_dimension[0] / 2, 0)
        )

        self.graphics_view.wheelSignal.connect(self.mouse_wheel_scrolled)
        self.graphics_view.scene().mouseClickedSignal.connect(self.mouse_clicked)
        self.graphics_view.scene().mouseReleasedSignal.connect(self.mouse_released)
        self.graphics_view.mouseMovedSignal.connect(self.mouse_moved)

        self.qimage = QtImport.QImage()
        self.qpixmap = QtImport.QPixmap()

        self.chan_frame = self.getChannelObject("chanFrame")
        if self.chan_frame is not None:
            self.chan_frame.connectSignal("update", self.frame_changed)

        self.chan_collect_status = self.getChannelObject("collectStatus")
        if self.chan_collect_status is not None:
            self._actual_collect_status = self.chan_collect_status.getValue()
            self.chan_collect_status.connectSignal("update", self.collect_status_update)
        self.chan_collect_frame = self.getChannelObject("collectFrame")
        if self.chan_collect_frame is not None:
            self.chan_collect_frame.connectSignal("update", self.collect_frame_update)
        self.chan_collect_error = self.getChannelObject("collectError")
        if self.chan_collect_error:
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

        self.cmd_collect_start = self.getCommandObject("collectStart")
        self.cmd_collect_abort = self.getCommandObject("collectAbort")

        self.diffractometer_hwobj = self.getObjectByRole("diffractometer")
        self.detector_distance_hwobj = self.getObjectByRole("detector_distance")

    def set_live_view_state(self, state):
        self.live_view_state = state

    def set_osc_start(self, osc_start):
        self.osc_start = osc_start

    def frame_changed(self, data):
        if self.live_view_state:
            jpgdata = StringIO(data)
            im = Image.open(jpgdata)
            self.qimage = ImageQt(im)

            # self.qimage = self.qimage.scaled(400, 400)
            # jpgdata = StringIO(data)
            # im = Image.open(jpgdata)
            # self.qimage = ImageQt(im)
            # f self.qimage is None:
            #   self.qimage = ImageQt(data)
            # lse:
            # self.qimage = self.qimage.loadFromData(Image.open(jpgdata))
            # self.qimage = QImage.loadFromData(data)

            # self.qpixmap.fromImage(self.qimage, QtImport.Qt.MonoOnly)
            self.graphics_camera_frame.setPixmap(
                self.qpixmap.fromImage(self.qimage, QtImport.Qt.MonoOnly)
            )

    def mouse_clicked(self, pos_x, pos_y, left_click):
        self.mouse_hold = True
        self.mouse_coord = [pos_x, pos_y]
        if self.centering_started:
            self.diffractometer_hwobj.image_clicked(pos_x, pos_y)
            self.display_relative_image(90)
            self.centering_started -= 1

    def mouse_released(self, pos_x, pos_y):
        self.mouse_hold = False

    def mouse_moved(self, pos_x, pos_y):
        if self.mouse_hold:
            if self.mouse_coord[0] - pos_x > 0:
                index = self.current_image_index + 1
            elif self.mouse_coord[0] - pos_x < 0:
                index = self.current_image_index - 1
            else:
                return

            if index < 0:
                index = len(self.raw_image_arr) - 1
            elif index >= len(self.raw_image_arr):
                index = 0
            self.mouse_coord[0] = pos_x
            self.display_image(index)

    def emit_frame(self):
        self.emit(
            "imageReceived", self.qpixmap.fromImage(self.qimage, QImport.Qt.MonoOnly)
        )

    def get_graphics_view(self):
        return self.graphics_view

    def set_repeate_image_play(self, value):
        self.repeat_image_play = value

    def set_graphics_scene_size(self, size, fixed):
        pass

    def pre_execute(self, data_model):
        self.emit("progressInit", ("Image acquisition", 100, False))
        self._collect_frame = 0

        path_template = data_model.acquisition.path_template
        acq_params = data_model.acquisition.acquisition_parameters
        im_params = data_model.xray_imaging_parameters

        self.detector_distance_hwobj.move(im_params.detector_distance, wait=True, timeout=30)

        self._number_of_images = acq_params.num_images

        if im_params.detector_distance:
            delta = im_params.detector_distance - self.detector_distance_hwobj.get_position()
            tine.set("/P14/P14DetTrans/ComHorTrans","IncrementMove.START", -0.003482*delta)
            self.detector_distance_hwobj.move(im_params.detector_distance, wait=True, timeout=30)

        self.cmd_collect_detector("pco")
        self.cmd_collect_directory(str(path_template.directory))
        self.cmd_collect_template(str(path_template.get_image_file_name()))
        self.cmd_collect_scan_type("xrimg")

        self.cmd_collect_exposure_time(acq_params.exp_time)
        self.cmd_collect_num_images(acq_params.num_images)
        self.cmd_collect_start_angle(acq_params.osc_start)
        self.cmd_collect_range(acq_params.osc_range)

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

    def execute(self, data_model):
        self._collecting = True
        self.ready_event.clear()
        self.data_collect_task = gevent.spawn(self.execute_task)
        self.ready_event.wait()
        self.ready_event.clear()

    def execute_task(self):
        self.cmd_collect_start()

    def post_execute(self, data_model):
        self.emit("progressStop", ())
        self._collecting = False

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
                    self.print_log("GUI", "error", "Error during acquisition")
                    self.ready_event.set()
                    self._collecting = False
                if self._previous_collect_status is None:
                    if self._actual_collect_status == "busy":
                        self.print_log("HWR", "info", "Collection: Preparing ...")
                elif self._previous_collect_status == "busy":
                    if self._actual_collect_status == "collecting":
                        self.emit("collectStarted", (None, 1))
                    elif self._actual_collect_status == "ready":
                        self.ready_event.set()
                        self._collecting = False
                elif self._previous_collect_status == "collecting":
                    if self._actual_collect_status == "ready":
                        self.ready_event.set()
                        self._collecting = False
                    elif self._actual_collect_status == "aborting":
                        self.print_log("HWR", "info", "Collection: Aborting...")
                        self.ready_event.set()
                        self._collecting = False

    def collect_error_update(self, error_msg):
        """Collect error behaviour

        :param error_msg: error message
        :type error_msg: string
        """

        if self._collecting and len(error_msg) > 0:
            self._error_msg = error_msg
            self.print_log(
                "GUI", "error", "Collection: Error from detector server: %s" % error_msg
            )

    def collect_error_update(self, error_msg):
        """Collect error behaviour

        :param error_msg: error message
        :type error_msg: string
        """

        if self._collecting and len(error_msg) > 0:
            self._error_msg = error_msg
            self.print_log(
                "GUI", "error", "Collection: Error from detector server: %s" % error_msg
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
        warning_list = warning_str.split("\n")
        print warning_list
        self.print_log("GUI", "warning", warning_list[-2])

    def camera_error_update(self, error_list):
        print error_list

    def set_ff_apply(self, state):
        self.ff_apply = state

    def display_image(self, index):
        angle = self.osc_start + index * len(self.raw_image_arr) / 360.0
        if angle > 360:
            angle -= 360
        elif angle < 0:
            angle += 360

        self.graphics_omega_reference_item.set_phi_position(angle)
        self.current_image_index = index

        im = self.raw_image_arr[index].astype(float)
        ff = self.ff_image_arr[0].astype(float)

        if self.ff_apply:
           #im = cv.subtract(im, ff)
           #im = cv.divide(im - 136., 255. - 136.)  
           #im = cv.multiply(im, 255)
           im = np.divide(im, ff, out=np.zeros_like(im), where=ff!=0)
           im = 256 * ((im - im.min()) / (im.max() - im.min()))

        self.qimage = QtImport.QImage(
            im.astype(np.uint8), im.shape[1], im.shape[0], im.shape[1], QtImport.QImage.Format_Indexed8
        )
        self.graphics_camera_frame.setPixmap(self.qpixmap.fromImage(self.qimage))
        self.graphics_view.scene().update()
        self.emit("imageLoaded", index)

    def display_relative_image(self, relative_angle):
        self.play_images(0.04, relative_angle, False)

    def load_images(self, data_path, flat_field_path):
        gevent.spawn(self.load_images_task, data_path, flat_field_path)

    def load_images_task(self, data_path, flat_field_path):
        base_name_list = os.path.splitext(os.path.basename(data_path))
        prefix = base_name_list[0].split("_")[0][:-5]
        suffix = base_name_list[1][1:]

        os.chdir(os.path.dirname(data_path))
        imlist = sorted(
            [
                os.path.join(os.path.dirname(data_path), f)
                for f in os.listdir(os.path.dirname(data_path))
                if f.startswith(prefix)
            ]
        )

        self.print_log("GUI", "info", "Imaging: Reading images from disk...")

        self.raw_image_arr = []
        self.norm_min_max = [255, 0]

        for filename in imlist:
            self.raw_image_arr.append(cv.imread(filename, 0))
            #im = self.raw_image_arr[-1][400:-1200,400:-500]
            """
            if self.raw_image_arr[-1][50:].min() < self.norm_min_max[0]:
                self.norm_min_max[0] = self.raw_image_arr[-1][50:].min()
            if self.raw_image_arr[-1][50:].max() > self.norm_min_max[1]:
                self.norm_min_max[1] = self.raw_image_arr[-1][50:].max()
            """
        """
        global self.raw_image_arr 
        self.raw_image_arr = [0] * len(imlist)
        self.norm_min_max = [255, 0]

        cp_count = multiprocessing.cpu_count()
        pool = ThreadPool(cp_count)
        results = pool.map(append_image, imlist)

        pool.close()
        pool.join()
        """

        self.print_log("GUI", "info", "Imaging: Reading of images done.")
        """
        for index in range(len(self.raw_image_arr)):
            if self.raw_image_arr[index].min() < self.norm_min_max[0]:
                self.norm_min_max[0] = self.raw_image_arr[index].min()
            if self.raw_image_arr[index].min() > self.norm_min_max[1]:
                self.norm_min_max[1] = self.raw_image_arr[index].max()
        """
        
        self.print_log("GUI", "info", "Imaging: Reading of images done.")

        """
        self.print_log("GUI", "info", "Imaging: Normalizing raw images...")
        for index in range(len(self.raw_image_arr)):
            self.raw_image_arr[index] = \
               256. * (self.raw_image_arr[index] - self.norm_min_max[0]) / \
               (self.norm_min_max[1] - self.norm_min_max[0]).astype(np.uint8)
        self.print_log("GUI", "info", "Imaging: Normalization done")
        """
        #if not self.ff_apply:
        #    self.emit("imageInit", len(imlist))
        #    self.display_image(0)

        self.print_log(
            "HWR", "debug", "Imaging: Reading flat field images from disk..."
        )

        """
        base_name_list = os.path.splitext(os.path.basename(flat_field_path))
        prefix = base_name_list[0].split("_")[0][:-5]
        suffix = base_name_list[1][1:]

        os.chdir(os.path.dirname(flat_field_path))
        imlist = [
            os.path.join(os.path.dirname(flat_field_path), f)
            for f in os.listdir(os.path.dirname(flat_field_path))
            if f.startswith(prefix)
        ]
        imlist.sort()

        self.ff_image_arr = []
        for image in imlist:
            self.ff_image_arr.append(cv.imread(image, 0))
        self.print_log(
            "HWR", "debug", "Imaging: Reading flat field images from disk done"
        )
        """
        
        self.ff_image_arr = [cv.imread(flat_field_path, 0)]
        self.print_log(
            "HWR", "debug", "Imaging: Done reading flat field images from disk"
        )

        self.emit('imageInit', len(imlist))
        self.display_image(0)

    def play_images(self, exp_time=0.04, relative_index=None, repeat=True):
        self.image_polling = gevent.spawn(
            self.do_image_polling, exp_time, relative_index, repeat
        )

    def do_image_polling(self, exp_time=0.04, relative_index=1, repeat=False):
        self.repeat_image_play = repeat

        direction = 1 if relative_index > 0 else -1
        rotate_in_sec = 5

        step = int(len(self.raw_image_arr) / (rotate_in_sec / exp_time))
        index = 0

        while self.current_image_index < len(self.raw_image_arr):
            if index >= abs(relative_index):
                break

            self.display_image(self.current_image_index)
            self.current_image_index += direction * step
            if self.repeat_image_play and self.current_image_index >= len(
                self.raw_image_arr
            ):
                self.current_image_index -= len(self.raw_image_arr)
            gevent.sleep(exp_time)
            index += step

    def stop_image_play(self):
        self.image_polling.kill()

    def stop_collect(self):
        self.cmd_collect_abort()    

    def mouse_wheel_scrolled(self, delta):
        if self.raw_image_arr is None:
            return

        if delta > 0:
            self.current_image_index -= 1
            if self.current_image_index < 0:
                self.current_image_index = len(self.raw_image_arr) - 1
        else:
            self.current_image_index += 1
            if self.current_image_index == len(self.raw_image_arr):
                self.current_image_index = 0
        self.display_image(self.current_image_index)

    def start_centering(self):
        self.centering_started = 3


class GraphicsCameraFrame(QtImport.QGraphicsPixmapItem):
    def __init__(self, parent=None):
        super(GraphicsCameraFrame, self).__init__(parent)

    def mousePressEvent(self, event):
        pos = QtImport.QPointF(event.pos())
        self.scene().parent().mouseClickedSignal.emit(
            pos.x(), pos.y(), event.button() == QtImport.Qt.LeftButton
        )
        self.update()

    def mouseMoveEvent(self, event):
        pos = QtImport.QPointF(event.pos())
        self.scene().parent().mouseMovedSignal.emit(pos.x(), pos.y())
        self.update()

    # def mouseDoubleClickEvent(self, event):
    #    position = QtImport.QPointF(event.pos())
    #    self.scene().mouseDoubleClickedSignal.emit(position.x(), position.y())
    #    self.update()

    def mouseReleaseEvent(self, event):
        pos = QtImport.QPointF(event.pos())
        self.scene().parent().mouseReleasedSignal.emit(pos.x(), pos.y())
        self.update()


class GraphicsView(QtImport.QGraphicsView):
    mouseClickedSignal = QtImport.pyqtSignal(int, int, bool)
    mouseReleasedSignal = QtImport.pyqtSignal(int, int)
    mouseMovedSignal = QtImport.pyqtSignal(int, int)
    keyPressedSignal = QtImport.pyqtSignal(str)
    wheelSignal = QtImport.pyqtSignal(int)

    def __init__(self, parent=None):
        super(GraphicsView, self).__init__(parent)

        self.setScene(QtImport.QGraphicsScene(self))
        self.scene().clearSelection()
        self.setMouseTracking(True)
        self.setDragMode(QtImport.QGraphicsView.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(QtImport.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtImport.Qt.ScrollBarAlwaysOff)

    def wheelEvent(self, event):
        self.wheelSignal.emit(event.delta())
