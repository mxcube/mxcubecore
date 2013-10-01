"""
Contains The classes

* ShapeHistory
* DrawingEvent
* Shape
* Point
* Line.

ShapeHistory keeps track of the current shapes the user has created. The
shapes handled are any that inherits the Shape base class. There are currently
two shapes implemented Point and Line.

Point is the graphical representation of a centred position. A point can be
stored and managed by the ShapeHistory.

Line is a line between two Point objects.

DrawingEvent is an extension of Qub and handles mouse and keyboard events for
the Qub canvas. It handles selection and some manipulation of the Shape objects.
"""

import logging
import qtcanvas
import qt
import traceback
import queue_model_objects_v1 as queue_model_objects
import types

from qt import Qt

from Qub.Objects.QubEventMgr import QubEventMgr
from Qub.Objects.QubDrawingEvent import QubDrawingEvent
from Qub.Objects.QubDrawingManager import QubLineDrawingMgr
from Qub.Objects.QubDrawingManager import QubPointDrawingMgr
from Qub.Objects.QubDrawingManager import QubAddDrawing
from Qub.Objects.QubDrawingCanvasTools import QubCanvasTarget

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareRepository import dispatcher

__author__ = "Marcus Oskarsson"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["My great coleagues", "The MxCuBE colaboration"]

__version__ = "0.1"
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Beta"


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

    def set_drawing(self, drawing):
        """
        Sets the drawing the Shape objects that are managed are drawn on.

        :param drawing: The drawing that the shapes are drawn on.
        :type drawing: QubDrawing (used by Qub)

        :returns: None
        """
        if self._drawing:
            logging.getLogger('HWR').info('Setting previous drawing:' + \
                                          str(self._drawing) + ' to ' + \
                                          str(drawing))
            
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

    def get_qimage(self, image, canvas,  zoom = 1):
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

            if isinstance(canvas,list) :
                itemsList = canvas
            else:
                itemsList = canvas.allItems()

            for item in itemsList :
                if item.isVisible() :
                    if hasattr(item, 'setScrollView'): #remove standalone items
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

    def add_shape(self, shape):
        """
        Adds the shape <shape> to the list of handled objects.

        :param shape: Shape to add.
        :type shape: Shape object.
        
        """
        self.shapes[shape] = shape

        self.get_drawing_event_handler().de_select_all()
        self.get_drawing_event_handler().set_selected(shape)

    def delete_shape(self, shape):
        """
        Removes the shape <shape> from the list of handled shapes.

        :param shape: The shape to remove
        :type shape: Shape object.
        """
        
        # Another quick and ugly fix:
        #shape.hide()

        if shape in self.selected_shapes:
            del self.selected_shapes[shape]

        if shape is self._drawing_event.current_shape:
            self._drawing_event.current_shape = None
        
        del self.shapes[shape]

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
        
        if self._drawing_event:
            self._drawing_event.de_select_all()


        # Temporary fix the bug that 
        for shape in self.shapes:
            shape.hide()

        self.shapes.clear()
        self.selected_shapes.clear()
        self._drawing_event.current_shape = None


    def get_grid(self):
        """
        Returns the current grid object.
        """
        grid_dict = dict()
        dispatcher.send("grid", self, grid_dict)
        return grid_dict
            

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
        if keyevent.key() == Qt.Key_Delete or \
                keyevent.key() == Qt.Key_Backspace:

            self.delete_selected()

        self.current_key_event = None
        self.current_key = None

    def mouseDblClick(self, x ,y):
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
            
        self.move_to_centred_position_cb(clicked_shape.\
                                         get_centred_positions()[0])
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
                if self.current_shape in self.qub_helper.selected_shapes and \
                       len(self.qub_helper.selected_shapes) > 1:

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

    def de_select_current(self):
        self.current_shape.unhighlight()
        del self.qub_helper.selected_shapes[self.current_shape]

        if callable(self.selection_cb):
            self.selection_cb(self.qub_helper.selected_shapes.values())

        self.current_shape = None

    def select_current(self):
        """
        Select the shape referenced by self._current_shape.
        """
        self.current_shape.highlight()
        self.qub_helper.selected_shapes[self.current_shape] = \
            self.current_shape

        if callable(self.selection_cb):
            self.selection_cb(self.qub_helper.selected_shapes.values())

    def delete_selected(self):
        """
        Delete the selected shape.
        """
        for shape in self.qub_helper.selected_shapes.values():
            if callable(self.deletion_cb):
                self.deletion_cb(shape)
                
            self.qub_helper.delete_shape(shape)
        self.de_select_all()
        self.current_shape = None

    def set_selected(self, shape):
        """
        Select the shape <shape> (programmatically).

        :param shape: The shape to select.
        :type shape: Shape
        """
        self.current_shape = shape
        self.select_current()
        
        
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
    def __init__(self, drawing, start_qub_p, end_qub_p, 
                 start_cpos, end_cpos):
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
            qub_line, _ = QubAddDrawing(self._drawing, QubLineDrawingMgr, 
                                         qtcanvas.QCanvasLine)
            qub_line.show()
            qub_line.setPoints(self.start_qub_p._x, self.start_qub_p._y,
                                self.end_qub_p._x, self.end_qub_p._y)
            qub_line.setColor(NORMAL_COLOR)

            pen = qt.QPen(self.start_qub_p.\
                           _drawingObjects[0].pen())
            pen.setWidth(1)
            pen.setColor(NORMAL_COLOR)
            qub_line.setPen(pen)
        except:
            logging.getLogger('HWR').\
                exception('Could not draw line')

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
            highlighted_pen = qt.QPen(self.qub_line.\
                                       _drawingObjects[0].pen())
            highlighted_pen.setWidth(3)
            highlighted_pen.setColor(SELECTED_COLOR)
            self.qub_line.setPen(highlighted_pen)
        except:
            logging.getLogger('HWR').exception('Could not higlight line')
            traceback.print_exc()

    def unhighlight(self):
        try:
            normal_pen = qt.QPen(self.qub_line.\
                                  _drawingObjects[0].pen())
            normal_pen.setWidth(1)
            normal_pen.setColor(NORMAL_COLOR)
            self.qub_line.setPen(normal_pen)
        except:
            logging.getLogger('HWR').exception('Could not un-higlight line') 
            traceback.print_exc()

    def get_hit(self, x, y):
        return None
        #return self.qub_line.getModifyClass(x, y)

    def get_qub_objects(self):
        return [self.start_qub_p, self.end_qub_p, self.qub_line]


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
        self._drawing = drawing

        self.qub_point = self.draw(screen_pos)

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
            qub_point, _ = QubAddDrawing(self._drawing, QubPointDrawingMgr, 
                                          QubCanvasTarget)
            # patch Qub event manager not to respond to Shift key
            # to prevent moving the point
            evmgr_ref = qub_point._eventMgr
            evmgr = evmgr_ref()
            if evmgr:
              for method_name in ("_mouseMove", "_mousePressed", "_mouseRelease"):
                def prevent_shift(self, event, mgr=None, method_name=method_name):
                  if event.state() & qt.Qt.ShiftButton:
                    return
                  return getattr(QubEventMgr, method_name)(self,event,mgr) 
                setattr(evmgr, method_name, types.MethodType(prevent_shift, evmgr)) 
             
            qub_point.show()

            if screen_pos:
                qub_point.setPoint(screen_pos[0], screen_pos[1])
                qub_point.setColor(NORMAL_COLOR)
        
        except:
            logging.getLogger('HWR').\
                exception('Could not draw the centred position')  
            
        return qub_point
        
    def show(self):
        self.qub_point.show()

    def hide(self):
        self.qub_point.hide()

    def move(self, new_positions):
        self.qub_point.move(new_positions[0][0], new_positions[0][1])

    def highlight(self):
        try:
            highlighted_pen = qt.QPen(self.qub_point.\
                                       _drawingObjects[0].pen())
            highlighted_pen.setWidth(2)
            highlighted_pen.setColor(SELECTED_COLOR)
            self.qub_point.setPen(highlighted_pen)
        except:
            logging.getLogger('HWR').exception('Could not higlight point')
            traceback.print_exc()

    def unhighlight(self):
        try:
            normal_pen = qt.QPen(self.qub_point.\
                                  _drawingObjects[0].pen())
            normal_pen.setWidth(1)
            normal_pen.setColor(NORMAL_COLOR)
            self.qub_point.setPen(normal_pen)
        except:
            logging.getLogger('HWR').exception('Could not un-higlight point') 
            traceback.print_exc()

    def get_qub_objects(self):
          return [self.qub_point]
