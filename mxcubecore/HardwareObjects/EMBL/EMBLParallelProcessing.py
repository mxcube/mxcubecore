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

from copy import copy
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy import ndimage

import SimpleHTML

from HardwareRepository.BaseHardwareObjects import HardwareObject

__license__ = "GPLv3+"


class EMBLParallelProcessing(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        # Hardware objects ----------------------------------------------------
        self.collect_hwobj = None
        self.lims_hwobj = None

        # Internal variables --------------------------------------------------
        self.run_as_mockup = None
        self.grid = None
        self.params_dict = None
        self.results_raw = None
        self.results_aligned = None
        self.done_event = None
        self.started = None

        self.chan_dozor_pass = None
        self.chan_frame_count = None

    def init(self):
        self.done_event = gevent.event.Event()

        self.collect_hwobj = self.getObjectByRole("collect")
        self.lims_hwobj = self.collect_hwobj.lims_client_hwobj

        self.chan_dozor_pass = self.getChannelObject("chanDozorPass")
        self.chan_dozor_pass.connectSignal("update", self.batch_processed)
        self.chan_frame_count = self.getChannelObject("chanFrameCount")
        self.chan_frame_count.connectSignal("update", self.frame_count_changed)

    def create_processing_input(self, data_collection):
        """Creates dozor input file base on data collection parameters

        :param data_collection: data collection object
        :type : queue_model_objects.DataCollection
        """
        acquisition = data_collection.acquisitions[0]
        acq_params = acquisition.acquisition_parameters

        if data_collection.grid:
            grid_params = data_collection.grid.get_properties()
            reversing_rotation = grid_params["reversing_rotation"]
        else:
            reversing_rotation = False

        first_image_num = acq_params.first_image
        images_num = acq_params.num_images
        last_image_num = first_image_num + images_num - 1
        run_number = acquisition.path_template.run_number
        lines_num = acq_params.num_lines

        self.params_dict["first_image_num"] = first_image_num
        self.params_dict["images_num"] = images_num
        self.params_dict["lines_num"] = lines_num
        self.params_dict["images_per_line"] = images_num / lines_num
        self.params_dict["run_number"] = run_number
        self.params_dict["osc_midle"] = acq_params.osc_start
        self.params_dict["osc_range"] = acq_params.osc_range
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

    def run_processing(self, data_collection):
        """Main parallel processing method.
           1. Generates EDNA input file
           2. Starts EDNA via subprocess

        :param data_collection: data collection object
        :type data_collection: queue_model_objects.DataCollection
        """
        self.data_collection = data_collection
        acquisition = self.data_collection.acquisitions[0]
        acq_params = acquisition.acquisition_parameters

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
        try:
            if not os.path.isdir(processing_archive_directory):
                os.makedirs(processing_archive_directory)
        except:
            logging.getLogger("GUI").exception(\
                "Unable to create archive directory %s" % \
                processing_archive_directory)

        grid_snapshot_filename = os.path.join(processing_archive_directory,
                                              "grid_snapshot.png")

        gevent.spawn(self.save_grid_snapshot_task,
                     grid_snapshot_filename,
                     data_collection) 

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

        self.create_processing_input(data_collection)

        self.results_raw = \
             {"image_num" : numpy.zeros(self.params_dict["images_num"]),
              "spots_num" : numpy.zeros(self.params_dict["images_num"]),
              "spots_int_aver" : numpy.zeros(self.params_dict["images_num"]),
              "spots_resolution" : numpy.zeros(self.params_dict["images_num"]),
              "score" : numpy.zeros(self.params_dict["images_num"])}

        if self.params_dict["lines_num"] > 1:
             self.results_aligned = \
               {"image_num" : numpy.zeros(self.params_dict["images_num"]).reshape(\
                                          self.params_dict["steps_x"],
                                          self.params_dict["steps_y"]),
                "spots_num" : numpy.zeros(self.params_dict["images_num"]).reshape(\
                                          self.params_dict["steps_x"],
                                          self.params_dict["steps_y"]),
                "spots_int_aver" : numpy.zeros(self.params_dict["images_num"]).reshape(\
                                               self.params_dict["steps_x"],
                                               self.params_dict["steps_y"]),
                "spots_resolution" : numpy.zeros(self.params_dict["images_num"]).reshape(\
                                                 self.params_dict["steps_x"],
                                                 self.params_dict["steps_y"]),
                "score" : numpy.zeros(self.params_dict["images_num"]).reshape(\
                                      self.params_dict["steps_x"],
                                      self.params_dict["steps_y"])}
        else:
              self.results_aligned = \
                {"image_num" : numpy.zeros(self.params_dict["images_num"]),
                 "spots_num" : numpy.zeros(self.params_dict["images_num"]),
                 "spots_int_aver" : numpy.zeros(self.params_dict["images_num"]),
                 "spots_resolution" : numpy.zeros(self.params_dict["images_num"]),
                 "score" : numpy.zeros(self.params_dict["images_num"])}

        self.emit("paralleProcessingResults",
                  (self.results_aligned,
                   self.params_dict,
                   False))

        self.started = True
        self.display_task = gevent.spawn(self.update_map)

    def save_grid_snapshot_task(self, grid_snapshot_filename, data_collection):
        try:
            if data_collection.grid is not None:
                logging.getLogger("HWR").info("Saving grid snapshot: %s..." % \
                    grid_snapshot_filename)
                grid_snapshot = data_collection.grid.get_snapshot()
                grid_snapshot.save(grid_snapshot_filename, 'PNG')
                logging.getLogger("HWR").info("Grid snapshot saved")
            else:
                logging.getLogger("HWR").info("Saving scene snapshot: %s..." % \
                    grid_snapshot_filename)
                self.collect_hwobj._take_crystal_snapshot(grid_snapshot_filename)
                logging.getLogger("HWR").info("Scene snapshot saved")
        except:
            logging.getLogger("GUI").exception(\
                "Could not save grid snapshot: %s" \
                % grid_snapshot_filename)
    
    def is_running(self):
        """Returns True if processing is running"""
        return not self.done_event.is_set()

    def stop_processing(self):
        """Stops processing"""
        self.set_processing_status("Stopped")

    def frame_count_changed(self, frame_count):
        if self.started and \
           frame_count >= self.params_dict["images_num"] - 1:
            self.set_processing_status("Success")

    def batch_processed(self, batch):
        """Method called from EDNA via xmlrpc to set results

        :param batch: list of dictionaries describing processing results
        :type batch: lis
        """
        logging.getLogger("user_level_log").info("Batch arrived %s" % str(self.started))
        if self.started and (type(batch) in (tuple, list)):
            if type(batch[0]) not in (tuple, list):
                batch = [batch]
            for image in batch:
                frame_num = int(image[0])
                self.results_raw["spots_num"][frame_num] = image[1]
                self.results_raw["spots_resolution"][frame_num] = image[3]
                self.results_raw["score"][frame_num] = image[2]

                for score_key in self.results_raw.keys():
                     if self.params_dict["lines_num"] > 1:
                          col, row = self.grid.get_col_row_from_image(frame_num)
                          self.results_aligned[score_key][col][row] = \
                              self.results_raw[score_key][frame_num]
                     else:
                          self.results_aligned[score_key][frame_num] = \
                              self.results_raw[score_key][frame_num]

        """
            self.emit("paralleProcessingResults",
                      (self.results_aligned,
                       self.params_dict,
                       False))
            if self.params_dict["lines_num"] > 1:
                self.grid.set_score(self.results_raw['score'])
        """
 
    def update_map(self):
        while self.started:
            self.emit("paralleProcessingResults",
                      (self.results_aligned,
                       self.params_dict,
                       False))
            if self.params_dict["lines_num"] > 1:
                self.grid.set_score(self.results_raw['score'])
            time.sleep(1) 

    def set_processing_status(self, status):
        """Sets processing status and finalize the processing
           Method called from EDNA via xmlrpc

        :param status: processing status (Success, Failed)
        :type status: str
        """
        gevent.sleep(1)
        self.batch_processed(self.chan_dozor_pass.getValue())

        self.emit("paralleProcessingResults",
                  (self.results_aligned,
                   self.params_dict,
                   True))
        self.data_collection.parallel_processing_result = copy(self.results_aligned)

        self.display_task.kill()

        if self.params_dict["workflow_type"] == "XrayCentering":
            self.store_processing_results(status)
            if self.results_aligned["best_positions"]:
                logging.getLogger("user_level_log").info(\
                       "Xray centering: Moving to the best position")
                self.diffractometer_hwobj.move_motors(\
                     self.results_aligned["best_positions"][0]["cpos"],
                     timeout=15)
            else:
                logging.getLogger("user_level_log").warning(\
                    "Xray Centering: No diffraction found. " + \
                    "Stopping Xray centering")
                status = "Failed" 
            self.done_event.set()
            if status == "Failed":
                self.emit("processingFailed")
            else:
                self.emit("processingFinished")
        else:
            self.done_event.set()
            self.started = False
            if status == "Failed":
                self.emit("processingFailed")
            else:
                self.emit("processingFinished")
            gevent.spawn(self.store_processing_results,
                         status)

    def store_processing_results(self, status):
        log = logging.getLogger("HWR")
        self.params_dict["status"] = status

        # --------------------------------------------------------------------- 
        # 1. Assembling all file names
        self.params_dict["processing_programs"] = "EDNAdozor"
        self.params_dict["processing_end_time"] = \
            time.strftime("%Y-%m-%d %H:%M:%S")
        self.params_dict["max_dozor_score"] = \
            self.results_aligned["score"].max()
        best_positions = self.results_aligned.get("best_positions", [])

        processing_plot_file = os.path.join(self.params_dict\
             ["directory"], "parallel_processing_result.png")
        processing_grid_overlay_file = os.path.join(self.params_dict\
             ["directory"], "grid_overlay.png")
        processing_plot_archive_file = os.path.join(self.params_dict\
             ["processing_archive_directory"], "parallel_processing_result.png")
        processing_csv_archive_file = os.path.join(self.params_dict\
             ["processing_archive_directory"], "parallel_processing_result.csv")

        # We store MeshScan and XrayCentring workflow in ISPyB
        # Parallel processing is also executed for all osc that have
        # more than 20 images, but results are not stored as workflow

        fig, ax = plt.subplots(nrows=1, ncols=1)
        # -----------------------------------------------------------------
        if self.params_dict["workflow_type"] in ("MeshScan", "XrayCentering"):
            # 2. Storing results in ISPyB
            log.info("Processing: Saving processing results in ISPyB")
            self.lims_hwobj.store_autoproc_program(self.params_dict)
            if self.data_collection.workflow_id is not None:
                self.params_dict["workflow_id"] = self.data_collection.workflow_id

            workflow_id, workflow_mesh_id, grid_info_id = \
                 self.lims_hwobj.store_workflow(self.params_dict)

            self.params_dict["workflow_id"] = workflow_id
            self.params_dict["workflow_mesh_id"] = workflow_mesh_id
            self.params_dict["grid_info_id"] = grid_info_id
            self.data_collection.workflow_id = workflow_id

            self.collect_hwobj.update_lims_with_workflow(\
                 workflow_id,
                 self.params_dict["grid_snapshot_filename"])
            #else:
            #    self.params_dict["workflow_id"] = self.data_collection.workflow_id
            self.lims_hwobj.store_workflow_step(self.params_dict)

            #TODO Get collection id from collection object
            self.lims_hwobj.set_image_quality_indicators_plot(\
                 self.collect_hwobj.collection_id,
                 processing_plot_archive_file,
                 processing_csv_archive_file)

            # --------------------------------------------------------------------- 
            # 3. If there are frames with score, then generate map for the best one
            if len(best_positions) > 0:
                self.collect_hwobj.store_image_in_lims_by_frame_num(best_positions[0]["index"])

            try:
                html_filename = os.path.join(self.params_dict["result_file_path"],
                                             "index.html")
                log.info("Processing: Generating results html %s" % html_filename)
                SimpleHTML.generate_mesh_scan_report(\
                    self.results_aligned, self.params_dict,
                    html_filename)
            except:
                log.exception("Processing: Could not create result html %s" % html_filename)

        if self.params_dict["lines_num"] > 1:
            current_max = max(fig.get_size_inches()) 
            grid_width = self.params_dict["steps_x"] * \
                         self.params_dict["xOffset"]
            grid_height = self.params_dict["steps_y"] * \
                          self.params_dict["yOffset"]
 
            if grid_width > grid_height:
                fig.set_size_inches(current_max,
                                    current_max * \
                                    grid_height / \
                                    grid_width)
            else:
                fig.set_size_inches(current_max * \
                                    grid_width / \
                                    grid_height,
                                    current_max)

            # Heat map generation
            # If mesh scan then a 2D plot
            im = ax.imshow(numpy.transpose(self.results_aligned["score"]),
                           interpolation='none',
                           aspect= 'auto',
                           extent=[0, self.results_aligned["score"].shape[0],
                                   0, self.results_aligned["score"].shape[1]])
            im.set_cmap('hot')

            try:
                log.info("Processing: Saving heat map figure for grid overlay %s" % \
                    processing_grid_overlay_file)
                if not os.path.exists(os.path.dirname(processing_grid_overlay_file)):
                    os.makedirs(os.path.dirname(processing_grid_overlay_file))

                #fig.savefig(processing_grid_overlay_file, dpi=150, transparent=True)
               
                plt.imsave(processing_grid_overlay_file,
                           numpy.transpose(self.results_aligned["score"]),
                           format="png",
                           cmap="hot")
                self.grid.set_overlay_pixmap(processing_grid_overlay_file)
            except:
                log.exception("Processing: Could not save figure for ISPyB %s" % \
                   processing_grid_overlay_file)
            
            if len(best_positions) > 0:
                plt.axvline(x=best_positions[0]["col"], linewidth=0.5)
                plt.axhline(y=best_positions[0]["row"], linewidth=0.5)

            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size=0.1, pad=0.05)
            cax.tick_params(axis='x', labelsize=8)
            cax.tick_params(axis='y', labelsize=8)
            plt.colorbar(im, cax=cax)
        else:
            #if helical line then a line plot
            plt.plot(self.results_aligned["score"],
                     label="Total score",
                     color="b",
                     marker="s",
                     linestyle="None")

        ax.tick_params(axis='x', labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        ax.set_title(self.params_dict["title"], fontsize=8)

        ax.grid(True)
        ax.spines['left'].set_position(('outward', 10))
        ax.spines['bottom'].set_position(('outward', 10))

        try:
            log.info("Processing: Saving heat map figure %s..." % \
                processing_plot_file)
            if not os.path.exists(os.path.dirname(processing_plot_file)):
                os.makedirs(os.path.dirname(processing_plot_file))
            fig.savefig(processing_plot_file, dpi=150, bbox_inches='tight')
        except:
            log.exception("Processing: Could not save figure %s" % \
                processing_plot_file)
        try:
            log.info("Processing: Saving heat map figure for ISPyB %s..." % \
                processing_plot_archive_file)
            if not os.path.exists(os.path.dirname(processing_plot_archive_file)):
                os.makedirs(os.path.dirname(processing_plot_archive_file))
            fig.savefig(processing_plot_archive_file, dpi=150, bbox_inches='tight')
        except:
            log.exception("Processing: Could not save figure for ISPyB %s" % \
                processing_plot_archive_file)

        plt.close(fig)

    def align_processing_results(self, start_index):
        """Realigns all results. Each results (one dimensional numpy array)
           is converted to 2d numpy array according to diffractometer geometry.
           Function also extracts 10 (if they exist) best positions
        """
        #Each result array is realigned
        for score_key in self.results_raw.keys():
            if self.params_dict["lines_num"] > 1: 
                col, row = self.grid.get_col_row_from_image_serial(\
                         start_index + self.params_dict["first_image_num"])
                #if (col < self.results_aligned[score_key].shape[0] and
                #    row < self.results_aligned[score_key].shape[1]):
                self.results_aligned[score_key][col][row] = self.results_raw[score_key][start_index]
            else:
                self.results_aligned[score_key] = self.results_raw[score_key]  

    def process_batch(self):
        if self.params_dict["lines_num"] > 1:
            self.grid.set_score(self.results_raw['score'])

        return 
        #Best positions are extracted
        best_positions_list = []

        index_arr = (-self.results_raw["score"]).argsort()[:10]
        if len(index_arr) > 0:
            for index in index_arr:
                if self.results_raw["score"][index] > 0:
                    best_position = {}
                    best_position["index"] = index
                    best_position["index_serial"] = self.params_dict["first_image_num"] + index
                    best_position["score"] = float(self.results_raw["score"][index])
                    best_position["spots_num"] = int(self.results_raw["spots_num"][index])
                    best_position["spots_int_aver"] = float(self.results_raw["spots_int_aver"][index])
                    best_position["spots_resolution"] = float(self.results_raw["spots_resolution"][index])
                    best_position["filename"] = ""
                    #best_position["filename"] = os.path.basename(\
                    #    self.params_dict["template"] % \
                    #    (self.params_dict["run_number"],
                    #     self.params_dict["first_image_num"] + index))

                    cpos = None
                    if num_lines > 1:
                        col, row = self.grid.get_col_row_from_image_serial(\
                             index + self.params_dict["first_image_num"])
                        col += 0.5
                        row = self.params_dict["steps_y"] - row - 0.5
                        cpos = self.grid.get_motor_pos_from_col_row(col, row)
                    else:
                        col = index
                        row = 0
                        #TODO make this nicer
                        num_images = self.data_collection.acquisitions[0].acquisition_parameters.num_images - 1
                        #(point_one, point_two) = self.data_collection.get_centred_positions()
                        #cpos = self.diffractometer_hwobj.get_point_from_line(point_one, point_two, index, num_images)
                    best_position["col"] = col
                    best_position["row"] = row
                    best_position['cpos'] = cpos
                    best_positions_list.append(best_position)

        self.results_aligned["best_positions"] = best_positions_list

    def extract_sweeps(self):
        """Extracts sweeps from processing results"""

        #self.results_aligned
        logging.getLogger("HWR").info("EMBLParallelProcessing: Extracting sweeps")
        for col in range(self.results_aligned["score"].shape[1]):
            mask = self.results_aligned['score'][:, col] > 0
            label_im, nb_labels = ndimage.label(mask)
            #sizes = ndimage.sum(mask, label_im, range(nb_labels + 1))
            labels = numpy.unique(label_im)
            label_im = numpy.searchsorted(labels, label_im)
