import time
from mxcubecore.utils import pyispyb_client
from datetime import datetime
from pprint import pprint
from mxcubecore.utils.pyispyb_client.api import authentication_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.login import Login
from mxcubecore.utils.pyispyb_client.model.token_response import TokenResponse

from mxcubecore.utils.pyispyb_client.model.ssx_data_collection_create import SSXDataCollectionCreate
from mxcubecore.utils.pyispyb_client.model.ssx_data_collection_group_create import SSXDataCollectionGroupCreate
from mxcubecore.utils.pyispyb_client.model.ssx_sample_create import SSXSampleCreate
from mxcubecore.utils.pyispyb_client.model.ssx_crystal_create import SSXCrystalCreate
from mxcubecore.utils.pyispyb_client.model.ssx_protein_create import SSXProteinCreate
from mxcubecore.utils.pyispyb_client.model.ssx_sample_component_create import SSXSampleComponentCreate

from mxcubecore.utils.pyispyb_client.api import serial_crystallography_api

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://py-ispyb-development:8000"
)

TOKEN = None


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = authentication_api.AuthenticationApi(api_client)
    login = Login(
        plugin="dummy",
        username="mxcube_service",
        password="dummy",
        #token="token_example",
    ) # Login | 

    try:
        # Login
        api_response = api_instance.login_ispyb_api_v1_auth_login_post(login)
        pprint(api_response)
        TOKEN = api_response.get("token")
    except pyispyb_client.ApiException as e:
        print("Exception when calling AuthenticationApi->login_ispyb_api_v1_auth_login_post: %s\n" % e)


# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    host = "http://py-ispyb-development:8000",
    access_token = TOKEN
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    ssx_data_collection_group_create = SSXDataCollectionGroupCreate(
        session_id=1,
        start_time=datetime.now(),
        end_time=datetime.now(),
        experiment_type="SSXChip",
        comments="comments_example",
        sample=SSXSampleCreate(
            name="name_example",
            support="support_example",
            crystal=SSXCrystalCreate(
                size_x=3.14,
                size_y=3.14,
                size_z=3.14,
                abundance=3.14,
                protein=SSXProteinCreate(
                    name="name_example",
                    acronym="acronym_example",
                ),
                components=[
                    SSXSampleComponentCreate(
                        name="name_example",
                        component_type="Ligand",
                        composition="composition_example",
                        abundance=3.14,
                    ),
                ],
            ),
            components=[
                SSXSampleComponentCreate(
                    name="name_example",
                    component_type="Ligand",
                    composition="composition_example",
                    abundance=3.14,
                ),
            ],
        ),
    ) # SSXDataCollectionGroupCreate | 

    # example passing only required values which don't have defaults set
    try:
        # Create Datacollectiongroup
        api_response = api_instance.create_datacollectiongroup(ssx_data_collection_group_create)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->create_datacollectiongroup: %s\n" % e)