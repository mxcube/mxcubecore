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

Starting point for discussion. Some points:

- We  could move the contents of 'beam' (below) to the top level.
  do we want that, with the attendant confusion?

- Do we want people to access teh contained hardware objecs (flux, motors, ...)
  or to we want wrapper functions in beam, diffractometer, etc.

- Are things in the right place? E.g. 'resolution' could certainly be elsewhere.



The proposed structure would be somethign like the following,
where the topmost level is contained in this object.

- beam: AbstractBeam # NB still TBD. Replaces and extends BeamInfo

    # Xray beam upstream of diffractometer, and related matters

    flux: AbstractFlux
    transmission: float
    energy: AbstractEnergy
    fastshutter: AbstractNState
    safetyshutter: AbstractNState
    door_interlock: AbstractNState
    # attenuators: AbstractAttenuator
    # slits: AbstractSlits
    # apertures: AbstractAperture

- diffractometer: AbstractDiffractometer

    # The diffractometer and related motors and actuators

    omega: AbstractMotor
    kappa: AbstractMotor
    phi: AbstractMotor
    chi: AbstractMotor
    get_rotation_motors()

    alignmentx: AbstractMotor
    alignmenty: AbstractMotor
    alignmentz: AbstractMotor
    centringx: AbstractMotor
    centringy: AbstractMotor
    get_alignment_motors()

    frontlight: AbstractNState
    backlight: AbstractNState
    scintillator: AbstractNState
    beamstop: AbstractNState
    capillary: AbstractNState

- graphics

    # The OAV, camera, and related.

    camera: AbstractVideoDevice
    zoom: AbstractNState
    # focus??  Generallyidentical to one of the alignment motors.
    # Shape history stored here

- detector: AbstractDetector

    # The detector and attached motors and actuators

    distance: AbstractMotor
    resolution: AbstractMotor
    two_theta: AbstractMotor
    detector_cover: AbstractNState

- sample_changer: AbstractSampleChanger

- queue: QueueManager

- queue_model: QueueModel

- session: Session

- lims_client: AbstractLimsClient # NBNB still TBD.

Experimental procedures

    # Top level objects? Dictionary?

    energy_scan
    mxcollect
    xrf_spectrum
    xray_imaging
    gphl_workflow
    edna
    centring ?

Server links

    # Top level objects? Dictionary?

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

__copyright__ = """ Copyright © 2019 by Global Phasing Ltd. """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"


class Beamline(object):
    """Beamline class serving as singleton container for links to HardwareObjects

    NB This is deliberately NOT a HardwareObjewct - I think we need somethings simpler here"""


    def __init__(self, hwr_repository_server):
        """
        In the longer term if might be worth it refactoring the configuration system

        Also, we should move the hwr_repository_server here
        and stop using the api module

        Param :
        :param hwr_repository_server: HardwareRepository.HardwareRepository.__HardwareRepositoryClient
        """

        self._hardware_repository = hwr_repository_server
        self._beamline_setup = hwr_repository_server.getHardareObject("beamline-setup")

    @property
    def beam(self):
        """Beam hardware object (NEW, expanded from BeamInfo)
        Should replace also BeamlineTools, BeamlineConfiguration

        :return Optional[HardwareRepository.HardwareObjects.BeamInfo]"""
        return self._beamline_setup.getObjectByRole("beam_info")

    @property
    def diffractometer(self):
        """Diffractometer hardware object

        :return HardwareRepository.HardwareObjects.abstract.AbstractDiffractometer.AbstractDiffractometer"""
        return self._beamline_setup.getObjectByRole("diffractometer")

    @property
    def graphics(self):
        """Object to handle OAV, camera, shapes, and related. Type is
         AbstractGraphicsObject (NEW - superclass of Qt4_GraphicsManager and Shapes)

        :return HardwareRepository.HardwareObjects.abstract.AbstractGraphicsObject.AbstractGraphicsObject"""
        return self._beamline_setup.getObjectByRole("shape_history")

    @property
    def detector(self):
        """Detector hardware object

        :return HardwareRepository.HardwareObjects.abstract.AbstractDetector.AbstractDetector"""
        return self._beamline_setup.getObjectByRole("detector")

    @property
    def sample_changer(self):
        """SampleChanger hardware object

        :return HardwareRepository.HardwareObjects.abstract.AbstractSampleChanger.AbstractSampleChanger"""
        return self._beamline_setup.getObjectByRole("sample_changer")

    @property
    def queue_manager(self):
        """Queue hardware object

        :return HardwareRepository.HardwareObjects.QueueManager.QueueManager"""
        return self._hardware_repository.getHardwareObject("queue")

    @property
    def queue_model(self):
        """Queue-model hardware object

        :return HardwareRepository.HardwareObjects.QueueModel.QueueModel"""
        return self._hardware_repository.getHardwareObject("queue-model")

    @property
    def session(self):
        """Session hardware object

        :return HardwareRepository.HardwareObjects.Session.Session"""
        return self._beamline_setup.getObjectByRole("session")

    @property
    def lims_client(self):
        """Lims client hardware object

        NB New AbstractLimsClient - needs to be written

        :return HardwareRepository.HardwareObjects.abstract.AbstractLimsClient.AbstractLimsClient"""
        return self._beamline_setup.getObjectByRole("lims_client")

