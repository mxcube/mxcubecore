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
EMBLOnlineProcessing
"""

import os
import ast
import logging
import subprocess

import numpy as np
import gevent

from HardwareRepository.HardwareObjects.abstract.AbstractOnlineProcessing import (
    AbstractOnlineProcessing,
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


from HardwareRepository import HardwareRepository as HWR

__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"


CRYSTFEL_GEOM_FILE_TEMPLATE = """clen = {:.5f}
photon_energy = {:.1f}

adu_per_photon = 1
res = {:.1f}

panel0/min_fs = 0
panel0/min_ss = 0
panel0/max_fs = {:.0f}
panel0/max_ss = {:.0f}
panel0/corner_x = {:.2f}
panel0/corner_y = {:.2f}
panel0/fs = x
panel0/ss = y
"""

CRYSTFEL_CELL_FILE_TEMPLATE = """CrystFEL unit cell file version 1.0

lattice_type = {:s}
centering = {:s}
{:s}

a = {:.2f} A
b = {:.2f} A
c = {:.2f} A
al = {:.2f} deg
be = {:.2f} deg
ga = {:.2f} deg
"""

CONST_H = 4.135667516e-15  # eV*s
CONST_C = 299792458.0


class EMBLOnlineProcessing(AbstractOnlineProcessing):
    """
    Obtains Dozor on the fly processing results
    Assembles crystfel input files and starts crystfel
    """

    def __init__(self, name):
        AbstractOnlineProcessing.__init__(self, name)

        self.display_task = None
        self.nxds_input_template = None

        self.crystfel_script = ""
        self.crystfel_script_template = None
        self.crystfel_params = None

        self.chan_dozor_pass = None
        self.chan_dozor_average_i = None
        self.chan_frame_count = None

        self.result_types = []

    def init(self):
        self.chan_dozor_average_i = self.get_channel_object("chanDozorAverageI")
        if self.chan_dozor_average_i is not None:
            key = "average_intensity"
            self.result_types.append(
                {"key": key, "descr": "Average I", "color": (255, 0, 0), "size": 0}
            )
            self.chan_dozor_average_i.connect_signal(
                "update", self.dozor_average_i_changed
            )

        AbstractOnlineProcessing.init(self)

        self.chan_dozor_pass = self.get_channel_object("chanDozorPass")
        if self.chan_dozor_pass is not None:
            self.chan_dozor_pass.connect_signal("update", self.batch_processed)

        self.chan_frame_count = self.get_channel_object("chanFrameCount")
        if self.chan_frame_count is not None:
            self.chan_frame_count.connect_signal("update", self.frame_count_changed)

        self.crystfel_script = self.get_property("crystfel_script")

        if self.get_property("nxds_input_template_file") is not None:
            with open(
                self.get_property("nxds_input_template_file"), "r"
            ) as template_file:
                self.nxds_input_template = "".join(template_file.readlines())

        if self.get_property("crystfel_script_template_file") is not None:
            with open(
                self.get_property("crystfel_script_template_file"), "r"
            ) as template_file:
                self.crystfel_script_template = "".join(template_file.readlines())

        if self.get_property("crystfel_params") is not None:
            self.crystfel_params = ast.literal_eval(self.get_property("crystfel_params"))

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
        input_file.setPixelMin(XSDataInteger(HWR.beamline.detector.get_pixel_min()))
        input_file.setPixelMax(XSDataInteger(HWR.beamline.detector.get_pixel_max()))
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

        input_filename = os.path.join(
            self.params_dict["process_directory"], "dozor_input.xml"
        )
        self.create_processing_input_file(input_filename)

        self.emit(
            "processingStarted",
            (self.params_dict, self.results_raw, self.results_aligned),
        )
        self.emit("processingResultsUpdate", False)

        all_file_filename = self.create_all_file_list()
        self.start_crystfel_autoproc(all_file_filename)

        self.started = True
        self.display_task = gevent.spawn(self.update_map)

        if self.chan_dozor_pass is None:
            # Start dozor via EDNA
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
        step = 30
        for key in ["score", "spots_num"]:
            for index in range(self.results_raw[key].size):
                self.results_raw[key][index] = numpy.mean(
                    self.results_raw[key][index - step : index + step]
                )

    def batch_processed(self, batch):
        """Method called from EDNA via xmlrpc to set results

        :param batch: list of dictionaries describing processing results
        :type batch: lis
        """
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
                        if frame_num < self.results_aligned[score_key].size:
                            self.results_aligned[score_key][
                                frame_num
                            ] = self.results_raw[score_key][frame_num]
            # if self.params_dict["lines_num"] <= 1:
            #    self.smooth()

    def dozor_average_i_changed(self, average_i_value):
        if self.started:
            self.results_raw["average_intensity"] = np.append(
                self.results_raw["average_intensity"], average_i_value
            )
            self.results_aligned["average_intensity"] = np.append(
                self.results_aligned["average_intensity"], average_i_value
            )

    def update_map(self):
        return
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
        # if self.params_dict["lines_num"] <= 1:
        #    self.smooth()
        GenericOnlineProcessing.set_processing_status(self, status)

    def store_processing_results(self, status):
        """
        Stors processing results
        :param status: str
        :return:
        """
        GenericOnlineProcessing.store_processing_results(self, status)
        self.display_task.kill()
        gevent.spawn(self.create_hit_list_files)

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
            "Online processing: Results saved in %s" % processing_xml_filename
        )

    def create_all_file_list(self):
        all_file_filename = os.path.join(
            self.params_dict["process_directory"], "images_fullpath.lst"
        )
        try:
            lst_file = open(all_file_filename, "w")
            for index in range(self.params_dict["images_num"]):
                lst_file.write(
                    self.params_dict["template"]
                    % (self.params_dict["run_number"], index + 1)
                    + "\n"
                )
            self.print_log(
                "HWR",
                "debug",
                "Online processing: All image list stored in %s" % all_file_filename,
            )
        except BaseException:
            self.print_log(
                "GUI",
                "error",
                "Online processing: Unable to store all image list in %s"
                % all_file_filename,
            )
        finally:
            lst_file.close()
        return all_file_filename

    def create_hit_list_files(self):
        """
        :return:
        """
        lst_filename = os.path.join(
            self.params_dict["process_directory"], "images_dozor_hits_fullpath.lst"
        )
        nxds_filename = os.path.join(
            self.params_dict["process_directory"], "images_dozor_hits_nopath.lst"
        )

        dozor_resolution_filename = os.path.join(
            self.params_dict["process_directory"], "dozor_resolution.lst"
        )

        num_dozor_hits = 0

        try:
            lst_file = open(lst_filename, "w")
            nxds_lst_file = open(nxds_filename, "w")
            dozor_resolution_file = open(dozor_resolution_filename, "w")

            for index in range(self.params_dict["images_num"]):
                if self.results_raw["score"][index] > 0:
                    filename = self.params_dict["template"] % (
                        self.params_dict["run_number"],
                        index + 1,
                    )
                    lst_file.write(filename + "\n")
                    nxds_lst_file.write(os.path.basename(filename) + "\n")

                    dozor_resolution_file.write(
                        "%s %s\n"
                        % (filename, self.results_raw["spots_resolution"][index])
                    )

                    num_dozor_hits = num_dozor_hits + 1
            self.print_log(
                "GUI",
                "info",
                "Online processing: Hit list for crystfel stored in %s" % lst_filename,
            )
            self.print_log(
                "GUI",
                "info",
                "Online processing: Hit list for nxds stored in %s" % nxds_filename,
            )
            self.print_log(
                "GUI",
                "info",
                "Online processing: DOZOR resolutions stored in %s"
                % dozor_resolution_filename,
            )

        except BaseException:
            self.print_log(
                "GUI",
                "error",
                "Online processing: Unable to store hit list in %s" % lst_filename,
            )

        finally:
            lst_file.close()
            nxds_lst_file.close()
            dozor_resolution_file.close()

        msg = (
            "Online processing: found %d dozor hits in %d collected images (%.2f%%)"
            % (
                num_dozor_hits,
                self.params_dict["images_num"],
                (100.0 * num_dozor_hits / self.params_dict["images_num"]),
            )
        )
        self.print_log("GUI", "info", msg)

    def start_crystfel_autoproc(self, all_file_filename):
        """
        Start crystfel processing
        :return:
        """
        acq_params = self.data_collection.acquisitions[0].acquisition_parameters
        proc_params = self.data_collection.processing_parameters

        sample_basename = self.params_dict["template"].split("/")[-1].split("_%d_%0")[0]
        stream_filename = sample_basename + "_crystfel_xgandalf.stream"

        # stream_filename   = "crystfel_xgandalf.stream"
        geom_filename = "crystfel_detector.geom"
        cell_filename = "crystfel_cell.cell"
        cell_filename_pdb = "crystfel_cell.pdb"
        crystfel_autoproc = os.path.join(
            self.params_dict["process_directory"], "crystfel_autoproc.sh"
        )
        log_filename = "crystfel_xgandalf.log"
        nxdsinp_filename = os.path.join(
            self.params_dict["process_directory"], "nXDS.INP"
        )
        procdir_cluster = self.params_dict["process_directory"].replace(
            "/data/users/", "/home/"
        )

        beam_x, beam_y = HWR.beamline.detector.get_beam_centre()
        pixel_size_mm_x, pixel_size_mm_y = HWR.beamline.detector.get_pixel_size_mm()

        self.print_log(
            "HWR",
            "debug",
            "detector:          " + str(HWR.beamline.detector.get_property("type")),
        )
        self.print_log(
            "HWR", "debug", "resolution cutoff: " + str(proc_params.resolution_cutoff)
        )
        self.print_log(
            "HWR", "debug", "space group:       " + str(proc_params.space_group)
        )
        self.print_log(
            "HWR", "debug", "PDB file:          " + str(proc_params.pdb_file)
        )
        self.print_log(
            "HWR",
            "debug",
            "unit cell:         "
            + str(proc_params.cell_a)
            + ", "
            + str(proc_params.cell_b)
            + ", "
            + str(proc_params.cell_c),
        )

        # Eiger 4M:
        detector_size_x = 2070
        detector_size_y = 2167
        # Pilatus 2M:
        # detector_size_x = 1475
        # detector_size_y = 1679

        geom_file = CRYSTFEL_GEOM_FILE_TEMPLATE.format(
            HWR.beamline.detector.distance.get_value() / 1000.0,
            acq_params.energy * 1000,
            1000.0 / pixel_size_mm_x,
            detector_size_x - 1,
            detector_size_y - 1,
            -beam_x / pixel_size_mm_x,
            -beam_y / pixel_size_mm_y,
        )

        data_file = open(
            os.path.join(self.params_dict["process_directory"], geom_filename), "w"
        )
        data_file.write(geom_file)
        data_file.close()

        if "P212121" in proc_params.space_group:
            lattice_type = "orthorhombic"
            point_group = "mmm"
            space_group = "P212121"
            centering = "P"
            unique_axis = ""
            space_group_number = 19
            run_mr = "false"
        elif "P21212" in proc_params.space_group:
            lattice_type = "orthorhombic"
            point_group = "mmm"
            space_group = "P21212"
            centering = "P"
            unique_axis = ""
            space_group_number = 18
            run_mr = "false"
        elif "I222" in proc_params.space_group:
            lattice_type = "orthorhombic"
            point_group = "mmm"
            space_group = "I222"
            centering = "I"
            unique_axis = ""
            space_group_number = 23
            run_mr = "true"
        elif "P43212" in proc_params.space_group:
            lattice_type = "tetragonal"
            point_group = "4/mmm"
            space_group = "P43212"
            centering = "P"
            unique_axis = "unique_axis = c"
            space_group_number = 96
            run_mr = "false"
        elif "P213" in proc_params.space_group:
            lattice_type = "cubic"
            point_group = "m-3"
            space_group = "P213"
            centering = "P"
            unique_axis = ""
            space_group_number = 198
            run_mr = "true"
        elif "P3221" in proc_params.space_group:
            lattice_type = "trigonal"
            point_group = "3m1_H"
            space_group = "P3221"
            centering = "P"
            unique_axis = "unique_axis = c"
            space_group_number = 154
            run_mr = "true"
        else:
            lattice_type = "triclinic"
            point_group = "1"
            space_group = "P1"
            centering = "P"
            unique_axis = ""
            space_group_number = 1
            run_mr = "true"

        """
        lattice_types = ("triclinic",
                         "monoclinic",
                         "orthorhombic",
                         "tetragonal",
                         "trigonal",
                         "hexagonal",
                         "cubic")
        """

        cell_a = proc_params.cell_a
        cell_b = proc_params.cell_b
        cell_c = proc_params.cell_c
        cell_alpha = proc_params.cell_alpha
        cell_beta = proc_params.cell_beta
        cell_gamma = proc_params.cell_gamma

        # cell_a     = 94.4
        # cell_b     = 98.9
        # cell_c     = 86.9
        # cell_alpha = 90.0
        # cell_beta  = 90.0
        # cell_gamma = 90.0

        cell_file = CRYSTFEL_CELL_FILE_TEMPLATE.format(
            lattice_type,
            centering,
            unique_axis,
            cell_a,
            cell_b,
            cell_c,
            cell_alpha,
            cell_beta,
            cell_gamma,
        )

        data_file = open(
            os.path.join(self.params_dict["process_directory"], cell_filename), "w"
        )
        data_file.write(cell_file)
        data_file.close()

        wavelength = 1e10 * CONST_H * CONST_C / (acq_params.energy * 1000)

        nxds_file = self.nxds_input_template.format(
            image_template=self.params_dict["template"],
            image_directory=os.path.dirname(self.params_dict["template"]),
            image_list="nxds_dozor_hits.lst",
            space_group_number=int(space_group_number),
            cell_a=cell_a,
            cell_b=cell_b,
            cell_c=cell_c,
            cell_alpha=cell_alpha,
            cell_beta=cell_beta,
            cell_gamma=cell_gamma,
            wavelength=wavelength,
            pixel_size_mm_x=pixel_size_mm_x,
            pixel_size_mm_y=pixel_size_mm_y,
            detector_size_x=detector_size_x,
            detector_size_y=detector_size_y,
            org_x=beam_x / pixel_size_mm_x,
            org_y=beam_y / pixel_size_mm_y,
            detector_distance=HWR.beamline.detector.distance.get_value(),
        )

        data_file = open(nxdsinp_filename, "w")
        data_file.write(nxds_file)
        data_file.close()

        # point_group = "422"
        # point_group = "6"
        # point_group = "mmm"

        end_of_line_to_execute = " %s %s %s %s %s %s %s %.2f" % (
            self.params_dict["process_directory"],
            all_file_filename,
            geom_filename,
            stream_filename,
            cell_filename,
            self.crystfel_params["point_group"],
            proc_params.space_group,
            acq_params.resolution,
        )

        self.print_log(
            "HWR",
            "debug",
            "Online processing: Starting crystfel %s with parameters %s "
            % (self.crystfel_script, end_of_line_to_execute),
        )

        crystfel_command = (
            "ssh bcrunch 'cd %s; bash crystfel_autoproc.sh'" % procdir_cluster
        )

        crystfel_script = self.crystfel_script_template.format(
            num_cores_crystfel=self.crystfel_params["num_cores_crystfel"],
            procdir_cluster=procdir_cluster,
            geom_filename=geom_filename,
            stream_filename=stream_filename,
            cell_filename=cell_filename,
            # num_cores_crystfel=self.crystfel_params["num_cores_crystfel"],
            # procdir_cluster=procdir_cluster,
            log_filename=log_filename,
            num_cores_partialator=self.crystfel_params["num_cores_partialator"],
            # procdir_cluster,
            # stream_filename,
            # cell_filename,
            pdb_file=proc_params.pdb_file,
            # proc_params.pdb_file,
            num_cores_fspipeline=self.crystfel_params["num_cores_fspipeline"],
            # procdir_cluster,
            pdb_file_end=str(proc_params.pdb_file).split("/")[-1],
            resolution="{:.1f}".format(proc_params.resolution_cutoff),
            hare_number=self.params_dict["hare_num"],
            burst_number=self.params_dict["num_images_per_trigger"],
            pointgroup=point_group,
            spacegroup=space_group,
            run_mr=run_mr,
        )

        data_file = open(crystfel_autoproc, "w")
        data_file.write(crystfel_script)
        data_file.close()

        self.print_log(
            "HWR",
            "debug",
            "Online processing: crystfel command: \n %s" % (crystfel_command),
        )

        subprocess.Popen(
            crystfel_command,
            shell=True,
            stdin=None,
            stdout=None,
            stderr=None,
            close_fds=True,
        )
