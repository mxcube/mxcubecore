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

"""Beamline class serving as singleton container for links to top-level HardwareObjects

flux: AbstractFlux
transmission: float
energy: AbstractEnergy
fast_shutter: AbstractNState
safety_shutter: AbstractNState
door_interlock: AbstractNState
diffractometer: AbstractDiffractometer
    omega: AbstractMotor
    kappa: AbstractMotor
    chi: AbstractMotor
    alignmentx: AbstractMotor
    alignmenty: AbstractMotor
    alignmentz: AbstractMotor
    centringx: AbstractMotor
    centringy: AbstractMotor
graphics: AbstractGraphics
    camera: AbstractVideoDevice
    zoom: AbstractNState
detector: AbstractDetector
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
offline_processing
online_processing
data_analysis
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import os

__license__ = "LGPLv3+"


class Beamline(object):
    """Beamline class serving as singleton container for links to HardwareObjects
    """

    def __init__(self, hwr_path, hwr_server):
        """
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

                setattr(self, role, self._hwr.loadHardwareObject(self._config_dict[role]))

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except  AttributeError:
            print("Unable to access beamline attribute %s" % name)
            return None

    def has_online_processing(self):
        return True

    def has_offline_processing(self):
        return True

    def get_available_online_processing(self):
        return ()

    def get_available_offline_processing(self):
        return ()
