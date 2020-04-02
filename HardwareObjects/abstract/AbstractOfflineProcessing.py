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


__license__ = "LGPLv3+"
__category__ = "General"


class AbstractOfflineProcessing(HardwareObject):
    """Hwobj assembles input xml and launches EDNAproc autoprocessing"""

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.result = None
        self.autoproc_programs = []

    def init(self):
        HardwareObject.init(self)
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
        return

    def create_autoproc_input(self, event, params):
        """Creates processing input xml

        :param event: processing type (after, before, image)
        :type event: str
        :param params: collection parameters
        :type params: dict
        """
        return
