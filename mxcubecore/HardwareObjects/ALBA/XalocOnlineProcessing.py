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
import subprocess

from mxcubecore.HardwareObjects.DozorOnlineProcessing import (
    DozorOnlineProcessing,
)

from XSDataCommon import XSDataBoolean
from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataString
from XSDataControlDozorv1_1 import XSDataInputControlDozor
from XSDataControlDozorv1_1 import XSDataResultControlDozor
from XSDataControlDozorv1_1 import XSDataControlImageDozor

import numpy

from scipy import ndimage
from scipy.interpolate import UnivariateSpline

from mxcubecore import HardwareRepository as HWR

__credits__ = ["ALBA Synchrotron"]
__licence__ = "LGPLv3+"
__version__ = "3"
__category__ = "General"

class XalocOnlineProcessing(DozorOnlineProcessing):
    def __init__(self, name):
        DozorOnlineProcessing.__init__(self, name)
        self.logger = logging.getLogger("HWR.XalocOnlineProcessing")

    def init(self):
        DozorOnlineProcessing.init(self)

    def run_processing(self, data_collection):
        """Starts parallel processing

        :param: data_collection: data collection obj
        :type: data_collection: queue_model_objects.DataCollection

        """
        self.data_collection = data_collection
        self.prepare_processing()

        input_filename = self.get_input_filename(self.data_collection)
        if not input_filename:
            input_filename = os.path.join(
                self.params_dict["process_directory"], "dozor_input.xml"
            )

        self.create_processing_input_file(input_filename)

        # results = {"raw" : self.results_raw,
        #           "aligned": self.results_aligned}
        # print "emit ! ", results
        # self.emit("processingStarted", (data_collection, results))
        # self.emit("processingResultsUpdate", False)

        if not os.path.isfile(self.start_command):
            msg = (
                "ParallelProcessing: Start command %s" % self.start_command
                + "is not executable"
            )
            self.logger.error(msg)
            self.set_processing_status("Failed")
        else:
            #TODO: it can be something more complex than a script file
            line_to_execute = (
                self.start_command
                + " "
                + input_filename
                #+ " "
                #+ self.params_dict["process_directory"]
            )
            
            line_to_execute = (
                'ssh opbl13@ctbl1301 \"' 
                + line_to_execute 
                + '\" '
            )
            self.logger.debug("Processing DOZOR with command: %s" % line_to_execute)

            self.started = True
            subprocess.Popen(
                str(line_to_execute),
                shell=True,
#                stdin=None,
#                stdout=None,
#                stderr=None,
#                close_fds=True,
            )

    def create_processing_input_file(self, processing_input_filename):
        """Creates dozor input file base on data collection parameters

        :param processing_input_filename
        :type : str
        """

        self.logger.debug('Creating Dozor input file %s' % processing_input_filename )

        input_file = XSDataInputControlDozor()
        input_file.setTemplate(XSDataString(self.params_dict["template"]))
        input_file.setFirst_image_number(XSDataInteger(self.params_dict["first_image_num"]))
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
        #input_file.setPixelMin(XSDataInteger(HWR.beamline.detector.get_pixel_min()))
        #input_file.setPixelMax(XSDataInteger(HWR.beamline.detector.get_pixel_max()))
        #input_file.setBeamstopSize(XSDataDouble(self.beamstop_hwobj.get_size()))
        #input_file.setBeamstopDistance(XSDataDouble(self.beamstop_hwobj.get_distance()))
        #input_file.setBeamstopDirection(XSDataString(self.beamstop_hwobj.get_direction()))

        input_file.exportToFile(processing_input_filename)

    def get_input_filename(self, data_collection):
        # Create dozor dir as in XalocCollect
        dozor_dir = self._create_proc_files_directory('dozor')
        input_filename = os.path.join(dozor_dir, "dozor_input.xml")
        return input_filename

    #def batch_processed2(self, batch):
        #"""Method called from EDNA via xmlrpc to set results

        #:param batch: list of dictionaries describing processing results
        #:type batch: lis
        #"""
        ## FORCED FOR TESTING
        ##No longer self.started = True

        #self.logger.debug("Batch arrived %s" % str(self.started))
        #self.logger.debug("Batch is %s" % batch)
        #if self.started and (type(batch) in (tuple, list)):
            #if type(batch[0]) not in (tuple, list):
                #batch = [batch]
            #self.logger.debug("Batch, for each image in batch")
            #for image in batch:
                #frame_num = int(image[0])
                #self.logger.debug("Frame number is %s" % frame_num)
                #self.results_raw["spots_num"][frame_num] = image[1]
                #self.results_raw["spots_resolution"][frame_num] = 1 / image[3]
                #self.results_raw["score"][frame_num] = image[2]

                #for score_key in self.results_raw.keys():
                    #if self.params_dict["lines_num"] > 1:
                        #col, row = self.grid.get_col_row_from_image(frame_num)
                        #self.results_aligned[score_key][col][row] =\
                            #self.results_raw[score_key][frame_num]
                    #else:
                        #self.results_aligned[score_key][frame_num] =\
                            #self.results_raw[score_key][frame_num]
            ## if self.params_dict["lines_num"] <= 1:
            ##    self.smooth()

            ## self.emit("paralleProcessingResults",
            ##          (self.results_aligned,
            ##           self.params_dict,
            ##           False))

    def batch_processed(self, batch):
        """Method called from EDNA via xmlrpc to set results
        :param batch: list of dictionaries describing processing results
        :type batch: lis
        """

        self.logger.debug("batch_processed called, batch is %s" % batch)
        self.logger.debug("Has process started? %s" % str(self.started))

        if self.started:
            for image in batch:
                self.logger.debug("Loop for each image in batch arrived")
                self.logger.debug("image is : %s" % image)
                self.results_raw["spots_num"][image[0] - 1] = image[1]
                self.results_raw["spots_resolution"][image[0] - 1] = image[3]
                self.results_raw["score"][image[0] - 1] = image[2]

            self.align_processing_results(batch[0][0] - 1, batch[-1][0] - 1)

            self.logger.debug("Emitting signal processingResultsUpdate")

            self.emit("processingResultsUpdate", False)

    # ONLY FOR ALBA!!! Similar function present in the XalocCollect
    def _create_proc_files_directory(self, proc_name):

        path_template = self.data_collection.acquisitions[
            0].path_template
        proc_dir = path_template.process_directory
        run_number = path_template.run_number
        prefix = path_template.get_prefix()

        i = 1

        while True:
            logging.getLogger('HWR').debug('*** iteration %s' % i)
            _dirname = "%s_%s_%s_%d" % (
                proc_name,
                prefix,
                run_number,
                i)
            _directory = os.path.join(
                proc_dir,
                _dirname)
            if not os.path.exists(_directory):
                break
            i += 1

        try:
            logging.getLogger('HWR').debug(
                'Creating proc directory %s: ' % _directory)
            self._create_directories(_directory)
            os.system("chmod -R 777 %s" % _directory)
        except Exception as e:
            msg = "Could not create directory %s\n%s" % (_directory, str(e))
            logging.getLogger('HWR').exception(msg)
            return

        # This is not yet implemented fpor dozor...maybe is not necesary

        # save directory names in current_dc_parameters. They will later be used
        #  by autoprocessing.
        # key = "%s_dir" % proc_name
        # self.current_dc_parameters[key] = _directory
        # logging.getLogger('HWR').debug("dc_pars[%s] = %s" % (key, _directory))
        return _directory

    # The following methods are copied to improve error logging, the functionality is the same
    def _create_directories(self, *args):
        """
        Descript. :
        """
        for directory in args:
            logging.getLogger('HWR').debug('Creating directory %s: ' % directory)
            try:
                os.makedirs(directory)
            except OSError as e:
                import errno
                if e.errno != errno.EEXIST:
                    logging.getLogger('HWR').error(
                        'Error in making parallel processing directories')
                    raise

    def align_processing_results(self, start_index, end_index):
        """Realigns all results. Each results (one dimensional numpy array)
           is converted to 2d numpy array according to diffractometer geometry.
           Function also extracts 10 (if they exist) best positions
        """
        # Each result array is realigned

        #self.logger.debug("align_processing_results, start_index %d, end_index %s, self.grid %s" % 
                          #(start_index, end_index, self.grid))
        for score_key in self.results_raw.keys():
            if (
                self.grid
                and self.results_raw[score_key].size == self.params_dict["images_num"]
            ):
                for cell_index in range(start_index, end_index + 1):
                    col, row = self.grid.get_col_row_from_image_serial(
                        cell_index + self.params_dict["first_image_num"]
                    )
                    if (
                        col < self.results_aligned[score_key].shape[0]
                        and row < self.results_aligned[score_key].shape[1]
                    ):
                        self.results_aligned[score_key][col][row] = self.results_raw[
                            score_key
                        ][cell_index]
            else:
                self.results_aligned[score_key] = self.results_raw[score_key]
                if self.interpolate_results:
                    x_array = np.linspace(
                        0,
                        self.params_dict["images_num"],
                        self.params_dict["images_num"],
                        dtype=int,
                    )
                    spline = UnivariateSpline(
                        x_array, self.results_aligned[score_key], s=10
                    )
                    self.results_aligned["interp_" + score_key] = spline(x_array)

        #self.logger.debug("self.results_aligned %s" % (str(self.results_aligned)) )

        if self.grid:
            # TODO: this should depend on the user selection of the self._score_type_cbox selection in the brick
            # IS this even used? The code doesnt get here
            self.grid.set_score(self.results_raw["score"]) 
            (center_x, center_y) = ndimage.measurements.center_of_mass(
                self.results_aligned["score"]
            )
            self.results_aligned["center_mass"] = self.grid.get_motor_pos_from_col_row(
                center_x, center_y
            )
        else:
            centred_positions = self.data_collection.get_centred_positions()
            if len(centred_positions) == 2:
                center_x = ndimage.measurements.center_of_mass(
                    self.results_aligned["score"]
                )[0]
                self.results_aligned[
                    "center_mass"
                ] = HWR.beamline.diffractometer.get_point_from_line(
                    centred_positions[0],
                    centred_positions[1],
                    center_x,
                    self.params_dict["images_num"],
                )
            else:
                self.results_aligned["center_mass"] = centred_positions[0]

        #self.logger.debug("self.results_aligned %s" % (str(self.results_aligned)) )

        # Best positions are extracted
        best_positions_list = []

        index_arr = (-self.results_raw["score"]).argsort()[:10]
        if len(index_arr) > 0:
            for index in index_arr:
                if self.results_raw["score"][index] > 0:
                    best_position = {}
                    best_position["index"] = index
                    best_position["index_serial"] = (
                        self.params_dict["first_image_num"] + index
                    )
                    best_position["score"] = self.results_raw["score"][index]
                    best_position["spots_num"] = self.results_raw["spots_num"][index]
                    best_position["spots_resolution"] = self.results_raw[
                        "spots_resolution"
                    ][index]
                    best_position["filename"] = os.path.basename(
                        self.params_dict["template"]
                        % (
                            self.params_dict["run_number"],
                            self.params_dict["first_image_num"] + index,
                        )
                    )

                    cpos = None
                    if self.grid:
                        col, row = self.grid.get_col_row_from_image_serial(
                            index + self.params_dict["first_image_num"]
                        )
                        col += 0.5
                        row = self.params_dict["steps_y"] - row - 0.5
                        cpos = self.grid.get_motor_pos_from_col_row(col, row)
                    else:
                        col = index
                        row = 0
                        cpos = None
                        # TODO make this nicer
                        # num_images = self.data_collection.acquisitions[0].acquisition_parameters.num_images - 1
                        # (point_one, point_two) = self.data_collection.get_centred_positions()
                        # cpos = HWR.beamline.diffractometer.get_point_from_line(point_one, point_two, index, num_images)
                    best_position["col"] = col
                    best_position["row"] = row
                    best_position["cpos"] = cpos
                    best_positions_list.append(best_position)

        self.results_aligned["best_positions"] = best_positions_list

        self.logger.debug("after best_poitions: self.results_aligned %s" % (str(self.results_aligned)) )


    # def update_map(self):
    #     """Updates plot map
    #
    #     :return: None
    #     """
    #     gevent.sleep(1)
    #     while self.started:
    #         self.emit("paralleProcessingResults",
    #                   (self.results_aligned,
    #                    self.params_dict,
    #                    False))
    #         if self.params_dict["lines_num"] > 1:
    #             self.grid.set_score(self.results_raw['score'])
    #         gevent.sleep(0.5)
    #
    # def set_processing_status(self, status):
    #     """Sets processing status and finalize the processing
    #        Method called from EDNA via xmlrpc
    #
    #     :param status: processing status (Success, Failed)
    #     :type status: str
    #     """
    #     self.batch_processed(self.chan_dozor_pass.get_value())
    #     GenericParallelProcessing.set_processing_status(self, status)
    #
    # def store_processing_results(self, status):
    #     GenericParallelProcessing.store_processing_results(self, status)
    #     self.display_task.kill()
    #
    #     processing_xml_filename = os.path.join(self.params_dict\
    #          ["directory"], "dozor_result.xml")
    #     dozor_result = XSDataResultControlDozor()
    #     for index in range(self.params_dict["images_num"]):
    #         dozor_image = XSDataControlImageDozor()
    #         dozor_image.setNumber(XSDataInteger(index))
    #         dozor_image.setScore(XSDataDouble(self.results_raw["score"][index]))
    #         dozor_image.setSpots_num_of(XSDataInteger(self.results_raw["spots_num"][index]))
    #         dozor_image.setSpots_resolution(XSDataDouble(self.results_raw["spots_resolution"][index]))
    #         dozor_result.addImageDozor(dozor_image)
    #     dozor_result.exportToFile(processing_xml_filename)
    #     logging.getLogger("HWR").info("Parallel processing: Results saved in %s" % processing_xml_filename)
