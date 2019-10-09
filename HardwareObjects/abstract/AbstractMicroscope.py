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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

import abc


class AbstractMicroscope(object):
    """ Abstract Mictoscope Class """
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self._camera_hwobj = None
        self._shapes_hwobj = None
        self._focus_hwobj = None
        self._zoom_hwobj = None
        self._frontlight_hwobj  = None
        self._backlight_hwobj  = None

    def get_snapshot(self, num=4):
        """ Get snappshot(s)
        Args:
            num(int): Number of snapshots to take.
        """
        pass

    def save_snapshot(self, filename):
        """ Save a snapshot to file.
        Args:
            filename (str): The filename.
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
        """ Get shapes object.
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
