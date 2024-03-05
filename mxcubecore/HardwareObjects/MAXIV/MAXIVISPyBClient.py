import logging
import time
from socket import gethostname
from urllib.error import URLError
from suds import WebFault
from suds.sudsobject import asdict

from ISPyBClient import ISPyBClient
from ISPyBClient import utf_encode, trace

from mxcubecore import HardwareRepository as HWR

try:
    from sdm import SDM
except Exception as ex:
    raise Exception("Cannot import SDM library. Error was {}".format(ex))


class MAXIVISPyBClient(ISPyBClient):
    """
    Web-service client for ISPyB. MAX IV modifications for getting the main proposer from our DUO
    """

    def __init__(self, *args):
        ISPyBClient.__init__(self, *args)

    def init(self):
        ISPyBClient.init(self)
        self.sdm = SDM(production=True)

    def is_connected(self):
        # This is a hack. We auth via REST not via this hwobj
        # Returning True here since other parts need it
        # TODO: remove all SOAP calls
        return True

    def get_todays_session(self, prop, create_session=True):
        logging.getLogger("HWR").debug("Getting todays session")

        try:
            sessions = prop["Session"]
        except KeyError:
            sessions = None

        # Check if there are sessions in the proposal
        todays_session = None
        if sessions is None or len(sessions) == 0:
            pass
        else:
            # Check for today's session
            for session in sessions:
                beamline = session["beamlineName"]
                start_date = "%s 00:00:00" % session["startDate"].split()[0]
                end_date = "%s 23:59:59" % session["endDate"].split()[0]
                try:
                    start_struct = time.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
                else:
                    try:
                        end_struct = time.strptime(end_date, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                    else:
                        start_time = time.mktime(start_struct)
                        end_time = time.mktime(end_struct)
                        current_time = time.time()
                        # Check beamline name
                        if beamline == self.beamline_name:
                            # Check date
                            if current_time >= start_time and current_time <= end_time:
                                todays_session = session
                                break

        new_session_flag = False
        if todays_session is None and create_session:
            new_session_flag = True
            current_time = time.localtime()
            start_time = time.strftime("%Y-%m-%d 00:00:00", current_time)
            end_time = time.mktime(current_time) + 60 * 60 * 24
            tomorrow = time.localtime(end_time)
            end_time = time.strftime("%Y-%m-%d 07:59:59", tomorrow)

            # Create a session
            new_session_dict = {}
            new_session_dict["proposalId"] = prop["Proposal"]["proposalId"]
            new_session_dict["startDate"] = start_time
            new_session_dict["endDate"] = end_time
            new_session_dict["beamlineName"] = self.beamline_name
            new_session_dict["scheduled"] = 0
            new_session_dict["nbShifts"] = 3
            new_session_dict[
                "comments"
            ] = "Session created by {} for {}, hostname: {}".format(
                self.ws_username, self.beamline_name, gethostname()
            )
            session_id = self.create_session(new_session_dict)
            new_session_dict["sessionId"] = session_id

            todays_session = new_session_dict
            logging.getLogger("HWR").debug("create new session")
        elif todays_session:
            session_id = todays_session["sessionId"]
            logging.getLogger("HWR").debug("getting local contact for %s" % session_id)
        else:
            todays_session = {}

        is_inhouse = HWR.beamline.session.is_inhouse(
            prop["Proposal"]["code"], prop["Proposal"]["number"]
        )
        return {
            "session": todays_session,
            "new_session_flag": new_session_flag,
            "is_inhouse": is_inhouse,
        }

    @trace
    def get_proposal(self, proposal_code, proposal_number):
        """
        Returns the tuple (Proposal, Person, Laboratory, Session, Status).
        Containing the data from the coresponding tables in the database
        the status of the database operations are returned in Status.

        :param proposal_code: The proposal code
        :type proposal_code: str
        :param proposal_number: The proposal number
        :type propsoal_number: int

        :returns: The dict (Proposal, Person, Laboratory, Sessions, Status).
        :rtype: dict
        """

        _person = {}

        if self._shipping:
            try:
                try:
                    self.sdm = SDM(production=True)
                    proposer = self.sdm.uo.get_proposal_proposer(proposal_number)
                    # {'username': u'mikegu', 'lastname': u'Eguiraun', 'userid': 2776, 'firstname': u'Mikel'}
                    _person["familyName"] = proposer.get("lastname")
                    _person["givenName"] = proposer.get("firstname")
                    _person["login"] = proposer.get("username")
                except Exception as ex:
                    logging.getLogger("ispyb_client").warning(
                        "Cannot retrieve info from DUO/SDM; %s", str(ex)
                    )

                try:
                    _person_from_ispyb = self._shipping.service.findPersonByLogin(
                        proposer.get("username"), self.beamline_name
                    )
                    _person_from_ispysb = utf_encode(asdict(_person_from_ispyb))
                except WebFault as e:
                    logging.getLogger("ispyb_client").warning(str(e))
                    person = {}

                # now we merge both dicts, personId is the one in ispyb
                _person["emailAddress"] = _person_from_ispysb.get("emailAddress")
                _person["laboratoryId"] = _person_from_ispysb.get("laboratoryId")
                _person["personId"] = _person_from_ispysb.get("personId")

                person = _person

                try:
                    proposal = self._shipping.service.findProposal(
                        proposal_code, proposal_number
                    )

                    if proposal:
                        proposal.code = proposal_code
                    else:
                        return {
                            "Proposal": {},
                            "Person": {},
                            "Laboratory": {},
                            "Session": {},
                            "status": {"code": "error"},
                        }

                except WebFault as e:
                    logging.getLogger("ispyb_client").exception(str(e))
                    proposal = {}

                try:
                    lab = None
                    lab = self._shipping.service.findLaboratoryByProposal(
                        proposal_code, proposal_number
                    )

                    if not lab:
                        lab = {}

                except WebFault as e:
                    logging.getLogger("ispyb_client").exception(str(e))

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
                            except:
                                pass

                            sessions.append(utf_encode(asdict(session)))

                except WebFault as e:
                    logging.getLogger("ispyb_client").exception(str(e))
                    sessions = []

            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
                return {
                    "Proposal": {},
                    "Person": {},
                    "Laboratory": {},
                    "Session": {},
                    "status": {"code": "error"},
                }

            return {
                "Proposal": utf_encode(asdict(proposal)),
                "Person": person,
                "Laboratory": utf_encode(asdict(lab)),
                "Session": sessions,
                "status": {"code": "ok"},
            }

        else:
            logging.getLogger("ispyb_client").exception(
                "Error in get_proposal: Could not connect to server,"
                + " returning empty proposal"
            )

            return {
                "Proposal": {},
                "Person": {},
                "Laboratory": {},
                "Session": {},
                "status": {"code": "error"},
            }

    @trace
    def get_proposals_by_user(self, user_name):
        """
        Modified versio to filter by beamline
        """
        proposal_list = []
        res_proposal = []
        logging.getLogger("HWR").info("get_proposals_by_user")
        if self._disabled:
            return proposal_list

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

            logging.getLogger("HWR").info(proposal_list)

            try:
                import sdm

                sdm = sdm.SDM(production=True)
            except Exception as ex:
                print(ex)
                traceback.print_exc()
            filtered_list = []
            for prop in proposal_list:
                number = prop.get("number")
                logging.getLogger("HWR").info(number)

                _bl = (
                    sdm.uo.get_proposal_info(number)
                    .get("beamline_assigned", "unknown")
                    .lower()
                )
                if HWR.beamline.session.beamline_name.lower() in _bl:
                    filtered_list.append(prop)

            proposal_list = filtered_list

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
