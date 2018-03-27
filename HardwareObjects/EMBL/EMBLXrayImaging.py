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
import gevent
import logging

import numpy as np
from scipy import misc
from QtImport import *

from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLXrayImaging(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.image_list = None
        self.graphics_scene = None
        self.graphics_camera_frame = None
        self.image_polling = None
        self.repeat_image_play = None
        self.current_image_index = None

    def init(self):
        self.graphics_view = GraphicsView()
        self.graphics_camera_frame = GraphicsCameraFrame() 
        self.graphics_view.scene().addItem(self.graphics_camera_frame)

        self.graphics_view.wheelSignal.connect(\
             self.mouse_wheel_scrolled)

    def get_graphics_view(self):
        return self.graphics_view

    def set_repeate_image_play(self, value):
        self.repeat_image_play = value 

    def start_imaging(self, data_model):
        print data_model

    def display_image(self, index):
        self.current_image_index = index
        self.graphics_camera_frame.setPixmap(QPixmap(self.image_list[index][1]))
        self.emit("imageLoaded", index, self.image_list[index][0])

    def load_images(self, path):
        base_name_list = os.path.splitext(os.path.basename(path))
        prefix = base_name_list[0].split("_")[0]
        suffix = base_name_list[1][1:]
        dir_content = os.listdir(os.path.dirname(path))
        dir_content.sort()
        self.image_list = []

        for filename in dir_content:
            full_filename = os.path.join(os.path.dirname(path), filename)
            if filename.startswith(prefix) and \
               filename.endswith(suffix) and \
               os.path.isfile(full_filename):
                logging.getLogger("HWR").debug("Reading image %s" % full_filename)
                self.image_list.append((full_filename,
                                        QImage(full_filename)))
         
        self.emit('imageInit', len(self.image_list))
        if self.image_list:
            self.graphics_view.setFixedSize(self.image_list[0][1].width(),
                                            self.image_list[0][1].height())
            self.display_image(0)

    def play_images(self, fps, repeat):
        self.image_polling = gevent.spawn(self.do_image_polling,
                                          fps,
                                          repeat)

    def do_image_polling(self, exp_time, repeat):
        self.repeat_image_play = repeat

        image_index = 0
        while image_index < len(self.image_list):
            self.display_image(image_index)
            image_index += 1
            if self.repeat_image_play and \
               image_index == len(self.image_list):
                image_index = 0
            gevent.sleep(exp_time)
           
 
    def stop_image_play(self):
        self.image_polling.kill()

    def mouse_wheel_scrolled(self, delta):
        if delta > 0:
            self.current_image_index -= 1
            if self.current_image_index < 0:
                self.current_image_index = 0
                return
        else:
            self.current_image_index += 1
            if self.current_image_index == len(self.image_list):
                self.current_image_index = len(self.image_list) - 1
                return
        self.display_image(self.current_image_index) 

class GraphicsCameraFrame(QGraphicsPixmapItem):
    def __init__ (self, parent=None):
        super(GraphicsCameraFrame, self).__init__(parent)

    """
    def mousePressEvent(self, event):
        position = QPointF(event.pos())
        self.scene().mouseClickedSignal.emit(position.x(), position.y(),
             event.button() == Qt.LeftButton)
        self.update()

    def mouseDoubleClickEvent(self, event):
        position = QPointF(event.pos())
        self.scene().mouseDoubleClickedSignal.emit(position.x(), position.y())
        self.update()

    def mouseReleaseEvent(self, event):
        position = QPointF(event.pos())
        self.scene().mouseReleasedSignal.emit(position.x(), position.y())
        self.update()
    """

class GraphicsView(QGraphicsView):
    mouseMovedSignal = pyqtSignal(int, int)
    keyPressedSignal = pyqtSignal(str)
    wheelSignal = pyqtSignal(int)

    def __init__ (self, parent=None):
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
