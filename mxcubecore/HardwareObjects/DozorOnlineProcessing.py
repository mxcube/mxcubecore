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


from XSDataCommon import (
    XSDataBoolean,
    XSDataDouble,
    XSDataInteger,
    XSDataString,
)
from XSDataControlDozorv1_1 import XSDataInputControlDozor

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractOnlineProcessing import (
    AbstractOnlineProcessing,
)

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"


class DozorOnlineProcessing(AbstractOnlineProcessing):
    def create_processing_input_file(self, processing_input_filename):
        """Creates dozor input file base on data collection parameters

        :param processing_input_filename
        :type : str
        """
        input_file = XSDataInputControlDozor()
        input_file.setTemplate(XSDataString(self.params_dict["template"]))
        input_file.setFirst_image_number(
            XSDataInteger(self.params_dict["first_image_num"])
        )
        input_file.setLast_image_number(XSDataInteger(self.params_dict["images_num"]))
        input_file.setFirst_run_number(XSDataInteger(self.params_dict["run_number"]))
        input_file.setLast_run_number(XSDataInteger(self.params_dict["run_number"]))
        input_file.setLine_number_of(XSDataInteger(self.params_dict["lines_num"]))
        input_file.setReversing_rotation(
            XSDataBoolean(self.params_dict["reversing_rotation"])
        )
        pixel_size = HWR.beamline.detector.get_pixel_size()
        input_file.setPixelMin(XSDataInteger(pixel_size[0]))
        input_file.setPixelMax(XSDataInteger(pixel_size[1]))
        input_file.setBeamstopSize(XSDataDouble(self.beamstop_hwobj.get_size()))
        input_file.setBeamstopDistance(XSDataDouble(self.beamstop_hwobj.get_distance()))
        input_file.setBeamstopDirection(
            XSDataString(self.beamstop_hwobj.get_direction())
        )

        input_file.exportToFile(processing_input_filename)

    def batch_processed(self, batch):
        """Method called from EDNA via xmlrpc to set results

        :param batch: list of dictionaries describing processing results
        :type batch: lis
        """

        if self.started:
            for image in batch:
                self.results_raw["spots_num"][image[0] - 1] = image[1]
                self.results_raw["spots_resolution"][image[0] - 1] = image[3]
                self.results_raw["score"][image[0] - 1] = image[4]

            self.align_processing_results(batch[0][0] - 1, batch[-1][0] - 1)
            self.emit("processingResultsUpdate", False)
