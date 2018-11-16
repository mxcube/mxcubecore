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

import os
import time
import gevent
import logging

from GenericParallelProcessing import GenericParallelProcessing

from XSDataCommon import XSDataBoolean
from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataString
from XSDataControlDozorv1_1 import XSDataInputControlDozor
from XSDataControlDozorv1_1 import XSDataResultControlDozor
from XSDataControlDozorv1_1 import XSDataControlImageDozor

import numpy

from scipy.interpolate import UnivariateSpline


__license__ = "LGPLv3+"


class EMBLParallelProcessing(GenericParallelProcessing):
    def __init__(self, name):
        GenericParallelProcessing.__init__(self, name)

        self.chan_dozor_pass = None
        self.chan_frame_count = None

    def init(self):
        GenericParallelProcessing.init(self)

        self.chan_dozor_pass = self.getChannelObject("chanDozorPass")
        self.chan_dozor_pass.connectSignal("update", self.batch_processed)
        self.chan_frame_count = self.getChannelObject("chanFrameCount")
        self.chan_frame_count.connectSignal("update", self.frame_count_changed)

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
        input_file.setPixelMin(XSDataInteger(self.detector_hwobj.get_pixel_min()))
        input_file.setPixelMax(XSDataInteger(self.detector_hwobj.get_pixel_max()))
        input_file.setBeamstopSize(XSDataDouble(self.beamstop_hwobj.get_size()))
        input_file.setBeamstopDistance(XSDataDouble(self.beamstop_hwobj.get_distance()))
        input_file.setBeamstopDirection(
            XSDataString(self.beamstop_hwobj.get_direction())
        )

        input_file.exportToFile(processing_input_filename)

    def run_processing(self, data_collection):
        """Main parallel processing method.
           1. Generates EDNA input file
           2. Starts EDNA via subprocess

        :param data_collection: data collection object
        :type data_collection: queue_model_objects.DataCollection
        """
        self.data_collection = data_collection
        self.prepare_processing()
        self.create_processing_input_file(
            os.path.join(self.params_dict["directory"], "dozor_input.xml")
        )

        self.emit(
            "paralleProcessingResults", (self.results_aligned, self.params_dict, False)
        )

        self.started = True
        self.display_task = gevent.spawn(self.update_map)

    def frame_count_changed(self, frame_count):
        if self.started and frame_count >= self.params_dict["images_num"] - 1:
            self.set_processing_status("Success")

    def smooth(self):
        good_index = numpy.where(self.results_raw["spots_resolution"] > 1 / 46.0)[0]
        good = self.results_aligned["spots_resolution"][good_index]
        # logging.getLogger("user_level_log").info("%d"%good_index.size)
        for x in range(20, good_index.size, 40):
            self.results_aligned["spots_resolution"][good_index[x]] = numpy.mean(
                good[x - 20: x + 20]
            )

        """  
	   print good_index, self.results_raw["spots_resolution"][good_index]
           f = UnivariateSpline(good_index,self.results_raw["spots_resolution"][good_index],s=10)
           self.results_raw["spots_resolution"][good_index] = f(good_index)
        """
        """
        n = len(self.results_raw["spots_resolution"])
        x = []
        for im in range(0,n):
            if self.results_raw["spots_resolution"]
        f = interp1d(self.results_aligned[""], self.results_aligned["spots_resolution"])
        """
        # for x in range(0, n):
        #   chunk = self.results_aligned["spots_resolution"][x:x+10]
        #      m = float(len(chunk))
        #      if m > 0:
        #         #self.results_aligned["spots_resolution"][x] = sum(chunk)/m

    def batch_processed(self, batch):
        """Method called from EDNA via xmlrpc to set results

        :param batch: list of dictionaries describing processing results
        :type batch: lis
        """
        # logging.getLogger("user_level_log").info("Batch arrived %s" % str(self.started))
        if self.started and (type(batch) in (tuple, list)):
            if type(batch[0]) not in (tuple, list):
                batch = [batch]

            for image in batch:
                frame_num = int(image[0])
                self.results_raw["spots_num"][frame_num] = image[1]
                self.results_raw["spots_resolution"][frame_num] = 1 / image[3]
                self.results_raw["score"][frame_num] = image[2]

                for score_key in self.results_raw.keys():
                    if self.params_dict["lines_num"] > 1:
                        col, row = self.grid.get_col_row_from_image(frame_num)
                        self.results_aligned[score_key][col][row] = self.results_raw[
                            score_key
                        ][frame_num]
                    else:
                        self.results_aligned[score_key][frame_num] = self.results_raw[
                            score_key
                        ][frame_num]
            if self.params_dict["lines_num"] <= 1:
                self.smooth()

            # self.emit("paralleProcessingResults",
            #          (self.results_aligned,
            #           self.params_dict,
            #           False))

    def update_map(self):
        gevent.sleep(1)
        while self.started:
            self.emit(
                "paralleProcessingResults",
                (self.results_aligned, self.params_dict, False),
            )
            if self.params_dict["lines_num"] > 1:
                self.grid.set_score(self.results_raw["score"])
            gevent.sleep(0.5)

    def set_processing_status(self, status):
        """Sets processing status and finalize the processing
           Method called from EDNA via xmlrpc

        :param status: processing status (Success, Failed)
        :type status: str
        """
        self.batch_processed(self.chan_dozor_pass.getValue())
        GenericParallelProcessing.set_processing_status(self, status)

    def store_processing_results(self, status):
        GenericParallelProcessing.store_processing_results(self, status)
        self.display_task.kill()

        processing_xml_filename = os.path.join(
            self.params_dict["directory"], "dozor_result.xml"
        )
        dozor_result = XSDataResultControlDozor()
        for index in range(self.params_dict["images_num"]):
            dozor_image = XSDataControlImageDozor()
            dozor_image.setNumber(XSDataInteger(index))
            dozor_image.setScore(XSDataDouble(self.results_raw["score"][index]))
            dozor_image.setSpots_num_of(
                XSDataInteger(self.results_raw["spots_num"][index])
            )
            dozor_image.setSpots_resolution(
                XSDataDouble(self.results_raw["spots_resolution"][index])
            )
            dozor_result.addImageDozor(dozor_image)
        dozor_result.exportToFile(processing_xml_filename)
        logging.getLogger("HWR").info(
            "Parallel processing: Results saved in %s" % processing_xml_filename
        )
