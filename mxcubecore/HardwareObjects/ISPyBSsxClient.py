"""
A client for ISPyB Webservices.
"""
import logging
import json
import cgi

from datetime import datetime
from requests import post, get
from urllib.parse import urljoin
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR

_CONNECTION_ERROR_MSG = (
    "Could not connect to ISPyB, please verify that "
    + "the server is running and that your "
    + "configuration is correct"
)
_NO_TOKEN_MSG = "Could not connect to ISPyB, no valid REST token available."


class ISPyBSsxClient(HardwareObject):
    """
    RESTful Web-service client for EXI.
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.__disabled = False
        self.__rest_root = None
        self.__rest_username = None
        self.__rest_token = None
        self.__rest_token_timestamp = None

    def init(self):
        logging.getLogger("requests").setLevel(logging.WARNING)
        self.__rest_root = self.get_property("restRoot").strip()
        self.__rest_username = self.get_property("restUserName").strip()
        self.__rest_password = self.get_property("restPass").strip()
        self.__update_rest_token()

    def get_login_type(self):
        return "user"

    def __update_rest_token(self):
        """
        Updates REST token if necessary by default token expires in 3h so we
        are checking the timestamp of the tocken and if it is older than 3h we
        update the rest token
        """
        request_token = False
        if not self.__rest_token_timestamp:
            request_token = True
        else:
            timedelta = datetime.now() - self.__rest_token_timestamp
            if timedelta.seconds > (3 * 60 * 60):
                request_token = True

        if request_token:
            self.authenticate(self.__rest_username, self.__rest_password)

    def authenticate(self, user, password):
        """
        Authenticate with RESTfull services, updates the authentication token,
        username and password used internally by this object.

        :param str user: Username
        :param str password: Password
        :returns: None

        """
        auth_url = self.__rest_root + "/auth/login"
        try:
            response = get(auth_url, auth=(user, password))
            self.__rest_token = response.json().get("token")
            self.__rest_token_timestamp = datetime.now()
            self.__rest_username = user
            self.__rest_password = password
        except Exception as ex:
            msg = "POST to %s failed reason %s" % (auth_url, str(ex))
            logging.getLogger("ispyb_client").exception(msg)

    def get_loaded_samples(self, proposal):
        self.__update_rest_token()
        if self.__rest_token:
            if True:
                url = self.__rest_root + "/samples"
                headers = {"Authorization": "Bearer " + self.__rest_token}
                response = get(url, headers=headers)
                return response.json()["data"]["rows"]
        else:
            logging.getLogger("ispyb_client").exception(_NO_TOKEN_MSG)
        return result

    def get_loaded_sample_info(self, loaded_sample_id):
        self.__update_rest_token()
        if self.__rest_token:
            if True:
                url = self.__rest_root + "/samples/" + str(loaded_sample_id) + "/info"
                headers = {"Authorization": "Bearer " + self.__rest_token}
                response = get(url, headers=headers)
                print(response.json())
                return response.json()
        else:
            logging.getLogger("ispyb_client").exception(_NO_TOKEN_MSG)
        return result

