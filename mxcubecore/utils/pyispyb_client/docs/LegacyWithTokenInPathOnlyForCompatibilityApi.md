# pyispyb_client.LegacyWithTokenInPathOnlyForCompatibilityApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_classification_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_classification_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/{proposal_id}/em/session/{session_id}/classification | Get Classification
[**get_ctf_thumbnail_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_ctf_thumbnail_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/{proposal_id}/em/datacollection/{datacollection_id}/movie/{movie_id}/ctf/thumbnail | Get Ctf Thumbnail
[**get_groups_for_session_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_groups_for_session_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/{proposal_id}/em/datacollection/session/{session_id}/list | Get Groups For Session
[**get_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/session/{session_id}/list | Get
[**get_motion_drift_thumbnail_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_motion_drift_thumbnail_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/{proposal_id}/em/datacollection/{datacollection_id}/movie/{movie_id}/motioncorrection/drift | Get Motion Drift Thumbnail
[**get_motion_thumbnail_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_motion_thumbnail_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/{proposal_id}/em/datacollection/{datacollection_id}/movie/{movie_id}/motioncorrection/thumbnail | Get Motion Thumbnail
[**get_movie_thumbnail_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_movie_thumbnail_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/{proposal_id}/em/datacollection/{datacollection_id}/movie/{movie_id}/thumbnail | Get Movie Thumbnail
[**get_movies_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_movies_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/{proposal_id}/em/datacollection/{datacollection_id}/movie/all | Get Movies
[**get_proposal_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_proposal_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/{proposal_id}/info/get | Get Proposal
[**get_proposals_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_proposals_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/list | Get Proposals
[**get_sessions_by_dates_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_sessions_by_dates_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/session/date/{start_date}/{end_date}/list | Get Sessions By Dates
[**get_sessions_for_proposal_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_sessions_for_proposal_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/{proposal_id}/session/list | Get Sessions For Proposal
[**get_sessions_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_sessions_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/session/list | Get Sessions
[**get_stats_dcids_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_stats_dcids_legacy_token) | **GET** /ispyb/api/v1/legacy/proposal/{proposal_id}/data_collections/{data_collections_ids}/stats | Get Stats Dcids
[**get_stats_group_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_stats_group_legacy_token) | **GET** /ispyb/api/v1/legacy/proposal/{proposal_id}/data_collections_group/{data_collections_group_id}/stats | Get Stats Group
[**get_stats_session_legacy_token**](LegacyWithTokenInPathOnlyForCompatibilityApi.md#get_stats_session_legacy_token) | **GET** /ispyb/api/v1/legacy/{token}/proposal/{proposal}/em/session/{session_id}/stats | Get Stats Session


# **get_classification_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_classification_legacy_token(token, session_id, _self, kwargs)

Get Classification

Get classification for session.  Args:     session_id (str): session id

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    token = "token_example" # str | 
    session_id = "session_id_example" # str | 
    _self = None # bool, date, datetime, dict, float, int, list, str, none_type | 
    kwargs = None # bool, date, datetime, dict, float, int, list, str, none_type | 

    # example passing only required values which don't have defaults set
    try:
        # Get Classification
        api_response = api_instance.get_classification_legacy_token(token, session_id, _self, kwargs)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_classification_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **token** | **str**|  |
 **session_id** | **str**|  |
 **_self** | **bool, date, datetime, dict, float, int, list, str, none_type**|  |
 **kwargs** | **bool, date, datetime, dict, float, int, list, str, none_type**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_ctf_thumbnail_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_ctf_thumbnail_legacy_token(movie_id, token, proposal_id)

Get Ctf Thumbnail

Get CTF thumbnail for movie.  Args:     proposal_id (str): proposal id or name     movie_id (str): movie id

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    movie_id = 1 # int | 
    token = "token_example" # str | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Ctf Thumbnail
        api_response = api_instance.get_ctf_thumbnail_legacy_token(movie_id, token, proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_ctf_thumbnail_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **movie_id** | **int**|  |
 **token** | **str**|  |
 **proposal_id** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_groups_for_session_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_groups_for_session_legacy_token(token, proposal_id, session_id)

Get Groups For Session

Get datacollection groups for session.  Args:     proposal_id (str): proposal id or name     session_id (str): session id

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    token = "token_example" # str | 
    proposal_id = "proposal_id_example" # str | 
    session_id = "session_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Groups For Session
        api_response = api_instance.get_groups_for_session_legacy_token(token, proposal_id, session_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_groups_for_session_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **token** | **str**|  |
 **proposal_id** | **str**|  |
 **session_id** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_legacy_token(token, session_id)

Get

Get data collection groups for session.  Args:     session_id (str): session id

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    token = "token_example" # str | 
    session_id = "session_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get
        api_response = api_instance.get_legacy_token(token, session_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **token** | **str**|  |
 **session_id** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_motion_drift_thumbnail_legacy_token**
> get_motion_drift_thumbnail_legacy_token(movie_id, token, proposal_id)

Get Motion Drift Thumbnail

Get motion correction drift thumbnail for movie.  Args:     proposal_id (str): proposal id or name     movie_id (str): movie id

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    movie_id = 1 # int | 
    token = "token_example" # str | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Motion Drift Thumbnail
        api_instance.get_motion_drift_thumbnail_legacy_token(movie_id, token, proposal_id)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_motion_drift_thumbnail_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **movie_id** | **int**|  |
 **token** | **str**|  |
 **proposal_id** | **str**|  |

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_motion_thumbnail_legacy_token**
> get_motion_thumbnail_legacy_token(movie_id, token, proposal_id)

Get Motion Thumbnail

Get motion correction thumbnail for movie.  Args:     proposal_id (str): proposal id or name     movie_id (str): movie id

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    movie_id = 1 # int | 
    token = "token_example" # str | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Motion Thumbnail
        api_instance.get_motion_thumbnail_legacy_token(movie_id, token, proposal_id)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_motion_thumbnail_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **movie_id** | **int**|  |
 **token** | **str**|  |
 **proposal_id** | **str**|  |

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_movie_thumbnail_legacy_token**
> get_movie_thumbnail_legacy_token(movie_id, token, proposal_id)

Get Movie Thumbnail

Get thumbnails for movie.  Args:     proposal_id (str): proposal id or name     movie_id (str): movie id

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    movie_id = 1 # int | 
    token = "token_example" # str | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Movie Thumbnail
        api_instance.get_movie_thumbnail_legacy_token(movie_id, token, proposal_id)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_movie_thumbnail_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **movie_id** | **int**|  |
 **token** | **str**|  |
 **proposal_id** | **str**|  |

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_movies_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_movies_legacy_token(datacollection_id, token, proposal_id)

Get Movies

Get movies date for datacollection.  Args:     proposal_id (str): proposal id or name     datacollection_id (str): data collection id

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    datacollection_id = 1 # int | 
    token = "token_example" # str | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Movies
        api_response = api_instance.get_movies_legacy_token(datacollection_id, token, proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_movies_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **datacollection_id** | **int**|  |
 **token** | **str**|  |
 **proposal_id** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_proposal_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_proposal_legacy_token(token, proposal_id)

Get Proposal

Get proposal information.  Args:     proposal_id (str): proposal id or name

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    token = "token_example" # str | 
    proposal_id = "proposal_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Proposal
        api_response = api_instance.get_proposal_legacy_token(token, proposal_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_proposal_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **token** | **str**|  |
 **proposal_id** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_proposals_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_proposals_legacy_token(token)

Get Proposals

Get all proposal that user is allowed to access.

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    token = "token_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Proposals
        api_response = api_instance.get_proposals_legacy_token(token)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_proposals_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **token** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_sessions_by_dates_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_sessions_by_dates_legacy_token(start_date, end_date, token)

Get Sessions By Dates

Get all sessions between two dates that user is allowed to access.  Args:     start_date (str): start date     end_date (str): end date

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    start_date = "start_date_example" # str | 
    end_date = "end_date_example" # str | 
    token = "token_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Sessions By Dates
        api_response = api_instance.get_sessions_by_dates_legacy_token(start_date, end_date, token)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_sessions_by_dates_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **start_date** | **str**|  |
 **end_date** | **str**|  |
 **token** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_sessions_for_proposal_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_sessions_for_proposal_legacy_token(proposal_id, token)

Get Sessions For Proposal

Get all sessions for proposal that user is allowed to access.  Args:     proposal_id (str): proposal id or name

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    proposal_id = "proposal_id_example" # str | 
    token = "token_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Sessions For Proposal
        api_response = api_instance.get_sessions_for_proposal_legacy_token(proposal_id, token)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_sessions_for_proposal_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **proposal_id** | **str**|  |
 **token** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_sessions_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_sessions_legacy_token(token)

Get Sessions

Get all sessions that user is allowed to access.

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    token = "token_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Sessions
        api_response = api_instance.get_sessions_legacy_token(token)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_sessions_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **token** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_stats_dcids_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_stats_dcids_legacy_token(data_collections_ids, proposal_id, token)

Get Stats Dcids

Get stats for data collection ids.  Args:     proposal_id (str): proposal id or name     data_collections_ids (str): comma-separated datacollection ids

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    data_collections_ids = "data_collections_ids_example" # str | 
    proposal_id = "proposal_id_example" # str | 
    token = "token_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Stats Dcids
        api_response = api_instance.get_stats_dcids_legacy_token(data_collections_ids, proposal_id, token)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_stats_dcids_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collections_ids** | **str**|  |
 **proposal_id** | **str**|  |
 **token** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_stats_group_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_stats_group_legacy_token(data_collections_group_id, proposal_id, token)

Get Stats Group

Get stats for datacollection group.  Args:     proposal_id (str): proposal id or name     data_collections_group_id (str): data collection group id

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    data_collections_group_id = 1 # int | 
    proposal_id = "proposal_id_example" # str | 
    token = "token_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Stats Group
        api_response = api_instance.get_stats_group_legacy_token(data_collections_group_id, proposal_id, token)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_stats_group_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **data_collections_group_id** | **int**|  |
 **proposal_id** | **str**|  |
 **token** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_stats_session_legacy_token**
> bool, date, datetime, dict, float, int, list, str, none_type get_stats_session_legacy_token(token, session_id)

Get Stats Session

Get stats for session.  Args:     session_id (str): session id

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import legacy_with_token_in_path_only_for_compatibility_api
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = legacy_with_token_in_path_only_for_compatibility_api.LegacyWithTokenInPathOnlyForCompatibilityApi(api_client)
    token = "token_example" # str | 
    session_id = "session_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Stats Session
        api_response = api_instance.get_stats_session_legacy_token(token, session_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LegacyWithTokenInPathOnlyForCompatibilityApi->get_stats_session_legacy_token: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **token** | **str**|  |
 **session_id** | **str**|  |

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

