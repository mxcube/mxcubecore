# pyispyb_client.SessionApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_session**](SessionApi.md#get_session) | **GET** /ispyb/api/v1/session/{sessionId} | Get Session


# **get_session**
> SessionResponse get_session(session_id)

Get Session

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import session_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.session_response import SessionResponse
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
    api_instance = session_api.SessionApi(api_client)
    session_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Session
        api_response = api_instance.get_session(session_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SessionApi->get_session: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **int**|  |

### Return type

[**SessionResponse**](SessionResponse.md)

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

