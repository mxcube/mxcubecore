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

DrawingEvent is an extension of Qub and handles mouse and keyboard events for
the Qub canvas. It handles selection and some manipulation of the Shape objects.
"""

import logging
import qtcanvas
import qt
import traceback
from HardwareRepository.HardwareObjects import queue_model_objects
import types

from qt import Qt

from Qub.Objects.QubEventMgr import QubEventMgr
from Qub.Objects.QubDrawingEvent import QubDrawingEvent
from Qub.Objects.QubDrawingManager import QubLineDrawingMgr
from Qub.Objects.QubDrawingManager import QubPointDrawingMgr
from Qub.Objects.QubDrawingManager import QubAddDrawing
from Qub.Objects.QubDrawingCanvasTools import QubCanvasTarget

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.dispatcher import dispatcher

from HardwareRepository import HardwareRepository
beamline_object = HardwareRepository.get_beamline()

SELECTED_COLOR = qt.Qt.green
NORMAL_COLOR = qt.Qt.yellow


class ShapeHistory(HardwareObject):
    """
    Keeps track of the current shapes the user has created. The
    shapes handled are any that inherits the Shape base class.
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._drawing = None
        self._drawing_event = DrawingEvent(self)
        self.shapes = {}
        self.selected_shapes = {}
        self.point_index = 0

    def set_drawing(self, drawing):
        """
        Sets the drawing the Shape objects that are managed are drawn on.

        :param drawing: The drawing that the shapes are drawn on.
        :type drawing: QubDrawing (used by Qub)

        :returns: None
        """
        if self._drawing:
            logging.getLogger("HWR").info(
                "Setting previous drawing:" + str(self._drawing) + " to " + str(drawing)
            )

        self._drawing = drawing
        self._drawing.addDrawingEvent(self._drawing_event)

    def get_drawing(self):
        """
        :returns: Returns the drawing of the shapes.
        :rtype: QubDrawing
        """
        return self._drawing

    def get_drawing_event_handler(self):
        """
        :returns: The event handler of the drawing.
        :rtype: QubDrawingEvent
        """
        return self._drawing_event

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

    def get_qimage(self, image, canvas, zoom=1):
        """
        Gets the QImage from a parent widget.

        :param image: The QWidget that contains the image to extract
        :type image: QWidget

        :param canvas: The QCanvas obejct to add as overlay
        :type canvas: QCanvas

        :param zoom: Zoom level
        :type zoom: int.

        :returns: The QImage contained in the parent widget.
        :rtype: QImage
        """
        if canvas is not None and image is not None:
            device = qt.QPixmap(image)
            painter = qt.QPainter(device)
            zoom = 1.0 / zoom
            painter.setWorldMatrix(qt.QWMatrix(zoom, 0, 0, zoom, 0, 0))

            if isinstance(canvas, list):
                itemsList = canvas
            else:
                itemsList = canvas.allItems()

            for item in itemsList:
                if item.isVisible():
                    if hasattr(item, "setScrollView"):  # remove standalone items
                        continue

                    item.draw(painter)

            painter.end()
            img = device.convertToImage()
        else:
            img = image

        return img

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
        if isinstance(shape, Point):
            shape.set_index(self.get_available_point_index())

        self.get_drawing_event_handler().de_select_all()
        self.get_drawing_event_handler().set_selected(shape, True, call_cb=True)

    def get_available_point_index(self):
        self.point_index += 1
        return self.point_index

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

        # If a point remove related line first
        if isinstance(shape, Point):
            for s in self.get_shapes():
                if isinstance(s, Line):
                    for s_qub_obj in s.get_qub_objects():
                        if s_qub_obj in shape.get_qub_objects():
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
        self.point_index = 0

    def de_select_all(self):
        self._drawing_event.de_select_all()

    def select_shape_with_cpos(self, cpos):
        self._drawing_event.de_select_all()

        for shape in self.get_shapes():
            if isinstance(shape, Point):
                if shape.get_centred_positions()[0] == cpos:
                    self._drawing_event.set_selected(shape, True, call_cb=False)

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
        self._drawing_event.set_selected(shape, True, call_cb=False)

    def de_select_shape(self, shape):
        """
        De-select the shape <shape> (programmatically).

        :param shape: The shape to de-select.
        :type shape: Shape
        """
        if self.is_selected(shape):
            self._drawing_event.set_selected(shape, False, call_cb=False)

    def is_selected(self, shape):
        return shape in self.selected_shapes

    def get_selected_shapes(self):
        return self.selected_shapes.values()

    @property
    def zoom(self):
        """zoom motor object

        NBNB HACK TODO - configure this here instead
        (instead of calling to diffractometer)

        Returns:
            AbstractActuator
        """
        return beamline_object.diffractometer.zoom

    @property
    def focus(self):
        """focus motor object

        NBNB HACK TODO - configure this here instead
        (instead of calling to diffractometer)

        Returns:
            AbstractActuator
        """
        return beamline_object.diffractometer.alignment_x

    @property
    def camera(self):
        """camera object

        NBNB TODO clean up and simplify configuration

        Returns:
            AbstractActuator
        """
        return beamline_object.diffractometer.camera



class DrawingEvent(QubDrawingEvent):
    """
    Extension of Qub that handles mouse and keyboard events for the
    Qub canvas. Handles selection and some manipulation of the
    Shape objects.
    """

    def __init__(self, qub_helper):
        QubDrawingEvent.__init__(self)
        self.qub_helper = qub_helper
        self.current_key_event = None
        self.current_key = None
        self.current_shape = None
        self.selection_cb = None
        self.deletion_cb = None
        self.move_to_centred_position_cb = None
        self.move_to_screen_position_cb = None

    def rawKeyPressed(self, keyevent):
        """
        Method defined by QubDrawingEvent. Called on key press.
        """
        self.current_key_event = keyevent
        self.current_key = keyevent.key()

    def rawKeyReleased(self, keyevent):
        """
        Method defined by QubDrawingEvent. Called on key release.
        Handles removal of a selected shape when delete is pressed.
        """
        if keyevent.key() == Qt.Key_Delete or keyevent.key() == Qt.Key_Backspace:

            self.delete_selected()

        self.current_key_event = None
        self.current_key = None

    def mouseDblClick(self, x, y):
        """
        Method defined by QubDrawingEvent. Called on mouse click.
        Checks if a shape is selected and 'moves to' the selected
        position.
        """
        clicked_shape = None
        for shape in self.qub_helper.get_shapes():
            modifier = shape.get_hit(x, y)

            if modifier:
                clicked_shape = shape
                break

        if clicked_shape is not None and not isinstance(clicked_shape, CanvasGrid):

            self.move_to_centred_position_cb(clicked_shape.get_centred_positions()[0])
        else:
            self.move_to_screen_position_cb(x, y)

    def mousePressed(self, x, y):
        """
        Selects the shape the mouse is over when clicked, de selects
        everything if nothing was under the mouse.
        """
        modifier = None

        for shape in self.qub_helper.get_shapes():
            modifier = shape.get_hit(x, y)

            if modifier:
                self.current_shape = shape
                break

        if not modifier:
            self.de_select_all()

    def mouseReleased(self, x, y):
        """
        Handles the type of selection, multiple shapes or
        only one.
        """
        if self.current_shape:
            modifier = self.current_shape.get_hit(x, y)

            if modifier:
                # Several positions selected
                if (
                    self.current_shape in self.qub_helper.selected_shapes
                    and len(self.qub_helper.selected_shapes) > 1
                ):

                    # Is a key pressed and is that key CTRL
                    if self.current_key == Qt.Key_Control:
                        self.de_select_current()
                    else:
                        self.de_select_all()

                # One position selected
                # Toggle a already selected position
                elif self.current_shape in self.qub_helper.selected_shapes:
                    self.de_select_current()
                else:
                    # Is a key pressed and is that key CTRL
                    if self.current_key == Qt.Key_Control:
                        pass
                    else:
                        self.de_select_all()

                    # Select the point
                    self.select_current()

        self.current_shape = None

    def de_select_all(self):
        """
        De selects all shapes.
        """
        for shape in self.qub_helper.selected_shapes.values():
            shape.unhighlight()

        self.qub_helper.selected_shapes = {}

        if callable(self.selection_cb):
            self.selection_cb(self.qub_helper.selected_shapes.values())

    def de_select_current(self, call_cb=True):
        self.set_selected(self.current_shape, False, call_cb)
        self.current_shape = None

    def select_current(self, call_cb=True):
        """
        Select the shape referenced by self._current_shape.
        """
        self.set_selected(self.current_shape, True, call_cb)

    def delete_selected(self):
        """
        Delete all the selected shapes.
        """
        for shape in self.qub_helper.selected_shapes.values():
            self.qub_helper.delete_shape(shape)

    def set_selected(self, shape, state, call_cb=True):
        """
        Select the shape <shape> (programmatically).

        :param shape: The shape to select.
        :type shape: Shape
        """
        if state:
            shape.highlight()
            self.qub_helper.selected_shapes[shape] = shape
        else:
            shape.unhighlight()
            del self.qub_helper.selected_shapes[shape]

        if callable(self.selection_cb) and call_cb:
            self.selection_cb(self.qub_helper.selected_shapes.values())


class Shape(object):
    """
    Base class for shapes.
    """

    def __init__(self):
        object.__init__(self)
        self._drawing = None

    def get_drawing(self):
        """
        :returns: The drawing on which the shape is drawn.
        :rtype: QDrawing
        """
        return self._drawing

    def draw(self):
        """
        Draws the shape on its drawing.
        """

    def get_centred_positions(self):
        """
        :returns: The centred position(s) associated with the shape.
        :rtype: List of CentredPosition objects.
        """

    def hide(self):
        """
        Hides the shape.
        """

    def show(self):
        """
        Shows the shape.
        """

    def update_position(self):
        pass

    def move(self, new_positions):
        """
        Moves the shape to the position <new_position>
        """

    def highlight(self):
        """
        Highlights the shape
        """

    def unhighlight(self):
        """
        Removes highlighting.
        """

    def get_hit(self, x, y):
        """
        :returns: True if the shape was hit by the mouse.
        """

    def get_qub_objects(self):
        """
        :returns: A list of qub objects.
        """


class Line(Shape):
    def __init__(self, drawing, start_qub_p, end_qub_p, start_cpos, end_cpos):
        object.__init__(self)

        self._drawing = drawing
        self.start_qub_p = start_qub_p
        self.end_qub_p = end_qub_p
        self.start_cpos = start_cpos
        self.end_cpos = end_cpos
        self.qub_line = None

        self.qub_line = self.draw()

    def draw(self):
        qub_line = None

        try:
            qub_line, _ = QubAddDrawing(
                self._drawing, QubLineDrawingMgr, qtcanvas.QCanvasLine
            )
            qub_line.show()
            qub_line.setPoints(
                self.start_qub_p._x,
                self.start_qub_p._y,
                self.end_qub_p._x,
                self.end_qub_p._y,
            )
            qub_line.setColor(NORMAL_COLOR)

            pen = qt.QPen(self.start_qub_p._drawingObjects[0].pen())
            pen.setWidth(1)
            pen.setColor(NORMAL_COLOR)
            qub_line.setPen(pen)
        except BaseException:
            logging.getLogger("HWR").exception("Could not draw line")

        return qub_line

    def get_centred_positions(self):
        return [self.start_cpos, self.end_cpos]

    def hide(self):
        self.qub_line.hide()

    def show(self):
        self.qub_line.show()

    def update_position(self):
        self.qub_line.moveFirstPoint(self.start_qub_p._x, self.start_qub_p._y)
        self.qub_line.moveSecondPoint(self.start_qub_p._x, self.start_qub_p._y)

    def move(self, new_positions):
        self.qub_line.moveFirstPoint(new_positions[0][0], new_positions[0][1])
        self.qub_line.moveSecondPoint(new_positions[1][0], new_positions[1][1])

    def highlight(self):
        try:
            highlighted_pen = qt.QPen(self.qub_line._drawingObjects[0].pen())
            highlighted_pen.setWidth(3)
            highlighted_pen.setColor(SELECTED_COLOR)
            self.qub_line.setPen(highlighted_pen)
        except BaseException:
            logging.getLogger("HWR").exception("Could not higlight line")
            traceback.print_exc()

    def unhighlight(self):
        try:
            normal_pen = qt.QPen(self.qub_line._drawingObjects[0].pen())
            normal_pen.setWidth(1)
            normal_pen.setColor(NORMAL_COLOR)
            self.qub_line.setPen(normal_pen)
        except BaseException:
            logging.getLogger("HWR").exception("Could not un-higlight line")
            traceback.print_exc()

    def get_hit(self, x, y):
        return None
        # return self.qub_line.getModifyClass(x, y)

    def get_qub_objects(self):
        return [self.start_qub_p, self.end_qub_p, self.qub_line]

    def get_points_index(self):
        if self.start_cpos and self.end_cpos:
            return (self.start_cpos.get_index(), self.end_cpos.get_index())


class Point(Shape):
    def __init__(self, drawing, centred_position, screen_pos):
        Shape.__init__(self)

        self.qub_point = None

        if centred_position is None:
            self.centred_position = queue_model_objects.CentredPosition()
            self.centred_position.centring_method = False
        else:
            self.centred_position = centred_position
        self.screen_pos = screen_pos
        self.point_index = None
        self._drawing = drawing

        self.qub_point = self.draw(screen_pos)

    def set_index(self, index):
        self.point_index = index

    def get_index(self):
        return self.point_index

    def get_qub_point(self):
        return self.qub_point

    def get_centred_positions(self):
        return [self.centred_position]

    def get_hit(self, x, y):
        return self.qub_point.getModifyClass(x, y)

    def draw(self, screen_pos):
        """
        Draws a qub point in the sample video.
        """
        qub_point = None

        try:
            qub_point, _ = QubAddDrawing(
                self._drawing, QubPointDrawingMgr, QubCanvasTarget
            )
            # patch Qub event manager not to respond to Shift key
            # to prevent moving the point
            evmgr_ref = qub_point._eventMgr
            evmgr = evmgr_ref()
            if evmgr:
                for method_name in ("_mouseMove", "_mousePressed", "_mouseRelease"):

                    def prevent_shift(self, event, mgr=None, method_name=method_name):
                        if event.state() & qt.Qt.ShiftButton:
                            return
                        return getattr(QubEventMgr, method_name)(self, event, mgr)

                    setattr(evmgr, method_name, types.MethodType(prevent_shift, evmgr))

            qub_point.show()

            if screen_pos:
                qub_point.setPoint(screen_pos[0], screen_pos[1])
                qub_point.setColor(NORMAL_COLOR)

        except BaseException:
            logging.getLogger("HWR").exception("Could not draw the centred position")

        return qub_point

    def show(self):
        self.qub_point.show()

    def hide(self):
        self.qub_point.hide()

    def move(self, new_positions):
        self.qub_point.move(new_positions[0][0], new_positions[0][1])

    def highlight(self):
        try:
            if self.point_index:
                text = "Point no. %d selected" % self.point_index
                if self.centred_position is not None:
                    if self.centred_position.kappa and self.centred_position.kappa_phi:
                        text = "Point no. %d (kappa: %0.2f phi: %0.2f) selected" % (
                            self.point_index,
                            self.centred_position.kappa,
                            self.centred_position.kappa_phi,
                        )
                self._drawing.setInfo(text)
                self.qub_point.setLabel(str(self.point_index))
            highlighted_pen = qt.QPen(self.qub_point._drawingObjects[0].pen())
            highlighted_pen.setWidth(2)
            highlighted_pen.setColor(SELECTED_COLOR)
            self.qub_point.setPen(highlighted_pen)
        except BaseException:
            logging.getLogger("HWR").exception("Could not higlight point")
            traceback.print_exc()

    def unhighlight(self):
        try:
            normal_pen = qt.QPen(self.qub_point._drawingObjects[0].pen())
            normal_pen.setWidth(1)
            normal_pen.setColor(NORMAL_COLOR)
            self.qub_point.setPen(normal_pen)
        except BaseException:
            logging.getLogger("HWR").exception("Could not un-higlight point")
            traceback.print_exc()

    def get_qub_objects(self):
        return [self.qub_point]


class CanvasGrid(qtcanvas.QCanvasRectangle):
    def __init__(
        self, canvas, cell_width=1, cell_height=1, beam_width=1, beam_height=1
    ):
        qtcanvas.QCanvasRectangle.__init__(self, canvas)
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
            offset = i * self.__cell_height
            self.__height = offset
            painter.drawLine(
                rect.left(), rect.top() + offset, rect.right(), rect.top() + offset
            )

        for i in range(0, num_colls + 1):
            offset = i * self.__cell_width
            self.__width = offset
            painter.drawLine(
                rect.left() + offset, rect.top(), rect.left() + offset, rect.bottom()
            )

        for i in range(0, num_rows):
            row_offset = i * self.__cell_height
            for k in range(0, num_colls):
                coll_offset = k * self.__cell_width
                self.__num_cells += 1
                if not self.__has_data:
                    if self.__num_cells % 2:
                        self.__grid_data[self.__num_cells] = (
                            self.__num_cells,
                            (0, 0, 150),
                        )
                    else:
                        self.__grid_data[self.__num_cells] = (
                            self.__num_cells,
                            (0, 0, 150),
                        )

                painter.setPen(qt.QPen(qt.Qt.black, 0, qt.Qt.SolidLine))

                color = self.__grid_data[self.__num_cells][1]

                # if self.__highlighted:
                painter.setBrush(qt.QBrush(qt.QColor(*color), qt.Qt.Dense4Pattern))
                # else:
                #    painter.setBrush(qt.QBrush(qt.QColor(*color), qt.Qt.Dense6Pattern))

                beam_hspacing = (self.__cell_width - self.__beam_width) / 2
                beam_vspacing = (self.__cell_height - self.__beam_height) / 2

                painter.drawEllipse(
                    rect.left() + coll_offset + beam_hspacing,
                    rect.top() + row_offset + beam_vspacing,
                    self.__beam_width,
                    self.__beam_height,
                )

                painter.setPen(qt.QPen(qt.Qt.black, 1, qt.Qt.SolidLine))
                tr = qt.QRect(
                    rect.left() + coll_offset,
                    rect.top() + row_offset,
                    self.__cell_width,
                    self.__cell_height,
                )

                score = self.__grid_data[self.__num_cells][0]

                if score:
                    painter.drawText(tr, qt.Qt.AlignCenter, str(score))

            if self.__label and self.__highlighted:
                # painter.setPen(qt.QPen(qt.Qt.green, 0, qt.Qt.SolidLine))
                painter.drawText(rect.right() + 2, rect.top() - 5, self.__label)

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

    def reposition(self, scale_factor_x=None, scale_factor_y=None):
        """
        Re-positions the shape, used when the scale factor changes (zooming)

        :param scale_factor_x: The new x scale factor
        :type scale_factor_x: float

        :param scale_factor_y: The new y scale factor
        :type scale_factor_y: float
        """
        if scale_factor_x:
            beam_dx = self.x() - self.__beam_pos[0]
            dx = beam_dx * scale_factor_x - beam_dx
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

        first_cell_center_x = (
            (x + (self.__cell_width / 2)) - self.__beam_pos[0]
        ) / self.__x_pixel_size
        first_cell_center_y = (
            (y + (self.__cell_height / 2)) - self.__beam_pos[1]
        ) / self.__y_pixel_size

        grid = {
            "id": key,
            "dx_mm": cell_width * (num_colls - 1),
            "dy_mm": cell_height * (num_rows - 1),
            "steps_x": num_colls,
            "steps_y": num_rows,
            "x1": first_cell_center_x,
            "y1": first_cell_center_y,
            "beam_width": self.__beam_width / self.__x_pixel_size,
            "beam_height": self.__beam_height / self.__y_pixel_size,
            "angle": 0,
        }

        # print "Beam: " + str(self.__beam_pos)
        # print "Grid: (%i, %i, %i, %i):" % (x, y, self.__cell_width,
        # self.__cell_height)

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
