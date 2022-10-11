# pyispyb_client.LabContactsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_lab_contact**](LabContactsApi.md#create_lab_contact) | **POST** /ispyb/api/v1/labcontacts/ | Create Lab Contact
[**get_lab_contact**](LabContactsApi.md#get_lab_contact) | **GET** /ispyb/api/v1/labcontacts/{labContactId} | Get Lab Contact
[**get_lab_contacts**](LabContactsApi.md#get_lab_contacts) | **GET** /ispyb/api/v1/labcontacts/ | Get Lab Contacts


# **create_lab_contact**
> LabContact create_lab_contact(lab_contact_create)

Create Lab Contact

Create a new lab contact

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import lab_contacts_api
from mxcubecore.utils.pyispyb_client.model.lab_contact_create import LabContactCreate
from mxcubecore.utils.pyispyb_client.model.lab_contact import LabContact
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
    api_instance = lab_contacts_api.LabContactsApi(api_client)
    lab_contact_create = LabContactCreate(
        proposal_id=1,
        card_name="card_name_example",
        default_courrier_company=None,
        courier_account=None,
        billing_reference=None,
        dewar_avg_customs_value=1,
        dewar_avg_transport_value=1,
        person=Person(
            given_name="given_name_example",
            family_name="family_name_example",
            email_address=None,
            phone_number=None,
            laboratory=Laboratory(
                name="H",
                address="address_example",
                city="city_example",
                postcode="postcode_example",
                country="country_example",
            ),
        ),
    ) # LabContactCreate | 

    # example passing only required values which don't have defaults set
    try:
        # Create Lab Contact
        api_response = api_instance.create_lab_contact(lab_contact_create)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LabContactsApi->create_lab_contact: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **lab_contact_create** | [**LabContactCreate**](LabContactCreate.md)|  |

### Return type

[**LabContact**](LabContact.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_lab_contact**
> LabContact get_lab_contact(lab_contact_id)

Get Lab Contact

Get a list of lab contacts

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import lab_contacts_api
from mxcubecore.utils.pyispyb_client.model.lab_contact import LabContact
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
    api_instance = lab_contacts_api.LabContactsApi(api_client)
    lab_contact_id = 1 # int | 

    # example passing only required values which don't have defaults set
    try:
        # Get Lab Contact
        api_response = api_instance.get_lab_contact(lab_contact_id)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LabContactsApi->get_lab_contact: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **lab_contact_id** | **int**|  |

### Return type

[**LabContact**](LabContact.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | No such contact |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_lab_contacts**
> PaginatedLabContact get_lab_contacts()

Get Lab Contacts

Get a list of lab contacts

### Example

* Bearer Authentication (HTTPBearer):

```python
import time
from mxcubecore.utils import pyispyb_clientfrom mxcubecore.utils.pyispyb_client.api import lab_contacts_api
from mxcubecore.utils.pyispyb_client.model.paginated_lab_contact import PaginatedLabContact
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
    api_instance = lab_contacts_api.LabContactsApi(api_client)
    skip = 0 # int | Results to skip (optional) if omitted the server will use the default value of 0
    limit = 25 # int | Number of results to show (optional) if omitted the server will use the default value of 25

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        # Get Lab Contacts
        api_response = api_instance.get_lab_contacts(skip=skip, limit=limit)
        pprint(api_response)
    except pyispyb_client.ApiException as e:
        print("Exception when calling LabContactsApi->get_lab_contacts: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skip** | **int**| Results to skip | [optional] if omitted the server will use the default value of 0
 **limit** | **int**| Number of results to show | [optional] if omitted the server will use the default value of 25

### Return type

[**PaginatedLabContact**](PaginatedLabContact.md)

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

