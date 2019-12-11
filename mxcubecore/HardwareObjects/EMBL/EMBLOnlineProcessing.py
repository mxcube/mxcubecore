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
import logging
import subprocess

import numpy
import gevent

from HardwareRepository.HardwareObjects.abstract.Abstract.OnlineProcessing import (
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
)
from HardwareRepository import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "Motor"


class EMBLOnlineProcessing(AbstractOnlineProcessing):
    """
    EMBLOnlineProcessing obtains Dozor on the fly processing results
    """

    def __init__(self, name):
        AbstractOnlineProcessing.__init__(self, name)

        self.crystfel_script = ""
        self.chan_dozor_pass = None
        self.chan_frame_count = None
        self.display_task = None

    def init(self):
        AbstractOnlineProcessing.init(self)

        self.chan_dozor_pass = self.getChannelObject("chanDozorPass")
        if self.chan_dozor_pass is not None:
            self.chan_dozor_pass.connectSignal("update", self.batch_processed)
        self.chan_frame_count = self.getChannelObject("chanFrameCount")
        if self.chan_frame_count is not None:
            self.chan_frame_count.connectSignal("update", self.frame_count_changed)

        self.crystfel_script = self.getProperty("crystfel_script")

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
        good_index = numpy.where(self.results_raw["spots_resolution"] > 1 / 46.0)[0]
        good = self.results_aligned["spots_resolution"][good_index]
        if self.results_raw["spots_resolution"].size > 200:
            points_index = self.results_raw["spots_resolution"].size / 200
            for x in range(0, good_index.size, points_index):
                self.results_aligned["spots_resolution"][good_index[x]] = numpy.mean(
                    good[max(x - points_index / 2, 0): x + points_index / 2]
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
        AbstractOnlineProcessing.set_processing_status(self, status)

    def store_processing_results(self, status):
        """
        Stors processing results
        :param status: str
        :return:
        """
        AbstractOnlineProcessing.store_processing_results(self, status)
        self.display_task.kill()
        gevent.spawn(self.create_hit_list_files)

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
                "Online processing: Unable to store all image list in %s" % all_file_filename,
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

        num_dozor_hits = 0

        try:
            lst_file = open(lst_filename, "w")
            nxds_lst_file = open(nxds_filename, "w")
            for index in range(self.params_dict["images_num"]):
                if self.results_raw["score"][index] > 0:
                    filename = self.params_dict["template"] % \
                        (self.params_dict["run_number"], index + 1)
                    lst_file.write(filename + "\n")
                    nxds_lst_file.write(os.path.basename(filename) + "\n")
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
        except BaseException:
            self.print_log(
                "GUI",
                "error",
                "Online processing: Unable to store hit list in %s" % lst_filename,
            )
        finally:
            lst_file.close()
            nxds_lst_file.close()

        self.print_log(
            "GUI",
            "info",
            "Online processing: found %d dozor hits in %d collected images (%.2f%%)" % (
                num_dozor_hits,
                self.params_dict["images_num"],
                (100.0 * num_dozor_hits / self.params_dict["images_num"]))
        )

    def start_crystfel_autoproc(self, all_file_filename):
        """
        Start crystfel processing
        :return:
        """
        acq_params = self.data_collection.acquisitions[0].acquisition_parameters
        proc_params = self.data_collection.processing_parameters

        # stream_filename   = os.path.join(self.params_dict["process_directory"], "crystfel_stream.stream" )
        # geom_filename     = os.path.join(self.params_dict["process_directory"], "crystfel_detector.geom" )
        # cell_filename     = os.path.join(self.params_dict["process_directory"], "crystfel_cell.cell" )
        stream_filename = "crystfel_xgandalf.stream"
        geom_filename = "crystfel_detector.geom"
        cell_filename = "crystfel_cell.cell"
        crystfel_autoproc = os.path.join(
            self.params_dict["process_directory"],
            "crystfel_autoproc.sh")
        log_filename = "crystfel_xgandalf.log"
        nxdsinp_filename = os.path.join(
            self.params_dict["process_directory"], "nXDS.INP")
        procdir_cluster = self.params_dict["process_directory"].replace(
            "/data/users/", "/home/")

        beam_x, beam_y = HWR.beamline.detector.get_beam_centre()
        pixel_size_mm_x, pixel_size_mm_y = HWR.beamline.detector.get_pixel_size_mm()

        # HWR.beamline.detector.getProperty("type")

        # Eiger 4M:
        detector_size_x = 2070
        detector_size_y = 2167
        # Pilatus 2M:
        detector_size_x = 1475
        detector_size_y = 1679

        geom_file = """
clen = {:.5f}
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
""".format(HWR.beamline.detector.get_distance() / 1000.,
           acq_params.energy * 1000,
           1000. / pixel_size_mm_x,
           detector_size_x - 1,
           detector_size_y - 1,
           -beam_x / pixel_size_mm_x,
           -beam_y / pixel_size_mm_y
           )

        data_file = open(
            os.path.join(
                self.params_dict["process_directory"],
                geom_filename),
            "w")
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

        cell_file = """CrystFEL unit cell file version 1.0

lattice_type = orthorhombic
centering = I

a = {:.2f} A
b = {:.2f} A
c = {:.2f} A
al = {:.2f} deg
be = {:.2f} deg
ga = {:.2f} deg
""".format(94.6, 99.4, 87.6, 90, 90, 90)

# """.format(57.5, 57.5, 189.4, 90, 90, 120)
# """.format(144.0, 144.0, 62.50, 90, 90, 120)
# """.format(125.40, 125.40, 54.50, 90, 90, 90)
# """.format(90.0, 101.0, 133.0, 90, 90, 90)
# """.format(79.8, 84.6, 98.5, 93.8, 93.9, 92.1)
# """.format(78.74, 78.74, 37.93, 90, 90, 90)
# """.format(94.7, 99.2, 87.4, 90, 90, 90)

#            cell_a=proc_params.cell_a,
#            cell_b=proc_params.cell_b,
#            cell_c=proc_params.cell_c,
#            cell_alpha=proc_params.cell_alpha,
#            cell_beta=proc_params.cell_beta,
#            cell_gamma=proc_params.cell_gamma,
#        )

        data_file = open(
            os.path.join(
                self.params_dict["process_directory"],
                cell_filename),
            "w")
        data_file.write(cell_file)
        data_file.close()

        constant_h = 4.135667516e-15   # eV*s
        constant_c = 299792458.        # m/s

        nxds_file = """
!*****************************************************************************
! nXDS.INP for the EIGER 4M on P14-EH2 (EMBL Hamburg)
!*****************************************************************************

!============= JOB CONTROL
 JOB= XYCORR INIT COLSPOT POWDER IDXREF INTEGRATE CORRECT

 MAXIMUM_NUMBER_OF_PROCESSORS= 99
!MAXIMUM_NUMBER_OF_JOBS= 1
!NAME_TEMPLATE_OF_DATA_FRAMES= {:s}
!LIB= /mx-beta/lib/xds-zcbf.so
!DATA_RANGE=1 10000
 IMAGE_DIRECTORY= {:s}
 IMAGE_LIST={:s}
 VERBOSE=0

!============= INIT
 BACKGROUND_RANGE= 1 30
 TRUSTED_REGION=0.0 1.41

!============= COLSPOT
!STRONG_PIXEL=7.0
 MINIMUM_NUMBER_OF_SPOTS=30
 MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT=2
!SPOT_MAXIMUM-CENTROID= 2.0

!============= IDXREF
 REFINE(IDXREF)= BEAM ORIENTATION CELL POSITION
!SEPMIN=7.00
!CLUSTER_RADIUS=3.00
!NUMBER_OF_TESTED_BASIS_ORIENTATIONS= 1000000
!MAXIMUM_NUMBER_OF_DIFFERENCE_VECTOR_CLUSTERS= 30
!INTEGER_ERROR=0.10
!INDEX_ERROR= 0.05
!INDEX_MAGNITUDE= 4
 INDEX_QUALITY= 0.50
 MINIMUM_FRACTION_OF_INDEXED_SPOTS= 0.20

!============= INTEGRATE
 INCLUDE_RESOLUTION_RANGE= 50.0 1.60
!NUMBER_OF_PROFILE_GRID_POINTS_ALONG_ALPHA/BETA=13
!MINPK= 75.0
!SIGNAL_PIXEL= 2.0
!BACKGROUND_PIXEL= 5.0
 MINIMUM_EWALD_OFFSET_CORRECTION= 0.50
!MINIMUM_ZETA= 0.05
!MAXIMUM_ERROR_OF_SPOT_POSITION= 20.0

!============= CORRECT
 POSTREFINE= SKALA BEAM ORIENTATION CELL B-FACTOR POSITION
!FRIEDEL'S_LAW= TRUE
 MERGE=FALSE

!============= CRYSTAL
 SPACE_GROUP_NUMBER= 23
 UNIT_CELL_CONSTANTS=  94.6 99.4 87.6 90 90 90

!============= ROTATION PARAMETERS
 ROTATION_AXIS= 0 -1 0
 OSCILLATION_RANGE= 0.0

!============= BEAM PARAMETERS
 X-RAY_WAVELENGTH=  {:.5f}
 INCIDENT_BEAM_DIRECTION=0.000  0.000  1.000
 FRACTION_OF_POLARIZATION= 0.98
 POLARIZATION_PLANE_NORMAL= 0 1 0

!============= DETECTOR PARAMETERS
 DETECTOR=EIGER
 NX= {:.0f}
 NY= {:.0f}
 QX= {:.4f}
 QY= {:.4f}
 MINIMUM_VALID_PIXEL_VALUE=0
 OVERLOAD=1048500
 SENSOR_THICKNESS=0.45
 DIRECTION_OF_DETECTOR_X-AXIS= 1 0 0
 DIRECTION_OF_DETECTOR_Y-AXIS= 0 1 0
 ORGX= {:.2f}
 ORGY= {:.2f}
 DETECTOR_DISTANCE= {:.2f}
""".format(self.params_dict["template"],
           os.path.dirname(self.params_dict["template"]),
           "nxds_dozor_hits.lst",
           1e10 * (constant_h * constant_c) / (acq_params.energy * 1000),
           pixel_size_mm_x,
           pixel_size_mm_y,
           detector_size_x,
           detector_size_y,
           beam_x / pixel_size_mm_x,
           beam_y / pixel_size_mm_y,
           HWR.beamline.detector.get_distance()
           )

        data_file = open(nxdsinp_filename, "w")
        data_file.write(nxds_file)
        data_file.close()

        point_group = "422"
        # point_group = "6"

        """
        proc_params_dict = {"directory" : self.params_dict["directory"],
                            "lst_file": lst_filename,
                            "geom_file": geom_filename,
                            "stream_file" : stream_filename,
                            "cell_filename" : cell_filename,
                            "point_group": "422",
                            "space_group": proc_params.space_group,
                            "hres": acq_params.resolution}
        log.info("Online processing: Crystfel processing parameters: %s" % str(proc_params_dict))
        """

        end_of_line_to_execute = " %s %s %s %s %s %s %s %.2f" % (
            self.params_dict["process_directory"],
            all_file_filename,
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
            "Online processing: Starting crystfel %s with parameters %s "
            % (self.crystfel_script, end_of_line_to_execute),
        )

        num_cores = 160

        crystfel_command = "ssh bcrunch 'set path = ( /mx-beta/crystfel/crystfel-0.8.0/bin $path ) ; \
                                         source /mx-beta/etc/setup.csh ; \
                                         srun -c " + str(num_cores) + " -D " + procdir_cluster + " \
                                             indexamajig -i images_fullpath.lst -g " + geom_filename + " \
                                                         --peaks=zaef --threshold=40 --min-gradient=100 --min-snr=5 --no-cell-combinations \
                                                         --indexing=xgandalf --int-radius=3,4,5 --wait-for-file=300 \
                                                         -o " + stream_filename + " \
                                                         -p " + cell_filename + " -j " + str(num_cores) + " \
                                                         >& " + procdir_cluster + "/" + log_filename + "'"

        data_file = open(crystfel_autoproc, "w")
        data_file.write("#!/bin/bash\n")
        data_file.write("\n")
        data_file.write("source /mx-beta/etc/setup.csh\n")
        data_file.write(
            "declare -x PATH=\"$PATH:/mx-beta/crystfel/crystfel-0.8.0/bin\"\n")
        data_file.write("\n")
        data_file.write("srun -c " + str(num_cores) + " -D " + procdir_cluster +
                        " indexamajig -i images_fullpath.lst -g " + geom_filename +
                        " --peaks=zaef --threshold=40 --min-gradient=100 --min-snr=5 --no-cell-combinations " +
                        " --indexing=mosflm --int-radius=3,4,5 --wait-for-file=300 " +
                        " -o " + stream_filename +
                        " -p " + cell_filename + " -j " + str(num_cores) +
                        " 2> " + procdir_cluster + "/" + log_filename + "\n")
        data_file.write("\n")
        data_file.write("mkdir crystfel_results\n")
        data_file.write("cd crystfel_results\n")
        data_file.write("\n")
        data_file.write(
            "crystfel_make_hkl_and_stats crystfel.stream crystfel_cell.cell 6 P63 1.6 -partialator\n")
        data_file.write("\n")
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
            close_fds=True)

        """
        subprocess.Popen(str(self.crystfel_script + end_of_line_to_execute),
                             shell=True, stdin=None, stdout=None,
                             stderr=None, close_fds=True)
        """
