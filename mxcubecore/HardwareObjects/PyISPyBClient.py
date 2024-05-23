"""
A client for PyISPyB Webservices.
"""
import os
import json
import logging
import datetime

from typing_extensions import Literal

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR
from mxcubecore.model.common import BeamlineParameters, ISPYBCollectionPrameters

import pyispyb_client

from pyispyb_client.apis.tags import authentication_api
from pyispyb_client.model.login import Login

from pyispyb_client.apis.tags import webservices_serial_crystallography_api
from pyispyb_client.apis.tags import serial_crystallography_api
from pyispyb_client.model.ssx_data_collection_create import (
    SSXDataCollectionCreate,
)
from pyispyb_client.model.ssx_data_collection_group_create import (
    SSXDataCollectionGroupCreate,
)
from pyispyb_client.model.ssx_sample_create import SSXSampleCreate
from pyispyb_client.model.ssx_crystal_create import SSXCrystalCreate
from pyispyb_client.model.ssx_protein_create import SSXProteinCreate
from pyispyb_client.model.ssx_sample_component_create import (
    SSXSampleComponentCreate,
)
from pyispyb_client.model.event_chain_create import EventChainCreate
from pyispyb_client.model.event_create import (
    EventCreate,
)

from pyispyb_client import Configuration


class PyISPyBClient(HardwareObject):
    """
    PyISPyB Web-service client.
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)

    def init(self):
        self._token_timestamp = None

        if HWR.beamline.config.session:
            self.beamline_name = HWR.beamline.config.session.beamline_name
        else:
            self.beamline_name = "ID:TEST"

        self._username = self.get_property("username", "").strip()
        self._password = self.get_property("password", "").strip()
        self._plugin = self.get_property("plugin", "").strip()
        self._host = self.get_property("host", "").strip()

        self._configuration = Configuration(
            host=self._host,
        )

        self._update_token()

    def _update_token(self, request_token=False):
        """ """
        if not self._token_timestamp:
            request_token = True
        else:
            timedelta = datetime.datetime.now() - self._token_timestamp
            if timedelta.seconds > (3 * 60 * 60):
                request_token = True

        if request_token:
            try:
                self.authenticate()
            except Exception:
                logging.getLogger("HWR").exception("")

    def authenticate(self):
        with pyispyb_client.ApiClient(self._configuration) as api_client:
            api_instance = authentication_api.AuthenticationApi(api_client)
            login = Login(
                plugin=self._plugin, login=self._username, password=self._password
            )

            try:
                api_response = api_instance.login_ispyb_api_v1_auth_login_post(login)

                self._configuration = Configuration(
                    host=self._host,
                    #                   access_token=api_response.body.token,
                )
                self._configuration.access_token = api_response.body.token
            except pyispyb_client.ApiException as e:
                print(
                    "Exception when calling AuthenticationApi->login_ispyb_api_v1_auth_login_post: %s\n"
                    % e
                )

    def get_current_beamline_values(self):
        return BeamlineParameters(
            **{
                "energy": HWR.beamline.config.energy.get_value(),
                "wavelength": HWR.beamline.config.energy.get_wavelength(),
                "resolution": HWR.beamline.config.resolution.get_value(),
                "transmission": HWR.beamline.config.transmission.get_value(),
                "detector_distance": HWR.beamline.config.detector.distance.get_value(),
                "beam_x": HWR.beamline.config.detector.get_beam_position()[0],
                "beam_y": HWR.beamline.config.detector.get_beam_position()[1],
                "beam_size_x": HWR.beamline.config.beam.get_beam_size()[0],
                "beam_size_y": HWR.beamline.config.beam.get_beam_size()[1],
                "beam_shape": HWR.beamline.config.beam.get_beam_shape(),
                "energy_bandwidth": HWR.beamline.config.beam.get_property(
                    "energy_bandwidth", 0.1
                ),
            }
        )

    def get_additional_lims_values(self):
        return ISPYBCollectionPrameters(
            **{
                "flux_start": HWR.beamline.config.flux.get_value(),
                "flux_end": HWR.beamline.config.flux.get_value(),
                "start_time": datetime.datetime.now(),
                "end_time": datetime.datetime.now(),
                "chip_model": HWR.beamline.config.collect.get_property("chip_model", ""),
                "polarisation": HWR.beamline.config.beam.polarisation,
                "mono_stripe": HWR.beamline.config.beam.get_property("mono_stripe", ""),
            }
        )

    def mxcube_to_ispyb_collection_type(
        self, collection_type: str
    ) -> Literal["SSX-CHIP", "SSX-Jet"]:
        val = "SSX-CHIP"

        if collection_type == "ssx_chip_collection":
            val = "SSX-CHIP"
        elif collection_type == "ssx_injector_collection":
            val = "SSX-Jet"

        return val

    def create_ssx_data_collection_group(self, collection_parameters, session_id=None):
        self._update_token()
        sacronym, sname = collection_parameters.path_parameters.prefix.split("-")
        session_id = session_id if session_id else int(HWR.beamline.config.session.session_id)

        with pyispyb_client.ApiClient(self._configuration) as api_client:
            # Create an instance of the API class
            api_instance = webservices_serial_crystallography_api.WebservicesSerialCrystallographyApi(
                api_client
            )
            ssx_data_collection_group_create = {
                "sessionId": session_id,
                "startTime": datetime.datetime.now(),
                # "endTime": datetime.datetime.now(),
                "experimentType": self.mxcube_to_ispyb_collection_type(
                    collection_parameters.common_parameters.type
                ),
                "experimentName": collection_parameters.common_parameters.label,
                #                "comments": "comments_example",
                "sample": {
                    "name": sname,
                    "support": "support_example",
                    "crystal": {
                        #                        "size_X": -1.0,
                        #                        "size_Y": -1.0,
                        #                        "size_Z": -1.0,
                        #                        "abundance": -1.0,
                        "protein": {
                            "name": sname,
                            "acronym": sacronym,
                        },
                        "components": [],
                        #                      "components": [{
                        #                               "name": "name",
                        #                               "componentType": "Ligand",
                        #                               "composition": "composition_example",
                        #    "abundance": -1.0,
                        #                           },
                        #                       ],
                        #                   },"components":[{
                        #                           "name": "name",
                        #                           "componentType": "Ligand",
                        #                           "composition": "composition_example",
                        #                            "abundance": -1.0,
                        #                       },
                        #                    ],
                    },
                    "components": [],
                },
            }

            try:
                api_response = api_instance.create_datacollectiongroup(
                    ssx_data_collection_group_create
                )
                # pprint.pprint(api_response)
                return int(api_response.body)
            except pyispyb_client.ApiException as e:
                print(
                    "Exception when calling SerialCrystallographyApi->create_datacollectiongroup: %s\n"
                    % e
                )

    def create_ssx_data_collection(
        self, dcg_id, collection_parameters, beamline_parameters, extra_lims_values
    ):
        # Enter a context with an instance of the API client
        with pyispyb_client.ApiClient(self._configuration) as api_client:
            # Create an instance of the API class
            api_instance = webservices_serial_crystallography_api.WebservicesSerialCrystallographyApi(
                api_client
            )
            ssx_data_collection_create = {
                "dataCollectionGroupId": dcg_id,
                "exposureTime": collection_parameters.user_collection_parameters.exp_time,
                "transmission": beamline_parameters.transmission,
                "flux": extra_lims_values.flux_start,
                "xBeam": beamline_parameters.beam_x,
                "yBeam": beamline_parameters.beam_y,
                "wavelength": beamline_parameters.wavelength,
                "detectorDistance": beamline_parameters.detector_distance,
                "beamSizeAtSampleX": beamline_parameters.beam_size_x,
                "beamSizeAtSampleY": beamline_parameters.beam_size_y,
                "average_temperature": 0.0,
                "xtalSnapshotFullPath1": "",
                "xtalSnapshotFullPath2": "",
                "xtalSnapshotFullPath3": "",
                "xtalSnapshotFullPath4": "",
                "imagePrefix": collection_parameters.path_parameters.prefix,
                "numberOfPasses": 1,
                "numberOfImages": collection_parameters.collection_parameters.num_images,
                "resolution": beamline_parameters.resolution,
                "resolutionAtCorner": 0.0,
                "flux_end": extra_lims_values.flux_end,
                "detector_id": HWR.beamline.config.detector.get_property("detector_id"),
                "startTime": extra_lims_values.start_time,
                "endTime": extra_lims_values.end_time,
                "repetitionRate": 0.0,
                "energyBandwidth": beamline_parameters.energy_bandwidth,
                "monoStripe": extra_lims_values.mono_stripe,
                "jetSize": 0,
                "jetSpeed": 0,
                "laserEnergy": 0,
                "chipModel": extra_lims_values.chip_model,
                "chipPattern": "",
                "beamShape": beamline_parameters.beam_shape,
                "polarisation": extra_lims_values.polarisation,
                "underlator_gap1": 0,
                "event_chains": [
                    {
                        "name": "name",
                        "events": [
                            {
                                "type": "XrayDetection",
                                "name": "name",
                                "offset": 0.0,
                                "duration": 0.0,
                                "period": 0.0,
                                "repetition": 0.0,
                            },
                        ],
                    },
                ],
            }

            # example passing only required values which don't have defaults set
            try:
                # Create Datacollection
                api_response = api_instance.create_datacollection(
                    ssx_data_collection_create
                )
                import pprint

                pprint.pprint(api_response)
            except pyispyb_client.ApiException as e:
                print(
                    "Exception when calling SerialCrystallographyApi->create_datacollection: %s\n"
                    % e
                )

    def create_ssx_collection(
        self, data_path, collection_parameters, beamline_parameters, extra_lims_values
    ):
        try:
            fpath = os.path.abspath(os.path.join(data_path + "../", "ispyb_data.json"))

            if os.path.exists(fpath):
                with open(fpath, "r+") as _f:
                    data = json.loads(fpath.read())
                    dcg_id = data["dcg_id"]
            else:
                dcg_id = self.create_ssx_data_collection_group(collection_parameters)

                with open(fpath, "w+") as _f:
                    data = {"dcg_id": dcg_id}
                    str_data = json.dumps(data, indent=4)
                    _f.write(str_data)

                self.create_ssx_data_collection(
                    dcg_id,
                    collection_parameters,
                    beamline_parameters,
                    extra_lims_values,
                )
        except Exception:
            logging.getLogger("HWR").exception("")
