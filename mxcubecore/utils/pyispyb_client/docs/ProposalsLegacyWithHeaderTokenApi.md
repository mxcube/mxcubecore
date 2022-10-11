# pyispyb_client.ProposalsLegacyWithHeaderTokenApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_proposal**](ProposalsLegacyWithHeaderTokenApi.md#get_proposal) | **GET** /ispyb/api/v1/proposals/{proposal_id} | Get Proposal
[**get_proposals**](ProposalsLegacyWithHeaderTokenApi.md#get_proposals) | **GET** /ispyb/api/v1/proposals | Get Proposals


# **get_proposal**
> bool, date, datetime, dict, float, int, list, str, none_type get_proposal(proposal_id)

Get Proposal

Get proposal information.  Args:     proposal_id (str): proposal id or name

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import proposals_legacy_with_header_token_api
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
    api_instance = proposals_legacy_with_header_token_api.ProposalsLegacyWithHeaderTokenApi(api_client)
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Proposal
        api_response = api_instance.get_proposal(proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling ProposalsLegacyWithHeaderTokenApi->get_proposal: %s\n" % e)
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

# **get_proposals**
> bool, date, datetime, dict, float, int, list, str, none_type get_proposals()

Get Proposals

Get all proposal that user is allowed to access.

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import proposals_legacy_with_header_token_api
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
    api_instance = proposals_legacy_with_header_token_api.ProposalsLegacyWithHeaderTokenApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Get Proposals
        api_response = api_instance.get_proposals()
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling ProposalsLegacyWithHeaderTokenApi->get_proposals: %s\n" % e)
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

