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
#   You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
Contains the classes

* ShapeHistory
* DrawingEvent
* Shape
* Point
* Line
* CanvasGrid

ShapeHistory keeps track of the current shapes the user has created. The
shapes handled are any that inherits the Shape base class. There are currently
two shapes implemented Point and Line.

Point is the graphical representation of a centred position. A point can be
stored and managed by the ShapeHistory. the Line object represents a line
between two Point objects.

"""

import logging
import traceback
import queue_model_objects_v1 as queue_model_objects
import types

from PyQt4 import QtCore
from PyQt4 import QtGui

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareRepository import dispatcher

SELECTED_COLOR = QtCore.Qt.green
NORMAL_COLOR = QtCore.Qt.yellow


class Qt4_GraphicsManager(HardwareObject):
    """
    Keeps track of the current shapes the user has created. The
    shapes handled are any that inherits the Shape base class.
    """
    def __init__(self, name):
        HardwareObject.__init__(self, name)
     
        self.pixels_per_mm = [0, 0]
        self.beam_size = [0, 0]
        self.beam_position = [0, 0]
        self.beam_shape = None
        self.graphics_scene_width = None
        self.graphics_scene_height = None
         
        # Graphics objects
        self.graphics_beam_item = GraphicsObjectBeam(self)
        self.graphics_scale_item = GraphicsObjectScale(self)
        self.graphics_omega_reference_item = GraphicsObjectOmegaReference(self)
        self.graphics_centring_lines_item = GraphicsObjectCentringLines(self)

        self.beam_info_dict = {}
        self.omega_axis_info_dict = {}
        self.shapes_dict = {}
        self.selected_shapes = {}

    def set_graphics_scene_size(self, size):
        self.graphics_scene_size = size
        self.graphics_scale_item.set_position(10, self.graphics_scene_size[1] - 10)

    def get_graphics_beam_item(self):
        return self.graphics_beam_item

    def get_scale_item(self):
        return self.graphics_scale_item

    def get_omega_reference_item(self):
        return self.graphics_omega_reference_item

    def set_centring_lines_enable(self, is_enabled):
        print "set_centring_lines_enable... ", is_enabled         
        if is_enabled:
            print self.graphics_centring_lines_item.parent

    def get_shapes(self):
        """
        :returns: All the shapes currently handled.
        """
        return self.shapes.values()

    def get_points(self):
        """
        :returns: All points currently handled
        """
        current_points = []

        for shape in self.get_shapes():
            if isinstance(shape, Point):
                current_points.append(shape)

        return current_points
        
    def add_shape(self, shape):
        """
        Adds the shape <shape> to the list of handled objects.

        :param shape: Shape to add.
        :type shape: Shape object.

        """
        self.shapes[shape] = shape

        self.get_drawing_event_handler().de_select_all()
        self.get_drawing_event_handler().set_selected(shape, True, call_cb = True)

    def _delete_shape(self, shape):
        shape.unhighlight()

        if shape in self.selected_shapes:
            del self.selected_shapes[shape]

            if callable(self._drawing_event.selection_cb):
                self._drawing_event.selection_cb(self.selected_shapes.values())

        if shape is self._drawing_event.current_shape:
            self._drawing_event.current_shape = None

        if callable(self._drawing_event.deletion_cb):
            self._drawing_event.deletion_cb(shape)

    def delete_shape(self, shape):
        """
        Removes the shape <shape> from the list of handled shapes.

        :param shape: The shape to remove
        :type shape: Shape object.
        """
        related_points = []

        #If a point remove related line first
        if isinstance(shape, Point):
            for s in self.get_shapes():
                if isinstance(s, Line):
                    for s_qub_obj in s.get_qub_objects():
                        if  s_qub_obj in shape.get_qub_objects():
                            self._delete_shape(s)
                            related_points.append(s)
                            break

        self._delete_shape(shape)
        del self.shapes[shape]

        # Delete the related shapes after self._delete_shapes so that
        # related object still exists when calling delete call back.
        for point in related_points:
            del self.shapes[point]

    def move_shape(self, shape, new_positions):
        """
        Moves the shape <shape> to the position <new_position>

        :param shape: The shape to move
        :type shape: Shape

        :param new_position: A tuple (X, Y)
        :type new_position: <int, int>
        """
        self.shapes[shape].move(new_positions)

    def clear_all(self):
        """
        Clear the shape history, remove all contents.
        """
        for shape in self.shapes:
            self._delete_shape(shape)

        self.shapes.clear()

    def de_select_all(self):
        self._drawing_event.de_select_all()

    def select_shape_with_cpos(self, cpos):
        self._drawing_event.de_select_all()

        for shape in self.get_shapes():
            if isinstance(shape, Point):
                if shape.get_centred_positions()[0] == cpos:
                    self._drawing_event.set_selected(shape, True, call_cb = False)

    def get_grid(self):
        """
        Returns the current grid object.
        """
        grid_dict = dict()
        dispatcher.send("grid", self, grid_dict)
        return grid_dict

    def set_grid_data(self, key, result_data):
        dispatcher.send("set_grid_data", self, key, result_data)

    def select_shape(self, shape):
        """
        Select the shape <shape> (programmatically).

        :param shape: The shape to select.
        :type shape: Shape
        """
        self._drawing_event.set_selected(shape, True, call_cb = False)

    def de_select_shape(self, shape):
        """
        De-select the shape <shape> (programmatically).

        :param shape: The shape to de-select.
        :type shape: Shape
        """
        if self.is_selected(shape):
            self._drawing_event.set_selected(shape, False, call_cb = False)

    def is_selected(self, shape):
        return shape in self.selected_shapes

    def get_selected_shapes(self):
        return self.selected_shapes.itervalues()

    def update_beam_position(self, beam_position):
        if beam_position is not None:
            self.graphics_beam_item.set_position(beam_position[0],
                                                 beam_position[1])

    def update_pixels_per_mm(self, pixels_per_mm):
        if pixels_per_mm is not None:
            self.pixels_per_mm = pixels_per_mm
            self.graphics_beam_item.set_size(self.beam_size[0] * self.pixels_per_mm[0],
                                             self.beam_size[1] * self.pixels_per_mm[1])

    def update_beam_info(self, beam_info):
        if beam_info is not None:
            self.beam_size[0] = beam_info.get("size_x")
            self.beam_size[1] = beam_info.get("size_y")
            self.beam_shape = beam_info.get("shape")
            self.graphics_beam_item.set_shape(self.beam_shape == "rectangular")
            if self.pixels_per_mm is not None:
                self.graphics_beam_item.set_size(self.beam_size[0] * self.pixels_per_mm[0],
                                                 self.beam_size[1] * self.pixels_per_mm[1])

    def update_omega_reference(self, omega_reference):
        self.graphics_omega_reference_item.set_reference(omega_reference)  


class Shape(QtGui.QGraphicsItem):
    """
    Base class for shapes.
    """
    def __init__(self, parent, position_x = 0, position_y = 0):
        QtGui.QGraphicsItem.__init__(self)
        rect = QtCore.QRectF(0, 0, 0, 0)
        self.rect = rect
        self.style = QtCore.Qt.SolidLine
        self.setMatrix = QtGui.QMatrix()
        self.setPos(position_x, position_y)

    def boundingRect(self):
        return self.rect.adjusted(-2, -2, 2, 2)

    def set_size(self, width, height):
        self.rect.setWidth(width)
        self.rect.setHeight(height)

    def set_position(self, position_x, position_y):
        if (position_x is not None and
            position_y is not None):
            self.setPos(position_x, position_y)

    def set_visible(self, is_visible):
        if is_visible: 
            self.show()
        else:
            self.hide()

    def boundingRect(self):
        return self.rect.adjusted(-2, -2, 2, 2)

class GraphicsObjectBeam(Shape):
    """
    Descrip. : 
    """
    def __init__(self, parent, position_x = 0, position_y= 0):
        Shape.__init__(self, parent, position_x = 0, position_y= 0)
        self.shape_is_rectangle = True

    def paint(self, painter, option, widget):
        pen = QtGui.QPen(self.style)
        pen.setWidth(1)
        if option.state & QtGui.QStyle.State_Selected:
            pen.setColor(QtCore.Qt.red)
        else:
            pen.setColor(QtCore.Qt.blue)
        painter.setPen(pen)
        if self.shape_is_rectangle:
            painter.drawRect(self.rect)
        else:
            painter.drawEllipse(self.rect)
        pen.setColor(QtCore.Qt.red) 
        painter.setPen(pen)
        painter.drawLine(int(self.rect.width() / 2) - 15, int(self.rect.height() / 2),
                         int(self.rect.width() / 2) + 15, int(self.rect.height() / 2))
        painter.drawLine(int(self.rect.width() / 2), int(self.rect.height() / 2) - 15, 
                         int(self.rect.width() / 2), int(self.rect.height() / 2) + 15)  

    def set_shape(self, is_rectangle):
        self.shape_is_rectangle = is_rectangle      

class GraphicsObjectScale(Shape):
    """
    Descrip. : 
    """
    def __init__(self, parent, position_x = 0, position_y= 0):
        Shape.__init__(self, parent, position_x = 0, position_y= 0)

    def paint(self, painter, option, widget):
        pen = QtGui.QPen(self.style)
        pen.setWidth(3)
        pen.setColor(QtCore.Qt.green)
        painter.setPen(pen)
        painter.drawLine(0, 0, 150, 0)
        painter.drawLine(0, 0, 0, -50)

class GraphicsObjectOmegaReference(Shape):
    """
    Descrip. : 
    """
    def __init__(self, parent, position_x = 0, position_y= 0):
        Shape.__init__(self, parent, position_x = 0, position_y= 0)
        self.parent = parent
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0

    def paint(self, painter, option, widget):
        pen = QtGui.QPen(self.style)
        pen.setWidth(1)
        pen.setColor(QtCore.Qt.white)
        painter.setPen(pen)
        painter.drawLine(self.start_x, self.start_y, self.end_x, self.end_y)

    def set_reference(self, omega_reference):
        line_length = self.parent.graphics_scene_size
        if omega_reference[0] is not None:
            #Omega reference is a vertical axis
            self.start_x = omega_reference[0]
            self.end_x = omega_reference[0]
            self.start_y = 0
            self.end_y = line_length[1]
        else:
            self.start_x = 0
            self.end_x = line_length[0]
            self.start_y = omega_reference[1]
            self.end_y = omega_reference[1]

class GraphicsObjectCentringLines(Shape):
    """
    Descrip. : 
    """
    def __init__(self, parent, position_x = 0, position_y= 0):
        Shape.__init__(self, parent, position_x = 0, position_y= 0)
        self.parent = parent

    def paint(self, painter, option, widget):
        pen = QtGui.QPen(self.style)
        pen.setWidth(1)
        pen.setColor(QtCore.Qt.white)
        painter.setPen(pen)

class GraphicsObjectCentredPoint(Shape):
    """
    Descrip. : Centred point class.
    Args.    : parent, centred position (motors position dict, 
               full_centring (True if 3click centring), initial position)
    """
    def __init__(self, parent, centred_position = None, full_centring = True,
                 position_x = 0, position_y = 0):
        Shape.__init__(self)

        self.full_centring = full_centring

        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable)

        if centred_position is None:
            self.centred_position = queue_model_objects.CentredPosition()
            self.centred_position.centring_method = False
        else:
            self.centred_position = centred_position
        self.set_size(20, 20)

    def paint(self, painter, option, widget):
        pen = QtGui.QPen(self.style)
        pen.setWidth(3)
        if option.state & QtGui.QStyle.State_Selected:
            pen.setColor(QtCore.Qt.green)
        else:
            pen.setColor(QtCore.Qt.yellow)
        painter.setPen(pen)
        painter.drawEllipse(self.rect)


    def __recalculate_beam_dim(self):
        """
        Calculates the beam widht and height when the pixel/mm scale changes
        """
        beam_height_mm = self.__beam_pos[3]
        beam_width_mm = self.__beam_pos[2]
        self.__cell_height = int(self.__cell_height_mm * self.__y_pixel_size)
        self.__beam_height = int(beam_height_mm * self.__y_pixel_size)
        self.__cell_width = int(self.__cell_width_mm * self.__x_pixel_size)
        self.__beam_width = int(beam_width_mm * self.__x_pixel_size)
        self.reshape()

    def set_cell_width(self, cell_width_mm):
        self.__cell_width_mm = cell_width_mm
        self.__cell_width = int(self.__cell_width_mm * self.__x_pixel_size)
        self.reshape()

    def set_cell_height(self, cell_height_mm):
        self.__cell_height_mm = cell_height_mm
        self.__cell_height = int(self.__cell_height_mm * self.__y_pixel_size)
        self.reshape()

class GraphicsScene(QtGui.QGraphicsScene):
    def __init__ (self, parent=None):
        super(GraphicsScene, self).__init__ (parent)
        self.centring_state = True

    def set_centring_state(self, state):
        self.centring_state = state

    def mousePressEvent(self, event):
        if self.centring_state:
            position = QtCore.QPointF(event.scenePos())
            print "pressed here: " + str(position.x()) + ", " + str(position.y())
        self.update()

    def mouseMoveEvent(self, event):
        print self.mouseGrabberItem()
        if self.centring_state:
            position = QtCore.QPointF(event.scenePos())
            print "moved here: " + str(position.x()) + ", " + str(position.y())
        self.update()

    def mouseReleaseEvent(self, event):
        if self.centring_state:
            position = QtCore.QPointF(event.scenePos())
            print "released here: " + str(position.x()) + ", " + str(position.y())
        self.update()
