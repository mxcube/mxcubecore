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

from mxcubecore.HardwareObjects.XSDataCommon import (
    XSDataDouble,
    XSDataFile,
    XSDataInteger,
    XSDataString,
)
from mxcubecore.HardwareObjects.XSDataAutoprocv1_0 import XSDataAutoprocInput
from mxcubecore.HardwareObjects.abstract.AbstractProcedure import AbstractProcedure
from mxcubecore import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class OfflineProcessingMockup(AbstractProcedure):
    """Hwobj assembles input xml and launches EDNAproc autoprocessing"""

    def __init__(self, name):
        AbstractProcedure.__init__(self, name)
        self.autoproc_programs = None

    def init(self):
        AbstractProcedure.init(self)
        try:
            self.autoproc_programs = self["programs"]
        except KeyError:
            self.print_log("Offline processing: No autoprocessing program defined.")

    def start_procedure(self, data_model):
        for program in self.autoproc_programs:
            if process_event == program.get_property("event"):
                executable = program.get_property("executable")

                will_execute = True
                if process_event == "after":
                    will_execute = HWR.beamline.run_offline_processing
                    end_of_line_to_execute = " %s %s " % (
                        data_model["xds_dir"],
                        data_model.get("collection_id"),
                    )
                elif process_event == "image":
                    filename = params_dict["template"] % data_model["frame_number"]
                    end_of_line_to_execute = " %s %s/%s" % (
                        data_model["archive_directory"],
                        data_model["directory"],
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
            "AutoprocessingMockup: Waiting for XDS.INP "
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
                    "AutoprocessingMockup: XDS.INP file is there, size={0}".format(
                        os.stat(autoproc_xds_filename).st_size
                    )
                )
            else:
                os.system("ls %s> /dev/null" % (os.path.dirname(autoproc_path)))
                gevent.sleep(xds_input_file_wait_resolution)
        if not xds_appeared:
            logging.error(
                "AutoprocessingMockup: XDS.INP file %s failed " % autoproc_xds_filename
                + "to appear after %d seconds" % xds_input_file_wait_timeout
            )
            return None, False

        autoproc_input.exportToFile(autoproc_input_filename)

        return autoproc_input_filename, True
