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

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from typing import (
    Any,
    Union,
)
from warnings import warn

from mxcubecore.dispatcher import dispatcher

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"

import logging

from mxcubecore.BaseHardwareObjects import (
    ConfiguredObject,
    HardwareObject,
)

# NBNB The acq parameter names match the attributes of AcquisitionParameters
# Whereas the limit parameter values use more understandable names
#
# TODO Make all tags consistent, including AcquisitionParameters attributes.


class Beamline(HardwareObject):
    """Beamline class serving as singleton container for links to HardwareObjects"""

    class HOConfig(ConfiguredObject.HOConfig):

        # Properties - definition and default values

        # List[str] of advanced method names
        advanced_methods = []

        # List[str] of available methods
        available_methods = []

        # int number of clicks used for click centring
        click_centring_num_clicks = 3

        # bool Is wavelength tunable
        tunable_wavelength = False

        # bool Disable number-of-passes widget NBNB TODO Move elsewhere??
        disable_num_passes = False

        # bool By default run online processing (characterization/mesh?)
        run_online_processing = False

        offline_processing_methods = []

        online_processing_methods = []

        # Dictionary-of-dictionaries of default acquisition parameters
        default_acquisition_parameters = {}

        # int Starting run number for path_template
        run_number = 1

        # List of undulators
        undulators = []

        # Format of mesh result for display
        mesh_result_format = "PNG"

        # bool Use the native mesh feature available, true by default
        use_native_mesh = True

        # bool Enable features to work with points in the plane, called
        # 2D-points, (none centred positions)
        enable_2d_points = True

        # Contained hardware objects

    @property
    def machine_info(self) -> HardwareObject | None:
        return self.get_object_by_role("machine_info")

    @property
    def transmission(self) -> HardwareObject | None:
        return self.get_object_by_role("transmission")

    @property
    def cryo(self) -> HardwareObject | None:
        return self.get_object_by_role("cryo")

    @property
    def energy(self) -> HardwareObject | None:
        return self.get_object_by_role("energy")

    @property
    def flux(self) -> HardwareObject | None:
        return self.get_object_by_role("flux")

    @property
    def beam(self) -> HardwareObject | None:
        return self.get_object_by_role("beam")

    @property
    def hutch_interlock(self) -> HardwareObject | None:
        return self.get_object_by_role("hutch_interlock")

    @property
    def safety_shutter(self) -> HardwareObject | None:
        return self.get_object_by_role("safety_shutter")

    @property
    def fast_shutter(self) -> HardwareObject | None:
        return self.get_object_by_role("fast_shutter")

    @property
    def diffractometer(self) -> HardwareObject | None:
        return self.get_object_by_role("diffractometer")

    @property
    def detector(self) -> HardwareObject | None:
        return self.get_object_by_role("detector")

    @property
    def resolution(self) -> HardwareObject | None:
        return self.get_object_by_role("resolution")

    @property
    def sample_changer(self) -> HardwareObject | None:
        return self.get_object_by_role("sample_changer")

    @property
    def sample_changer_maintenance(self) -> HardwareObject | None:
        return self.get_object_by_role("sample_changer_maintenance")

    @property
    def harvester(self) -> HardwareObject | None:
        return self.get_object_by_role("harvester")

    @property
    def harvester_maintenance(self) -> HardwareObject | None:
        return self.get_object_by_role("harvester_maintenance")

    @property
    def plate_manipulator(self) -> HardwareObject | None:
        return self.get_object_by_role("plate_manipulator")

    @property
    def session(self) -> HardwareObject | None:
        return self.get_object_by_role("session")

    @property
    def lims(self) -> HardwareObject | None:
        return self.get_object_by_role("lims")

    @property
    def sample_view(self) -> HardwareObject | None:
        return self.get_object_by_role("sample_view")

    @property
    def queue_manager(self) -> HardwareObject | None:
        return self.get_object_by_role("queue_manager")

    @property
    def queue_model(self) -> HardwareObject | None:
        return self.get_object_by_role("queue_model")

    @property
    def collect(self) -> HardwareObject | None:
        return self.get_object_by_role("collect")

    @property
    def xrf_spectrum(self) -> HardwareObject | None:
        return self.get_object_by_role("xrf_spectrum")

    @property
    def energy_scan(self) -> HardwareObject | None:
        return self.get_object_by_role("energy_scan")

    @property
    def imaging(self) -> HardwareObject | None:
        return self.get_object_by_role("imaging")

    @property
    def beamline_actions(self) -> HardwareObject | None:
        return self.get_object_by_role("beamline_actions")

    @property
    def xml_rpc_server(self) -> HardwareObject | None:
        return self.get_object_by_role("xml_rpc_server")

    @property
    def workflow(self) -> HardwareObject | None:
        return self.get_object_by_role("workflow")

    @property
    def control(self) -> HardwareObject | None:
        return self.get_object_by_role("control")

    @property
    def gphl_workflow(self) -> HardwareObject | None:
        return self.get_object_by_role("gphl_workflow")

    @property
    def gphl_connection(self) -> HardwareObject | None:
        return self.get_object_by_role("gphl_connection")

    @property
    def xray_centring(self) -> HardwareObject | None:
        return self.get_object_by_role("xray_centring")

    @property
    def online_processing(self) -> HardwareObject | None:
        return self.get_object_by_role("online_processing")

    @property
    def offline_processing(self) -> HardwareObject | None:
        return self.get_object_by_role("offline_processing")

    @property
    def characterisation(self) -> HardwareObject | None:
        return self.get_object_by_role("characterisation")

    @property
    def image_tracking(self) -> HardwareObject | None:
        return self.get_object_by_role("image_tracking")

    @property
    def procedure(self) -> HardwareObject | None:
        return self.get_object_by_role("procedure")

    @property
    def data_publisher(self) -> HardwareObject | None:
        return self.get_object_by_role("data_publisher")

    def _init(self) -> None:
        """Object initialisation - executed *before* loading contents"""

    def init(self):
        """Object initialisation - executed *after* loading contents"""

    def _hwr_init_done(self):
        """
        Method called after the initialization of HardwareRepository is done
        (when all HardwareObjects have been created and initialized)
        """
        self._hardware_object_id_dict = self._get_id_dict()

    def get_id(self, ho: HardwareObject) -> str:
        warn(
            "Beamline.get_id is Deprecated. Use hwobj.id instead", stacklevel=2
        )
        return ho.id

    def get_hardware_object(self, _id: str) -> Union[HardwareObject, None]:
        warn(
            "Beamline.get_hardware_object is Deprecated. Use get_by_id instead",
            stacklevel=2
        )
        return self.get_by_id(_id)

    # Signal handling functions:
    def emit(self, signal: Union[str, object, Any], *args) -> None:
        """Emit signal. Accepts both multiple args and a single tuple of args.

        This is needed for communication from the GUI to the core
        (jsonparamsgui in mxcubeqt)

        NBNB TODO HACK
        This is a duplicate of the same function in HardwareObjectMixin.
        Since the Beamline is not a CommandContainer or a normal HardwareObject
        it may not be appropriate to make it a subclass of HardwareObjectYaml
        We need to consider how we want this organised

        Args:
            signal (Union[str, object, Any]): In practice a string, or dispatcher.
            *args (tuple): Arguments sent with signal.
        """

        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]
        responses: list = dispatcher.send(signal, self, *args)
        if not responses:
            raise RuntimeError(
                "Signal %s is not connected" % signal
            )


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
        from mxcubecore.model import queue_model_objects

        acq_parameters = queue_model_objects.AcquisitionParameters()

        params = self.config.default_acquisition_parameters["default"].copy()
        if acquisition_type != "default":
            dd0 = self.config.default_acquisition_parameters.get(acquisition_type)
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
        osc_start = motor_positions.get("phi")
        if osc_start is None:
            acq_parameters.osc_start = params.get("osc_start")
        else:
            acq_parameters.osc_start = osc_start

        kappa = motor_positions.get("kappa")
        if kappa is None:
            acq_parameters.kappa = None
        else:
            acq_parameters.kappa = round(float(kappa), 2)

        kappa_phi = motor_positions.get("kappa_phi")
        if kappa_phi is None:
            acq_parameters.kappa_phi = None
        else:
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

        acq_parameters.shutterless = params.get("shutterless", True)

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
        from mxcubecore.model import queue_model_objects

        path_template = queue_model_objects.PathTemplate()

        acq_params = self.get_default_acquisition_parameters()
        path_template.start_num = acq_params.first_image
        path_template.num_files = acq_params.num_images

        path_template.run_number = self.config.run_number

        return path_template

    def get_default_characterisation_parameters(self):
        return self.characterisation.get_default_characterisation_parameters()

    def force_emit_signals(self):
        hwobjs = list(self.objects_by_role.values())
        for hwobj in hwobjs:
            hwobj.force_emit_signals()
            hwobjs.extend(hwobj.objects_by_role.values())
