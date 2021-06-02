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

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import os
import time
from mxcubecore.TaskUtils import task
from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect
from mxcubecore import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]


class CollectMockup(AbstractCollect):
    """
    """

    def __init__(self, name):
        """

        :param name: name of the object
        :type name: string
        """

        AbstractCollect.__init__(self, name)

    def init(self):
        """Main init method
        """

        AbstractCollect.init(self)

    def _execute(self, data_model):
        """Main collection hook
        """

        AbstractCollect._execute(self, data_model)

        acq_params = data_model.acquisitions[0].acquisition_parameters
        for image in range(acq_params.num_images):
            time.sleep(acq_params.exp_time)
            self.emit("imageTaken", image)
            self.emit("progressStep", (int(float(image) / acq_params.num_images * 100)))

        #self._set_successful()