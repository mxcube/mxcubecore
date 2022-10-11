# pyispyb_client.SessionsLegacyWithHeaderTokenApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_sessions**](SessionsLegacyWithHeaderTokenApi.md#get_sessions) | **GET** /ispyb/api/v1/sessions | Get Sessions
[**get_sessions_by_dates**](SessionsLegacyWithHeaderTokenApi.md#get_sessions_by_dates) | **GET** /ispyb/api/v1/sessions/date/{start_date}/{end_date} | Get Sessions By Dates
[**get_sessions_for_proposal**](SessionsLegacyWithHeaderTokenApi.md#get_sessions_for_proposal) | **GET** /ispyb/api/v1/sessions/proposal/{proposal_id} | Get Sessions For Proposal


# **get_sessions**
> bool, date, datetime, dict, float, int, list, str, none_type get_sessions()

Get Sessions

Get all sessions that user is allowed to access.

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import sessions_legacy_with_header_token_api
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
    api_instance = sessions_legacy_with_header_token_api.SessionsLegacyWithHeaderTokenApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Get Sessions
        api_response = api_instance.get_sessions()
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SessionsLegacyWithHeaderTokenApi->get_sessions: %s\n" % e)
```


### Parameters
This endpoint does not need any parameter.

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_sessions_by_dates**
> bool, date, datetime, dict, float, int, list, str, none_type get_sessions_by_dates(start_date, end_date)

Get Sessions By Dates

Get all sessions between two dates that user is allowed to access.  Args:     start_date (str): start date     end_date (str): end date

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import sessions_legacy_with_header_token_api
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
    api_instance = sessions_legacy_with_header_token_api.SessionsLegacyWithHeaderTokenApi(api_client)
    start_date = "start_date_example" # str | 
    end_date = "end_date_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Sessions By Dates
        api_response = api_instance.get_sessions_by_dates(start_date, end_date)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SessionsLegacyWithHeaderTokenApi->get_sessions_by_dates: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **start_date** | **str**|  |
 **end_date** | **str**|  |

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

# **get_sessions_for_proposal**
> bool, date, datetime, dict, float, int, list, str, none_type get_sessions_for_proposal(proposal_id)

Get Sessions For Proposal

Get all sessions for proposal that user is allowed to access.  Args:     proposal_id (str): proposal id or name

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import sessions_legacy_with_header_token_api
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
    api_instance = sessions_legacy_with_header_token_api.SessionsLegacyWithHeaderTokenApi(api_client)
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Sessions For Proposal
        api_response = api_instance.get_sessions_for_proposal(proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SessionsLegacyWithHeaderTokenApi->get_sessions_for_proposal: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **proposal_id** | **str**|  |

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

