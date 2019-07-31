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

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"

import warnings
from collections import OrderedDict
from HardwareRepository.BaseHardwareObjects import ConfiguredObject

# NBNB The acq parameter names match the attributes of AcquisitionParameters
# Whereas the limit parmeter values use more udnerstandable names
#
# TODO Make all tags consistent, including AcquisitionParameters attributes.


class Beamline(ConfiguredObject):
    """Beamline class serving as singleton container for links to HardwareObjects"""

    # Roles of defined objects and the category they belong to
    # NB the double underscore is deliberate - attribute must be hidden from subclasses
    __object_role_categories = OrderedDict()

    # NBNB these should be accessed ONLY as beamline.SUPPORTED_..._PARAMETERS
    # NBNB Subclasses may add local parameters but may NOT remove any
    #
    # Supported acquisition parameter tags:
    SUPPORTED_ACQ_PARAMETERS = frozenset(
        (
            "exp_time",
            "osc_range",
            "num_passes",
            "first_image",
            "run_number",
            "overlap",
            "num_images",
            "inverse_beam",
            "take_dark_current",
            "skip_existing_images",
            "take_snapshots",
        )
    )
    # Supported limit parameter tags:
    SUPPORTED_LIMIT_PARAMETERS = frozenset(
        ("exposure_time", "osc_range", "number_of_images", "kappa", "kappa_phi")
    )

    def __init__(self, name):
        """

        Args:
            name (str) : Object name, generally saet to teh role name of the object
        """
        super(Beamline, self).__init__(name)

        # List[str] of advanced method names
        self.advanced_methods = []

        # bool Is wavelength tunable
        self.tunable_wavelength = False

        # bool Disable number-of-passes widget NBNB TODO Move elsewhere??
        self.disable_num_passes = False

        # bool By default run processing of (certain?)data collections in aprallel?
        self.run_processing_parallel = False

        # Dictionary-of-dictionaries of default acquisition parameters
        self.default_acquisition_parameters = {}

        # Dictionary of acquisition parameter limits
        self.acquisition_limit_values = {}

        # int Starting run number for path_template
        self.run_number = 1

    def _init(self):
        """Objetc initialisation - executed *before* loading contents"""
        pass

    def init(self):
        """Object initialisation - executed *after* loading contents"""

        # Validate acquisition parameters
        for acquisition_type, params in self.default_acquisition_parameters.items():
            unrecognised = [x for x in params if x not in self.SUPPORTED_ACQ_PARAMETERS]
            if unrecognised:
                warnings.warn(
                    "Unrecognised acquisition parameters for %s: %s"
                    % (acquisition_type, unrecognised)
                )
        # Validate limits parameters
        unrecognised = [
            x
            for x in self.acquisition_limit_values
            if x not in self.SUPPORTED_LIMIT_PARAMETERS
        ]
        if unrecognised:
            warnings.warn("Unrecognised parameter limits for: %s" % unrecognised)

    @property
    def role_to_category(self):
        """Mapping from role to category

        Returns:
            OrderedDict[text_str, text_str]
        """
        # Copy roles from superclass and add those form this class
        result = super(Beamline, self).role_to_category
        result.update(self.__object_role_categories)
        return result

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

    __object_role_categories["flux"] = "hardware"

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
    def plate_manipulator(self):
        """Plate Manuipulator Hardware object
        NBNB TODO REMOVE THIS and treat as an alternative sample changer instead.

        Returns:
            Optional[AbstractSampleChanger]:
        """
        warnings.warn(
            DeprecationWarning(
                "plate_manipulator role should be replaced by sample_changer"
            )
        )
        return self._objects.get("plate_manipulator")

    __object_role_categories["plate_manipulator"] = "hardware"

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
    def centring(self):
        """Centring procedures object. Includes X-ray, n-click, optical, move_to_beam

        Returns:
            Optional[AbstractCentring]:
        """
        return self._objects.get("centring")

    __object_role_categories["centring"] = "procedure"

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
    def data_analysis(self):
        """EDNA charadterisation and analysis procedure.

        NB the current code looks rather EDNA-specific
        to be called 'AbsatractCharacterisation'.
        Potentially we could generalise it, and maybe make it into a procedure???

        Returns:
            Optional[EdnaCharacterisation]:
        """
        return self._objects.get("data_analysis")

    __object_role_categories["data_analysis"] = "analysis"

    @property
    def beam_realign(self):
        """Beam-realign procedure object

        Returns:
            Optional[AbstractProcedure]:
        """
        return self._objects.get("beam_realign")

    __object_role_categories["beam_realign"] = "procedure"

    @property
    def image_tracking(self):
        """Imaging tracking object

        Returns:
            Optional[HardwareObject]:
        """
        return self._objects.get("image_tracking")

    __object_role_categories["image_tracking"] = "hardware"

    # NB Objects need not be HardwareObjects
    # We still categorise them as'hardware' if they are not procedures, though
    # The attribute values will be given in the config.yml file

    def get_default_acquisition_parameters(self, acquisition_type="default"):
        """
        :returns: A AcquisitionParameters object with all default parameters for the
                  specified acquisition type. "default" is a standard acqquisition
        """
        # Imported here to avoid circular imports
        from HardwareRepository.HardwareObjects import queue_model_objects
        acq_parameters = queue_model_objects.AcquisitionParameters()

        params = self.default_acquisition_parameters["default"].copy()
        if acquisition_type != "default":
            dd0 = self.default_acquisition_parameters.get(acquisition_type)
            if dd0 is None:
                warnings.warn(
                    "No separate parameters for acquisition type: %s - using default."
                    % acquisition_type
                )
            else:
                params.update(dd0)

        for tag, val in params.items():
            setattr(acq_parameters, tag, val)

        motor_positions = self.diffractometer.get_positions()
        osc_start = motor_positions.get("phi", params["osc_start"])
        acq_parameters.osc_start = round(float(osc_start), 2)
        kappa = motor_positions.get("kappa", 0.0)
        acq_parameters.kappa = round(float(kappa), 2)
        kappa_phi = motor_positions.get("kappa_phi", 0.0)
        acq_parameters.kappa_phi = round(float(kappa_phi), 2)

        try:
            acq_parameters.resolution = self.resolution.getPosition()
        except:
            acq_parameters.resolution = 0.0

        try:
            acq_parameters.energy = self.energy.get_current_energy()
        except:
            acq_parameters.energy = 0.0

        try:
            acq_parameters.transmission = self.transmission.get_value()
        except:
            acq_parameters.transmission = 0.0

        try:
            acq_parameters.shutterless = self.detector.has_shutterless()
        except:
            acq_parameters.shutterless = False

        try:
            acq_parameters.detector_mode = self.detector.get_detector_mode()
        except:
            acq_parameters.detector_mode = ""

        return acq_parameters

    def get_default_path_template(self):
        """
        :returns: A PathTemplate object with default parameters.
        """
        # Imported here to avoid circular imports
        from HardwareRepository.HardwareObjects import queue_model_objects
        path_template = queue_model_objects.PathTemplate()

        path_template.directory = str()
        path_template.process_directory = str()
        path_template.base_prefix = str()
        path_template.mad_prefix = ""
        path_template.reference_image_prefix = ""
        path_template.wedge_prefix = ""

        acq_params = self.get_default_acquisition_parameters()
        path_template.start_num = acq_params.first_image
        path_template.num_files = acq_params.num_images

        path_template.run_number = self.run_number

        file_info = self.session["file_info"]
        path_template.suffix = file_info.getProperty("file_suffix")
        path_template.precision = "04"
        try:
            if file_info.getProperty("precision"):
                path_template.precision = eval(file_info.getProperty("precision"))
        except BaseException:
            pass

        return path_template
