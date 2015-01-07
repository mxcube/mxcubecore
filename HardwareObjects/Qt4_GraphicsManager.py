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

    def get_snapshot(self, qub_objects):
        """
        Get a snapshot of the video stream and overlay the objects
        in qub_objects.

        :param qub_objects: The QCanvas object to add on top of the video.
        :type qub_objects: QCanvas

        :returns: The snapshot
        :rtype: QImage
        """
        qimg = None

        try:
            matrix = self._drawing.matrix()
        except AttributeError:
            qimg = None
        else:
            zoom = 1
            if matrix is not None:
                zoom = matrix.m11()

            img = self._drawing.getPPP()
            qimg = self.get_qimage(img, qub_objects, zoom)

        return qimg

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

class CanvasGrid(Shape) :
    def __init__(self, canvas, cell_width = 1, cell_height = 1,
                 beam_width = 1, beam_height = 1) :
        Shape.__init__(self, canvas)
        self.__painter = None

        # Grid dimension
        self.__num_cells = 0

        # Total width and height in px
        self.__width = None
        self.__height = None
        self.__cell_width = cell_width
        self.__cell_height = cell_height

        # Grid dimensions
        self.__num_colls = 0
        self.__num_rows = 0

        # Scale px/mm 
        self.__x_pixel_size = 1
        self.__y_pixel_size = 1

        # Beam position and dimension on the format:
        # (x pos in px, y pos in px, width in mm, height in mm)
        self.__beam_pos = (0, 0, beam_width, beam_height)
        self.__beam_width = beam_width * self.__x_pixel_size
        self.__beam_height = beam_height * self.__y_pixel_size

        # (score, (r,g,b))
        self.__grid_data = {}
        self.__has_data = False

        self.__beam_shape = None
        self.__highlighted = False
        self.__label = "Grid n"

    def drawShape(self, painter):
        """
        Overloads the QCanvasRectangle drawShape. Performs the drawing of the
        grid.

        :param painter: The QPainter object to use when drawing.
        :type painter: QPainter
        """
        self.__painter = painter
        rect = self.rect()

        self.__num_cells = 0
        num_rows = (rect.bottom() - rect.top()) / self.__cell_height
        num_colls = (rect.right() - rect.left()) / self.__cell_width

        if self.__highlighted:
            painter.setPen(qt.QPen(qt.Qt.green, 0, qt.Qt.SolidLine))
        else:
            painter.setPen(qt.QPen(qt.Qt.black, 0, qt.Qt.DotLine))

        for i in range(0, num_rows + 1):
            offset =  i*self.__cell_height
            self.__height = offset
            painter.drawLine(rect.left(), rect.top() + offset,
                             rect.right(), rect.top() + offset)

        for i in range(0, num_colls + 1):
            offset =  i*self.__cell_width
            self.__width = offset
            painter.drawLine(rect.left() + offset, rect.top(),
                             rect.left() + offset, rect.bottom())

        for i in range(0, num_rows):
            row_offset = i*self.__cell_height
            for k in range(0, num_colls):
                coll_offset = k*self.__cell_width
                self.__num_cells += 1
                if not self.__has_data:
                    if self.__num_cells % 2:
                        self.__grid_data[self.__num_cells] = (self.__num_cells, (0, 0, 150))
                    else:
                        self.__grid_data[self.__num_cells] = (self.__num_cells, (0, 0, 150))

                painter.setPen(qt.QPen(qt.Qt.black, 0, qt.Qt.SolidLine))
                    
                color = self.__grid_data[self.__num_cells][1]

                #if self.__highlighted:
                painter.setBrush(qt.QBrush(qt.QColor(*color), qt.Qt.Dense4Pattern))
                #else:
                #    painter.setBrush(qt.QBrush(qt.QColor(*color), qt.Qt.Dense6Pattern))

                beam_hspacing = (self.__cell_width - self.__beam_width) / 2
                beam_vspacing = (self.__cell_height - self.__beam_height) /2
                
                painter.drawEllipse(rect.left() + coll_offset + beam_hspacing,
                                    rect.top() + row_offset + beam_vspacing,
                                    self.__beam_width, self.__beam_height)

                painter.setPen(qt.QPen(qt.Qt.black, 1, qt.Qt.SolidLine))
                tr = qt.QRect(rect.left() + coll_offset, rect.top() + row_offset,
                              self.__cell_width, self.__cell_height)
                
                score = self.__grid_data[self.__num_cells][0]

                if score:
                    painter.drawText(tr, qt.Qt.AlignCenter, str(score))

            if self.__label and self.__highlighted:
                #painter.setPen(qt.QPen(qt.Qt.green, 0, qt.Qt.SolidLine))
                painter.drawText(rect.right() + 2, rect.top() - 5 , self.__label)

        self.__num_rows = num_rows
        self.__num_colls = num_colls

    def reshape(self):
        """
        Reshapes the grid, mostly used after it has been drawn or resized to
        achive a "snap to" like effect.
        """
        self.__width = self.__cell_width * self.__num_colls
        self.__height = self.__cell_height * self.__num_rows
        self.setSize(self.__width + 1, self.__height + 1)

    def reposition(self, scale_factor_x = None, scale_factor_y = None):
        """
        Re-positions the shape, used when the scale factor changes (zooming)

        :param scale_factor_x: The new x scale factor
        :type scale_factor_x: float

        :param scale_factor_y: The new y scale factor
        :type scale_factor_y: float
        """
        if scale_factor_x:
            beam_dx = self.x() - self.__beam_pos[0]
            dx =  beam_dx * scale_factor_x - beam_dx
            self.moveBy(dx, 0)

        if scale_factor_y:
            beam_dy = self.y() - self.__beam_pos[1]
            dy = beam_dy * scale_factor_y - beam_dy
            self.moveBy(0, dy)

    def highlight(self, state):
        """
        :param state: true if the grid is to be highlighted false otherwise
        :type state: boolean
        """
        self.__highlighted = state

    def set_label(self, label):
        """
        :param label: The label of the grid (displayed in the top right corner)
        :type label: str
        """
        self.__label = label

    def get_nummer_of_cells(self):
        """
        :returns: The total number of cells in the grid
        :rtype: int
        """
        return self.__num_cells

    def set_data(self, data):
        """
        :param data: The result data to use when displaying the grid
        :type data: dict

        The data dict should have the following format:

        {1: (cell_label, (r,g,b)),
         .
         .
         .
         index_n-1: (cell_label, (r,g,b)),
         index_n: (cell_label, (r,g,b)),
        }

        and contain as many elements as the grid contains cells. That is
        index_n = self.get_nummer_of_cells()

        cell_label is the label displayed in the cell center and the rgb triplet
        the background color of the cell.
        """
        self.__has_data = True
        self.__grid_data = data

    def set_x_pixel_size(self, x_size):
        """
        Sets the x-axis pixel per mm scale value.
        
        :param x_size: x-axis pixels per mm
        :type x_size: float
        """
        self.__x_pixel_size = x_size
        self.__recalculate_beam_dim()
        
    def set_y_pixel_size(self, y_size):
        """
        Sets the y-axis pixel per mm scale value.
        
        :param y_size: y-axis pixels per mm
        :type y_size: float
        """
        self.__y_pixel_size = y_size
        self.__recalculate_beam_dim()
        
    def set_beam_position(self, x, y, w=0, h=0):
        """
        Set beam position and dimension

        :param x: x position in pixels
        :type x: int

        :param y: y position in pixels
        :type y: int

        :param w: width in mm
        :type w: float

        :param h: height in mm
        :type h: float
        """
        self.__beam_pos = (x, y, w, h)
        if w and h:
            self.__recalculate_beam_dim()

    def _get_grid(self, key):
        """
        :returns: A dictionary with grid dimensions and position.
        :rtype: dict

        The dictionary has the following format:

        grid = {'id': 'grid-n',
                'dx_mm': total width in mm,
                'dy_mm': total height in mm,
                'steps_x': number of colls,
                'steps_y': number of rows,
                'x1': top left cell center x coord,
                'y1': top left cell center y coord,
                'beam_width': beam width in mm
                'beam_height': beam height in mm
                'angle': 0}
        """
        rect = self.rect()

        num_rows = (rect.bottom() - rect.top()) / self.__cell_height
        num_colls = (rect.right() - rect.left()) / self.__cell_width
        
        x = rect.left()
        y = rect.top()

        cell_width = float(self.__cell_width / self.__x_pixel_size)
        cell_height = float(self.__cell_height / self.__y_pixel_size)
        
        first_cell_center_x = ((x + (self.__cell_width / 2)) - self.__beam_pos[0]) / self.__x_pixel_size
        first_cell_center_y = ((y + (self.__cell_height / 2)) - self.__beam_pos[1]) / self.__y_pixel_size

        grid = {'id': key,
                'dx_mm': cell_width * (num_colls - 1),
                'dy_mm': cell_height * (num_rows - 1),
                'steps_x': num_colls,
                'steps_y': num_rows,
                'x1': first_cell_center_x,
                'y1': first_cell_center_y,
                'beam_width': self.__beam_width / self.__x_pixel_size,
                'beam_height': self.__beam_height / self.__y_pixel_size,
                'angle': 0}

        return grid

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
        self.centring_state = None

    def set_centring_state(self, state):
        self.centring_state = state

    def mousePressEvent(self, event):
        if self.centring_state:
            position = QtCore.QPointF(event.scenePos())
            print "pressed here: " + str(position.x()) + ", " + str(position.y())
        self.update()

    def mouseMoveEvent(self, event):
        if self.centring_state:
            position = QtCore.QPointF(event.scenePos())
            print "moved here: " + str(position.x()) + ", " + str(position.y())
        self.update()

    def mouseReleaseEvent(self, event):
        if centring_state:
            position = QtCore.QPointF(event.scenePos())
            print "released here: " + str(position.x()) + ", " + str(position.y())
        self.update()
