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

from __future__ import print_function
import os
import time
import gevent
import dxchange
import logging
import multiprocessing

import Image
from PIL.ImageQt import ImageQt

from cStringIO import StringIO
import numpy as np

# from scipy import misc
from skimage.measure import compare_ssim as ssim
from QtImport import *
from joblib import Parallel, delayed

from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"

"""
Dependecies:
 * dxchange: https://github.com/data-exchange/dxchange.git
 * tifffile: via pip
"""


class EMBLXrayImaging(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.display_image_list = []
        self.raw_image_arr = None
        self.ff_image_arr = None
        self.ff_corrected_image_arr = None
        self.image = None
        self.qimage = None
        self.qpixmap = None

        self.graphics_scene = None
        self.graphics_camera_frame = None
        self.image_polling = None
        self.repeat_image_play = None
        self.current_image_index = None
        self.mouse_hold = False
        self.mouse_coord = [0, 0]

    def init(self):
        self.graphics_view = GraphicsView()
        self.graphics_camera_frame = GraphicsCameraFrame()
        self.graphics_view.scene().addItem(self.graphics_camera_frame)

        self.graphics_view.wheelSignal.connect(self.mouse_wheel_scrolled)
        self.graphics_view.mouseClickedSignal.connect(self.mouse_clicked)
        self.graphics_view.mouseReleasedSignal.connect(self.mouse_released)
        self.graphics_view.mouseMovedSignal.connect(self.mouse_moved)

        # self.qimage = ImageQt()
        self.qpixmap = QPixmap()

        self.chan_frame = self.getChannelObject("chanFrame")
        if self.chan_frame is not None:
            self.chan_frame.connectSignal("update", self.frame_changed)

    def get_image_dimensions(self):
        return 2048, 2048

    def getHeight(self):
        return 2048

    def getWidth(self):
        return 2048

    def start_camera(self):
        pass

    def frame_changed(self, data):
        jpgdata = StringIO(data)
        # im = Image.open(jpgdata)
        # self.qimage = ImageQt(im)
        if self.qimage is None:
            self.qimage = ImageQt(im)
        else:
            self.qimage.loadFromData(Image.open(jpgdata))
        self.qpixmap.fromImage(self.qimage, Qt.MonoOnly)
        self.emit("imageReceived", self.qpixmap)

    def mouse_clicked(self, pos_x, pos_y, left_click):
        self.mouse_hold = True
        self.mouse_coord = [pos_x, pos_y]

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
                index = len(self.display_image_list) - 1
            elif index >= len(self.display_image_list):
                index = 0
            self.mouse_coord[0] = pos_x
            self.display_image(index)

    def get_graphics_view(self):
        return self.graphics_view

    def set_repeate_image_play(self, value):
        self.repeat_image_play = value

    def start_imaging(self, data_model):
        print(data_model)

    def set_graphics_scene_size(self, size, fixed):
        pass

    def display_image(self, index):
        self.current_image_index = index

        # x = self.display_image_list[index]
        # h,w = x.shape
        # COLORTABLE = [~((i + (i<<8) + (i<<16))) for i in range(255,-1,-1)]
        # image = QImage(x.data, w, h, QImage.Format_ARGB32)

        # im_np = np.transpose(self.display_image_list[index], (1,0,2))
        # qimage = QImage(im_np,
        #                im_np.shape[1],
        #                im_np.shape[0],
        #                QImage.Format_RGB888)
        self.graphics_camera_frame.setPixmap(self.display_image_list[index])
        # self.emit("imageLoaded", index, self.display_image_list[index][0])

    def load_images(self, data_path, flat_field_path):
        fileformat = "ppm", "PPM", "tiff", "TIFF", "tif", "TIF", "png", "PNG", "raw"
        cut = False
        self.display_image_list = []

        base_name_list = os.path.splitext(os.path.basename(data_path))
        prefix = base_name_list[0].split("_")[0]
        suffix = base_name_list[1][1:]

        os.chdir(os.path.dirname(data_path))
        imfiles = os.listdir(os.path.dirname(data_path))
        imlist = sorted(
            [filename for filename in imfiles if filename.endswith(fileformat)]
        )
        self.emit("imageInit", len(imlist))

        logging.getLogger("HWR").debug("Start")
        for image in imlist:
            self.display_image_list.append(QPixmap(image))
        logging.getLogger("HWR").debug("end")

        if self.display_image_list is not None:
            self.graphics_view.setFixedSize(1024, 1024)
            # self.graphics_view.setFixedSize(self.display_image_list.shape[1],
            #                                self.display_image_list.shape[0])
            self.display_image(0)

        # gevent.spawn_later(1, self.convert_images, data_path, flat_field_path)

    def convert_images(self, raw_data_path, flat_field_path):
        cut = False
        fileformat = "ppm", "PPM", "tiff", "TIFF", "tif", "TIF", "png", "PNG", "raw"
        a, b, c, d = 0, 0, 100, 100

        os.chdir(os.path.dirname(raw_data_path))
        imfiles = os.listdir(os.path.dirname(raw_data_path))
        imlist = sorted(
            [filename for filename in imfiles if filename.endswith(fileformat)]
        )
        if cut:
            image_arr = dxchange.reader.read_tiff_stack(
                imlist[0], range(len(imlist)), slc=((b, d, 1), (a, c, 1))
            ).astype("float32")
        else:
            image_arr = dxchange.reader.read_tiff_stack(
                imlist[0], range(len(imlist))
            ).astype("float32")
        self.raw_image_arr = image_arr.transpose(1, 2, 0)

        os.chdir(os.path.dirname(flat_field_path))
        flfiles = os.listdir(os.path.dirname(flat_field_path))
        fllist = sorted(
            [filename for filename in flfiles if filename.endswith(fileformat)]
        )
        if cut:
            ff_arr = dxchange.reader.read_tiff_stack(
                fllist[0], range(len(fllist)), slc=((b, d, 1), (a, c, 1))
            ).astype("float32")
        else:
            ff_arr = dxchange.reader.read_tiff_stack(
                fllist[0], range(len(fllist))
            ).astype("float32")
        self.ff_image_arr = ff_arr.transpose(1, 2, 0)

        num_cores = multiprocessing.cpu_count()
        filtered = Parallel(n_jobs=num_cores)(
            delayed(self.find_flat)(self.raw_image_arr[:, :, i], self.ff_image_arr)
            for i in range(self.raw_image_arr.shape[2])
        )
        self.ff_corrected_image_arr = numpy.transpose(
            numpy.asarray(filtered), (1, 2, 0)
        )

    def find_flat(self, image, flat):
        best = [0, 0]
        for f in range(flat.shape[2]):
            if cut:
                rms = ssim(image, flat[:, :, f])
            else:
                rms = ssim(image[a:c, b:d], flat[a:c, b:d, f])

            if rms > best[0]:
                best = [rms, f]

        arr = image / flat[:, :, best[1]]
        return arr

    def play_images(self, fps, repeat):
        self.image_polling = gevent.spawn(self.do_image_polling, fps, repeat)

    def do_image_polling(self, exp_time, repeat):
        self.repeat_image_play = repeat

        image_index = 0
        while image_index < len(self.display_image_list):
            self.display_image(image_index)
            image_index += 1
            if self.repeat_image_play and image_index == len(self.display_image_list):
                image_index = 0
            gevent.sleep(exp_time)

    def stop_image_play(self):
        self.image_polling.kill()

    def mouse_wheel_scrolled(self, delta):
        if self.display_image_list is None:
            return

        if delta > 0:
            self.current_image_index -= 1
            if self.current_image_index < 0:
                self.current_image_index = len(self.display_image_list) - 1
        else:
            self.current_image_index += 1
            if self.current_image_index == len(self.display_image_list):
                self.current_image_index = 0
        self.display_image(self.current_image_index)


class GraphicsCameraFrame(QGraphicsPixmapItem):
    def __init__(self, parent=None):
        super(GraphicsCameraFrame, self).__init__(parent)

    def mousePressEvent(self, event):
        pos = QPointF(event.pos())
        self.scene().parent().mouseClickedSignal.emit(
            pos.x(), pos.y(), event.button() == Qt.LeftButton
        )
        self.update()

    def mouseMoveEvent(self, event):
        pos = QPointF(event.pos())
        self.scene().parent().mouseMovedSignal.emit(pos.x(), pos.y())
        self.update()

    # def mouseDoubleClickEvent(self, event):
    #    position = QPointF(event.pos())
    #    self.scene().mouseDoubleClickedSignal.emit(position.x(), position.y())
    #    self.update()

    def mouseReleaseEvent(self, event):
        pos = QPointF(event.pos())
        self.scene().parent().mouseReleasedSignal.emit(pos.x(), pos.y())
        self.update()


class GraphicsView(QGraphicsView):
    mouseClickedSignal = pyqtSignal(int, int, bool)
    mouseReleasedSignal = pyqtSignal(int, int)
    mouseMovedSignal = pyqtSignal(int, int)
    keyPressedSignal = pyqtSignal(str)
    wheelSignal = pyqtSignal(int)

    def __init__(self, parent=None):
        super(GraphicsView, self).__init__(parent)

        self.graphics_scene = QGraphicsScene(self)
        self.setScene(self.graphics_scene)
        self.graphics_scene.clearSelection()
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def wheelEvent(self, event):
        self.wheelSignal.emit(event.delta())
