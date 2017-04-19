#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import logging
import gevent
import numpy
import subprocess

import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy import ndimage

import SimpleHTML

from HardwareRepository.BaseHardwareObjects import HardwareObject

from XSDataCommon import XSDataBoolean
from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataString
from XSDataControlDozorv1_1 import XSDataInputControlDozor


__license__ = "GPLv3+"


class ParallelProcessing(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        # Hardware objects ----------------------------------------------------
        self.collect_hwobj = None
        self.detector_hwobj = None
        self.beamstop_hwobj = None
        self.lims_hwobj = None

        # Internal variables --------------------------------------------------
        self.start_command = None
        self.run_as_mockup = None
        self.params_dict = None
        self.results_raw = None
        self.results_aligned = None
        self.done_event = None

    def init(self):
        self.done_event = gevent.event.Event()

        self.collect_hwobj = self.getObjectByRole("collect")

        try:
            self.detector_hwobj = self.collect_hwobj.detector_hwobj
            self.lims_hwobj = self.collect_hwobj.lims_client_hwobj
        except:
            try:
                self.detector_hwobj = self.collect_hwobj.bl_config.detector_hwobj
                self.lims_hwobj = self.collect_hwobj.cl_config.lims_client_hwobj
            except:
                pass

        if self.detector_hwobj is None:
            logging.info("ParallelProcessing: Detector hwobj not defined")

        self.beamstop_hwobj = self.getObjectByRole("beamstop")
        if self.beamstop_hwobj is None:
            logging.info("ParallelProcessing: Beamstop hwobj not defined")

        self.start_command = str(self.getProperty("processing_command"))
        self.run_as_mockup = self.getProperty("run_as_mockup")

    def create_processing_input(self, data_collection):
        """Creates dozor input file base on data collection parameters

        :param data_collection: data collection object
        :type : queue_model_objects.DataCollection
        """
        acquisition = data_collection.acquisitions[0]
        acq_params = acquisition.acquisition_parameters

        input_file = XSDataInputControlDozor()
        image_file_template = "%s_%%d_%%05d.cbf" % (
            acquisition.path_template.get_prefix())

        template = os.path.join(acquisition.path_template.directory,
                                image_file_template)

        first_image_num = acq_params.first_image
        images_num = acq_params.num_images
        last_image_num = first_image_num + images_num - 1
        run_number = acquisition.path_template.run_number
        lines_num = acq_params.num_lines
        pixel_min = 0
        pixel_max = 0
        beamstop_size = 0
        beamstop_distance = 0
        beamstop_direction = 0

        pixel_min = self.detector_hwobj.get_pixel_min()
        pixel_max = self.detector_hwobj.get_pixel_max()
        beamstop_size = self.beamstop_hwobj.get_size()
        beamstop_distance = self.beamstop_hwobj.get_distance()
        beamstop_direction = self.beamstop_hwobj.get_direction()

        if data_collection.grid:
            grid_params = data_collection.grid.get_properties()
            reversing_rotation = grid_params["reversing_rotation"]
        else:
            reversing_rotation = False

        self.params_dict["template"] = template
        self.params_dict["first_image_num"] = first_image_num
        self.params_dict["images_num"] = images_num
        self.params_dict["lines_num"] = lines_num
        self.params_dict["images_per_line"] = images_num / lines_num
        self.params_dict["run_number"] = run_number
        self.params_dict["pixel_min"] = pixel_min
        self.params_dict["pixel_max"] = pixel_max
        self.params_dict["beamstop_size"] = beamstop_size
        self.params_dict["beamstop_distance"] = beamstop_distance
        self.params_dict["beamstop_direction"] = beamstop_direction
        self.params_dict["status"] = "Started"
        self.params_dict["title"] = "%s_%d_#####.cbf (%d - %d)" % \
             (acquisition.path_template.get_prefix(),
              acquisition.path_template.run_number,
              first_image_num,
              last_image_num)
        self.params_dict["comments"] = "Scan lines: %d, frames per line: %d" % \
             (lines_num, images_num / lines_num)

        if lines_num > 1:
            self.params_dict["dx_mm"] = grid_params["dx_mm"]
            self.params_dict["dy_mm"] = grid_params["dy_mm"]
            self.params_dict["steps_x"] = grid_params["steps_x"]
            self.params_dict["steps_y"] = grid_params["steps_y"]
            self.params_dict["xOffset"] = grid_params["xOffset"]
            self.params_dict["yOffset"] = grid_params["yOffset"]
        else:
            self.params_dict["steps_y"] = 1

        input_file.setTemplate(XSDataString(template))
        input_file.setFirst_image_number(XSDataInteger(first_image_num))
        input_file.setLast_image_number(XSDataInteger(last_image_num))
        input_file.setFirst_run_number(XSDataInteger(run_number))
        input_file.setLast_run_number(XSDataInteger(run_number))
        input_file.setLine_number_of(XSDataInteger(lines_num))
        input_file.setReversing_rotation(XSDataBoolean(reversing_rotation))
        input_file.setPixelMin(XSDataInteger(pixel_min))
        input_file.setPixelMax(XSDataInteger(pixel_max))
        input_file.setBeamstopSize(XSDataDouble(beamstop_size))
        input_file.setBeamstopDistance(XSDataDouble(beamstop_distance))
        input_file.setBeamstopDirection(XSDataString(beamstop_direction))

        return input_file

    def run_processing(self, data_collection):
        """Main parallel processing method.
           1. Generates EDNA input file
           2. Starts EDNA via subprocess

        :param data_collection: data collection object
        :type data_collection: queue_model_objects.DataCollection
        """

        acquisition = data_collection.acquisitions[0]
        acq_params = acquisition.acquisition_parameters
        self.processing_results_align = {}

        prefix = acquisition.path_template.get_prefix()
        run_number = acquisition.path_template.run_number
        process_directory = acquisition.path_template.process_directory
        archive_directory = acquisition.path_template.get_archive_directory()
        self.grid = data_collection.grid

        # Estimates dozor directory. If run number found then creates
        # processing and archive directory
        i = 1
        while True:
            processing_input_file_dirname = "dozor_%s_run%s_%d" % \
                                            (prefix, run_number, i)
            processing_directory = os.path.join(\
               process_directory, processing_input_file_dirname)
            processing_archive_directory = os.path.join(\
               archive_directory, processing_input_file_dirname)
            if not os.path.exists(processing_directory):
                break
            i += 1
        if not os.path.isdir(processing_directory):
            os.makedirs(processing_directory)
        if not os.path.isdir(processing_archive_directory):
            os.makedirs(processing_archive_directory)

        try:
            grid_snapshot_filename = None
            if data_collection.grid is not None:
                grid_snapshot_filename = os.path.join(\
                    processing_archive_directory, "grid_snapshot.png")
                logging.getLogger("HWR").info("Saving grid snapshot: %s" % \
                    grid_snapshot_filename)
                grid_snapshot = data_collection.grid.get_snapshot()
                grid_snapshot.save(grid_snapshot_filename, 'PNG')
        except:
            logging.getLogger("HWR").exception(\
                "Could not save grid snapshot: %s" \
                % grid_snapshot_filename)

        self.params_dict = {}
        self.params_dict["workflow_type"] = data_collection.run_processing_parallel
        self.params_dict["directory"] = processing_directory
        self.params_dict["processing_archive_directory"] = processing_archive_directory
        self.params_dict["grid_snapshot_filename"] = grid_snapshot_filename
        self.params_dict["images_num"] = acq_params.num_lines
        self.params_dict["result_file_path"] = \
             self.params_dict["processing_archive_directory"]
        self.params_dict["plot_path"] = os.path.join(\
             self.params_dict["directory"],
             "parallel_processing_result.png")
        self.params_dict["cartography_path"] = os.path.join(\
             self.params_dict["processing_archive_directory"],
             "parallel_processing_result.png")
        self.params_dict["log_file_path"] = os.path.join(\
             self.params_dict["processing_archive_directory"],
             "dozor_log.log")
        self.params_dict["group_id"] = data_collection.lims_group_id
        self.params_dict["processing_start_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

        processing_input = self.create_processing_input(data_collection)
        processing_input_file = os.path.join(processing_directory, "dozor_input.xml")
        processing_input.exportToFile(processing_input_file)

        self.results_raw = \
             {"image_num" : numpy.zeros(self.params_dict["images_num"]),
              "spots_num" : numpy.zeros(self.params_dict["images_num"]),
              "spots_int_aver" : numpy.zeros(self.params_dict["images_num"]),
              "spots_resolution" : numpy.zeros(self.params_dict["images_num"]),
              "score" : numpy.zeros(self.params_dict["images_num"])}
        self.align_processing_results(self.results_raw, self.grid)
        self.emit("paralleProcessingResults",
                  (self.processing_results_align,
                   self.params_dict,
                   False))

        return

        if not self.run_as_mockup:
            if not os.path.isfile(self.start_command):
                msg = "ParallelProcessing: Start command %s" % \
                      self.start_command + \
                      "is not executable"
                logging.getLogger("queue_exec").error(msg)
                self.set_processing_status("Failed")
            else:
                msg = "ParallelProcessing: Starting processing using " + \
                      "xml file %s" % processing_input_file
                logging.getLogger("queue_exec").info(msg)
                line_to_execute = self.start_command + ' ' + \
                      processing_input_file + ' ' + \
                      processing_directory

                subprocess.Popen(str(line_to_execute), shell=True, stdin=None,
                      stdout=None, stderr=None, close_fds=True)
        else:
            add = 0 
            for key in self.results_raw.keys():
                self.results_raw[key] = numpy.linspace(0, 
                   self.params_dict["images_num"], 
                   self.params_dict["images_num"]) + add
                add += 10
            self.align_processing_results(self.results_raw, self.grid)
            self.set_processing_status("Success")

    def is_running(self):
        """Returns True if processing is running"""

        return not self.done_event.is_set()

    def stop_processing(self):
        """Stops processing"""

        self.set_processing_status("Stopped")

    def batch_processed(self, batch):
        """Method called from EDNA via xmlrpc to set results

        :param batch: list of dictionaries describing processing results
        :type batch: list
        """

        """
        for image in batch:
            self.results_raw["spots_num"]\
                 [image["image_num"]] = image["spots_num_of"]
            self.results_raw["spots_int_aver"]\
                 [image["image_num"]] = image["spots_int_aver"]
            self.results_raw["spots_resolution"]\
                 [image["image_num"]] = image["spots_resolution"]
            self.results_raw["score"]\
                 [image["image_num"]] = image["score"]
        """
        for image in batch:
            self.results_raw["spots_num"]\
                 [image[0]] = image[1]
            self.results_raw["spots_int_aver"]\
                 [image[0]] = image[2]
            self.results_raw["spots_resolution"]\
                 [image[0]] = image[3]
            self.results_raw["score"]\
                 [image[0]] = image[4]

        self.align_processing_results(self.results_raw, self.grid)
        self.emit("paralleProcessingResults",
                  (self.processing_results_align,
                   self.params_dict,
                   False))

    def set_processing_status(self, status):
        """Sets processing status and finalize the processing
           Method called from EDNA via xmlrpc

        :param status: processing status (Success, Failed)
        :type status: str
        """

        log = logging.getLogger("HWR")
        self.params_dict["status"] = status

        if status == "Failed": 
            self.emit("processingFailed")
        else:
            self.emit("processingFinished")

        
        self.emit("paralleProcessingResults",
                  (self.processing_results_align,
                   self.params_dict,
                   True))

        #Processing finished. Results are aligned and 10 best positions estimated
        self.params_dict["processing_programs"] = "EDNAdozor"
        self.params_dict["processing_end_time"] = \
            time.strftime("%Y-%m-%d %H:%M:%S")
        self.params_dict["max_dozor_score"] = \
            self.processing_results_align["score"].max()
        best_positions = self.processing_results_align.get("best_positions", [])

        # We store MeshScan and XrayCentring workflow in ISPyB
        # Parallel processing is also executed for all osc that have
        # more than 20 images, but results are not stored as workflow

        fig, ax = plt.subplots(nrows=1, ncols=1)
        if self.params_dict["lines_num"] > 1:
            log.info("Saving autoprocessing program in ISPyB")
            self.lims_hwobj.store_autoproc_program(self.params_dict)

            log.info("Saving processing results in ISPyB")
            workflow_id, workflow_mesh_id, grid_info_id = \
                 self.lims_hwobj.store_workflow(self.params_dict)
            self.params_dict["workflow_id"] = workflow_id
            self.params_dict["workflow_mesh_id"] = workflow_mesh_id
            self.params_dict["grid_info_id"] = grid_info_id

            self.collect_hwobj.update_lims_with_workflow(workflow_id,
                 self.params_dict["grid_snapshot_filename"])

            self.lims_hwobj.store_workflow_step(self.params_dict)

            try:
                html_filename = os.path.join(self.params_dict["result_file_path"],
                                             "index.html")
                log.info("Generating results html %s" % html_filename)
                SimpleHTML.generate_mesh_scan_report(\
                    self.processing_results_align, self.params_dict,
                    html_filename)
            except:
                log.exception("Could not create result html %s" % html_filename)

            # Heat map generation
            # If mesh scan then a 2D plot
            im = ax.imshow(self.processing_results_align["score"],
                           interpolation='none', aspect='auto',
                           extent=[0, self.processing_results_align["score"].shape[1], 0,
                                   self.processing_results_align["score"].shape[0]])
            if len(best_positions) > 0:
                plt.axvline(x=best_positions[0]["col"] - 0.5, linewidth=0.5)
                plt.axhline(y=best_positions[0]["row"] - 0.5, linewidth=0.5)

            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size=0.1, pad=0.05)
            cax.tick_params(axis='x', labelsize=8)
            cax.tick_params(axis='y', labelsize=8)
            plt.colorbar(im, cax=cax)
            im.set_cmap('hot')
        else:
            #if helical line then a line plot
            plt.plot(self.processing_results_align["score"],
                     label="Total score",
                     color="r")
            plt.plot(self.processing_results_align["spots_num"],
                     label="Number of spots",
                     linestyle="None",
                     color="b",
                     marker="o")
            plt.plot(self.processing_results_align["spots_int_aver"],
                     label="Int aver",
                     linestyle="None",
                     color="g",
                     marker="s")
            plt.plot(self.processing_results_align["spots_resolution"],
                     linestyle="None",
                     label="Resolution",
                     color="m",
                     marker="s")
            plt.legend()
            ylim = ax.get_ylim()
            ax.set_ylim((-1, ylim[1]))

        ax.tick_params(axis='x', labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        ax.set_title(self.params_dict["title"], fontsize=8)

        ax.grid(True)
        ax.spines['left'].set_position(('outward', 10))
        ax.spines['bottom'].set_position(('outward', 10))

        processing_plot_file = os.path.join(self.params_dict\
             ["directory"], "parallel_processing_result.png")
        processing_plot_archive_file = os.path.join(self.params_dict\
             ["processing_archive_directory"], "parallel_processing_result.png")

        try:
            log.info("Saving heat map figure %s" % \
                processing_plot_file)
            if not os.path.exists(os.path.dirname(processing_plot_file)):
                os.makedirs(os.path.dirname(processing_plot_file))
            fig.savefig(processing_plot_file, dpi=150, bbox_inches='tight')
        except:
            log.exception("Could not save figure %s" % \
                processing_plot_file)
        try:
            log.info("Saving heat map figure for ISPyB %s" % \
                processing_plot_archive_file)
            if not os.path.exists(os.path.dirname(processing_plot_archive_file)):
                os.makedirs(os.path.dirname(processing_plot_archive_file))
            fig.savefig(processing_plot_archive_file, dpi=150, bbox_inches='tight')
        except:
            log.exception("Could not save figure for ISPyB %s" % \
                processing_plot_archive_file)
        plt.close(fig)
        self.done_event.set()

    def align_processing_results(self, results_dict, grid):
        """Realigns all results. Each results (one dimensional numpy array)
           is converted to 2d numpy array according to diffractometer geometry.
           Function also extracts 10 (if they exist) best positions

        :param results_dict: 5 one dimensional numpy arrays with results
        :type results_dict: dict
        :param grid: grid object
        :type grid: GraphicsLib.GraphicsItemGrid
        """

        #Each result array is realigned
        aligned_results = {}
        for key in results_dict.iterkeys():
            self.processing_results_align[key] = \
                self.align_result_array(results_dict[key], grid)
        if self.params_dict['lines_num'] > 1:
            grid.set_score(results_dict['score'])

        #Best positions are extracted
        best_positions_list = []
        index_arr = (-results_dict["score"]).argsort()[:10]
        if len(index_arr) > 0:
            for index in index_arr:
                if results_dict["score"][index] > 0:
                    best_position = {}
                    best_position["index"] = index
                    best_position["index_serial"] = self.params_dict["first_image_num"] + index
                    best_position["score"] = float(results_dict["score"][index])
                    best_position["spots_num"] = int(results_dict["spots_num"][index])
                    best_position["spots_int_aver"] = float(results_dict["spots_int_aver"][index])
                    best_position["spots_resolution"] = float(results_dict["spots_resolution"][index])
                    best_position["filename"] = os.path.basename(self.params_dict["template"] % \
                        (self.params_dict["run_number"],
                         self.params_dict["first_image_num"] + index))

                    cpos = None
                    if self.params_dict["lines_num"] > 1:
                        col, row = grid.get_col_row_from_image_serial(\
                             index + self.params_dict["first_image_num"])
                        cpos = grid.get_motor_pos_from_col_row(\
                             col, row, as_cpos=True)
                        #entred_position = self.params_dict["associated_grid"].get_motor_pos_from_col_row(col, row)
                    else:
                        col = index
                        row = 0
                        #cpos = self.params_dict["associated_data_collection"].get_motor_pos(index, as_cpos=True)
                        cpos = None
                        #TODO Add best position for helical line
                    best_position["col"] = col + 1
                    best_position["row"] = self.params_dict["steps_y"] - row
                    best_position['cpos'] = cpos
                    best_positions_list.append(best_position)
        self.processing_results_align["best_positions"] = best_positions_list

    def align_result_array(self, result_array, grid):
        """Realigns result array based on the grid

        :returns: numpy 2d array
        """
        num_lines = self.params_dict["lines_num"]
        if num_lines == 1:
            if result_array.max() != 0:
                return result_array / result_array.max()
            else:
                return result_array

        num_images_per_line = self.params_dict["images_per_line"]
        num_colls = self.params_dict["steps_x"]
        num_rows = self.params_dict["steps_y"]
        first_image_number = self.params_dict["first_image_num"]

        aligned_result_array = numpy.zeros(num_lines * num_images_per_line).\
                        reshape(num_colls, num_rows)

        for cell_index in range(aligned_result_array.size):
            col, row = grid.get_col_row_from_image_serial(\
                cell_index + first_image_number)
            if (col < aligned_result_array.shape[0] and
                row < aligned_result_array.shape[1]):
                aligned_result_array[col][row] = result_array[cell_index]
        if aligned_result_array.max() > 0:
            aligned_result_array = aligned_result_array / \
                aligned_result_array.max() 

        return numpy.transpose(aligned_result_array)

    def extract_sweeps(self):
        """Extracts sweeps from processing results"""

        #self.processing_results_align
        logging.getLogger("HWR").info("ParallelProcessing: Extracting sweeps")
        for col in range(self.processing_results_align["score"].shape[1]):
            mask = self.processing_results_align['score'][:, col] > 0
            label_im, nb_labels = ndimage.label(mask)
            sizes = ndimage.sum(mask, label_im, range(nb_labels + 1))
            labels = numpy.unique(label_im)
            label_im = numpy.searchsorted(labels, label_im)
