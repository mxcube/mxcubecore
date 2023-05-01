"""
A client for PyISPyB Webservices.
"""
import urllib3
import logging
import datetime

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR
from mxcubecore.model.common import BeamlineParameters

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

        if HWR.beamline.session:
            self.beamline_name = HWR.beamline.session.beamline_name
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
                    # access_token=api_response.body.token,
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
                "energy": HWR.beamline.energy.get_value(),
                "wavelength": HWR.beamline.energy.get_wavelength(),
                "resolution": HWR.beamline.resolution.get_value(),
                "transmission": HWR.beamline.transmission.get_value(),
                "detector_distance": HWR.beamline.detector.distance.get_value(),
                "beam_x": HWR.beamline.detector.get_beam_position()[0],
                "beam_y": HWR.beamline.detector.get_beam_position()[1],
            }
        )

    def create_ssx_data_collection_group(self, session_id=None):
        self._update_token()

        session_id = session_id if session_id else int(HWR.beamline.session.session_id)

        with pyispyb_client.ApiClient(self._configuration) as api_client:
            # Create an instance of the API class
            api_instance = webservices_serial_crystallography_api.WebservicesSerialCrystallographyApi(
                api_client
            )
            ssx_data_collection_group_create = {
                "sessionId": session_id,
                "startTime": datetime.datetime.now(),
                "endTime": datetime.datetime.now(),
                "experimentType": "SSX-Chip",
                "experimentName": "SSX-Chip experiment",
                "comments": "comments_example",
                "sample": {
                    "name": "name",
                    "support": "support_example",
                    "crystal": {
                        "size_X": -1.0,
                        "size_Y": -1.0,
                        "size_Z": -1.0,
                        "abundance": -1.0,
                        "protein": {
                            "name": "name",
                            "acronym": "acronym_example",
                        },
                        "components": [
                            {
                                "name": "name",
                                "componentType": "Ligand",
                                "composition": "composition_example",
                                "abundance": -1.0,
                            },
                        ],
                    },
                    "components": [
                        {
                            "name": "name",
                            "componentType": "Ligand",
                            "composition": "composition_example",
                            "abundance": -1.0,
                        },
                    ],
                },
            }

            try:
                api_response = api_instance.create_datacollectiongroup(
                    ssx_data_collection_group_create
                )
                # pprint.pprint(api_response)
                return api_response.body
            except pyispyb_client.ApiException as e:
                print(
                    "Exception when calling SerialCrystallographyApi->create_datacollectiongroup: %s\n"
                    % e
                )

    def create_ssx_data_collection(
        self, dcg_id, collection_parameters, beamline_parameters
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
                "flux": 0.0,
                "xBeam": beamline_parameters.beam_x,
                "yBeam": beamline_parameters.beam_y,
                "wavelength": beamline_parameters.wavelength,
                "detectorDistance": beamline_parameters.detector_distance,
                "beamSizeAtSampleX": 0.0,
                "beamSizeAtSampleY": 0.0,
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
                "flux_end": 0.0,
                "detector_id": 4,
                "startTime": datetime.datetime.now(),
                "endTime": datetime.datetime.now(),
                "repetitionTate": 0.0,
                "energyBandwidth": 0.0,
                "monoStripe": "mono_stripe_example",
                "jetSize": 0,
                "jetSpeed": 0,
                "laserEnergy": 0,
                "chipModel": "",
                "chipPattern": "",
                "beamShape": "",
                "polarisation": 0,
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

    def create_ssx_collection(self, collection_parameters, beamline_parameters):
        return
        try:
            dcg = self.create_ssx_data_collection_group()
            self.create_ssx_data_collection(
                dcg, collection_parameters, beamline_parameters
            )
        except Exception:
            logging.getLogger("HWR").exception("")
