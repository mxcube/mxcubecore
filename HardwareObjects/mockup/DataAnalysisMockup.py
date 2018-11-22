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

import edna_test_data
import AbstractDataAnalysis

from XSDataMXCuBEv1_3 import XSDataResultMXCuBE

from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["MXCuBE colaboration"]
__license__ = "LGPLv3"


class DataAnalysisMockup(AbstractDataAnalysis.AbstractDataAnalysis, HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

    def get_html_report(self, edna_result):
        html_report = None

        try:
            html_report = str(edna_result.getHtmlPage().getPath().getValue())
        except AttributeError:
            pass

        return html_report

    def from_params(self, data_collection, char_params):
        return

    def characterise(self, edna_input):
        return XSDataResultMXCuBE.parseString(edna_test_data.EDNA_RESULT_DATA)

    def is_running(self):
        return
