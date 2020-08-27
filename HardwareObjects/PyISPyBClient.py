"""
A client for ISPyB Webservices.
"""
import logging
import json
import cgi

from datetime import datetime
from requests import post, get
from urllib.parse import urljoin
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository import HardwareRepository as HWR

_CONNECTION_ERROR_MSG = (
    "Could not connect to ISPyB, please verify that "
    + "the server is running and that your "
    + "configuration is correct"
)
_NO_TOKEN_MSG = "Could not connect to ISPyB, no valid REST token available."

ispyb_log = logging.getLogger("ispyb_client")
logging.getLogger("requests").setLevel(logging.WARNING)


class PyISPyBClient(HardwareObject):
    """
    RESTful Web-service client.
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.__connected = False
        self.__translations = {}
        self.__root_url = None
        self.__username = None
        self.__password = None

        self.__token = None
        self.__token_timestamp = None
        self.base_result_url = None


    def init(self):
        self.__root_url = self.getProperty("root_url").strip()
        self.__username = self.getProperty("username").strip()
        self.__password = self.getProperty("password").strip()
        self.base_result_url = self.getProperty("base_result_url", "").strip()

        if self.getProperty("master_token"):
            self.__token = self.getProperty("master_token")
            self.__token_timestamp = datetime.now()
            self.update_state(self.STATES.READY)
        else:
            self.__update_rest_token()

    def get_login_type(self):
        return "user"

    def __update_rest_token(self):
        """
        Updates REST token if necessary by default token expires in 3h so we
        are checking the timestamp of the tocken and if it is older than 3h we
        update the rest token
        """
        #TODO call rest url something like /auth/is_token_valid
        request_token = False
        if not self.__token_timestamp:
            request_token = True
        else:
            timedelta = datetime.now() - self.__token_timestamp
            if timedelta.seconds > (3 * 60 * 60):
                request_token = True
            

        if request_token:
            self.authenticate()

    def authenticate(self):
        """
        Authenticate with RESTfull services, updates the authentication token,
        username and password used internally by this object.

        :returns: None

        """

        try:
            response = get(urljoin(self.root_url, "/auth/login"), auth=(self.__username, self.__password))

            self.__token = response.json().get("token")
            self.__token_timestamp = datetime.now()
        except Exception as ex:
            msg = "Failed to authenticate user %s (%s)" % (self.__username, str(ex))
            ispyb_log.exception(msg)
        else:
            msg = "Authenticated to LIMS"
            ispyb_log.debug(msg)

    def get_proposals_by_user(self, user_name):
        """
        Descript. : gets all proposals for selected user
                    at first all proposals for user are obtained
                    then for each proposal all sessions are obtained
                    TODO: also user and laboratory should be obtained
        """
        #self.__update_rest_token()
        result = []
        if self.__token:
            try:
                url = "{root_url}/proposal/login_name/{login_name}"
                url = url.format(
                    root_url=self.__root_url,
                    login_name=user_name
                )
                headers = {"Authorization": "Bearer " + self.__token}
                response = get(url, headers=headers)
                proposal_list = response.json()
                if not proposal_list:
                    ispyb_log.debug("No proposal assicated with user %s found" % user_name)
                else:
                    for proposal in proposal_list:
                        if proposal["proposalType"] in ("MX", "MB"):
                            temp_proposal = {"Proposal" : {}, "Session" : []}
                            temp_proposal["Proposal"]["proposalId"] = proposal["proposalId"]
                            temp_proposal["Proposal"]["code"] = proposal["proposalCode"]
                            temp_proposal["Proposal"]["number"] = proposal["proposalNumber"]
                            temp_proposal["Proposal"]["title"] = proposal["title"]
                            sessions = self.get_proposal_sessions(proposal["proposalId"])

                            for session in sessions:
                                date_object = datetime.strptime(
                                    session["startDate"], "%b %d, %Y %I:%M:%S %p"
                                )
                                session["startDate"] = datetime.strftime(
                                    date_object, "%Y-%m-%d %H:%M:%S"
                                )
                                date_object = datetime.strptime(
                                    session["endDate"], "%b %d, %Y %I:%M:%S %p"
                                )
                                session["endDate"] = datetime.strftime(
                                    date_object, "%Y-%m-%d %H:%M:%S"
                                )
                                temp_proposal["Session"].append(session)

                            result.append(temp_proposal)
            except BaseException:
                ispyb_log.exception(_CONNECTION_ERROR_MSG)
        else:
            ispyb_log.exception(_NO_TOKEN_MSG)
        print(result)
        return result

    def get_proposal_sessions(self, proposal_id):
        #self.__update_rest_token()
        session_list = []
        try:
            url = "{root_url}/session/params".format(
                root_url=self.__root_url,
                )
            headers = {"Authorization": "Bearer " + self.__token}
            params = {"proposalId" : proposal_id}
            response = get(url, headers=headers, params=params)

            session_list = response.json()
        except BaseException:
            logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
        return session_list

    def create_session(self, session_dict):
        """
        Create a new session for "current proposal", the attribute
        porposalId in <session_dict> has to be set (and exist in ISPyB).

        :param session_dict: Dictonary with session parameters.
        :type session_dict: dict

        :returns: The session id of the created session.
        :rtype: int
        """
        result = None
        
        #if self.is_ready()
        if True:
            #try:
            if True:
                session_dict["beamLineName"] = session_dict["beamlineName"]
                session_dict.pop("beamlineName")
                session_dict["sessionTitle"] = session_dict["comments"]
                session_dict.pop("comments")

                

                #session = 
                url = "{root_url}/session".format(root_url=self.__root_url)
                headers = {
                    "Authorization": "Bearer " + self.__token,
                    "Content-type": "application/json"
                    }
                print('To be stored %s' % str(session_dict))
                response = post(url, headers=headers, json=session_dict)
                print(response.status_code)
                result = response.json()

            #except WebFault as e:
            #    session = {}
            #    ispyb_log.exception(str(e))
            #except URLError:
            #    ispyb_log.exception(_CONNECTION_ERROR_MSG)
            ispyb_log.info(
                "[ISPYB] Session created: %s" % result
            )
        else:
            logging.getLogger("ispyb_client").exception(
                "Error in create_session: could not connect to server"
            )
        return result

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
        print(("store_data_collection...", mx_collection))
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
        print(("store_bl_config...", bl_config))

    def update_data_collection(self, mx_collection, wait=False):
        """
        Updates the datacollction mx_collection, this requires that the
        collectionId attribute is set and exists in the database.

        :param mx_collection: The dictionary with collections parameters.
        :type mx_collection: dict

        :returns: None
        """
        print(("update_data_collection... ", mx_collection))

    def store_image(self, image_dict):
        """
        Stores the image (image parameters) <image_dict>

        :param image_dict: A dictonary with image pramaters.
        :type image_dict: dict

        :returns: None
        """
        print(("store_image ", image_dict))

    def get_samples(self, proposal_id, session_id):
        pass




