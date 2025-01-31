"""Bliss session and tools for sending the scan data for plotting.
Emits new_plot, plot_data and plot_end.
"""

import itertools

import gevent
import numpy
from bliss.config import static

from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


def all_equal(iterable):
    """Check for same number of points on each line"""
    grp = itertools.groupby(iterable)
    return next(grp, True) and not next(grp, False)


class Bliss(HardwareObject):
    """Bliss class"""

    def __init__(self, *args):
        HardwareObject.__init__(self, *args)
        self.__scan_data = {}

    def init(self, *args):
        """Initialis the bliss session"""
        cfg = static.get_config()
        session = cfg.get(self.get_property("session"))

        session.setup(self.__dict__, verbose=True)

        self.__scan_data = dict()

    def __on_scan_new(self, scan_info):
        """New scan. Emit new_plot.
        Args:
            scan_info(dict): Contains SCAN_INFO dictionary from bliss
        """
        scan_id = scan_info["scan_nb"]
        self.__scan_data[scan_id] = list()

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
