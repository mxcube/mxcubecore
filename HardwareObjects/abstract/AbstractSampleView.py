#
#  Project: MXCuBE
#  https://github.com/mxcube.
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

import abc

from HardwareRepository.BaseHardwareObjects import HardwareObject


class AbstractSampleView(HardwareObject):
    """ AbstractSampleView Class """

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._camera = None
        self._focus = None
        self._zoom = None
        self._frontlight = None
        self._backlight = None
        self._shapes = None

    @abc.abstractmethod    
    def get_snapshot(self, overlay=True, bw=False, return_as_array=False):
        """ Get snappshot(s)
        Args:
            overlay(bool): Display shapes and other items on the snapshot
            bw(bool): return grayscale image
            return_as_array(bool): return as np array
        """
        pass

    @abc.abstractmethod
    def save_snapshot(self, filename, overlay=True, bw=False):
        """ Save a snapshot to file.
        Args:
            filename (str): The filename.
            overlay(bool): Display shapes and other items on the snapshot
            bw(bool): return grayscale image
        """
        pass

    def save_scene_animation(self, filename, duration=1):
        """ Take snapshots and create an animation.
        Args:
            filename (str): Filename.
            duration (int): Duration time [s].
        """
        pass

    @property
    def camera(self):
        """ Get camera object.
        Returns:
            (AbstractCamera): Camera hardware object.
        """
        return self._camera

    @property
    def shapes(self):
        """ Get shapes dict.
        Returns:
            (AbstractShapes): Shapes hardware object.
        """
        return self._shapes

    @property
    def zoom(self):
        """ Get zoom object.
        Returns:
            (AbstractZoom): Zoom gardware object.
        """
        return self._zoom

    @property
    def frontlight(self):
        """ Get Front light object
        Returns:
            (AbstractLight): Front light hardware object.
        """
        return self._frontlight

    @property
    def backlight(self):
        """ Get Back light object.
        Returns:
            (AbstractLight): Back light hardware object.
        """
        return self._backlight

    @abc.abstractmethod
    def start_centring(self, tree_click=True):
        return

    @abc.abstractmethod
    def cancel_centring(self):
        return

    @abc.abstractmethod
    def start_auto_centring(self):
        return

    @abc.abstractmethod
    def create_line(self):
        return

    @abc.abstractmethod
    def create_auto_line(self):
        return

    @abc.abstractmethod
    def create_grid(self, spacing):
        return

    @abc.abstractmethod
    def clear_all_shapes(self):
        return
