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


class ISPyBRestClient(HardwareObject):
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
        self.beamline_name = None

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
            self.base_result_url = self.get_property("base_result_url", "").strip()
        except AttributeError:
            pass

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
        auth_url = urljoin(self.__rest_root, "authenticate?site=" + self.__site)

        try:
            data = {"login": str(user), "password": str(password)}
            response = post(auth_url, data=data)

            self.__rest_token = response.json().get("token")
            self.__rest_token_timestamp = datetime.now()
            self.__rest_username = user
            self.__rest_password = password
        except Exception as ex:
            msg = "POST to %s failed reason %s" % (auth_url, str(ex))
            logging.getLogger("ispyb_client").exception(msg)
        else:
            msg = "Authenticated to LIMS token is: %s" % self.__rest_root
            logging.getLogger("ispyb_client").exception(msg)

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
        url = "#"

        if self.base_result_url is not None and did:
            path = "mx/#/mx/proposal/{pcode}{pnumber}/datacollection/datacollectionid/{did}/main"
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
        self.__update_rest_token()

        url = "{rest_root}{token}"
        url += "/proposal/{pcode}{pnumber}/mx/datacollection/session/{sid}/list"
        url = url.format(
            rest_root=self.__rest_root,
            token=str(self.__rest_token),
            pcode=HWR.beamline.session.proposal_code,
            pnumber=HWR.beamline.session.proposal_number,
            sid=HWR.beamline.session.session_id,
        )

        try:
            response = json.loads(get(url).text)
        except Exception as ex:
            response = []
            logging.getLogger("ispyb_client").exception(str(ex))

        return response

    def get_dc(self, dc_id):
        """
        Get data collection with id <dc_id>

        :param int dc_id: The collection id
        :returns: Data collection dict
        """
        self.__update_rest_token()

        url = "{rest_root}{token}"
        url += "/proposal/{pcode}{pnumber}/mx/datacollection/{dc_id}/list"
        url = url.format(
            rest_root=self.__rest_root,
            token=str(self.__rest_token),
            pcode=HWR.beamline.session.proposal_code,
            pnumber=HWR.beamline.session.proposal_number,
            dc_id=dc_id,
        )
        try:
            response = json.loads(get(url).text)[0]
        except Exception as ex:
            response = None
            # logging.getLogger("ispyb_client").exception(str(ex))

        lims_dc = {}
        lims_dc["workflow_result_url_list"] = []

        try:
            if response and "WorkflowStep_workflowStepId" in response:
                step_id_list = response["WorkflowStep_workflowStepId"].split(",")

                for step_id in step_id_list:
                    url = "{rest_root}{token}"
                    url += (
                        "/proposal/{pcode}{pnumber}/mx/workflow/step/{step_id}/result"
                    )
                    url = url.format(
                        rest_root=self.__rest_root,
                        token=str(self.__rest_token),
                        pcode=HWR.beamline.session.proposal_code,
                        pnumber=HWR.beamline.session.proposal_number,
                        step_id=step_id,
                    )

                    lims_dc["workflow_result_url_list"].append(url)
        except Exception as ex:
            logging.getLogger("ispyb_client").exception(str(ex))

        if response:
            for key, value in response.items():
                if key.startswith("DataCollection_"):
                    k = str(key.replace("DataCollection_", ""))
                    lims_dc[k] = value
                elif key == "firstImageId":
                    lims_dc["firstImageId"] = value
                elif key == "lastImageId":
                    lims_dc["lastImageId"] = value

        return lims_dc

    def get_quality_indicator_plot(self, collection_id):
        """
        Get the imagequliaty indicator plot for collection with
        collection id <collection_id>

        :param int collection_id: The collection id
        :returns: tuple on the form (file name, base64 encoded data)
        """
        self.__update_rest_token()
        fname, data = ("", "")

        url = "{rest_root}{token}"
        url += (
            "/proposal/{pcode}{pnumber}/mx/datacollection/{dcid}/qualityindicatorplot"
        )
        url = url.format(
            rest_root=self.__rest_root,
            token=str(self.__rest_token),
            pcode=HWR.beamline.session.proposal_code,
            pnumber=HWR.beamline.session.proposal_number,
            dcid=collection_id,
        )

        try:
            response = get(url)
            data = response.content
        except Exception as ex:
            response = []
            logging.getLogger("ispyb_client").exception(str(ex))

        return data

    def get_dc_thumbnail(self, image_id):
        """
        Get the image data for image with id <image_id>

        :param int image_id: The image id
        :returns: tuple on the form (file name, base64 encoded data)
        """

        self.__update_rest_token()
        fname, data = ("", "")

        url = "{rest_root}{token}"
        url += "/proposal/{pcode}{pnumber}/mx/image/{image_id}/thumbnail"
        url = url.format(
            rest_root=self.__rest_root,
            token=str(self.__rest_token),
            pcode=HWR.beamline.session.proposal_code,
            pnumber=HWR.beamline.session.proposal_number,
            image_id=image_id,
        )

        try:
            response = get(url)
            data = response.content
            value, params = cgi.parse_header(response.headers)
            fname = params["filename"]

        except Exception as ex:
            response = []
            logging.getLogger("ispyb_client").exception(str(ex))

        return fname, data

    def get_dc_image(self, image_id):
        """
        Get the image data for image with id <image_id>

        :param int image_id: The image id
        :returns: tuple on the form (file name, base64 encoded data)
        """

        self.__update_rest_token()
        fname, data = ("", "")

        url = "{rest_root}{token}"
        url += "/proposal/{pcode}{pnumber}/mx/image/{image_id}/get"
        url = url.format(
            rest_root=self.__rest_root,
            token=str(self.__rest_token),
            pcode=HWR.beamline.session.proposal_code,
            pnumber=HWR.beamline.session.proposal_number,
            image_id=image_id,
        )

        try:
            response = get(url)
            data = response.content
            value, params = cgi.parse_header(response.headers)
            fname = params["filename"]

        except Exception as ex:
            response = []
            logging.getLogger("ispyb_client").exception(str(ex))

        return fname, data

    def get_proposals_by_user(self, user_name):
        """
        Descript. : gets all proposals for selected user
                    at first all proposals for user are obtained
                    then for each proposal all sessions are obtained
                    TODO: also user and laboratory should be obtained
        """
        self.__update_rest_token()
        result = []
        if self.__rest_token:
            try:
                url = "{rest_root}{token}/proposal/{username}/list"
                url = url.format(
                    rest_root=self.__rest_root,
                    token=self.__rest_token,
                    username=user_name,
                )

                response = get(url)
                proposal_list = json.loads(str(response.text))

                for proposal in proposal_list:
                    temp_proposal_dict = {}
                    # Backward compatability with webservices
                    # Could be removed if webservices disapear
                    temp_proposal_dict["Proposal"] = {}
                    temp_proposal_dict["Proposal"]["type"] = str(
                        proposal["Proposal_proposalType"]
                    )

                    if temp_proposal_dict["Proposal"]["type"] in ("MX", "MB"):
                        temp_proposal_dict["Proposal"]["proposalId"] = proposal[
                            "Proposal_proposalId"
                        ]
                        temp_proposal_dict["Proposal"]["code"] = str(
                            proposal["Proposal_proposalCode"]
                        )
                        temp_proposal_dict["Proposal"]["number"] = proposal[
                            "Proposal_proposalNumber"
                        ]
                        temp_proposal_dict["Proposal"]["title"] = proposal[
                            "Proposal_title"
                        ]
                        temp_proposal_dict["Proposal"]["personId"] = proposal[
                            "Proposal_personId"
                        ]

                        res_sessions = self.get_proposal_sessions(
                            temp_proposal_dict["Proposal"]["proposalId"]
                        )

                        proposal_sessions = []
                        for session in res_sessions:
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
                            proposal_sessions.append(session)

                            temp_proposal_dict["Sessions"] = proposal_sessions

                        result.append(temp_proposal_dict)
            except Exception:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
        else:
            logging.getLogger("ispyb_client").exception(_NO_TOKEN_MSG)
        return result

    def get_proposal_sessions(self, proposal_id):
        self.__update_rest_token()
        session_list = []
        if self.__rest_token:
            try:
                response = get(
                    self.__rest_root
                    + self.__rest_token
                    + "/proposal/%s/session/list" % proposal_id
                )
                session_list = response.json()
                # for session in all_sessions:
                #    if session['proposalVO']['proposalId'] == proposal_id:
                # session_list.append(all_sessions)
            except Exception:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
        else:
            logging.getLogger("ispyb_client").exception(_NO_TOKEN_MSG)

        return session_list

    # @trace
    def get_session_local_contact(self, session_id):
        """
        Descript. : Retrieves the person entry associated with the session
                    id <session_id>
        Args      : param session_id (ype session_id: int)
        Return    : Person object as dict (type: dict)
        """
        self.__update_rest_token()
        session_list = []
        result = {}

        if self.__rest_token:
            response = get(
                self.__rest_root
                + self.__rest_token
                + "/proposal/session/%d/localcontact" % session_id
            )
        else:
            logging.getLogger("ispyb_client").exception(_NO_TOKEN_MSG)
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

    def __find_sample(self, sample_ref_list, code=None, location=None):
        """
        Returns the sample with the matching "search criteria" <code> and/or
        <location> with-in the list sample_ref_list.

        The sample_ref object is defined in the head of the file.

        :param sample_ref_list: The list of sample_refs to search.
        :type sample_ref: list

        :param code: The vial datamatrix code (or bar code)
        :param type: str

        :param location: A tuple (<basket>, <vial>) to search for.
        :type location: tuple
        """

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

    def get_bl_sample(self, bl_sample_id):
        """
        Fetch the BLSample entry with the id bl_sample_id

        :param bl_sample_id:
        :type bl_sample_id: int

        :returns: A BLSampleWSValue, defined in the wsdl.
        :rtype: BLSampleWSValue

        """

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

    def _store_data_collection_group(self, group_data):
        self.update_rest_token()
        if self.__rest_token:
            try:
                response = get(
                    self.__rest_root
                    + self.__rest_token
                    + "/proposal/%s/session/list" % self.__rest_username
                )
                all_sessions = response.json()
                for session in all_sessions:
                    if session["proposalVO"]["proposalId"] == proposal_id:
                        session_list.append(session)
            except Exception:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
        else:
            logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

        return session_list
