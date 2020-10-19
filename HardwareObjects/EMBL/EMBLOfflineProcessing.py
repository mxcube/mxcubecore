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
import subprocess

import gevent

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects.XSDataCommon import (
    XSDataDouble,
    XSDataFile,
    XSDataInteger,
    XSDataString,
)
from HardwareRepository.HardwareObjects.XSDataAutoprocv1_0 import XSDataAutoprocInput


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLOfflineProcessing(HardwareObject):
    """Hwobj assembles input xml and launches EDNAproc autoprocessing"""

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.result = None
        self.autoproc_programs = []

    def init(self):
        try:
            self.autoproc_programs = self["programs"]
        except KeyError:
            self.print_log("AutoProcessing: no autoprocessing program defined.")

    def execute_autoprocessing(
        self, process_event, params_dict, frame_number, run_processing=True
    ):
        """Method called from collection hwobj after successfull collection.

        :param process_event: processing type (after, before, image)
        :type process_event: str
        :param params_dict: collection parameters
        :type params_dict: dict
        :param frame_number: frame number
        :type frame_number: int
        :param run_processing: True = run processing or
                               False = create just input file
        :type run_processing: bool
        """
        self.autoproc_procedure(
            process_event, params_dict, frame_number, run_processing
        )

    def autoproc_procedure(
        self, process_event, params_dict, frame_number, run_processing=True
    ):
        """
        Main autoprocessing procedure. At the beginning correct event (defined
        in xml) is found. If the event is executable then accordingly to the
        event type (image, after) then the sequence is executed:
        Implemented tasks:
           - after : Main autoprocessing procedure
                     1. Input file is generated with create_autoproc_input
                        Input file has a name template
                        "edna-autoproc-input-%Y%m%d_%H%M%S.xml".
                     2. Then it waits for XDS.INP directory and if it exists
                        then creates input file
                     3. edna_autoprocessing.sh script is
                        executed with parameters:
                        - arg1 : generated xml file
                        - arg2 : process dir
                     4. script executes EDNA EDPluginControlEDNAproc
           - image : Thumbnail generation for first and last image
                     1. No input file is generated
                     2. edna_thumbnails.sh script is executed with parameters:
                        - arg1 : image base dir (place where thumb
                                 will be generated)
                        - arg2 : file name

        :param process_event: processing type (after, before, image)
        :type process_event: str
        :param params_dict: collection parameters
        :type params_dict: dict
        :param frame_number: frame number
        :type frame_number: int
        :param run_processing: True = run processing or
                               False = create just input file
        :type run_processing: bool
        """
        for program in self.autoproc_programs:
            if process_event == program.get_property("event"):
                executable = program.get_property("executable")

                will_execute = True
                if process_event == "after":
                    will_execute = run_processing
                    end_of_line_to_execute = " %s %s %s %s" % (
                        params_dict["xds_dir"],
                        params_dict.get("collection_id"),
                        params_dict["sample_reference"]["cell"],
                        params_dict["sample_reference"]["spacegroup"],
                    )
                elif process_event == "image":
                    filename = params_dict["fileinfo"]["template"] % frame_number
                    end_of_line_to_execute = " %s %s/%s" % (
                        params_dict["fileinfo"]["archive_directory"],
                        params_dict["fileinfo"]["directory"],
                        filename,
                    )
                if will_execute:
                    subprocess.Popen(
                        str(executable + end_of_line_to_execute),
                        shell=True,
                        stdin=None,
                        stdout=None,
                        stderr=None,
                        close_fds=True,
                    )

    def create_autoproc_input(self, event, params):
        """Creates processing input xml

        :param event: processing type (after, before, image)
        :type event: str
        :param params: collection parameters
        :type params: dict
        """
        xds_input_file_wait_timeout = 20
        xds_input_file_wait_resolution = 1

        file_name_timestamp = time.strftime("%Y%m%d_%H%M%S")

        autoproc_path = params.get("xds_dir")
        autoproc_xds_filename = os.path.join(autoproc_path, "XDS.INP")
        autoproc_input_filename = os.path.join(
            autoproc_path, "edna-autoproc-input-%s.xml" % file_name_timestamp
        )
        autoproc_output_file_name = os.path.join(
            autoproc_path, "edna-autoproc-results-%s.xml" % file_name_timestamp
        )

        autoproc_input = XSDataAutoprocInput()
        autoproc_xds_file = XSDataFile()
        autoproc_xds_file.setPath(XSDataString(autoproc_xds_filename))
        autoproc_input.setInput_file(autoproc_xds_file)

        autoproc_output_file = XSDataFile()
        autoproc_output_file.setPath(XSDataString(autoproc_output_file_name))
        autoproc_input.setOutput_file(autoproc_output_file)

        autoproc_input.setData_collection_id(XSDataInteger(params.get("collection_id")))
        residues_num = float(params.get("residues", 0))
        if residues_num != 0:
            autoproc_input.setNres(XSDataDouble(residues_num))
        space_group = params.get("sample_reference").get("spacegroup", "")
        if len(space_group) > 0:
            autoproc_input.setSpacegroup(XSDataString(space_group))
        unit_cell = params.get("sample_reference").get("cell", "")
        if len(unit_cell) > 0:
            autoproc_input.setUnit_cell(XSDataString(unit_cell))

        autoproc_input.setCc_half_cutoff(XSDataDouble(18.0))

        # Maybe we have to check if directory is there.
        # Maybe create dir with mxcube
        xds_appeared = False
        wait_xds_start = time.time()
        logging.debug(
            "EMBLAutoprocessing: Waiting for XDS.INP "
            + "file: %s" % autoproc_xds_filename
        )
        while (
            not xds_appeared
            and time.time() - wait_xds_start < xds_input_file_wait_timeout
        ):
            if (
                os.path.exists(autoproc_xds_filename)
                and os.stat(autoproc_xds_filename).st_size > 0
            ):
                xds_appeared = True
                logging.debug(
                    "EMBLAutoprocessing: XDS.INP file is there, size={0}".format(
                        os.stat(autoproc_xds_filename).st_size
                    )
                )
            else:
                os.system("ls %s> /dev/null" % (os.path.dirname(autoproc_path)))
                gevent.sleep(xds_input_file_wait_resolution)
        if not xds_appeared:
            logging.error(
                "EMBLAutoprocessing: XDS.INP file %s failed " % autoproc_xds_filename
                + "to appear after %d seconds" % xds_input_file_wait_timeout
            )
            return None, False

        autoproc_input.exportToFile(autoproc_input_filename)

        return autoproc_input_filename, True
