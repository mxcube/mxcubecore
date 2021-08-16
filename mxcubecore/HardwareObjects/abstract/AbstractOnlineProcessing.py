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

import os
import time
import logging
import json
import subprocess
import numpy as np

from copy import copy
from scipy import ndimage
from scipy.interpolate import UnivariateSpline
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

import gevent

import SimpleHTML
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR


__license__ = "LGPLv3+"


DEFAULT_RESULT_TYPES = [
    {"key": "spots_resolution", "descr": "Resolution", "color": (120, 0, 0)},
    {"key": "score", "descr": "Score", "color": (0, 120, 0)},
    {"key": "spots_num", "descr": "Number of spots", "color": (0, 0, 120)},
]


"""
AbstractOnlineProcessing hardware object handles online data processing.
Typical example of online processing is a mesh scan where user is provided
with real-time results describing diffraction quality.
Method run_processing is called from the queue_entry when the data collection
starts. Then empty arrays to store results are created.
Typicaly an input file is created and processing is started with script via
subprocess.Popen. Results are emited with paralleProcessingResults signal.

Implementations:
 * DozorOnlinelProcessing: online processing based on the EDNA Dozor plugin.
   Started with EDNA and results are set via xmlrpc.
 * OnlineProcessigMockup: mockup version allows to simulate online processing.
"""


class AbstractOnlineProcessing(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        # Hardware objects ----------------------------------------------------
        self.ssx_setup = None

        # Internal variables --------------------------------------------------
        self.start_command = None
        self.kill_command = None
        self.data_collection = None
        self.grid = None
        self.params_dict = None
        self.result_types = None
        self.results_raw = None
        self.results_aligned = None
        self.interpolate_results = None
        self.done_event = None
        self.started = None
        self.workflow_info = None

        self.current_grid_index = None
        self.grid_properties = []

    def init(self):
        self.done_event = gevent.event.Event()
        self.ssx_setup = self.get_object_by_role("ssx_setup")

        self.result_types = self.get_property("result_types", DEFAULT_RESULT_TYPES)
        self.start_command = str(self.get_property("processing_command"))
        self.kill_command = str(self.get_property("kill_command"))
        self.interpolate_results = self.get_property("interpolate_results")

    def get_result_types(self):
        return self.result_types

    def prepare_processing(self):
        """Prepares processing parameters, creates empty result arrays and
           create necessary directories to store results

        :param data_collection: data collection object
        :type : queue_model_objects.DataCollection
        """
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

        template = os.path.join(
            acquisition.path_template.directory,
            "%s_%%d_%%0%sd.cbf"
            % (
                acquisition.path_template.get_prefix(),
                acquisition.path_template.precision,
            ),
        )
        if acquisition.path_template.compression:
            template += ".gz"

        workflow_step_directory = None
        self.params_dict = {}

        if self.data_collection.run_online_processing == "XrayCentering":
            prefix = "xray_centering_%s" % prefix
            if self.grid:
                workflow_step_directory = "/mesh"
            else:
                workflow_step_directory = "/line"

        if self.workflow_info is not None:
            process_directory = self.workflow_info["process_root_directory"]
            archive_directory = self.workflow_info["archive_root_directory"]
        else:
            i = 1
            while True:
                process_input_file_dirname = "%s_run%s_%d" % (prefix, run_number, i)
                process_directory = os.path.join(
                    acquisition.path_template.process_directory,
                    process_input_file_dirname,
                )
                archive_directory = os.path.join(
                    acquisition.path_template.get_archive_directory(),
                    process_input_file_dirname,
                )
                if not os.path.exists(process_directory):
                    break
                i += 1

        self.params_dict["process_root_directory"] = process_directory
        self.params_dict["archive_root_directory"] = archive_directory
        self.params_dict["result_file_path"] = archive_directory
        self.params_dict["collection_id"] = HWR.beamline.collect.collection_id

        if workflow_step_directory:
            process_directory += workflow_step_directory
            archive_directory += workflow_step_directory

        try:
            if not os.path.isdir(process_directory):
                os.makedirs(process_directory)
        except Exception:
            logging.getLogger("GUI").exception(
                "Online processing: Unable to create processing directory %s"
                % process_directory
            )
            self.set_processing_status("Failed")

        self.params_dict["process_directory"] = process_directory
        self.params_dict["archive_directory"] = archive_directory

        # self.params_dict["plot_path"] = os.path.join(
        # self.params_dict["directory"],
        #    "online_processing_result.png")

        self.params_dict["folder_path"] = archive_directory
        self.params_dict["cartography_path"] = os.path.join(
            archive_directory, "online_processing_plot.png"
        )
        self.params_dict["log_file_path"] = os.path.join(
            archive_directory, "online_processing.log"
        )
        self.params_dict["html_file_path"] = os.path.join(
            archive_directory, "index.html"
        )
        self.params_dict["json_file_path"] = os.path.join(
            archive_directory, "report.json"
        )
        self.params_dict["csv_file_path"] = os.path.join(
            archive_directory, "online_processing.csv"
        )

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
        self.params_dict["hare_num"] = acq_params.hare_num

        if not acq_params.num_images_per_trigger:
            self.params_dict["num_images_per_trigger"] = 1
        else:
            self.params_dict[
                "num_images_per_trigger"
            ] = acq_params.num_images_per_trigger

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
        self.params_dict["workflow_type"] = self.data_collection.run_online_processing

        self.params_dict["group_id"] = self.data_collection.lims_group_id
        self.params_dict["processing_start_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

        if grid_params:
            self.params_dict["dx_mm"] = grid_params["dx_mm"]
            self.params_dict["dy_mm"] = grid_params["dy_mm"]
            self.params_dict["steps_x"] = grid_params["steps_x"]
            self.params_dict["steps_y"] = grid_params["steps_y"]
            self.params_dict["xOffset"] = grid_params["xOffset"]
            self.params_dict["yOffset"] = grid_params["yOffset"]
            self.params_dict["reversing_rotation"] = grid_params["reversing_rotation"]
            # self.store_coordinate_map()
        else:
            self.params_dict["steps_y"] = 1
            self.params_dict["reversing_rotation"] = False

        self.results_raw = {}
        self.results_aligned = {}

        # Empty numpy arrays to store raw and aligned results
        for result_type in self.result_types:
            # images_num =  self.params_dict["images_num"]
            if "size" in result_type:
                images_num = result_type["size"]
            else:
                images_num = self.params_dict["images_num"]

            self.results_raw[result_type["key"]] = np.zeros(images_num)
            self.results_aligned[result_type["key"]] = np.zeros(images_num)

            if self.interpolate_results:
                self.results_aligned["interp_" + result_type] = np.zeros(images_num)
            if (
                self.data_collection.is_mesh()
                and images_num == self.params_dict["images_num"]
            ):
                self.results_aligned[result_type["key"]] = self.results_aligned[
                    result_type["key"]
                ].reshape(self.params_dict["steps_x"], self.params_dict["steps_y"])

        # if not self.data_collection.is_mesh():
        #    self.results_raw["x_array"] = np.linspace(
        #        0, images_num, images_num, dtype=np.int32
        #    )

        try:
            gevent.spawn(
                self.save_snapshot_task, os.path.join(archive_directory, "snapshot.png")
            )
        except Exception:
            logging.getLogger("GUI").exception(
                "Online processing: Could not save snapshot: %s"
                % os.path.join(archive_directory, "snapshot.png")
            )

        self.emit(
            "processingStarted",
            (self.data_collection, self.results_raw, self.results_aligned),
        )

    def create_processing_input_file(self, processing_input_filename):
        """Creates processing input file

        :param processing_input_filename
        :type : str
        """
        return

    def run_processing(self, data_collection):
        """Starts Online processing

        :param: data_collection: data collection obj
        :type: data_collection: queue_model_objects.DataCollection

        """
        self.data_collection = data_collection
        self.prepare_processing()
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
                "OnlineProcessing: Start command %s" % self.start_command
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
                + self.params_dict["process_directory"]
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

    def save_snapshot_task(self, snapshot_filename):
        """Saves snapshot

        :param snapshot_filename: snapshot filename
        :type snapshot_filename: str
        :param data_collection: data collection object
        :type data_collection: queue_model_objects.DataCollection
        """
        try:
            if self.data_collection.grid is not None:
                snapshot = self.data_collection.grid.get_snapshot()
                snapshot.save(snapshot_filename, "PNG")
            else:
                HWR.beamline.collect._take_crystal_snapshot(snapshot_filename)
                logging.getLogger("HWR").info(
                    "Online processing: Snapshot %s saved." % snapshot_filename
                )
        except Exception:
            logging.getLogger("GUI").exception(
                "Online processing: Could not save snapshot %s" % snapshot_filename
            )

    def is_running(self):
        """Returns True if processing is running"""
        return not self.done_event.is_set()

    def stop_processing(self):
        """Stops processing"""
        self.started = False
        self.set_processing_status("Stopped")
        # subprocess.Popen(self.kill_command, shell=True, stdin=None,
        #                 stdout=None, stderr=None, close_fds=True)

    def set_processing_status(self, status):
        """Sets processing status and finalize the processing
           Method called from EDNA via xmlrpc

        :param status: processing status (Success, Failed)
        :type status: str
        """
        self.emit("processingResultsUpdate", True)

        self.data_collection.set_online_processing_results(
            copy(self.results_raw), copy(self.results_aligned)
        )

        if self.params_dict["workflow_type"] == "XrayCentering":
            if self.results_aligned["best_positions"]:
                logging.getLogger("GUI").info(
                    "Xray centering: Moving to the best position"
                )
                HWR.beamline.diffractometer.move_motors(
                    self.results_aligned["center_mass"], timeout=15
                )
                self.store_processing_results(status)
            else:
                logging.getLogger("GUI").warning(
                    "Xray Centering: No diffraction found. " + "Stopping Xray centering"
                )
                status = "Failed"
                self.workflow_info = None
            self.done_event.set()
            if status == "Failed":
                self.emit("processingFailed")
            else:
                self.emit("processingFinished")
        else:
            self.workflow_info = None
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
        # Assembling all file names
        self.params_dict["max_dozor_score"] = self.results_aligned["score"].max()
        best_positions = self.results_aligned.get("best_positions", [])

        processing_grid_overlay_file = os.path.join(
            self.params_dict["archive_directory"], "grid_overlay.png"
        )
        # processing_plot_archive_file = os.path.join(
        #    self.params_dict["archive_directory"], "online_processing_plot.png"
        # )
        processing_csv_archive_file = os.path.join(
            self.params_dict["archive_directory"], "online_processing_score.csv"
        )

        # If MeshScan and XrayCentring then info is stored in ISPyB
        if self.params_dict["workflow_type"] in (
            "MeshScan",
            "XrayCentering",
            "LineScan",
        ):
            if self.workflow_info is not None:
                self.params_dict["workflow_id"] = self.workflow_info["workflow_id"]

            (
                workflow_id,
                workflow_mesh_id,
                grid_info_id,
            ) = HWR.beamline.lims.store_workflow(self.params_dict)

            self.params_dict["workflow_id"] = workflow_id
            self.params_dict["workflow_mesh_id"] = workflow_mesh_id
            self.params_dict["grid_info_id"] = grid_info_id

            if self.params_dict["workflow_type"] == "XrayCentering" and self.grid:
                self.workflow_info = {
                    "workflow_id": self.params_dict["workflow_id"],
                    "process_root_directory": self.params_dict[
                        "process_root_directory"
                    ],
                    "archive_root_directory": self.params_dict[
                        "archive_root_directory"
                    ],
                }
            else:
                self.workflow_info = None

            HWR.beamline.collect.update_lims_with_workflow(
                workflow_id,
                os.path.join(self.params_dict["archive_directory"], "snapshot.png"),
            )

            HWR.beamline.lims.store_workflow_step(self.params_dict)
            if len(best_positions) > 0:
                HWR.beamline.collect.store_image_in_lims_by_frame_num(
                    best_positions[0]["index"]
                )
            log.info("Online processing: Results saved in ISPyB")

        HWR.beamline.lims.set_image_quality_indicators_plot(
            HWR.beamline.collect.collection_id,
            self.params_dict["cartography_path"],
            self.params_dict["csv_file_path"],
        )

        fig, ax = plt.subplots(nrows=1, ncols=1)
        if self.grid:
            current_max = max(fig.get_size_inches())
            grid_width = self.params_dict["steps_x"] * self.params_dict["xOffset"]
            grid_height = self.params_dict["steps_y"] * self.params_dict["yOffset"]

            if grid_width > grid_height:
                fig.set_size_inches(current_max, current_max * grid_height / grid_width)
            else:
                fig.set_size_inches(current_max * grid_width / grid_height, current_max)

            im = ax.imshow(
                np.transpose(self.results_aligned["score"]),
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
                    np.transpose(self.results_aligned["score"]),
                    format="png",
                    cmap="hot",
                )
                self.grid.set_overlay_pixmap(processing_grid_overlay_file)
                log.info(
                    "Online processing: Grid overlay figure saved %s"
                    % processing_grid_overlay_file
                )
            except Exception:
                log.exception(
                    "Online processing: Could not save grid overlay figure %s"
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
            # max_resolution = self.params_dict["resolution"]
            # min_resolution = self.results_aligned["spots_resolution"].max()

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
                fontsize=8,
            )
            ax.set_ylim(-0.01, 1.1)
            ax.set_xlim(0, self.params_dict["images_num"])

            positions = np.linspace(
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
            new_labels = np.linspace(
                0,
                self.results_aligned["spots_num"].max(),
                len(ay1.get_yticklabels()),
                dtype=np.int16,
            )
            ay1.set_yticklabels(new_labels)
            ay1.set_ylabel("Number of spots")

        # ---------------------------------------------------------------------
        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.set_title(self.params_dict["title"], fontsize=8)

        ax.grid(True)
        ax.spines["left"].set_position(("outward", 10))
        ax.spines["bottom"].set_position(("outward", 10))

        # ---------------------------------------------------------------------
        # Stores plot in the processing directory
        try:
            if not os.path.exists(
                os.path.dirname(self.params_dict["cartography_path"])
            ):
                os.makedirs(os.path.dirname(self.params_dict["cartography_path"]))
            fig.savefig(
                self.params_dict["cartography_path"], dpi=100, bbox_inches="tight"
            )
            log.info(
                "Online processing: Plot saved in %s"
                % self.params_dict["cartography_path"]
            )
        except Exception:
            log.exception(
                "Online processing: Could not save plot in %s"
                % self.params_dict["cartography_path"]
            )

        # ---------------------------------------------------------------------
        # Stores plot for ISPyB
        try:
            if not os.path.exists(
                os.path.dirname(self.params_dict["cartography_path"])
            ):
                os.makedirs(os.path.dirname(self.params_dict["cartography_path"]))
            fig.savefig(
                self.params_dict["cartography_path"], dpi=100, bbox_inches="tight"
            )
            log.info(
                "Online processing: Plot for ISPyB saved in %s"
                % self.params_dict["cartography_path"]
            )
        except Exception:
            log.exception(
                "Online processing: Could not save plot for ISPyB %s"
                % self.params_dict["cartography_path"]
            )

        plt.close(fig)

        # ---------------------------------------------------------------------
        # Generates html and json files
        try:
            # SimpleHTML.generate_online_processing_report(
            #    self.results_aligned, self.params_dict
            #)
            log.info(
                "Online processing: Html report saved in %s"
                % self.params_dict["html_file_path"]
            )
            log.info(
                "Online processing: Json report saved in %s"
                % self.params_dict["json_file_path"]
            )
        except Exception:
            log.exception(
                "Online processing: Could not save results html %s"
                % self.params_dict["html_file_path"]
            )
            log.exception(
                "Online processing: Could not save json results in %s"
                % self.params_dict["json_file_path"]
            )

        # ---------------------------------------------------------------------
        # Writes results in the csv file
        try:
            processing_csv_file = open(processing_csv_archive_file, "w")
            processing_csv_file.write(
                "%s,%d,%d,%d,%d,%d,%s,%d,%d,%f,%f,%s\n"
                % (
                    self.params_dict["template"],
                    self.params_dict["first_image_num"],
                    self.params_dict["images_num"],
                    self.params_dict["run_number"],
                    self.params_dict["run_number"],
                    self.params_dict["lines_num"],
                    str(self.params_dict["reversing_rotation"]),
                    HWR.beamline.detector.get_pixel_min(),
                    HWR.beamline.detector.get_pixel_max(),
                    HWR.beamline.beamstop.get_size(),
                    HWR.beamline.beamstop.get_distance(),
                    HWR.beamline.beamstop.get_direction(),
                )
            )
            for index in range(self.params_dict["images_num"]):
                processing_csv_file.write(
                    "%d,%f,%d,%f\n"
                    % (
                        index,
                        self.results_raw["score"][index],
                        self.results_raw["spots_num"][index],
                        self.results_raw["spots_resolution"][index],
                    )
                )
            log.info(
                "Online processing: Raw data stored in %s"
                % processing_csv_archive_file
            )
            processing_csv_file.close()
        except Exception:
            log.error(
                "Online processing: Unable to store raw data in %s"
                % processing_csv_archive_file
            )
        # ---------------------------------------------------------------------

    def align_processing_results(self, start_index, end_index):
        """Realigns all results. Each results (one dimensional numpy array)
           is converted to 2d numpy array according to diffractometer geometry.
           Function also extracts 10 (if they exist) best positions
        """
        # Each result array is realigned

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

        if self.grid:
            self.grid.set_score(self.results_raw["spots_num"])
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

    def extract_sweeps(self):
        """Extracts sweeps from processing results"""

        # self.results_aligned
        logging.getLogger("HWR").info("Online processing: Extracting sweeps")
        for col in range(self.results_aligned["score"].shape[1]):
            mask = self.results_aligned["score"][:, col] > 0
            label_im, nb_labels = ndimage.label(mask)
            # sizes = ndimage.sum(mask, label_im, range(nb_labels + 1))
            labels = np.unique(label_im)
            label_im = np.searchsorted(labels, label_im)

    def store_coordinate_map(self):
        mesh_best_file = os.path.join(
            self.params_dict["process_directory"], "mesh_best.json"
        )

        json_dict = {"meshPositions": []}
        for index, item in enumerate(self.grid.get_coordinate_map()):
            json_dict["meshPositions"].append(
                {"index": index, "indexY": item[0], "indexZ": item[1]}
            )
        with open(mesh_best_file, "w") as fp:
            json.dump(json_dict, fp)

        self.print_log("Online processing: Mesh best file %s saved" % mesh_best_file)
