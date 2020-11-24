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
        self.__disabled = False
        self.__translations = {}
        self.__root_url = None
        self.__username = None
        self.__password = None

        self.__token = None
        self.__token_timestamp = None
        self.base_result_url = None


    def init(self):
        self.__root_url = self.get_property("root_url").strip()
        self.__username = self.get_property("username").strip()
        self.__password = self.get_property("password").strip()
        self.base_result_url = self.get_property("base_result_url", "").strip()

        if self.get_property("master_token"):
            self.__token = self.get_property("master_token")
            self.__token_timestamp = datetime.now()
            self.update_state(self.STATES.READY)
        else:
            self.__update_rest_token()

    
    def disable(self):
        self.__disabled = True

    def enable(self):
        self.__disabled = False
    
    def call_get(self, relative_url, host="ispyb_core", params=None):
        url = urljoin(self.__root_url, relative_url)
        headers = {
            "Authorization": "Bearer " + self.__token,
            "Content-type": "application/json",
            "Host": host
        }
        print(url, headers, params)
        response = get(url, headers=headers, params=params)

        return response.status_code, response.json()

    def call_post(self, relative_url, json_data, host="ispyb_core"):
        url = urljoin(self.__root_url, relative_url)
        headers = {
            "Authorization": "Bearer " + self.__token,
            "Content-type": "application/json",
            "Host": host
        }
        print(url)
        response = post(url, headers=headers, json=json_data)
        print(response.status_code)
        return response.status_code, response.json()

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
                params = {"login_name" : user_name}

                status_code, data_json = self.call_get("proposals", params=params)
                proposal_list = data_json["data"]["rows"]

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
                                session["beamlineName"] = session["beamLineName"]
                                date_object = datetime.strptime(
                                    session["startDate"][:-6], "%Y-%m-%dT%H:%M:%S"
                                )
                                session["startDate"] = datetime.strftime(
                                    date_object, "%Y-%m-%d %H:%M:%S"
                                )
                                date_object = datetime.strptime(
                                    session["endDate"][:-6], "%Y-%m-%dT%H:%M:%S"
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
        return result

    def get_proposal_sessions(self, proposal_id):
        #self.__update_rest_token()
        session_list = []
        try:
            params = {"proposalId" : proposal_id}

            status_code, data_json = self.call_get("sessions", params=params)
            session_list = data_json["data"]["rows"]
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
                #session_dict.pop("beamlineName")
                session_dict["sessionTitle"] = session_dict["comments"]
                #session_dict.pop("comments")

                status_code, result = self.call_post("sessions", session_dict)
            #except WebFault as e:
            #    session = {}
            #    ispyb_log.exception(str(e))
            #except URLError:
            #    ispyb_log.exception(_CONNECTION_ERROR_MSG)
            ispyb_log.info(
                "[ISPYB] Session created: %s" % str(result)
            )
        else:
            logging.getLogger("ispyb_client").exception(
                "Error in create_session: could not connect to server"
            )
        return result

    def get_session_local_contact(self, session_id):
        """
        Descript. : Retrieves the person entry associated with the session
                    id <session_id>
        Args      : param session_id (ype session_id: int)
        Return    : Person object as dict (type: dict)
        """
        url = "session/descr/%d" % session_id
        status_code, result = self.call_get(url)

        return result["proposal"]["person"]

    def _store_data_collection_group(self, group_data):
        """
        """
        group_id = None
        

        return group_id

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
        beamline_setup_id = None
        collection_id = None
        detector_id = None

        logging.getLogger("HWR").debug(
            "Storing data collection in lims. Data to store: %s, %s"
            % (str(mx_collection), str(bl_config))
        )

        if bl_config:
            beamline_setup_id = self.store_beamline_setup(
                mx_collection,
                bl_config
            )

        detector_id  = self.find_detector(bl_config)

        data_collection = {}

        if detector:
            detector_id = detector.detectorId
            data_collection["detectorId"] = detector["detectorId"]

        #collection_id = self._collection.service.storeOrUpdateDataCollection(
        #        data_collection
        #    )
            
        #else:
        #    logging.getLogger("ispyb_client").exception(
        #        "Error in store_data_collection: could not connect to server"
        #    )

        return collection_id, detector_id

    def store_beamline_setup(self, session, bl_config):
        """
        Stores the beamline setup dict <bl_config>.

        :param session: The session dict
        :type session: dict

        :param bl_config: The dictonary with beamline settings.
        :type bl_config: dict

        :returns beamline_setup_id: The database id of the beamline setup.
        :rtype: str
        """

        energy_limits = HWR.beamline.energy.get_limits()

        beamlines_setup_dict = {
            "detectorId":  None,
            "synchrotronMode" : bl_config.synchrotron_name,
            "monochromatorType": bl_config.monochromator_type,
            "focusingOptic": bl_config.focusing_optic,
            "beamDivergenceVertical": bl_config.beam_divergence_vertical,
            "beamDivergenceHorizontal": bl_config.beam_divergence_horizontal,
            "polarisation": bl_config.polarisation,
            "minExposureTimePerImage": bl_config.minimum_exposure_time,
            "setupDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "energyMin": energy_limits[0],
            "energyMax": energy_limits[1],
        }

        if bl_config.undulators:
            for index, undulator in enumerate(bl_config.undulators):
                beamlines_setup_dict["undulatorType%d" % index] = undulator.type

        status_code, result = self.call_post("sessions/beamline_setup", beamlines_setup_dict)
        return result["beamLineSetupId"]

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

    def store_robot_action(self, robot_action_dict):
        return
