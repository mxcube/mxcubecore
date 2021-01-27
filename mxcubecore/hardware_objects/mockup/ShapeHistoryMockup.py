"""
Contains the classes

* ShapeHistory
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
import os
from mxcubecore.hardware_objects import queue_model_objects

from mxcubecore.BaseHardwareObjects import HardwareObject

SELECTED_COLOR = "green"
NORMAL_COLOR = "yellow"


class ShapeHistoryMockup(HardwareObject):
    """
    Keeps track of the current shapes the user has created. The
    shapes handled are any that inherits the Shape base class.
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._drawing = None
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

    def get_drawing(self):
        """
        :returns: Returns the drawing of the shapes.
        :rtype: QubDrawing
        """
        return self._drawing

    def get_snapshot(self, qub_objects):
        """
        Get a snapshot of the video stream and overlay the objects
        in qub_objects.

        :param qub_objects: The QCanvas object to add on top of the video.
        :type qub_objects: QCanvas

        :returns: The snapshot
        :rtype: QImage
        """
        cwd = os.getcwd()
        path = os.path.join(cwd, "./test/HardwareObjectsMockup.xml/")
        qimg_path = os.path.join(path, "mxcube_sample_snapshot.jpeg")
        qimg = open(qimg_path, "rb").read()

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
        cwd = os.getcwd()
        path = os.path.join(cwd, "./test/HardwareObjectsMockup.xml/")
        img_path = os.path.join(path, "mxcube_sample_snapshot.jpeg")
        img = open(img_path, "rb").read()

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
        return

    def de_select_all(self):
        return

    def select_shape_with_cpos(self, cpos):
        return


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
        pass

    def get_centred_positions(self):
        """
        :returns: The centred position(s) associated with the shape.
        :rtype: List of CentredPosition objects.
        """
        pass

    def hide(self):
        """
        Hides the shape.
        """
        pass

    def show(self):
        """
        Shows the shape.
        """
        pass

    def update_position(self):
        pass

    def move(self, new_positions):
        """
        Moves the shape to the position <new_position>
        """
        pass

    def highlight(self):
        """
        Highlights the shape
        """
        pass

    def unhighlight(self):
        """
        Removes highlighting.
        """
        pass

    def get_hit(self, x, y):
        """
        :returns: True if the shape was hit by the mouse.
        """
        pass

    def get_qub_objects(self):
        """
        :returns: A list of qub objects.
        """
        pass


class Line(Shape):
    def __init__(self, drawing, start_qub_p, end_qub_p, start_cpos, end_cpos):
        object.__init__(self)

        self._drawing = drawing
        self.start_qub_p = start_qub_p
        self.end_qub_p = end_qub_p
        self.start_cpos = start_cpos
        self.end_cpos = end_cpos
        self.qub_line = None

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
        return

    def unhighlight(self):
        return

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

    def draw(self, screen_pos):
        """
        Draws a qub point in the sample video.
        """
        qub_point = None

        return qub_point

    def show(self):
        return

    def hide(self):
        return

    def move(self, new_positions):
        return

    def highlight(self):
        return

    def unhighlight(self):
        return
