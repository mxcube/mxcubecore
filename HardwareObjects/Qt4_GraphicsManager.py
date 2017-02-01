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

"""
Qt4_GraphicsManager keeps track of the current shapes the user has created. 
All shapes (graphics items) are based on Qt native QGraphicsLib.GraphicsItem objects.
QGraphicsScene and QGraphicsView are used to display objects

example xml:

<object class="Qt4_GraphicsManager">
   <object href="/Qt4_mini-diff-mockup" role="diffractometer"/>
   <object href="/beam-info" role="beam_info"/>
</object>
"""

import os
#import atexit
import tempfile
import logging
import numpy as np

from copy import deepcopy
from scipy import ndimage
from scipy.interpolate import splrep, sproot

from QtImport import *

import Qt4_GraphicsLib as GraphicsLib
import queue_model_objects_v1 as queue_model_objects
from HardwareRepository.BaseHardwareObjects import HardwareObject


class Qt4_GraphicsManager(HardwareObject):
    """
    Descript. : Keeps track of the current shapes the user has created. The
                Diffractometer and BeamInfo hardware objects are mandotary
    """
    def __init__(self, name):
        """
        :param name: name
        :type name: str
        """
        HardwareObject.__init__(self, name)

        self.diffractometer_hwobj = None
        self.camera_hwobj = None
        self.beam_info_hwobj = None
    
        self.graphics_config_filename = None 
        self.pixels_per_mm = [0, 0]
        self.beam_position = [0, 0]
        self.beam_info_dict = {}
        self.graphics_scene_size = [0, 0]
        self.mouse_position = [0, 0]
        self.image_scale = None 
        self.image_scale_list = []
        self.auto_grid = None
        self.auto_grid_size_mm = (0, 0)

        self.omega_axis_info_dict = {}
        self.in_centring_state = None
        self.in_grid_drawing_state = None
        self.in_measure_distance_state = None
        self.in_measure_angle_state = None
        self.in_measure_area_state = None
        self.in_move_beam_mark_state = None
        self.in_select_items_state = None
        self.in_beam_define_state = None
        self.in_magnification_mode = None
        self.wait_grid_drawing_click = None
        self.wait_measure_distance_click = None
        self.wait_measure_angle_click = None
        self.wait_measure_area_click = None
        self.wait_beam_define_click = None
        self.current_centring_method = None
        self.point_count = 0
        self.line_count = 0
        self.grid_count = 0
        self.shape_dict = {}

        self.graphics_view = None
        self.graphics_camera_frame = None
        self.graphics_beam_item = None
        self.graphics_scale_item = None
        self.graphics_omega_reference_item = None
        self.graphics_centring_lines_item = None
        self.graphics_grid_draw_item = None
        self.graphics_measure_distance_item = None
        self.graphics_measure_angle_item = None
        self.graphics_measure_area_item = None
        self.graphics_move_beam_mark_item = None
        self.graphics_select_tool_item = None
        self.graphics_beam_define_item = None
        self.graphics_move_up_item = None
        self.graphics_move_right_item = None
        self.graphics_move_down_item = None
        self.graphics_move_left_item = None
        self.graphics_magnification_item = None
 
    def init(self):
        """Main init function. Initiates all graphics items, hwobjs and 
           connects all qt signals to slots.
        """

        self.graphics_view = GraphicsLib.GraphicsView()
        self.graphics_camera_frame = GraphicsLib.GraphicsCameraFrame()
        self.graphics_scale_item = GraphicsLib.GraphicsItemScale(self)
        self.graphics_omega_reference_item = \
             GraphicsLib.GraphicsItemOmegaReference(self)
        self.graphics_beam_item = GraphicsLib.GraphicsItemBeam(self)
        self.graphics_info_item = GraphicsLib.GraphicsItemInfo(self)
        self.graphics_info_item.hide()
        self.graphics_move_beam_mark_item = \
             GraphicsLib.GraphicsItemMoveBeamMark(self)
        self.graphics_move_beam_mark_item.hide()
        self.graphics_centring_lines_item = \
             GraphicsLib.GraphicsItemCentringLines(self)
        self.graphics_centring_lines_item.hide()
        self.graphics_measure_distance_item = \
             GraphicsLib.GraphicsItemMeasureDistance(self)
        self.graphics_measure_distance_item.hide()
        self.graphics_measure_angle_item = \
             GraphicsLib.GraphicsItemMeasureAngle(self)
        self.graphics_measure_angle_item.hide()
        self.graphics_measure_area_item = \
             GraphicsLib.GraphicsItemMeasureArea(self)
        self.graphics_measure_area_item.hide()
        self.graphics_select_tool_item = GraphicsLib.GraphicsSelectTool(self)
        self.graphics_select_tool_item.hide()
        self.graphics_beam_define_item = GraphicsLib.GraphicsItemBeamDefine(self)
        self.graphics_beam_define_item.hide()
        self.graphics_move_up_item = GraphicsLib.GraphicsItemMove(self, "up")
        self.graphics_move_right_item = GraphicsLib.GraphicsItemMove(self, "right")
        self.graphics_move_down_item = GraphicsLib.GraphicsItemMove(self, "down")
        self.graphics_move_left_item = GraphicsLib.GraphicsItemMove(self, "left")
        #self.graphics_magnification_frame = \
        #     GraphicsLib.GraphicsMagnificationFrame()
        self.graphics_magnification_item = \
              GraphicsLib.GraphicsMagnificationItem(self)
        self.graphics_magnification_item.hide()
         
        self.graphics_view.graphics_scene.addItem(self.graphics_camera_frame) 
        self.graphics_view.graphics_scene.addItem(self.graphics_omega_reference_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_beam_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_info_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_move_beam_mark_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_centring_lines_item) 
        self.graphics_view.graphics_scene.addItem(self.graphics_scale_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_measure_distance_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_measure_angle_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_measure_area_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_select_tool_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_beam_define_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_move_up_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_move_right_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_move_down_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_move_left_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_magnification_item)

        self.graphics_view.scene().mouseClickedSignal.connect(\
             self.mouse_clicked)
        self.graphics_view.scene().mouseDoubleClickedSignal.connect(\
             self.mouse_double_clicked)
        self.graphics_view.scene().mouseReleasedSignal.connect(\
             self.mouse_released)
        self.graphics_view.scene().itemClickedSignal.connect(\
             self.item_clicked)
        self.graphics_view.scene().itemDoubleClickedSignal.connect(\
             self.item_double_clicked)
        self.graphics_view.scene().moveItemClickedSignal.connect(\
             self.move_item_clicked)
        self.graphics_view.mouseMovedSignal.connect(self.mouse_moved)
        self.graphics_view.keyPressedSignal.connect(self.key_pressed)
        self.graphics_view.wheelSignal.connect(self.mouse_wheel_scrolled)

        self.diffractometer_hwobj = self.getObjectByRole("diffractometer")
        pixels_per_mm = self.diffractometer_hwobj.get_pixels_per_mm()
        self.diffractometer_pixels_per_mm_changed(pixels_per_mm)             
        GraphicsLib.GraphicsItemGrid.set_grid_direction(\
               self.diffractometer_hwobj.get_grid_direction())

        self.connect(self.diffractometer_hwobj, "minidiffStateChanged", 
                     self.diffractometer_state_changed)
        self.connect(self.diffractometer_hwobj, "centringStarted",
                     self.diffractometer_centring_started)
        self.connect(self.diffractometer_hwobj, "centringAccepted", 
                     self.create_centring_point)
        self.connect(self.diffractometer_hwobj, "centringSuccessful", 
                     self.diffractometer_centring_successful)
        self.connect(self.diffractometer_hwobj, "centringFailed", 
                     self.diffractometer_centring_failed)
        self.connect(self.diffractometer_hwobj, "pixelsPerMmChanged", 
                     self.diffractometer_pixels_per_mm_changed) 
        self.connect(self.diffractometer_hwobj, "omegaReferenceChanged", 
                     self.diffractometer_omega_reference_changed)
        self.connect(self.diffractometer_hwobj, "phiMotorMoved",
                     self.diffractometer_phi_motor_moved)
        self.connect(self.diffractometer_hwobj, "minidiffPhaseChanged",
                     self.diffractometer_phase_changed)

        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        if self.beam_info_hwobj is not None:
            self.beam_info_dict = self.beam_info_hwobj.get_beam_info()
            self.beam_position = self.beam_info_hwobj.get_beam_position()
            self.connect(self.beam_info_hwobj, 
                         "beamPosChanged", 
                         self.beam_position_changed)
            self.connect(self.beam_info_hwobj, 
                         "beamInfoChanged",
                         self.beam_info_changed)

            self.beam_info_changed(self.beam_info_dict)
            self.beam_position_changed(self.beam_info_hwobj.get_beam_position())
        else:
            logging.getLogger("HWR").error("GraphicsManager: BeamInfo hwobj not defined")

        self.camera_hwobj = self.getObjectByRole("camera")
        if self.camera_hwobj is not None:
            self.graphics_scene_size = self.camera_hwobj.get_image_dimensions()
            self.set_graphics_scene_size(self.graphics_scene_size, False)
            self.camera_hwobj.start_camera()
            self.connect(self.camera_hwobj, 
                         "imageReceived", 
                         self.camera_image_received) 
        else:         
            logging.getLogger("HWR").error("GraphicsManager: Camera hwobj not defined")

        try:
            self.image_scale_list = eval(self.getProperty("imageScaleList"))
            if len(self.image_scale_list) > 0:
                self.image_scale = self.getProperty("defaultImageScale") 
                self.set_image_scale(self.image_scale, self.image_scale is not None)
        except:
            pass

        if self.getProperty("store_graphics_config") == True:
            #atexit.register(self.save_graphics_config)
            self.graphics_config_filename = self.getProperty("graphics_config_filename")
            if self.graphics_config_filename is None:
                self.graphics_config_filename = os.path.join(\
                    tempfile.gettempdir(), "mxcube", "graphics_config.dat")
            self.load_graphics_config()
        
        try:
           self.auto_grid_size_mm = eval(self.getProperty("auto_grid_size_mm"))
        except:
           self.auto_grid_size_mm = (0.2, 0.2)

        self.graphics_move_up_item.setVisible(self.getProperty("enable_move_buttons") == True)
        self.graphics_move_right_item.setVisible(self.getProperty("enable_move_buttons") == True)
        self.graphics_move_down_item.setVisible(self.getProperty("enable_move_buttons") == True)
        self.graphics_move_left_item.setVisible(self.getProperty("enable_move_buttons") == True)
        try:
            self.graphics_magnification_item.set_properties(\
                 self.getProperty("magnification_tool"))
        except:
            pass
        #self.init_auto_grid()  

    def save_graphics_config(self):
        """Saves graphical objects in the file
        """

        if self.graphics_config_filename is None:
            return

        logging.getLogger("HWR").debug("GraphicsManager: Saving graphics " + \
            "in configuration file %s" % self.graphics_config_filename)
        try:
            if not os.path.exists(os.path.dirname(self.graphics_config_filename)):
                os.makedirs(os.path.dirname(self.graphics_config_filename))
            graphics_config_file = open(self.graphics_config_filename, "w")
            graphics_config = []
            for shape in self.get_shapes():
                if isinstance(shape, GraphicsLib.GraphicsItemPoint):
                    cpos = shape.get_centred_position()
                    graphics_config.append({"type" : "point",
                                            "index": shape.index,
                                            "pos_x": shape.start_coord,
                                            "pos_y": shape.end_coord,
                                            "cpos": cpos.as_dict(),
                                            "cpos_index": cpos.get_index()})
                elif isinstance(shape, GraphicsLib.GraphicsItemLine):
                    (start_point_index, end_point_index) = shape.get_points_index()
                    graphics_config.append({"type" : "line",
                                            "index": shape.index,
                                            "start_point_index": start_point_index,
                                            "end_point_index": end_point_index,})

            graphics_config_file.write(repr(graphics_config))
            graphics_config_file.close()
        except:
            logging.getLogger("HWR").error("GraphicsManager: Error saving graphics " + \
               "in configuration file %s" % self.graphics_config_filename)

    def load_graphics_config(self):
        """Loads graphics from file
        """
        if os.path.exists(self.graphics_config_filename):
            try:
               logging.getLogger("HWR").debug("GraphicsManager: Loading graphics " + \
                  "from configuration file %s" % self.graphics_config_filename)
               graphics_config_file = open(self.graphics_config_filename)
               graphics_config = eval(graphics_config_file.read())
               for graphics_item in graphics_config:
                   if graphics_item["type"] == "point":
                       point = self.create_centring_point(\
                          None, {"motors": graphics_item["cpos"]})
                       point.index = graphics_item["index"]
                       cpos = point.get_centred_position()
                       cpos.set_index(graphics_item["cpos_index"])
               for graphics_item in graphics_config:
                   if graphics_item["type"] == "line":
                       start_point = self.get_point_by_index(\
                          graphics_item["start_point_index"])
                       end_point = self.get_point_by_index(\
                          graphics_item["end_point_index"])
                       self.create_line(start_point, end_point)
               self.de_select_all()
               graphics_config_file.close()
            except:
               logging.getLogger("HWR").error("GraphicsManager: Unable to load " + \
                  "graphics from configuration file %s" % self.graphics_config_filename)

    def camera_image_received(self, pixmap_image):
        """Method called when a frame from camera arrives.
           Slot to signal 'imageReceived'

        :param pixmap_image: frame from camera
        :type pixmap_image: QtGui.QPixmapImage
        """
        if self.image_scale:
            pixmap_image = pixmap_image.scaled(QSize(\
               pixmap_image.width() * self.image_scale,
               pixmap_image.height() * self.image_scale))
        self.graphics_camera_frame.setPixmap(pixmap_image)

        if self.in_magnification_mode:
            self.graphics_magnification_item.set_pixmap(pixmap_image)

    def beam_position_changed(self, position):
        """Method called when beam position on the screen changed.

        :param position: beam position on a screen
        :type position: list of two int
        """
        if position:
            self.beam_position = position
            for graphics_item in self.graphics_view.graphics_scene.items():
                if isinstance(graphics_item, GraphicsLib.GraphicsItem):
                    graphics_item.set_beam_position(position)

    def beam_info_changed(self, beam_info):
        """Method called when beam info changed

        :param beam_info: information about the beam shape
        :type beam_info: dict with beam info parameters
        """
        if beam_info:
            self.beam_info_dict = beam_info
            for graphics_item in self.graphics_view.graphics_scene.items():
                if isinstance(graphics_item, GraphicsLib.GraphicsItem):
                    graphics_item.set_beam_info(beam_info)

    def diffractometer_state_changed(self, *args):
        """Method called when diffractometer state changed.
           Updates point screen coordinates and grid coorner coordinates.
           If diffractometer not ready then hides all shapes.
        """
        if self.diffractometer_hwobj.is_ready():
            for shape in self.get_shapes():
                if isinstance(shape, GraphicsLib.GraphicsItemPoint):
                    cpos =  shape.get_centred_position()
                    new_x, new_y = self.diffractometer_hwobj.\
                        motor_positions_to_screen(cpos.as_dict())
                    shape.set_start_position(new_x, new_y)
                elif isinstance(shape, GraphicsLib.GraphicsItemGrid):
                    grid_cpos = shape.get_centred_position()
                    if grid_cpos is not None:
                        current_cpos = queue_model_objects.CentredPosition(\
                            self.diffractometer_hwobj.get_positions())

                        current_cpos.set_motor_pos_delta(0.1)
                        grid_cpos.set_motor_pos_delta(0.1)

                        if hasattr(grid_cpos, "zoom"):
                            current_cpos.zoom = grid_cpos.zoom

                        center_coord = self.diffractometer_hwobj.\
                            motor_positions_to_screen(grid_cpos.as_dict())
                        if center_coord:
                            shape.set_center_coord(center_coord)

                            corner_coord = []
                            for motor_pos in shape.get_motor_pos_corner():
                                corner_coord.append((self.diffractometer_hwobj.\
                                    motor_positions_to_screen(motor_pos)))
                            shape.set_corner_coord(corner_coord)
      
                            if current_cpos == grid_cpos:
                                shape.set_projection_mode(False)
                            else:    
                                shape.set_projection_mode(True)

            self.show_all_items()
            self.graphics_view.graphics_scene.update()
            self.emit("diffractometerReady", True)
        else:
            self.hide_all_items()
            self.emit("diffractometerReady", False)
      
    def diffractometer_phase_changed(self, phase):
        """Phase changed event.
           If PHASE_BEAM then displays a grid on the screen
        """  
        self.graphics_scale_item.set_display_grid(\
             phase == self.diffractometer_hwobj.PHASE_BEAM)
        self.emit("diffractometerPhaseChanged", phase)

    def diffractometer_centring_started(self, centring_method, flexible):
        """Method called when centring started as a reply from diffractometer

        :param centring_method: centring method
        :type centring_method: str
        :param flexible: flexible bit
        :type flexible: bool
        :emits: centringStarted
        """
        self.current_centring_method = centring_method
        self.emit("centringStarted")  

    def create_centring_point(self, centring_state, centring_status):
        """Creates a new centring position and adds it to graphics point.

        :param centring_state: 
        :type centring_state: str
        :param centring_status: dictionary with motor pos and etc
        :type centring_status: dict
        :emits: centringInProgress
        """
        p_dict = {}

        if 'motors' in centring_status and \
                'extraMotors' in centring_status:

            p_dict = dict(centring_status['motors'],
                          **centring_status['extraMotors'])
        elif 'motors' in centring_status:
            p_dict = dict(centring_status['motors'])

        self.emit("centringInProgress", False)

        if p_dict:
            cpos = queue_model_objects.CentredPosition(p_dict)
            screen_pos = self.diffractometer_hwobj.\
                    motor_positions_to_screen(cpos.as_dict())
            point = GraphicsLib.GraphicsItemPoint(cpos, True, 
                    screen_pos[0], screen_pos[1])
            self.add_shape(point)
            cpos.set_index(point.index)
            return point

    def diffractometer_centring_successful(self, method, centring_status):
        """Last stage in centring procedure

        :param method: method name
        :type method: str
        :param centring_status: centring status
        :type centring_status: dict
        :emits: - centringSuccessful 
                - infoMsg
        """
        self.set_centring_state(False)
        self.emit("centringSuccessful", method, centring_status)
        self.emit("infoMsg", "Click Save to store the centred point "+\
                  "or start a new centring")

    def diffractometer_centring_failed(self, method, centring_status):
        """CleanUp method after centring failed

        :param method: method name
        :type method: str
        :param centring_status: centring status
        :type centring_status: dict
        :emits: - centringFailed
                - infoMsg
        """
        self.set_centring_state(False) 
        self.emit("centringFailed", method, centring_status)
        self.emit("infoMsg", "")

    def diffractometer_pixels_per_mm_changed(self, pixels_per_mm):
        """Updates graphics scale when zoom changed

        :param pixels_per_mm: two floats for scaling
        :type pixels_per_mm: list with two floats
        """
        if type(pixels_per_mm) in (list, tuple):
            if pixels_per_mm != self.pixels_per_mm:
                self.pixels_per_mm = pixels_per_mm
                for item in self.graphics_view.graphics_scene.items():
                    if isinstance(item, GraphicsLib.GraphicsItem):
                        item.set_pixels_per_mm(self.pixels_per_mm)
                self.graphics_view.graphics_scene.update()

    def diffractometer_omega_reference_changed(self, omega_reference):
        """Method called when omega reference changed

        :param omega_reference: omega reference values
        :type omega_reference: list of two coordinated
        """
        self.graphics_omega_reference_item.set_reference(omega_reference)

    def diffractometer_phi_motor_moved(self, position):
        """Method when phi motor changed. Updates omega reference by
           redrawing phi angle
       
        :param position: phi rotation value
        :type position: float
        """
        self.graphics_omega_reference_item.set_phi_position(position)
        
    def mouse_clicked(self, pos_x, pos_y, left_click=True):
        """Method when mouse clicked on GraphicsScene

        :param pos_x: screen coordinate X
        :type pos_x: int
        :param pos_y: screen coordinate Y
        :type pos_y: int
        :param left_click: left button clicked
        :type left_click: bool
        :emits: - shapeSelected
                - pointSelected
                - infoMsg
        """
        if self.in_centring_state:
            self.graphics_centring_lines_item.add_position(pos_x, pos_y)
            self.diffractometer_hwobj.image_clicked(pos_x, pos_y)
        elif self.wait_grid_drawing_click:
            self.in_grid_drawing_state = True
            self.graphics_grid_draw_item.set_draw_mode(True)
            self.graphics_grid_draw_item.set_draw_start_position(pos_x, pos_y)
            self.graphics_grid_draw_item.show()
        elif self.wait_measure_distance_click:
            self.start_graphics_item(self.graphics_measure_distance_item)
            self.in_measure_distance_state = True
            self.wait_measure_distance_click = False
        elif self.wait_measure_angle_click:
            self.start_graphics_item(self.graphics_measure_angle_item)
            self.in_measure_angle_state = True
            self.wait_measure_angle_click = False
        elif self.wait_measure_area_click:
            self.start_graphics_item(self.graphics_measure_area_item)
            self.in_measure_area_state = True
            self.wait_measure_area_click = False
        elif self.wait_beam_define_click:
            self.start_graphics_item(self.graphics_beam_define_item)
            self.in_beam_define_state = True
            self.wait_beam_define_click = False
        elif self.in_measure_distance_state:
            self.graphics_measure_distance_item.store_coord(pos_x, pos_y)
        elif self.in_measure_angle_state:
            self.graphics_measure_angle_item.store_coord(pos_x, pos_y)
        elif self.in_measure_area_state:
            self.graphics_measure_area_item.store_coord()
        elif self.in_move_beam_mark_state:
            self.stop_move_beam_mark()
        elif self.in_beam_define_state:
            self.stop_beam_define()
            #self.graphics_beam_define_item.store_coord(pos_x, pos_y)
        else:
            self.emit("pointSelected", None)
            self.emit("infoMsg", "")
            if left_click: 
                self.graphics_select_tool_item.set_start_position(pos_x, pos_y)
                self.graphics_select_tool_item.set_end_position(pos_x, pos_y)
                self.graphics_select_tool_item.show()
                self.in_select_items_state = True
            for graphics_item in self.graphics_view.scene().items():
                graphics_item.setSelected(False)
                if type(graphics_item) in [GraphicsLib.GraphicsItemPoint, 
                                           GraphicsLib.GraphicsItemLine, 
                                           GraphicsLib.GraphicsItemGrid]:
                    self.emit("shapeSelected", graphics_item, False)  
                    #if isinstance(graphics_item, GraphicsLib.GraphicsItemPoint):
                    #    self.emit("pointSelected", graphics_item)

    def mouse_double_clicked(self, pos_x, pos_y):
        """If in one of the measuring states, then stops measuring.
           Otherwise moves to screen coordinate

        :param pos_x: screen coordinate X
        :type pos_x: int
        :param pos_y: screen coordinate Y
        :type pos_y: int
        """
        if self.in_measure_distance_state:
            self.stop_measure_distance()
        elif self.in_measure_angle_state:
            self.stop_measure_angle()
        elif self.in_measure_area_state:
            self.stop_measure_area()
        elif self.in_beam_define_state:
            self.stop_beam_define()
        else: 
            self.diffractometer_hwobj.move_to_beam(pos_x, pos_y)

    def mouse_released(self, pos_x, pos_y):
        """Mouse release method. Used to finish grid drawing and item 
           selection with selection rectangle

        :param pos_x: screen coordinate X
        :type pos_x: int
        :param pos_y: screen coordinate Y
        :type pos_y: int
        :emits: shapeCreated
        """
        if self.in_grid_drawing_state:
            QApplication.restoreOverrideCursor()
            self.update_grid_motor_positions(self.graphics_grid_draw_item)
            self.graphics_grid_draw_item.set_draw_mode(False)
            self.wait_grid_drawing_click = False
            self.in_grid_drawing_state = False
            self.de_select_all()
            self.emit("shapeCreated", self.graphics_grid_draw_item, "Grid")
            self.graphics_grid_draw_item.setSelected(True) 
            self.shape_dict[self.graphics_grid_draw_item.get_display_name()] = \
                 self.graphics_grid_draw_item
        elif self.in_beam_define_state:
            self.stop_beam_define()
        elif self.in_select_items_state:
            self.graphics_select_tool_item.hide()
            self.in_select_items_state = False
            """
            for point in self.get_points():
                if point.isSelected():
                    self.emit("pointSelected", point)
            """
            self.select_lines_and_grids()
           
    def mouse_moved(self, pos_x, pos_y):
        """Executed when mouse moved. Used in all measure methods, centring
           procedure and item selection procedure.

        :param pos_x: screen coordinate X
        :type pos_x: int
        :param pos_y: screen coordinate Y
        :type pos_y: int
        :emits: mouseMoved
        """
        self.emit("mouseMoved", pos_x, pos_y)
        self.mouse_position[0] = pos_x
        self.mouse_position[1] = pos_y
        if self.in_centring_state:
            self.graphics_centring_lines_item.set_start_position(pos_x, pos_y)
        elif self.in_grid_drawing_state:
            if self.graphics_grid_draw_item.is_draw_mode():
                self.graphics_grid_draw_item.set_draw_end_position(pos_x, pos_y)
        elif self.in_measure_distance_state:
            self.graphics_measure_distance_item.set_coord(self.mouse_position)
        elif self.in_measure_angle_state:
            self.graphics_measure_angle_item.set_coord(self.mouse_position)
        elif self.in_measure_area_state:
            self.graphics_measure_area_item.set_coord(self.mouse_position)
        elif self.in_move_beam_mark_state:
            self.graphics_move_beam_mark_item.set_end_position(\
                self.mouse_position[0], self.mouse_position[1])
        elif self.in_beam_define_state:
            self.graphics_beam_define_item.set_end_position(\
                self.mouse_position[0], self.mouse_position[1])
        elif self.in_select_items_state:
             
            self.graphics_select_tool_item.set_end_position(pos_x, pos_y)
            select_start_x = self.graphics_select_tool_item.start_coord[0]
            select_start_y = self.graphics_select_tool_item.start_coord[1]
            if abs(select_start_x - pos_x) > 5 and \
               abs(select_start_y - pos_y) > 5:
                painter_path = QPainterPath()
                painter_path.addRect(min(select_start_x, pos_x),
                                     min(select_start_y, pos_y),
                                     abs(select_start_x - pos_x),
                                     abs(select_start_y - pos_y))
                self.graphics_view.graphics_scene.setSelectionArea(painter_path)
                """
                for point in self.get_points():
                    if point.isSelected():
                        self.emit("pointSelected", point)
                self.select_lines_and_grids()
                """
        elif self.in_magnification_mode:
            self.graphics_magnification_item.set_end_position(pos_x, pos_y)

    def key_pressed(self, key_event):
        """Method when key on GraphicsView pressed.
           - Deletes selected shapes if Delete pressed
           - Cancels measurement action if Escape pressed

        :param key_event: key event type
        :type key_event: str
        """
        if key_event == "Delete":
            for item in self.graphics_view.graphics_scene.items():
                if item.isSelected():
                    self.delete_shape(item)
        elif key_event == "Escape":
            self.stop_measure_distance()
            self.stop_measure_angle()
            self.stop_measure_area()  
            if self.in_beam_define_state:
                self.stop_beam_define()
            if self.in_magnification_mode:
                self.set_magnification_mode(False)
        #elif key_event == "Up":
        #    self.diffractometer_hwobj.move_to_beam(self.beam_position[0],
        #                                           self.beam_position[1] - 50)
        #elif key_event == "Down":
        #    self.diffractometer_hwobj.move_to_beam(self.beam_position[0], 
        #                                           self.beam_position[1] + 50)
        elif key_event == "Plus":
            self.diffractometer_hwobj.zoom_in()
        elif key_event == "Minus":
            self.diffractometer_hwobj.zoom_out()

    def mouse_wheel_scrolled(self, delta):
        """Method called when mouse wheel is scrolled.
           Rotates omega axis up or down
        """
        if delta > 0:
            self.diffractometer_hwobj.move_omega_relative(20)
        else:
            self.diffractometer_hwobj.move_omega_relative(-20)
 
    def item_clicked(self, item, state):
        """Item clicked event

        :param item: clicked item
        :type item: QGraphicsLib.GraphicsItem
        :param state: selection state
        :type state: bool 
        :emits: - pointsSelected
                - infoMsg
        """
        if type(item) in [GraphicsLib.GraphicsItemPoint, 
                          GraphicsLib.GraphicsItemLine, 
                          GraphicsLib.GraphicsItemGrid]: 
            self.emit("shapeSelected", item, state)
            if isinstance(item, GraphicsLib.GraphicsItemPoint):
                self.emit("pointSelected", item)
                self.emit("infoMsg", item.get_full_name() + " selected")

    def item_double_clicked(self, item):
        """Item double clicked method.
           If centring point double clicked then moves motors to the 
           centring position

        :param item: double clicked item
        :type item: QGraphicsLib.GraphicsItem
        """ 
        if isinstance(item, GraphicsLib.GraphicsItemPoint):
            self.diffractometer_hwobj.move_to_centred_position(\
                 item.get_centred_position())

    def move_item_clicked(self, direction):
        print "Move screen: ", direction
    
    def get_graphics_view(self):
        """Rturns current GraphicsView
     
        :returns: QGraphicsView
        """
        return self.graphics_view

    def get_graphics_camera_frame(self):
        """Rturns current CameraFrame
     
        :returns: GraphicsCameraFrame
        """
        return self.graphics_camera_frame 

    def set_graphics_scene_size(self, size, fixed):
        """Sets fixed size of scene

        :param size: scene size
        :type size: list
        :param fixed: fixed bit
        :type fixed: bool
        """
        if not self.graphics_scene_size or fixed:
            self.graphics_scene_size = size
            self.graphics_scale_item.set_start_position(size[0], size[1])
            self.graphics_view.scene().setSceneRect(0, 0, size[0], size[1])
            #self.graphics_view.setFixedSize(size[0] + 2, size[1] + 2)

    def set_centring_state(self, state):
        """Sets centrin state
 
        :param state: centring state
        :type state: bool
        """
        self.in_centring_state = state
        self.graphics_centring_lines_item.setVisible(state)
        self.graphics_centring_lines_item.centring_points = []

    def get_shapes(self):
        """Returns currently handled shapes.

        :returns: list with shapes
        """
        shapes_list = []
        for shape in self.graphics_view.graphics_scene.items():
            if type(shape) in (GraphicsLib.GraphicsItemPoint, 
                               GraphicsLib.GraphicsItemLine, 
                               GraphicsLib.GraphicsItemGrid):
                shapes_list.append(shape)                 
        return shapes_list

    def get_points(self):
        """Returns all points

        :returns: list with GraphicsLib.GraphicsItemPoint
        """
        current_points = []

        for shape in self.get_shapes():
            if isinstance(shape, GraphicsLib.GraphicsItemPoint):
                current_points.append(shape)

        return current_points

    def get_point_by_index(self, index):
        """Returns centring point by its index

        :param index: point index
        :type inde: int
        :returns: Qt4_GraphicsLib.GraphicsPoint
        """
        for point in self.get_points():
            if point.index == index:
                return point 
        
    def add_shape(self, shape):
        """Adds the shape <shape> to the list of handled objects.

        :param shape: Shape to add.
        :type shape: Shape object.
        :emits: shapeSelected
        """
        self.de_select_all()
        if isinstance(shape, GraphicsLib.GraphicsItemPoint):
            self.point_count += 1
            shape.index = self.point_count
            self.emit("shapeCreated", shape, "Point")
            self.emit("pointSelected", shape)
            self.emit("infoMsg", "Centring %s created" % shape.get_full_name())
        elif isinstance(shape, GraphicsLib.GraphicsItemLine):
            self.line_count += 1
            shape.index = self.line_count
            self.emit("shapeCreated", shape, "Line")
            self.emit("infoMsg", "%s created" % shape.get_full_name())
        self.shape_dict[shape.get_display_name()] = shape
        self.graphics_view.graphics_scene.addItem(shape)
        shape.setSelected(True)
        self.emit("shapeSelected", shape, True)
        self.save_graphics_config()

    def delete_shape(self, shape):
        """Removes the shape <shape> from the list of handled shapes.

        :param shape: The shape to remove
        :type shape: GraphicsLib.GraphicsItem object
        :emits: shapeDeleted
        """
        if isinstance(shape, GraphicsLib.GraphicsItemPoint):
            for s in self.get_shapes():
                if isinstance(s, GraphicsLib.GraphicsItemLine):
                    if shape in s.get_graphics_points():
                        self.delete_shape(s)
                        break
        shape_type = ""
        if isinstance(shape, GraphicsLib.GraphicsItemPoint):
            shape_type = "Point"
        elif isinstance(shape, GraphicsLib.GraphicsItemLine):
            shape_type = "Line"
        elif isinstance(shape, GraphicsLib.GraphicsItemGrid):
            shape_type = "Grid"

        self.emit("shapeDeleted", shape, shape_type)
        self.graphics_view.graphics_scene.removeItem(shape)
        self.graphics_view.graphics_scene.update()

    def get_shape_by_name(self, shape_name):
        """Returns shape by name

        :param shape_name: name of the shape
        :type shape_name: str
        :returns: GraphicsLib.GraphicsItem
        """
        return self.shape_dict.get(shape_name)            

    def clear_all(self):
        """Clear the shape history, remove all contents.
        """

        self.point_count = 0
        self.line_count = 0
        self.grid_count = 0
        for shape in self.get_shapes():
            #if shape == self.auto_grid:
            #    shape.hide()
            #else:
            self.delete_shape(shape)
        self.graphics_view.graphics_scene.update()

    def de_select_all(self):
        """Deselects all shapes
        """
        self.graphics_view.graphics_scene.clearSelection()

    def select_shape(self, shape, state=True):
        """Selects shape

        :param shape: shape to be selected or unselected
        :type shape: Qtg4_GraphicsLib.GraphicsItem
        :param state: selection state
        :type state: bool
        """
        shape.setSelected(state)
        self.graphics_view.graphics_scene.update()

    def select_all_points(self):
        """Selects all points
        """
        self.de_select_all()
        for shape in self.get_points():
            shape.setSelected(True) 
        self.graphics_view.graphics_scene.update()

    def select_shape_with_cpos(self, cpos):
        """Selects point with centred position

        :param cpos: centring point 
        :type cpos: queue_model_objects.CentredPosition
        """
        self.de_select_all()
        for shape in self.get_points():
            if shape.get_centred_position() == cpos:
                shape.setSelected(True)
        #self.graphics_view.graphics_scene.update()

    def get_selected_shapes(self):
        """Returns selected shapes

        :returns: list with GraphicsLib.GraphicsItem
        """

        selected_shapes = []
        for item in self.graphics_view.graphics_scene.items():
            if (type(item) in (GraphicsLib.GraphicsItemPoint, 
                               GraphicsLib.GraphicsItemLine,
                               GraphicsLib.GraphicsItemGrid) and
                item.isSelected()):
                selected_shapes.append(item) 
        return selected_shapes

    def get_selected_points(self):
        """Returns selected points

        :returns: list with GraphicsLib.GraphicsItemPoint
        """

        selected_points = []
        selected_shapes = self.get_selected_shapes()
        for shape in selected_shapes:
            if isinstance(shape, GraphicsLib.GraphicsItemPoint):
                selected_points.append(shape)
        return sorted(selected_points, key = lambda x : x.index, reverse = False)

    def hide_all_items(self):
        """Hides all items
        """
        for shape in self.get_shapes():
            if shape != self.auto_grid:
                shape.hide()

    def show_all_items(self):
        """Shows all items
        """
        for shape in self.get_shapes():
            if shape != self.auto_grid:
               shape.show()

    def get_scene_snapshot(self, shape=None, bw=None, return_as_array=None):
        """Takes a snapshot of the scene

        :param shape: shape that needs to be selected
        :type shape: GraphicsLib.GraphicsItem
        :returns: QImage
        """

        if shape:
            self.hide_all_items()
            #self.de_select_all()
            shape.show()
            #shape.setSelected(True)
            #self.select_shape_with_cpos(shape.get_centred_position())
        self.graphics_omega_reference_item.hide() 

        image = QImage(self.graphics_view.graphics_scene.sceneRect().\
            size().toSize(), QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        image_painter = QPainter(image)
        self.graphics_view.render(image_painter)
        image_painter.end()
        self.show_all_items()
        self.graphics_omega_reference_item.show()
        if return_as_array:
            pass         
        else:
            return image

    def save_scene_snapshot(self, filename):
        """Method to save snapshot
        
        :param file_name: file name
        :type file_name: str 
        """
        logging.getLogger("user_level_log").debug("Saving scene snapshot: %s" % filename)
        snapshot = self.get_scene_snapshot()
        snapshot.save(filename)

    def get_raw_snapshot(self, bw=False, return_as_array=False):
        """Returns a raw snapshot from camera

        :param bw: black and white
        :type bw: bool
        :param return_as_array: return image as numpy array
        :type return_as_array: bool
        """
        return self.camera_hwobj.get_snapshot(bw, return_as_array)

    def save_raw_snapshot(self, filename, bw=False, image_type='PNG'):
        """Save raw image from camera in file

        :param filename: filename
        :type filename: str
        :param bw: black and white
        :type bw: bool
        :param image_type: image format. Default png
        :type image_type: str         
        """
        logging.getLogger("user_level_log").debug("Saving raw snapshot: %s" % filename)
        self.camera_hwobj.save_snapshot(filename, image_type)

    def start_measure_distance(self, wait_click=False):
        """Distance measuring method

        :param wait_click: wait for first click to start
        :type wait_click: bool
        :emits: infoMsg
        """ 

        QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        if wait_click:
            logging.getLogger("user_level_log").info("Click to start " + \
                    "distance  measuring (Double click stops)")  
            self.wait_measure_distance_click = True
            self.emit("infoMsg", "Distance measurement")
        else:
            self.wait_measure_distance_click = False
            self.in_measure_distance_state = True
            self.start_graphics_item(self.graphics_measure_distance_item)

    def start_measure_angle(self, wait_click = False):
        """Angle measuring method

        :param wait_click: wait for first click to start
        :type wait_click: bool
        :emits: infoMsg
        """

        QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        if wait_click:
            logging.getLogger("user_level_log").info("Click to start " + \
                 "angle measuring (Double click stops)")
            self.wait_measure_angle_click = True
            self.emit("infoMsg", "Angle measurement")
        else:
            self.wait_measure_angle_click = False
            self.in_measure_angle_state = True
            self.start_graphics_item(self.graphics_measure_angle_item)
            
    def start_measure_area(self, wait_click = False):
        """Area measuring method

        :param wait_click: wait for first click to start
        :type wait_click: bool
        :emits: infoMsg
        """

        QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        if wait_click:
            logging.getLogger("user_level_log").info("Click to start area " + \
                    "measuring (Double click stops)")
            self.wait_measure_area_click = True
            self.emit("infoMsg", "Area measurement")
        else:
            self.wait_measure_area_click = False
            self.in_measure_area_state = True
            self.start_graphics_item(self.graphics_measure_area_item)

    def start_move_beam_mark(self):
        """Method to move beam mark

        :emits: infoMsg
        """

        QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        self.emit("infoMsg", "Move beam mark")
        self.in_move_beam_mark_state = True
        self.start_graphics_item(\
             self.graphics_move_beam_mark_item,
             start_pos = self.graphics_beam_item.start_coord)
        #self.graphics_move_beam_mark_item.set_beam_mark(\
        #     self.beam_info_dict, self.pixels_per_mm) 

    def start_define_beam(self):
        """Method to define beam size. 
           User 

        :emits: infoMsg
        """

        QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        logging.getLogger("user_level_log").info("Select an area to " + \
                 "define beam size")
        self.wait_beam_define_click = True
        self.emit("infoMsg", "Define beam size")

    def start_graphics_item(self, item, start_pos=None, end_pos=None):
        """Updates item on the scene

        :param item: item
        :type item: GraphicsLib.GraphicsItem
        :param start_pos: draw start position
        :type start_pos: list with x and y coordinates
        :param end_pos: draw end position
        :type end_pos: list with x and y coordinates
        """

        if not start_pos:
            start_pos = self.mouse_position
        if not end_pos:
            end_pos = self.mouse_position
        item.set_start_position(start_pos[0], start_pos[1])
        item.set_end_position(end_pos[0], end_pos[1])
        item.show()
        self.graphics_view.graphics_scene.update()

    def stop_measure_distance(self):
        """Stops distance measurement

        :emits: infoMsg
        """

        QApplication.restoreOverrideCursor()
        self.in_measure_distance_state = False
        self.wait_measure_distance_click = False
        self.graphics_measure_distance_item.hide()
        self.graphics_view.graphics_scene.update()
        self.emit("infoMsg", "")

    def stop_measure_angle(self):
        """Stops angle measurement

        :emits: infoMsg
        """

        QApplication.restoreOverrideCursor()
        self.in_measure_angle_state = False
        self.wait_measure_angle_click = False
        self.graphics_measure_angle_item.hide()
        self.graphics_view.graphics_scene.update()
        self.emit("infoMsg", "")

    def stop_measure_area(self):
        """Stops area measurement

        :emits: infoMsg
        """

        QApplication.restoreOverrideCursor()
        self.in_measure_area_state = False
        self.wait_measure_area_click = False
        self.graphics_measure_area_item.hide()
        self.graphics_view.graphics_scene.update()
        self.emit("infoMsg", "")

    def stop_move_beam_mark(self):
        """Stops to move beam mark

        :emits: infoMsg
        """

        QApplication.restoreOverrideCursor()
        self.in_move_beam_mark_state = False
        self.graphics_move_beam_mark_item.hide()
        self.graphics_view.graphics_scene.update()
        self.beam_info_hwobj.set_beam_position(\
             self.graphics_move_beam_mark_item.end_coord[0],
             self.graphics_move_beam_mark_item.end_coord[1])
        self.emit("infoMsg", "")

    def stop_beam_define(self):
        """Stops beam define

        :emits: infoMsg
        """

        QApplication.restoreOverrideCursor()
        self.in_beam_define_state = False
        self.wait_beam_define_click = False
        self.graphics_beam_define_item.hide()
        self.graphics_view.graphics_scene.update()
        self.emit("infoMsg", "")
        self.beam_info_hwobj.set_slits_gap(\
             self.graphics_beam_define_item.width_microns,
             self.graphics_beam_define_item.height_microns)
        self.diffractometer_hwobj.move_to_beam(\
             self.graphics_beam_define_item.center_coord[0],
             self.graphics_beam_define_item.center_coord[1])

    def start_centring(self, tree_click=None):
        """Starts centring procedure
 
        :param tree_click: centring with 3 clicks
        :type tree_click: bool
        :emits: - centringInProgress
                - infoMsg
        """ 
        self.emit("centringInProgress", True)
        if tree_click:
            self.hide_all_items()
            QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
            self.set_centring_state(True) 
            self.diffractometer_hwobj.start_centring_method(\
                 self.diffractometer_hwobj.CENTRING_METHOD_MANUAL)
            self.emit("infoMsg", "3 click centring")
        else: 
            self.diffractometer_hwobj.start_move_to_beam(
                 self.beam_position[0], self.beam_position[1])

    def accept_centring(self):
        """Accepts centring
        """
        self.show_all_items()
        QApplication.restoreOverrideCursor()
        self.diffractometer_hwobj.accept_centring()

    def reject_centring(self):
        """Rejects centring
        """
        self.show_all_items()
        QApplication.restoreOverrideCursor()
        self.diffractometer_hwobj.reject_centring()  

    def cancel_centring(self, reject=False): 
        """Cancels centring

        :param reject: reject position
        :type reject: bool
        """
        self.show_all_items()
        QApplication.restoreOverrideCursor()
        self.diffractometer_hwobj.cancel_centring_method(reject = reject)

    def start_visual_align(self):
        """Starts visual align procedure when two centring points are selected
           Orientates two points along the osc axes

        :emits: infoMsg
        """

        selected_points = self.get_selected_points()
        if len(selected_points) == 2:
            self.diffractometer_hwobj.visual_align(\
                 selected_points[0].get_centred_position(),
                 selected_points[1].get_centred_position())
            self.emit("infoMsg", "Visual align")
        else:
            msg = "Select two centred position (CTRL click) to continue"
            logging.getLogger("user_level_log").error(msg)  

    def create_line(self, start_point=None, end_point=None):
        """Creates helical line if two centring points selected
        """

        selected_points = (start_point, end_point) 
        if None in selected_points:
            selected_points = self.get_selected_points()
        if len(selected_points) > 1:
            line = GraphicsLib.GraphicsItemLine(selected_points[0],
                                                selected_points[1])
            self.add_shape(line)
            return line
        else:
            msg = "Please select two points (with same kappa and phi) " + \
                  "to create a helical line"
            logging.getLogger("GUI").error(msg)

    def create_auto_line(self):
        """Creates a automatic helical line
        """
        point_one_motor_pos = self.diffractometer_hwobj.get_positions()
        point_two_motor_pos = deepcopy(point_one_motor_pos)

        point_one_motor_pos['phiy'] = point_one_motor_pos['phiy'] - 0.1
        cpos_one = queue_model_objects.CentredPosition(point_one_motor_pos)
        point_one = GraphicsLib.GraphicsItemPoint(cpos_one)
        self.add_shape(point_one)
        cpos_one.set_index(point_one.index)

        point_two_motor_pos['phiy'] = point_two_motor_pos['phiy'] + 0.1
        cpos_two = queue_model_objects.CentredPosition(point_two_motor_pos)
        point_two = GraphicsLib.GraphicsItemPoint(cpos_two)
        self.add_shape(point_two)
        cpos_two.set_index(point_two.index)

        line = self.create_line(point_one, point_two)        
        self.diffractometer_state_changed()
        return line

    def create_grid(self, spacing=(0, 0)):
        """Creates grid

        :param spacing: spacing between beams
        :type spacing: list with two floats (can be negative)        
        """ 
        if not self.wait_grid_drawing_click: 
            QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
            self.graphics_grid_draw_item = GraphicsLib.GraphicsItemGrid(self, 
                 self.beam_info_dict, spacing, self.pixels_per_mm)
            self.graphics_grid_draw_item.set_draw_mode(True) 
            self.graphics_grid_draw_item.index = self.grid_count
            self.grid_count += 1
            self.graphics_view.graphics_scene.addItem(self.graphics_grid_draw_item)
            self.wait_grid_drawing_click = True 

    def init_auto_grid(self):
        """Initiates auto grid
        """
        self.auto_grid = GraphicsLib.GraphicsItemGrid(self, 
             self.beam_info_dict, (0, 0), self.pixels_per_mm)
        self.auto_grid.index = - 1
        motor_pos = self.diffractometer_hwobj.get_centred_point_from_coord(\
            self.beam_position[0],
            self.beam_position[1],
            return_by_names=True)
        self.auto_grid.set_centred_position(queue_model_objects.\
            CentredPosition(motor_pos))
        self.auto_grid.hide()
        self.graphics_view.graphics_scene.addItem(self.auto_grid)

    def update_auto_grid(self):
        """Creates automatic grid
        """ 
        self.auto_grid.beam_position = self.beam_position
        motor_pos = self.diffractometer_hwobj.get_centred_point_from_coord(\
            self.beam_position[0], 
            self.beam_position[1],
            return_by_names=True)
        self.auto_grid.set_centred_position(queue_model_objects.\
            CentredPosition(motor_pos))
        self.auto_grid.update_auto_grid(self.auto_grid_size_mm)
        self.auto_grid.show()
        return self.auto_grid

    def update_grid_motor_positions(self, grid_object):
        """Updates grid corner positions
        """
        grid_center_x, grid_center_y = grid_object.get_center_coord()
        motor_pos = self.diffractometer_hwobj.get_centred_point_from_coord(\
            grid_center_x, grid_center_y, return_by_names=True)
        grid_object.set_centred_position(queue_model_objects.\
            CentredPosition(motor_pos))

        motor_pos_corner = []
        for index, corner_coord in enumerate(grid_object.get_corner_coord()):
            motor_pos_corner.append(self.diffractometer_hwobj.\
                 get_centred_point_from_coord(corner_coord.x(),
                                              corner_coord.y(),
                                              return_by_names=True))
        grid_object.set_motor_pos_corner(motor_pos_corner)

    def refresh_camera(self):
        """To be deleted
        """

        self.beam_info_dict = self.beam_info_hwobj.get_beam_info()
        self.beam_info_changed(self.beam_info_dict) 

    def select_lines_and_grids(self):
        """Selects all lines and grids that are in the rectangle of
           item selection tool
        """

        select_start_coord = self.graphics_select_tool_item.start_coord
        select_end_coord = self.graphics_select_tool_item.end_coord
        select_middle_x = (select_start_coord[0] + select_end_coord[0]) / 2.0
        select_middle_y = (select_start_coord[1] + select_end_coord[1]) / 2.0
 
        for shape in self.shape_dict.values():
            if isinstance(shape, GraphicsLib.GraphicsItemLine):
                (start_point, end_point) = shape.get_graphics_points()
                if min(start_point.start_coord[0], 
                       end_point.start_coord[0]) \
                   < select_middle_x  < \
                   max(start_point.start_coord[0], \
                       end_point.start_coord[0]) and \
                   min(start_point.start_coord[1], \
                       end_point.start_coord[1]) < \
                   select_middle_y < \
                   max(start_point.start_coord[1],
                       end_point.start_coord[1]):
                    shape.setSelected(True)

    def get_image_scale_list(self):
        """Returns list with available image scales

        :returns: list with floats
        """ 

        return self.image_scale_list

    def set_image_scale(self, image_scale, use_scale=False):
        """Scales scene
        
        :param image_scale: image scale
        :type image_scale: float 0 - 1.0 
        :param use_scale: enables/disables image scale
        :type use_scale: bool
        :emits: imageScaleChanged
        """
        scene_size = self.graphics_scene_size
        if image_scale == 1:
            use_scale = False
        if use_scale:
            self.image_scale = image_scale
            scene_size = [scene_size[0] * image_scale,
                          scene_size[1] * image_scale]
        else: 
            self.image_scale = 1
        self.graphics_view.graphics_scene.image_scale = self.image_scale
        

        self.graphics_view.scene().setSceneRect(0, 0, \
             scene_size[0] - 10, scene_size[1] - 10)
        self.graphics_view.toggle_scrollbars_enable(self.image_scale > 1)
        self.emit('imageScaleChanged', self.image_scale)

    def get_image_scale(self):
        """Returns current scale factor of image
     
        :returns: float
        """

        return self.image_scale

    def auto_focus(self):
        """Starts auto focus
        """

        self.diffractometer_hwobj.start_auto_focus()

    def start_auto_centring(self):
        """Starts auto centring
        """
        #self.display_info_msg(["Auto centring in progress...",
        #                       "Please wait."])
        self.emit("centringInProgress", True)
        self.diffractometer_hwobj.start_centring_method(\
             self.diffractometer_hwobj.CENTRING_METHOD_AUTO, wait=True)
        self.emit("infoMsg", "Automatic centring")

    def move_beam_mark_auto(self):
        """Automatic procedure detects beam positions and updates
           beam info.
        """
 
        beam_shape_dict = self.detect_object_shape()
        self.beam_info_hwobj.set_beam_position(\
             beam_shape_dict["center"][0],
             beam_shape_dict["center"][1])

    def detect_object_shape(self):
        """Method used to detect a shape on the image.
           It is used to detect beam shape and loop       
        returns: dictionary with parameters:
                 - center: list with center coordinates
                 - width: estimated beam width
                 - height: estimated beam height 
        """

        object_shape_dict = {"center" : (0, 0),
                             "width": -1,
                             "height": -1}
        image_array = self.camera_hwobj.get_snapshot(bw=True, return_as_array=True)
        image_array[image_array < 120] = 0
        #image_array[image_array > 120] = 1

        hor_sum = image_array.sum(axis=0)
        ver_sum = image_array.sum(axis=1)

        try:
            half_max = hor_sum.max() / 2.0
            s = splrep(np.linspace(0, hor_sum.size, hor_sum.size), hor_sum - half_max)
            hor_roots = sproot(s)

            half_max = ver_sum.max() / 2.0
            s = splrep(np.linspace(0, ver_sum.size, ver_sum.size), ver_sum - half_max)
            ver_roots = sproot(s)

            if len(hor_roots) and len(ver_roots):
                object_shape_dict["width"] = int(hor_roots[-1] - hor_roots[0])
                object_shape_dict["height"] = int(ver_roots[-1] - ver_roots[0])
        except:
            logging.getLogger("user_level_log").debug("Qt4_GraphicsManager: " +\
                "Unable to detect object shape")

        try:
            image_array = np.transpose(image_array)
            beam_x, beam_y = ndimage.measurements.\
                center_of_mass(image_array)
            #(beam_x, beam_y) = np.unravel_index(np.argmax(image_array), image_array.shape)
            if np.isnan(beam_x) or np.isnan(beam_y):
                beam_x = None
                beam_y = None
            object_shape_dict["center"] = (beam_x, beam_y)
        except:
            logging.getLogger("user_level_log").debug("Qt4_GraphicsManager: " +\
                "Unable to detect image center of mass")
        return object_shape_dict

    def get_beam_displacement(self, reference=None):
        """Calculates beam displacement:
           - detects beam shape. If no shape detected returns (None, None)
           - if beam detected then calculates the displacement in mm 
        """
        beam_shape_dict = self.detect_object_shape()
        if None or 0 in beam_shape_dict['center'] or \
           beam_shape_dict['width'] == -1 or \
           beam_shape_dict['height'] == -1:
            return (None, None)
        else:
            if reference == "beam": 
                return ((self.beam_position[0] - beam_shape_dict['center'][0]) /\
                         self.pixels_per_mm[0],
                        (self.beam_position[1] - beam_shape_dict['center'][1]) / \
                         self.pixels_per_mm[1])
            else: 
                return ((682 - beam_shape_dict['center'][0]) / self.pixels_per_mm[0],
                        (501 - beam_shape_dict['center'][1]) / self.pixels_per_mm[1])

    def display_grid(self, state):
        """
        Descript.
        """
        self.graphics_scale_item.set_display_grid(state) 

    def create_automatic_line(self):
        """
        Descript.
        """
        pass 

    def set_display_overlay(self, state):
        """Enables or disables beam shape drawing for graphics scene
           items (lines and grids)

        """
        for shape in self.get_shapes():
            if isinstance(shape, GraphicsLib.GraphicsItemLine):
                shape.set_beam_info(self.beam_info_dict)
                shape.set_pixels_per_mm(self.pixels_per_mm)
                shape.set_display_overlay(state > 0)

    def display_info_msg(self, msg, pos_x=None, pos_y=None, hide_msg=True):
        """
        Descript.
        """
        if pos_x is None:
            pos_x = 10
            #pos_x = self.beam_position[0]
        if pos_y is None:
            pos_y = 50
            #pos_y = self.beam_position[1]
        self.graphics_info_item.display_info(msg, pos_x, pos_y, hide_msg) 

    def hide_info_msg(self):
        self.graphics_info_item.hide()

    def swap_line_points(self, line):
        (point_start, point_end) = line.get_graphical_points()
        line.set_graphical_points(point_end, point_start)
        self.emit("shapeChanged", line, "Line")
        line.update_item()

    def display_beam_size(self, state):
        """Enables or disables displaying the beam size"""
        self.graphics_beam_item.enable_beam_size(state) 

    def set_magnification_mode(self, mode):
        if mode:
            QApplication.setOverrideCursor(QCursor(Qt.ClosedHandCursor))
        else:
            QApplication.restoreOverrideCursor()
        self.graphics_magnification_item.setVisible(mode)
        self.in_magnification_mode = mode 
