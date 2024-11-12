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

from typing import List

from mxcubecore.HardwareObjects import edna_test_data
from mxcubecore.HardwareObjects.EDNACharacterisation import EDNACharacterisation
from mxcubecore.HardwareObjects.XSDataMXCuBEv1_4 import (
    XSDataInputMXCuBE,
    XSDataResultMXCuBE,
)
from mxcubecore.model import queue_model_objects as qmo

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3"


class EDNACharacterisationMockup(EDNACharacterisation):
    def __init__(self, name) -> None:
        super(EDNACharacterisationMockup, self).__init__(name)

    def input_from_params(self, data_collection, char_params) -> XSDataInputMXCuBE:
        return XSDataInputMXCuBE.parseString(self.edna_default_input)

    def characterise(self, edna_input) -> XSDataResultMXCuBE:
        return XSDataResultMXCuBE.parseString(edna_test_data.EDNA_RESULT_DATA)

    def is_running(self) -> bool:
        return False

    def dc_from_output(
        self, edna_result, reference_image_collection
    ) -> List[qmo.DataCollection]:
        return []

    def get_default_characterisation_parameters(self) -> qmo.CharacterisationParameters:
        return super(
            EDNACharacterisationMockup, self
        ).get_default_characterisation_parameters()
