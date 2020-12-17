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
MAXIVAutoProcessing
"""

import os
import time
import logging
import gevent
import subprocess

from XSDataAutoprocv1_0 import XSDataAutoprocInput

from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataString

from mx3core.BaseHardwareObjects import HardwareObject


class MAXIVAutoProcessing(HardwareObject):
    """
    Descript. :
    """

    def __init__(self, name):
        """
        Descript. :
        """
        HardwareObject.__init__(self, name)
        self.result = None
        self.autoproc_programs = None
        self.current_autoproc_procedure = None

    def init(self):
        """
        Descript. :
        """
        self.autoproc_programs = self["programs"]

    def execute_autoprocessing(self, process_event, params_dict, frame_number):
        """
        Descript. :
        """
        if self.autoproc_programs is not None:
            self.current_autoproc_procedure = gevent.spawn(
                self.autoproc_procedure, process_event, params_dict, frame_number
            )
            self.current_autoproc_procedure.link(self.autoproc_done)

    def autoproc_procedure(self, process_event, params_dict, frame_number):
        """
        Descript. :

        Main autoprocessing procedure. At the beginning correct event (defined
        in xml) is found. If the event is executable then accordingly to the
        event type (image, after) then the sequence is executed:
        Implemented tasks:
           - after : Main autoprocessing procedure
                     1. Input file is generated with create_autoproc_input
                        Input file has name "edna-autoproc-input-%Y%m%d_%H%M%S.xml".
                     2. Then it waits for XDS.INP directory and if it exists then
                        creates input file
                     3. edna_autoprocessing.sh script is executed with parameters:
                        - arg1 : generated xml file
                        - arg2 : process dir
                     4. script executes EDNA EDPluginControlAutoprocv1_0
           - image : Thumbnail generation for first and last image
                     1. No input file is generated
                     2. edna_thumbnails.sh script is executed with parameters:
                        - arg1 : image base dir (place where thumb will be generated)
                        - arg2 : file name
        """
        for program in self.autoproc_programs:
            if process_event == program.get_property("event"):
                module = program.get_property("module").lower()
                print(2 * "###########")
                if process_event == "after":
                    input_filename, will_execute = self.create_autoproc_input(
                        process_event, params_dict
                    )
                    path = params_dict["auto_dir"]
                    mode = "after"
                    dataCollectionId = str(params_dict["collection_id"])
                    residues = 200
                    anomalous = False
                    cell = "0,0,0,0,0,0"
                    print("Module: ", module, ">> Will execute: ", will_execute)
                    print("input_filename   ", input_filename)
                    try:
                        if module == "ednaproc" and will_execute:
                            from ednaProcLauncher import EdnaProcLauncher

                            mod = EdnaProcLauncher(
                                path,
                                mode,
                                dataCollectionId,
                                residues,
                                anomalous,
                                cell,
                                None,
                            )

                        elif module == "autoproc" and will_execute:
                            from autoProcLauncher import AutoProcLauncher

                            mod = AutoProcLauncher(
                                path,
                                mode,
                                dataCollectionId,
                                residues,
                                anomalous,
                                cell,
                                None,
                            )
                    except Exception as ex:
                        print(ex)
                if process_event == "image":
                    if (
                        frame_number == 1
                        or frame_number
                        == params_dict["oscillation_sequence"][0]["number_of_images"]
                    ):
                        endOfLineToExecute = " %s %s/%s_%d_%05d.cbf" % (
                            params_dict["fileinfo"]["directory"],
                            params_dict["fileinfo"]["directory"],
                            params_dict["fileinfo"]["prefix"],
                            params_dict["fileinfo"]["run_number"],
                            frame_number,
                        )
                        will_execute = True
                if will_execute:
                    logging.getLogger("HWR").info(
                        "[MAXIVAutoprocessing] Executing module: %s" % module
                    )
                    try:
                        mod.parse_and_execute()
                    except Exception as ex:
                        logging.getLogger("HWR").error(
                            "[MAXIVAutoprocessing] Module %s  execution error." % module
                        )
                        print(module, ex)

    def autoproc_done(self, current_autoproc):
        """
        Descript. :
        """
        self.current_autoproc_procedure = None
        logging.getLogger("HWR").info("Autoprocessing executed.")

    def create_autoproc_input(self, event, params):
        """
        Descript. :
        """
        WAIT_XDS_TIMEOUT = 20
        WAIT_XDS_RESOLUTION = 1

        file_name_timestamp = time.strftime("%Y%m%d_%H%M%S")

        autoproc_path = params.get("xds_dir")
        autoproc_xds_filename = os.path.join(autoproc_path, "XDS.INP")
        autoproc_input_filename = os.path.join(
            autoproc_path, "edna-autoproc-input-%s" % file_name_timestamp
        )
        autoproc_output_file_name = os.path.join(
            autoproc_path, "edna-autoproc-results-%s" % file_name_timestamp
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
        if not isinstance(space_group, int) and len(space_group) > 0:
            autoproc_input.setSpacegroup(XSDataString(space_group))
        unit_cell = params.get("sample_reference").get("cell", "")
        if len(unit_cell) > 0:
            autoproc_input.setUnit_cell(XSDataString(unit_cell))

        autoproc_input.setCc_half_cutoff(XSDataDouble(18.0))

        # Maybe we have to check if directory is there. Maybe create dir with mxcube
        xds_appeared = False
        wait_xds_start = time.time()
        logging.info(
            "MAXIVAutoprocessing: Waiting for XDS.INP file: %s" % autoproc_xds_filename
        )
        while not xds_appeared and time.time() - wait_xds_start < WAIT_XDS_TIMEOUT:
            if (
                os.path.exists(autoproc_xds_filename)
                and os.stat(autoproc_xds_filename).st_size > 0
            ):
                xds_appeared = True
                logging.debug(
                    "MAXIVAutoprocessing: XDS.INP file is there, size={0}".format(
                        os.stat(autoproc_xds_filename).st_size
                    )
                )
            else:
                os.system("ls %s> /dev/null" % (os.path.dirname(autoproc_path)))
                gevent.sleep(WAIT_XDS_RESOLUTION)
        if not xds_appeared:
            logging.error(
                "MAXIVAutoprocessing: XDS.INP file ({0}) failed to appear after {1} seconds".format(
                    autoproc_xds_filename, WAIT_XDS_TIMEOUT
                )
            )
            return None, False

        autoproc_input.exportToFile(autoproc_input_filename)

        return autoproc_input_filename, True
