"""
A client for ISPyB Webservices.
"""

import logging
import warnings

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ProposalTypeISPyBLims import ProposalTypeISPyBLims
from mxcubecore.model.lims_session import (
    LimsSessionManager,
    Session,
)

# to simulate wrong loginID, use anything else than idtest
# to simulate wrong psd, use "wrong" for password
# to simulate ispybDown, but ldap login succeeds, use "ispybDown" for password
# to simulate no session scheduled, use "nosession" for password


LOGIN_TYPE_FALLBACK = "proposal"


class ISPyBClientMockup(ProposalTypeISPyBLims):
    """
    Web-service client for ISPyB.
    """

    def __init__(self, name):
        super().__init__(name)

        self.loginType = LOGIN_TYPE_FALLBACK

    def init(self):
        try:
            self.base_result_url = self.get_property("base_result_url").strip()
        except AttributeError:
            pass

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
                "number": "0",
                "proposalId": 1,
                "type": "MX",
            },
            "Session": [
                {
                    "scheduled": 0,
                    "startDate": "2013-06-11 00:00:00",
                    "endDate": "2023-06-12 07:59:59",
                    "beamlineName": self.beamline_name,
                    "timeStamp": "2013-06-11 09:40:36",
                    "comments": "Session created by the BCM",
                    "sessionId": 34591,
                    "proposalId": 1,
                    "nbShifts": 3,
                }
            ],
            "Laboratory": {"laboratoryId": 1, "name": "TEST eh1"},
        }

        self.loginType = self.get_property("loginType", LOGIN_TYPE_FALLBACK)

    def get_login_type(self):
        warnings.warn(
            "Deprecated method `get_login_type`. Use `loginType` property instead.",
            DeprecationWarning,
        )
        return self.loginType

    def is_user_login_type(self):
        return self.loginType == "user"

    def _authenticate(self, user_name, password):
        if user_name != "idtest0":
            raise Exception(f"Could not authenticate")

        if password == "wrong":
            raise Exception("Could not authenticate")

        if password == "ispybDown":
            raise Exception("Could not authenticate")

    def _create_test_session(self):
        session_dict = {
            "session_id": "1565334143",
            "beamline_name": "ID23-1",
            "start_date": "20240615",
            "start_time": "14:50:34",
            "end_date": "20240925",
            "end_time": "14:50:34",
            "title": "MXCuBE Sample tracking Development ",
            "code": "ID23-1",
            "number": "0424",
            "proposal_id": "1565334143",
            "proposal_name": "ID23-1-0424",
            "comments": "",
            "nb_shifts": "3",
            "scheduled": "True",
            "is_rescheduled": False,
            "is_scheduled_time": True,
            "is_scheduled_beamline": True,
            "user_portal_URL": "",
            "data_portal_URL": "https://data2.esrf.fr/investigation/1565334143/datasets",
            "logbook_URL": "https://data2.esrf.fr/investigation/1565334143/logbook",
        }

        session: Session = Session(**session_dict)
        return LimsSessionManager(sessions=[session], active_session=session)

    def login(
        self, user_name: str, password: str, is_local_host: bool
    ) -> LimsSessionManager:
        logging.getLogger("HRW").debug(
            "Login on ISPyBLims proposal=%s is_local_host=%s"
            % (user_name, str(is_local_host)),
        )
        self._authenticate(user_name, password)
        self.session_manager = LimsSessionManager()
        # Authentication
        try:
            self._authenticate(user_name, password)
            self.user_name = user_name
        except BaseException as e:
            raise e

        self.session_manager = self._create_test_session()
        return self.session_manager

    def create_session(self, proposal):
        self.session_manager = self._create_test_session()
        return self.session_manager

    def get_proposal(self, proposal_code, proposal_number):
        """
        Returns the tuple (Proposal, Person, Laboratory, Session, Status).
        Containing the data from the coresponding tables in the database
        the status of the database operations are returned in Status.

        :param proposal_code: The proposal code
        :type proposal_code: str
        :param proposal_number: The proposal number
        :type proposal_number: int

        :returns: The dict (Proposal, Person, Laboratory, Sessions, Status).
        :rtype: dict
        """
        return self.__test_proposal

    def get_proposals_by_user(self, user_name):
        return [self.__test_proposal]

    def get_session_local_contact(self, session_id):
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

    def is_connected(self):
        return self.login_ok

    def isInhouseUser(self, proposal_code, proposal_number):
        """
        Returns True if the proposal is considered to be a
        in-house user.

        :param proposal_code:
        :type proposal_code: str

        :param proposal_number:
        :type proposal_number: str

        :rtype: bool
        """
        for proposal in self["inhouse"]:
            if proposal_code == proposal.code:
                if str(proposal_number) == str(proposal.number):
                    return True
        return False

    def _store_data_collection_group(self, group_data_dict):
        pass

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
        logging.getLogger("HWR").debug(
            "Data collection parameters stored " + "in ISPyB: %s" % str(mx_collection)
        )
        logging.getLogger("HWR").debug(
            "Beamline setup stored in ISPyB: %s" % str(bl_config)
        )

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
        pass

    def update_data_collection(self, mx_collection, wait=False):
        """
        Updates the datacollction mx_collection, this requires that the
        collectionId attribute is set and exists in the database.

        :param mx_collection: The dictionary with collections parameters.
        :type mx_collection: dict

        :returns: None
        """
        pass

    def update_bl_sample(self, bl_sample):
        """
        Creates or stos a BLSample entry.

        :param sample_dict: A dictonary with the properties for the entry.
        :type sample_dict: dict
        # NBNB update doc string
        """
        pass

    def store_image(self, image_dict):
        """
        Stores the image (image parameters) <image_dict>

        :param image_dict: A dictonary with image pramaters.
        :type image_dict: dict

        :returns: None
        """
        pass

    def store_robot_action(self, robot_action_dict):
        """
        Stores the robot action dictionary.

        Structure of robot_action_dictionary:
        {
            "actionType":str,
            "containerLocation": str,
            "dewarLocation":str,
            "message":str,
            "sampleBarcode":str,
            "sessionId":int,
            "sampleId":int.
            "startTime":str,
            "endTime":str,
            "xtalSnapshotAfter:str",
            "xtalSnapshotBefore:str",
        }

        Args:
            robot_action_dict: robot action dictionary as defined above
        """
        pass

    def __find_sample(self, sample_ref_list, code=None, location=None):
        """
        Returns the sample with the matching "search criteria" <code> and/or
        <location> with-in the list sample_ref_list.

        The sample_ref object is defined in the head of the file.

        :param sample_ref_list: The list of sample_refs to search.

        :param code: The vial datamatrix code (or bar code)

        :param location: A tuple (<basket>, <vial>) to search for.
        :type location: tuple
        """
        pass

    def get_samples(self, lims_name):
        # Try GPhL emulation samples, if available
        gphl_workflow = HWR.beamline.gphl_workflow
        if gphl_workflow is not None:
            sample_dicts = gphl_workflow.get_emulation_samples()
            if sample_dicts:
                return sample_dicts

        return [
            {
                "cellA": 0.0,
                "cellAlpha": 0.0,
                "cellB": 0.0,
                "cellBeta": 0.0,
                "cellC": 0.0,
                "cellGamma": 0.0,
                "containerSampleChangerLocation": "1",
                "crystalSpaceGroup": "P212121",
                "diffractionPlan": {
                    "diffractionPlanId": 457980,
                    "experimentKind": "Default",
                    "numberOfPositions": 0,
                    "observedResolution": 0.0,
                    "preferredBeamDiameter": 0.0,
                    "radiationSensitivity": 0.0,
                    "requiredCompleteness": 0.0,
                    "requiredMultiplicity": 0.0,
                    "requiredResolution": 0.0,
                },
                "experimentType": "Default",
                "proteinAcronym": "A-TIM",
                "sampleId": 515485,
                "sampleLocation": "1",
                "sampleName": "fghfg",
                "smiles": None,
            },
            {
                "cellA": 0.0,
                "cellAlpha": 0.0,
                "cellB": 0.0,
                "cellBeta": 0.0,
                "cellC": 0.0,
                "cellGamma": 0.0,
                "containerSampleChangerLocation": "2",
                "crystalSpaceGroup": "P2",
                "diffractionPlan": {
                    "diffractionPlanId": 457833,
                    "experimentKind": "OSC",
                    "numberOfPositions": 0,
                    "observedResolution": 0.0,
                    "preferredBeamDiameter": 0.0,
                    "radiationSensitivity": 0.0,
                    "requiredCompleteness": 0.0,
                    "requiredMultiplicity": 0.0,
                    "requiredResolution": 0.0,
                },
                "experimentType": "OSC",
                "proteinAcronym": "B2 hexa",
                "sampleId": 515419,
                "sampleLocation": "1",
                "sampleName": "sample",
            },
            {
                "cellA": 0.0,
                "cellAlpha": 0.0,
                "cellB": 0.0,
                "cellBeta": 0.0,
                "cellC": 0.0,
                "cellGamma": 0.0,
                "containerSampleChangerLocation": "2",
                "crystalSpaceGroup": "P2",
                "diffractionPlan": {
                    "diffractionPlanId": 457834,
                    "experimentKind": "OSC",
                    "numberOfPositions": 0,
                    "observedResolution": 0.0,
                    "preferredBeamDiameter": 0.0,
                    "radiationSensitivity": 0.0,
                    "requiredCompleteness": 0.0,
                    "requiredMultiplicity": 0.0,
                    "requiredResolution": 0.0,
                },
                "experimentType": "OSC",
                "proteinAcronym": "B2 hexa",
                "sampleId": 515420,
                "sampleLocation": "2",
                "sampleName": "sample",
            },
            {
                "cellA": 0.0,
                "cellAlpha": 0.0,
                "cellB": 0.0,
                "cellBeta": 0.0,
                "cellC": 0.0,
                "cellGamma": 0.0,
                "containerSampleChangerLocation": "2",
                "crystalSpaceGroup": "P2",
                "diffractionPlan": {
                    "diffractionPlanId": 457835,
                    "experimentKind": "OSC",
                    "numberOfPositions": 0,
                    "observedResolution": 0.0,
                    "preferredBeamDiameter": 0.0,
                    "radiationSensitivity": 0.0,
                    "requiredCompleteness": 0.0,
                    "requiredMultiplicity": 0.0,
                    "requiredResolution": 0.0,
                },
                "experimentType": "OSC",
                "proteinAcronym": "B2 hexa",
                "sampleId": 515421,
                "sampleLocation": "3",
                "sampleName": "sample",
            },
            {
                "cellA": 0.0,
                "cellAlpha": 0.0,
                "cellB": 0.0,
                "cellBeta": 0.0,
                "cellC": 0.0,
                "cellGamma": 0.0,
                "containerSampleChangerLocation": "2",
                "crystalSpaceGroup": "P2",
                "diffractionPlan": {
                    "diffractionPlanId": 457836,
                    "experimentKind": "OSC",
                    "numberOfPositions": 0,
                    "observedResolution": 0.0,
                    "preferredBeamDiameter": 0.0,
                    "radiationSensitivity": 0.0,
                    "requiredCompleteness": 0.0,
                    "requiredMultiplicity": 0.0,
                    "requiredResolution": 0.0,
                },
                "experimentType": "OSC",
                "proteinAcronym": "B2 hexa",
                "sampleId": 515422,
                "sampleLocation": "5",
                "sampleName": "sample",
            },
            {
                "cellA": 0.0,
                "cellAlpha": 0.0,
                "cellB": 0.0,
                "cellBeta": 0.0,
                "cellC": 0.0,
                "cellGamma": 0.0,
                "containerSampleChangerLocation": "2",
                "crystalSpaceGroup": "P2",
                "diffractionPlan": {
                    "diffractionPlanId": 457837,
                    "experimentKind": "OSC",
                    "numberOfPositions": 0,
                    "observedResolution": 0.0,
                    "preferredBeamDiameter": 0.0,
                    "radiationSensitivity": 0.0,
                    "requiredCompleteness": 0.0,
                    "requiredMultiplicity": 0.0,
                    "requiredResolution": 0.0,
                },
                "experimentType": "OSC",
                "proteinAcronym": "B2 hexa",
                "sampleId": 515423,
                "sampleLocation": "6",
                "sampleName": "sample",
            },
            {
                "cellA": 0.0,
                "cellAlpha": 0.0,
                "cellB": 0.0,
                "cellBeta": 0.0,
                "cellC": 0.0,
                "cellGamma": 0.0,
                "containerSampleChangerLocation": "2",
                "crystalSpaceGroup": "P2",
                "diffractionPlan": {
                    "diffractionPlanId": 457838,
                    "experimentKind": "OSC",
                    "numberOfPositions": 0,
                    "observedResolution": 0.0,
                    "preferredBeamDiameter": 0.0,
                    "radiationSensitivity": 0.0,
                    "requiredCompleteness": 0.0,
                    "requiredMultiplicity": 0.0,
                    "requiredResolution": 0.0,
                },
                "experimentType": "OSC",
                "proteinAcronym": "B2 hexa",
                "sampleId": 515424,
                "sampleLocation": "7",
                "sampleName": "sample",
            },
        ]

    # Bindings to methods called from older bricks.
    getProposal = get_proposal
    getSessionLocalContact = get_session_local_contact
    storeDataCollection = store_data_collection
    storeBeamLineSetup = store_beamline_setup
    updateBLSample = update_bl_sample
    updateDataCollection = update_data_collection
    storeImage = store_image
