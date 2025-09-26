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

"""Abstract class for a Sample View.
Defines methods to handle snapshots, animation and shapes.
"""

__copyright__ = """2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

import abc
from typing import (
    Literal,
    Union,
)

from mxcubecore.BaseHardwareObjects import HardwareObject

ShapeState = Literal["HIDDEN", "SAVED", "TMP"]


class AbstractSampleView(HardwareObject):
    """AbstractSampleView Class"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        super().__init__(name)
        self._focus = None
        self._zoom = None
        self._frontlight = None
        self._backlight = None
        self._shapes = {}

    @property
    def camera(self):
        return self.get_object_by_role("camera")

    @abc.abstractmethod
    def get_snapshot(
        self,
        overlay: Union[bool, str] = True,
        bw: bool = False,
        return_as_array: bool = False,
    ):
        """Get snappshot(s)
        Args:
            overlay(bool | str): Display shapes and other items on the snapshot
            bw(bool): return grayscale image
            return_as_array(bool): return as np array
        """

    @abc.abstractmethod
    def save_snapshot(
        self, filename, overlay: Union[bool, str] = True, bw: bool = False
    ):
        """Save a snapshot to file.
        Args:
            filename (str): The filename.
            overlay(bool | str): Display shapes and other items on the snapshot.
            bw(bool): Return grayscale image.
        """

    def save_scene_animation(self, filename, duration=1):
        """Take snapshots and create an animation.
        Args:
            filename (str): The filename.
            duration (int): Duration time [s].
        """

    @property
    def shapes(self):
        """Get shapes dict.
        Returns:
            (AbstractShapes): Shapes hardware object.
        """
        return self._shapes

    @property
    def zoom(self):
        """Get zoom object.
        Returns:
            (AbstractZoom): Zoom gardware object.
        """
        return self._zoom

    @property
    def frontlight(self):
        """Get Front light object
        Returns:
            (AbstractLight): Front light hardware object.
        """
        return self._frontlight

    @property
    def backlight(self):
        """Get Back light object.
        Returns:
            (AbstractLight): Back light hardware object.
        """
        return self._backlight

    @abc.abstractmethod
    def start_manual_centring(self, nb_click=3):
        """Starts manual centring procedure"""

    @abc.abstractmethod
    def start_auto_centring(self):
        """Start automatic centring procedure"""

    def move_to_beam(self, x: float, y: float):
        """Move the sample to the x,y coordinates"""

    @abc.abstractmethod
    def get_positions(self) -> dict:
        """Get motor positions for the centring motors.
        Returns:
            Centring motor positions as {role: position}
        """

    @abc.abstractmethod
    def add_shape(self, shape):
        """Add the shape <shape> to the dictionary of handled shapes.
        Args:
            shape(Shape): Shape to add
        """

    @abc.abstractmethod
    def add_shape_from_mpos(
        self,
        mpos_list: list,
        screen_coord: tuple,
        _type: str,
        state: ShapeState = "SAVED",
        user_state: ShapeState = "SAVED",
    ):
        """Add a shape of type <t>, with motor positions from mpos_list and
        screen position screen_coord.
        Args:
            mpos_list (list[mpos_list]): List of motor positions
            screen_coord (tuple(x, y): Screen coordinate for shape
            _type (str): Type str for shape, P (Point), L (Line), G (Grid)
            user_state (ShapeState): State of the shape set by the user
        Returns:
            (Shape): Shape of type _type
        """

    @abc.abstractmethod
    def delete_shape(self, sid: str):
        """Remove the shape with specified id from the list of handled shapes.
        Args:
            sid (str): The id of the shape to remove
        Returns:
            (Shape): The removed shape
        """
        return

    @abc.abstractmethod
    def select_shape(self, sid: str):
        """Select the shape <shape>.
        Args:
            sid (str): Id of the shape to select.
        """
        return

    @abc.abstractmethod
    def de_select_shape(self, sid: str):
        """De-select the shape with id <sid>.
        Args:
            sid (str): The id of the shape to de-select.
        """
        return

    @abc.abstractmethod
    def is_selected(self, sid: str) -> bool:
        """Check if Shape with specified id is selected.
        Args:
            sid (str): Shape id.
        Returns:
            (Boolean) True if selected, False otherwise.
        """

    @abc.abstractmethod
    def get_selected_shapes(self) -> list:
        """Get all selected shapes.
        Returns:
           (list) List of the selected Shapes.
        """

    @abc.abstractmethod
    def de_select_all(self):
        """De-select all shapes."""

    @abc.abstractmethod
    def select_shape_with_cpos(self, cpos):
        """Selects shape with the assocaitaed centred position <cpos>
        Args:
            cpos (CentredPosition): Centred position
        """

    @abc.abstractmethod
    def clear_all(self):
        """Clear the shapes, remove all contents."""

    @abc.abstractmethod
    def get_shape(self, sid: str):
        """
        Get Shape with id <sid>.

        Args:
            sid (str): id of Shape to retrieve

        Returns:
            (Shape) All the shapes
        """

    @abc.abstractmethod
    def get_grid(self):
        """Get the first of the selected grids, (the one that was selected
        first in a sequence of select operations).
        Returns:
            (dict): The first selected grid as a dictionary.
        """

    @abc.abstractmethod
    def get_points(self) -> list:
        """Get all currently handled centred points.
        Returns:
            (list): All points currently handled as list.
        """

    @abc.abstractmethod
    def get_lines(self) -> list:
        """Get all the currently handled lines.

        Returns:
            (list): All lines currently handled as list.
        """

    @abc.abstractmethod
    def get_grids(self) -> list:
        """Get all currently handled grids.
        Returns:
            (list): All grids currently handled as list.
        """

    @abc.abstractmethod
    def inc_used_for_collection(self, cpos):
        """Increase the counter that keepts on collect made on this shape,
        shape with associated CentredPosition cpos.
        Args:
            cpos (CentredPosition): CentredPosition of shape
        """

    def motor_positions_to_screen(self, positions_dict: dict) -> tuple:
        """Get the motor positions according to the calibration"""
