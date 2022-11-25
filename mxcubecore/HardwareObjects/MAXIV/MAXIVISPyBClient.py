import logging
from urllib.parse import urljoin
from urllib.error import URLError
from suds import WebFault
from suds.sudsobject import asdict

from ISPyBClient import ISPyBClient
from ISPyBClient import utf_encode, trace

try:
    from sdm import SDM
except Exception as ex:
    raise Exception('Cannot import SDM library. Error was {}'.format(ex))


class MAXIVISPyBClient(ISPyBClient):
    """
    Web-service client for ISPyB. MAX IV modifications for getting the main proposer from our DUO
    """

    def __init__(self, *args):
        ISPyBClient.__init__(self, *args)

    def init(self):
        ISPyBClient.init(self)
        # self.__shipping = self._ISPyBClient__shipping
        # self.__collection = self._ISPyBClient__collection

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
                    # person = self.__shipping.service.\
                    #          findPersonByProposal(proposal_code,
                    #                               proposal_number)
                    _sdm = SDM(production=True)
                    proposer = _sdm.uo.get_proposal_proposer(proposal_number)
                    # {'username': u'mikegu', 'lastname': u'Eguiraun', 'userid': 2776, 'firstname': u'Mikel'}
                    _person['familyName'] = proposer.get('lastname')
                    _person['givenName'] = proposer.get('firstname')
                    _person['login'] = proposer.get('username')
                except Exception as ex:
                    logging.getLogger("ispyb_client").warning("Cannot retrieve info from DUO/SDM; %s", str(ex))

                try:
                    _person_from_ispyb = self._shipping.service.findPersonByLogin(proposer.get("username"), self.beamline_name)
                    _person_from_ispysb = utf_encode(asdict(_person_from_ispyb))
                except WebFault as e:
                    logging.getLogger("ispyb_client").warning(str(e))
                    person = {}

                # now we merge both dicts, personId is the one in ispyb
                _person['emailAddress'] = _person_from_ispysb.get('emailAddress')
                _person['laboratoryId'] = _person_from_ispysb.get('laboratoryId')
                _person['personId'] = _person_from_ispysb.get('personId')

                person = _person

                try:
                    proposal = self._shipping.service.\
                        findProposal(proposal_code,
                                     proposal_number)

                    if proposal:
                        proposal.code = proposal_code
                    else:
                        return {'Proposal': {},
                                'Person': {},
                                'Laboratory': {},
                                'Session': {},
                                'status': {'code':'error'}}

                except WebFault as e:
                    logging.getLogger("ispyb_client").exception(str(e))
                    proposal = {}

                try:
                    lab = None
                    lab = self._shipping.service.findLaboratoryByProposal(proposal_code, proposal_number)

                    if not lab:
                        lab = {}

                except WebFault as e:
                    logging.getLogger("ispyb_client").exception(str(e))

                    lab = {}
                try:
                    res_sessions = self._collection.service.\
                        findSessionsByProposalAndBeamLine(proposal_code,
                                                          proposal_number,
                                                          self.beamline_name)
                    sessions = []

                    # Handels a list of sessions
                    for session in res_sessions:
                        if session is not None :
                            try:
                                session.startDate = \
                                    datetime.strftime(session.startDate,
                                                      "%Y-%m-%d %H:%M:%S")
                                session.endDate = \
                                    datetime.strftime(session.endDate,
                                                      "%Y-%m-%d %H:%M:%S")
                            except:
                                pass

                            sessions.append(utf_encode(asdict(session)))

                except WebFault as e:
                    logging.getLogger("ispyb_client").exception(str(e))
                    sessions = []

            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
                return {'Proposal': {},
                        'Person': {},
                        'Laboratory': {},
                        'Session': {},
                        'status': {'code':'error'}}

            return  {'Proposal': utf_encode(asdict(proposal)),
                     'Person': person,
                     'Laboratory': utf_encode(asdict(lab)),
                     'Session': sessions,
                     'status': {'code':'ok'}}

        else:
            logging.getLogger("ispyb_client").\
                exception("Error in get_proposal: Could not connect to server," + \
                          " returning empty proposal")

            return {'Proposal': {},
                    'Person': {},
                    'Laboratory': {},
                    'Session': {},
                    'status': {'code':'error'}}
