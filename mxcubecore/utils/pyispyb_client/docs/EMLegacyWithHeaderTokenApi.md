# pyispyb_client.EMLegacyWithHeaderTokenApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_classification**](EMLegacyWithHeaderTokenApi.md#get_classification) | **GET** /ispyb/api/v1/em/session/{session_id}/classification | Get Classification
[**get_ctf_thumbnail**](EMLegacyWithHeaderTokenApi.md#get_ctf_thumbnail) | **GET** /ispyb/api/v1/em/proposal/{proposal_id}/movie/{movie_id}/thumbnail/ctf | Get Ctf Thumbnail
[**get_groups_for_session**](EMLegacyWithHeaderTokenApi.md#get_groups_for_session) | **GET** /ispyb/api/v1/em/proposal/{proposal_id}/session/{session_id}/data_collections/groups | Get Groups For Session
[**get_motion_drift_thumbnail**](EMLegacyWithHeaderTokenApi.md#get_motion_drift_thumbnail) | **GET** /ispyb/api/v1/em/proposal/{proposal_id}/movie/{movie_id}/plot/motioncorrectiondrift | Get Motion Drift Thumbnail
[**get_motion_thumbnail**](EMLegacyWithHeaderTokenApi.md#get_motion_thumbnail) | **GET** /ispyb/api/v1/em/proposal/{proposal_id}/movie/{movie_id}/thumbnail/motioncorrection | Get Motion Thumbnail
[**get_movie_thumbnail**](EMLegacyWithHeaderTokenApi.md#get_movie_thumbnail) | **GET** /ispyb/api/v1/em/proposal/{proposal_id}/movie/{movie_id}/thumbnail | Get Movie Thumbnail
[**get_movies**](EMLegacyWithHeaderTokenApi.md#get_movies) | **GET** /ispyb/api/v1/em/proposal/{proposal_id}/datacollection/{datacollection_id}/movies | Get Movies
[**get_stats_dcids**](EMLegacyWithHeaderTokenApi.md#get_stats_dcids) | **GET** /ispyb/api/v1/em/proposal/{proposal_id}/data_collections/{data_collections_ids}/stats | Get Stats Dcids
[**get_stats_group**](EMLegacyWithHeaderTokenApi.md#get_stats_group) | **GET** /ispyb/api/v1/em/proposal/{proposal_id}/data_collections_group/{data_collections_group_id}/stats | Get Stats Group
[**get_stats_session**](EMLegacyWithHeaderTokenApi.md#get_stats_session) | **GET** /ispyb/api/v1/em/session/{session_id}/stats | Get Stats Session


# **get_classification**
> bool, date, datetime, dict, float, int, list, str, none_type get_classification(session_id, _self, kwargs)

Get Classification

Get classification for session.  Args:     session_id (str): session id

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import em_legacy_with_header_token_api
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
    api_instance = em_legacy_with_header_token_api.EMLegacyWithHeaderTokenApi(api_client)
    session_id = "session_id_example" # str | 
    _self = None # bool, date, datetime, dict, float, int, list, str, none_type | 
    kwargs = None # bool, date, datetime, dict, float, int, list, str, none_type | 

    # example passing only required values which don't have defaults set
    try:
        # Get Classification
        api_response = api_instance.get_classification(session_id, _self, kwargs)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EMLegacyWithHeaderTokenApi->get_classification: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **str**|  |
 **_self** | **bool, date, datetime, dict, float, int, list, str, none_type**|  |
 **kwargs** | **bool, date, datetime, dict, float, int, list, str, none_type**|  |

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

# **get_ctf_thumbnail**
> bool, date, datetime, dict, float, int, list, str, none_type get_ctf_thumbnail(movie_id, proposal_id)

Get Ctf Thumbnail

Get CTF thumbnail for movie.  Args:     proposal_id (str): proposal id or name     movie_id (str): movie id

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import em_legacy_with_header_token_api
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
    api_instance = em_legacy_with_header_token_api.EMLegacyWithHeaderTokenApi(api_client)
    movie_id = 1 # int | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Ctf Thumbnail
        api_response = api_instance.get_ctf_thumbnail(movie_id, proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EMLegacyWithHeaderTokenApi->get_ctf_thumbnail: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **movie_id** | **int**|  |
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

# **get_groups_for_session**
> bool, date, datetime, dict, float, int, list, str, none_type get_groups_for_session(proposal_id, session_id)

Get Groups For Session

Get datacollection groups for session.  Args:     proposal_id (str): proposal id or name     session_id (str): session id

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import em_legacy_with_header_token_api
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
    api_instance = em_legacy_with_header_token_api.EMLegacyWithHeaderTokenApi(api_client)
    proposal_id = "proposal_id_example" # str | 
    session_id = "session_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Groups For Session
        api_response = api_instance.get_groups_for_session(proposal_id, session_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EMLegacyWithHeaderTokenApi->get_groups_for_session: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **proposal_id** | **str**|  |
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

# **get_motion_drift_thumbnail**
> bool, date, datetime, dict, float, int, list, str, none_type get_motion_drift_thumbnail(movie_id, proposal_id)

Get Motion Drift Thumbnail

Get motion correction drift thumbnail for movie.  Args:     proposal_id (str): proposal id or name     movie_id (str): movie id

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import em_legacy_with_header_token_api
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
    api_instance = em_legacy_with_header_token_api.EMLegacyWithHeaderTokenApi(api_client)
    movie_id = 1 # int | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Motion Drift Thumbnail
        api_response = api_instance.get_motion_drift_thumbnail(movie_id, proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EMLegacyWithHeaderTokenApi->get_motion_drift_thumbnail: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **movie_id** | **int**|  |
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

# **get_motion_thumbnail**
> bool, date, datetime, dict, float, int, list, str, none_type get_motion_thumbnail(movie_id, proposal_id)

Get Motion Thumbnail

Get motion correction thumbnail for movie.  Args:     proposal_id (str): proposal id or name     movie_id (str): movie id

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import em_legacy_with_header_token_api
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
    api_instance = em_legacy_with_header_token_api.EMLegacyWithHeaderTokenApi(api_client)
    movie_id = 1 # int | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Motion Thumbnail
        api_response = api_instance.get_motion_thumbnail(movie_id, proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EMLegacyWithHeaderTokenApi->get_motion_thumbnail: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **movie_id** | **int**|  |
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

# **get_movie_thumbnail**
> bool, date, datetime, dict, float, int, list, str, none_type get_movie_thumbnail(movie_id, proposal_id)

Get Movie Thumbnail

Get thumbnails for movie.  Args:     proposal_id (str): proposal id or name     movie_id (str): movie id

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import em_legacy_with_header_token_api
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
    api_instance = em_legacy_with_header_token_api.EMLegacyWithHeaderTokenApi(api_client)
    movie_id = 1 # int | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Movie Thumbnail
        api_response = api_instance.get_movie_thumbnail(movie_id, proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EMLegacyWithHeaderTokenApi->get_movie_thumbnail: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **movie_id** | **int**|  |
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

# **get_movies**
> bool, date, datetime, dict, float, int, list, str, none_type get_movies(datacollection_id, proposal_id)

Get Movies

Get movies date for datacollection.  Args:     proposal_id (str): proposal id or name     datacollection_id (str): data collection id

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import em_legacy_with_header_token_api
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
    api_instance = em_legacy_with_header_token_api.EMLegacyWithHeaderTokenApi(api_client)
    datacollection_id = 1 # int | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Movies
        api_response = api_instance.get_movies(datacollection_id, proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EMLegacyWithHeaderTokenApi->get_movies: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **datacollection_id** | **int**|  |
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

# **get_stats_dcids**
> bool, date, datetime, dict, float, int, list, str, none_type get_stats_dcids(data_collections_ids, proposal_id)

Get Stats Dcids

Get stats for data collection ids.  Args:     proposal_id (str): proposal id or name     data_collections_ids (str): comma-separated datacollection ids

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import em_legacy_with_header_token_api
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
    api_instance = em_legacy_with_header_token_api.EMLegacyWithHeaderTokenApi(api_client)
    data_collections_ids = "data_collections_ids_example" # str | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Stats Dcids
        api_response = api_instance.get_stats_dcids(data_collections_ids, proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EMLegacyWithHeaderTokenApi->get_stats_dcids: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collections_ids** | **str**|  |
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

# **get_stats_group**
> bool, date, datetime, dict, float, int, list, str, none_type get_stats_group(data_collections_group_id, proposal_id)

Get Stats Group

Get stats for datacollection group.  Args:     proposal_id (str): proposal id or name     data_collections_group_id (str): data collection group id

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import em_legacy_with_header_token_api
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
    api_instance = em_legacy_with_header_token_api.EMLegacyWithHeaderTokenApi(api_client)
    data_collections_group_id = 1 # int | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Stats Group
        api_response = api_instance.get_stats_group(data_collections_group_id, proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EMLegacyWithHeaderTokenApi->get_stats_group: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collections_group_id** | **int**|  |
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

# **get_stats_session**
> bool, date, datetime, dict, float, int, list, str, none_type get_stats_session(session_id)

Get Stats Session

Get stats for session.  Args:     session_id (str): session id

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import em_legacy_with_header_token_api
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
    api_instance = em_legacy_with_header_token_api.EMLegacyWithHeaderTokenApi(api_client)
    session_id = "session_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Stats Session
        api_response = api_instance.get_stats_session(session_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling EMLegacyWithHeaderTokenApi->get_stats_session: %s\n" % e)
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

