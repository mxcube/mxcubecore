#! /usr/bin/env python
# encoding: utf-8
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""Beamline class serving as singleton container for links to top-level HardwareObjects

flux: AbstractFlux
transmission: float
energy: AbstractEnergy
fast_shutter: AbstractNState
safety_shutter: AbstractNState
door_interlock: AbstractNState

diffractometer: AbstractDiffractometer
    # The diffractometer and related motors and actuators
    omega: AbstractMotor
    kappa: AbstractMotor
    chi: AbstractMotor
    alignmentx: AbstractMotor
    alignmenty: AbstractMotor
    alignmentz: AbstractMotor
    centringx: AbstractMotor
    centringy: AbstractMotor
graphics
    camera: AbstractVideoDevice
    zoom: AbstractNState
detector: AbstractDetector
    # The detector and attached motors and actuators
    distance: AbstractMotor
    resolution: AbstractMotor
    two_theta: AbstractMotor
    detector_cover: AbstractNState
sample_changer: AbstractSampleChanger
queue_manager: QueueManager
queue_model: QueueModel
session: Session
lims: AbstractLimsClient # NBNB still TBD.
energy_scan
collect
xrf_spectrum
xray_imaging
gphl_workflow
centring

    rpc_server
    redis_client
Software procedures
    # Top level objects? Dictionary?
    auto_processing
    data_analysis
    parallel_processing
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import os

__license__ = "LGPLv3+"


class Beamline(object):
    """Beamline class serving as singleton container for links to HardwareObjects
    NB This is deliberately NOT a HardwareObjewct - I think we need somethings simpler here"""


    def __init__(self, hwr_path, hwr_server):
        """
        In the longer term if might be worth it refactoring the configuration system
        Also, we should move the hwr_repository_server here
        and stop using the api module
        Param :
        :param hwr_repository_server: HardwareRepository.HardwareRepository.__HardwareRepositoryClient
        """
        self._hwr = hwr_server
        self._config_dict = {}

        config_filename = str(os.path.join(hwr_path[0], "config.txt"))
        config_file = open(config_filename, "r")

        for line in config_file.readlines():
            line = line.replace("\n", "").replace("\t", "")
            if line and not line.startswith("#"):
                (role, xml_filename) = line.replace(" ", "").split(",")
                self._config_dict[str(role)] = str(xml_filename)
      

        self.transmission = self._hwr.loadHardwareObject(self._config_dict["transmission"])
        self.energy = self._hwr.loadHardwareObject(self._config_dict["energy"])
        self.flux = self._hwr.loadHardwareObject(self._config_dict["flux"])
        self.resolution = self._hwr.loadHardwareObject(self._config_dict["resolution"])
        
        self.machine_info = self._hwr.loadHardwareObject(self._config_dict["machine_info"]) 
        self.beam = self._hwr.loadHardwareObject(self._config_dict["beam"])
        self.safety_shutter = self._hwr.loadHardwareObject(self._config_dict["safety_shutter"])

        self.diffractometer = self._hwr.loadHardwareObject(self._config_dict["diffractometer"])
        self.graphics = self._hwr.loadHardwareObject(self._config_dict["graphics"])
        self.detector = self._hwr.loadHardwareObject(self._config_dict["detector"])
        self.sample_changer = self._hwr.loadHardwareObject(self._config_dict["sample_changer"])
        self.plate_manipulator = self._hwr.loadHardwareObject(self._config_dict["plate_manipulator"])
        self.queue_manager = self._hwr.getHardwareObject(self._config_dict["queue_manager"])
        self.queue_model = self._hwr.getHardwareObject(self._config_dict["queue_model"])
        self.session = self._hwr.loadHardwareObject(self._config_dict["session"])
        self.lims = self._hwr.loadHardwareObject(self._config_dict["lims"])
