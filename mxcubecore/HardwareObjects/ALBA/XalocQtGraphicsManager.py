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

import logging

from mxcubecore.HardwareObjects.QtGraphicsManager import QtGraphicsManager 
from mxcubecore.HardwareObjects import QtGraphicsLib as GraphicsLib
from mxcubecore import HardwareRepository as HWR

class XalocQtGraphicsManager(QtGraphicsManager):
    def __init__(self, name):
        QtGraphicsManager.__init__(self, name)
        self.userlogger = logging.getLogger("user_level_log")
        
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
            if self.current_centring_method == HWR.beamline.diffractometer.CENTRING_METHOD_MANUAL:
                self.graphics_centring_lines_item.add_position(pos_x, pos_y)
                self.diffractometer_hwobj.image_clicked(pos_x, pos_y)
            else: 
                self.userlogger.error("Click ignored, not in manual centring. ")
                self.userlogger.error("\tChange centring procedure in the \"Centring\" pulldown close to the ISPyB button if necessary")
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
        if self.in_centring_state:
            self.userlogger.error("Double click ignored, centring in progress. ")
            self.userlogger.error("\tWait for the centring procedure to finish")
        elif self.in_measure_distance_state:
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
                self.diffractometer_state_changed()
                self.graphics_view.graphics_scene.update()


    # CHECK: accept_centring, reject_centring, cancel_centring, start_one_click_centring, stop_one_click_centring
    #   did not have an emit, but this perhaps is done through emits from the diffractometer??
    def accept_centring(self):
        """Accepts centring
        """
        self.set_cursor_busy(False)
        self.diffractometer_hwobj.accept_centring()
        self.diffractometer_state_changed()
        self.show_all_items()
        self.emit("centringInProgress", False)

    def reject_centring(self):
        """Rejects centring
        """
        self.set_cursor_busy(False)
        self.diffractometer_hwobj.reject_centring()
        self.show_all_items()
        self.emit("centringInProgress", False)

    def cancel_centring(self, reject=False):
        """Cancels centring

        :param reject: reject position
        :type reject: bool
        """
        self.set_cursor_busy(False)
        self.diffractometer_hwobj.cancel_centring_method(reject=reject)
        self.show_all_items()
        self.emit("centringInProgress", False)

    def start_one_click_centring(self):
        self.set_cursor_busy(True)
        self.emit("infoMsg", "Click on the screen to create centring points")
        self.in_one_click_centering = True
        self.graphics_centring_lines_item.setVisible(True)
        self.emit("centringInProgress", True)

    def stop_one_click_centring(self):
        self.set_cursor_busy(False)
        self.emit("infoMsg", "")
        self.in_one_click_centering = False
        self.graphics_centring_lines_item.setVisible(False)
        self.emit("centringInProgress", False)

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
            self.emit('gridDrawn')

