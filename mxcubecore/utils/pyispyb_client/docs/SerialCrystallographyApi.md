# pyispyb_client.SerialCrystallographyApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_datacollection**](SerialCrystallographyApi.md#create_datacollection) | **POST** /ispyb/api/v1/ssx/datacollection | Create Datacollection
[**create_datacollectiongroup**](SerialCrystallographyApi.md#create_datacollectiongroup) | **POST** /ispyb/api/v1/ssx/datacollectiongroup | Create Datacollectiongroup
[**create_ssx_hits**](SerialCrystallographyApi.md#create_ssx_hits) | **POST** /ispyb/api/v1/ssx/datacollection/{dataCollectionId}/hits | Create Ssx Hits
[**get_datacollection**](SerialCrystallographyApi.md#get_datacollection) | **GET** /ispyb/api/v1/ssx/datacollection/{dataCollectionId} | Get Datacollection
[**get_datacollection_sample**](SerialCrystallographyApi.md#get_datacollection_sample) | **GET** /ispyb/api/v1/ssx/datacollection/{dataCollectionId}/sample | Get Datacollection Sample
[**get_datacollection_sequences**](SerialCrystallographyApi.md#get_datacollection_sequences) | **GET** /ispyb/api/v1/ssx/datacollection/{dataCollectionId}/sequences | Get Datacollection Sequences
[**get_datacollectiongroup**](SerialCrystallographyApi.md#get_datacollectiongroup) | **GET** /ispyb/api/v1/ssx/datacollectiongroup/{dataCollectionGroupId} | Get Datacollectiongroup
[**get_datacollectiongroup_sample**](SerialCrystallographyApi.md#get_datacollectiongroup_sample) | **GET** /ispyb/api/v1/ssx/datacollectiongroup/{dataCollectionGroupId}/sample | Get Datacollectiongroup Sample
[**get_datacollectiongroups**](SerialCrystallographyApi.md#get_datacollectiongroups) | **GET** /ispyb/api/v1/ssx/datacollectiongroup | Get Datacollectiongroups
[**get_datacollections**](SerialCrystallographyApi.md#get_datacollections) | **GET** /ispyb/api/v1/ssx/datacollection | Get Datacollections
[**get_graph_data**](SerialCrystallographyApi.md#get_graph_data) | **GET** /ispyb/api/v1/ssx/graph/{graphId}/data | Get Graph Data
[**get_graphs**](SerialCrystallographyApi.md#get_graphs) | **GET** /ispyb/api/v1/ssx/datacollection/{dataCollectionId}/graphs | Get Graphs
[**get_ssx_hits**](SerialCrystallographyApi.md#get_ssx_hits) | **GET** /ispyb/api/v1/ssx/datacollection/{dataCollectionId}/hits | Get Ssx Hits


# **create_datacollection**
> SSXDataCollectionResponse create_datacollection(ssx_data_collection_create)

Create Datacollection

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.ssx_data_collection_create import SSXDataCollectionCreate
from mxcubecore.utils.pyispyb_client.model.ssx_data_collection_response import SSXDataCollectionResponse
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    ssx_data_collection_create = SSXDataCollectionCreate(
        session_id=1,
        data_collection_group_id=1,
        exposure_time=3.14,
        transmission=3.14,
        flux=3.14,
        x_beam=3.14,
        y_beam=3.14,
        wavelength=3.14,
        detector_distance=3.14,
        beam_size_at_sample_x=3.14,
        beam_size_at_sample_y=3.14,
        average_temperature=3.14,
        xtal_snapshot_full_path1="xtal_snapshot_full_path1_example",
        xtal_snapshot_full_path2="xtal_snapshot_full_path2_example",
        xtal_snapshot_full_path3="xtal_snapshot_full_path3_example",
        xtal_snapshot_full_path4="xtal_snapshot_full_path4_example",
        image_prefix="image_prefix_example",
        number_of_passes=1,
        number_of_images=1,
        resolution=3.14,
        resolution_at_corner=3.14,
        flux_end=3.14,
        detector_id=1,
        start_time=dateutil_parser('1970-01-01T00:00:00.00Z'),
        end_time=dateutil_parser('1970-01-01T00:00:00.00Z'),
        repetition_rate=3.14,
        energy_bandwidth=3.14,
        mono_stripe="mono_stripe_example",
        sequences=[
            SSXSequenceCreate(
                name="name_example",
                events=[
                    SSXSequenceEventCreate(
                        type="XrayDetection",
                        name="name_example",
                        time=dateutil_parser('1970-01-01T00:00:00.00Z'),
                        duration=3.14,
                        period=3.14,
                        repetition=3.14,
                    ),
                ],
            ),
        ],
    ) # SSXDataCollectionCreate | 

    # example passing only required values which don't have defaults set
    try:
        # Create Datacollection
        api_response = api_instance.create_datacollection(ssx_data_collection_create)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->create_datacollection: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **ssx_data_collection_create** | [**SSXDataCollectionCreate**](SSXDataCollectionCreate.md)|  |

### Return type

[**SSXDataCollectionResponse**](SSXDataCollectionResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_datacollectiongroup**
> DataCollectionGroupResponse create_datacollectiongroup(ssx_data_collection_group_create)

Create Datacollectiongroup

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.ssx_data_collection_group_create import SSXDataCollectionGroupCreate
from mxcubecore.utils.pyispyb_client.model.data_collection_group_response import DataCollectionGroupResponse
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    ssx_data_collection_group_create = SSXDataCollectionGroupCreate(
        session_id=1,
        start_time=dateutil_parser('1970-01-01T00:00:00.00Z'),
        end_time=dateutil_parser('1970-01-01T00:00:00.00Z'),
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
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **ssx_data_collection_group_create** | [**SSXDataCollectionGroupCreate**](SSXDataCollectionGroupCreate.md)|  |

### Return type

[**DataCollectionGroupResponse**](DataCollectionGroupResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_ssx_hits**
> SSXHitsResponse create_ssx_hits(data_collection_id, ssx_hits_create)

Create Ssx Hits

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.ssx_hits_response import SSXHitsResponse
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.ssx_hits_create import SSXHitsCreate
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    data_collection_id = 1 # int | 
    ssx_hits_create = SSXHitsCreate(
        nb_hits=1,
        nb_indexed=1,
        latice_type="latice_type_example",
        estimated_resolution=3.14,
        unit_cells=[
            [
                3.14,
            ],
        ],
    ) # SSXHitsCreate | 

    # example passing only required values which don't have defaults set
    try:
        # Create Ssx Hits
        api_response = api_instance.create_ssx_hits(data_collection_id, ssx_hits_create)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->create_ssx_hits: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collection_id** | **int**|  |
 **ssx_hits_create** | [**SSXHitsCreate**](SSXHitsCreate.md)|  |

### Return type

[**SSXHitsResponse**](SSXHitsResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_datacollection**
> SSXDataCollectionResponse get_datacollection(data_collection_id)

Get Datacollection

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.ssx_data_collection_response import SSXDataCollectionResponse
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    data_collection_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Datacollection
        api_response = api_instance.get_datacollection(data_collection_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->get_datacollection: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collection_id** | **int**|  |

### Return type

[**SSXDataCollectionResponse**](SSXDataCollectionResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | Entity not found |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_datacollection_sample**
> SSXSampleResponse get_datacollection_sample(data_collection_id)

Get Datacollection Sample

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.ssx_sample_response import SSXSampleResponse
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    data_collection_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Datacollection Sample
        api_response = api_instance.get_datacollection_sample(data_collection_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->get_datacollection_sample: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collection_id** | **int**|  |

### Return type

[**SSXSampleResponse**](SSXSampleResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | Entity not found |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_datacollection_sequences**
> [SSXSequenceResponse] get_datacollection_sequences(data_collection_id)

Get Datacollection Sequences

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.ssx_sequence_response import SSXSequenceResponse
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    data_collection_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Datacollection Sequences
        api_response = api_instance.get_datacollection_sequences(data_collection_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->get_datacollection_sequences: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collection_id** | **int**|  |

### Return type

[**[SSXSequenceResponse]**](SSXSequenceResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | Entity not found |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_datacollectiongroup**
> DataCollectionGroupResponse get_datacollectiongroup(data_collection_group_id)

Get Datacollectiongroup

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.data_collection_group_response import DataCollectionGroupResponse
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    data_collection_group_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Datacollectiongroup
        api_response = api_instance.get_datacollectiongroup(data_collection_group_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->get_datacollectiongroup: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collection_group_id** | **int**|  |

### Return type

[**DataCollectionGroupResponse**](DataCollectionGroupResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_datacollectiongroup_sample**
> SSXSampleResponse get_datacollectiongroup_sample(data_collection_group_id)

Get Datacollectiongroup Sample

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.ssx_sample_response import SSXSampleResponse
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    data_collection_group_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Datacollectiongroup Sample
        api_response = api_instance.get_datacollectiongroup_sample(data_collection_group_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->get_datacollectiongroup_sample: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collection_group_id** | **int**|  |

### Return type

[**SSXSampleResponse**](SSXSampleResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | Entity not found |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_datacollectiongroups**
> [DataCollectionGroupResponse] get_datacollectiongroups(session_id)

Get Datacollectiongroups

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.data_collection_group_response import DataCollectionGroupResponse
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    session_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Datacollectiongroups
        api_response = api_instance.get_datacollectiongroups(session_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->get_datacollectiongroups: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **int**|  |

### Return type

[**[DataCollectionGroupResponse]**](DataCollectionGroupResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | Entity not found |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_datacollections**
> [SSXDataCollectionResponse] get_datacollections(session_id, data_collection_group_id)

Get Datacollections

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.ssx_data_collection_response import SSXDataCollectionResponse
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    session_id = 1 # int | 
    data_collection_group_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Datacollections
        api_response = api_instance.get_datacollections(session_id, data_collection_group_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->get_datacollections: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **int**|  |
 **data_collection_group_id** | **int**|  |

### Return type

[**[SSXDataCollectionResponse]**](SSXDataCollectionResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | Entity not found |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_graph_data**
> [GraphDataResponse] get_graph_data(graph_id)

Get Graph Data

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.graph_data_response import GraphDataResponse
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    graph_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Graph Data
        api_response = api_instance.get_graph_data(graph_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->get_graph_data: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **graph_id** | **int**|  |

### Return type

[**[GraphDataResponse]**](GraphDataResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_graphs**
> [GraphResponse] get_graphs(data_collection_id)

Get Graphs

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.graph_response import GraphResponse
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    data_collection_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Graphs
        api_response = api_instance.get_graphs(data_collection_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->get_graphs: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collection_id** | **int**|  |

### Return type

[**[GraphResponse]**](GraphResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_ssx_hits**
> SSXHitsResponse get_ssx_hits(data_collection_id)

Get Ssx Hits

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import serial_crystallography_api
from mxcubecore.utils.pyispyb_client.model.ssx_hits_response import SSXHitsResponse
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: HTTPBearer
configuration = pyispyb_client.Configuration(
    access_token = 'YOUR_BEARER_TOKEN'
)

# Enter a context with an instance of the API client
with pyispyb_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = serial_crystallography_api.SerialCrystallographyApi(api_client)
    data_collection_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Ssx Hits
        api_response = api_instance.get_ssx_hits(data_collection_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SerialCrystallographyApi->get_ssx_hits: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collection_id** | **int**|  |

### Return type

[**SSXHitsResponse**](SSXHitsResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

