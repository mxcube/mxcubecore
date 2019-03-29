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


"""
EMBLParallelProcessing
"""

import os
import logging

import numpy
import gevent

from HardwareRepository.HardwareObjects.GenericParallelProcessing import (
    GenericParallelProcessing,
)

from HardwareRepository.HardwareObjects.XSDataCommon import (
    XSDataBoolean,
    XSDataDouble,
    XSDataInteger,
    XSDataString,
)
from HardwareRepository.HardwareObjects.XSDataControlDozorv1_1 import (
    XSDataInputControlDozor,
    XSDataResultControlDozor,
    XSDataControlImageDozor,
)


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "Motor"


class EMBLParallelProcessing(GenericParallelProcessing):
    """
    EMBLParallelProcessing
    """

    def __init__(self, name):
        """
        Init
        :param name:
        """
        GenericParallelProcessing.__init__(self, name)

        self.chan_dozor_pass = None
        self.chan_frame_count = None
        self.display_task = None

    def init(self):
        """
        Init
        :return:
        """

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
        """
        :param data_collection: data collection object
        :type data_collection: queue_model_objects.DataCollection
        """
        self.data_collection = data_collection
        self.prepare_processing()
        self.create_processing_input_file(
            os.path.join(self.params_dict["process_directory"], "dozor_input.xml")
        )

        self.emit(
            "processingStarted",
            (self.params_dict, self.results_raw, self.results_aligned),
        )
        self.emit("processingResultsUpdate", False)

        self.started = True
        self.display_task = gevent.spawn(self.update_map)

    def frame_count_changed(self, frame_count):
        """
        Finishes processing if the last frame is processed
        :param frame_count:
        :return:
        """
        if self.started:
            self.emit("processingFrame", frame_count)
            if frame_count >= self.params_dict["images_num"] - 1:
                self.set_processing_status("Success")

    def smooth(self):
        """
        Smooths the resolution
        :return:
        """
        good_index = numpy.where(self.results_raw["spots_resolution"] > 1 / 46.0)[0]
        good = self.results_aligned["spots_resolution"][good_index]
        if self.results_raw["spots_resolution"].size > 200:
            points_index = self.results_raw["spots_resolution"].size / 200

            for x in range(0, good_index.size, points_index):
                self.results_aligned["spots_resolution"][good_index[x]] = numpy.mean(
                    good[max(x - points_index / 2, 0) : x + points_index / 2]
                )

        # logging.getLogger("user_level_log").info("%d"%good_index.size)
        # for x in range(20, good_index.size, 1):
        #    self.results_aligned["spots_resolution"][good_index[x]] = numpy.mean(good[x-20:x+20])

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
            # if self.params_dict["lines_num"] <= 1:
            #   self.smooth()

    def update_map(self):
        """
        Emits heat map update signal
        :return:
        """
        gevent.sleep(1)
        while self.started:
            self.emit("processingResultsUpdate", False)
            if self.params_dict["lines_num"] > 1:
                self.grid.set_score(self.results_raw["score"])
            gevent.sleep(0.5)

    def set_processing_status(self, status):
        """Sets processing status and finalize the processing
           Method called from EDNA via xmlrpc

        :param status: processing status (Success, Failed)
        :type status: str
        """
        # self.batch_processed(self.chan_dozor_pass.getValue())
        GenericParallelProcessing.set_processing_status(self, status)

    def store_processing_results(self, status):
        """
        Stors processing results
        :param status: str
        :return:
        """
        GenericParallelProcessing.store_processing_results(self, status)
        self.display_task.kill()
        gevent.spawn(self.store_result_xml)

        if self.params_dict["workflow_type"] == "Still":
            self.start_crystfel_autoproc()

    def store_result_xml(self):
        """
        Stores results in xml for further usage
        :return:
        """
        processing_xml_filename = os.path.join(
            self.params_dict["process_directory"], "dozor_result.xml"
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

    def start_crystfel_autoproc(self):
        """
        Start crystfel processing
        :return:
        """
        acq_params = self.data_collection.acquisitions[0].acquisition_parameters
        proc_params = self.data_collection.processing_parameters

        lst_filename = os.path.join(
            self.params_dict["process_directory"], "crystfel_hits.lst"
        )
        stream_filename = os.path.join(
            self.params_dict["process_directory"], "crystfel_stream.stream"
        )
        geom_filename = os.path.join(
            self.params_dict["process_directory"], "crystfel_detector.geom"
        )
        cell_filename = os.path.join(
            self.params_dict["process_directory"], "crystfel_cell.cell"
        )

        # Writes lst file for crystfel
        try:
            lst_file = open(lst_filename, "w")
            for index in range(self.params_dict["images_num"]):
                if self.results_raw["score"][index] > 0:
                    lst_file.write(
                        self.params_dict["template"]
                        % (self.params_dict["run_number"], index + 1)
                        + "\n"
                    )
            self.print_log(
                "HWR",
                "debug",
                "Parallel processing: Hit list stored in %s" % lst_filename,
            )
        except BaseException:
            self.print_log(
                "GUI",
                "error",
                "Parallel processing: Unable to store hit list in %s" % lst_filename,
            )
        finally:
            lst_file.close()

        geom_file = """
clen = 0.12000
photon_energy = {energy}

adu_per_photon = 1
res = 13333.3   ; 75 micron pixel size

panel0/min_fs = 0
panel0/min_ss = 0
panel0/max_fs = 2069
panel0/max_ss = 2166
panel0/corner_x = -1118.00
panel0/corner_y = -1079.00
panel0/fs = x
panel0/ss = y
""".format(
            energy=acq_params.energy
        )

        data_file = open(geom_filename, "w")
        data_file.write(geom_file)
        data_file.close()

        """
        if "P1" in proc_params.space_group:
            lattice_type = "triclinic"

        lattice_types = ("triclinic",
                         "monoclinic",
                         "orthorhombic",
                         "tetragonal",
                         "trigonal",
                         "hexagonal",
                         "cubic")
        """

        cell_file = """
CrystFEL unit cell file version 1.0

lattice_type = tetragonal
centering = P
unique_axis = c

a = {cell_a} A
b = {cell_b} A
c = {cell_c} A
al = {cell_alpha} deg
be = {cell_beta} deg
ga = {cell_gamma} deg
""".format(
            cell_a=proc_params.cell_a,
            cell_b=proc_params.cell_b,
            cell_c=proc_params.cell_c,
            cell_alpha=proc_params.cell_alpha,
            cell_beta=proc_params.cell_beta,
            cell_gamma=proc_params.cell_gamma,
        )

        data_file = open(cell_filename, "w")
        data_file.write(cell_file)
        data_file.close()

        point_group = "422"

        """
        proc_params_dict = {"directory" : self.params_dict["directory"],
                            "lst_file": lst_filename,
                            "geom_file": geom_filename,
                            "stream_file" : stream_filename,
                            "cell_filename" : cell_filename,
                            "point_group": "422",
                            "space_group": proc_params.space_group,
                            "hres": acq_params.resolution}
        log.info("Parallel processing: Crystfel processing parameters: %s" % str(proc_params_dict))
        """

        end_of_line_to_execute = " %s %s %s %s %s %s %s %.2f" % (
            self.params_dict["process_directory"],
            lst_filename,
            geom_filename,
            stream_filename,
            cell_filename,
            point_group,
            proc_params.space_group,
            acq_params.resolution,
        )

        self.print_log(
            "HWR",
            "debug",
            "Parallel processing: Starting crystfel %s with parameters %s "
            % (self.crystfel_script, end_of_line_to_execute),
        )

        """
        subprocess.Popen(str(self.crystfel_script + end_of_line_to_execute),
                             shell=True, stdin=None, stdout=None,
                             stderr=None, close_fds=True)
        """
