# pyispyb_client.AuthenticationApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**login_ispyb_api_v1_auth_login_post**](AuthenticationApi.md#login_ispyb_api_v1_auth_login_post) | **POST** /ispyb/api/v1/auth/login | Login


# **login_ispyb_api_v1_auth_login_post**
> TokenResponse login_ispyb_api_v1_auth_login_post(login)

Login

Login a user

### Example


```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import authentication_api
from mxcubecore.utils.pyispyb_client.model.login import Login
from mxcubecore.utils.pyispyb_client.model.http_validation_error import HTTPValidationError
from mxcubecore.utils.pyispyb_client.model.token_response import TokenResponse
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = pyispyb_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with pyispyb_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = authentication_api.AuthenticationApi(api_client)
    login = Login(
        plugin="plugin_example",
        username="username_example",
        password="password_example",
        token="token_example",
    ) # Login | 

    # example passing only required values which don't have defaults set
    try:
        # Login
        api_response = api_instance.login_ispyb_api_v1_auth_login_post(login)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling AuthenticationApi->login_ispyb_api_v1_auth_login_post: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **login** | [**Login**](Login.md)|  |

### Return type

[**TokenResponse**](TokenResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**401** | Could not login user |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

