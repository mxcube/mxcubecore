# pyispyb_client.EventsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_datacollection_image**](EventsApi.md#get_datacollection_image) | **GET** /ispyb/api/v1/events/image/{dataCollectionId} | Get Datacollection Image
[**get_events**](EventsApi.md#get_events) | **GET** /ispyb/api/v1/events/ | Get Events


# **get_datacollection_image**
> get_datacollection_image(data_collection_id)

Get Datacollection Image

Get a data collection image

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import events_api
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
    api_instance = events_api.EventsApi(api_client)
    data_collection_id = 1 # int | 
    image_id = 0 # int | Image 1-4 to return (optional) if omitted the server will use the default value of 0
    snapshot = False # bool | Get snapshot image (optional) if omitted the server will use the default value of False

    # example passing only required values which don't have defaults set
    try:
        # Get Datacollection Image
        api_instance.get_datacollection_image(data_collection_id)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EventsApi->get_datacollection_image: %s\n" % e)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        # Get Datacollection Image
        api_instance.get_datacollection_image(data_collection_id, image_id=image_id, snapshot=snapshot)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EventsApi->get_datacollection_image: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collection_id** | **int**|  |
 **image_id** | **int**| Image 1-4 to return | [optional] if omitted the server will use the default value of 0
 **snapshot** | **bool**| Get snapshot image | [optional] if omitted the server will use the default value of False

### Return type

void (empty response body)

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

# **get_events**
> PaginatedEvent get_events()

Get Events

Get a list of events

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import events_api
from mxcubecore.utils.pyispyb_client.model.paginated_event import PaginatedEvent
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
    api_instance = events_api.EventsApi(api_client)
    skip = 0 # int | Results to skip (optional) if omitted the server will use the default value of 0
    limit = 25 # int | Number of results to show (optional) if omitted the server will use the default value of 25
    session = "H072888001528021798096225500850762068629-39333975650685139102691291732729478601482026" # str | Session name to filter by (optional)
    data_collection_group_id = 1 # int | Data collection group id to filter by (optional)
    bl_sample_id = 1 # int | Sample id to filter by (optional)
    protein_id = 1 # int | Protein id to filter by (optional)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        # Get Events
        api_response = api_instance.get_events(skip=skip, limit=limit, session=session, data_collection_group_id=data_collection_group_id, bl_sample_id=bl_sample_id, protein_id=protein_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EventsApi->get_events: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skip** | **int**| Results to skip | [optional] if omitted the server will use the default value of 0
 **limit** | **int**| Number of results to show | [optional] if omitted the server will use the default value of 25
 **session** | **str**| Session name to filter by | [optional]
 **data_collection_group_id** | **int**| Data collection group id to filter by | [optional]
 **bl_sample_id** | **int**| Sample id to filter by | [optional]
 **protein_id** | **int**| Protein id to filter by | [optional]

### Return type

[**PaginatedEvent**](PaginatedEvent.md)

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

