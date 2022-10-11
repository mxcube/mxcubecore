# pyispyb_client.SamplesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_sample**](SamplesApi.md#get_sample) | **GET** /ispyb/api/v1/samples/{blSampleId} | Get Sample
[**get_samples**](SamplesApi.md#get_samples) | **GET** /ispyb/api/v1/samples/ | Get Samples


# **get_sample**
> Sample get_sample(bl_sample_id)

Get Sample

Get a samples

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import samples_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.sample import Sample
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
    api_instance = samples_api.SamplesApi(api_client)
    bl_sample_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Sample
        api_response = api_instance.get_sample(bl_sample_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SamplesApi->get_sample: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **bl_sample_id** | **int**|  |

### Return type

[**Sample**](Sample.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | No such sample |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_samples**
> PaginatedSample get_samples()

Get Samples

Get a list of samples

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import samples_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.paginated_sample import PaginatedSample
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
    api_instance = samples_api.SamplesApi(api_client)
    skip = 0 # int | Results to skip (optional) if omitted the server will use the default value of 0
    limit = 25 # int | Number of results to show (optional) if omitted the server will use the default value of 25
    protein_id = 1 # int | Protein id to filter by (optional)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        # Get Samples
        api_response = api_instance.get_samples(skip=skip, limit=limit, protein_id=protein_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling SamplesApi->get_samples: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skip** | **int**| Results to skip | [optional] if omitted the server will use the default value of 0
 **limit** | **int**| Number of results to show | [optional] if omitted the server will use the default value of 25
 **protein_id** | **int**| Protein id to filter by | [optional]

### Return type

[**PaginatedSample**](PaginatedSample.md)

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

