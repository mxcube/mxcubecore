#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
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
"""Bliss session and tools for sending the scan data for plotting.
Emits new_plot, plot_data and plot_end.
Example yaml file:
.. code-block:: yaml

 class: Bliss.Bliss
 configuration:
   session: mxcubebliss
"""

import itertools

import numpy
from bliss.config import static

from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


def all_equal(iterable):
    """Check for same number of points on each line"""
    grp = itertools.groupby(iterable)
    return next(grp, True) and not next(grp, False)


class Bliss(HardwareObject):
    """Bliss class"""

    def __init__(self, name):
        super().__init__(name)
        self.__scan_data = {}
        self.session_name = None

    def init(self):
        """Initialise the bliss session"""
        cfg = static.get_config()
        session = cfg.get(self.get_property("session"))
        session.setup(self.__dict__, verbose=True)

    def __on_scan_new(self, scan_info):
        """New scan. Emit new_plot.
        Args:
            scan_info(dict): Contains SCAN_INFO dictionary from bliss
        """
        scan_id = scan_info["scan_nb"]
        self.__scan_data[scan_id] = []

        if not scan_info["save"]:
            scan_info["root_path"] = "<no file>"

        self.emit(
            "new_plot",
            {
                "id": scan_info["scan_nb"],
                "title": scan_info["title"],
                "labels": scan_info["labels"],
            },
        )

    def __on_scan_data(self, scan_info, data):
        """Retrieve the scan data. Emit plot_data.
        Args:
            scan_info (dict): SCAN_INFO dictionary from bliss
            data (numpy array): data from bliss
        """

        scan_id = scan_info["scan_nb"]
        new_data = numpy.column_stack([data[name] for name in scan_info["labels"]])
        self.__scan_data[scan_id].append(new_data)
        self.emit(
            "plot_data",
            {
                "id": scan_id,
                "data": numpy.concatenate(self.__scan_data[scan_id]).tolist(),
            },
        )

    def __on_scan_end(self, scan_info):
        """Retrieve remaining data at the end of the scan. Emit plot_end.
        Args:
            scan_info (int): ID of the scan
        """
        scan_id = scan_info["scan_nb"]
        self.emit(
            "plot_end",
            {
                "id": scan_id,
                "data": numpy.concatenate(self.__scan_data[scan_id]).tolist(),
            },
        )
        del self.__scan_data[scan_id]
