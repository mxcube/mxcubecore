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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import numpy
import gevent

from GenericParallelProcessing import GenericParallelProcessing


__license__ = "LGPLv3"


class ParallelProcessingMockup(GenericParallelProcessing):
    def __init__(self, name):
        GenericParallelProcessing.__init__(self, name)

        self.result_type = None

    def init(self):
        GenericParallelProcessing.init(self)
        self.result_type = self.getProperty("result_type", "random")

    def run_processing(self, data_collection):
        """
        no     : no frames with a score
        firste : first frame has a score
        middle : middle frame has a score
        last   : last frame has a score
        linear : score distributed in a linear way
        random : random score distribution
        """
        self.data_collection = data_collection
        self.prepare_processing()

        self.emit(
            "paralleProcessingResults", (self.results_aligned, self.params_dict, False)
        )

        index = 0
        for key in self.results_raw.keys():
            if self.result_type == "first":
                self.results_raw[key][0] = 1
            elif self.result_type == "last":
                self.results_raw[key][self.params_dict["images_num"] - 1] = 1
            elif self.result_type == "middle":
                self.results_raw[key][self.params_dict["images_num"] / 2 - 1] = 1
                self.results_raw[key][self.params_dict["images_num"] / 2] = 3
                self.results_raw[key][self.params_dict["images_num"] / 2 + 1] = 2.5
            elif self.result_type == "linear":
                self.results_raw[key] = (
                    numpy.linspace(
                        0,
                        self.params_dict["images_num"],
                        self.params_dict["images_num"],
                    )
                    + index
                )
            elif self.result_type == "random":
                self.results_raw[key] = numpy.random.randint(
                    1, self.params_dict["images_num"], self.params_dict["images_num"]
                )

            if key == "spots_resolution":
                self.results_raw[key] = (
                    self.results_raw[key]
                    / float(self.params_dict["images_num"])
                    * self.params_dict["resolution"]
                    + self.params_dict["resolution"]
                )
                self.results_raw[key] = 1.0 / self.results_raw[key]

            index += 1

        for index in range(self.params_dict["images_num"]):
            if not index % 10:
                self.align_processing_results(index - 10, index)
                gevent.sleep(0.1)
                self.emit(
                    "paralleProcessingResults",
                    (self.results_aligned, self.params_dict, False),
                )
                self.print_log(
                    "GUI",
                    "info",
                    "Parallel processing: Frame %d/%d done"
                    % (index + 1, self.params_dict["images_num"]),
                )
        self.align_processing_results(0, self.params_dict["images_num"] - 1)
        self.emit(
            "paralleProcessingResults", (self.results_aligned, self.params_dict, False)
        )

        self.set_processing_status("Success")
