import logging
import qtcanvas
import qt
import traceback
import queue_model_objects_v1 as queue_model_objects

from qt import Qt

from Qub.Objects.QubDrawingEvent import QubDrawingEvent
from Qub.Objects.QubDrawingManager import QubLineDrawingMgr
from Qub.Objects.QubDrawingManager import QubPointDrawingMgr
from Qub.Objects.QubDrawingManager import Qub2PointSurfaceDrawingMgr
from Qub.Objects.QubDrawingManager import QubAddDrawing
from Qub.Objects.QubDrawingCanvasTools import QubCanvasTarget
from Qub.Tools import QubImageSave

from HardwareRepository.BaseHardwareObjects import HardwareObject


class ShapeHistory(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._drawing = None
        self._drawing_event = DrawingEvent(self)
        self.shapes = {}
        self.selected_shapes = {}


    def set_drawing(self, drawing):
        if self._drawing:
            logging.getLogger('HWR').info('Setting previous drawing:' + \
                                          str(self._drawing) + ' to ' + \
                                          str(drawing))
            
        self._drawing = drawing
        self._drawing.addDrawingEvent(self._drawing_event)


    def get_drawing(self):
        return self._drawing


    def get_centred_positions(self):
        return self.qub_points.keys()


    def get_drawing_event_handler(self):
        return self._drawing_event


    def get_snapshot(self, qub_objects):
        matrix = self._drawing.matrix()

        zoom = 1
        if matrix is not None:
            zoom = matrix.m11()

        img = self._drawing.getPPP()
        qimg = self.get_qimage(img, qub_objects, zoom)

        return qimg


    def get_qimage(self, image, canvas,  zoom = 1):
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
        return self.shapes.values()


    def add_shape(self, shape):
        self.shapes[shape] = shape


    def delete_shape(self, shape):
        del self.shapes[shape] 


    def move_shape(self, shape, new_positions):
        self.shapes[shape].move(new_positions)


    def get_shapes(self):
        return self.shapes.values()


    def clear_all(self):
        if self._drawing_event:
            self._drawing_event.de_select_all()
        
        self.shapes.clear()
        self.selected_shapes.clear()

    
class DrawingEvent(QubDrawingEvent):
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
        self.current_key_event = keyevent
        self.current_key = keyevent.key()


    def rawKeyReleased(self, keyevent):
        if keyevent.key() == Qt.Key_Delete or \
                keyevent.key() == Qt.Key_Backspace:

            self.delete_selected()

        self.current_key_event = None
        self.current_key = None


    def mouseDblClick(self,x,y):
        clicked_shape = None
        for shape in self.qub_helper.get_shapes():            
            modifier = shape.get_hit(x, y)

            if modifier:
                clicked_shape = shape
                break
            
        self.move_to_centred_position_cb(clicked_shape.\
                                         get_centred_positions()[0])
        
    def mousePressed(self, x, y):
        modifier = None
        
        #for (cpos, qub_point) in self.qub_helper.qub_points.iteritems():
        for shape in self.qub_helper.get_shapes():            
            modifier = shape.get_hit(x, y)

            if modifier:
                self.current_shape = shape
                break

        if not modifier:
            self.de_select_all()
            

    def mouseReleased(self, x, y):
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


    def select_current(self):
        self.current_shape.highlight()
        self.qub_helper.selected_shapes[self.current_shape] = \
            self.current_shape

        if callable(self.selection_cb):
            self.selection_cb(self.qub_helper.selected_shapes.values())


    def delete_selected(self):
        for shape in self.qub_helper.selected_shapes.values():
            if callable(self.deletion_cb):
                self.deletion_cb(shape)
                
            self.qub_helper.delete_shape(shape)
        self.de_select_all()
        self.current_shape = None


        
class Shape(object):
    def __init__(self):
        object.__init__(self)
        self._drawing = None


    def get_drawing(self):
        return self._drawing


    def draw(self):
        pass


    def get_centred_positions(self):
        pass


    def hide(self):
        pass


    def show(self):
        pass


    def update_position(self):
        pass

        
    def move(self, new_positions):        
        pass


    def highlight(self):
        pass


    def unhighlight(self):
        pass


    def get_hit(self, x, y):
        pass


    def get_qub_objects(self):
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
            qub_line.setColor(Qt.yellow)

            pen = qt.QPen(self.start_qub_p.\
                           _drawingObjects[0].pen())
            pen.setWidth(1)
            pen.setColor(qt.Qt.yellow)
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
            highlighted_pen.setColor(qt.Qt.white)
            self.qub_line.setPen(highlighted_pen)
        except:
            logging.getLogger('HWR').exception('Could not higlight line')
            traceback.print_exc()


    def unhighlight(self):
        try:
            normal_pen = qt.QPen(self.qub_line.\
                                  _drawingObjects[0].pen())
            normal_pen.setWidth(1)
            normal_pen.setColor(qt.Qt.yellow)
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
            qub_point.show()
            qub_point.setPoint(screen_pos[0], screen_pos[1])
            qub_point.setColor(Qt.yellow)
        
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
            highlighted_pen.setColor(qt.Qt.white)
            self.qub_point.setPen(highlighted_pen)
        except:
            logging.getLogger('HWR').exception('Could not higlight point')
            traceback.print_exc()


    def unhighlight(self):
        try:
            normal_pen = qt.QPen(self.qub_point.\
                                  _drawingObjects[0].pen())
            normal_pen.setWidth(1)
            normal_pen.setColor(qt.Qt.yellow)
            self.qub_point.setPen(normal_pen)
        except:
            logging.getLogger('HWR').exception('Could not un-higlight point') 
            traceback.print_exc()


    def get_qub_objects(self):
          return [self.qub_point]
