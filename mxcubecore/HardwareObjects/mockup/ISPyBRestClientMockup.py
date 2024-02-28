"""
A client for ISPyB Webservices.
"""
from __future__ import print_function
import logging
from datetime import datetime
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR

try:
    from urlparse import urljoin
except Exception:
    # Python3
    from urllib.parse import urljoin


_CONNECTION_ERROR_MSG = (
    "Could not connect to ISPyB, please verify that "
    + "the server is running and that your "
    + "configuration is correct"
)
_NO_TOKEN_MSG = "Could not connect to ISPyB, no valid REST token available."


class ISPyBRestClientMockup(HardwareObject):
    """
    RESTful Web-service client for EXI.
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.__disabled = False
        self.__test_proposal = None
        self.__translations = {}
        self.__rest_root = None
        self.__rest_username = None
        self.__rest_token = None
        self.__rest_token_timestamp = None
        self.base_result_url = None
        self.login_ok = True

        self.__test_proposal = {
            "status": {"code": "ok"},
            "Person": {
                "personId": 1,
                "laboratoryId": 1,
                "login": None,
                "familyName": "operator on IDTESTeh1",
            },
            "Proposal": {
                "code": "idtest",
                "title": "operator on IDTESTeh1",
                "personId": 1,
                "number": "000",
                "proposalId": 1,
                "type": "MX",
            },
            "Session": [
                {
                    "scheduled": 0,
                    "startDate": "2013-06-11 00:00:00",
                    "endDate": "2013-06-12 07:59:59",
                    "beamlineName": "ID:TEST",
                    "timeStamp": datetime(2013, 6, 11, 9, 40, 36),
                    "comments": "Session created by the BCM",
                    "sessionId": 34591,
                    "proposalId": 1,
                    "nbShifts": 3,
                }
            ],
            "Laboratory": {"laboratoryId": 1, "name": "TEST eh1"},
        }

    def init(self):

        if HWR.beamline.session:
            self.beamline_name = HWR.beamline.session.beamline_name
        else:
            self.beamline_name = "ID:TEST"

        logging.getLogger("requests").setLevel(logging.WARNING)

        self.__rest_root = self.get_property("restRoot").strip()
        self.__rest_username = self.get_property("restUserName").strip()
        self.__rest_password = self.get_property("restPass").strip()
        self.__site = self.get_property("site").strip()

        try:
            self.base_result_url = self.get_property("base_result_url").strip()
        except AttributeError:
            pass

        self.__update_rest_token()

    def __update_rest_token(self):
        self.authenticate(self.__rest_username, self.__rest_password)

    def authenticate(self, user, password):
        """
        Authenticate with RESTfull services, updates the authentication token,
        username and password used internally by this object.

        :param str user: Username
        :param str password: Password
        :returns: None

        """
        if password == "wrong":
            raise Exception("Wrong credentials")
        self.__rest_token = "#MOCKTOKEN123"
        self.__rest_token_timestamp = datetime.now()
        self.__rest_username = user
        self.__rest_password = password
        msg = "Authenticated to LIMS token is: %s" % self.__rest_root
        logging.getLogger("ispyb_client").debug(msg)

    def sample_link(self):
        """
        Get the LIMS link to sample information

        :returns: Link to sample information
        """
        self.__update_rest_token()
        return urljoin(self.__rest_root, "samples?token=%s" % self.__rest_token)

    def dc_link(self, did):
        """
        Get the LIMS link the data collection with id <id>.

        :param str did: Data collection ID
        :returns: The link to the data collection
        """
        url = None

        if self.base_result_url is not None:
            path = "/#/mx/{pcode}{pnumber}/datacollection/datacollectionid/{did}/main"
            path = path.format(
                pcode=HWR.beamline.session.proposal_code,
                pnumber=HWR.beamline.session.proposal_number,
                did=did,
            )

            url = urljoin(self.base_result_url, path)

        return url

    def get_dc_list(self):
        """
        Get the list of data collections for the current session belonging to
        the current proposal. (Given by the session object)

        :returns: A list of LIMS DataCollection Objects
        """
        return []

    def get_dc(self, dc_id):
        """
        Get data collection with id <dc_id>

        :param int dc_id: The collection id
        :returns: Data collection dict
        """
        dc_dict = {}

        return dc_dict

    def get_dc_thumbnail(self, image_id):
        """
        Get the image data for image with id <image_id>

        :param int image_id: The image id
        :returns: tuple on the form (file name, base64 encoded data)
        """
        fname, data = ("", "")
        return fname, data

    def get_proposals_by_user(self, user_name):
        """
        Descript. : gets all proposals for selected user
                    at first all proposals for user are obtained
                    then for each proposal all sessions are obtained
                    TODO: also user and laboratory should be obtained
        """
        return [self.__test_proposal]

    def get_proposal_sessions(self, proposal_id):
        session_list = []
        return session_list

    def get_session_local_contact(self, session_id):
        """
        Retrieves the person entry associated with the session id <session_id>
        :param int session_id: session_id

        :returns: Person dict
        :rtype: dict
        """
        return {
            "personId": 1,
            "laboratoryId": 1,
            "login": None,
            "familyName": "operator on ID14eh1",
        }

    def translate(self, code, what):
        """
        Given a proposal code, returns the correct code to use in the GUI,
        or what to send to LDAP, user office database, or the ISPyB database.
        """
        try:
            translated = self.__translations[code][what]
        except KeyError:
            translated = code

        return translated

    def store_data_collection(self, mx_collection, bl_config=None):
        """
        Stores the data collection mx_collection, and the beamline setup
        if provided.

        :param mx_collection: The data collection parameters.
        :type mx_collection: dict

        :param bl_config: The beamline setup.
        :type bl_config: dict

        :returns: None

        """
        print("store_data_collection...", mx_collection)
        return None, None

    def store_beamline_setup(self, session_id, bl_config):
        """
        Stores the beamline setup dict <bl_config>.

        :param session_id: The session id that the bl_config
                           should be associated with.
        :type session_id: int

        :param bl_config: The dictonary with beamline settings.
        :type bl_config: dict

        :returns beamline_setup_id: The database id of the beamline setup.
        :rtype: str
        """
        print("store_beamline_setup...", bl_config)

    def update_data_collection(self, mx_collection, wait=False):
        """
        Updates the datacollction mx_collection, this requires that the
        collectionId attribute is set and exists in the database.

        :param mx_collection: The dictionary with collections parameters.
        :type mx_collection: dict

        :returns: None
        """
        print("update_data_collection... ", mx_collection)

    def store_image(self, image_dict):
        """
        Stores the image (image parameters) <image_dict>

        :param image_dict: A dictonary with image pramaters.
        :type image_dict: dict

        :returns: None
        """
        print("store_image ", image_dict)

    def get_samples(self, proposal_id, session_id):
        pass

    def get_session_samples(self, proposal_id, session_id, sample_refs):
        """
        Retrives the list of samples associated with the session <session_id>.
        The samples from ISPyB is cross checked with the ones that are
        currently in the sample changer.

        The datamatrix code read by the sample changer is used in case
        of conflict.

        :param proposal_id: ISPyB proposal id.
        :type proposal_id: int

        :param session_id: ISPyB session id to retreive samples for.
        :type session_id: int

        :param sample_refs: The list of samples currently in the
                            sample changer. As a list of sample_ref
                            objects
        :type sample_refs: list (of sample_ref objects).

        :returns: A list with sample_ref objects.
        :rtype: list
        """
        pass

    def get_bl_sample(self, bl_sample_id):
        """
        Fetch the BLSample entry with the id bl_sample_id

        :param bl_sample_id:
        :type bl_sample_id: int

        :returns: A BLSampleWSValue, defined in the wsdl.
        :rtype: BLSampleWSValue

        """
        pass

    def disable(self):
        self.__disabled = True

    def enable(self):
        self.__disabled = False

    def store_data_collection_group(self, mx_collection):
        """
        Stores or updates a DataCollectionGroup object.
        The entry is updated of the group_id in the
        mx_collection dictionary is set to an exisitng
        DataCollectionGroup id.

        :param mx_collection: The dictionary of values to create the object from.
        :type mx_collection: dict

        :returns: DataCollectionGroup id
        :rtype: int
        """
        pass

    def is_connected(self):
        return self.login_ok
