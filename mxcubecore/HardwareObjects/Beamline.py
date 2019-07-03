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

All HardwareObjects
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

__copyright__ = """ Copyright © 2019 by Global Phasing Ltd. """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"

from collections import OrderedDict
from BaseHardwareObjects import ConfiguredObject


class Beamline(ConfiguredObject):
    """Beamline class serving as singleton container for links to HardwareObjects"""

    # Roles of defined objects and the category they belong to
    # NB the double underscore is deliberate - attribute must be hidden from subclasses
    __object_role_categories = OrderedDict()

    @property
    def machine_info(self):
        """Machine information Hardware object

        Returns:
            Optional[AbstractMachineInfo]:
        """
        return self._objects.get("machine_info")

    __object_role_categories["machine_info"] = "hardware"

    @property
    def transmission(self):
        """Transmission Hardware object

        Returns:
            Optional[AbstractTransmission]:
        """
        return self._objects.get("transmission")

    __object_role_categories["transmission"] = "hardware"

    @property
    def energy(self):
        """Energy Hardware object

        Returns:
            Optional[AbstractEnergy]:
        """
        return self._objects.get("energy")

    __object_role_categories["energy"] = "hardware"

    @property
    def flux(self):
        """Flux Hardware object

        Returns:
            Optional[AbstractActuator]:
        """
        return self._objects.get("flux")

    __object_role_categories["fkux"] = "hardware"

    @property
    def beam(self):
        """Beam Hardware object

        Returns:
            Optional[AbstractBeam]:
        """
        return self._objects.get("beam")

    __object_role_categories["beam"] = "hardware"

    @property
    def hutch_interlock(self):
        """Hutch Interlock Hardware object

        Returns:
            Optional[AbstractInterlock]:
        """
        return self._objects.get("hutch_interlock")

    __object_role_categories["hutch_interlock"] = "hardware"

    @property
    def safety_shutter(self):
        """Safety Shutter Hardware object

        Returns:
            Optional[AbstractShutter]:
        """
        return self._objects.get("safety_shutter")

    __object_role_categories["safety_shutter"] = "hardware"

    @property
    def fast_shutter(self):
        """Fast Shutter Hardware object

        Returns:
            Optional[AbstractShutter]:
        """
        return self._objects.get("fast_shutter")

    __object_role_categories["fast_shutter"] = "hardware"

    @property
    def diffractometer(self):
        """Diffractometer Hardware object

        Returns:
            Optional[AbstractDiffractometer]:
        """
        return self._objects.get("diffractometer")

    __object_role_categories["diffractometer"] = "hardware"

    @property
    def detector(self):
        """Detector Hardware object

        Returns:
            Optional[AbstractDetector]:
        """
        return self._objects.get("detector")

    __object_role_categories["detector"] = "hardware"

    @property
    def resolution(self):
        """Resolution Hardware object

        Returns:
            Optional[AbstractActuator]:
        """
        return self._objects.get("resolution")

    __object_role_categories["resolution"] = "hardware"

    @property
    def sample_changer(self):
        """Sample Changer Hardware object
        can be a sample changer, plate_manipulator, jets, chips

        Returns:
            Optional[AbstractSampleChanger]:
        """
        return self._objects.get("sample_changer")

    __object_role_categories["sample_changer"] = "hardware"

    @property
    def session(self):
        """Session Hardware object, holding information on current session and user.

        Returns:
            Optional[Session]:
        """
        return self._objects.get("session")

    __object_role_categories["session"] = "hardware"

    @property
    def lims(self):
        """LIMS client object.

        Returns:
            Optional[ISPyBClient]:
        """
        return self._objects.get("lims")

    __object_role_categories["lims"] = "hardware"

    @property
    def graphics(self):
        """Graphics/OAV object. Includes defined shapes.

        Returns:
            Optional[AbstractGraphics]:
        """
        return self._objects.get("graphics")

    __object_role_categories["graphics"] = "hardware"

    @property
    def queue_manager(self):
        """Queue manager object.

        Returns:
            Optional[QueueManager]:
        """
        return self._objects.get("queue_manager")

    __object_role_categories["queue_manager"] = "hardware"

    @property
    def queue_model(self):
        """Queue model object.

        Returns:
            Optional[QueueModel]:
        """
        return self._objects.get("queue_model")

    __object_role_categories["queue_model"] = "hardware"

    # Procedures

    @property
    def collect(self):
        """Data collection procedure.

        Returns:
            Optional[AbstractCollect]:
        """
        return self._objects.get("collect")

    __object_role_categories["collect"] = "procedure"

    @property
    def xrf_spectrum(self):
        """X-ray fluorescence spectrum procedure.

        Returns:
            Optional[AbstractProcedure]
        """
        return self._objects.get("xrf_spectrum")

    __object_role_categories["xrf_spectrum"] = "procedure"

    @property
    def energy_scan(self):
        """Energy scan procedure.

        Returns:
            Optional[AbstractProcedure]:
        """
        return self._objects.get("energy_scan")

    __object_role_categories["energy_scan"] = "procedure"

    @property
    def imaging(self):
        """Imaging procedure.

        Returns:
            Optional[AbstractProcedure]:
        """
        return self._objects.get("imaging")

    __object_role_categories["imaging"] = "procedure"

    @property
    def gphl_workflow(self):
        """Global phasing data collection workflow procedure.

        Returns:
            Optional[GpglWorkflow]:
        """
        return self._objects.get("gphl_workflow")

    __object_role_categories["gphl_workflow"] = "procedure"

    # This one is 'hardware', but it is put with its companion
    @property
    def gphl_connection(self):
        """Global PHasing workflow remote connection

        Returns:
            Optional[GphlWorkflowConnection]:
        """
        return self._objects.get("gphl_connection")

    __object_role_categories["gphl_connection"] = "hardware"

    # centring

    # NB Could centring be treated as procedures instesad?

    @property
    def n_click_centring(self):
        """Manual (n-click) centring procedure.

        Returns:
            Optional[AbstractCentring]:
        """
        return self._objects.get("n_click_centring")

    __object_role_categories["n_click_centring"] = "centring"

    @property
    def move_to_beam(self):
        """Manual in-plane, double-click (move-to-beam) centring procedure.

        Returns:
            Optional[AbstractCentring]:
        """
        return self._objects.get("move_to_beam")

    __object_role_categories["move_to_beam"] = "centring"

    @property
    def optical_centring(self):
        """Automatic optical centring procedure.

        Returns:
            Optional[AbstractCentring]:
        """
        return self._objects.get("optical_centring")

    __object_role_categories["optical_centring"] = "centring"

    @property
    def x_ray_centring(self):
        """Automatic X-ray centring procedure.

        Returns:
            Optional[AbstractCentring]:
        """
        return self._objects.get("x_ray_centring")

    __object_role_categories["x_ray_centring"] = "centring"

    # Analysis (combines processing and data analysis)

    @property
    def online_processing(self):
        """Synchronous (on-line) data processing procedure.

        Returns:
            Optional[AbstractProcessing]:
        """
        return self._objects.get("online_processing")

    __object_role_categories["online_processing"] = "analysis"

    @property
    def offline_processing(self):
        """Asynchronous (queue sumbission) data processing procedure.

        Returns:
            Optional[AbstractProcessing]:
        """
        return self._objects.get("offline_processing")

    __object_role_categories["offline_processing"] = "analysis"

    @property
    def edna_characterisation(self):
        """EDNA charadterisatoin and analysis procedure.

        NB the current code looks rather EDNA-specific
        to be called 'AbsatractCharacterisation'.
        Potentially we could generalise it, and maybe make it into a procedure???

        Returns:
            Optional[EdnaCharacterisation]:
        """
        return self._objects.get("edna_characterisation")

    __object_role_categories["edna_characterisation"] = "analysis"


class BeamlineSubclass(Beamline):
    """Example of Beamline subclass, for local enhancements"""

    # Roles of defined objects and the category they belong to
    # NB the double underscore is deliberate - attribute must be hidden from subclasses
    __object_role_categories = OrderedDict()

    def __init__(self, mode="production"):
        """Subclass init

        Adds slots for non-object configuration parameters

        """
        super(self, BeamlineSubclass).__init__(self)

        self.mode = mode

        # Add non-object attriiutes to configure

        # List/tuple of advanced methods. Value set in config file
        self.advanced_methods = None

        # Boolean - is wavelength tunable? Value set in config file
        self.tunable_wavelength = None

        # Boolean - disable number-of-passes input box. Value set in config file
        self.disable_num_passes = None

    # NB This property is the only addition necessary to make the subclass finction
    @property
    def role_to_category(self):
        """Mapping from role to category

        Returns:
            OrderedDict[text_str, text_str]
        """
        # Copy roles from superclass and add those form this class
        result = super(self, BeamlineSubclass).role_to_category
        result.update(self.__object_role_categories)
        return result

    # Additional properties

    @property
    def beam_definer(self):
        """Beam-definer Hardware object

        Returns:
            Optional[AbstractMotor]:
        """
        return self._objects.get("beam_definer")

    __object_role_categories["beam_definer"] = "hardware"

    @property
    def beam_realign(self):
        """Beam-realign procedure object

        Returns:
            Optional[AbstractProcedure]:
        """
        return self._objects.get("beam_realign")

    __object_role_categories["beam_realign"] = "procedure"

    # NB Objects need not be HardwareObjects
    # We still categorise them as'hardware' if they are not procedures, though
    # The attribute values will be given in the config.yml file
    @property
    def default_characterisation_parameters(self):
        """Default characterisation parameters object

        Returns:
            Optional[queue_model_objects.CharacterisationParameters]:
        """
        return self._objects.get("default_characterisation_parameters")

    __object_role_categories["default_characterisation_parameters"] = "hardware"
