"""
A client for PyISPyB Webservices.
"""
import logging
import datetime

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR

from mxcubecore.utils import pyispyb_client

from mxcubecore.utils.pyispyb_client.api import authentication_api
from mxcubecore.utils.pyispyb_client.model.login import Login

from mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.ssx_data_collection_create import (
    SSXDataCollectionCreate,
)
from mxcubecore.utils.pyispyb_client.model.ssx_data_collection_group_create import (
    SSXDataCollectionGroupCreate,
)
from mxcubecore.utils.pyispyb_client.model.ssx_sample_create import SSXSampleCreate
from mxcubecore.utils.pyispyb_client.model.ssx_crystal_create import SSXCrystalCreate
from mxcubecore.utils.pyispyb_client.model.ssx_protein_create import SSXProteinCreate
from mxcubecore.utils.pyispyb_client.model.ssx_sample_component_create import (
    SSXSampleComponentCreate,
)
from mxcubecore.utils.pyispyb_client.model.ssx_sequence_create import SSXSequenceCreate
from mxcubecore.utils.pyispyb_client.model.ssx_sequence_event_create import (
    SSXSequenceEventCreate,
)


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
        self._plugin = self.get_property("password", "").strip()
        self._host = self.get_property("host", "").strip()

        self._configuration = pyispyb_client.Configuration(
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
            self.authenticate()

    def authenticate(self):
        with pyispyb_client.ApiClient(self._configuration) as api_client:
            api_instance = authentication_api.AuthenticationApi(api_client)

            login = Login(
                plugin=self._plugin, username=self._username, password=self._password
            )

            try:
                api_response = api_instance.login_ispyb_api_v1_auth_login_post(login)

                self._configuration = pyispyb_client.Configuration(
                    host=self._host,
                    access_token=api_response.get("token"),
                )
            except pyispyb_client.ApiException as e:
                print(
                    "Exception when calling AuthenticationApi->login_ispyb_api_v1_auth_login_post: %s\n"
                    % e
                )

    def create_ssx_data_collection_group(self, session_id=None):
        self._update_token()

        session_id = session_id if session_id else int(HWR.beamline.session.session_id)

        with pyispyb_client.ApiClient(self._configuration) as api_client:
            # Create an instance of the API class
            api_instance = serial_crystallography_api.SerialCrystallographyApi(
                api_client
            )
            ssx_data_collection_group_create = SSXDataCollectionGroupCreate(
                session_id=session_id,
                start_time=datetime.datetime.now(),
                end_time=datetime.datetime.now(),
                experiment_type="SSXChip",
                comments="comments_example",
                sample=SSXSampleCreate(
                    name="name",
                    support="support_example",
                    crystal=SSXCrystalCreate(
                        size_x=-1.0,
                        size_y=-1.0,
                        size_z=-1.0,
                        abundance=-1.0,
                        protein=SSXProteinCreate(
                            name="name",
                            acronym="acronym_example",
                        ),
                        components=[
                            SSXSampleComponentCreate(
                                name="name",
                                component_type="Ligand",
                                composition="composition_example",
                                abundance=-1.0,
                            ),
                        ],
                    ),
                    components=[
                        SSXSampleComponentCreate(
                            name="name",
                            component_type="Ligand",
                            composition="composition_example",
                            abundance=-1.0,
                        ),
                    ],
                ),
            )

            try:
                api_response = api_instance.create_datacollectiongroup(
                    ssx_data_collection_group_create
                )
                # pprint.pprint(api_response)
                return api_response
            except pyispyb_client.ApiException as e:
                print(
                    "Exception when calling SerialCrystallographyApi->create_datacollectiongroup: %s\n"
                    % e
                )

    def create_ssx_data_collection(
        self, dcg, collection_parameters, beamline_parameters
    ):
        # Enter a context with an instance of the API client
        with pyispyb_client.ApiClient(self._configuration) as api_client:
            # Create an instance of the API class
            api_instance = serial_crystallography_api.SerialCrystallographyApi(
                api_client
            )
            ssx_data_collection_create = SSXDataCollectionCreate(
                session_id=HWR.beamline.session.session_id,
                data_collection_group_id=dcg.data_collection_group_id,
                exposure_time=collection_parameters.user_collection_parameters.exp_time,
                transmission=beamline_parameters.transmission,
                flux=0.0,
                x_beam=beamline_parameters.beam_x,
                y_beam=beamline_parameters.beam_y,
                wavelength=beamline_parameters.wavelength,
                detector_distance=beamline_parameters.detector_distance,
                beam_size_at_sample_x=0.0,
                beam_size_at_sample_y=0.0,
                average_temperature=0.0,
                xtal_snapshot_full_path1="",
                xtal_snapshot_full_path2="",
                xtal_snapshot_full_path3="",
                xtal_snapshot_full_path4="",
                image_prefix=collection_parameters.path_parameters.prefix,
                number_of_passes=1,
                number_of_images=collection_parameters.user_collection_parameters.num_images,
                resolution=beamline_parameters.resolution,
                resolution_at_corner=0.0,
                flux_end=0.0,
                detector_id=1,
                start_time=datetime.datetime.now(),
                end_time=datetime.datetime.now(),
                repetition_rate=0.0,
                energy_bandwidth=0.0,
                mono_stripe="mono_stripe_example",
                sequences=[
                    SSXSequenceCreate(
                        name="name",
                        events=[
                            SSXSequenceEventCreate(
                                type="XrayDetection",
                                name="name",
                                time=datetime.datetime.now(),
                                duration=0.0,
                                period=0.0,
                                repetition=0.0,
                            ),
                        ],
                    ),
                ],
            )  # SSXDataCollectionCreate |

            # example passing only required values which don't have defaults set
            try:
                # Create Datacollection
                api_response = api_instance.create_datacollection(
                    ssx_data_collection_create
                )
                # pprint.pprint(api_response)
            except pyispyb_client.ApiException as e:
                print(
                    "Exception when calling SerialCrystallographyApi->create_datacollection: %s\n"
                    % e
                )

    def create_ssx_collection(self, collection_parameters, beamline_parameters):
        try:
            dcg = self.create_ssx_data_collection_group()
            self.create_ssx_data_collection(
                dcg, collection_parameters, beamline_parameters
            )
        except Exception:
            logging.getLogger("HWR").exception("")
