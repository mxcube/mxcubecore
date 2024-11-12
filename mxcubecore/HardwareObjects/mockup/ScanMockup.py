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

import ast
import random

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.DataPublisher import (
    DataType,
    PlotDim,
    PlotType,
    one_d_data,
)


class ScanMockup(HardwareObject):
    """
    ScanMockup generates random data points to simulate an arbitrary scan
    """

    def __init__(self, name):
        super(ScanMockup, self).__init__(name)
        self._npoints = 100
        self._min = 0
        self._max = 10
        self._sample_rate = 0.5
        self._current_value = 0
        self._task = None
        self._dp_id = None

    def init(self):
        """
        FWK2 Init method
        """
        super(ScanMockup, self).init()

        self._npoints = self.get_property("number_of_points", 100)
        self._min, self._max = ast.literal_eval(self.get_property("min_max", "(0, 10)"))
        self._sample_rate = self.get_property("sample_rate", 0.5)

        HWR.beamline.data_publisher.register(
            "mockupscan",
            "MOCK SCAN",
            "diode",
            axis_labels=["time", "counts"],
            data_type=DataType.FLOAT,
            data_dim=PlotDim.ONE_D,
            plot_type=PlotType.SCATTER,
            content_type="MOCK SCAN",
            sample_rate=self._sample_rate,
            _range=(self._min, self._max),
            meta={},
        )

    def _generate_points(self):
        points = 0

        HWR.beamline.data_publisher.start("mockupscan")

        while points < self._npoints:
            self._current_value = random.uniform(self._min, self._max)

            HWR.beamline.data_publisher.pub(
                "mockupscan",
                one_d_data(points * self._sample_rate, self._current_value),
            )

            gevent.sleep(self._sample_rate)
            points += 1

        HWR.beamline.data_publisher.stop("mockupscan")

    def start(self):
        """
        Start scan
        """
        if not self._task:
            self._task = gevent.spawn(self._generate_points)

    def stop(self):
        """
        Stop scan
        """
        self._task.kill()
        self._task = None
