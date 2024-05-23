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

from typing import Union, Any
from warnings import warn
from mxcubecore.dispatcher import dispatcher

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"

import logging

from mxcubecore.BaseHardwareObjects import ConfiguredObject, HardwareObject

# NBNB The acq parameter names match the attributes of AcquisitionParameters
# Whereas the limit parameter values use more understandable names
#
# TODO Make all tags consistent, including AcquisitionParameters attributes.


class Beamline(ConfiguredObject):
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

        # Dictionary of acquisition parameter limits
        acquisition_limit_values = {}

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

        machine_info = None
        transmission = None
        cryo = None
        energy = None
        flux = None
        beam = None
        hutch_interlock = None
        safety_shutter = None
        fast_shutter = None
        diffractometer = None
        detector = None
        resolution = None
        sample_changer = None
        sample_changer_maintenance = None
        plate_manipulator = None
        session = None
        lims = None
        sample_view = None
        queue_manager = None
        queue_model = None
        collect = None
        xrf_spectrum = None
        energy_scan = None
        imaging = None
        beamline_actions = None
        xml_rpc_server = None
        workflow = None
        control = None
        gphl_workflow = None
        gphl_connection = None
        xray_centring = None
        online_processing = None
        offline_processing = None
        characterisation = None
        image_tracking = None
        mock_procedures = None
        data_publisher = None

    def _init(self) -> None:
        """Object initialisation - executed *before* loading contents"""
        pass

    def init(self):
        """Object initialisation - executed *after* loading contents"""
        pass

    def _hwr_init_done(self):
        """
        Method called after the initialization of HardwareRepository is done
        (when all HardwareObjects have been created and initialized)
        """
        self._hardware_object_id_dict = self._get_id_dict()

    def get_id(self, ho: HardwareObject) -> str:
        warn("Beamline.get_id is Deprecated. Use hwobj.id instead")
        return ho.id

    def get_hardware_object(self, _id: str) -> Union[HardwareObject, None]:
        warn("Beamline.get_hardware_object is Deprecated. Use get_by_id instead")
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
