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
import logging
import gevent
import numpy
import subprocess

from copy import copy
from scipy import ndimage
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

import SimpleHTML
from HardwareRepository.BaseHardwareObjects import HardwareObject


__license__ = "LGPLv3+"


DEFAULT_SCORE_NAME_LIST = ("image_num", "spots_num", "spots_resolution", "score")

"""
GenericParallel processing hardware object handles online data processing.
Typical example of parallel processing is a mesh scan where user is provided
with real-time results describing diffraction quality.
Method run_processing is called from the queue_entry when the data collection
starts. Then empty arrays to store results are created.
Typicaly an input file is created and processing is started with script via
subprocess.Popen. Results are emited with paralleProcessingResults signal.

Implementations:
 * DozorParallelProcessing: parallel processing based on the Dozor. Started 
   with EDNA and results are set via xmlrpc.
 * ParallelProcessigMockup: mockup version capable to display various
   diffraction scenariou: no diffraction, linear, random, etc.
"""


class GenericParallelProcessing(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        # Hardware objects ----------------------------------------------------
        self.collect_hwobj = None
        self.detector_hwobj = None
        self.diffractometer_hwobj = None
        self.beamstop_hwobj = None
        self.lims_hwobj = None

        # Internal variables --------------------------------------------------
        self.start_command = None
        self.kill_command = None
        self.data_collection = None
        self.grid = None
        self.params_dict = None
        self.results_name_list = ()
        self.results_raw = None
        self.results_aligned = None
        self.done_event = None
        self.started = None

        self.max_x_points = 100
        self.plot_points_num = None

    def init(self):
        self.done_event = gevent.event.Event()

        self.collect_hwobj = self.getObjectByRole("collect")
        self.diffractometer_hwobj = self.getObjectByRole("diffractometer")

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

        self.results_name_list = self.getProperty(
            "result_name_list", DEFAULT_SCORE_NAME_LIST
        )
        self.start_command = str(self.getProperty("processing_command"))
        self.kill_command = str(self.getProperty("kill_command"))

    def prepare_processing(self):
        """Prepares processing parameters, creates empty result arrays and 
           create necessary directories to store results

        :param data_collection: data collection object
        :type : queue_model_objects.DataCollection
        """
        # self.data_collection = data_collection
        acquisition = self.data_collection.acquisitions[0]
        acq_params = acquisition.acquisition_parameters
        self.grid = self.data_collection.grid
        grid_params = None
        if self.grid:
            grid_params = self.grid.get_properties()

        prefix = acquisition.path_template.get_prefix()
        run_number = acquisition.path_template.run_number
        first_image_num = acq_params.first_image
        images_num = acq_params.num_images
        last_image_num = first_image_num + images_num - 1
        lines_num = acq_params.num_lines
        process_directory = acquisition.path_template.process_directory
        archive_directory = acquisition.path_template.get_archive_directory()
        template = os.path.join(
            acquisition.path_template.directory,
            "%s_%%d_%%05d.cbf" % acquisition.path_template.get_prefix(),
        )

        # Estimates and creates dozor directory
        i = 1
        while True:
            processing_input_file_dirname = "dozor_%s_run%s_%d" % (
                prefix,
                run_number,
                i,
            )
            processing_directory = os.path.join(
                process_directory, processing_input_file_dirname
            )
            processing_archive_directory = os.path.join(
                archive_directory, processing_input_file_dirname
            )
            if not os.path.exists(processing_directory):
                break
            i += 1

        try:
            if not os.path.isdir(processing_directory):
                os.makedirs(processing_directory)
        except:
            logging.getLogger("GUI").exception(
                "Parallel processing: Unable to create directory %s"
                % processing_directory
            )
            self.set_processing_status("Failed")

        try:
            if not os.path.isdir(processing_archive_directory):
                os.makedirs(processing_archive_directory)
        except:
            logging.getLogger("GUI").exception(
                "Parallel processing: Unable to create archive directory %s"
                % processing_archive_directory
            )
            self.set_processing_status("Failed")

        self.params_dict = {}
        self.params_dict["template"] = template
        self.params_dict["first_image_num"] = first_image_num
        self.params_dict["images_num"] = images_num
        self.params_dict["lines_num"] = lines_num
        self.params_dict["images_per_line"] = images_num / lines_num
        self.params_dict["run_number"] = run_number
        self.params_dict["osc_midle"] = acq_params.osc_start
        self.params_dict["osc_range"] = acq_params.osc_range
        self.params_dict["resolution"] = acq_params.resolution
        self.params_dict["exp_time"] = acq_params.exp_time

        self.params_dict["status"] = "Started"
        self.params_dict["title"] = "%s_%d_#####.cbf (%d - %d)" % (
            prefix,
            run_number,
            first_image_num,
            last_image_num,
        )
        self.params_dict["comments"] = "Scan lines: %d, frames per line: %d" % (
            lines_num,
            images_num / lines_num,
        )
        self.params_dict["workflow_type"] = self.data_collection.run_processing_parallel
        self.params_dict["directory"] = processing_directory
        self.params_dict["processing_archive_directory"] = processing_archive_directory
        self.params_dict["result_file_path"] = self.params_dict[
            "processing_archive_directory"
        ]
        self.params_dict["plot_path"] = os.path.join(
            self.params_dict["directory"], "parallel_processing_result.png"
        )
        self.params_dict["cartography_path"] = os.path.join(
            self.params_dict["processing_archive_directory"],
            "parallel_processing_result.png",
        )
        self.params_dict["log_file_path"] = os.path.join(
            self.params_dict["processing_archive_directory"], "dozor_log.log"
        )
        self.params_dict["group_id"] = self.data_collection.lims_group_id
        self.params_dict["processing_start_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

        if lines_num > 1 and grid_params:
            self.params_dict["dx_mm"] = grid_params["dx_mm"]
            self.params_dict["dy_mm"] = grid_params["dy_mm"]
            self.params_dict["steps_x"] = grid_params["steps_x"]
            self.params_dict["steps_y"] = grid_params["steps_y"]
            self.params_dict["xOffset"] = grid_params["xOffset"]
            self.params_dict["yOffset"] = grid_params["yOffset"]
            self.params_dict["reversing_rotation"] = grid_params["reversing_rotation"]
        else:
            self.params_dict["steps_y"] = 1
            self.params_dict["reversing_rotation"] = False

        self.results_raw = {}
        self.results_aligned = {}

        # Empty numpy arrays to store raw and aligned results
        if self.data_collection.is_mesh():
            self.plot_points_num = images_num
        else:
            self.plot_points_num = min(self.max_x_points, images_num)

        for result_name in self.results_name_list:
            self.results_raw[result_name] = numpy.zeros(images_num)
            self.results_aligned[result_name] = numpy.zeros(self.plot_points_num)
            # self.results_aligned['image_number']=numpy.linspace(0,images_num,images_num)
            if self.data_collection.is_mesh():
                self.results_aligned[result_name] = self.results_aligned[
                    result_name
                ].reshape(self.params_dict["steps_x"], self.params_dict["steps_y"])
            else:
                self.results_aligned["x_array"] = numpy.linspace(
                    0, images_num, self.plot_points_num, dtype=numpy.int16
                )

        try:
            if self.data_collection.grid is not None:
                grid_snapshot_filename = os.path.join(
                    processing_archive_directory, "grid_snapshot.png"
                )
                self.params_dict["grid_snapshot_filename"] = grid_snapshot_filename

                gevent.spawn(self.save_grid_snapshot_task, grid_snapshot_filename)
        except:
            logging.getLogger("GUI").exception(
                "Parallel processing: Could not save grid snapshot: %s"
                % grid_snapshot_filename
            )

    def create_processing_input_file(self, processing_input_filename):
        """Creates processing input file

        :param processing_input_filename
        :type : str
        """
        return

    def run_processing(self, data_collection):
        """Starts parallel processing

        :param: data_collection: data collection obj
        :type: data_collection: queue_model_objects.DataCollection

        """
        self.data_collection = data_collection
        self.prepare_processing()
        input_filename = os.path.join(self.params_dict["directory"], "dozor_input.xml")
        self.create_processing_input_file(input_filename)

        self.emit(
            "paralleProcessingResults", (self.results_aligned, self.params_dict, False)
        )

        if not os.path.isfile(self.start_command):
            msg = (
                "ParallelProcessing: Start command %s" % self.start_command
                + "is not executable"
            )
            logging.getLogger("queue_exec").error(msg)
            self.set_processing_status("Failed")
        else:
            line_to_execute = (
                self.start_command
                + " "
                + input_filename
                + " "
                + self.params_dict["directory"]
            )

            self.started = True
            subprocess.Popen(
                str(line_to_execute),
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                close_fds=True,
            )

    def save_grid_snapshot_task(self, grid_snapshot_filename):
        """Saves grid snapshot

        :param grid_snapshot_filename: snapshot filename
        :type grid_snapshot_filename: str
        :param data_collection: data collection object
        :type data_collection: queue_model_objects.DataCollection
        """
        try:
            if self.data_collection.grid is not None:
                grid_snapshot = self.data_collection.grid.get_snapshot()
                grid_snapshot.save(grid_snapshot_filename, "PNG")
            else:
                self.collect_hwobj._take_crystal_snapshot(grid_snapshot_filename)
                logging.getLogger("HWR").info(
                    "Parallel processing: Grid snapshot %s saved."
                    % grid_snapshot_filename
                )
        except:
            logging.getLogger("GUI").exception(
                "Parallel processing: Could not save grid snapshot %s"
                % grid_snapshot_filename
            )

    def is_running(self):
        """Returns True if processing is running"""
        return not self.done_event.is_set()

    def stop_processing(self):
        """Stops processing"""
        self.set_processing_status("Stopped")
        # subprocess.Popen(self.kill_command, shell=True, stdin=None,
        #                 stdout=None, stderr=None, close_fds=True)

    def set_processing_status(self, status):
        """Sets processing status and finalize the processing
           Method called from EDNA via xmlrpc

        :param status: processing status (Success, Failed)
        :type status: str
        """
        self.emit(
            "paralleProcessingResults", (self.results_aligned, self.params_dict, True)
        )

        self.data_collection.parallel_processing_result = copy(self.results_aligned)

        if self.params_dict["workflow_type"] == "XrayCentering":
            self.store_processing_results(status)
            if self.results_aligned["best_positions"]:
                logging.getLogger("GUI").info(
                    "Xray centering: Moving to the best position"
                )
                self.diffractometer_hwobj.move_motors(
                    self.results_aligned["best_positions"][0]["cpos"], timeout=15
                )
            else:
                logging.getLogger("GUI").warning(
                    "Xray Centering: No diffraction found. " + "Stopping Xray centering"
                )
                status = "Failed"
            self.done_event.set()
            if status == "Failed":
                self.emit("processingFailed")
            else:
                self.emit("processingFinished")
        else:
            if status == "Failed":
                self.emit("processingFailed")
            else:
                self.emit("processingFinished")

            self.done_event.set()
            self.store_processing_results(status)

    def store_processing_results(self, status):
        """Stores result plots. In the case of MeshScan and XrayCentering
           html is created and results saved in ISPyB
      
        :param status: status type
        :type status: str
        """
        log = logging.getLogger("HWR")

        self.started = False
        self.params_dict["status"] = status

        # ---------------------------------------------------------------------
        # 1. Assembling all file names
        self.params_dict["processing_programs"] = "EDNAdozor"
        self.params_dict["processing_end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.params_dict["max_dozor_score"] = self.results_aligned["score"].max()
        best_positions = self.results_aligned.get("best_positions", [])

        processing_plot_file = os.path.join(
            self.params_dict["directory"], "parallel_processing_result.png"
        )
        processing_grid_overlay_file = os.path.join(
            self.params_dict["directory"], "grid_overlay.png"
        )
        processing_plot_archive_file = os.path.join(
            self.params_dict["processing_archive_directory"],
            "parallel_processing_result.png",
        )
        processing_csv_archive_file = os.path.join(
            self.params_dict["processing_archive_directory"],
            "parallel_processing_result.csv",
        )

        # If MeshScan and XrayCentring then info is stored in ISPyB
        if self.params_dict["workflow_type"] in ("MeshScan", "XrayCentering"):
            log.info("Parallel processing: Saving results in ISPyB...")
            self.lims_hwobj.store_autoproc_program(self.params_dict)
            if self.data_collection.workflow_id is not None:
                self.params_dict["workflow_id"] = self.data_collection.workflow_id

            workflow_id, workflow_mesh_id, grid_info_id = self.lims_hwobj.store_workflow(
                self.params_dict
            )

            self.params_dict["workflow_id"] = workflow_id
            self.params_dict["workflow_mesh_id"] = workflow_mesh_id
            self.params_dict["grid_info_id"] = grid_info_id
            self.data_collection.workflow_id = workflow_id

            self.collect_hwobj.update_lims_with_workflow(
                workflow_id, self.params_dict["grid_snapshot_filename"]
            )
            self.lims_hwobj.store_workflow_step(self.params_dict)

            # self.lims_hwobj.set_image_quality_indicators_plot(
            #     self.collect_hwobj.collection_id,
            #     processing_plot_archive_file,
            #     processing_csv_archive_file)

            if len(best_positions) > 0:
                self.collect_hwobj.store_image_in_lims_by_frame_num(
                    best_positions[0]["index"]
                )
            log.info("Parallel processing: Results saved in ISPyB")

            try:
                html_filename = os.path.join(
                    self.params_dict["result_file_path"], "index.html"
                )
                SimpleHTML.generate_mesh_scan_report(
                    self.results_aligned, self.params_dict, html_filename
                )
                log.info("Parallel processing: Results html saved %s" % html_filename)
            except:
                log.exception(
                    "Parallel processing: Could not save results html %s"
                    % html_filename
                )

        fig, ax = plt.subplots(nrows=1, ncols=1)
        if self.params_dict["lines_num"] > 1:
            current_max = max(fig.get_size_inches())
            grid_width = self.params_dict["steps_x"] * self.params_dict["xOffset"]
            grid_height = self.params_dict["steps_y"] * self.params_dict["yOffset"]

            if grid_width > grid_height:
                fig.set_size_inches(current_max, current_max * grid_height / grid_width)
            else:
                fig.set_size_inches(current_max * grid_width / grid_height, current_max)

            im = ax.imshow(
                numpy.transpose(self.results_aligned["score"]),
                interpolation="none",
                aspect="auto",
                extent=[
                    0,
                    self.results_aligned["score"].shape[0],
                    0,
                    self.results_aligned["score"].shape[1],
                ],
            )
            im.set_cmap("hot")

            try:
                if not os.path.exists(os.path.dirname(processing_grid_overlay_file)):
                    os.makedirs(os.path.dirname(processing_grid_overlay_file))

                plt.imsave(
                    processing_grid_overlay_file,
                    numpy.transpose(self.results_aligned["score"]),
                    format="png",
                    cmap="hot",
                )
                self.grid.set_overlay_pixmap(processing_grid_overlay_file)
                log.info(
                    "Parallel processing: Grid overlay figure saved %s"
                    % processing_grid_overlay_file
                )
            except:
                log.exception(
                    "Parallel processing: Could not save grid overlay figure %s"
                    % processing_grid_overlay_file
                )

            if len(best_positions) > 0:
                plt.axvline(x=best_positions[0]["col"], linewidth=0.5)
                plt.axhline(y=best_positions[0]["row"], linewidth=0.5)

                divider = make_axes_locatable(ax)
                cax = divider.append_axes("right", size=0.1, pad=0.05)
                cax.tick_params(axis="x", labelsize=8)
                cax.tick_params(axis="y", labelsize=8)
                plt.colorbar(im, cax=cax)
        else:
            max_resolution = self.params_dict["resolution"]
            min_resolution = self.results_aligned["spots_resolution"].max()

            # TODO plot results based on the result_name_list
            max_score = self.results_aligned["score"].max()
            if max_score == 0:
                max_score = 1
            max_spots_num = self.results_aligned["spots_num"].max()
            if max_spots_num == 0:
                max_spots_num = 1

            plt.plot(
                self.results_aligned["score"] / max_score, ".", label="Score", c="r"
            )
            plt.plot(
                self.results_aligned["spots_num"] / max_spots_num,
                ".",
                label="Number of spots",
                c="b",
            )
            plt.plot(
                self.results_aligned["spots_resolution"], ".", label="Resolution", c="y"
            )

            ax.legend(
                loc="lower center",
                fancybox=True,
                numpoints=1,
                borderaxespad=0.0,
                bbox_to_anchor=(0.5, -0.13),
                ncol=3,
            )
            ax.set_ylim(-0.01, 1.1)

            positions = numpy.linspace(
                0, self.results_aligned["spots_resolution"].max(), 5
            )
            labels = ["inf"]
            for item in positions[1:]:
                labels.append("%.2f" % (1.0 / item))
            ax.set_yticks(positions)
            ax.set_yticklabels(labels)

            # new_labels = numpy.linspace(min_resolution, max_resolution / 1.2, len(ax.get_yticklabels()))
            # new_labels = numpy.round(new_labels, 1)
            # ax.set_yticklabels(new_labels)
            ax.set_ylabel("Resolution")

            ay1 = ax.twinx()
            new_labels = numpy.linspace(
                0,
                self.results_aligned["spots_num"].max(),
                len(ay1.get_yticklabels()),
                dtype=numpy.int16,
            )
            ay1.set_yticklabels(new_labels)
            ay1.set_ylabel("Number of spots")

        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.set_title(self.params_dict["title"], fontsize=8)

        ax.grid(True)
        ax.spines["left"].set_position(("outward", 10))
        ax.spines["bottom"].set_position(("outward", 10))

        self.lims_hwobj.set_image_quality_indicators_plot(
            self.collect_hwobj.collection_id,
            processing_plot_archive_file,
            processing_csv_archive_file,
        )

        try:
            if not os.path.exists(os.path.dirname(processing_plot_file)):
                os.makedirs(os.path.dirname(processing_plot_file))
            fig.savefig(processing_plot_file, dpi=150, bbox_inches="tight")
            log.info(
                "Parallel processing: Heat map figure %s saved" % processing_plot_file
            )
        except:
            log.exception(
                "Parallel processing: Could not save figure %s" % processing_plot_file
            )
        try:
            if not os.path.exists(os.path.dirname(processing_plot_archive_file)):
                os.makedirs(os.path.dirname(processing_plot_archive_file))
            fig.savefig(processing_plot_archive_file, dpi=150, bbox_inches="tight")
            log.info(
                "Parallel processing: Archive heat map figure %s saved"
                % processing_plot_archive_file
            )
        except:
            log.exception(
                "Parallel processing: Could not save archive figure %s"
                % processing_plot_archive_file
            )

        plt.close(fig)

        # Writes results in the csv file
        """
        try:
            processing_csv_file = open(processing_csv_filename, "w")
            processing_csv_file.write("%s,%d,%d,%d,%d,%d,%s,%d,%d,%f,%f,%s\n" %(\
                                      self.params_dict["template"],
                                      self.params_dict["first_image_num"],
                                      self.params_dict["images_num"],
                                      self.params_dict["run_number"],
                                      self.params_dict["run_number"],
                                      self.params_dict["lines_num"],
                                      str(self.params_dict["reversing_rotation"]),
                                      self.detector_hwobj.get_pixel_min(),
                                      self.detector_hwobj.get_pixel_max(),
                                      self.beamstop_hwobj.get_size(),
                                      self.beamstop_hwobj.get_distance(),
                                      self.beamstop_hwobj.get_direction()))
            for index in range(self.params_dict["images_num"]):
                processing_csv_file.write("%d,%f,%d,%f\n" % (\
                                          index, 
                                          self.results_raw["score"][index],
                                          self.results_raw["spots_num"][index],
                                          self.results_raw["spots_resolution"][index]))
            log.info("Parallel processing: Raw data stored in %s" % \
                     processing_csv_filename)
        except:
            log.error("Parallel processing: Unable to store raw data in %s" % \
                      processing_csv_filename) 
        finally:
            processing_csv_file.close()
        """

    def align_processing_results(self, start_index, end_index):
        """Realigns all results. Each results (one dimensional numpy array)
           is converted to 2d numpy array according to diffractometer geometry.
           Function also extracts 10 (if they exist) best positions
        """
        # Each result array is realigned
        for score_key in self.results_raw.keys():
            if self.params_dict["lines_num"] > 1:
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
                self.results_aligned[score_key] = self.results_raw[score_key][
                    :: self.params_dict["images_num"] / self.plot_points_num
                ]

        if self.params_dict["lines_num"] > 1:
            self.grid.set_score(self.results_raw["score"])

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
                    if self.params_dict["lines_num"] > 1:
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
                        # cpos = self.diffractometer_hwobj.get_point_from_line(point_one, point_two, index, num_images)
                    best_position["col"] = col
                    best_position["row"] = row
                    best_position["cpos"] = cpos
                    best_positions_list.append(best_position)

        self.results_aligned["best_positions"] = best_positions_list

    def extract_sweeps(self):
        """Extracts sweeps from processing results"""

        # self.results_aligned
        logging.getLogger("HWR").info("ParallelProcessing: Extracting sweeps")
        for col in range(self.results_aligned["score"].shape[1]):
            mask = self.results_aligned["score"][:, col] > 0
            label_im, nb_labels = ndimage.label(mask)
            # sizes = ndimage.sum(mask, label_im, range(nb_labels + 1))
            labels = numpy.unique(label_im)
            label_im = numpy.searchsorted(labels, label_im)
