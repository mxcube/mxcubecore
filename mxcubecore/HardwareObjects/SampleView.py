#
#  Project name: MXCuBE
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


import base64
import copy
import logging
import math
from ast import literal_eval
from functools import reduce
from io import BytesIO

import numpy as np
from gevent import GreenletExit
from PIL import Image

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects import sample_centring
from mxcubecore.HardwareObjects.abstract.AbstractSampleView import (
    AbstractSampleView,
    ShapeState,
)
from mxcubecore.model import queue_model_objects as qmo

__copyright__ = """by the MXCuBE collaboration """
__license__ = "LGPLv3+"


def combine_images(img1, img2):
    if img1.size != img2.size:
        raise ValueError("Images must be the same size")

    combined_img = Image.new("RGB", img1.size)

    pixels1 = img1.load()
    pixels2 = img2.load()
    combined_pixels = combined_img.load()

    width, height = img1.size
    for x in range(width):
        for y in range(height):
            pixel1 = pixels1[x, y]
            pixel2 = pixels2[x, y]

            if pixel2[0] <= 200 and pixel2[1] <= 60 and pixel2[2] <= 140:
                combined_pixels[x, y] = pixel1
            else:
                combined_pixels[x, y] = pixel2

    return combined_img


class SampleView(AbstractSampleView):
    """SampleView class"""

    def __init__(self, name):
        super().__init__(name)
        self.centring_motors = {}
        self.current_centring_procedure = None
        self.current_centring_method = None
        self.centring_status = {}

    def init(self):
        super().init()

        centring_motor_roles = literal_eval(self.get_property("centring_motors", []))
        # need to set the motor names for the centring points
        qmo.CentredPosition.DIFFRACTOMETER_MOTOR_NAMES = centring_motor_roles
        centring_ref_position = literal_eval(
            self.get_property("centring_reference_position", {})
        )
        dm = HWR.beamline.diffractometer

        for role in centring_motor_roles:
            if role in dm.motors_hwobj_dict:
                motor_obj = dm.motors_hwobj_dict[role]
                ref_position = None
                if role in centring_ref_position:
                    ref_position = centring_ref_position[role]
                self.centring_motors[role] = sample_centring.CentringMotor(
                    motor_obj, reference_position=ref_position
                )
                self.centring_motors[role].motor.connect(
                    "stateChanged", self._update_shape_positions
                )
        self._camera = self.get_object_by_role("camera")
        self._last_oav_image = None

        self.hide_grid_threshold = self.get_property("hide_grid_threshold", 5)
        self.centring_status = {"valid": False}

    def _update_shape_positions(self, *args, **kwargs):
        for shape in self.get_shapes():
            shape.update_position(self.motor_positions_to_screen)

        self.emit("shapesChanged")

    def get_positions(self) -> dict:
        """Get motor positions for the centring motors.
        Returns:
            Centring motor positions as {role: position}
        """
        motors_dict = {}
        for key, val in self.centring_motors.items():
            motors_dict.update({key: val.motor.get_value()})
        return motors_dict

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        return self.get_positions()

    def motor_positions_to_screen(self, positions_dict: dict) -> tuple:
        """Get the motor positions according to the calibration"""
        if not positions_dict:
            raise RuntimeError("Unknown position")
        try:
            dm = HWR.beamline.diffractometer
            p_x, p_y = dm.get_pixels_per_mm()
            if None in (p_x, p_y):
                return 0, 0

            beam_position = HWR.beamline.beam.get_beam_position_on_screen()
            omega_angle = math.radians(dm.omega.get_value())
            sampx = positions_dict.get("sampx") - dm.sampx.get_value()
            sampy = positions_dict.get("sampy") - dm.sampy.get_value()
            phiy = positions_dict.get("phiy") - dm.phiy.get_value()
            phiz = positions_dict.get("phiz") - dm.phiz.get_value()
            rot_matrix = np.matrix(
                [
                    math.cos(omega_angle),
                    -math.sin(omega_angle),
                    math.sin(omega_angle),
                    math.cos(omega_angle),
                ]
            )
            rot_matrix.shape = (2, 2)
            inv_rot_matrix = np.array(rot_matrix.I)
            dx, dy = np.dot(np.array([sampx, sampy]), inv_rot_matrix) * p_x

            x = (phiy * p_x) + beam_position[0]
            y = dy + (phiz * p_y) + beam_position[1]

        except AttributeError as err:
            raise NotImplementedError from err
        return x, y

    def start_manual_centring(self, nb_click=3):
        """Do the manual centring procedure.
        Args:
           nb_click (int): Number of clicks.
        """
        if self.current_centring_procedure is not None:
            logging.getLogger("HWR").exception("Already centring")

        self.current_centring_method = "Manual"
        self.emit("centringStarted", ("Manual"))
        beam_pos = HWR.beamline.beam.get_beam_position_on_screen()
        dm = HWR.beamline.diffractometer
        pixels_per_mm = dm.get_pixels_per_mm()
        dm.wait_ready(5)

        self.current_centring_procedure = sample_centring.start(
            self.centring_motors,
            pixels_per_mm[0],
            pixels_per_mm[1],
            beam_pos[0],
            beam_pos[1],
            chi_angle=0.0,
        )

        self.current_centring_procedure.link(self.manual_centring_done)

    def get_centring_status(self):
        return copy.deepcopy(self.centring_status)

    def image_clicked(self, x, y):
        logging.getLogger("user_level_log").info(
            f"Centring click at x:{int(x)}, y:{int(y)}"
        )
        sample_centring.user_click(x, y, wait=True)

    def manual_centring_done(self, manual_centring_procedure):
        try:
            motor_pos = manual_centring_procedure.get()
            if isinstance(motor_pos, GreenletExit):
                raise motor_pos
        except Exception:
            logging.exception("Could not complete manual centring")
            self.centring_failed()
        else:
            self.emit("centringMoving", ())
            try:
                sample_centring.end()
            except Exception:
                logging.exception("Could not move to centred position")
                self.centring_failed()

            self.centring_done()

    def centring_done(self):
        self.centring_status = {"motors": {}, "method": self.current_centring_method}
        self.centring_status["motors"] = self.get_positions()

        self.centring_status["valid"] = True

        self.emit(
            "centringSuccessful",
            (self.current_centring_method, self.get_centring_status()),
        )
        self.current_centring_method = None
        self.current_centring_procedure = None

    def accept_centring(self):
        self.centring_status["valid"] = True
        self.emit("centringAccepted", (True, self.get_centring_status()))
        logging.getLogger("user_level_log").info("Centring successful")

    def reject_centring(self):
        if self.current_centring_procedure:
            self.current_centring_procedure.kill(block=True)
        self.centring_status["valid"] = False
        self.emit("centringAccepted", (False, self.get_centring_status()))
        logging.getLogger("user_level_log").info("Centring cancelled")

    def cancel_centring(self):
        """Cancel current centring procedure."""
        if self.current_centring_procedure:
            try:
                self.current_centring_procedure.kill(block=True)
            except Exception:
                logging.getLogger("HWR").exception(
                    "Problem aborting the centring method"
                )

            logging.getLogger("HWR").exception("Centring canceled")
        self.centring_failed()

    def centring_failed(self):
        """Execute if centring failed or canceled."""
        self.centring_status["valid"] = False
        self.emit(
            "centringFailed", (self.current_centring_method, self.get_centring_status())
        )
        self.current_centring_procedure = None
        self.current_centring_method = None

    def start_auto_centring(self):
        """Start automatic centring procedure"""
        if self.current_centring_procedure is not None:
            logging.getLogger("HWR").exception("Already centring")

        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()
        dm = HWR.beamline.diffractometer
        dm.set_phase("Centring", wait=True)

        pixels_per_mm_x, pixels_per_mm_y = dm.get_pixels_per_mm()
        dm.wait_ready(5)

        self.current_centring_procedure = sample_centring.start_auto(
            self,
            self.centring_motors,
            pixels_per_mm_x,
            pixels_per_mm_y,
            beam_pos_x,
            beam_pos_y,
            chi_angle=0.0,
        )

        self.current_centring_method = "Automatic"
        self.emit("centringStarted", ("Automatic"))
        self.current_centring_procedure.link(self.auto_centring_done)

    def move_to_beam(self, x: float, y: float):
        """Move the sample to the x,y coordinates"""
        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()
        dm = HWR.beamline.diffractometer
        pixels_per_mm_x, pixels_per_mm_y = dm.get_pixels_per_mm()
        if not all([pixels_per_mm_x, pixels_per_mm_y]):
            logging.getLogger("HWR").exception("Cannot move to beam")

        # here added the calculation for moving to the beam position
        dx = (x - beam_pos_x) / pixels_per_mm_x
        dy = (y - beam_pos_y) / pixels_per_mm_y

        dm.wait_ready(5)

        motors_dict = self.get_positions()
        omega_angle = math.radians(motors_dict.get("omega", 0))

        rot_matrix = np.matrix(
            [
                [math.cos(omega_angle), -math.sin(omega_angle)],
                [math.sin(omega_angle), math.cos(omega_angle)],
            ]
        )
        inv_rot_matrix = np.array(rot_matrix.I)
        dsampx, dsampy = np.dot(np.array([0, dy]), inv_rot_matrix)

        chi_angle = math.radians(motors_dict.get("chi", 0))
        chi_rot = np.matrix(
            [
                [math.cos(chi_angle), -math.sin(chi_angle)],
                [math.sin(chi_angle), math.cos(chi_angle)],
            ]
        )

        sx, sy = np.dot(np.array([dsampx, dsampy]), np.array(chi_rot))

        sampx = motors_dict.get("sampx") + sx
        sampy = motors_dict.get("sampx") + sy
        phiy = motors_dict.get("phiy") + dx

        self.centring_motors.get("sampx").set_value(-sampx)
        self.centring_motors.get("sampy").set_value(sampy)
        self.centring_motors.get("phiy").set_value(-phiy)

    def get_snapshot(
        self,
        overlay: [str | None] = None,
        bw: bool = False,
        return_as_array: bool = False,
    ) -> BytesIO:
        """
        Get snapshot(s)

        Args:
            overlay(str): Image data with shapes and other items to display
                          on the snapshot
            bw(bool): return grayscale image
            return_as_array(bool): return as np array

        Returns:
            (BytesIO) snapshot as bytes image
        """
        img = self.take_snapshot(overlay_data=overlay, bw=bw)

        if return_as_array:
            return np.array(img)

        buffered = BytesIO()
        img.save(buffered, format="JPEG")

        return buffered

    def save_snapshot(
        self, filename: str, overlay: [str | None] = None, bw: bool = False
    ):
        """
        Save a snapshot to file.

        Args:
            filename(str): The filename.
            overlay(str): Image data with shapes and other items to display
                          on the snapshot
            bw(bool): return grayscale image. Default False
        """
        img = self.take_snapshot(overlay_data=overlay, bw=bw)
        img.save(filename)

        self._last_oav_image = filename

    def take_snapshot(self, overlay_data: [str | None] = None, bw: bool = False):
        """
        Get snapshot with overlaid data.

        Args:
            overlay_data (str): base64 encoded image to lay over camera image
            bw (bool): return grayscale image

        Returns:
            (Image) rgb or grayscale image
        """
        data, width, height = self.camera.get_last_image()

        img = Image.frombytes("RGB", (width, height), data)

        if overlay_data:
            overlay_data = base64.b64decode(overlay_data)
            overlay_image = Image.open(BytesIO(overlay_data))
            overlay_image = overlay_image.resize(
                (width, height), Image.Resampling.LANCZOS
            )
            img = combine_images(img, overlay_image.convert("RGB"))

        if bw:
            img.convert("1")

        return img

    def get_last_image_path(self):
        return self._last_oav_image

    def add_shape(self, shape):
        """
        Add the shape <shape> to the dictionary of handled shapes.

        Args:
            param (shape): Shape to add.
            type (shape): Shape object.
        """
        self.shapes[shape.id] = shape
        shape.shapes_hw_object = self

    def add_shape_from_mpos(
        self,
        mpos_list,
        screen_coord,
        t,
        state: ShapeState = "SAVED",
        user_state: ShapeState = "SAVED",
    ):
        """
        Adds a shape of type <t>, with motor positions from mpos_list and
        screen position screen_coord.

        Args:
            mpos_list (list[mpos_list]): List of motor positions
            screen_coord (tuple(x, y): Screen coordinate for shape
            t (str): Type str for shape, P (Point), L (Line), G (Grid)

        Returns:
            (Shape) Shape of type <t>
        """
        cls_dict = {"P": Point, "L": Line, "G": Grid, "2DP": TwoDPoint}
        _cls = cls_dict[t]
        shape = None

        if _cls:
            shape = _cls(mpos_list, screen_coord)
            # In case the shape is being recreated, we need to restore it's state.
            shape.state = state
            shape.user_state = user_state

            self.add_shape(shape)

        return shape

    def add_shape_from_refs(
        self, refs, t, state: ShapeState = "SAVED", user_state: ShapeState = "SAVED"
    ):
        """
        Adds a shape of type <t>, taking motor positions and screen positions
        from reference points in refs.

        Args:
            refs (list[str]): List of id's of the reference Points
            t (str): Type str for shape, P (Point), L (Line), G (Grid)

        Returns:
            (Shape): Shape of type <t>
        """
        mpos = [self.get_shape(refid).mpos() for refid in refs]
        spos_list = [self.get_shape(refid).screen_coord for refid in refs]
        spos = reduce((lambda x, y: tuple(x) + tuple(y)), spos_list, ())
        shape = self.add_shape_from_mpos(mpos, spos, t, state, user_state)
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
           (list[Shape]) List of selected Shapes
        """
        return [s for s in self.shapes.values() if s.is_selected()]

    def de_select_all(self):
        """De select all shapes."""

        for shape in self.shapes.values():
            shape.de_select()

    def select_shape_with_cpos(self, cpos):
        """
        Selects shape with the assocaitaed centred position <cpos>

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

    # For backwards compatibility with old ShapeHisotry object
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

    def set_grid_data(self, sid: str, result_data, data_file_path: str):
        """
        Sets grid rsult data for a shape with the specified id.

        Args:
            sid: The id of the shape to set grid data for.
            result_data: The result data to set for the shape.
                         Either a base64 encoded string for PNG/image or a
                         dictionary for RGB (keys are cell number and value
                         RGBa list). Data is only updated if result is RGB based
            data_file_path: The path to the data file associated with the
                            result data.

        Raises:
            AttributeError: If no shape with the specified id exists.
        """

        shape = self.get_shape(sid)

        if shape:
            if shape.result and isinstance(shape.result, dict):
                # append data
                shape.result.update(result_data)
            else:
                shape.set_result(result_data)
                shape.result_data_path = data_file_path

            self.emit("newGridResult", shape)
        else:
            msg = f"Cant set result, no shape with id {sid}"
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


class Shape:
    """
    Base class for shapes.
    """

    SHAPE_COUNT = 0

    def __init__(self, mpos_list=None, screen_coord=(-1, -1)):
        Shape.SHAPE_COUNT += 1
        self.t = "S"
        self.id = ""
        self.cp_list = []
        self.name = ""
        self.state: ShapeState = "SAVED"
        # used to persist user preferences to show or hide particular shape.
        self.user_state: ShapeState = "SAVED"
        self.label = ""
        self.screen_coord = screen_coord
        self.selected = False
        self.refs = []
        self.shapes_hw_object = None
        mpos_list = mpos_list or []
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
        spos_list = tuple([pos for x in spos_list for pos in x])
        self.screen_coord = spos_list

    def add_cp_from_mp(self, mpos_list):
        for mp in mpos_list:
            self.cp_list.append(qmo.CentredPosition(mp))

    def set_id(self, id_num):
        self.id = f"{self.t}{id_num}"
        self.name = f"{self.label}-{id_num}"

    def move_to_mpos(self, mpos_list, screen_coord=None):
        self.cp_list = []
        self.add_cp_from_mp(mpos_list)

        if screen_coord:
            self.screen_coord = screen_coord

    def update_from_dict(self, shape_dict):
        # We do not allow id or result updates
        shape_dict.pop("id", None)
        shape_dict.pop("result", None)

        for key, value in shape_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def as_dict(self):
        cpos_list = [x.as_dict() for x in self.cp_list]

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
        self.cp_list[0].index = self.name

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
        super().__init__(mpos_list, screen_coord)
        Line.SHAPE_COUNT += 1
        self.t = "L"
        self.label = "Line"
        self.set_id(Line.SHAPE_COUNT)

    def set_id(self, id_num):
        Shape.set_id(self, id_num)
        self.cp_list[0].index = self.name

    def get_points_index(self):
        if all(self.cp_list):
            return (self.cp_list[0].get_index(), self.cp_list[1].get_index())
        return (None, None)


class Grid(Shape):
    SHAPE_COUNT = 0

    def __init__(self, mpos_list, screen_coord):
        super().__init__(mpos_list, screen_coord)
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
        # result is a base64 encoded string for PNG/image heatmap results
        # or a dictionary (for RGB number based results)
        self.result = None
        self.pixels_per_mm = [1, 1]
        self.beam_pos = [1, 1]
        self.beam_width = 0
        self.beam_height = 0
        self.hide_threshold = 5

        self.set_id(Grid.SHAPE_COUNT)

    def update_position(self, transform):
        phi_pos = HWR.beamline.diffractometer.omega.get_value() % 360
        _d = abs((self.get_centred_position().phi % 360) - phi_pos)

        if self.user_state == "HIDDEN":
            self.state = "HIDDEN"
            return

        if min(_d, 360 - _d) > self.shapes_hw_object.hide_grid_threshold:
            self.state = "HIDDEN"
        else:
            super().update_position(transform)
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
        if self.cell_count_fun == "inverse-zig-zag":
            return self.num_cols
        return self.num_rows

    def set_id(self, id_num):
        Shape.set_id(self, id_num)
        self.cp_list[0].index = self.name

    def set_result(self, result_data):
        self.result = result_data

    def get_result(self):
        return self.result

    def as_dict(self):
        d = Shape.as_dict(self)
        # replace cpos_list with the motor positions
        d["motor_positions"] = self.cp_list[0].as_dict()

        pixels_per_mm = HWR.beamline.diffractometer.get_pixels_per_mm()
        beam_pos = HWR.beamline.beam.get_beam_position_on_screen()
        size_x, size_y, shape, _label = HWR.beamline.beam.get_value()

        d["x1"] = -float((beam_pos[0] - d["screen_coord"][0]) / pixels_per_mm[0])
        d["y1"] = -float((beam_pos[1] - d["screen_coord"][1]) / pixels_per_mm[1])
        d["steps_x"] = d["num_cols"]
        d["steps_y"] = d["num_rows"]
        d["dx_mm"] = d["width"] / pixels_per_mm[0]
        d["dy_mm"] = d["height"] / pixels_per_mm[1]
        d["beam_width"] = size_x
        d["beam_height"] = size_y
        d["angle"] = 0

        return d
