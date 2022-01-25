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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Beamline class serving as singleton container for links to top-level HardwareObjects

All HardwareObjects
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"

import logging

from mxcubecore.BaseHardwareObjects import ConfiguredObject

# NBNB The acq parameter names match the attributes of AcquisitionParameters
# Whereas the limit parmeter values use more udnerstandable names
#
# TODO Make all tags consistent, including AcquisitionParameters attributes.


class Beamline(ConfiguredObject):
    """Beamline class serving as singleton container for links to HardwareObjects"""

    # Roles of defined objects and the category they belong to
    # NB the double underscore is deliberate - attribute must be hidden from subclasses
    __content_roles = []

    # Names of procedures under Beamline - set of sttrings.
    # NB subclasses must add additional parocedures to this set,
    # and may NOT override _procedure_names
    _procedure_names = set()

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

        # List[str] of available methods
        self.available_methods = []

        # int number of clicks used for click centring
        self.click_centring_num_clicks = 3

        # bool Is wavelength tunable
        self.tunable_wavelength = False

        # bool Disable number-of-passes widget NBNB TODO Move elsewhere??
        self.disable_num_passes = False

        # bool By default run processing of (certain?)data collections?
        self.run_offline_processing = False
        
        # bool By default run online processing (characterization/mesh?)
        self.run_online_processing = False
        
        self.offline_processing_methods = []

        self.online_processing_methods = []

        # Dictionary-of-dictionaries of default acquisition parameters
        self.default_acquisition_parameters = {}

        # Dictionary of acquisition parameter limits
        self.acquisition_limit_values = {}

        # int Starting run number for path_template
        self.run_number = 1

        # List of undulators
        self.undulators = []

    def init(self):
        """Object initialisation - executed *after* loading contents"""

        # Validate acquisition parameters
        for acquisition_type, params in self.default_acquisition_parameters.items():
            unrecognised = [x for x in params if x not in self.SUPPORTED_ACQ_PARAMETERS]
            if unrecognised:
                logging.getLogger("HWR").warning(
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
            logging.getLogger("HWR").warning(
                "Unrecognised parameter limits for: %s" % unrecognised
            )

    # NB this function must be re-implemented in nested subclasses
    @property
    def all_roles(self):
        """Tuple of all content object roles, indefinition and loading order

        Returns:
            tuple[text_str, ...]
        """
        return super(Beamline, self).all_roles + tuple(self.__content_roles)

    @property
    def machine_info(self):
        """Machine information Hardware object

        Returns:
            Optional[AbstractMachineInfo]:
        """
        return self._objects.get("machine_info")

    __content_roles.append("machine_info")

    @property
    def transmission(self):
        """Transmission Hardware object

        Returns:
            Optional[AbstractTransmission]:
        """
        return self._objects.get("transmission")

    __content_roles.append("transmission")

    @property
    def energy(self):
        """Energy Hardware object

        Returns:
            Optional[AbstractEnergy]:
        """
        return self._objects.get("energy")

    __content_roles.append("energy")

    @property
    def flux(self):
        """Flux Hardware object

        Returns:
            Optional[AbstractActuator]:
        """
        return self._objects.get("flux")

    __content_roles.append("flux")

    @property
    def beam(self):
        """Beam Hardware object

        Returns:
            Optional[AbstractBeam]:
        """
        return self._objects.get("beam")

    __content_roles.append("beam")

    @property
    def hutch_interlock(self):
        """Hutch Interlock Hardware object

        Returns:
            Optional[AbstractInterlock]:
        """
        return self._objects.get("hutch_interlock")

    __content_roles.append("hutch_interlock")

    @property
    def sample_environment(self):
        """Sample Environment Hardware Object

        Returns:
            Optional[AbstractSampleEnvironment]:
        """
        return self._objects.get("sample_environment")

    __content_roles.append("sample_environment")

    @property
    def safety_shutter(self):
        """Safety Shutter Hardware object

        Returns:
            Optional[AbstractShutter]:
        """
        return self._objects.get("safety_shutter")

    __content_roles.append("safety_shutter")

    @property
    def fast_shutter(self):
        """Fast Shutter Hardware object

        Returns:
            Optional[AbstractShutter]:
        """
        return self._objects.get("fast_shutter")

    __content_roles.append("fast_shutter")

    @property
    def diffractometer(self):
        """Diffractometer Hardware object

        Returns:
            Optional[AbstractDiffractometer]:
        """
        return self._objects.get("diffractometer")

    __content_roles.append("diffractometer")

    @property
    def detector(self):
        """Detector Hardware object

        Returns:
            Optional[AbstractDetector]:
        """
        return self._objects.get("detector")

    __content_roles.append("detector")

    @property
    def resolution(self):
        """Resolution Hardware object

        Returns:
            Optional[AbstractActuator]:
        """
        return self._objects.get("resolution")

    __content_roles.append("resolution")

    @property
    def sample_changer(self):
        """Sample Changer Hardware object
        can be a sample changer, plate_manipulator, jets, chips

        Returns:
            Optional[AbstractSampleChanger]:
        """
        return self._objects.get("sample_changer")

    __content_roles.append("sample_changer")

    @property
    def sample_changer_maintenance(self):
        """Sample Changer Maintnance Hardware object

        Returns:
            Optional[AbstractMaintnanceSampleChanger]:
        """
        return self._objects.get("sample_changer_maintenance")

    __content_roles.append("sample_changer_maintenance")

    @property
    def plate_manipulator(self):
        """Plate Manuipulator Hardware object
        NBNB TODO REMOVE THIS and treat as an alternative sample changer instead.

        Returns:
            Optional[AbstractSampleChanger]:
        """
        return self._objects.get("plate_manipulator")

    __content_roles.append("plate_manipulator")

    @property
    def session(self):
        """Session Hardware object, holding information on current session and user.

        Returns:
            Optional[Session]:
        """
        return self._objects.get("session")

    __content_roles.append("session")

    @property
    def lims(self):
        """LIMS client object.

        Returns:
            Optional[ISPyBClient]:
        """
        return self._objects.get("lims")

    __content_roles.append("lims")

    @property
    def sample_view(self):
        """Sample view object. Includes defined shapes.

        Returns:
            Optional[AbstractSampleView]:
        """
        return self._objects.get("sample_view")

    __content_roles.append("sample_view")

    @property
    def queue_manager(self):
        """Queue manager object.

        Returns:
            Optional[QueueManager]:
        """
        return self._objects.get("queue_manager")

    __content_roles.append("queue_manager")

    @property
    def queue_model(self):
        """Queue model object.

        Returns:
            Optional[QueueModel]:
        """
        return self._objects.get("queue_model")

    __content_roles.append("queue_model")

    # Procedures

    @property
    def collect(self):
        """Data collection procedure.

        Returns:
            Optional[AbstractCollect]:
        """
        return self._objects.get("collect")

    __content_roles.append("collect")

    @property
    def xrf_spectrum(self):
        """X-ray fluorescence spectrum procedure.

        Returns:
            Optional[AbstractProcedure]
        """
        return self._objects.get("xrf_spectrum")

    __content_roles.append("xrf_spectrum")

    @property
    def energy_scan(self):
        """Energy scan procedure.

        Returns:
            Optional[AbstractProcedure]:
        """
        return self._objects.get("energy_scan")

    __content_roles.append("energy_scan")

    @property
    def imaging(self):
        """Imaging procedure.

        Returns:
            Optional[AbstractProcedure]:
        """
        return self._objects.get("imaging")

    __content_roles.append("imaging")

    @property
    def xml_rpc_server(self):
        """XMLRPCServer for RPC

        Returns:
            Optional[XMLRPCServer]:
        """
        return self._objects.get("xml_rpc_server")

    __content_roles.append("xml_rpc_server")

    @property
    def beamline_actions(self):
        """Beamline actions

        Returns:
            Optional[HardwareObject]:
        """
        return self._objects.get("beamline_actions")

    __content_roles.append("beamline_actions")

    @property
    def workflow(self):
        """Standarad EDNA workflow procedure.

        Returns:
            Optional[Workflow]:
        """
        return self._objects.get("workflow")

    __content_roles.append("workflow")

    @property
    def gphl_workflow(self):
        """Global phasing data collection workflow procedure.

        Returns:
            Optional[GpglWorkflow]:
        """
        return self._objects.get("gphl_workflow")

    __content_roles.append("gphl_workflow")

    # This one is 'hardware', but it is put with its companion
    @property
    def gphl_connection(self):
        """Global PHasing workflow remote connection

        Returns:
            Optional[GphlWorkflowConnection]:
        """
        return self._objects.get("gphl_connection")

    __content_roles.append("gphl_connection")

    # centring

    # NB Could centring be treated as procedures instesad?

    @property
    def centring(self):
        """Centring procedures object. Includes X-ray, n-click, optical, move_to_beam

        Returns:
            Optional[AbstractCentring]:
        """
        return self._objects.get("centring")

    __content_roles.append("centring")

    # Analysis (combines processing and data analysis)

    @property
    def online_processing(self):
        """Synchronous (on-line) data processing procedure.

        Returns:
            Optional[AbstractProcessing]:
        """
        return self._objects.get("online_processing")

    __content_roles.append("online_processing")

    @property
    def offline_processing(self):
        """Asynchronous (queue sumbission) data processing procedure.

        Returns:
            Optional[AbstractProcessing]:
        """
        return self._objects.get("offline_processing")

    __content_roles.append("offline_processing")

    @property
    def characterisation(self):
        """EDNA characterisation and analysis procedure.

        NB the current code looks rather EDNA-specific
        to be called 'AbsatractCharacterisation'.
        Potentially we could generalise it, and maybe make it into a procedure???

        Returns:
            Optional[EdnaCharacterisation]:
        """
        return self._objects.get("characterisation")

    __content_roles.append("characterisation")

    @property
    def beam_realign(self):
        """Beam-realign procedure object

        Returns:
            Optional[AbstractProcedure]:
        """
        return self._objects.get("beam_realign")

    __content_roles.append("beam_realign")

    @property
    def image_tracking(self):
        """Imaging tracking object

        Returns:
            Optional[HardwareObject]:
        """
        return self._objects.get("image_tracking")

    __content_roles.append("image_tracking")

    # Procedures

    @property
    def mock_procedure(self):
        """
        """
        return self._objects.get("mock_procedure")

    __content_roles.append("mock_procedure")

    @property
    def data_publisher(self):
        """
        """
        return self._objects.get("data_publisher")

    __content_roles.append("data_publisher")

    # NB this is just an example of a globally shared procedure description
    @property
    def manual_centring(self):
        """ Manual centring Procedure

        NB AbstractManualCentring serves to define the parameters for manual centring
        The actual implementation is set by configuration,
        and can be given as an AbstractManualCentring subclass on each beamline

        Returns:
            Optional[AbstractManualCentring]
        """
        return self._objects.get("manual_centring")

    __content_roles.append("manual_centring")
    # Registers this object as a procedure:
    _procedure_names.add("manual_centring")

    # Additional functions

    # NB Objects need not be HardwareObjects
    # We still categorise them as'hardware' if they are not procedures, though
    # The attribute values will be given in the config.yml file
    def get_default_acquisition_parameters(self, acquisition_type="default"):
        """
        :returns: A AcquisitionParameters object with all default parameters for the
                  specified acquisition type. "default" is a standard acqquisition
        """
        # Imported here to avoid circular imports
        from mxcubecore.HardwareObjects import queue_model_objects

        acq_parameters = queue_model_objects.AcquisitionParameters()

        params = self.default_acquisition_parameters["default"].copy()
        if acquisition_type != "default":
            dd0 = self.default_acquisition_parameters.get(acquisition_type)
            if dd0 is None:
                logging.getLogger("HWR").warning(
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
        kappa = kappa if kappa else 0.0
        acq_parameters.kappa = round(float(kappa), 2)
        kappa_phi = motor_positions.get("kappa_phi", 0.0)
        kappa_phi = kappa_phi if kappa_phi else 0.0
        acq_parameters.kappa_phi = round(float(kappa_phi), 2)

        try:
            acq_parameters.resolution = self.resolution.get_value()
        except Exception:
            logging.getLogger("HWR").warning(
                "get_default_acquisition_parameters: "
                "No current resolution, setting to 0.0"
            )
            acq_parameters.resolution = 0.0

        try:
            acq_parameters.energy = self.energy.get_value()
        except Exception:
            logging.getLogger("HWR").warning(
                "get_default_acquisition_parameters: "
                "No current energy, setting to 0.0"
            )
            acq_parameters.energy = 0.0

        try:
            acq_parameters.transmission = self.transmission.get_value()
        except Exception:
            logging.getLogger("HWR").warning(
                "get_default_acquisition_parameters: "
                "No current transmission, setting to 0.0"
            )
            acq_parameters.transmission = 0.0

        try:
            acq_parameters.shutterless = self.detector.has_shutterless()
        except Exception:
            logging.getLogger("HWR").warning(
                "get_default_acquisition_parameters: "
                "Could not get has_shutterless, setting to False"
            )
            acq_parameters.shutterless = False

        try:
            acq_parameters.detector_binning_mode = self.detector.get_binning_mode()
        except Exception:
            logging.getLogger("HWR").warning(
                "get_default_acquisition_parameters: "
                "Could not get detector mode, setting to ''"
            )
            acq_parameters.detector_binning_mode = ""

        try:
            acq_parameters.detector_roi_mode = self.detector.get_roi_mode()
        except Exception:
            logging.getLogger("HWR").warning(
                "get_default_acquisition_parameters: "
                "Could not get roi mode, setting to ''"
            )
            acq_parameters.detector_roi_mode = ""

        return acq_parameters

    def get_default_path_template(self):
        """
        :returns: A PathTemplate object with default parameters.
        """
        # Imported here to avoid circular imports
        from mxcubecore.HardwareObjects import queue_model_objects

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
        path_template.suffix = file_info.get_property("file_suffix")
        path_template.precision = "04"
        try:
            if file_info.get_property("precision"):
                path_template.precision = eval(file_info.get_property("precision"))
        except Exception:
            pass

        return path_template

    def get_default_characterisation_parameters(self):
        return self.characterisation.get_default_characterisation_parameters()

    def force_emit_signals(self):
        for role in self.all_roles:
            hwobj =  getattr(self, role)
            if hwobj is not None:
                try:
                    hwobj.force_emit_signals()
                    for attr in dir(hwobj):
                        if not attr.startswith("_"):
                            if hasattr(getattr(hwobj, attr), 'force_emit_signals'):
                                child_hwobj = getattr(hwobj, attr)
                                child_hwobj.force_emit_signals()
                except BaseException as ex:
                    logging.getLogger("HWR").error("Unable to call force_emit_signals (%s)" % str(ex))
