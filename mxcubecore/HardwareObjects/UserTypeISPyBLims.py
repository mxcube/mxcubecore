from __future__ import print_function

import itertools
import logging
import sys

from suds import WebFault
from suds.client import Client
from suds.sudsobject import asdict

from mxcubecore.HardwareObjects.abstract.ISPyBAbstractLIMS import ISPyBAbstractLIMS
from mxcubecore.mxcubecore.model.lims_session import LimsSessionManager

try:
    from urllib2 import URLError
    from urlparse import urljoin
except Exception:
    # Python3
    from urllib.error import URLError

suds_encode = str.encode

if sys.version_info > (3, 0):
    suds_encode = bytes.decode

logging.getLogger("suds").setLevel(logging.INFO)


class UserTypeISPyBLims(ISPyBAbstractLIMS):
    """
    ISPyB proposal-based client
    """

    def __init__(self, name):
        super().__init__(name)
        self._collection = None

    def get_user_name(self):
        return self.user_name

    def is_user_login_type(self):
        return True

    def init(self):
        try:
            # ws_root is a property in the configuration xml file
            if self.ws_root:
                global _WS_COLLECTION_URL

                _WSDL_ROOT = self.ws_root.strip()

                _WS_COLLECTION_URL = _WSDL_ROOT + "ToolsForCollectionWebService?wsdl"

                if self.ws_root.strip().startswith("https://"):
                    from suds.transport.https import HttpAuthenticated
                else:
                    from suds.transport.http import HttpAuthenticated

                t2 = HttpAuthenticated(
                    username=self.ws_username,
                    password=self.ws_password,
                    proxy=self.proxy,
                )

                try:

                    self._collection = Client(
                        _WS_COLLECTION_URL,
                        timeout=3,
                        transport=t2,
                        cache=None,
                        proxy=self.proxy,
                    )

                    # ensure that suds do not create those files in tmp

                    self._collection.set_options(
                        cache=None, location=_WS_COLLECTION_URL
                    )

                except URLError as e:
                    logging.getLogger("ispyb_client").exception(str(e))
                    return
        except Exception as e:
            logging.getLogger("ispyb_client").exception(str(e))
            return

    def login(self, loginID, psd, ldap_connection=None) -> LimsSessionManager:
        login_name = loginID
        proposal_code = ""
        proposal_number = ""
        self.user_name = loginID

        # For porposal login, split the loginID to code and numbers
        if self.loginType == "proposal":
            proposal_code = "".join(
                itertools.takewhile(lambda c: not c.isdigit(), loginID)
            )
            proposal_number = loginID[len(proposal_code) :]

        # if translation of the loginID is needed, need to be tested by ESRF
        if self.loginTranslate is True:
            login_name = self._translate(proposal_code, "ldap") + str(proposal_number)

        # Authentication
        if self.authServerType == "ldap":
            logging.getLogger("HWR").debug(
                "Starting LDAP authentication %s" % login_name
            )
            ok = self.ldap_login(login_name, psd, ldap_connection)
            msg = loginID
            logging.getLogger("HWR").debug("User %s logged in LDAP" % login_name)
        elif self.authServerType == "ispyb":
            logging.getLogger("HWR").debug("ISPyB login")
            ok, msg = self._ispybLogin(login_name, psd)
        else:
            raise Exception("Authentication server type is not defined")

        if not ok:
            msg = "%s." % msg.capitalize()
            # refuse Login
            logging.getLogger("HWR").error("ISPyB login not ok")
            raise "Error lims authentication"
            # return ProposalTuple(Status(code="error", msg=msg))

        # login succeed, get proposal and sessions
        if self.loginType == "proposal":
            # get the proposal ID
            _code = self._translate(proposal_code, "ispyb")
            return self.adapter.get_sessions_by_code_and_number(
                _code, proposal_number, self.beamline_name
            )
        elif self.loginType == "user":
            return self.adapter.get_sessions_by_username(
                loginID, self.beamline_name
            )  # get_proposal_by_username(loginID)

    def get_proposals_by_user(self, user_name):
        proposal_list = []
        res_proposal = []

        if self._shipping:
            try:
                proposals = eval(
                    self._shipping.service.findProposalsByLoginName(user_name)
                )
                if proposal_list is not None:
                    for proposal in proposals:
                        if (
                            proposal["type"].upper() in ["MX", "MB"]
                            and proposal not in proposal_list
                        ):
                            proposal_list.append(proposal)
            except WebFault as e:
                proposal_list = []
                logging.getLogger("ispyb_client").exception(e.message)

            proposal_list = newlist = sorted(
                proposal_list, key=lambda k: int(k["proposalId"])
            )

            res_proposal = []
            if len(proposal_list) > 0:
                for proposal in proposal_list:
                    proposal_code = proposal["code"]
                    proposal_number = proposal["number"]

                    # person
                    try:
                        person = self._shipping.service.findPersonByProposal(
                            proposal_code, proposal_number
                        )
                        if not person:
                            person = {}
                    except WebFault as e:
                        logging.getLogger("ispyb_client").exception(str(e))
                        person = {}

                    # lab
                    try:
                        lab = self._shipping.service.findLaboratoryByProposal(
                            proposal_code, proposal_number
                        )
                        if not lab:
                            lab = {}
                    except WebFault as e:
                        logging.getLogger("ispyb_client").exception(str(e))
                        lab = {}

                    # sessions
                    try:
                        res_sessions = (
                            self._collection.service.findSessionsByProposalAndBeamLine(
                                proposal_code, proposal_number, self.beamline_name
                            )
                        )
                        sessions = []
                        for session in res_sessions:
                            if session is not None:
                                try:
                                    session.startDate = datetime.strftime(
                                        session.startDate, "%Y-%m-%d %H:%M:%S"
                                    )
                                    session.endDate = datetime.strftime(
                                        session.endDate, "%Y-%m-%d %H:%M:%S"
                                    )
                                except Exception:
                                    pass
                                sessions.append(utf_encode(asdict(session)))

                    except WebFault as e:
                        logging.getLogger("ispyb_client").exception(str(e))
                        sessions = []

                    res_proposal.append(
                        {
                            "Proposal": proposal,
                            "Person": utf_encode(asdict(person)),
                            "Laboratory": utf_encode(asdict(lab)),
                            "Session": sessions,
                        }
                    )
            else:
                logging.getLogger("ispyb_client").warning(
                    "No proposals for user %s found" % user_name
                )
        else:
            logging.getLogger("ispyb_client").exception(
                "Error in get_proposal: Could not connect to server,"
                + " returning empty proposal"
            )
        return res_proposal

    def get_proposal_by_username(self, username: str):
        proposal_code = ""
        proposal_number = 0

        empty_dict = {
            "Proposal": {},
            "Person": {},
            "Laboratory": {},
            "Session": {},
            "status": {"code": "error"},
        }

        if not self._shipping:
            logging.getLogger("ispyb_client").warning(
                "Error in get_proposal: Could not connect to server,"
                + " returning empty proposal"
            )
            return empty_dict

        try:
            try:
                person = self._shipping.service.findPersonByLogin(
                    username, self.beamline_name
                )
            except WebFault as e:
                logging.getLogger("ispyb_client").warning(str(e))
                person = {}

            try:
                proposal = self._shipping.service.findProposalByLoginAndBeamline(
                    username, self.beamline_name
                )
                if not proposal:
                    logging.getLogger("ispyb_client").warning(
                        "Error in get_proposal: No proposal has been found to  the user, returning empty proposal"
                    )
                    return empty_dict
                proposal_code = proposal.code
                proposal_number = proposal.number
            except WebFault as e:
                logging.getLogger("ispyb_client").warning(str(e))
                proposal = {}

            try:
                lab = self._shipping.service.findLaboratoryByCodeAndNumber(
                    proposal_code, proposal_number
                )
            except WebFault as e:
                logging.getLogger("ispyb_client").warning(str(e))
                lab = {}

            try:
                res_sessions = (
                    self._collection.service.findSessionsByProposalAndBeamLine(
                        proposal_code, proposal_number, self.beamline_name
                    )
                )
                sessions = []

                # Handels a list of sessions
                for session in res_sessions:
                    if session is not None:
                        try:
                            session.startDate = datetime.strftime(
                                session.startDate, "%Y-%m-%d %H:%M:%S"
                            )
                            session.endDate = datetime.strftime(
                                session.endDate, "%Y-%m-%d %H:%M:%S"
                            )
                        except Exception:
                            pass

                        sessions.append(utf_encode(asdict(session)))

            except WebFault as e:
                logging.getLogger("ispyb_client").warning(str(e))
                sessions = []

        except URLError:
            logging.getLogger("ispyb_client").warning(_CONNECTION_ERROR_MSG)
            return empty_dict

        logging.getLogger("ispyb_client").info(str(sessions))
        return {
            "Proposal": utf_encode(asdict(proposal)),
            "Person": utf_encode(asdict(person)),
            "Laboratory": utf_encode(asdict(lab)),
            "Session": sessions,
            "status": {"code": "ok"},
        }
