#
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
Graphics item library:
 - GraphicsItem : base class for all items
 - GraphicsItemBeam : beam shape
 - GraphicsItemInfo : info message
 - GraphicsItemPoint : centring point
 - GraphicsItemLine : line between two centring points
 - GraphicsItemGrid : 2D grid
 - GraphicsItemScale : scale on the bottom left corner
 - GraphicsItemOmegaReference : omega rotation line
 - GraphicsSelectTool : item selection tool
 - GraphicsItemCentringLine : centring lines for 3 click centring
 - GraphicsItemHistogram: histogram item
 - GraphicsItemMoveBeamMark : item to move beam mark
 - GraphicsItemBeamDefine : beam size definer with slits
 - GraphicsItemMeasureDistance : line to measure distance
 - GraphicsItemMeasureAngle : object to measure angle between two lines
 - GraphicsItemMeasureArea : item to measure area
 - GraphicsItemMove : move buttons
 - GraphicsMagnificationItem : tool to zoom selected area
 - GraphicsCameraFrame : camera frame
 - GraphicsScene : scene where all items are displayed
 - GraphicsView : widget that contains GraphicsScene
"""

import copy
import math
import logging
from datetime import datetime

from mxcubecore.utils import qt_import

from mxcubecore.model import queue_model_objects
from mxcubecore.utils.conversion import string_types


SELECTED_COLOR = qt_import.Qt.green
NORMAL_COLOR = qt_import.Qt.yellow
SOLID_LINE_STYLE = qt_import.Qt.SolidLine
SOLID_PATTERN_STYLE = qt_import.Qt.SolidPattern
LIGHT_GREEN = qt_import.QColor(125, 181, 121)


class GraphicsItem(qt_import.QGraphicsItem):
    """Base class for all graphics items."""

    def __init__(self, parent=None, position_x=0, position_y=0):
        """
        :param position_x: x coordinate in the scene
        :type position_x: int
        :param position_y: y coordinate in the scene
        :type position_y: int
        """

        qt_import.QGraphicsItem.__init__(self)
        self.index = None
        self.base_color = None
        self.used_count = 0
        self.pixels_per_mm = [0, 0]
        self.start_coord = [0, 0]
        self.end_coord = [0, 0]
        self.beam_size_mm = [0, 0]
        self.beam_size_pix = [0, 0]
        self.beam_position = [0, 0]
        self.beam_is_rectangle = False
        self.rect = qt_import.QRectF(0, 0, 0, 0)
        self.display_beam_shape = None

        self.setPos(position_x, position_y)

        self.custom_pen_color = qt_import.Qt.white
        self.custom_pen = qt_import.QPen(SOLID_LINE_STYLE)
        self.custom_pen.setWidth(1)
        self.custom_pen.setColor(self.custom_pen_color)

        self.custom_brush = qt_import.QBrush(SOLID_PATTERN_STYLE)
        brush_color = qt_import.QColor(70, 70, 165)
        brush_color.setAlpha(70)
        self.custom_brush.setColor(brush_color)
        self.custom_brush.setStyle(qt_import.Qt.SolidPattern)

        self.setPos(position_x, position_y)

    def boundingRect(self):
        """Returns adjusted rect

        :returns: QRect
        """

        return self.rect.adjusted(0, 0, 40, 40)

    def set_size(self, width, height):
        """Sets fixed size

        :param width: width
        :type width: int
        :param height: height
        :type height: int
        """

        self.rect.setWidth(width)
        self.rect.setHeight(height)

    def set_start_position(self, position_x, position_y):
        """Sets start position"""

        if position_x is not None and position_y is not None:
            self.start_coord[0] = position_x
            self.start_coord[1] = position_y
        self.scene().update()

    def get_start_position(self):
        """Returns start coordinate of the shape

        :return: list with two int
        """
        return self.start_coord

    def set_end_position(self, position_x, position_y):
        """Sets the end position of the item

        :param position_x: x position in pix
        :type position_x: int
        :param position_y: y position in pix
        :type position_y: int
        """
        if position_x is not None and position_y is not None:
            self.end_coord = [position_x, position_y]
        self.scene().update()

    def get_display_name(self):
        """Returns items display name

        :returns: str
        """
        return "Item %d" % self.index

    def get_full_name(self):
        """Returns full name of the item

        :returns: str
        """
        return self.get_display_name()

    def set_base_color(self, color):
        """Sets base color for lines

        :param color: color
        :type color: QColor
        """
        self.base_color = color

    def update_item(self):
        """Updates current item. Calls parent scene update method"""
        self.scene().update()

    def mousePressEvent(self, event):
        """Emits scene itemClickedSignal to indicate selected item"""
        self.update()
        self.scene().itemClickedSignal.emit(self, self.isSelected())

    def toggle_selected(self):
        """Toggles item selection"""
        self.setSelected(not self.isSelected())
        self.update()

    def set_beam_info(self, beam_info):
        """Updates beam information

        :param beam_info: dictionary with beam parameters
                          (size_x, size_y, shape)
        :type beam_info: dict
        """
        self.beam_is_rectangle = beam_info.get("shape") == "rectangular"
        self.beam_size_mm[0] = beam_info.get("size_x", 0)
        self.beam_size_mm[1] = beam_info.get("size_y", 0)
        if not math.isnan(self.pixels_per_mm[0]):
            self.beam_size_pix[0] = int(self.beam_size_mm[0] * self.pixels_per_mm[0])
        if not math.isnan(self.pixels_per_mm[1]):
            self.beam_size_pix[1] = int(self.beam_size_mm[1] * self.pixels_per_mm[1])

    def set_beam_position(self, beam_position):
        """Sets beam position"""
        self.beam_position = beam_position

    def set_pixels_per_mm(self, pixels_per_mm):
        """Sets pixels per mm and updates item"""
        if not (math.isnan(pixels_per_mm[0]) or math.isnan(pixels_per_mm[1])):
            self.pixels_per_mm = pixels_per_mm
            self.beam_size_pix[0] = int(self.beam_size_mm[0] * self.pixels_per_mm[0])
            self.beam_size_pix[1] = int(self.beam_size_mm[1] * self.pixels_per_mm[1])
            self.update_item()

    def set_tool_tip(self, tooltip=None):
        """Sets tooltip"""
        if tooltip:
            self.setToolTip(self.get_full_name() + "\n" + tooltip)
        else:
            self.setToolTip(self.get_full_name())

    def set_custom_pen_color(self, color):
        """Defines custom pen color"""
        self.custom_pen_color = color


class GraphicsItemBeam(GraphicsItem):
    """Beam base class"""

    def __init__(self, parent, position_x=0, position_y=0):
        """Sets item flag ItemIsMovable"""
        GraphicsItem.__init__(self, parent, position_x=0, position_y=0)
        self.beam_is_rectangle = True
        self.display_beam_size = False
        self.detected_beam_info_dict = [None, None]
        self.setFlags(qt_import.QGraphicsItem.ItemIsMovable)

    def paint(self, painter, option, widget):
        """Main beam painter method
        Draws ellipse or rectangle with a cross in the middle
        """
        self.custom_pen.setColor(qt_import.Qt.blue)
        painter.setPen(self.custom_pen)

        if self.beam_is_rectangle:
            painter.drawRect(
                self.beam_position[0] * self.scene().image_scale
                - self.beam_size_pix[0] / 2 * self.scene().image_scale,
                self.beam_position[1] * self.scene().image_scale
                - self.beam_size_pix[1] / 2 * self.scene().image_scale,
                self.beam_size_pix[0] * self.scene().image_scale,
                self.beam_size_pix[1] * self.scene().image_scale,
            )
        else:
            painter.drawEllipse(
                int(
                    self.beam_position[0] * self.scene().image_scale
                    - self.beam_size_pix[0] / 2 * self.scene().image_scale
                ),
                int(
                    self.beam_position[1] * self.scene().image_scale
                    - self.beam_size_pix[1] / 2 * self.scene().image_scale
                ),
                int(self.beam_size_pix[0] * self.scene().image_scale),
                int(self.beam_size_pix[1] * self.scene().image_scale),
            )

        self.custom_pen.setColor(qt_import.Qt.red)
        painter.setPen(self.custom_pen)
        painter.drawLine(
            int(self.beam_position[0] * self.scene().image_scale - 10),
            int(self.beam_position[1] * self.scene().image_scale),
            int(self.beam_position[0] * self.scene().image_scale + 10),
            int(self.beam_position[1] * self.scene().image_scale),
        )
        painter.drawLine(
            int(self.beam_position[0] * self.scene().image_scale),
            int(self.beam_position[1] * self.scene().image_scale - 10),
            int(self.beam_position[0] * self.scene().image_scale),
            int(self.beam_position[1] * self.scene().image_scale + 10),
        )
        if self.display_beam_size:
            self.custom_pen.setColor(qt_import.Qt.darkGray)
            painter.setPen(self.custom_pen)
            painter.drawText(
                int(self.beam_position[0] + self.beam_size_pix[0] / 2 + 2),
                int(self.beam_position[1] + self.beam_size_pix[1] / 2 + 10),
                "%d x %d %sm"
                % (self.beam_size_mm[0] * 1000, self.beam_size_mm[1] * 1000, "\u00B5"),
            )
        if None not in self.detected_beam_info_dict:
            painter.drawLine(
                int(self.detected_beam_info_dict[0] - 10),
                int(self.detected_beam_info_dict[1] - 10),
                int(self.detected_beam_info_dict[0] + 10),
                int(self.detected_beam_info_dict[1] + 10),
            )
            painter.drawLine(
                int(self.detected_beam_info_dict[0] + 10),
                int(self.detected_beam_info_dict[1] - 10),
                int(self.detected_beam_info_dict[0] - 10),
                int(self.detected_beam_info_dict[1] + 10),
            )

    def enable_beam_size(self, state):
        """Enable or disable info about beam size

        :param state: display state
        :type state: bool
        :return: None
        """
        self.display_beam_size = state

    def set_detected_beam_position(self, pos_x, pos_y):
        """Updates beam mark position

        :param pos_x: position x
        :type pos_x: int
        :param pos_y: position y
        :type pos_y: int
        :return: None
        """
        self.detected_beam_info_dict = (pos_x, pos_y)


class GraphicsItemInfo(GraphicsItem):
    """Message box for displaying information on the screen"""

    def __init__(self, parent, position_x=0, position_y=0):
        """
        Init
        :param parent:
        :param position_x: int
        :param position_y: int
        """

        GraphicsItem.__init__(self, parent, position_x=0, position_y=0)
        self.beam_is_rectangle = True
        self.start_coord = [position_x, position_y]
        self.setFlags(qt_import.QGraphicsItem.ItemIsMovable)

        self.__msg = None
        self.__pos_x = None
        self.__pos_y = None
        self.__display_time = 5
        self.__draw_rect = None
        self.__created_time = None

    def paint(self, painter, option, widget):
        """Main painter class. Draws message box and after display time
        hides the message box.
        """
        self.custom_pen.setColor(qt_import.Qt.transparent)
        painter.setPen(self.custom_pen)
        self.custom_brush.setColor(qt_import.QColor(255, 255, 255, 140))
        painter.setBrush(self.custom_brush)

        font = painter.font()
        font.setBold(True)
        font.setItalic(True)
        font.setPointSize(12)
        painter.setFont(font)

        if self.__msg:
            painter.drawRoundedRect(self.__draw_rect, 10, 10)
            self.custom_pen.setColor(qt_import.Qt.black)
            painter.setPen(self.custom_pen)
            if isinstance(self.__msg, str):
                painter.drawText(self.__pos_x + 5, self.__pos_y + 10, self.__msg)
            else:
                for index, text_line in enumerate(self.__msg):
                    painter.drawText(
                        self.__pos_x + 5, self.__pos_y + 10 + 15 * index, text_line
                    )
        if self.__created_time:
            time_delta = datetime.now() - self.__created_time
            if self.__display_time:
                if time_delta.seconds > self.__display_time:
                    self.hide()

    def display_info(self, msg, pos_x, pos_y, hide_msg=True):
        """
        Shows message on the view
        :param msg: str
        :param pos_x: int
        :param pos_y: int
        :param hide_msg: bool. Hide msg after 5 sec timeout
        :return:
        """
        self.__msg = msg
        self.__pos_x = pos_x
        self.__pos_y = pos_y

        if hide_msg:
            self.__created_time = datetime.now()
        else:
            self.__created_time = None
        if isinstance(msg, string_types):
            height = 25
        else:
            height = 20 * len(msg)
        height += 10
        self.__draw_rect = qt_import.QRectF(
            pos_x, pos_y, self.scene().width() - 20, height
        )
        self.show()
        self.scene().update()


class GraphicsItemPoint(GraphicsItem):
    """Centred point class."""

    def __init__(
        self, centred_position=None, full_centring=True, position_x=0, position_y=0
    ):
        """
        :param: parent
        :param centred position: motor positions
        :type centred_position: dict with motors positions
        :param full_centring: indicates centring method
        :type full_centring : bool. True if 3click centring
        :param position_x: horizontal beam position
        :type position_x: int
        :param position_y: vertical beam position
        :type position_y: int
        """

        GraphicsItem.__init__(self, position_x, position_y)

        self.__full_centring = full_centring
        self.setFlags(qt_import.QGraphicsItem.ItemIsSelectable)

        if centred_position is None:
            self.__centred_position = queue_model_objects.CentredPosition()
            self.__centred_position.centring_method = False
        else:
            self.__centred_position = centred_position

        self.start_coord = [position_x, position_y]
        self.setPos(position_x - 10, position_y - 10)

    def boundingRect(self):
        """Returns adjusted rect

        :returns: QRect
        """

        return self.rect.adjusted(0, 0, 20, 20)

    def get_display_name(self):
        """Returns display name

        :return: str
        """
        return "Point %d" % self.index

    def get_full_name(self):
        """Returns full name

        :return: str
        """
        full_name = "Point %d" % self.index
        try:
            full_name += " (kappa: %0.2f phi: %0.2f)" % (
                self.__centred_position.kappa,
                self.__centred_position.kappa_phi,
            )
        except Exception:
            pass
        return full_name

    def get_centred_position(self):
        """Return centered position

        :return: cpos
        """
        return self.__centred_position

    def set_centred_position(self, centred_position):
        """Sets centred position

        :param centred_position:
        :return:
        """
        self.__centred_position = centred_position

    def paint(self, painter, option, widget):
        """
        Main pain method
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        self.custom_pen.setWidth(1)
        if self.used_count > 0:
            self.custom_pen.setColor(qt_import.Qt.red)
        else:
            self.custom_pen.setWidth(1)
            if self.base_color:
                self.custom_pen.setColor(self.base_color)
            else:
                self.custom_pen.setColor(NORMAL_COLOR)

        if self.isSelected():
            self.custom_pen.setColor(SELECTED_COLOR)
            self.custom_pen.setWidth(2)

        painter.setPen(self.custom_pen)
        painter.drawEllipse(0, 0, 20, 20)
        painter.drawLine(0, 0, 20, 20)
        painter.drawLine(0, 20, 20, 0)

        if self.index:
            display_str = str(self.index)
        else:
            display_str = "#"
        if self.isSelected():
            display_str += " selected"
        painter.drawText(22, 0, display_str)

        """
        if self.isSelected() and self.used_count > 0:
            painter.drawText(22, 27,
                             "%s exposure(s)" % self.used_count)
        """

    def set_start_position(self, position_x, position_y):
        """Sets start position

        :param position_x: horizontal coordinate
        :type position_y: int
        :param position_y: vertical coordinate
        :type position_y: int
        :return: None
        """
        if position_x is not None and position_y is not None:
            self.start_coord[0] = position_x
            self.start_coord[1] = position_y
            self.setPos(position_x - 10, position_y - 10)
            self.scene().update()

    def mouseDoubleClickEvent(self, event):
        """Emits itemDoubleClickedSignal

        :param event: Qt event
        :return:
        """
        self.scene().itemDoubleClickedSignal.emit(self)
        self.update()


class GraphicsItemLine(GraphicsItem):
    """Line class"""

    def __init__(self, cp_start, cp_end):
        """
        Init
        :param cp_start:
        :param cp_end:
        """
        GraphicsItem.__init__(self)

        self.setFlags(qt_import.QGraphicsItem.ItemIsSelectable)
        self.__cp_start = cp_start
        self.__cp_end = cp_end
        self.__num_images = 0
        self.__display_overlay = False
        self.__fill_alpha = 120

        brush_color = qt_import.QColor(70, 70, 165)
        brush_color.setAlpha(5)
        self.custom_brush.setColor(brush_color)

        self.setToolTip(self.get_full_name())

    def set_fill_alpha(self, value):
        """Sets the transparency level"""
        self.__fill_alpha = value
        brush_color = qt_import.QColor(70, 70, 165, self.__fill_alpha)
        self.custom_brush.setColor(brush_color)

    def set_display_overlay(self, state):
        """Enables overlay"""
        self.__display_overlay = state

    def get_display_name(self):
        """Returns line name displayed on the screen"""
        return "Line %d" % self.index

    def get_full_name(self):
        """Returns line name displayed in the line listwidget"""
        start_cpos = self.__cp_start.get_centred_position()
        end_cpos = self.__cp_end.get_centred_position()
        full_name = "Line (points: %d, %d)" % (
            self.__cp_start.index,
            self.__cp_end.index,
        )
        try:
            full_name += "kappa: %.2f phi: %.2f" % (
                start_cpos.kappa,
                start_cpos.kappa_phi,
            )
        except Exception:
            pass
        return full_name

    def paint(self, painter, option, widget):
        """Main paint method"""
        painter.setBrush(self.custom_brush)
        (start_cp_x, start_cp_y) = self.__cp_start.get_start_position()
        (end_cp_x, end_cp_y) = self.__cp_end.get_start_position()
        mid_x = min(start_cp_x, end_cp_x) + abs((start_cp_x - end_cp_x) / 2.0)
        mid_y = min(start_cp_y, end_cp_y) + abs((start_cp_y - end_cp_y) / 2.0)

        if self.isSelected() and self.__num_images and self.__display_overlay:
            painter.setPen(qt_import.Qt.NoPen)
            for beam_index in range(self.__num_images):
                coord_x = start_cp_x + (end_cp_x - start_cp_x) * beam_index / float(
                    self.__num_images
                )
                coord_y = start_cp_y + (end_cp_y - start_cp_y) * beam_index / float(
                    self.__num_images
                )
                painter.drawEllipse(
                    int(coord_x - self.beam_size_pix[0] / 2),
                    int(coord_y - self.beam_size_pix[1] / 2),
                    int(self.beam_size_pix[0]),
                    int(self.beam_size_pix[1]),
                )

        info_txt = "Line %d (%d->%d)" % (
            self.index,
            self.__cp_start.index,
            self.__cp_end.index,
        )

        if self.isSelected():
            self.custom_pen.setColor(SELECTED_COLOR)
            info_txt += " selected"
            painter.drawText(mid_x + 5, mid_y, info_txt)
            if self.__num_images:
                info_txt += " (%d images)" % self.__num_images
        else:
            self.custom_pen.setColor(NORMAL_COLOR)

        self.custom_pen.setWidth(2)
        painter.setPen(self.custom_pen)

        painter.drawLine(int(start_cp_x), int(start_cp_y), int(end_cp_x), int(end_cp_y))
        painter.drawText(mid_x + 5, mid_y, info_txt)

    def set_num_images(self, num_images):
        """Sets the number of collection frames"""
        self.__num_images = num_images
        self.update_item()

    def get_points_index(self):
        """Returns point indexes"""
        return (self.__cp_start.index, self.__cp_end.index)

    def get_graphical_points(self):
        """Returns start and end points of the line"""
        return (self.__cp_start, self.__cp_end)

    def set_graphical_points(self, cp_start, cp_end):
        """Sets the starting and ending points of the line"""
        self.__cp_start = cp_start
        self.__cp_end = cp_end
        self.update_item()

    def get_centred_positions(self):
        """Returns centered positions associated to the starting and
        ending points of the line
        """
        return (
            self.__cp_start.get_centred_position(),
            self.__cp_end.get_centred_position(),
        )


class GraphicsItemGrid(GraphicsItem):

    TOP_LEFT = 0
    TOP_RIGHT = 1
    BOT_LEFT = 2
    BOT_RIGHT = 3

    """Grid representation is based on two grid states:
               __draw_mode = True: user defines grid size
                             False: grid is defined
    In draw mode during the draw grid size is esitmated and based
    on the cell size and number of col and row actual grid
    object is painted. After drawing corner_points are added. These
    4 corner points are motor position dict. When one or several
    motors are moved corner_cord are updated and grid is painted
    in projection mode.
    """

    def __init__(self, parent, beam_info, spacing_mm, pixels_per_mm):
        """
        Init
        :param parent:
        :param beam_info:
        :param spacing_mm:
        :param pixels_per_mm:
        """
        GraphicsItem.__init__(self, parent)

        self.setFlags(qt_import.QGraphicsItem.ItemIsSelectable)

        self.pixels_per_mm = pixels_per_mm
        self.beam_is_rectangle = beam_info.get("shape") == "rectangular"
        self.beam_size_mm[0] = beam_info.get("size_x")
        self.beam_size_mm[1] = beam_info.get("size_y")
        self.beam_size_pix[0] = self.beam_size_mm[0] * self.pixels_per_mm[0]
        self.beam_size_pix[1] = self.beam_size_mm[1] * self.pixels_per_mm[1]

        if 0 in spacing_mm:
            spacing_mm = (beam_info.get("size_x"), beam_info["size_y"])
        self.__spacing_mm = spacing_mm
        self.__spacing_pix = [
            self.__spacing_mm[0] * self.pixels_per_mm[0],
            self.__spacing_mm[1] * self.pixels_per_mm[1],
        ]

        self.__frame_polygon = qt_import.QPolygon()
        for index in range(4):
            self.__frame_polygon.append(qt_import.QPoint())

        self.__center_coord = qt_import.QPoint()
        self.__num_cols = 0
        self.__num_rows = 0
        self.__num_lines = 0
        self.__num_images_per_line = 0
        self.__first_image_num = 1
        self.__centred_point = None
        self.__draw_mode = False
        self.__draw_projection = False
        self.__coordinate_map = []

        self.__osc_start = None
        self.__osc_range = 0.1
        self.__motor_pos_corner = []
        self.__centred_position = None
        self.__snapshot = None
        self.__grid_size_pix = [0, 0]
        self.__grid_range_pix = {"fast": 0, "slow": 0}
        self.__reversing_rotation = True
        self.__score = None
        self.__automatic = False
        self.__fill_alpha = 120
        self.__display_overlay = True
        self.__osc_range = 0
        self.__overlay_pixmap = None
        self.__original_pixmap = None
        self.base_color = qt_import.QColor(70, 70, 165, self.__fill_alpha)

    @staticmethod
    def set_grid_direction(grid_direction):
        """Sets grids direction."""
        GraphicsItemGrid.grid_direction = grid_direction

    @staticmethod
    def set_auto_grid_size(auto_grid_size):
        """Sets auto grid size in mm"""
        GraphicsItemGrid.auto_grid_size = auto_grid_size

    def get_display_name(self):
        """Returns display name"""
        if self.__automatic:
            return "Automatic mesh %d: %d x %d" % (
                (self.index + 1),
                self.__num_cols,
                self.__num_rows,
            )
        else:
            return "Mesh %d: %d x %d" % (
                (self.index + 1),
                self.__num_cols,
                self.__num_rows,
            )

    def get_full_name(self):
        return "Mesh %d (hor. spacing: %.1f, ver. spacing: %.1f)" % (
            self.index + 1,
            self.__spacing_mm[0],
            self.__spacing_mm[1],
        )

    def get_col_row_num(self):
        """
        Returns number of col and row
        :return: int, int
        """
        return self.__num_cols, self.__num_rows

    def get_line_image_per_line_num(self):
        """
        Rerturns num lines and num images per line
        :return: int, int
        """
        return self.__num_lines, self.__num_images_per_line

    def get_grid_range_mm(self):
        """
        Returns grid range in mm
        :return: (float, float)
        """
        return (
            self.__spacing_mm[0] * (self.__num_cols - 1),
            self.__spacing_mm[1] * (self.__num_rows - 1),
        )

    def get_grid_scan_mm(self):
        """
        Returns scan area in mm
        :return: (float, float)
        """
        fast_mm = abs(
            self.grid_direction["fast"][0]
            * self.__spacing_mm[0]
            * (self.__num_cols - 1)
            + self.grid_direction["fast"][1]
            * self.__spacing_mm[1]
            * (self.__num_rows - 1)
        )
        slow_mm = abs(
            self.grid_direction["slow"][0]
            * self.__spacing_mm[0]
            * (self.__num_cols - 1)
            + self.grid_direction["slow"][1]
            * self.__spacing_mm[1]
            * (self.__num_rows - 1)
        )
        return (fast_mm, slow_mm)

    def get_grid_size_mm(self):
        """
        Returns grid size in mm
        :return: (float, float)
        """
        return (
            self.__spacing_mm[0] * self.__num_cols,
            self.__spacing_mm[1] * self.__num_rows,
        )

    def set_pixels_per_mm(self, pixels_per_mm):
        """
        Sets pixels per mm
        :param pixels_per_mm: (float, float)
        :return:
        """
        GraphicsItem.set_pixels_per_mm(self, pixels_per_mm)
        self.__spacing_pix = [
            self.pixels_per_mm[0] * self.__spacing_mm[0],
            self.pixels_per_mm[1] * self.__spacing_mm[1],
        ]
        self.__grid_size_pix[0] = self.__spacing_pix[0] * self.__num_cols
        self.__grid_size_pix[1] = self.__spacing_pix[1] * self.__num_rows

        self.update_grid_draw_parameters()

    def set_osc_range(self, osc_range):
        """
        Sets osc range
        :param osc_range: (float,float)
        :return:
        """
        self.__osc_range = osc_range

    def set_end_position(self, pos_x, pos_y):
        """Actual drawing moment, when grid size is defined"""
        self.end_coord[0] = pos_x
        self.end_coord[1] = pos_y
        self.update_grid_draw_parameters(in_draw=True)

    def update_grid_draw_parameters(self, in_draw=False, adjust_size=True):
        """
        Updates grid parameters
        :param in_draw: boolean
        :param adjust_size: boolean
        :return:
        """

        # Create a copy of start and end coordinates
        # Using local copy of coordinates allows to account for a situation when
        # grid is drawn from other then top left corner
        start_coord = copy.copy(self.start_coord)
        end_coord = copy.copy(self.end_coord)

        if start_coord[0] > end_coord[0]:
            start_coord[0], end_coord[0] = end_coord[0], start_coord[0]

        if start_coord[1] > end_coord[1]:
            start_coord[1], end_coord[1] = end_coord[1], start_coord[1]

        if in_draw or not adjust_size:
            # Number of columns and rows is calculated
            num_cols = int(
                abs(self.start_coord[0] - self.end_coord[0]) / self.__spacing_pix[0]
            )
            num_rows = int(
                abs(self.start_coord[1] - self.end_coord[1]) / self.__spacing_pix[1]
            )

            if num_rows * num_cols > pow(2, 16):
                msg_text = (
                    "Unable to draw grid containing "
                    + "more than %d cells!" % pow(2, 16)
                )
                logging.getLogger("GUI").info(msg_text)
                return

            self.__num_cols = num_cols
            self.__num_rows = num_rows

            if in_draw:
                self.__grid_size_pix[0] = self.__spacing_pix[0] * self.__num_cols
                self.__grid_size_pix[1] = self.__spacing_pix[1] * self.__num_rows

                self.__center_coord.setX(start_coord[0] + self.__grid_size_pix[0] / 2.0)
                self.__center_coord.setY(start_coord[1] + self.__grid_size_pix[1] / 2.0)

        if in_draw or adjust_size:
            # if True:
            # Frame polygon is defined by 4 corner points:
            # 0 1
            # 3 2
            self.__frame_polygon.setPoint(
                GraphicsItemGrid.TOP_LEFT, start_coord[0], start_coord[1]
            )
            self.__frame_polygon.setPoint(
                GraphicsItemGrid.TOP_RIGHT,
                start_coord[0] + self.__grid_size_pix[0],
                start_coord[1],
            )
            self.__frame_polygon.setPoint(
                GraphicsItemGrid.BOT_LEFT,
                start_coord[0] + self.__grid_size_pix[0],
                start_coord[1] + self.__grid_size_pix[1],
            )
            self.__frame_polygon.setPoint(
                GraphicsItemGrid.BOT_RIGHT,
                start_coord[0],
                start_coord[1] + self.__grid_size_pix[1],
            )

            # self.__num_cols = int(self.__grid_size_pix[0] / self.__spacing_pix[0])
            # self.__num_rows = int(self.__grid_size_pix[1] / self.__spacing_pix[1])

        self.__grid_range_pix["fast"] = abs(
            self.grid_direction["fast"][0]
            * (self.__grid_size_pix[0] - self.__spacing_pix[0])
        ) + abs(
            self.grid_direction["fast"][1]
            * (self.__grid_size_pix[1] - self.__spacing_pix[1])
        )
        self.__grid_range_pix["slow"] = abs(
            self.grid_direction["slow"][0]
            * (self.__grid_size_pix[0] - self.__spacing_pix[0])
        ) + abs(
            self.grid_direction["slow"][1]
            * (self.__grid_size_pix[1] - self.__spacing_pix[1])
        )

        self.__num_lines = abs(self.grid_direction["fast"][1] * self.__num_cols) + abs(
            self.grid_direction["slow"][1] * self.__num_rows
        )
        self.__num_images_per_line = abs(
            self.grid_direction["fast"][0] * self.__num_cols
        ) + abs(self.grid_direction["slow"][0] * self.__num_rows)

        if min(self.__spacing_pix) >= 20:
            self.update_coordinate_map()

        self.scene().update()

    def update_coordinate_map(self):
        """
        Updates coordinated of the corner points
        :return:
        """
        self.__coordinate_map = []
        for image_index in range(self.__num_cols * self.__num_rows):
            line, image = self.get_line_image_num(image_index + self.__first_image_num)
            pos_x, pos_y = self.get_coord_from_line_image(line, image)
            col, row = self.get_col_row_from_line_image(line, image)
            self.__coordinate_map.append((line, image, pos_x, pos_y, col, row))

    def set_corner_coord(self, corner_coord):
        """
        Sets corner coordinates
        :param corner_coord: list of 4 coordinates (x, y)
        :return:
        """
        for index, coord in enumerate(corner_coord):
            self.__frame_polygon.setPoint(index, coord[0], coord[1])

        if self.__overlay_pixmap:
            if min(self.__spacing_pix) < 20:
                width = abs(corner_coord[0][0] - corner_coord[1][0])
                height = abs(corner_coord[0][1] - corner_coord[3][1])
                self.__overlay_pixmap.setPixmap(
                    self.__original_pixmap.scaled(width, height)
                )
                self.__overlay_pixmap.setVisible(True)
                self.__overlay_pixmap.setOpacity(self.__fill_alpha / 255.0)
                self.__overlay_pixmap.setPos(corner_coord[0][0], corner_coord[0][1])
            else:
                self.__overlay_pixmap.setVisible(False)

        self.__grid_size_pix[0] = self.__spacing_pix[0] * self.__num_cols
        self.__grid_size_pix[1] = self.__spacing_pix[1] * self.__num_rows
        self.scene().update()

    def set_overlay_pixmap(self, filename):
        """
        Sets overlay pixmap
        :param filename:
        :return:
        """
        if not self.__overlay_pixmap:
            self.__overlay_pixmap = qt_import.QGraphicsPixmapItem(self)
            self.__original_pixmap = qt_import.QPixmap(filename)
        else:
            self.__original_pixmap.load(filename)

        width, height = self.get_size_pix()
        self.__overlay_pixmap.setPixmap(self.__original_pixmap.scaled(width, height))
        self.__overlay_pixmap.setPos(
            self.__frame_polygon.point(0).x(), self.__frame_polygon.point(0).y()
        )
        self.__overlay_pixmap.setOpacity(self.__fill_alpha / 255.0)
        self.__overlay_pixmap.setVisible(min(self.__spacing_pix) < 20)

    def set_center_coord(self, center_coord):
        """
        Sets center coordinate
        :param center_coord: (int, int)
        :return:
        """
        self.__center_coord.setX(center_coord[0])
        self.__center_coord.setY(center_coord[1])
        self.update_coordinate_map()

    def set_spacing(self, spacing, adjust_size=False):
        """
        Sets spacing between scan cols and rows
        :param spacing: (float, float)
        :param adjust_size: boolean
        :return:
        """
        self.__spacing_mm[0] = spacing[0]
        self.__spacing_mm[1] = spacing[1]
        self.__spacing_pix[0] = self.pixels_per_mm[0] * self.__spacing_mm[0]
        self.__spacing_pix[1] = self.pixels_per_mm[1] * self.__spacing_mm[1]
        if adjust_size:
            self.__grid_size_pix[0] = self.__spacing_pix[0] * self.__num_cols
            self.__grid_size_pix[1] = self.__spacing_pix[1] * self.__num_rows

        self.update_grid_draw_parameters(adjust_size=adjust_size)

    def set_draw_mode(self, draw_mode):
        """
        Sets drawing mode
        :param draw_mode: boolean
        :return:
        """
        self.__draw_mode = draw_mode

    def is_draw_mode(self):
        """
        Returns True if the grid is in drawing process
        :return: boolean
        """
        return self.__draw_mode

    def set_projection_mode(self, mode):
        """
        Sets the projection mode
        :param mode: boolean
        :return:
        """
        self.__draw_projection = mode

    def get_properties(self):
        """
        Returns a dict with grid properties
        :return: dict
        """
        (dx_mm, dy_mm) = self.get_grid_range_mm()
        (fast_mm, slow_mm) = self.get_grid_scan_mm()
        return {
            "name": "Mesh %d" % (self.index + 1),
            "direction": self.grid_direction,
            "reversing_rotation": self.__reversing_rotation,
            "steps_x": self.__num_cols,
            "steps_y": self.__num_rows,
            "xOffset": self.__spacing_mm[0],
            "yOffset": self.__spacing_mm[1],
            "dx_mm": dx_mm,
            "dy_mm": dy_mm,
            "fast_mm": fast_mm,
            "slow_mm": slow_mm,
            "num_lines": self.__num_lines,
            "num_images_per_line": self.__num_images_per_line,
            "first_image_num": self.__first_image_num,
        }

    def update_auto_grid(self, beam_info, beam_position, spacing_mm):
        """
        Updated auto grid
        :param beam_info: dict with beam info
        :param beam_position: (int, int)
        :param spacing_mm: (float, float)
        :return:
        """
        self.set_beam_info(beam_info)
        self.beam_position = beam_position

        self.__spacing_mm = spacing_mm
        self.__spacing_pix = [
            self.__spacing_mm[0] * self.pixels_per_mm[0],
            self.__spacing_mm[1] * self.pixels_per_mm[1],
        ]

        self.__num_cols = int(self.auto_grid_size[0] / self.__spacing_mm[0])
        self.__num_rows = int(self.auto_grid_size[1] / self.__spacing_mm[1])

        self.__grid_size_pix[0] = self.__spacing_pix[0] * self.__num_cols
        self.__grid_size_pix[1] = self.__spacing_pix[1] * self.__num_rows

        self.__num_lines = abs(self.grid_direction["fast"][1] * self.__num_cols) + abs(
            self.grid_direction["slow"][1] * self.__num_rows
        )
        self.__num_images_per_line = abs(
            self.grid_direction["fast"][0] * self.__num_cols
        ) + abs(self.grid_direction["slow"][0] * self.__num_rows)

        self.set_center_coord(self.beam_position)

        self.update_grid_draw_parameters()

        self.__automatic = True
        self.__draw_projection = False

        self.__motor_pos_corner = []
        self.__motor_pos_corner.append(
            self.get_motor_pos_from_col_row(0, self.__num_rows)
        )
        self.__motor_pos_corner.append(
            self.get_motor_pos_from_col_row(self.__num_cols, self.__num_rows)
        )
        self.__motor_pos_corner.append(
            self.get_motor_pos_from_col_row(self.__num_cols, 0)
        )
        self.__motor_pos_corner.append(self.get_motor_pos_from_col_row(0, 0))
        self.update_item()

    def get_center_coord(self):
        """
        Returns center coordinates
        :return: (int, int)
        """
        return self.__center_coord.x(), self.__center_coord.y()

    def get_corner_coord(self):
        """
        Returns corner coordinates
        :return: list of 4 lists
        """
        point_list = []
        for index in range(4):
            point_list.append(self.__frame_polygon.point(index))
        return point_list

    def set_motor_pos_corner(self, motor_pos_corner):
        """
        Sets motor positions
        :param motor_pos_corner:
        :return:
        """
        self.__motor_pos_corner = motor_pos_corner

    def get_motor_pos_corner(self):
        """
        Returns motor positions associated to the grid coorners
        :return:
        """
        return self.__motor_pos_corner

    def set_centred_position(self, centred_position):
        """
        Sets centred position
        :param centred_position:
        :return:
        """
        self.__centred_position = centred_position
        self.__osc_start = self.__centred_position.phi

    def get_centred_position(self):
        """
        Returns centred positions. Used during the collection
        :return:
        """
        return self.__centred_position

    def set_score(self, score):
        """
        Sets score
        :param score: np two dimensional array
        :return:
        """
        self.__score = score

    def get_snapshot(self):
        """
        Returns grid snapshot
        :return:
        """
        return self.__snapshot

    def set_snapshot(self, snapshot):
        """
        Sets grid snapshot
        :param snapshot:
        :return:
        """
        self.__snapshot = snapshot

    def set_fill_alpha(self, value):
        """
        Sets the transparency level
        :param value:
        :return:
        """
        self.__fill_alpha = value
        if self.__overlay_pixmap:
            self.__overlay_pixmap.setOpacity(self.__fill_alpha / 255.0)
        else:
            self.base_color.setAlpha(self.__fill_alpha)

    def set_display_overlay(self, state):
        """
        Enables, disables display overlay
        :param state: boolean
        :return:
        """
        self.__display_overlay = state

    def set_base_color(self, color):
        """
        Sets base color
        :param color: QColor
        :return:
        """
        self.base_color = color
        self.base_color.setAlpha(self.__fill_alpha)
        self.scene().update()

    def paint(self, painter, option, widget):
        """
        Main pain method
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        self.custom_pen.setColor(qt_import.Qt.darkGray)
        self.custom_pen.setWidth(1)

        if self.__draw_mode:
            self.custom_pen.setStyle(qt_import.Qt.DashLine)
        if self.__draw_mode or self.isSelected():
            self.custom_pen.setColor(SELECTED_COLOR)
        # if self.used_count > 0:
        #    brush_color = LIGHT_GREEN
        # else:
        brush_color = self.base_color

        painter.setPen(self.custom_pen)
        self.custom_brush.setColor(brush_color)
        painter.setBrush(self.custom_brush)

        if self.__draw_projection:
            # In projection mode, just the frame is displayed
            painter.drawPolygon(self.__frame_polygon, qt_import.Qt.OddEvenFill)
        else:
            # Draws beam shape and displays number of image if
            # less than 1000 cells and size is greater than 20px
            if min(self.__spacing_pix) < 20:
                painter.drawPolygon(self.__frame_polygon, qt_import.Qt.OddEvenFill)
            else:
                for image_index in range(self.__num_cols * self.__num_rows):
                    # Estimate area where frame number or score will be displayed
                    (line, image, pos_x, pos_y, col, row) = self.__coordinate_map[
                        image_index
                    ]
                    paint_rect = qt_import.QRect(
                        pos_x - self.__spacing_pix[0] / 2,
                        pos_y - self.__spacing_pix[1] / 2,
                        self.__spacing_pix[0],
                        self.__spacing_pix[1],
                    )

                    # If score exists overlay color may change
                    cell_score = None
                    if self.__display_overlay:
                        cell_score = 1.0
                        if self.__score is not None:
                            cell_score = self.__score[image_index]

                            if self.__score.max() > 0:
                                cell_score = float(cell_score) / self.__score.max()
                                brush_color.setHsv(
                                    0 + 60 * cell_score,
                                    255,
                                    255 * cell_score,
                                    self.__fill_alpha,
                                )
                                self.custom_brush.setColor(brush_color)
                                painter.setBrush(self.custom_brush)
                            else:
                                painter.setBrush(qt_import.Qt.transparent)
                    else:
                        painter.setBrush(qt_import.Qt.transparent)

                    painter.drawText(
                        paint_rect,
                        qt_import.Qt.AlignCenter,
                        str(image_index + self.__first_image_num),
                    )
                    if self.beam_is_rectangle:
                        painter.drawRect(
                            pos_x - self.beam_size_pix[0] / 2,
                            pos_y - self.beam_size_pix[1] / 2,
                            self.beam_size_pix[0],
                            self.beam_size_pix[1],
                        )
                    else:
                        painter.drawEllipse(
                            int(pos_x - self.beam_size_pix[0] / 2),
                            int(pos_y - self.beam_size_pix[1] / 2),
                            int(self.beam_size_pix[0]),
                            int(self.beam_size_pix[1]),
                        )

        # Draws x in the middle of the grid
        coordx = int(self.__center_coord.x())
        coordy = int(self.__center_coord.y())
        painter.drawLine(coordx - 5, coordy - 5, coordx + 5, coordy + 5)
        painter.drawLine(coordx + 5, coordy - 5, coordx - 5, coordy + 5)

        if self.__automatic:
            grid_info = "Auto mesh %d" % (self.index + 1)
        else:
            grid_info = "Mesh %d" % (self.index + 1)

        painter.drawText(
            self.__frame_polygon.point(GraphicsItemGrid.TOP_RIGHT).x() + 10,
            self.__frame_polygon.point(GraphicsItemGrid.TOP_RIGHT).y(),
            grid_info,
        )
        painter.drawText(
            self.__frame_polygon.point(GraphicsItemGrid.TOP_RIGHT).x() + 10,
            self.__frame_polygon.point(GraphicsItemGrid.TOP_RIGHT).y() + 12,
            "%d lines" % self.__num_lines,
        )
        painter.drawText(
            self.__frame_polygon.point(GraphicsItemGrid.TOP_RIGHT).x() + 10,
            self.__frame_polygon.point(GraphicsItemGrid.TOP_RIGHT).y() + 24,
            "%d frames per line" % self.__num_images_per_line,
        )

    def move_by_pix(self, move_direction):
        """Moves grid by one pixel"""
        move_delta_x = 0
        move_delta_y = 0
        if move_direction == "left":
            move_delta_x = -1
        elif move_direction == "right":
            move_delta_x = 1
        elif move_direction == "up":
            move_delta_y = -1
        elif move_direction == "down":
            move_delta_y = 1

        for index in range(4):
            self.__frame_polygon.setPoint(
                index,
                self.__frame_polygon.point(index).x() + move_delta_x,
                self.__frame_polygon.point(index).y() + move_delta_y,
            )

        self.__center_coord.setX(self.__center_coord.x() + move_delta_x)
        self.__center_coord.setY(self.__center_coord.y() + move_delta_y)
        self.scene().update()

    def get_size_pix(self):
        """
        Returns size in pixels
        :return:
        """
        width_pix = self.__spacing_pix[0] * self.__num_cols
        height_pix = self.__spacing_pix[1] * self.__num_rows
        return (width_pix, height_pix)

    def get_line_image_num(self, image_number):
        """
        From serial frame (==image) number returns a number of line == grid coord.
        along scan slow direction, image == grid coord. along scan fast direction
        """

        line = int((image_number - self.__first_image_num) / self.__num_images_per_line)
        image = (
            image_number - self.__first_image_num - line * self.__num_images_per_line
        )
        return line, image

    def get_coord_from_line_image(self, line, image):
        """Returns the screen coordinates x, y in pixel, of a middle
        of the cell that correspoinds to
        number an frame #image in line #line
        """
        ref_fast, ref_slow = self.get_coord_ref_from_line_image(line, image)

        coord_x = (
            self.__center_coord.x()
            + self.__grid_range_pix["fast"] * self.grid_direction["fast"][0] * ref_fast
            + self.__grid_range_pix["slow"] * self.grid_direction["slow"][0] * ref_slow
        )
        coord_y = (
            self.__center_coord.y()
            + self.__grid_range_pix["fast"] * self.grid_direction["fast"][1] * ref_fast
            + self.__grid_range_pix["slow"] * self.grid_direction["slow"][1] * ref_slow
        )
        return coord_x, coord_y

    def get_coord_ref_from_line_image(self, line, image):
        """returns nameless constants used in conversion between
        scan and screen coordinates.
        """
        fast_ref = 0.5
        if self.__num_images_per_line > 1:
            fast_ref = 0.5 - float(image) / (self.__num_images_per_line - 1)
        if self.__reversing_rotation:
            fast_ref = pow(-1, line % 2) * fast_ref

        slow_ref = 0.5
        if self.__num_lines > 1:
            slow_ref = 0.5 - float(line) / (self.__num_lines - 1)
        return fast_ref, slow_ref

    def get_direction_parameters(self):
        """
        Calculates and returns direction parameters
        :return:
        """
        start_x, start_y = self.get_coord_from_line_image(0, 0)
        end_x, end_y = self.get_coord_from_line_image(0, 2)
        return {"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y}

    def get_image_from_col_row(self, col, row):
        """calculate image serial number, number of line and number of
        image in line from col and row col and row can be floats
        """
        image = int(
            self.__num_images_per_line / 2.0
            + self.grid_direction["fast"][0] * (self.__num_cols / 2.0 - col)
            - self.grid_direction["fast"][1] * (self.__num_rows / 2.0 - row)
        )
        line = int(
            self.__num_lines / 2.0
            + self.grid_direction["slow"][0] * (self.__num_cols / 2.0 - col)
            - self.grid_direction["slow"][1] * (self.__num_rows / 2.0 - row)
        )

        if self.__reversing_rotation and line % 2:
            image_serial = (
                self.__first_image_num
                + self.__num_images_per_line * (line + 1)
                - 1
                - image
            )
        else:
            image_serial = (
                self.__first_image_num + self.__num_images_per_line * line + image
            )

        return image, line, image_serial

    def get_col_row_from_image_serial(self, image_serial):
        """
        Returns col row based on serial image index
        :param image_serial: int, int
        :return:
        """
        line, image = self.get_line_image_num(image_serial)
        return self.get_col_row_from_line_image(line, image)

    def get_col_row_from_image(self, image_num):
        """
        Returns col row based on the image number
        :param image_num: int
        :return: int, int
        """
        (line, image, pos_x, pos_y, col, row) = self.__coordinate_map[image_num]
        return col, row

    def get_col_row_from_line_image(self, line, image):
        """converts frame grid coordinates from scan grid "slow","fast") to screen grid
        ("col","raw"), i.e. rotates/inverts the scan coordinates
        into grid coordinates.
        """
        ref_fast, ref_slow = self.get_coord_ref_from_line_image(line, image)

        col = (
            self.__num_cols / 2.0
            + (self.__num_images_per_line - 1)
            * self.grid_direction["fast"][0]
            * ref_fast
            + (self.__num_lines - 1) * self.grid_direction["slow"][0] * ref_slow
        )
        row = (
            self.__num_rows / 2.0
            + (self.__num_images_per_line - 1)
            * self.grid_direction["fast"][1]
            * ref_fast
            + (self.__num_lines - 1) * self.grid_direction["slow"][1] * ref_slow
        )
        return int(col), int(row)

    def get_motor_pos_from_col_row(self, col, row, as_cpos=False):
        """x = x(click - x_middle_of_the_plot), y== the same"""
        new_point = copy.deepcopy(self.__centred_position.as_dict())
        (hor_range, ver_range) = self.get_grid_size_mm()
        hor_range = -hor_range * (self.__num_cols / 2.0 - col) / self.__num_cols
        ver_range = -ver_range * (self.__num_rows / 2.0 - row) / self.__num_rows

        if self.grid_direction["fast"][0] == 1:
            # MD2 when fast direction is horizontal direction
            new_point["sampx"] = new_point["sampx"] + ver_range * math.sin(
                math.pi * (self.__osc_start - self.grid_direction["omega_ref"]) / 180.0
            )
            new_point["sampy"] = new_point["sampy"] - ver_range * math.cos(
                math.pi * (self.__osc_start - self.grid_direction["omega_ref"]) / 180.0
            )
            new_point["phiy"] = new_point["phiy"] - hor_range
            new_point["phi"] = (
                new_point["phi"]
                - self.__osc_range * self.__num_cols / 2
                + (self.__num_cols - col) * self.__osc_range
            )
        else:
            # MD3
            new_point["sampx"] = new_point["sampx"] - hor_range * math.sin(
                math.pi * (self.__osc_start - self.grid_direction["omega_ref"]) / 180.0
            )
            new_point["sampy"] = new_point["sampy"] + hor_range * math.cos(
                math.pi * (self.__osc_start - self.grid_direction["omega_ref"]) / 180.0
            )
            new_point["phiy"] = new_point["phiy"] + ver_range
            new_point["phi"] = (
                new_point["phi"]
                - self.__osc_range * self.__num_rows / 2
                + (self.__num_rows - row) * self.__osc_range
            )

        if as_cpos:
            return queue_model_objects.CentredPosition(new_point)
        else:
            return new_point


class GraphicsItemScale(GraphicsItem):
    """Displays vertical and horizontal scale on the bottom, left corner.
    Horizontal scale is scaled to 50 or 100 microns and
    vertical scale is two times shorter.
    """

    HOR_LINE_LEN_MICRONS = (300, 200, 100, 50, 30, 20, 10)
    HOR_LINE_LEN_MM = (10, 5, 2, 1)

    LOWER_LEFT, UPPER_LEFT = (0, 1)

    def __init__(self, parent, position_x=0, position_y=0, anchor=None):
        """
        Init
        :param parent:
        :param position_x: int
        :param position_y: int
        """
        GraphicsItem.__init__(self, parent, position_x=0, position_y=0)
        self.__scale_len = 0
        self.__scale_len_pix = 0
        self.__scale_unit = "\u00B5"
        self.__display_grid = False

        if anchor is None:
            anchor = GraphicsItemScale.LOWER_LEFT
        self.set_anchor(anchor)

        self.custom_pen_color = SELECTED_COLOR
        self.custom_pen.setWidth(3)
        self.custom_pen.setColor(self.custom_pen_color)

    def set_anchor(self, anchor_position):
        self.anchor_position = anchor_position

    def paint(self, painter, option, widget):
        """
        Main pain method
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        scene_width = self.scene().width()
        scene_height = self.scene().height()

        # self.custom_pen.setStyle(SOLID_LINE_STYLE)
        # self.custom_pen.setColor(self.custom_pen_color)
        painter.setPen(self.custom_pen)

        if self.anchor_position == GraphicsItemScale.LOWER_LEFT:
            line_horiz_coords = (
                7,
                self.start_coord[1] - 15,
                7 + self.__scale_len_pix,
                self.start_coord[1] - 15,
            )
            horiz_text_pos = (self.__scale_len_pix - 18, self.start_coord[1] - 20)

            line_vert_coords = (
                7,
                self.start_coord[1] - 15,
                7,
                self.start_coord[1] - 15 - self.__scale_len_pix / 2,
            )
            vert_text_pos = (12, self.start_coord[1] - 7 - self.__scale_len_pix / 2)
        elif self.anchor_position == GraphicsItemScale.UPPER_LEFT:
            line_horiz_coords = (7, 15, 7 + self.__scale_len_pix, 15)
            horiz_text_pos = (self.__scale_len_pix + 18, 20)
            line_vert_coords = (7, 15, 7, 15 + self.__scale_len_pix / 2)
            vert_text_pos = (12, 7 + self.__scale_len_pix / 2)

        x0, y0, x1, y1 = line_horiz_coords
        painter.drawLine(int(x0), int(y0), int(x1), int(y1))

        x0, y0 = horiz_text_pos
        painter.drawText(
            int(x0), int(y0), "%d %s" % (self.__scale_len, self.__scale_unit)
        )

        x0, y0, x1, y1 = line_vert_coords
        painter.drawLine(int(x0), int(y0), int(x1), int(y1))

        x0, y0 = vert_text_pos
        painter.drawText(
            int(x0), int(y0), "%d %s" % (self.__scale_len / 2, self.__scale_unit)
        )

        if self.__display_grid:
            self.custom_pen.setStyle(qt_import.Qt.DotLine)
            self.custom_pen.setWidth(1)
            self.custom_pen.setColor(qt_import.Qt.gray)
            painter.setPen(self.custom_pen)
            halfwidth = int(scene_width / 2)
            halfheight = int(scene_height / 2)
            for line in range(1, 3):
                painter.drawLine(
                    halfwidth + line * 80,
                    halfheight - 20 * line,
                    halfwidth + line * 80,
                    halfheight + 20 * line,
                )
                painter.drawLine(
                    halfwidth - line * 80,
                    halfheight - 20 * line,
                    halfwidth - line * 80,
                    halfheight + 20 * line,
                )

                painter.drawLine(
                    halfwidth - line * 30,
                    halfheight - 50 * line,
                    halfwidth + line * 30,
                    halfheight - 50 * line,
                )
                painter.drawLine(
                    halfwidth - line * 30,
                    halfheight + 50 * line,
                    halfwidth + line * 30,
                    halfheight + 50 * line,
                )

            self.custom_pen.setStyle(qt_import.Qt.DashLine)
            self.custom_pen.setWidth(1)
            self.custom_pen.setColor(qt_import.Qt.yellow)
            painter.setPen(self.custom_pen)
            painter.drawLine(
                halfwidth - 20,
                halfheight,
                halfwidth + 20,
                halfheight,
            )
            painter.drawLine(
                halfwidth,
                halfheight - 20,
                halfwidth,
                halfheight + 20,
            )

    def set_pixels_per_mm(self, pixels_per_mm):
        """
        Updates pixel per mm and chooses scale length and unit
        :param pixels_per_mm: (float, float)
        :return:
        """
        self.pixels_per_mm = pixels_per_mm
        for line_len in GraphicsItemScale.HOR_LINE_LEN_MICRONS:
            if (
                self.pixels_per_mm[0] * line_len / 1000 <= 200
                and self.pixels_per_mm[0] * line_len / 1000 > 50
            ):
                self.__scale_len = line_len
                self.__scale_unit = "\u00B5"
                self.__scale_len_pix = int(
                    self.pixels_per_mm[0] * self.__scale_len / 1000
                )
                return

        for line_len in GraphicsItemScale.HOR_LINE_LEN_MM:
            if self.pixels_per_mm[0] * line_len <= 200:
                self.__scale_len = line_len
                self.__scale_unit = "mm"
                self.__scale_len_pix = int(self.pixels_per_mm[0] * self.__scale_len)
                return

    def set_start_position(self, position_x, position_y):
        """
        Sets the starting position of the scale
        :param position_x: int
        :param position_y: int
        :return:
        """
        if position_x is not None and position_y is not None:
            self.start_coord[0] = int(position_x)
            self.start_coord[1] = int(position_y)

    def set_display_grid(self, display_grid):
        """
        Display grid
        :param display_grid:
        :return:
        """
        self.__display_grid = display_grid


class GraphicsItemOmegaReference(GraphicsItem):
    """Reference line of the rotation axis"""

    def __init__(self, parent):
        """
        Init
        :param parent:
        """
        GraphicsItem.__init__(self, parent)
        self.phi_position = None

    def paint(self, painter, option, widget):
        """
        Main pain method
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        painter.setPen(self.custom_pen)
        painter.drawLine(
            self.start_coord[0],
            self.start_coord[1],
            self.end_coord[0],
            self.end_coord[1],
        )
        if self.phi_position:
            painter.drawText(
                self.end_coord[0] - 40,
                self.end_coord[1] - 10,
                "%d %s" % (self.phi_position, "\u00b0"),
            )

    def set_phi_position(self, phi_position):
        """
        Updates phi position
        :param phi_position:
        :return:
        """
        self.phi_position = phi_position

    def set_reference(self, omega_reference):
        """
        Sets omega reference and defines if the axis is vertical or horizontal
        :param omega_reference: (int, int)
        :return:
        """
        if omega_reference[0] > 0:
            # Omega reference is a vertical axis
            self.start_coord = [int(omega_reference[0]), 0]
            self.end_coord = [int(omega_reference[0]), self.scene().height()]
        else:
            self.start_coord = [0, int(omega_reference[1])]
            self.end_coord = [self.scene().width(), int(omega_reference[1])]


class GraphicsItemText(GraphicsItem):
    """Reference line of the rotation axis"""

    def __init__(self, parent, pos_x=0, pos_y=0):
        """
        Init
        :param parent:
        :param pos_x: int
        :param pos_y: int
        """
        GraphicsItem.__init__(self, parent)

        self.pos_x = pos_x
        self.pos_y = pos_y
        self.text = ""

    def paint(self, painter, option, widget):
        """
        Main pain method
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        painter.setPen(self.custom_pen)
        painter.drawText(self.pos_x, self.pos_y, self.text)

    def set_text(self, text):
        """
        Updates text to be drawen
        :param text: str
        :return:
        """
        self.text = text


class GraphicsSelectTool(GraphicsItem):
    """Draws a rectangle and selects centring points"""

    def __init__(self, parent):
        """
        Init
        :param parent:
        """
        GraphicsItem.__init__(self, parent)

        self.custom_pen.setColor(SELECTED_COLOR)

    def paint(self, painter, option, widget):
        """
        Main pain class. Draws a selection rectangle
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        painter.setPen(self.custom_pen)
        painter.drawRect(
            min(self.start_coord[0], self.end_coord[0]),
            min(self.start_coord[1], self.end_coord[1]),
            abs(self.start_coord[0] - self.end_coord[0]),
            abs(self.start_coord[1] - self.end_coord[1]),
        )


class GraphicsItemCentringLines(GraphicsItem):
    """Centring lines are displayed during the 3-click centering"""

    def __init__(self, parent):
        """
        Init
        :param parent:
        """
        GraphicsItem.__init__(self, parent)

        self.custom_pen.setColor(NORMAL_COLOR)
        self.centring_points = []

    def paint(self, painter, option, widget):
        """
        Draws two perpendicular centering lines
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        painter.setPen(self.custom_pen)
        painter.drawLine(
            self.start_coord[0], 0, self.start_coord[0], self.scene().height()
        )
        painter.drawLine(
            0, self.start_coord[1], self.scene().width(), self.start_coord[1]
        )
        """
        if len(self.centring_points) in (0, 1):
            painter.drawText(self.start_coord[0] + 10,
                             self.start_coord[1] - 10,
                             "%d clicks left" % (3 - len(self.centring_points)))
        elif len(self.centring_points) == 2:
            painter.drawText(self.start_coord[0] + 10,
                             self.start_coord[1] - 10,
                             "1 click left")
        """
        for centring_point in self.centring_points:
            painter.drawLine(
                centring_point[0] - 3,
                centring_point[1] - 3,
                centring_point[0] + 3,
                centring_point[1] + 3,
            )
            painter.drawLine(
                centring_point[0] - 3,
                centring_point[1] + 3,
                centring_point[0] + 3,
                centring_point[1] - 3,
            )

    def add_position(self, pos_x, pos_y):
        """
        Adds centering position
        :param pos_x:
        :param pos_y:
        :return:
        """
        self.centring_points.append((pos_x, pos_y))


class GraphicsItemHistogram(GraphicsItem):
    """Centring lines are displayed during the 3-click centering"""

    def __init__(self, parent):
        """
        Init
        :param parent:
        """
        GraphicsItem.__init__(self, parent)
        self.hor_painter_path = None
        self.ver_painter_path = None

    def paint(self, painter, option, widget):
        """
        Paint histogram
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        self.custom_pen.setStyle(SOLID_LINE_STYLE)
        self.custom_pen.setColor(SELECTED_COLOR)
        painter.setPen(self.custom_pen)

        painter.drawPath(self.hor_painter_path)
        painter.drawPath(self.ver_painter_path)

    def update_histogram(self, hor_array, ver_array):
        """
        Updates histogram
        :param hor_array: numpy array
        :param ver_array: numpy array
        :return:
        """
        scene_height = self.scene().height()

        self.hor_painter_path = qt_import.QPainterPath()
        self.ver_painter_path = qt_import.QPainterPath()

        for x, y in enumerate(hor_array):
            if x == 0:
                self.hor_painter_path.moveTo(x, scene_height - 50 * y / hor_array.max())
            self.hor_painter_path.lineTo(x, scene_height - 50 * y / hor_array.max())

        for y, x in enumerate(ver_array):
            if y == 0:
                self.ver_painter_path.moveTo(5 + 50 * x / ver_array.max(), y)
            self.ver_painter_path.lineTo(5 + 50 * x / ver_array.max(), y)


class GraphicsItemMoveBeamMark(GraphicsItem):
    """Tool to move beam mark to a new location"""

    def __init__(self, parent):
        """
        Init
        :param parent:
        """
        GraphicsItem.__init__(self, parent)

        self.custom_pen.setColor(SELECTED_COLOR)

    def paint(self, painter, option, widget):
        """
        Paints beam mark at the user defined position
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        self.custom_pen.setStyle(SOLID_LINE_STYLE)
        painter.setPen(self.custom_pen)
        painter.drawLine(
            self.start_coord[0],
            self.start_coord[1],
            self.end_coord[0],
            self.end_coord[1],
        )
        if self.beam_size_pix:
            self.custom_pen.setStyle(qt_import.Qt.DashLine)
            painter.setPen(self.custom_pen)
            painter.drawEllipse(
                int(self.end_coord[0] - self.beam_size_pix[0] / 2),
                int(self.end_coord[1] - self.beam_size_pix[1] / 2),
                int(self.beam_size_pix[0]),
                int(self.beam_size_pix[1]),
            )


class GraphicsItemBeamDefine(GraphicsItem):
    """Tool to define beam size with slits.
    Draw a rectange to define width and height.
    After drawing move diffractometer to the center of the rect.
    """

    def __init__(self, parent):
        """
        Init
        :param parent:
        """
        GraphicsItem.__init__(self, parent)

        self.center_coord = [0, 0]
        self.width_microns = 0
        self.height_microns = 0

    def paint(self, painter, option, widget):
        """
        Paints a rectangle that will define beam size
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        self.custom_pen.setColor(SELECTED_COLOR)
        painter.setPen(self.custom_pen)
        painter.setBrush(self.custom_brush)
        painter.drawRect(
            min(self.start_coord[0], self.end_coord[0]),
            min(self.start_coord[1], self.end_coord[1]),
            abs(self.start_coord[0] - self.end_coord[0]),
            abs(self.start_coord[1] - self.end_coord[1]),
        )
        painter.drawText(
            self.end_coord[0] + 7,
            self.end_coord[1],
            "%d x %d %sm" % (self.width_microns, self.height_microns, "\u00B5"),
        )

        self.custom_pen.setColor(qt_import.Qt.red)
        painter.setPen(self.custom_pen)
        painter.drawLine(
            self.center_coord[0] - 10,
            self.center_coord[1],
            self.center_coord[0] + 10,
            self.center_coord[1],
        )
        painter.drawLine(
            self.center_coord[0],
            self.center_coord[1] - 10,
            self.center_coord[0],
            self.center_coord[1] + 10,
        )

    def set_end_position(self, position_x, position_y):
        """
        Sets draw end position
        :param position_x:
        :param position_y:
        :return:
        """
        self.end_coord[0] = position_x
        self.end_coord[1] = position_y

        pix_width = max(self.start_coord[0], self.end_coord[0]) - min(
            self.start_coord[0], self.end_coord[0]
        )
        pix_height = max(self.start_coord[1], self.end_coord[1]) - min(
            self.start_coord[1], self.end_coord[1]
        )
        self.center_coord[0] = (
            min(self.start_coord[0], self.end_coord[0]) + pix_width / 2
        )
        self.center_coord[1] = (
            min(self.start_coord[1], self.end_coord[1]) + pix_height / 2
        )
        self.width_microns = pix_width / self.pixels_per_mm[0] * 1000
        self.height_microns = pix_height / self.pixels_per_mm[1] * 1000

        self.scene().update()


class GraphicsItemMeasureDistance(GraphicsItem):
    """Item to measure distance between to points"""

    def __init__(self, parent):
        """
        Init
        :param parent:
        """
        GraphicsItem.__init__(self, parent)

        self.setFlags(qt_import.QGraphicsItem.ItemIsSelectable)
        self.do_measure = None
        self.measure_unit = "\u00B5"
        self.measure_points = None
        self.measured_distance = None
        self.custom_pen_color = SELECTED_COLOR
        self.custom_pen.setColor(self.custom_pen_color)

    def paint(self, painter, option, widget):
        """
        Main pain method
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        painter.setPen(self.custom_pen)
        painter.drawLine(self.measure_points[0], self.measure_points[1])
        painter.drawText(
            self.measure_points[1].x() + 15,
            self.measure_points[1].y() + 10,
            "%.2f %s" % (self.measured_distance, self.measure_unit),
        )

    def set_start_position(self, position_x, position_y):
        """
        Sets start position
        :param position_x: int
        :param position_y: int
        :return:
        """
        self.measured_distance = 0
        self.measure_points = []
        self.measure_points.append(qt_import.QPoint(position_x, position_y))
        self.measure_points.append(qt_import.QPoint(position_x, position_y))

    def set_coord(self, coord):
        """
        Adds new coordinate
        :param coord: (int, int)
        :return:
        """
        self.measure_points[len(self.measure_points) - 1].setX(coord[0])
        self.measure_points[len(self.measure_points) - 1].setY(coord[1])
        if len(self.measure_points) == 2:
            self.measured_distance = (
                math.sqrt(
                    pow(
                        (self.measure_points[0].x() - self.measure_points[1].x())
                        / self.pixels_per_mm[0],
                        2,
                    )
                    + pow(
                        (self.measure_points[0].y() - self.measure_points[1].y())
                        / self.pixels_per_mm[1],
                        2,
                    )
                )
                * 1000
            )
            if self.measured_distance > 1000:
                self.measured_distance /= 1000
                self.measure_unit = "mm"
            else:
                self.measure_unit = "\u00B5"
            self.scene().update()

    def store_coord(self, position_x, position_y):
        """
        Stores coordinate
        :param position_x: int
        :param position_y: int
        :return:
        """
        if len(self.measure_points) == 2:
            measured_pixels = math.sqrt(
                pow((self.measure_points[0].x() - self.measure_points[1].x()), 2)
                + pow((self.measure_points[0].y() - self.measure_points[1].y()), 2)
            )
            self.scene().measureItemChanged.emit(
                self.measure_points, int(measured_pixels)
            )
        elif len(self.measure_points) == 3:
            self.measure_points = []
            self.measure_points.append(qt_import.QPoint(position_x, position_y))

        self.measure_points.append(qt_import.QPoint(position_x, position_y))


class GraphicsItemMeasureAngle(GraphicsItem):
    """Item to measure angle between two vectors"""

    def __init__(self, parent):
        """
        Init
        :param parent:
        """
        GraphicsItem.__init__(self, parent)

        self.measure_points = None
        self.measured_angle = None
        self.setFlags(qt_import.QGraphicsItem.ItemIsSelectable)

        self.custom_pen.setColor(SELECTED_COLOR)

    def paint(self, painter, option, widget):
        """
        Main pain method
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        painter.setPen(self.custom_pen)
        if len(self.measure_points) > 1:
            painter.drawLine(self.measure_points[0], self.measure_points[1])
            if len(self.measure_points) > 2:
                painter.drawLine(self.measure_points[1], self.measure_points[2])
                painter.drawText(
                    self.measure_points[2].x() + 10,
                    self.measure_points[2].y() + 10,
                    "%.2f %s" % (self.measured_angle, "\u00B0"),
                )

    def set_start_position(self, position_x, position_y):
        """
        Sets start position
        :param position_x: int
        :param position_y: int
        :return:
        """
        self.measured_angle = 0
        self.measure_points = []
        self.measure_points.append(qt_import.QPoint(position_x, position_y))
        self.measure_points.append(qt_import.QPoint(position_x, position_y))

    def set_coord(self, coord):
        """
        Adds new coordinate and measures the angle between two vectors
        :param coord: (int, int)
        :return:
        """
        self.measure_points[len(self.measure_points) - 1].setX(coord[0])
        self.measure_points[len(self.measure_points) - 1].setY(coord[1])
        if len(self.measure_points) == 3:
            self.measured_angle = -math.degrees(
                math.atan2(
                    self.measure_points[2].y() - self.measure_points[1].y(),
                    self.measure_points[2].x() - self.measure_points[1].x(),
                )
                - math.atan2(
                    self.measure_points[0].y() - self.measure_points[1].y(),
                    self.measure_points[0].x() - self.measure_points[1].x(),
                )
            )
            self.scene().update()

    def store_coord(self, position_x, position_y):
        """Stores coordinate"""
        if len(self.measure_points) == 4:
            self.measure_points = []
            self.measure_points.append(qt_import.QPoint(position_x, position_y))
        self.measure_points.append(qt_import.QPoint(position_x, position_y))


class GraphicsItemMeasureArea(GraphicsItem):
    """Item to measure area"""

    def __init__(self, parent):
        """
        Init
        :param parent:
        """
        GraphicsItem.__init__(self, parent)

        self.measured_area = None
        self.current_point = None
        self.last_point_set = None
        self.setFlags(qt_import.QGraphicsItem.ItemIsSelectable)
        self.measure_polygon = qt_import.QPolygon()
        self.current_point = qt_import.QPoint(0, 0)
        self.min_max_coord = None

    def paint(self, painter, option, widget):
        """
        Paints a polygon and displays measured area
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        self.custom_pen.setStyle(SOLID_LINE_STYLE)
        self.custom_pen.setColor(SELECTED_COLOR)
        painter.setPen(self.custom_pen)
        painter.setBrush(self.custom_brush)

        painter.drawLine(self.measure_polygon.last(), self.current_point)
        painter.drawPolygon(self.measure_polygon, qt_import.Qt.OddEvenFill)
        painter.drawText(
            self.current_point.x() + 10,
            self.current_point.y() + 10,
            "%.2f %s" % (self.measured_area, "\u00B5"),
        )

        if self.min_max_coord:
            hor_size = (
                abs(self.min_max_coord[0][0] - self.min_max_coord[1][0])
                / self.pixels_per_mm[0]
                * 1000
            )
            ver_size = (
                abs(self.min_max_coord[0][1] - self.min_max_coord[1][1])
                / self.pixels_per_mm[1]
                * 1000
            )
            painter.drawLine(
                self.min_max_coord[0][0] - 10,
                self.min_max_coord[0][1],
                self.min_max_coord[0][0] - 10,
                self.min_max_coord[1][1],
            )
            painter.drawText(
                self.min_max_coord[0][0] - 40,
                self.min_max_coord[0][1],
                "%.1f %s" % (ver_size, "\u00B5"),
            )
            painter.drawLine(
                self.min_max_coord[0][0],
                self.min_max_coord[1][1] + 10,
                self.min_max_coord[1][0],
                self.min_max_coord[1][1] + 10,
            )
            painter.drawText(
                self.min_max_coord[1][0],
                self.min_max_coord[1][1] + 25,
                "%.1f %s" % (hor_size, "\u00B5"),
            )

    def set_start_position(self, pos_x, pos_y):
        """
        Sets start position
        :param pos_x: int
        :param pos_y: int
        :return:
        """
        self.min_max_coord = None
        self.measured_area = 0
        self.measure_polygon.clear()
        self.measure_polygon.append(qt_import.QPoint(pos_x, pos_y))
        self.current_point = qt_import.QPoint(pos_x, pos_y)

    def set_coord(self, coord):
        """
        Sets coordinate
        :param coord: (int, int)
        :return:
        """
        if not self.last_point_set:
            self.current_point.setX(coord[0])
            self.current_point.setY(coord[1])
            self.scene().update()

    def store_coord(self, last=None):
        """
        Stores coordinate and measures area
        :param last:
        :return:
        """
        self.last_point_set = last
        self.measure_polygon.append(self.current_point)
        if self.min_max_coord is None:
            self.min_max_coord = [
                [self.measure_polygon.value(0).x(), self.measure_polygon.value(0).y()],
                [self.measure_polygon.value(0).x(), self.measure_polygon.value(0).y()],
            ]
        for point_index in range(1, self.measure_polygon.count()):
            if self.measure_polygon.value(point_index).x() < self.min_max_coord[0][0]:
                self.min_max_coord[0][0] = self.measure_polygon.value(point_index).x()
            elif self.measure_polygon.value(point_index).x() > self.min_max_coord[1][0]:
                self.min_max_coord[1][0] = self.measure_polygon.value(point_index).x()
            if self.measure_polygon.value(point_index).y() < self.min_max_coord[0][1]:
                self.min_max_coord[0][1] = self.measure_polygon.value(point_index).y()
            elif self.measure_polygon.value(point_index).y() > self.min_max_coord[1][1]:
                self.min_max_coord[1][1] = self.measure_polygon.value(point_index).y()
        if self.measure_polygon.count() > 2:
            self.measured_area = 0
            for point_index in range(self.measure_polygon.count() - 1):
                self.measured_area += (
                    self.measure_polygon.value(point_index).x()
                    * self.measure_polygon.value(point_index + 1).y()
                )
                self.measured_area -= (
                    self.measure_polygon.value(point_index + 1).x()
                    * self.measure_polygon.value(point_index).y()
                )
            self.measured_area += (
                self.measure_polygon.value(len(self.measure_polygon) - 1).x()
                * self.measure_polygon.value(0).y()
            )
            self.measured_area -= (
                self.measure_polygon.value(0).x()
                * self.measure_polygon.value(len(self.measure_polygon) - 1).y()
            )
            self.measured_area = abs(
                self.measured_area
                / (2 * self.pixels_per_mm[0] * self.pixels_per_mm[1])
                * 1e6
            )
        self.scene().update()


class GraphicsItemMoveButton(GraphicsItem):
    """Move buttons"""

    def __init__(self, parent, direction):
        """
        Init
        :param parent:
        :param direction:
        """
        GraphicsItem.__init__(self, parent)

        self.setAcceptHoverEvents(True)
        self.direction = direction
        self.item_hover = False
        self.arrow_polygon = qt_import.QPolygon()
        self.set_size(20, 20)

        if direction == "up":
            self.setPos(25, 5)
            points = ((10, 0), (20, 19), (10, 15), (0, 19), (10, 0))
        elif direction == "right":
            points = ((1, 0), (20, 10), (1, 20), (5, 10), (1, 0))
            self.setPos(45, 25)
        elif direction == "down":
            points = ((0, 1), (10, 5), (20, 1), (10, 20), (0, 1))
            self.setPos(25, 45)
        elif direction == "left":
            points = ((0, 10), (19, 0), (15, 10), (19, 20), (0, 10))
            self.setPos(5, 25)

        for point in points:
            self.arrow_polygon.append(qt_import.QPoint(*point))

    def boundingRect(self):
        """Returns bounding rect
        :returns: QRect
        """
        return self.rect

    def paint(self, painter, option, widget):
        """
        Main pain method
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        self.custom_pen.setStyle(SOLID_LINE_STYLE)
        painter.setPen(self.custom_pen)
        painter.setBrush(self.custom_brush)

        painter.drawPolygon(self.arrow_polygon, qt_import.Qt.OddEvenFill)
        if self.item_hover:
            self.custom_brush.setColor(NORMAL_COLOR)
        else:
            self.custom_brush.setColor(qt_import.QColor(70, 70, 165, 40))
        painter.drawPolygon(self.arrow_polygon, qt_import.Qt.OddEvenFill)

    def hoverEnterEvent(self, event):
        """
        Event if mouse hovers overt the item
        :param event:
        :return:
        """
        self.item_hover = True
        qt_import.QGraphicsItem.hoverEnterEvent(self, event)

    def hoverLeaveEvent(self, event):
        """
        Event when mouse leaves the item
        :param event:
        :return:
        """
        self.item_hover = False
        qt_import.QGraphicsItem.hoverLeaveEvent(self, event)

    def mousePressEvent(self, event):
        """
        Event when user clicks on the item
        :param event:
        :return:
        """
        self.scene().moveItemClickedSignal.emit(self.direction)
        qt_import.QGraphicsItem.mousePressEvent(self, event)


class GraphicsMagnificationItem(GraphicsItem):
    """Magnification tool"""

    def __init__(self, parent):
        """
        Init
        :param parent:
        """
        GraphicsItem.__init__(self, parent)

        self.graphics_pixmap = qt_import.QPixmap()
        self.scale = 3
        self.area_size = 50

    def paint(self, painter, option, widget):
        """
        Draws a small rectangle with a scaled image
        :param painter:
        :param option:
        :param widget:
        :return:
        """
        self.custom_pen.setColor(SELECTED_COLOR)
        painter.setPen(self.custom_pen)
        # painter.setBrush(self.custom_brush)

        if self.end_coord[0] > (
            self.scene().width() - self.area_size * self.scale + self.area_size / 2.0
        ):
            offset_x = -self.area_size * (self.scale + 1)
        else:
            offset_x = self.area_size / 2.0 + 20
        if self.end_coord[1] > (
            self.scene().height() - self.area_size * self.scale + self.area_size / 2.0
        ):
            offset_y = -self.area_size * (self.scale + 1)
        else:
            offset_y = self.area_size / 2.0 + 20

        painter.drawRect(
            self.end_coord[0] - self.area_size / 2.0,
            self.end_coord[1] - self.area_size / 2.0,
            self.area_size,
            self.area_size,
        )
        painter.drawPixmap(
            self.end_coord[0] + offset_x,
            self.end_coord[1] + offset_y,
            self.area_size * self.scale,
            self.area_size * self.scale,
            self.graphics_pixmap,
        )

    def set_pixmap(self, pixmap_image):
        """
        Sets the pixmap
        :param pixmap_image: QPixmap
        :return:
        """
        self.graphics_pixmap = pixmap_image.copy(
            self.end_coord[0] - self.area_size / 2.0,
            self.end_coord[1] - self.area_size / 2.0,
            self.area_size,
            self.area_size,
        ).scaled(self.area_size * self.scale, self.area_size * self.scale)

    def set_properties(self, property_dict):
        """
        Sets the magnification properties
        :param property_dict:
        :return:
        """
        self.scale = property_dict.get("scale", 3)
        self.area_size = property_dict.get("area_size", 50)


class GraphicsView(qt_import.QGraphicsView):
    """
    Custom GraphicsView
    """

    mouseMovedSignal = qt_import.pyqtSignal(int, int)
    keyPressedSignal = qt_import.pyqtSignal(str)
    wheelSignal = qt_import.pyqtSignal(int)

    def __init__(self, parent=None):
        """
        Init
        :param parent:
        """
        super(GraphicsView, self).__init__(parent)

        self.graphics_scene = GraphicsScene(self)
        self.setScene(self.graphics_scene)
        self.graphics_scene.clearSelection()
        self.setMouseTracking(True)
        self.setDragMode(qt_import.QGraphicsView.RubberBandDrag)
        # self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(qt_import.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(qt_import.Qt.ScrollBarAlwaysOff)

        """
        self.setToolTip("Keyboard shortcuts:\n" + \
                        "  Ctrl+1 : 3 click centring\n" + \
                        "  Ctrl+2 : Save centring point\n" + \
                        "  Ctrl+L : Create line\n" + \
                        "  Ctrl+G : Start grid drawing\n\n" + \
                        "  Ctrl+A : Select all centring points\n" + \
                        "  Ctrl+D : Deselect all items\n" + \
                        "  Ctrl+X : Delete all items\n\n" + \
                        "  + : Zoom in\n" + \
                        "  - : Zoom out\n\n" + \
                        "Mouse wheel : Rotate omega")
        """

    def mouseMoveEvent(self, event):
        """
        Mouse move event
        :param event:
        :return:
        """
        self.mouseMovedSignal.emit(event.x(), event.y())
        self.update()
        qt_import.QGraphicsView.mouseMoveEvent(self, event)

    def keyPressEvent(self, event):
        """
        Key press event
        :param event:
        :return:
        """
        if event.key() in (qt_import.Qt.Key_Delete, qt_import.Qt.Key_Backspace):
            self.keyPressedSignal.emit("Delete")
        elif event.key() == qt_import.Qt.Key_Escape:
            self.keyPressedSignal.emit("Escape")
        elif event.key() == qt_import.Qt.Key_Up:
            self.scene().moveItemClickedSignal.emit("up")
            # self.keyPressedSignal.emit("Up")
        elif event.key() == qt_import.Qt.Key_Down:
            self.scene().moveItemClickedSignal.emit("down")
            # self.keyPressedSignal.emit("Down")
        elif event.key() == qt_import.Qt.Key_Left:
            self.scene().moveItemClickedSignal.emit("left")
        elif event.key() == qt_import.Qt.Key_Right:
            self.scene().moveItemClickedSignal.emit("right")
        elif event.key() == qt_import.Qt.Key_Plus:
            self.keyPressedSignal.emit("Plus")
        elif event.key() == qt_import.Qt.Key_Minus:
            self.keyPressedSignal.emit("Minus")

    def toggle_scrollbars_enable(self, state):
        """
        Defines scrollbar behaviour
        :param state:
        :return:
        """
        if state:
            self.setHorizontalScrollBarPolicy(qt_import.Qt.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(qt_import.Qt.ScrollBarAsNeeded)
        else:
            self.setHorizontalScrollBarPolicy(qt_import.Qt.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(qt_import.Qt.ScrollBarAlwaysOff)

    def wheelEvent(self, event):
        """
        Wheel event
        :param event:
        :return:
        """
        try:
            delta = event.angleDelta().y()
        except:
            delta = event.delta()
        self.wheelSignal.emit(delta)

        """
        //Get the original screen centerpoint
        QPointF screenCenter = GetCenter(); //CurrentCenterPoint; //(visRect.center());
        ui->graphicsView->setTransformationAnchor(QGraphicsView::AnchorUnde rMouse);
        //Scale the view ie. do the zoom
        double scaleFactor = 1.15; //How fast we zoom
        if(event->delta() > 0) {
        //Zoom in
        ui->graphicsView->scale(scaleFactor, scaleFactor);
        } else {
        //Zooming out
        ui->graphicsView->scale(1.0 / scaleFactor, 1.0 / scaleFactor);
        }
        ui->graphicsView->setTransformationAnchor(QGraphicsView::NoAnchor );
        //Get the position after scaling, in scene coords
        QPointF pointAfterScale(ui->graphicsView->mapToScene(event->pos()));

        //Get the offset of how the screen moved
        QPointF offset = pointBeforeScale - pointAfterScale;

        //Adjust to the new center for correct zooming
        QPointF newCenter = screenCenter + offset;
        SetCenter(newCenter);
        """


class GraphicsScene(qt_import.QGraphicsScene):
    """
    Implemented signals:
    - mouseClickedSignal (pos_x, pos_y, is left key)
    - mouseDoubleClickedSignal (pos_x, pos_y)
    - mouseReleasedSignal (pos_x, pos_y)
    - itemDoubleClickedSignal (GraphicsItem)
    - itemClickedSignal (GraphicsItem, isSelected)
    """

    mouseClickedSignal = qt_import.pyqtSignal(int, int, bool)
    mouseDoubleClickedSignal = qt_import.pyqtSignal(int, int)
    mouseReleasedSignal = qt_import.pyqtSignal(int, int)
    itemDoubleClickedSignal = qt_import.pyqtSignal(GraphicsItem)
    itemClickedSignal = qt_import.pyqtSignal(GraphicsItem, bool)
    moveItemClickedSignal = qt_import.pyqtSignal(str)
    measureItemChanged = qt_import.pyqtSignal(list, int)

    def __init__(self, parent=None):
        """
        Init
        :param parent:
        """
        super(GraphicsScene, self).__init__(parent)

        self.image_scale = 1


class GraphicsCameraFrame(qt_import.QGraphicsPixmapItem):
    """
    Camera frame class
    """

    def __init__(self, parent=None):
        """
        Init
        :param parent:
        """
        super(GraphicsCameraFrame, self).__init__(parent)

    def mousePressEvent(self, event):
        """
        Mouse press event
        :param event:
        :return:
        """
        position = qt_import.QPointF(event.scenePos())
        self.scene().mouseClickedSignal.emit(
            position.x(), position.y(), event.button() == qt_import.Qt.LeftButton
        )
        self.update()

    def mouseDoubleClickEvent(self, event):
        """
        Mouse double click event
        :param event:
        :return:
        """
        position = qt_import.QPointF(event.scenePos())
        self.scene().mouseDoubleClickedSignal.emit(position.x(), position.y())
        self.update()

    def mouseReleaseEvent(self, event):
        """
        Mouse release event
        :param event:
        :return:
        """
        position = qt_import.QPointF(event.scenePos())
        self.scene().mouseReleasedSignal.emit(position.x(), position.y())
        self.update()
