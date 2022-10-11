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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

import copy
from functools import reduce

from mxcubecore.model import queue_model_objects

from mxcubecore.HardwareObjects.abstract.AbstractSampleView import (
    AbstractSampleView,
)

from mxcubecore import HardwareRepository as HWR


class SampleView(AbstractSampleView):
    def __init__(self, name):
        AbstractSampleView.__init__(self, name)
        self._shapes = {}

    def init(self):
        super(SampleView, self).init()

        self._camera = self.get_object_by_role("camera")
        self._focus = self.get_object_by_role("focus")
        self._zoom = self.get_object_by_role("zoom")
        self._frontlight = self.get_object_by_role("frontlight")
        self._backlight = self.get_object_by_role("backlight")
        self._diffractometer = self.get_object_by_role("diffractometer")

        self._ui_snapshot_cb = None

        self.hide_grid_threshold = self.get_property("hide_grid_threshold", 5)

        for motor_name, motor_ho in self._diffractometer.get_motors().items():
            motor_ho.connect("stateChanged", self._update_shape_positions)


    def _update_shape_positions(self, *args, **kwargs):
        shapes_updated = False

        for shape in self.get_shapes():
            previous_screen_coord = shape.screen_coord
            shape.update_position(HWR.beamline.diffractometer.motor_positions_to_screen)

            # We assume that all positions are changed when a motor moves
            # and that if the screen coordinate for the first motor is unchanged
            # so are the rest, simply return and emit no change.
            if shape.screen_coord != previous_screen_coord:
                shapes_updated = True
            else:
                break

        if shapes_updated:
            self.emit("shapesChanged")

    @property
    def shapes(self):
        return self._shapes

    def start_centring(self, tree_click=True):
        """
        Starts centring procedure
        """
        pass

    def cancel_centring(self):
        """
        Cancels current centring procedure
        """
        pass

    def start_auto_centring(self):
        """
        Start automatic centring procedure
        """
        pass

    def set_ui_snapshot_cb(self, fun):
        self._ui_snapshot_cb = fun

    def get_snapshot(self, overlay=True, bw=False, return_as_array=False):
        """ Get snappshot(s)
        Args:
            overlay(bool): Display shapes and other items on the snapshot
            bw(bool): return grayscale image
            return_as_array(bool): return as np array
        """
        pass

    def save_snapshot(self, path, overlay=True, bw=False):
        """ Save a snapshot to file.
        Args:
            path (str): The filename.
            overlay(bool): Display shapes and other items on the snapshot
            bw(bool): return grayscale image
        """
        if overlay:
            img = self._ui_snapshot_cb(path, bw)
        else:
            self.camera.take_snapshot(path, bw)

    def add_shape(self, shape):
        """
        Add the shape <shape> to the dictionary of handled shapes.

        :param shape: Shape to add.
        :type shape: Shape object.
        """
        self.shapes[shape.id] = shape
        shape.shapes_hw_object = self

    def add_shape_from_mpos(self, mpos_list, screen_coord, t):
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
        cls_dict = {"P": Point, "L": Line, "G": Grid, "2DP": TwoDPoint}
        _cls = cls_dict[t]
        shape = None

        if _cls:
            shape = _cls(mpos_list, screen_coord)
            self.add_shape(shape)

        return shape

    def add_shape_from_refs(self, refs, t):
        """
        Adds a shape of type <t>, taking motor positions and screen positions
        from reference points in refs.

        Args:
            refs (list[str]): List of id's of the refrence Points
            t (str): Type str for shape, P (Point), L (Line), G (Grid)

        Returns:
            (Shape): Shape of type <t>
        """
        mpos = [self.get_shape(refid).mpos() for refid in refs]
        spos_list = [self.get_shape(refid).screen_coord for refid in refs]
        spos = reduce((lambda x, y: tuple(x) + tuple(y)), spos_list, ())
        shape = self.add_shape_from_mpos(mpos, spos, t)
        shape.refs = refs

        return shape

    def delete_shape(self, sid):
        """
        Removes the shape with id <sid> from the list of handled shapes.

        Args:
            sid (str): The id of the shape to remove

        Returns:
            (Shape): The removed shape
        """
        shape = self.shapes.pop(sid, None)

        if shape:
            shape.shapes_hw_object = None

        return shape

    def select_shape(self, sid):
        """
        Select the shape <shape>.

        Args:
            sid (str): Id of the shape to select.
        """
        shape = self.shapes.get(sid, None)

        if shape:
            shape.select()

    def de_select_shape(self, sid):
        """
        De-select the shape with id <sid>.

        Args:
            sid (str): The id of the shape to de-select.
        """
        shape = self.shapes.get(sid, None)

        if shape:
            shape.de_select()

    def is_selected(self, sid):
        """
        Check if Shape with <sid> is selected.

        Returns:
            (Boolean) True if Shape with <sid> is selected False otherwise
        """
        shape = self.shapes.get(sid, None)
        return bool(shape and shape.is_selected())

    def get_selected_shapes(self):
        """
        Get all selected shapes.

        Returns:
           (list[Shape]) List fot selected Shapes
        """
        return [s for s in self.shapes.values() if s.is_selected()]

    def de_select_all(self):
        """De select all shapes."""

        for shape in self.shapes.values():
            shape.de_select()

    def select_shape_with_cpos(self, cpos):
        """
        Selects shape with the assocaitaed centerd posotion <cpos>

        Args:
            cpos (CenteredPosition)
        """
        return

    def clear_all(self):
        """
        Clear the shapes, remove all contents.
        """
        self._shapes = {}
        Grid.SHAPE_COUNT = 0
        Line.SHAPE_COUNT = 0
        Point.SHAPE_COUNT = 0

    def get_shapes(self):
        """
        Get all Shapes.

        Returns:
            (list[Shape]) All the shapes
        """
        return self.shapes.values()

    def get_points(self):
        """
        Get all Points currently handled.

        Returns:
            (list[Point]) All points currently handled
        """
        current_points = []

        for shape in self.get_shapes():
            if isinstance(shape, Point):
                current_points.append(shape)

        return current_points

    def get_lines(self):
        """
        Get all Lines currently handled.

        Returns:
            (list[Line]) All lines currently handled
        """
        lines = []

        for shape in self.get_shapes():
            if isinstance(shape, Line):
                lines.append(shape)

        return lines

    def get_grids(self):
        """
        Get all Grids currently handled.

        Returns:
            (list[Grid]) All lines currently handled
        """
        grid = []

        for shape in self.get_shapes():
            if isinstance(shape, Grid):
                grid.append(shape)

        return grid

    def get_shape(self, sid):
        """
        Get Shape with id <sid>.

        Args:
            sid (str): id of Shape to retrieve

        Returns:
            (Shape) All the shapes
        """
        return self.shapes.get(sid, None)

    # For backwards compatability with old ShapeHisotry object
    # returns first of selected grids
    def get_grid(self):
        """
        Get the first of the selected grids, (the one that was selected first in
        a sequence of select operations)

        Returns:
            (dict): The first selected grid as a dictionary
        """
        grid = None

        for shape in self.get_shapes():
            if isinstance(shape, Grid):
                grid = shape.as_dict()
                break

        return grid

    def set_grid_data(self, sid, result_data):
        shape = self.get_shape(sid)

        if shape:
            shape.set_result(result_data)
            self.emit("newGridResult", shape)
        else:
            msg = "Cant set result for %s, no shape with id %s" % (sid, sid)
            raise AttributeError(msg)


    def get_grid_data(self, key):
        result = {}
        shape = self.get_shape(key)

        if shape:
            result = shape.get_result()

        return result

    def inc_used_for_collection(self, cpos):
        """
        Increase counter that keepts on collect made on this shape,
        shape with associated CenteredPosition cpos

        Args:
            cpos (CenteredPosition): CenteredPosition of shape
        """
        # Signature incompatible with AbstractSampleView
        pass


class Shape(object):
    """
    Base class for shapes.
    """

    SHAPE_COUNT = 0

    def __init__(self, mpos_list=[], screen_coord=(-1, -1)):
        object.__init__(self)
        Shape.SHAPE_COUNT += 1
        self.t = "S"
        self.id = ""
        self.cp_list = []
        self.name = ""
        self.state = "SAVED"
        self.label = ""
        self.screen_coord = screen_coord
        self.selected = False
        self.refs = []
        self.shapes_hw_object = None

        self.add_cp_from_mp(mpos_list)

    def get_centred_positions(self):
        """
        :returns: The centred position(s) associated with the shape.
        :rtype: List of CentredPosition objects.
        """
        return self.cp_list

    def get_centred_position(self):
        return self.get_centred_positions()[0]

    def select(self):
        self.selected = True

    def de_select(self):
        self.selected = False

    def is_selected(self):
        return self.selected

    def update_position(self, transform):
        spos_list = [transform(cp.as_dict()) for cp in self.cp_list]
        spos_list = tuple([pos for l in spos_list for pos in l])
        self.screen_coord = spos_list

    def add_cp_from_mp(self, mpos_list):
        for mp in mpos_list:
            self.cp_list.append(queue_model_objects.CentredPosition(mp))

    def set_id(self, id_num):
        self.id = self.t + "%s" % id_num
        self.name = self.label + "-%s" % id_num

    def move_to_mpos(self, mpos_list, screen_coord=[]):
        self.cp_list = []
        self.add_cp_from_mp(mpos_list)

        if screen_coord:
            self.screen_coord = screen_coord

    def update_from_dict(self, shape_dict):
        # We dont allow id or result updates
        shape_dict.pop("id", None)
        shape_dict.pop("result", None)

        for key, value in shape_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def as_dict(self):
        cpos_list = []

        for cpos in self.cp_list:
            cpos_list.append(cpos.as_dict())

        d = copy.deepcopy(vars(self))

        # Do not serialize Shapes HW Object
        d.pop("shapes_hw_object")

        # replace cpos_list with a list of motor positions
        d.pop("cp_list")
        d["motor_positions"] = str(cpos_list)

        return d


class Point(Shape):
    SHAPE_COUNT = 0

    def __init__(self, mpos_list, screen_coord):
        Shape.__init__(self, mpos_list, screen_coord)
        Point.SHAPE_COUNT += 1
        self.t = "P"
        self.label = "Point"
        self.set_id(Point.SHAPE_COUNT)

    def mpos(self):
        return self.cp_list[0].as_dict()

    def set_id(self, id_num):
        Shape.set_id(self, id_num)
        self.cp_list[0].index = self.id

    def as_dict(self):
        d = Shape.as_dict(self)
        # replace cpos_list with the motor positions
        d["motor_positions"] = self.cp_list[0].as_dict()
        return d


class TwoDPoint(Point):
    SHAPE_COUNT = 0

    def __init__(self, mpos_list, screen_coord):
        Point.__init__(self, mpos_list, screen_coord)
        self.t = "2DP"
        self.label = "2D-Point"
        self.set_id(Point.SHAPE_COUNT)


class Line(Shape):
    SHAPE_COUNT = 0

    def __init__(self, mpos_list, screen_coord):
        Shape.__init__(self, mpos_list, screen_coord)
        Line.SHAPE_COUNT += 1
        self.t = "L"
        self.label = "Line"
        self.set_id(Line.SHAPE_COUNT)

    def get_centred_positions(self):
        return [self.start_cpos, self.end_cpos]

    def get_points_index(self):
        if all(self.cp_list):
            return (self.cp_list[0].get_index(), self.cp_list[1].get_index())


class Grid(Shape):
    SHAPE_COUNT = 0

    def __init__(self, mpos_list, screen_coord):
        Shape.__init__(self, mpos_list, screen_coord)
        Grid.SHAPE_COUNT += 1
        self.t = "G"
        self.set_id(Grid.SHAPE_COUNT)

        self.width = -1
        self.height = -1
        self.cell_count_fun = "zig-zag"
        self.cell_h_space = -1
        self.cell_height = -1
        self.cell_v_space = -1
        self.cell_width = -1
        self.label = "Grid"
        self.num_cols = -1
        self.num_rows = -1
        self.selected = False
        self.result = []
        self.pixels_per_mm = [1, 1]
        self.beam_pos = [1, 1]
        self.beam_width = 0
        self.beam_height = 0
        self.hide_threshold = 5

        self.set_id(Grid.SHAPE_COUNT)

    def update_position(self, transform):
        phi_pos = HWR.beamline.diffractometer.phiMotor.get_value() % 360
        d = abs((self.get_centred_position().phi % 360) - phi_pos)

        if min(d, 360 - d) > self.shapes_hw_object.hide_grid_threshold:
            self.state = "HIDDEN"
        else:
            super(Grid, self).update_position(transform)
            self.state = "SAVED"

    def get_centred_position(self):
        return self.cp_list[0]

    def get_grid_range(self):
        return (
            float(self.cell_width * (self.num_cols - 1)),
            float(self.cell_height * (self.num_rows - 1)),
        )

    def get_num_lines(self):
        if self.cell_count_fun == "zig-zag":
            return self.num_rows
        elif self.cell_count_fun == "inverse-zig-zag":
            return self.num_cols
        else:
            return self.num_rows

    def set_id(self, id_num):
        Shape.set_id(self, id_num)
        self.cp_list[0].index = self.id

    def set_result(self, result_data):
        self.result = result_data
        self._result = result_data

    def get_result(self):
        return self.result

    def as_dict(self):
        d = Shape.as_dict(self)
        # replace cpos_list with the motor positions
        d["motor_positions"] = self.cp_list[0].as_dict()

        # MXCuBE - 2 WF compatability
        d["x1"] = -float(
            (self.beam_pos[0] - d["screen_coord"][0]) / self.pixels_per_mm[0]
        )
        d["y1"] = -float(
            (self.beam_pos[1] - d["screen_coord"][1]) / self.pixels_per_mm[1]
        )
        d["steps_x"] = d["num_cols"]
        d["steps_y"] = d["num_rows"]
        d["dx_mm"] = d["width"] / self.pixels_per_mm[0]
        d["dy_mm"] = d["height"] / self.pixels_per_mm[1]
        d["beam_width"] = d["beam_width"]
        d["beam_height"] = d["beam_height"]
        d["angle"] = 0

        return d
