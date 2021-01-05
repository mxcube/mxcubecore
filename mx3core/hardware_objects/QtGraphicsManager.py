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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
Qt4/5/PySide Graphics manager for MxCuBE.
Hardware object handles QGraphicsView and QGraphicsScene with all
objects and actions necessary for MXCuBE:
- Creating/removing/editing/drawing of centring points, collection vectors
  and 2D grids
- Display of beam shape, rotatio axis, scales
- Distance, angle and area measurement tools
- Video handling, scalling and magnification tools

example xml:
<object class="QtGraphicsManager">
   <object href="/mini-diff-mockup" role="diffractometer"/>
   <object href="/beam-info" role="beam_info"/>
   <object href="/Qtvideo-mockup" role="camera"/>

   <magnification_tool>{"scale": 4, "area_size": 50}</magnification_tool>
</object>
"""

from __future__ import print_function
import os
import math
import logging

try:
    import cPickle as pickle
except Exception:
    import _pickle as pickle

from datetime import datetime
from copy import deepcopy

import gevent
import numpy as np
from scipy import ndimage, interpolate, signal

from matplotlib import cm
import matplotlib.pyplot as plt

try:
    import lucid2 as lucid
except ImportError:
    try:
        import lucid
    except ImportError:
        pass

from gui.utils import QtImport

from mx3core.hardware_objects import queue_model_objects
from mx3core.hardware_objects import QtGraphicsLib as GraphicsLib
from mx3core.hardware_objects.abstract.AbstractSampleView import (
    AbstractSampleView,
)

from mx3core import HardwareRepository as HWR

__credits__ = ["MXCuBE collaboration"]
__category__ = "Graphics"


class QtGraphicsManager(AbstractSampleView):
    def __init__(self, name):
        """
        :param name: name
        :type name: str
        """
        AbstractSampleView.__init__(self, name)

        self.diffractometer_hwobj = None

        self.graphics_config_filename = None
        self.omega_angle = 0
        self.pixels_per_mm = [0, 0]
        self.beam_position = [0, 0]
        self.beam_info_dict = {}
        self.graphics_scene_size = None
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
        self.in_one_click_centering = None
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
        self.temp_animation_dir = None
        self.omega_move_delta = None
        self.cursor = None

        self.graphics_view = None
        self.graphics_camera_frame = None
        self.graphics_beam_item = None
        self.graphics_info_item = None
        self.graphics_scale_item = None
        self.graphics_omega_reference_item = None
        self.graphics_centring_lines_item = None
        self.graphics_histogram_item = None
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
        self.graphics_view.setVerticalScrollBarPolicy(QtImport.Qt.ScrollBarAsNeeded)
        self.graphics_view.setHorizontalScrollBarPolicy(QtImport.Qt.ScrollBarAsNeeded)
        self.graphics_camera_frame = GraphicsLib.GraphicsCameraFrame()
        self.graphics_scale_item = GraphicsLib.GraphicsItemScale(self)
        self.graphics_histogram_item = GraphicsLib.GraphicsItemHistogram(self)
        self.graphics_histogram_item.hide()
        self.graphics_omega_reference_item = GraphicsLib.GraphicsItemOmegaReference(
            self
        )
        self.graphics_beam_item = GraphicsLib.GraphicsItemBeam(self)
        self.graphics_info_item = GraphicsLib.GraphicsItemInfo(self)
        self.graphics_info_item.hide()
        self.graphics_move_beam_mark_item = GraphicsLib.GraphicsItemMoveBeamMark(self)
        self.graphics_move_beam_mark_item.hide()
        self.graphics_centring_lines_item = GraphicsLib.GraphicsItemCentringLines(self)
        self.graphics_centring_lines_item.hide()
        self.graphics_measure_distance_item = GraphicsLib.GraphicsItemMeasureDistance(
            self
        )
        self.graphics_measure_distance_item.hide()

        self.graphics_measure_angle_item = GraphicsLib.GraphicsItemMeasureAngle(self)
        self.graphics_measure_angle_item.hide()
        self.graphics_measure_area_item = GraphicsLib.GraphicsItemMeasureArea(self)
        self.graphics_measure_area_item.hide()
        self.graphics_select_tool_item = GraphicsLib.GraphicsSelectTool(self)
        self.graphics_select_tool_item.hide()
        self.graphics_beam_define_item = GraphicsLib.GraphicsItemBeamDefine(self)
        self.graphics_beam_define_item.hide()
        self.graphics_magnification_item = GraphicsLib.GraphicsMagnificationItem(self)
        self.graphics_magnification_item.hide()

        self.graphics_view.graphics_scene.addItem(self.graphics_camera_frame)
        self.graphics_view.graphics_scene.addItem(self.graphics_omega_reference_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_beam_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_info_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_move_beam_mark_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_centring_lines_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_histogram_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_scale_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_measure_distance_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_measure_angle_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_measure_area_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_select_tool_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_beam_define_item)
        self.graphics_view.graphics_scene.addItem(self.graphics_magnification_item)

        self.graphics_view.scene().mouseClickedSignal.connect(self.mouse_clicked)
        self.graphics_view.scene().mouseDoubleClickedSignal.connect(
            self.mouse_double_clicked
        )
        self.graphics_view.scene().mouseReleasedSignal.connect(self.mouse_released)
        self.graphics_view.scene().itemClickedSignal.connect(self.item_clicked)
        self.graphics_view.scene().itemDoubleClickedSignal.connect(
            self.item_double_clicked
        )
        self.graphics_view.scene().moveItemClickedSignal.connect(self.move_item_clicked)
        # self.graphics_view.scene().gridClickedSignal.connect(self.grid_clicked)

        self.graphics_view.mouseMovedSignal.connect(self.mouse_moved)
        self.graphics_view.keyPressedSignal.connect(self.key_pressed)
        self.graphics_view.wheelSignal.connect(self.mouse_wheel_scrolled)

        self.diffractometer_hwobj = self.get_object_by_role("diffractometer")
        self.graphics_view.resizeEvent = self.resizeEvent

        if self.diffractometer_hwobj is not None:
            pixels_per_mm = self.diffractometer_hwobj.get_pixels_per_mm()
            self.diffractometer_pixels_per_mm_changed(pixels_per_mm)
            GraphicsLib.GraphicsItemGrid.set_grid_direction(
                self.diffractometer_hwobj.get_grid_direction()
            )

            self.connect(
                self.diffractometer_hwobj,
                "minidiffStateChanged",
                self.diffractometer_state_changed,
            )
            self.connect(
                self.diffractometer_hwobj,
                "centringStarted",
                self.diffractometer_centring_started,
            )
            self.connect(
                self.diffractometer_hwobj,
                "centringAccepted",
                self.create_centring_point,
            )
            self.connect(
                self.diffractometer_hwobj,
                "centringSuccessful",
                self.diffractometer_centring_successful,
            )
            self.connect(
                self.diffractometer_hwobj,
                "centringFailed",
                self.diffractometer_centring_failed,
            )
            self.connect(
                self.diffractometer_hwobj,
                "pixelsPerMmChanged",
                self.diffractometer_pixels_per_mm_changed,
            )
            self.connect(
                self.diffractometer_hwobj,
                "omegaReferenceChanged",
                self.diffractometer_omega_reference_changed,
            )
            self.connect(
                self.diffractometer_hwobj,
                "phiMotorMoved",
                self.diffractometer_phi_motor_moved,
            )
            self.connect(
                self.diffractometer_hwobj,
                "minidiffPhaseChanged",
                self.diffractometer_phase_changed,
            )
        else:
            logging.getLogger("HWR").error(
                "GraphicsManager: Diffractometer hwobj not defined"
            )

        if HWR.beamline.beam is not None:
            self.beam_info_dict = HWR.beamline.beam.get_beam_info_dict()
            self.beam_position = HWR.beamline.beam.get_beam_position_on_screen()
            self.connect(
                HWR.beamline.beam, "beamPosChanged", self.beam_position_changed
            )
            self.connect(HWR.beamline.beam, "beamInfoChanged", self.beam_info_changed)

            self.beam_info_changed(self.beam_info_dict)
            self.beam_position_changed(HWR.beamline.beam.get_beam_position_on_screen())
        else:
            logging.getLogger("HWR").error(
                "GraphicsManager: BeamInfo hwobj not defined"
            )

        self.camera_hwobj = self.get_object_by_role(
            self.get_property("camera_name", "camera")
        )
        if self.camera_hwobj is not None:
            graphics_scene_size = self.camera_hwobj.get_image_dimensions()
            self.set_graphics_scene_size(graphics_scene_size, False)
            self.camera_hwobj.start_camera()
            self.connect(self.camera_hwobj, "imageReceived", self.camera_image_received)
        else:
            logging.getLogger("HWR").error("GraphicsManager: Camera hwobj not defined")

        try:
            self.image_scale_list = eval(self.get_property("image_scale_list", "[]"))
            if len(self.image_scale_list) > 0:
                self.image_scale = self.get_property("default_image_scale")
                self.set_image_scale(self.image_scale, self.image_scale is not None)
        except Exception:
            pass

        """
        if self.get_property("store_graphics_config") == True:
            #atexit.register(self.save_graphics_config)
            self.graphics_config_filename = self.get_property("graphics_config_filename")
            if self.graphics_config_filename is None:
                self.graphics_config_filename = os.path.join(
                    self.user_file_directory,
                    "graphics_config.dat")
            self.load_graphics_config()
        """

        try:
            self.auto_grid_size_mm = eval(self.get_property("auto_grid_size_mm"))
        except Exception:
            self.auto_grid_size_mm = (0.1, 0.1)

        """
        self.graphics_move_up_item.setVisible(
            self.get_property("enable_move_buttons") is True
        )
        self.graphics_move_right_item.setVisible(
            self.get_property("enable_move_buttons") is True
        )
        self.graphics_move_down_item.setVisible(
            self.get_property("enable_move_buttons") is True
        )
        self.graphics_move_left_item.setVisible(
            self.get_property("enable_move_buttons") is True
        )
        """

        # self.set_scrollbars_off(\
        #     self.get_property("scrollbars_always_off") is True)

        try:
            self.graphics_magnification_item.set_properties(
                eval(self.get_property("magnification_tool"))
            )
        except Exception:
            pass

        # try:
        #    self.set_view_scale(self.get_property("view_scale"))
        # except:
        #    pass

        # self.temp_animation_dir = os.path.join(self.user_file_directory, "animation")

        self.omega_move_delta = self.get_property("omega_move_delta", 10)

        custom_cursor_filename = self.get_property("custom_cursor", "")
        if os.path.exists(custom_cursor_filename):
            self.cursor = QtImport.QCursor(
                QtImport.QPixmap(custom_cursor_filename), 0, 0
            )
            self.set_cursor_busy(False)
        else:
            self.cursor = QtImport.Qt.ArrowCursor

    @property
    def zoom(self):
        """zoom motor object

        NBNB HACK TODO - configure this here instead
        (instead of calling to diffractometer)

        Returns:
            AbstractActuator
        """
        return self.diffractometer_hwobj.zoom

    @property
    def focus(self):
        """focus motor object

        NBNB HACK TODO - configure this here instead
        (instead of calling to diffractometer)

        Returns:
            AbstractActuator
        """
        return self.diffractometer_hwobj.alignment_x

    @property
    def camera(self):
        """camera object

        NBNB TODO clean up and simplify configuration

        Returns:
            AbstractActuator
        """
        return self.camera_hwobj

    def add_shape_from_mpos(self, mpos_list, screen_cord, _type):
        """
        Adds a shape of type <t>, with motor positions from mpos_list and
        screen position screen_coord.

        Args:
            mpos_list (list[mpos_list]): List of motor positions
            screen_coord (tuple(x, y): Screen cordinate for shape
            t (str): Type str for shape, P (Point), L (Line), G (Grid)

        Returns:
            (Shape) Shape of type <t>
        """
        return

    def de_select_shape(self, sid):
        """
        De-select the shape with id <sid>.

        Args:
            sid (str): The id of the shape to de-select.
        """
        return

    def clear_all(self):
        """
        Clear the shapes, remove all contents.
        """
        return

    def de_select_all(self):
        """De select all shapes."""
        return

    def get_shape(self, sid):
        """
        Get Shape with id <sid>.

        Args:
            sid (str): id of Shape to retrieve

        Returns:
            (Shape) All the shapes
        """
        return

    def get_grid(self):
        """
        Get the first of the selected grids, (the one that was selected first in
        a sequence of select operations)

        Returns:
            (dict): The first selected grid as a dictionary
        """
        return

    def get_lines(self):
        """
        Get all Lines currently handled.

        Returns:
            (list[Line]): All lines currently handled
        """
        return

    def get_grids(self):
        """
        Get all Grids currently handled.

        Returns:
            (list[Grid]): All grids currently handled
        """
        return

    def is_selected(self, sid):
        """
        Check if Shape with <sid> is selected.

        Returns:
            (Boolean) True if Shape with <sid> is selected False otherwise
        """
        return

    def save_graphics_config(self):
        """Saves graphical objects in the file
        """

        return
        """
        graphics_config_file.write(pickle.dumps(self.dump_shapes()))
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
        """

    def load_graphics_config(self):
        """Loads graphics from file
        """
        if os.path.exists(self.graphics_config_filename):
            try:
                logging.getLogger("HWR").debug(
                    "GraphicsManager: Loading graphics "
                    + "from configuration file %s" % self.graphics_config_filename
                )
                graphics_config_file = open(self.graphics_config_filename)
                graphics_config = eval(graphics_config_file.read())
                for graphics_item in graphics_config:
                    if graphics_item["type"] == "point":
                        point = self.create_centring_point(
                            None, {"motors": graphics_item["cpos"]}
                        )
                        point.index = graphics_item["index"]
                        cpos = point.get_centred_position()
                        cpos.set_index(graphics_item["cpos_index"])
                for graphics_item in graphics_config:
                    if graphics_item["type"] == "line":
                        start_point = self.get_point_by_index(
                            graphics_item["start_point_index"]
                        )
                        end_point = self.get_point_by_index(
                            graphics_item["end_point_index"]
                        )
                        self.create_line(start_point, end_point)
                self.de_select_all()
                graphics_config_file.close()
            except Exception:
                logging.getLogger("HWR").error(
                    "GraphicsManager: Unable to load "
                    + "graphics from configuration file %s"
                    % self.graphics_config_filename
                )

    def dump_shapes(self):
        graphics_config = []
        for shape in self.get_shapes():
            if isinstance(shape, GraphicsLib.GraphicsItemPoint):
                cpos = shape.get_centred_position()
                graphics_config.append(
                    {
                        "type": "point",
                        "index": shape.index,
                        "pos_x": shape.start_coord,
                        "pos_y": shape.end_coord,
                        "cpos": cpos.as_dict(),
                        "cpos_index": cpos.get_index(),
                    }
                )
            elif isinstance(shape, GraphicsLib.GraphicsItemLine):
                (start_point_index, end_point_index) = shape.get_points_index()
                graphics_config.append(
                    {
                        "type": "line",
                        "index": shape.index,
                        "start_point_index": start_point_index,
                        "end_point_index": end_point_index,
                    }
                )

        return graphics_config

    def load_shapes(self, graphics_config):
        for graphics_item in graphics_config:
            if graphics_item["type"] == "point":
                point = self.create_centring_point(
                    None, {"motors": graphics_item["cpos"]}, emit=False
                )
                point.index = graphics_item["index"]
                cpos = point.get_centred_position()
                cpos.set_index(graphics_item["cpos_index"])
        for graphics_item in graphics_config:
            if graphics_item["type"] == "line":
                start_point = self.get_point_by_index(
                    graphics_item["start_point_index"]
                )
                end_point = self.get_point_by_index(graphics_item["end_point_index"])
                self.create_line(start_point, end_point, emit=False)
        self.de_select_all()

    def camera_image_received(self, pixmap_image, msg=None):
        """Method called when a frame from camera arrives.
           Slot to signal 'imageReceived'

        :param pixmap_image: frame from camera
        :type pixmap_image: QtGui.QPixmapImage
        """
        if pixmap_image:
            if self.image_scale:
                pixmap_image = pixmap_image.scaled(
                    QtImport.QSize(
                        pixmap_image.width() * self.image_scale,
                        pixmap_image.height() * self.image_scale,
                    )
                )
            self.graphics_camera_frame.setPixmap(pixmap_image)

            if self.in_magnification_mode:
                self.graphics_magnification_item.set_pixmap(pixmap_image)
        else:
            self.display_info_msg(msg, 10, 500, False)

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
        if self.diffractometer_hwobj.is_ready() and not self.in_centring_state:
            for shape in self.get_shapes():
                if isinstance(shape, GraphicsLib.GraphicsItemPoint):
                    cpos = shape.get_centred_position()
                    new_x, new_y = self.diffractometer_hwobj.motor_positions_to_screen(
                        cpos.as_dict()
                    )
                    shape.set_start_position(new_x, new_y)
                elif isinstance(shape, GraphicsLib.GraphicsItemGrid):
                    grid_cpos = shape.get_centred_position()
                    if grid_cpos is not None:
                        current_cpos = queue_model_objects.CentredPosition(
                            self.diffractometer_hwobj.get_positions()
                        )

                        current_cpos.set_motor_pos_delta(0.1)
                        grid_cpos.set_motor_pos_delta(0.1)

                        if hasattr(grid_cpos, "zoom"):
                            current_cpos.zoom = grid_cpos.zoom

                        center_coord = self.diffractometer_hwobj.motor_positions_to_screen(
                            grid_cpos.as_dict()
                        )
                        if center_coord:
                            shape.set_center_coord(center_coord)

                            corner_coord = []
                            for motor_pos in shape.get_motor_pos_corner():
                                corner_coord.append(
                                    (
                                        self.diffractometer_hwobj.motor_positions_to_screen(
                                            motor_pos
                                        )
                                    )
                                )
                            shape.set_corner_coord(corner_coord)

                            if current_cpos == grid_cpos:
                                shape.set_projection_mode(False)
                            else:
                                shape.set_projection_mode(True)

            self.show_all_items()
            self.graphics_view.graphics_scene.update()
            # self.update_histogram()
            self.emit("diffractometerReady", True)
        else:
            self.hide_all_items()
            self.emit("diffractometerReady", False)

    def resizeEvent(self, event):
        GraphicsLib.GraphicsView.resizeEvent(self.graphics_view, event)
        if self.graphics_view.verticalScrollBar().isVisible():
            self.graphics_scale_item.set_anchor(GraphicsLib.GraphicsItemScale.UPPER_LEFT)
        else:
            self.graphics_scale_item.set_anchor(GraphicsLib.GraphicsItemScale.LOWER_LEFT)
        self.graphics_view.update()
 
    def diffractometer_phase_changed(self, phase):
        """Phase changed event.
           If PHASE_BEAM then displays a grid on the screen
        """
        self.graphics_scale_item.set_display_grid(
            phase == self.diffractometer_hwobj.PHASE_BEAM
        )
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
        self.set_centring_state(True)
        self.emit("centringStarted")

    def create_centring_point(self, centring_state, centring_status, emit=True):
        """Creates a new centring position and adds it to graphics point.

        :param centring_state:
        :type centring_state: str
        :param centring_status: dictionary with motor pos and etc
        :type centring_status: dict
        :emits: centringInProgress
        """
        p_dict = {}

        if "motors" in centring_status and "extraMotors" in centring_status:

            p_dict = dict(centring_status["motors"], **centring_status["extraMotors"])
        elif "motors" in centring_status:
            p_dict = dict(centring_status["motors"])

        self.emit("centringInProgress", False)

        if p_dict:
            cpos = queue_model_objects.CentredPosition(p_dict)
            screen_pos = self.diffractometer_hwobj.motor_positions_to_screen(
                cpos.as_dict()
            )
            point = GraphicsLib.GraphicsItemPoint(
                cpos, True, screen_pos[0], screen_pos[1]
            )
            self.add_shape(point, emit)
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
        self.set_cursor_busy(False)
        self.set_centring_state(False)
        self.diffractometer_state_changed()
        self.emit("centringSuccessful", method, centring_status)
        self.emit(
            "infoMsg",
            "Click Save to store the centred point " + "or start a new centring",
        )

        gevent.spawn_later(2, self.save_crystal_image)

    def save_crystal_image(self):
        try:
            raw_snapshot = self.get_raw_snapshot()
            result_image = raw_snapshot.copy(
                self.beam_position[0]
                - self.beam_info_dict["size_x"] * self.pixels_per_mm[0] / 2,
                self.beam_position[1]
                - self.beam_info_dict["size_y"] * self.pixels_per_mm[1] / 2,
                self.beam_info_dict["size_x"] * self.pixels_per_mm[0] * 1.5,
                self.beam_info_dict["size_y"] * self.pixels_per_mm[1] * 1.5,
            )
            date_time_str = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            result_image.save("/opt/embl-hh/var/crystal_images/%s.png" % date_time_str)
        except Exception:
            pass

    def diffractometer_centring_failed(self, method, centring_status):
        """CleanUp method after centring failed

        :param method: method name
        :type method: str
        :param centring_status: centring status
        :type centring_status: dict
        :emits: - centringFailed
                - infoMsg
        """
        self.set_cursor_busy(False)
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
        self.omega_angle = position
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
            self.graphics_grid_draw_item.set_start_position(pos_x, pos_y)
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
            # self.graphics_beam_define_item.store_coord(pos_x, pos_y)
        elif self.in_one_click_centering:
            self.diffractometer_hwobj.start_move_to_beam(pos_x, pos_y)
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
                if type(graphics_item) in [
                    GraphicsLib.GraphicsItemPoint,
                    GraphicsLib.GraphicsItemLine,
                    GraphicsLib.GraphicsItemGrid,
                ]:
                    self.emit("shapeSelected", graphics_item, False)
                    # if isinstance(graphics_item, GraphicsLib.GraphicsItemPoint):
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
        self.emit("imageDoubleClicked", pos_x, pos_y)

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
            self.set_cursor_busy(False)
            self.update_grid_motor_positions(self.graphics_grid_draw_item)
            self.graphics_grid_draw_item.set_draw_mode(False)
            self.wait_grid_drawing_click = False
            self.in_grid_drawing_state = False
            self.de_select_all()
            self.emit("shapeCreated", self.graphics_grid_draw_item, "Grid")
            self.graphics_grid_draw_item.setSelected(True)
            self.graphics_grid_draw_item.update_coordinate_map()
            # self._shapes.add_shape(self.graphics_grid_draw_item.get_display_name(),
            #                       self.graphics_grid_draw_item
            # )
            self.shape_dict[
                self.graphics_grid_draw_item.get_display_name()
            ] = self.graphics_grid_draw_item
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

        # need to distinguish between View and Scene coordinates.
        # moved_mouse connected to graphics_view's mouseMovedSignal
        # I think we need Scene's coordinates here:
        scene_point = self.graphics_view.mapToScene(QtImport.QPoint(pos_x, pos_y))
        self.emit("mouseMoved", scene_point.x(), scene_point.y())
        self.mouse_position[0] = scene_point.x()
        self.mouse_position[1] = scene_point.y()
        if self.in_centring_state or self.in_one_click_centering:
            self.graphics_centring_lines_item.set_start_position(
                scene_point.x(), scene_point.y()
            )
        elif self.in_grid_drawing_state:
            if self.graphics_grid_draw_item.is_draw_mode():
                self.graphics_grid_draw_item.set_end_position(
                    scene_point.x(), scene_point.y()
                )
        elif self.in_measure_distance_state:
            self.graphics_measure_distance_item.set_coord(self.mouse_position)
        elif self.in_measure_angle_state:
            self.graphics_measure_angle_item.set_coord(self.mouse_position)
        elif self.in_measure_area_state:
            self.graphics_measure_area_item.set_coord(self.mouse_position)
        elif self.in_move_beam_mark_state:
            self.graphics_move_beam_mark_item.set_end_position(
                self.mouse_position[0], self.mouse_position[1]
            )
        elif self.in_beam_define_state:
            self.graphics_beam_define_item.set_end_position(
                self.mouse_position[0], self.mouse_position[1]
            )
        elif self.in_select_items_state:

            self.graphics_select_tool_item.set_end_position(
                scene_point.x(), scene_point.y()
            )
            select_start_x = self.graphics_select_tool_item.start_coord[0]
            select_start_y = self.graphics_select_tool_item.start_coord[1]
            if (
                abs(select_start_x - scene_point.x()) > 5
                and abs(select_start_y - scene_point.y()) > 5
            ):
                painter_path = QtImport.QPainterPath()
                painter_path.addRect(
                    min(select_start_x, scene_point.x()),
                    min(select_start_y, scene_point.y()),
                    abs(select_start_x - scene_point.x()),
                    abs(select_start_y - scene_point.y()),
                )
                self.graphics_view.graphics_scene.setSelectionArea(painter_path)
                """
                for point in self.get_points():
                    if point.isSelected():
                        self.emit("pointSelected", point)
                self.select_lines_and_grids()
                """
        elif self.in_magnification_mode:
            self.graphics_magnification_item.set_end_position(
                scene_point.x(), scene_point.y()
            )

        # TODO add grid commands
        # else:
        #    for shape in self.get_selected_shapes():
        #        if isinstance(shape, GraphicsLib.GraphicsItemGrid):
        #            print(shape)

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
            self.stop_one_click_centring()
            if self.in_beam_define_state:
                self.stop_beam_define()
            if self.in_magnification_mode:
                self.set_magnification_mode(False)
            self.in_move_beam_mark_state = False
            self.graphics_move_beam_mark_item.hide()
            # self.graphics_beam_item.set_detected_beam_position(None, None)

        # elif key_event == "Up":
        #    self.diffractometer_hwobj.move_to_beam(self.beam_position[0],
        #                                           self.beam_position[1] - 50)
        # elif key_event == "Down":
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
            self.diffractometer_hwobj.move_omega_relative(self.omega_move_delta)
        else:
            self.diffractometer_hwobj.move_omega_relative(-self.omega_move_delta)

    def item_clicked(self, item, state):
        """Item clicked event

        :param item: clicked item
        :type item: QGraphicsLib.GraphicsItem
        :param state: selection state
        :type state: bool
        :emits: - pointsSelected
                - infoMsg
        """
        if type(item) in [
            GraphicsLib.GraphicsItemPoint,
            GraphicsLib.GraphicsItemLine,
            GraphicsLib.GraphicsItemGrid,
        ]:
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
            self.diffractometer_hwobj.move_to_centred_position(
                item.get_centred_position()
            )

    def move_item_clicked(self, direction):
        """Moves sample
        """
        # TODO Not implemented yet
        print("Move screen: ", direction)

    def grid_clicked(self, grid, image, line, image_num):
        self.emit("gridClicked", (grid, image, line, image_num))

    def set_cursor_busy(self, state):
        return
        if state:
            QtImport.QApplication.setOverrideCursor(
                QtImport.QCursor(QtImport.Qt.BusyCursor)
            )
        else:
            QtImport.QApplication.setOverrideCursor(self.cursor)

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
            # self.graphics_view.setFixedSize(size[0] + 2, size[1] + 2)

    def set_centring_state(self, state):
        """Sets centrin state

        :param state: centring state
        :type state: bool
        """
        self.in_centring_state = state
        self.graphics_centring_lines_item.setVisible(state)
        self.graphics_centring_lines_item.centring_points = []
        if not state:
            self.set_cursor_busy(False)

    def get_shapes(self):
        """Returns currently handled shapes.

        :returns: list with shapes
        """
        shapes_list = []
        for shape in self.graphics_view.graphics_scene.items():
            if type(shape) in (
                GraphicsLib.GraphicsItemPoint,
                GraphicsLib.GraphicsItemLine,
                GraphicsLib.GraphicsItemGrid,
            ):
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
        :returns: QtGraphicsLib.GraphicsPoint
        """
        for point in self.get_points():
            if point.index == index:
                return point

    def add_shape(self, shape, emit=True):
        """Adds the shape <shape> to the list of handled objects.

        :param shape: Shape to add.
        :type shape: Shape object.
        :emits: shapeSelected
        """
        self.de_select_all()
        if isinstance(shape, GraphicsLib.GraphicsItemPoint):
            self.point_count += 1
            shape.index = self.point_count
        elif isinstance(shape, GraphicsLib.GraphicsItemLine):
            self.line_count += 1
            shape.index = self.line_count
        self.shape_dict[shape.get_display_name()] = shape
        # self._shapes.add_shape(shape.get_display_name(), shape)
        self.graphics_view.graphics_scene.addItem(shape)

        if isinstance(shape, GraphicsLib.GraphicsItemPoint):
            if emit:
                self.emit("shapeCreated", shape, "Point")
            self.emit("pointSelected", shape)
            self.emit("infoMsg", "Centring %s created" % shape.get_full_name())
        elif isinstance(shape, GraphicsLib.GraphicsItemLine):
            if emit:
                self.emit("shapeCreated", shape, "Line")
            self.emit("infoMsg", "%s created" % shape.get_full_name())

        shape.set_tool_tip()
        shape.setSelected(True)
        self.emit("shapeSelected", shape, True)

    def delete_shape(self, shape):
        """Removes the shape <shape> from the list of handled shapes.

        :param shape: The shape to remove
        :type shape: GraphicsLib.GraphicsItem object
        :emits: shapeDeleted
        """
        if isinstance(shape, GraphicsLib.GraphicsItemPoint):
            for s in self.get_shapes():
                if isinstance(s, GraphicsLib.GraphicsItemLine):
                    if shape in s.get_graphical_points():
                        self.delete_shape(s)
                        break
        shape_type = ""
        if isinstance(shape, GraphicsLib.GraphicsItemPoint):
            shape_type = "Point"
        elif isinstance(shape, GraphicsLib.GraphicsItemLine):
            shape_type = "Line"
        elif isinstance(shape, GraphicsLib.GraphicsItemGrid):
            shape_type = "Grid"

        self.graphics_view.graphics_scene.removeItem(shape)
        self.graphics_view.graphics_scene.update()
        self.emit("shapeDeleted", shape, shape_type)

    def get_shape_by_name(self, shape_name):
        """Returns shape by name

        :param shape_name: name of the shape
        :type shape_name: str
        :returns: GraphicsLib.GraphicsItem
        """
        return self.shape_dict.get(shape_name)
        # self._shapes.get_shape_by_name(shape_name)

    def clear_all_shapes(self):
        """Clear the shape history, remove all contents.
        """
        self.point_count = 0
        self.line_count = 0
        self.grid_count = 0
        for shape in self.get_shapes():
            if shape == self.auto_grid:
                shape.hide()
            else:
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
        # self.graphics_view.graphics_scene.update()

    def get_selected_shapes(self):
        """Returns selected shapes

        :returns: list with GraphicsLib.GraphicsItem
        """

        selected_shapes = []
        for item in self.graphics_view.graphics_scene.items():
            if (
                type(item)
                in (
                    GraphicsLib.GraphicsItemPoint,
                    GraphicsLib.GraphicsItemLine,
                    GraphicsLib.GraphicsItemGrid,
                )
                and item.isSelected()
            ):
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
        return sorted(selected_points, key=lambda x: x.index, reverse=False)

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

    def inc_used_for_collection(self, cpos):
        for shape in self.get_points():
            if shape.get_centred_position() == cpos:
                shape.used_count += 1

    def set_shape_tooltip(self, cpos, tooltip):
        for shape in self.get_points():
            if shape.get_centred_position() == cpos:
                shape.set_tool_tip(tooltip)

    def get_scene_snapshot(self, shape=None, bw=None, return_as_array=None):
        """Takes a snapshot of the scene

        :param shape: shape that needs to be selected
        :type shape: GraphicsLib.GraphicsItem
        :returns: QImage
        """
        if shape:
            self.hide_all_items()
            # self.de_select_all()
            shape.show()
            # shape.setSelected(True)
            # self.select_shape_with_cpos(shape.get_centred_position())
        # self.graphics_omega_reference_item.hide()

        image = QtImport.QImage(
            self.graphics_view.graphics_scene.sceneRect().size().toSize(),
            QtImport.QImage.Format_ARGB32,
        )
        image.fill(QtImport.Qt.transparent)
        image_painter = QtImport.QPainter(image)
        self.graphics_view.render(image_painter)
        image_painter.end()
        self.show_all_items()
        self.graphics_omega_reference_item.show()
        if return_as_array:
            ptr = image.bits()
            ptr.setsize(image.byteCount())
            return np.array(ptr).reshape(image.height(), image.width(), 4)
        else:
            return image

    def save_scene_snapshot(self, filename):
        """Method to save snapshot

        :param file_name: file name
        :type file_name: str
        """
        logging.getLogger("HWR").debug("Saving scene snapshot: %s" % filename)
        try:
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            snapshot = self.get_scene_snapshot()
            snapshot.save(filename)

            if not os.path.exists(filename):
                raise Exception("Unable to save snapshot to %s" % filename)
        except Exception:
            logging.getLogger("user_level_log").error(
                "Unable to save snapshot: %s" % filename
            )

    def save_scene_animation(self, filename, duration_sec=1):
        """Saves animated gif of a rotating sample"""
        """Save animation task"""

        # self.diffractometer_hwobj.set_ready(False)
        gevent.spawn(self.diffractometer_hwobj.move_omega_relative, 180)
        gevent.spawn(self.save_scene_animation_task, filename, duration_sec)

    def save_scene_animation_task(self, filename, duration_sec):

        from array2gif import write_gif

        image_list = []

        # while not self.diffractometer_hwobj.is_ready():
        for i in range(4):
            arr = self.get_scene_snapshot(return_as_array=True)
            width = arr.shape[0]
            height = arr.shape[1]
            r = np.ravel(arr)[::3]
            g = np.ravel(arr)[1::3]
            b = np.ravel(arr)[2::3]
            image_list.append(np.append(np.append(r, g), b).reshape(3, width, height))
            gevent.sleep(0.04)

        tt = image_list[0]
        write_gif(image_list, "/tmp/test_anim.gif", fps=15)

    def get_snapshot(self, overlay=True, bw=False, return_as_array=False):
        """Returns a raw snapshot from camera

        :param bw: black and white
        :type bw: bool
        :param return_as_array: return image as numpy array
        :type return_as_array: bool
        """
        if overlay:
            self.get_scene_snapshot(bw, return_as_array)
        else:
            self.camera_hwobj.get_snapshot(bw, return_as_array)

    def save_snapshot(self, filename, overlay=True, bw=False):
        """Save raw image from camera in file

        :param filename: filename
        :type filename: str
        :param bw: black and white
        :type bw: bool
        :param image_type: image format. Default png
        :type image_type: str
        """
        try:
            if overlay:
                self.save_scene_snapshot(filename)
            else:
                self.camera_hwobj.save_snapshot(filename, "PNG")
        except Exception:
            logging.getLogger("HWR").exception(
                "Unable to save snapshot in %s" % filename
            )

    def save_beam_profile(self, profile_filename):
        image_array = self.get_raw_snapshot(bw=True, return_as_array=True)
        try:
            hor_sum = image_array.sum(axis=0)
            ver_sum = image_array.sum(axis=1)

            fig, axarr = plt.subplots(1, 2)

            axarr[0].plot(np.arange(0, hor_sum.size, 1), hor_sum)
            axarr[1].plot(ver_sum[::-1], np.arange(0, ver_sum.size, 1))

            fig.savefig(profile_filename, dpi=300, bbox_inches="tight")
        except Exception:
            logging.getLogger("HWR").exception(
                "Unable to save beam profile image: %s" % profile_filename
            )

    def open_beam_profile_view(self):
        """Opens new dialog with 3D beam profile"""
        image_array = self.get_raw_snapshot(bw=True, return_as_array=True)
        fig = plt.figure()
        ax = fig.gca(projection="3d")
        ax.set_axis_bgcolor("gray")

        X = np.arange(0, image_array.shape[0])
        Y = np.arange(0, image_array.shape[1])
        X, Y = np.meshgrid(X, Y)

        ax.plot_surface(
            X,
            Y,
            np.transpose(image_array),
            cmap=cm.gnuplot,
            linewidth=0,
            antialiased=False,
        )

        # fig.colorbar(surf, shrink=0.5, aspect=5)
        plt.show()

    def start_measure_distance(self, wait_click=False):
        """Distance measuring method

        :param wait_click: wait for first click to start
        :type wait_click: bool
        :emits: infoMsg
        """
        self.set_cursor_busy(True)
        if wait_click:
            logging.getLogger("user_level_log").info(
                "Click to start " + "distance  measuring (Double click stops)"
            )
            self.wait_measure_distance_click = True
            self.emit("infoMsg", "Distance measurement")
        else:
            self.wait_measure_distance_click = False
            self.in_measure_distance_state = True
            self.start_graphics_item(self.graphics_measure_distance_item)

    def start_measure_angle(self, wait_click=False):
        """Angle measuring method

        :param wait_click: wait for first click to start
        :type wait_click: bool
        :emits: infoMsg
        """
        self.set_cursor_busy(True)
        if wait_click:
            logging.getLogger("user_level_log").info(
                "Click to start " + "angle measuring (Double click stops)"
            )
            self.wait_measure_angle_click = True
            self.emit("infoMsg", "Angle measurement")
        else:
            self.wait_measure_angle_click = False
            self.in_measure_angle_state = True
            self.start_graphics_item(self.graphics_measure_angle_item)

    def start_measure_area(self, wait_click=False):
        """Area measuring method

        :param wait_click: wait for first click to start
        :type wait_click: bool
        :emits: infoMsg as str
        """
        self.set_cursor_busy(True)
        if wait_click:
            logging.getLogger("user_level_log").info(
                "Click to start area " + "measuring (Double click stops)"
            )
            self.wait_measure_area_click = True
            self.emit("infoMsg", "Area measurement")
        else:
            self.wait_measure_area_click = False
            self.in_measure_area_state = True
            self.start_graphics_item(self.graphics_measure_area_item)

    def start_move_beam_mark(self):
        """Method to move beam mark

        :emits: infoMsg as str
        """
        self.set_cursor_busy(True)
        self.emit("infoMsg", "Move beam mark")
        self.in_move_beam_mark_state = True
        self.start_graphics_item(
            self.graphics_move_beam_mark_item, start_pos=self.beam_position
        )
        # self.graphics_move_beam_mark_item.set_beam_mark(\
        #     self.beam_info_dict, self.pixels_per_mm)

    def start_define_beam(self):
        """Method to define beam size.
           User

        :emits: infoMsg as str
        """
        self.set_cursor_busy(True)
        logging.getLogger("user_level_log").info(
            "Select an area to " + "define beam size"
        )
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

        :emits: infoMsg as str
        """
        self.set_cursor_busy(False)
        self.in_measure_distance_state = False
        self.wait_measure_distance_click = False
        self.graphics_measure_distance_item.hide()
        self.graphics_view.graphics_scene.update()
        self.emit("infoMsg", "")

    def stop_measure_angle(self):
        """Stops angle measurement

        :emits: infoMsg as str
        """
        self.set_cursor_busy(False)
        self.in_measure_angle_state = False
        self.wait_measure_angle_click = False
        self.graphics_measure_angle_item.hide()
        self.graphics_view.graphics_scene.update()
        self.emit("infoMsg", "")

    def stop_measure_area(self):
        """Stops area measurement

        :emits: infoMsg as str
        """
        self.set_cursor_busy(False)
        self.in_measure_area_state = False
        self.wait_measure_area_click = False
        self.graphics_measure_area_item.hide()
        self.graphics_view.graphics_scene.update()
        self.emit("infoMsg", "")

    def stop_move_beam_mark(self):
        """Stops to move beam mark

        :emits: infoMsg as str
        """
        self.set_cursor_busy(False)
        self.in_move_beam_mark_state = False
        self.graphics_move_beam_mark_item.hide()
        self.graphics_view.graphics_scene.update()
        HWR.beamline.beam.set_beam_position(
            self.graphics_move_beam_mark_item.end_coord[0],
            self.graphics_move_beam_mark_item.end_coord[1],
        )
        self.emit("infoMsg", "")

    def stop_beam_define(self):
        """Stops beam define

        :emits: infoMsg as str
        """
        self.set_cursor_busy(False)
        self.in_beam_define_state = False
        self.wait_beam_define_click = False
        self.graphics_beam_define_item.hide()
        self.graphics_view.graphics_scene.update()
        self.emit("infoMsg", "")
        HWR.beamline.beam.set_slits_gap(
            self.graphics_beam_define_item.width_microns,
            self.graphics_beam_define_item.height_microns,
        )
        self.diffractometer_hwobj.move_to_beam(
            self.graphics_beam_define_item.center_coord[0],
            self.graphics_beam_define_item.center_coord[1],
        )

    def start_centring(self, tree_click=None):
        """Starts centring procedure

        :param tree_click: centring with 3 clicks
        :type tree_click: bool
        :emits: - centringInProgress as bool
                - infoMsg: as str
        """
        self.emit("centringInProgress", True)
        if tree_click:
            self.hide_all_items()
            self.set_cursor_busy(True)
            self.set_centring_state(True)
            self.diffractometer_hwobj.start_centring_method(
                self.diffractometer_hwobj.CENTRING_METHOD_MANUAL
            )
            self.emit("infoMsg", "3 click centring")
        else:
            # self.accept_centring()
            self.diffractometer_hwobj.start_move_to_beam(
                self.beam_position[0], self.beam_position[1]
            )

    def accept_centring(self):
        """Accepts centring
        """
        self.set_cursor_busy(False)
        self.diffractometer_hwobj.accept_centring()
        self.diffractometer_state_changed()
        self.show_all_items()

    def reject_centring(self):
        """Rejects centring
        """
        self.set_cursor_busy(False)
        self.diffractometer_hwobj.reject_centring()
        self.show_all_items()

    def cancel_centring(self, reject=False):
        """Cancels centring

        :param reject: reject position
        :type reject: bool
        """
        self.set_cursor_busy(False)
        self.diffractometer_hwobj.cancel_centring_method(reject=reject)
        self.show_all_items()

    def start_one_click_centring(self):
        self.set_cursor_busy(True)
        self.emit("infoMsg", "Click on the screen to create centring points")
        self.in_one_click_centering = True
        self.graphics_centring_lines_item.setVisible(True)

    def stop_one_click_centring(self):
        self.set_cursor_busy(False)
        self.emit("infoMsg", "")
        self.in_one_click_centering = False
        self.graphics_centring_lines_item.setVisible(False)

    def start_visual_align(self):
        """Starts visual align procedure when two centring points are selected
           Orientates two points along the osc axes

        :emits: infoMsg as str
        """
        selected_points = self.get_selected_points()
        if len(selected_points) == 2:
            self.diffractometer_hwobj.visual_align(
                selected_points[0].get_centred_position(),
                selected_points[1].get_centred_position(),
            )
            self.emit("infoMsg", "Visual align")
        else:
            msg = "Select two centred position (CTRL click) to continue"
            logging.getLogger("user_level_log").error(msg)

    def create_line(self, start_point=None, end_point=None, emit=True):
        """Creates helical line if two centring points selected
        """
        line = None
        selected_points = (start_point, end_point)

        if None in selected_points:
            selected_points = self.get_selected_points()
        if len(selected_points) > 1:
            line = GraphicsLib.GraphicsItemLine(selected_points[0], selected_points[1])
            self.add_shape(line, emit)
        else:
            msg = (
                "Please select two points (with same kappa and phi) "
                + "to create a helical line"
            )
            logging.getLogger("GUI").error(msg)
        return line

    def create_auto_line(self, cpos=None):
        """Creates a automatic helical line
        """
        if cpos is None:
            point_one_motor_pos = self.diffractometer_hwobj.get_positions()
        else:
            point_one_motor_pos = cpos

        point_two_motor_pos = deepcopy(point_one_motor_pos)

        # TODO
        # This is for MD2, add MD3 and move to diffractometer

        ver_range = -0.1
        omega_ref = 0.0
        point_one_motor_pos["sampx"] = point_one_motor_pos[
            "sampx"
        ] + ver_range * math.sin(
            math.pi * (point_one_motor_pos["phi"] - omega_ref) / 180.0
        )
        point_one_motor_pos["sampy"] = point_one_motor_pos[
            "sampy"
        ] - ver_range * math.cos(
            math.pi * (point_one_motor_pos["phi"] - omega_ref) / 180.0
        )

        ver_range = 0.1
        point_two_motor_pos["sampx"] = point_two_motor_pos[
            "sampx"
        ] + ver_range * math.sin(
            math.pi * (point_one_motor_pos["phi"] - omega_ref) / 180.0
        )
        point_two_motor_pos["sampy"] = point_two_motor_pos[
            "sampy"
        ] - ver_range * math.cos(
            math.pi * (point_one_motor_pos["phi"] - omega_ref) / 180.0
        )

        cpos_one = queue_model_objects.CentredPosition(point_one_motor_pos)
        point_one = GraphicsLib.GraphicsItemPoint(cpos_one)
        self.add_shape(point_one)
        cpos_one.set_index(point_one.index)

        cpos_two = queue_model_objects.CentredPosition(point_two_motor_pos)
        point_two = GraphicsLib.GraphicsItemPoint(cpos_two)
        self.add_shape(point_two)
        cpos_two.set_index(point_two.index)

        line = self.create_line(point_one, point_two)
        self.diffractometer_state_changed()

        return line, cpos_one, cpos_two

    def create_grid(self, spacing=(0, 0)):
        """Creates grid

        :param spacing: spacing between beams
        :type spacing: list with two floats (can be negative)
        """
        if not self.wait_grid_drawing_click:
            self.set_cursor_busy(True)
            self.graphics_grid_draw_item = GraphicsLib.GraphicsItemGrid(
                self, self.beam_info_dict, spacing, self.pixels_per_mm
            )
            self.graphics_grid_draw_item.set_draw_mode(True)
            self.graphics_grid_draw_item.index = self.grid_count
            self.grid_count += 1
            self.graphics_view.graphics_scene.addItem(self.graphics_grid_draw_item)
            self.wait_grid_drawing_click = True

    def create_auto_grid(self):
        # self.start_auto_centring(wait=True)
        grid_size = (1, 1)
        grid_spacing = (self.beam_info_dict["size_x"], self.beam_info_dict["size_y"])

        GraphicsLib.GraphicsItemGrid.set_auto_grid_size(grid_size)
        temp_grid = GraphicsLib.GraphicsItemGrid(
            self, self.beam_info_dict, (0, 0), self.pixels_per_mm
        )
        self.graphics_view.graphics_scene.addItem(temp_grid)
        temp_grid.index = self.grid_count
        motor_pos = self.diffractometer_hwobj.get_centred_point_from_coord(
            self.beam_position[0], self.beam_position[1], return_by_names=True
        )
        temp_grid.set_centred_position(queue_model_objects.CentredPosition(motor_pos))
        temp_grid.update_auto_grid(
            self.beam_info_dict, self.beam_position, grid_spacing
        )

        self.emit("shapeCreated", temp_grid, "Grid")
        self.shape_dict[temp_grid.get_display_name()] = temp_grid
        # self._shapes.add_shape(temp_grid.get_display_name(), temp_grid)
        self.grid_count += 1

        return temp_grid

        # spawn(self.auto_grid_procedure)

    def auto_grid_procedure(self):
        """Test
        """
        logging.getLogger("user_level_log").info("Auto grid procedure started...")
        temp_grid = None
        """
        self.diffractometer_hwobj.move_omega(0)
        self.diffractometer_hwobj.move_sample_out()
        background_image = self.get_raw_snapshot(bw=True, return_as_array=True)
        self.diffractometer_hwobj.move_sample_in()

        number_of_snapshots = 6
        snapshot_list = []

        for index in range(number_of_snapshots):
            (info, x, y) = lucid.find_loop(
                self.get_raw_snapshot(bw=False, return_as_array=True)
            )
            snapshot_list.append(
                {
                    "omega": index * 360 / number_of_snapshots,
                    "image": self.get_raw_snapshot(bw=True, return_as_array=True),
                    "optical_x": x,
                    "optical_y": y,
                }
            )
            self.diffractometer_hwobj.move_omega_relative(360 / number_of_snapshots)

        auto_mesh = AutoMesh.getAutoMesh(
            background_image,
            snapshot_list,
            (self.beam_info_dict["size_x"], self.beam_info_dict["size_y"]),
            self.pixels_per_mm,
        )

        self.diffractometer_hwobj.move_omega(auto_mesh["angle"])

        grid_spacing = (
            self.beam_info_dict["size_x"] / 2,
            self.beam_info_dict["size_y"] / 2,
        )

        GraphicsLib.GraphicsItemGrid.set_auto_grid_size(
            (auto_mesh["dx_mm"], auto_mesh["dy_mm"])
        )
        temp_grid = GraphicsLib.GraphicsItemGrid(
            self, self.beam_info_dict, (0, 0), self.pixels_per_mm
        )
        self.graphics_view.graphics_scene.addItem(temp_grid)
        temp_grid.index = self.grid_count
        motor_pos = self.diffractometer_hwobj.get_centred_point_from_coord(
            auto_mesh["center_x"], auto_mesh["center_y"], return_by_names=True
        )
        temp_grid.set_centred_position(queue_model_objects.CentredPosition(motor_pos))
        temp_grid.update_auto_grid(
            self.beam_info_dict, self.beam_position, grid_spacing
        )

        self.emit("shapeCreated", temp_grid, "Grid")
        self.shape_dict[temp_grid.get_display_name()] = temp_grid
        self.grid_count += 1

        self.diffractometer_state_changed()
        logging.getLogger("user_level_log").info("Auto grid created")
        """
        return temp_grid

    def update_grid_motor_positions(self, grid_object):
        """Updates grid corner positions
        """
        grid_center_x, grid_center_y = grid_object.get_center_coord()
        motor_pos = self.diffractometer_hwobj.get_centred_point_from_coord(
            grid_center_x, grid_center_y, return_by_names=True
        )
        grid_object.set_centred_position(queue_model_objects.CentredPosition(motor_pos))

        motor_pos_corner = []
        for index, corner_coord in enumerate(grid_object.get_corner_coord()):
            motor_pos_corner.append(
                self.diffractometer_hwobj.get_centred_point_from_coord(
                    corner_coord.x(), corner_coord.y(), return_by_names=True
                )
            )
        grid_object.set_motor_pos_corner(motor_pos_corner)

    def refresh_camera(self):
        """Not called, To be deleted
        """
        self.beam_info_dict = HWR.beamline.beam.get_info_dict()
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
            # for shape in self._shapes.get_all_shapes():
            if isinstance(shape, GraphicsLib.GraphicsItemLine):
                (start_point, end_point) = shape.get_graphics_points()
                if min(
                    start_point.start_coord[0], end_point.start_coord[0]
                ) < select_middle_x < max(
                    start_point.start_coord[0], end_point.start_coord[0]
                ) and min(
                    start_point.start_coord[1], end_point.start_coord[1]
                ) < select_middle_y < max(
                    start_point.start_coord[1], end_point.start_coord[1]
                ):
                    shape.setSelected(True)

    def get_image_scale_list(self):
        """Returns list with available image scales

        :returns: list with floats
        """
        return self.image_scale_list

    def set_view_scale(self, view_scale):
        """Scales all objects on the view"""
        if isinstance(view_scale, float):
            self.graphics_view.scale(view_scale, view_scale)

    def set_image_scale(self, image_scale, use_scale=False):
        """Scales the incomming frame

        :param image_scale: image scale
        :type image_scale: float 0 - 1.0
        :param use_scale: enables/disables image scale
        :type use_scale: bool
        :emits: imageScaleChanged
        """
        self.graphics_view.scale(image_scale, image_scale)
        return
        """
        scene_size = self.graphics_scene_size
        if image_scale == 1:
            use_scale = False
        if use_scale:
            self.image_scale = image_scale
            scene_size = [scene_size[0] * image_scale, scene_size[1] * image_scale]
        else:
            self.image_scale = 1
        self.graphics_view.graphics_scene.image_scale = self.image_scale

        self.graphics_view.scene().setSceneRect(
            0, 0, scene_size[0] - 10, scene_size[1] - 10
        )
        self.graphics_view.toggle_scrollbars_enable(self.image_scale > 1)
        self.emit("imageScaleChanged", self.image_scale)
        """

    def get_image_scale(self):
        """Returns current scale factor of image

        :returns: float
        """
        return self.image_scale

    def auto_focus(self):
        """Starts auto focus
        """
        self.diffractometer_hwobj.start_auto_focus()

    def start_auto_centring(self, wait=False):
        """Starts auto centring
        """
        # self.display_info_msg(["Auto centring in progress...",
        #                       "Please wait."])
        self.emit("centringInProgress", True)
        self.diffractometer_hwobj.start_centring_method(
            self.diffractometer_hwobj.CENTRING_METHOD_AUTO, wait=wait
        )
        self.emit("infoMsg", "Automatic centring")

    def move_beam_mark_auto(self):
        """Automatic procedure detects beam positions and updates
           beam info.
        """
        beam_shape_dict = self.detect_object_shape()
        HWR.beamline.beam.set_beam_position(
            beam_shape_dict["center"][0], beam_shape_dict["center"][1]
        )
        # self.graphics_beam_item.set_detected_beam_position(beam_shape_dict)

    def detect_object_shape(self):
        """Method used to detect a shape on the image.
           It is used to detect beam shape and loop
        returns: dictionary with parameters:
                 - center: list with center coordinates
                 - width: estimated beam width
                 - height: estimated beam height
        """
        object_shape_dict = {"center": (0, 0), "width": -1, "height": -1}
        image_array = self.camera_hwobj.get_snapshot(bw=True, return_as_array=True)

        # TODO filter the image
        image_array[image_array < 30] = 0

        hor_sum = image_array.sum(axis=0)
        ver_sum = image_array.sum(axis=1)

        beam_x = None
        beam_y = None

        try:
            half_max = hor_sum.max() / 2.0
            s = interpolate.splrep(
                np.linspace(0, hor_sum.size, hor_sum.size), hor_sum - half_max
            )
            hor_roots = interpolate.sproot(s)

            half_max = ver_sum.max() / 2.0
            s = interpolate.splrep(
                np.linspace(0, ver_sum.size, ver_sum.size), ver_sum - half_max
            )
            ver_roots = interpolate.sproot(s)

            if len(hor_roots) and len(ver_roots):
                object_shape_dict["width"] = int(hor_roots[-1] - hor_roots[0])
                object_shape_dict["height"] = int(ver_roots[-1] - ver_roots[0])

            # beam_spl_x = (hor_roots[0] + hor_roots[1]) / 2.0
            # beam_spl_y = (ver_roots[0] + ver_roots[1]) / 2.0
        except Exception:
            logging.getLogger("user_level_log").debug(
                "QtGraphicsManager: " + "Unable to detect object shape"
            )
            # beam_spl_x = 0
            # beam_spl_y = 0

        f = interpolate.interp1d(np.arange(0, hor_sum.size, 1), hor_sum)
        xx = np.arange(0, hor_sum.size, 1)
        yy = f(xx)
        window = signal.gaussian(200, 60)
        smoothed = signal.convolve(yy, window / window.sum(), mode="same")
        beam_x = xx[np.argmax(smoothed)]

        f = interpolate.interp1d(np.arange(0, ver_sum.size, 1), ver_sum)
        xx = np.arange(0, ver_sum.size, 1)
        yy = f(xx)
        window = signal.gaussian(200, 60)
        smoothed = signal.convolve(yy, window / window.sum(), mode="same")
        beam_y = xx[np.argmax(smoothed)]

        beam_mass_x, beam_mass_y = ndimage.measurements.center_of_mass(
            np.transpose(image_array)
        )

        """
        logging.getLogger("user_level_log").info(\
                "By spline %s %s" % \
                (str(beam_spl_x), str(beam_spl_y)))
        logging.getLogger("user_level_log").info(\
                "By 1d interp %s %s" \
                %(str(beam_x), str(beam_y)))
        logging.getLogger("user_level_log").info(\
                "By center of mass %s %s" \
                %(str(beam_mass_x), str(beam_mass_y)))
        """

        if None in (beam_x, beam_y):
            # image_array = np.transpose(image_array)
            beam_x = beam_mass_x
            beam_y = beam_mass_y
        # else:
        #    beam_x = int((beam_x + beam_mass_x) / 2)
        #    beam_y = int((beam_y + beam_mass_y) / 2)

        object_shape_dict["center"] = (beam_x, beam_y)

        self.graphics_beam_item.set_detected_beam_position(beam_x, beam_y)

        return object_shape_dict

    def get_beam_displacement(self, reference=None):
        """Calculates beam displacement:
           - detects beam shape. If no shape detected returns (None, None)
           - if beam detected then calculates the displacement in mm

        :param reference: beam centring reference
        :type reference : str. For example "beam" will return the difference
                          between actual beam positon and beam shape
        """
        beam_shape_dict = self.detect_object_shape()

        if (
            None
            or 0 in beam_shape_dict["center"]
            or (beam_shape_dict["width"] < 1 and beam_shape_dict["height"] < 1)
        ):
            return (None, None)
        else:
            if reference == "beam":
                return (
                    (self.beam_position[0] - beam_shape_dict["center"][0])
                    / self.pixels_per_mm[0],
                    (self.beam_position[1] - beam_shape_dict["center"][1])
                    / self.pixels_per_mm[1],
                )
            elif reference == "screen":
                # Displacement from the screen center
                return (
                    (self.graphics_scene_size[0] / 2 - beam_shape_dict["center"][0])
                    / self.pixels_per_mm[0],
                    (self.graphics_scene_size[1] / 2 - beam_shape_dict["center"][1])
                    / self.pixels_per_mm[1],
                )
            else:
                return (
                    (reference[0] - beam_shape_dict["center"][0])
                    / self.pixels_per_mm[0],
                    (reference[1] - beam_shape_dict["center"][1])
                    / self.pixels_per_mm[1],
                )

    def display_grid(self, state):
        """Display a grid on the screen
        """
        self.graphics_scale_item.set_display_grid(state)

    def display_histogram(self, state):
        self.graphics_histogram_item.setVisible(state)
        if state:
            self.update_histogram()

    def update_histogram(self):
        image_array = self.camera_hwobj.get_snapshot(bw=True, return_as_array=True)
        self.graphics_histogram_item.update_histogram(
            image_array.sum(axis=0), image_array.sum(axis=1)
        )

    def create_automatic_line(self):
        """Create automatic line for xray centring
        """
        raise NotImplementedError

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
        """Displays info message on the screen
        """
        if pos_x is None:
            pos_x = 10
            # pos_x = self.beam_position[0]
        if pos_y is None:
            pos_y = 50
            # pos_y = self.beam_position[1]
        self.graphics_info_item.display_info(msg, pos_x, pos_y, hide_msg)

    def hide_info_msg(self):
        """Hides info message"""
        self.graphics_info_item.hide()

    def swap_line_points(self, line):
        """Swaps centring points of a helical line
           This method reverses the direction of a helical scan
        """
        (point_start, point_end) = line.get_graphical_points()
        line.set_graphical_points(point_end, point_start)
        self.emit("shapeChanged", line, "Line")
        line.update_item()

    def display_beam_size(self, state):
        """Enables or disables displaying the beam size"""
        self.graphics_beam_item.enable_beam_size(state)

    def set_magnification_mode(self, mode):
        """Display or hide magnification tool"""
        if mode:
            QtImport.QApplication.setOverrideCursor(
                QtImport.QCursor(QtImport.Qt.ClosedHandCursor)
            )
        else:
            self.set_cursor_busy(False)
        self.graphics_magnification_item.setVisible(mode)
        self.in_magnification_mode = mode

    def set_scrollbars_off(self, state):
        """Enables or disables scrollbars"""
        if state:
            self.graphics_view.setHorizontalScrollBarPolicy(
                QtImport.Qt.ScrollBarAlwaysOff
            )
            self.graphics_view.setVerticalScrollBarPolicy(
                QtImport.Qt.ScrollBarAlwaysOff
            )
