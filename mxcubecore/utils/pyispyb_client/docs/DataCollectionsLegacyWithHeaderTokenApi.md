# pyispyb_client.DataCollectionsLegacyWithHeaderTokenApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get**](DataCollectionsLegacyWithHeaderTokenApi.md#get) | **GET** /ispyb/api/v1/data_collections/groups/session/{session_id} | Get


# **get**
> bool, date, datetime, dict, float, int, list, str, none_type get(session_id)

Get

Get data collection groups for session.  Args:     session_id (str): session id

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import data_collections_legacy_with_header_token_api
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
    api_instance = data_collections_legacy_with_header_token_api.DataCollectionsLegacyWithHeaderTokenApi(api_client)
    session_id = "session_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get
        api_response = api_instance.get(session_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling DataCollectionsLegacyWithHeaderTokenApi->get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

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

