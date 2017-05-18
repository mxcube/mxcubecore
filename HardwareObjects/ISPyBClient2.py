"""
A client for ISPyB Webservices.
"""

import logging
import gevent
import suds; logging.getLogger("suds").setLevel(logging.INFO)
import os
import itertools
import time
import json

from suds.transport.http import HttpAuthenticated
from suds.client import Client
from suds import WebFault
from suds.sudsobject import asdict
from urllib2 import URLError
from HardwareRepository.BaseHardwareObjects import HardwareObject
from datetime import datetime
from collections import namedtuple
from pprint import pformat


# Production web-services:    http://160.103.210.1:8080/ispyb-ejb3/ispybWS/
# Test web-services:          http://160.103.210.4:8080/ispyb-ejb3/ispybWS/

# The WSDL root is configured in the hardware object XML file.
#_WS_USERNAME, _WS_PASSWORD have to be configured in the HardwareObject XML file.
_WSDL_ROOT = ''
_WS_BL_SAMPLE_URL = _WSDL_ROOT + 'ToolsForBLSampleWebService?wsdl'
_WS_SHIPPING_URL = _WSDL_ROOT + 'ToolsForShippingWebService?wsdl'
_WS_COLLECTION_URL = _WSDL_ROOT + 'ToolsForCollectionWebService?wsdl'
_WS_AUTOPROC_URL = _WSDL_ROOT + 'ToolsForAutoprocessingWebService?wsdl'
_WS_USERNAME = None
_WS_PASSWORD = None

_CONNECTION_ERROR_MSG = "Could not connect to ISPyB, please verify that " + \
                        "the server is running and that your " + \
                        "configuration is correct"


SampleReference = namedtuple('SampleReference', ['code',
                                                 'container_reference',
                                                 'sample_reference',
                                                 'container_code'])

def trace(fun):
    def _trace(*args):
        log_msg = "lims client " + fun.__name__ + " called with: "

        for arg in args[1:]:
            try:
                log_msg += pformat(arg, indent = 4, width = 80) + ', '
            except:
                pass

        logging.getLogger("ispyb_client").debug(log_msg)
        result = fun(*args)

        try:
            result_msg = "lims client " + fun.__name__ + \
                " returned  with: " + pformat(result, indent = 4, width = 80)
        except:
            pass

        logging.getLogger("ispyb_client").debug(result_msg)
        return result

    return _trace


def in_greenlet(fun):
    def _in_greenlet(*args, **kwargs):
        log_msg = "lims client " + fun.__name__ + " called with: "

        for arg in args[1:]:
            try:
                log_msg += pformat(arg, indent = 4, width = 80) + ', '
            except:
                pass

        logging.getLogger("ispyb_client").debug(log_msg)
        task = gevent.spawn(fun, *args)
        if kwargs.get("wait", False):
          task.get()

    return _in_greenlet


def utf_encode(res_d):
    for key in res_d.iterkeys():
        if isinstance(res_d[key], dict):
            utf_encode(res_d)

        if isinstance(res_d[key], suds.sax.text.Text):
            try:
                res_d[key] = res_d[key].encode('utf8', 'ignore')
            except:
                pass

    return res_d


class ISPyBClient2(HardwareObject):
    """
    Web-service client for ISPyB.
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.ldapConnection=None
        self.beamline_name = "unknown"
        self.__shipping = None
        self.__collection = None
        self.__tools_ws = None
        self.__translations = {}
        self.__disabled = False

        self.authServerType = None
        self.loginType = None
        self.loginTranslate = None

        self.ws_username = None
        self.ws_password = None

    def init(self):
        """
        Init method declared by HardwareObject.
        """
        self.authServerType = self.getProperty('authServerType') or "ldap"
        if self.authServerType == "ldap":
            # Initialize ldap
            self.ldapConnection=self.getObjectByRole('ldapServer')
            if self.ldapConnection is None:
                logging.getLogger("HWR").debug('LDAP Server is not available')

        self.loginType = self.getProperty("loginType") or "proposal"
        self.loginTranslate = self.getProperty("loginTranslate") or True
        self.session_hwobj = self.getObjectByRole('session')
        self.beamline_name = self.session_hwobj.beamline_name

        self.ws_username = self.getProperty('ws_username')
        if not self.ws_username:
            self.ws_username = _WS_USERNAME
        self.ws_password = self.getProperty('ws_password')
        if not self.ws_password:
            self.ws_password = _WS_PASSWORD

        try:
            # ws_root is a property in the configuration xml file
            if self.ws_root:
                global _WSDL_ROOT
                global _WS_BL_SAMPLE_URL
                global _WS_SHIPPING_URL
                global _WS_COLLECTION_URL
                global _WS_SCREENING_URL
                global _WS_AUTOPROC_URL

                _WSDL_ROOT = self.ws_root.strip()
                _WS_BL_SAMPLE_URL = _WSDL_ROOT + \
                    'ToolsForBLSampleWebService?wsdl'
                _WS_SHIPPING_URL = _WSDL_ROOT + \
                    'ToolsForShippingWebService?wsdl'
                _WS_COLLECTION_URL = _WSDL_ROOT + \
                    'ToolsForCollectionWebService?wsdl'
                _WS_AUTOPROC_URL = _WSDL_ROOT + \
                    'ToolsForAutoprocessingWebService?wsdl'

                t1 = HttpAuthenticated(username = self.ws_username, 
                                      password = self.ws_password)
                
                t2 = HttpAuthenticated(username = self.ws_username, 
                                      password = self.ws_password)
                
                t3 = HttpAuthenticated(username = self.ws_username, 
                                      password = self.ws_password)

                t4 = HttpAuthenticated(username = self.ws_username,
                                       password = self.ws_password)
                
                try: 
                    self.__shipping = Client(_WS_SHIPPING_URL, timeout = 3,
                                             transport = t1, cache = None)
                    self.__collection = Client(_WS_COLLECTION_URL, timeout = 3,
                                               transport = t2, cache = None)
                    self.__tools_ws = Client(_WS_BL_SAMPLE_URL, timeout = 3,
                                             transport = t3, cache = None)
                    self.__autoproc_ws = Client(_WS_AUTOPROC_URL, timeout = 3,
                                             transport = t4, cache = None)
                
                    # ensure that suds do not create those files in tmp 
                    self.__shipping.set_options(cache=None)
                    self.__collection.set_options(cache=None)
                    self.__tools_ws.set_options(cache=None)
                    self.__autoproc_ws.set_options(cache=None)
                except URLError:
                    logging.getLogger("ispyb_client")\
                        .exception(_CONNECTION_ERROR_MSG)
                    return
        except:
            logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
            return

        # Add the porposal codes defined in the configuration xml file
        # to a directory. Used by translate()
        try:
            proposals = self.session_hwobj['proposals']
            for proposal in proposals:
                code = proposal.code
                self.__translations[code] = {}
                try:
                    self.__translations[code]['ldap'] = proposal.ldap
                except AttributeError:
                    pass
                try:
                    self.__translations[code]['ispyb'] = proposal.ispyb
                except AttributeError:
                    pass
                try:
                    self.__translations[code]['gui'] = proposal.gui
                except AttributeError:
                    pass
        except IndexError:
            pass

    def get_login_type(self):
        return self.loginType

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


    def clear_daily_email(self):
        raise NotImplementedException("Depricated ?")


    def send_email(self):
        raise NotImplementedException("Depricated ?")

    @trace
    def get_proposal_by_username(self, username):

        proposal_code   = ""
        proposal_number = 0

        empty_dict = {'Proposal': {}, 'Person': {}, 'Laboratory': {}, 'Session': {}, 'status': {'code':'error'}}

        if not self.__shipping:
           logging.getLogger("ispyb_client").\
                warning("Error in get_proposal: Could not connect to server," + \
                          " returning empty proposal")
           return empty_dict


        try:
            try:
                person = self.__shipping.service.findPersonByLogin(username, os.environ["SMIS_BEAMLINE_NAME"])
            except WebFault, e:
                logging.getLogger("ispyb_client").warning(e.message)
                person = {}

            try:
                proposal = self.__shipping.service.findProposalByLoginAndBeamline(username, os.environ["SMIS_BEAMLINE_NAME"])
                if not proposal:
                    logging.getLogger("ispyb_client").warning("Error in get_proposal: No proposal has been found to  the user, returning empty proposal")
                    return empty_dict
                proposal_code   = proposal.code
                proposal_number = proposal.number
            except WebFault, e:
                logging.getLogger("ispyb_client").warning(e.message)
                proposal = {}

            try:
                lab = self.__shipping.service.findLaboratoryByCodeAndNumber(proposal_code, proposal_number)
            except WebFault, e:
                logging.getLogger("ispyb_client").warning(e.message)
                lab = {}

            try:
                res_sessions = self.__collection.service.\
                    findSessionsByProposalAndBeamLine(proposal_code,
                                                           proposal_number,
                                                           os.environ["SMIS_BEAMLINE_NAME"])
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

            except WebFault, e:
                logging.getLogger("ispyb_client").warning(e.message)
                sessions = []

        except URLError:
            logging.getLogger("ispyb_client").warning(_CONNECTION_ERROR_MSG)
            return empty_dict


        logging.getLogger("ispyb_client").info( str(sessions) )
        return  {'Proposal': utf_encode(asdict(proposal)),
                 'Person': utf_encode(asdict(person)),
                 'Laboratory': utf_encode(asdict(lab)),
                 'Session': sessions,
                 'status': {'code':'ok'}}

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
        if self.__shipping:
            try:
                try:
                    person = self.__shipping.service.\
                             findPersonByProposal(proposal_code,
                                                  proposal_number)
                    if not person:
                        person = {}

                except WebFault, e:
                    logging.getLogger("ispyb_client").exception(str(e))
                    person = {}

                try:
                    proposal = self.__shipping.service.\
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

                except WebFault, e:
                    logging.getLogger("ispyb_client").exception(str(e))
                    proposal = {}

                try:
                    lab = None
                    #lab = self.__shipping.service.findLaboratoryByCodeAndNumber(proposal_code, proposal_number)
                    lab = self.__shipping.service.findLaboratoryByProposal(proposal_code, proposal_number)

                    if not lab:
                        lab = {}

                except WebFault, e:
                    logging.getLogger("ispyb_client").exception(str(e))

                    lab = {}
                try:
                    res_sessions = self.__collection.service.\
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

                except WebFault, e:
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
                     'Person': utf_encode(asdict(person)),
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

    @trace
    def get_proposal_by_username(self, username):

        proposal_code   = ""
        proposal_number = 0

        empty_dict = {'Proposal': {}, 'Person': {}, 'Laboratory': {}, 'Session': {}, 'status': {'code':'error'}}

        if not self.__shipping:
           logging.getLogger("ispyb_client").\
                warning("Error in get_proposal: Could not connect to server," + \
                          " returning empty proposal")
           return empty_dict


        try:
            try:
                person = self.__shipping.service.findPersonByLogin(username, self.beamline_name)
            except WebFault, e:
                logging.getLogger("ispyb_client").warning(str(e))
                person = {}

            try:
                proposal = self.__shipping.service.findProposalByLoginAndBeamline(username, self.beamline_name)
                if not proposal:
                    logging.getLogger("ispyb_client").warning("Error in get_proposal: No proposal has been found to  the user, returning empty proposal")
                    return empty_dict
                proposal_code   = proposal.code
                proposal_number = proposal.number
            except WebFault, e:
                logging.getLogger("ispyb_client").warning(str(e))
                proposal = {}

            try:
                lab = self.__shipping.service.findLaboratoryByCodeAndNumber(proposal_code, proposal_number)
            except WebFault, e:
                logging.getLogger("ispyb_client").warning(str(e))
                lab = {}

            try:
                res_sessions = self.__collection.service.\
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

            except WebFault, e:
                logging.getLogger("ispyb_client").warning(str(e))
                sessions = []

        except URLError:
            logging.getLogger("ispyb_client").warning(_CONNECTION_ERROR_MSG)
            return empty_dict


        logging.getLogger("ispyb_client").info( str(sessions) )
        return  {'Proposal': utf_encode(asdict(proposal)),
                 'Person': utf_encode(asdict(person)),
                 'Laboratory': utf_encode(asdict(lab)),
                 'Session': sessions,
                 'status': {'code':'ok'}}

    @trace
    def get_session_local_contact(self, session_id):
        """
        Retrieves the person entry associated with the session id <session_id>

        :param session_id:
        :type session_id: int
        :returns: Person object as dict.
        :rtype: dict
        """

        if self.__shipping:

            try:
                person = self.__shipping.service.\
                    findPersonBySessionIdLocalContact(session_id)
            except WebFault, e:
                logging.getLogger("ispyb_client").exception(str(e))
                person = {}
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
                person = {}

            if person is None:
                return {}
            else:
                utf_encode(asdict(person))

        else:
            logging.getLogger("ispyb_client").\
                exception("Error in get_session_local_contact: Could not get " + \
                          "local contact")
            return {}

    def _ispybLogin (self, loginID, psd):
        # to do, check how it is done in EMBL
        return True, "True"

    def login (self,loginID, psd, ldap_connection=None):
        if ldap_connection is None:
            ldap_connection = self.ldapConnection
        login_name=loginID
        proposal_code = ""
        proposal_number = ""

        # For porposal login, split the loginID to code and numbers
        if self.loginType == "proposal" :
            proposal_code = "".join(itertools.takewhile(lambda c: not c.isdigit(), loginID))
            proposal_number = loginID[len(proposal_code):]

        # if translation of the loginID is needed, need to be tested by ESRF
        if self.loginTranslate is True:
            login_name=self.translate(proposal_code,'ldap')+str(proposal_number)

        # Authentication
        if self.authServerType == 'ldap':
            logging.getLogger('HWR').debug('LDAP login')
            ok, msg=ldap_connection.login(login_name,psd)
        elif self.authServerType == 'ispyb':
            logging.getLogger('HWR').debug('ISPyB login')
            ok, msg=self._ispybLogin(login_name,psd)
        else:
            raise Exception ("Authentication server type is not defined")

        if not ok:
            msg="%s." % msg.capitalize()
            # refuse Login
            return {'status':{ "code": "error", "msg": msg }, 'Proposal': None, 'session': None}

        # login succeed, get proposal and sessions
        #logging.getLogger('HWR').debug('Logged in: querying ISPyB database...')
        if self.loginType == "proposal":
            # get the proposal ID
            prop=self.get_proposal(proposal_code,proposal_number)
        elif self.loginType =="user":
            prop=self.get_proposal_by_username(loginID)

        # Check if everything went ok
        prop_ok=True
        try:
            prop_ok=(prop['status']['code']=='ok')
        except KeyError:
            prop_ok=False
        if not prop_ok:
#todo
            msg =  "Couldn't contact the ISPyB database server: you've been logged as the local user.\nYour experiments' information will not be stored in ISPyB"
            return {'status':{ "code": "ispybDown", "msg": msg }, 'Proposal': None, 'session': None}

#        logging.getLogger('HWR').debug('Proposal is fine, get sessions from ISPyB...')
#        logging.getLogger('HWR').debug(prop)

        proposal=prop['Proposal']
        todays_session=self.get_todays_session(prop)

#        logging.getLogger('HWR').debug(todays_session)
        return {'status':{ "code": "ok", "msg": msg }, 'Proposal': proposal,
        'session': todays_session,
        "local_contact": self.get_session_local_contact(todays_session['session']['sessionId']),
        "person": prop['Person'],
        "laboratory": prop['Laboratory']}

    def get_todays_session(self, prop):
        try:
            sessions=prop['Session']
        except KeyError:
            sessions=None
        # Check if there are sessions in the proposal
        todays_session=None
        if sessions is None or len(sessions)==0:
            pass
        else:
            # Check for today's session
            for session in sessions:
                beamline=session['beamlineName']
                start_date="%s 00:00:00" % session['startDate'].split()[0]
                end_date="%s 23:59:59" % session['endDate'].split()[0]
                try:
                    start_struct=time.strptime(start_date,"%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
                else:
                    try:
                        end_struct=time.strptime(end_date,"%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                    else:
                        start_time=time.mktime(start_struct)
                        end_time=time.mktime(end_struct)
                        current_time=time.time()
                        # Check beamline name
                        if beamline==self.beamline_name:
                            # Check date
                            if current_time>=start_time and current_time<=end_time:
                                todays_session=session
                                break
        new_session_flag= False
        if todays_session is None:
            # a newSession will be created, UI (Qt, web) can decide to accept the newSession or not
            new_session_flag= True
            current_time=time.localtime()
            start_time=time.strftime("%Y-%m-%d 00:00:00", current_time)
            end_time=time.mktime(current_time)+60*60*24
            tomorrow=time.localtime(end_time)
            end_time=time.strftime("%Y-%m-%d 07:59:59", tomorrow)

            # Create a session
            new_session_dict={}
            new_session_dict['proposalId']=prop['Proposal']['proposalId']
            new_session_dict['startDate']=start_time
            new_session_dict['endDate']=end_time
            new_session_dict['beamlineName']=self.beamline_name
            new_session_dict['scheduled']=0
            new_session_dict['nbShifts']=3
            new_session_dict['comments']="Session created by the BCM"
            session_id=self.create_session(new_session_dict)
            new_session_dict['sessionId']=session_id

            todays_session=new_session_dict
            localcontact=None
            logging.getLogger('HWR').debug('create new session')

        else:
            session_id=todays_session['sessionId']
            logging.getLogger('HWR').debug('getting local contact for %s' % session_id)
            localcontact=self.get_session_local_contact(session_id)

        is_inhouse = self.session_hwobj.is_inhouse(prop['Proposal']["code"], prop['Proposal']["number"])
        return {"session": todays_session,"new_session_flag":new_session_flag, "is_inhouse": is_inhouse}


    @trace
    def store_data_collection(self, *args, **kwargs):
        try:
          return self._store_data_collection(*args, **kwargs)
        except gevent.GreenletExit:
          # aborted by user ('kill')
          raise
        except:
          # if anything else happens, let upper level process continue
          # (not a fatal error), but display exception still
          logging.exception("Could not store data collection")
          return (0,0,0)

    def _store_data_collection(self, mx_collection, beamline_setup = None):
        """
        Stores the data collection mx_collection, and the beamline setup
        if provided.

        :param mx_collection: The data collection parameters.
        :type mx_collection: dict

        :param beamline_setup: The beamline setup.
        :type beamline_setup: dict

        :returns: None

        """
        if self.__disabled:
            return (0,0,0)

        if self.__collection:
            data_collection = ISPyBValueFactory().\
                from_data_collect_parameters(self.__collection, mx_collection)

            if beamline_setup:
                lims_beamline_setup = ISPyBValueFactory.\
                    from_bl_config(self.__collection, beamline_setup)
          
                lims_beamline_setup.synchrotronMode = \
                    data_collection.synchrotronMode

                self.store_beamline_setup(mx_collection['sessionId'],
                                          lims_beamline_setup )

                detector_params = \
                    ISPyBValueFactory().detector_from_blc(beamline_setup,
                                                          mx_collection)

                detector = self.find_detector(*detector_params)
                detector_id = 0

                if detector:
                    detector_id = detector.detectorId
                    data_collection.detectorId = detector_id

            collection_id = self.__collection.service.\
                            storeOrUpdateDataCollection(data_collection)

            return (collection_id, detector_id)
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in store_data_collection: could not connect" + \
                          " to server")


    @trace
    def store_beamline_setup(self, session_id, beamline_setup):
        """
        Stores the beamline setup dict <beamline_setup>.

        :param session_id: The session id that the beamline_setup
                           should be associated with.
        :type session_id: int

        :param beamline_setup: The dictonary with beamline settings.
        :type beamline_setup: dict

        :returns beamline_setup_id: The database id of the beamline setup.
        :rtype: str
        """
        blSetupId = None
        if self.__collection:

            session = {}

            try:
                session = self.get_session(session_id)
            except:
                logging.getLogger("ispyb_client").exception(\
                    "ISPyBClient: exception in store_beam_line_setup")
            else:
                if session is not None:
                    try:
                        blSetupId = self.__collection.service.\
                                     storeOrUpdateBeamLineSetup(beamline_setup)

                        session['beamLineSetupId'] = blSetupId
                        self.update_session(session)

                    except WebFault, e:
                        logging.getLogger("ispyb_client").exception(str(e))
                    except URLError:
                        logging.getLogger("ispyb_client").\
                            exception(_CONNECTION_ERROR_MSG)
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in store_beamline_setup: could not connect" + \
                          " to server")

        return blSetupId


    #@trace
    @in_greenlet
    def update_data_collection(self, mx_collection, wait=False):
        """
        Updates the datacollction mx_collection, this requires that the
        collectionId attribute is set and exists in the database.

        :param mx_collection: The dictionary with collections parameters.
        :type mx_collection: dict

        :returns: None
        """
        if self.__disabled:
            return

        if self.__collection:
            if 'collection_id' in mx_collection:
                try:
                    # Update the data collection group
                    self.store_data_collection_group(mx_collection)
                    data_collection = ISPyBValueFactory().\
                        from_data_collect_parameters(self.__collection, mx_collection)
                    self.__collection.service.\
                        storeOrUpdateDataCollection(data_collection)
                except WebFault:
                    logging.getLogger("ispyb_client").\
                        exception("ISPyBClient: exception in update_data_collection")
                except URLError:
                    logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
            else:
                logging.getLogger("ispyb_client").error("Error in update_data_collection: " + \
                                        "collection-id missing, the ISPyB data-collection is not updated.")

        else:
            logging.getLogger("ispyb_client").\
                exception("Error in update_data_collection: could not connect" + \
                          " to server")


    @trace
    def update_bl_sample(self, bl_sample):
        """
        Creates or stos a BLSample entry.

        :param sample_dict: A dictonary with the properties for the entry.
        :type sample_dict: dict
        """
        if self.__disabled:
           return {}

        if self.__tools_ws:
            try:
                status = self.__tools_ws.service.\
                    storeOrUpdateBLSample(bl_sample)
            except WebFault, e:
                logging.getLogger("ispyb_client").exception(str(e))
                status = {}
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            return status
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in update_bl_sample: could not connect to server")


    #@in_greenlet
    def store_image(self, image_dict):
        """
        Stores the image (image parameters) <image_dict>

        :param image_dict: A dictonary with image pramaters.
        :type image_dict: dict

        :returns: None
        """
        if self.__disabled:
            return
    
        if self.__collection:
            if 'dataCollectionId' in image_dict:
                try:
                    image_id = self.__collection.service.storeOrUpdateImage(image_dict)
                    return image_id
                except WebFault:
                    logging.getLogger("ispyb_client").\
                        exception("ISPyBClient: exception in store_image")
                except URLError:
                    logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
            else:
                logging.getLogger("ispyb_client").error("Error in store_image: " + \
                                                        "data_collection_id missing, could not store image in ISPyB")
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in store_image: could not connect to server")


    def __find_sample(self, sample_ref_list, code = None, location = None):
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
        for sample_ref in sample_ref_list:

            if code and location:
                if sample_ref.code == code and \
                        sample_ref.container_reference == location[0] and \
                        sample_ref.sample_reference == location[1]:
                    return sample_ref
            elif code:
                if sample_ref.code == code:
                    return sample_ref
            elif location:
                if sample_ref.container_reference == location[0] and \
                       sample_ref.sample_reference == location[1]:
                    return sample_ref

        return None


    @trace
    def get_samples(self, proposal_id, session_id):
        response_samples = None

        if self.__tools_ws:
            try:
                response_samples = self.__tools_ws.service.\
                    findSampleInfoLightForProposal(proposal_id,
                                                   self.beamline_name)
            except WebFault, e:
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in get_samples: could not connect to server")

        return response_samples


    @trace
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
        if self.__tools_ws:
            sample_references = []
            session = self.get_session(session_id)
            response_samples = []

            for sample_ref in sample_refs:
                sample_reference = SampleReference(*sample_ref)
                sample_references.append(sample_reference)

            try:
                response_samples = self.__tools_ws.service.\
                    findSampleInfoLightForProposal(proposal_id,
                                                   self.beamline_name)

            except WebFault, e:
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            samples = []
            for sample in response_samples:
                try:
                    loc = [None, None]
                    try:
                      loc[0]=int(sample.containerSampleChangerLocation)
                    except:
                      pass
                    try:
                      loc[1]=int(sample.sampleLocation)
                    except:
                      pass

                    # Unmatched sample, just catch and do nothing
                    # (dont remove from sample_ref)
                    if not sample.code and \
                            not sample.sampleLocation:
                        pass
                    # Sample location and code was found in ISPyB and they match
                    # with the sample changer.
                    elif sample.code and sample.sampleLocation:
                        sc_sample = \
                            self.__find_sample(sample_references,
                                               code = sample.code,
                                               location = loc)

                        # The sample codes dose not match
                        if not sc_sample:
                            sc_sample = self.__find_sample(sample_references,
                                                           location = loc)

                            if sc_sample.code != '':
                                sample.code = sc_sample.code

                        sample_references.remove(sc_sample)


                    # Only location was found, update with the code
                    # from sample changer if it exists.
                    elif sample.sampleLocation:
                        sc_sample = \
                            self.__find_sample(sample_references,
                                               location = loc)
                        if sc_sample:
                            sample.sampleCode = sc_sample.code
                            sample_references.remove(sc_sample)

                    # Sample code was found in ISPyB but dosent match with
                    # the samplechanger at given location
                    #
                    # Use the information from the sample changer.
                    else:
                        #Use sample changer code for sample  ?
                        sample.containerSampleChangerLocation = \
                            sample_references.containter_referance
                        sample.sampleLocation = \
                            sample_references.sample_reference

                        loc = (int(sample.containerSampleChangerLocation),
                               int(sample.sampleLocation))

                        sc_sample = \
                            self.__find_sample(sample_references,
                                               location = loc)
                        if sc_sample:
                            sample.code = sc_sample.code
                            sample_references.remove(sc_sample)


                    samples.append(utf_encode(asdict(sample)))

#                         {'BLSample': utf_encode(asdict(sample.blSample)),
#                          'Container': utf_encode(asdict(sample.container)),
#                          'Crystal': utf_encode(asdict(sample.crystal)),
#                          'DiffractionPlan_BLSample': \
#                              utf_encode(asdict(sample.diffractionPlan)),
#                          'Protein': utf_encode(asdict(sample.protein))})
                except:
                    pass


            # Add the unmatched samples to the result from ISPyB
            for sample_ref in sample_references:
                samples.append(
                    {'code': sample_ref.code,
                     'location': sample_ref.sample_reference,
                     'containerSampleChangerLocation': sample_ref.container_reference})
                #  samples.append(
#                     {'BLSample': {'code': sample_ref.code,
#                                   'location': \
#                                   sample_ref.sample_reference},
#                      'Container': {'sampleChangerLocation': \
#                                        sample_ref.container_reference},
#                      'Crystal': {},
#                      'DiffractionPlan_BLSample': {},
#                      'Protein': {}})


            return {'loaded_sample': samples,
                    'status': {'code':'ok'}}
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in get_session_samples: could not connect " + \
                          "to server")


    @trace
    def get_bl_sample(self, bl_sample_id):
        """
        Fetch the BLSample entry with the id bl_sample_id

        :param bl_sample_id:
        :type bl_sample_id: int

        :returns: A BLSampleWSValue, defined in the wsdl.
        :rtype: BLSampleWSValue

        """

        if self.__tools_ws:

            try:
                result = self.__tools_ws.service.findBLSample(bl_sample_id)
            except WebFault, e:
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            return utf_encode(asdict(result))
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in get_bl_sample: could not connect to server")

    @trace
    def create_session(self, session_dict):
        """
        Create a new session for "current proposal", the attribute
        porposalId in <session_dict> has to be set (and exist in ISPyB).

        :param session_dict: Dictonary with session parameters.
        :type session_dict: dict

        :returns: The session id of the created session.
        :rtype: int
        """
        if self.__collection:

            try:
                # The old API used date formated strings and the new
                # one uses DateTime objects.
                session_dict["startDate"]  = datetime.\
                    strptime(session_dict["startDate"] , "%Y-%m-%d %H:%M:%S")
                session_dict["endDate"] = datetime.\
                    strptime(session_dict["endDate"], "%Y-%m-%d %H:%M:%S")

                session = self.__collection.service.\
                    storeOrUpdateSession(session_dict)

                # changing back to string representation of the dates,
                # since the session_dict is used after this method is called,
                session_dict["startDate"]  = datetime.\
                    strftime(session_dict["startDate"] , "%Y-%m-%d %H:%M:%S")
                session_dict["endDate"] = datetime.\
                    strftime(session_dict["endDate"], "%Y-%m-%d %H:%M:%S")

            except WebFault, e:
                session = {}
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            return session
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in create_session: could not connect to server")


    @trace
    def update_session(self, session_dict):
        """
        Update the session with the data in <session_dict>, the attribute
        sessionId in <session_dict> must be set.

        Warning: Missing attibutes in <session_dict> will set to null,
                 this could leed to loss of data.

        :param session_dict: The session to update.
        :type session_dict: dict

        :returns: None
        """
        if self.__collection:
            return self.create_session(session_dict)
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in update_session: could not connect to server")

    @trace
    def store_energy_scan(self, energyscan_dict):
        """
        Store energyscan.

        :param energyscan_dict: Energyscan data to store.
        :type energyscan_dict: dict

        :returns Dictonary with the energy scan id:
        :rtype: dict
        """
        if self.__collection:

            status = {'energyScanId': -1}

            try:
                energyscan_dict['startTime'] = datetime.\
                    strptime(energyscan_dict["startTime"], "%Y-%m-%d %H:%M:%S")

                energyscan_dict['endTime'] = datetime.\
                    strptime(energyscan_dict["endTime"], "%Y-%m-%d %H:%M:%S")

                try:
                  del energyscan_dict['remoteEnergy']
                except KeyError:
                  pass

                status['energyScanId'] = self.__collection.service.\
                    storeOrUpdateEnergyScan(energyscan_dict)

            except WebFault:
                logging.getLogger("ispyb_client").\
                    exception("ISPyBClient: exception in store_energy_scan")
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            return status
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in store_energy_scan: could not connect to" \
                          + " server")

    @trace
    def associate_bl_sample_and_energy_scan(self, entry_dict):

        if self.__collection:

            try:
                result = self.__collection.service.\
                    storeBLSampleHasEnergyScan(entry_dict['energyScanId'],
                                               entry_dict['blSampleId'])

            except WebFault, e:
                result = -1
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            return result
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in associate_bl_sample_and_energy_scan: could" + \
                          " not connect to server")

    @trace
    def get_data_collection(self, data_collection_id):
        """
        Retrives the data collection with id <data_collection_id>

        :param data_collection_id: Id of data collection.
        :type data_collection_id: int

        :rtype: dict
        """
        if self.__collection:

            try:
                dc_response = self.__collection.service.\
                    findDataCollection(data_collection_id)

                dc = utf_encode(asdict(dc_response))
                dc['startTime'] = datetime.\
                    strftime(dc["startTime"] , "%Y-%m-%d %H:%M:%S")
                dc['endTime'] =  datetime.\
                    strftime(dc["endTime"] , "%Y-%m-%d %H:%M:%S")

            except WebFault, e:
                dc = {}
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError:
                dc = {}
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            return dc
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in get_data_collection: could not connect" + \
                          " to server")


    @trace
    def get_data_collection_id(self, dc_dict):

        if self.__collection.service:

            try:
                dc = self.__collection.service.\
                    findDataCollectionFromImageDirectoryAndImagePrefixAndNumber(
                    dc_dict['directory'], dc_dict['prefix'],
                    dc_dict['run_number'])
            except WebFault, e:
                dc = {}
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            return dc
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in get_data_collection_id: could not" + \
                      " connect to server")


    @trace
    def get_sample_last_data_collection(self, blsampleid):
        raise NotImplementedException("Unused method ?")


    @trace
    def get_session(self, session_id):
        """
        Retrieves the session with id <session_id>.

        :returns: Dictionary with session data.
        :rtype: dict
        """
        if self.__collection:
            session = {}
            try:
                session = self.__collection.service.\
                    findSession(session_id)

                if session is not None :
                    session.startDate = datetime.strftime(session.startDate,
                                                          "%Y-%m-%d %H:%M:%S")
                    session.endDate = datetime.strftime(session.endDate,
                                                        "%Y-%m-%d %H:%M:%S")
                    session = utf_encode(asdict(session))

            except WebFault, e:
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            return session

        else:
            logging.getLogger("ispyb_client").\
                exception("Error in get_session: could not connect to server")

    @trace
    def store_xfe_spectrum(self, xfespectrum_dict):
        """
        Stores a xfe spectrum.

        :returns: A dictionary with the xfe spectrum id.
        :rtype: dict

        """
        status = {'xfeFluorescenceSpectrumId': -1}

        if self.__collection:

            try:
                xfespectrum_dict['startTime'] = datetime.\
                    strptime(xfespectrum_dict["startTime"],"%Y-%m-%d %H:%M:%S")

                xfespectrum_dict['endTime'] = datetime.\
                    strptime(xfespectrum_dict["endTime"], "%Y-%m-%d %H:%M:%S")

                status['xfeFluorescenceSpectrumId'] = \
                    self.__collection.service.\
                    storeOrUpdateXFEFluorescenceSpectrum(xfespectrum_dict)

            except WebFault:
                logging.getLogger("ispyb_client").\
                    exception("ISPyBClient: exception in store_xfe_spectrum")
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

            return status
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in store_xfe_spectrum: could not connect to" +
                      " server")

    def disable(self):
        self.__disabled = True


    def enable(self):
        self.__disabled = False


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
        for proposal in self['inhouse']:
            if proposal_code == proposal.code:
                if str(proposal_number) == str(proposal.number):
                    return True
        return False


    def find_detector(self, type, manufacturer,
                      model, mode):
        """
        Returns the Detector3VO object with the characteristics
        matching the ones given.
        """

        if self.__collection:
            try:
                res= self.__collection.service.\
                       findDetectorByParam("", manufacturer, model, mode)
                return res
            except WebFault:
                logging.getLogger("ispyb_client").\
                    exception("ISPyBClient: exception in find_detector")
        else:
            logging.getLogger("ispyb_client").\
                exception("Error find_detector: could not connect to" +
                      " server")


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

        if self.__collection:
            group = ISPyBValueFactory().dcg_from_dc_params(self.__collection, mx_collection)

            group_id = self.__collection.service.\
                       storeOrUpdateDataCollectionGroup(group)

            return group_id


    def _store_data_collection_group(self, group_data):
        """
        """
        group_id = self.__collection.service.\
                   storeOrUpdateDataCollectionGroup(group_data)

        return group_id

    @trace
    def get_proposals_by_user(self, user_name):
        proposal_list = []
        res_proposal = []

        if self.__disabled:
            return proposal_list

        if self.__shipping:
            try:
               proposals = eval(self.__shipping.service.\
                  findProposalsByLoginName(user_name))  
               if proposal_list is not None:
                   for proposal in proposals:
                        if proposal['type'].upper() in ['MX', 'MB'] and \
                           proposal not in proposal_list:
                           proposal_list.append(proposal)
            except WebFault, e:
               proposal_list = []
               logging.getLogger("ispyb_client").exception(e.message)

            res_proposal = []
            if len(proposal_list) > 0:
                for proposal in proposal_list:

                    proposal_code = proposal['code']
                    proposal_number = proposal['number']

                    #person
                    try:
                        person = self.__shipping.service.\
                                      findPersonByProposal(proposal_code,
                                                           proposal_number)
                        if not person:
                            person = {}
                    except WebFault, e:
                        logging.getLogger("ispyb_client").exception(e.message)
                        person = {}

                    #lab
                    try:
                        lab = self.__shipping.service.\
                                   findLaboratoryByProposal(proposal_code,
                                                            proposal_number)
                        if not lab:
                            lab = {}
                    except WebFault, e:
                        logging.getLogger("ispyb_client").exception(e.message)
                        lab = {}

                    #sessions
                    try:
                        res_sessions = self.__collection.service.\
                               findSessionsByProposalAndBeamLine(proposal_code,
                                                                 proposal_number,
                                                                 self.beamline_name)
                        sessions = []
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

                    except WebFault, e:
                        logging.getLogger("ispyb_client").exception(e.message)
                        sessions = []

                    
                    res_proposal.append({'Proposal': proposal,
                                         'Person': utf_encode(asdict(person)),
                                         'Laboratory': utf_encode(asdict(lab)),
                                         'Session' : sessions})
            else:
                logging.getLogger("ispyb_client").\
                   warning("No proposals for user %s found" %user_name)
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in get_proposal: Could not connect to server," + \
                          " returning empty proposal")
        return res_proposal 

    def store_autoproc_program(self, autoproc_program_dict):
        """
        """
        autoproc_program_id = None
        try:
            autoproc_program_id = self.__autoproc_ws.service.\
                storeOrUpdateAutoProcProgram(\
                   processingPrograms = autoproc_program_dict["processing_programs"],
                   processingStatus = 1, #make correct
                   processingStartTime = datetime.strptime(autoproc_program_dict\
                        ["processing_start_time"], "%Y-%m-%d %H:%M:%S"),
                   processingEndTime = datetime.strptime(autoproc_program_dict\
                        ["processing_end_time"], "%Y-%m-%d %H:%M:%S"))
        except ex:
            msg = 'Could not store autoprocessing program in lims: %s' % ex.message
            logging.getLogger("ispyb_client").exception(msg)
        return autoproc_program_id

    @trace
    def store_workflow(self, *args, **kwargs):
        try:
          return self._store_workflow(*args, **kwargs)
        except gevent.GreenletExit:
          raise
        except:
          logging.exception("Could not store workflow")
          return None, None, None

    def store_workflow_step(self, *args, **kwargs):
        try:
          return self._store_workflow_step(*args, **kwargs)
        except gevent.GreenletExit:
          raise
        except:
          logging.exception("Could not store workflow step")
          return None

    def _store_workflow(self, info_dict):
        """
        :param mx_collection: The data collection parameters.
        :type mx_collection: dict
        :returns: None
        """
        if self.__disabled:
            return None, None, None

        workflow_id = None
        workflow_mesh_id = None
        grid_info_id = None

        if self.__collection:
            workflow_vo = ISPyBValueFactory().\
                workflow_from_workflow_info(info_dict)
            workflow_id = self.__collection.service.\
                          storeOrUpdateWorkflow(workflow_vo)

            workflow_mesh_vo = ISPyBValueFactory().\
                 workflow_mesh_from_workflow_info(info_dict)
            workflow_mesh_vo.workflowId = workflow_id

            workflow_mesh_id = self.__collection.service.\
                               storeOrUpdateWorkflowMesh(workflow_mesh_vo)

            grid_info_vo = ISPyBValueFactory().\
               grid_info_from_workflow_info(info_dict)
            grid_info_vo.workflowMeshId = workflow_mesh_id

            grid_info_id = self.__collection.service.\
                           storeOrUpdateGridInfo(grid_info_vo)
            return workflow_id, workflow_mesh_id, grid_info_id
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in store_workflow: could not connect" + \
                          " to server")
        return workflow_id, workflow_mesh_id, grid_info_id

    def _store_workflow_step(self, workflow_info_dict): 
        """
        :param mx_collection: The data collection parameters.
        :type mx_collection: dict
        :returns: None
        """
        if self.__disabled:
            return None

        workflow_step_id = None
        if self.__collection:
            workflow_step_dict = {}
            workflow_step_dict['workflowId'] = workflow_info_dict.get("workflow_id")
            workflow_step_dict['workflowStepType'] = workflow_info_dict.get("workflow_type", "MeshScan")
            workflow_step_dict['status'] = workflow_info_dict.get("status", "")
            workflow_step_dict['folderPath'] = workflow_info_dict.get("result_file_path", "")
            workflow_step_dict['imageResultFilePath'] = os.path.join(\
                workflow_step_dict['folderPath'], "parallel_processing_result.png")
            workflow_step_dict['htmlResultFilePath'] = os.path.join(\
                workflow_step_dict['folderPath'], "index.html")
            workflow_step_dict['resultFilePath'] = os.path.join(\
                workflow_step_dict['folderPath'], "index.html")
            workflow_step_dict['comments'] = workflow_info_dict.get("comments", "")
            workflow_step_dict['crystalSizeX'] = workflow_info_dict.get("crystal_size_x")
            workflow_step_dict['crystalSizeY'] = workflow_info_dict.get("crystal_size_y")
            workflow_step_dict['crystalSizeZ'] = workflow_info_dict.get("crystal_size_z")
            workflow_step_dict['maxDozorScore'] = workflow_info_dict.get("max_dozor_score")

            workflow_step_id = self.__collection.service.\
                          storeWorkflowStep(json.dumps(workflow_step_dict))
        else:
            logging.getLogger("ispyb_client").\
                exception("Error in store_workflow step: could not connect" + \
                          " to server")
        return workflow_step_id
        

    def store_image_quality_indicators(self, image_dict):
        """Stores image quality indicators
        """
        quality_ind_id = -1
        quality_ind_dict = {"imageId": image_dict["image_id"],
                            "autoProcProgramId": image_dict["auto_proc_program"],
                            "dozor_score": image_dict["score"],
                            "spotTotal" : image_dict["spots_num"],
                            "goodBraggCandidates": image_dict["spots_num"],
                            "totalIntegratedSignal": image_dict["spots_int_aver"],
                            "method1Res": image_dict["spots_resolution"]}
        try:
           quality_ind_id = self.__autoproc_ws.service.\
                storeOrUpdateImageQualityIndicators(quality_ind_dict)
        except ex:
            msg = 'Could not store image quality indicators in lims: %s' % ex.message
            logging.getLogger("ispyb_client").exception(msg)
        return quality_ind_id

    def set_image_quality_indicators_plot(self, collection_id, plot_path, csv_path):
        """Assigns image quality indicators png and csv filenames to collection"""
        try:
            self.__collection.service.setImageQualityIndicatorsPlot(\
                collection_id, plot_path, csv_path)
        except ex:
            msg = 'Could not set image quality indicators in lims: %s' % ex.message
            logging.getLogger("ispyb_client").exception(msg)

    def store_robot_action(self, sample_id, session_id, robot_action_dict):
        """Stores robot action"""
        try:
            ws_client = Client(_WS_COLLECTION_URL,
                               cache = None)
            robot_action_vo = ws_client.factory.create('robotActionWS3VO')
            robot_action_vo.sessionId = session_id
            robot_action_vo.blSampleId = sample_id
            action_id = self.__collection.service.storeRobotAction(robot_action_vo)
        except ex:
            msg = 'Could not store robot action in lims: %s' % ex.message
            logging.getLogger("ispyb_client").exception(msg)
    

    # Bindings to methods called from older bricks.
    getProposal = get_proposal
    getSessionLocalContact = get_session_local_contact
    createSession = create_session
    getSessionSamples = get_session_samples
    getSession = get_session
    storeDataCollection = store_data_collection
    storeBeamLineSetup = store_beamline_setup
    getDataCollection = get_data_collection
    updateBLSample = update_bl_sample
    getBLSample = get_bl_sample
    associateBLSampleAndEnergyScan = associate_bl_sample_and_energy_scan
    updateDataCollection = update_data_collection
    storeImage = store_image
    storeEnergyScan = store_energy_scan
    storeXfeSpectrum = store_xfe_spectrum

    # Methods that seems to be unused
    getSampleLastDataCollection = get_sample_last_data_collection
    getDataCollectionId = get_data_collection_id


class ISPyBValueFactory():
    """
    Constructs ws objects from "old style" mxCuBE dictonaries.
    """
    @staticmethod
    def detector_from_blc(bl_config, mx_collect_dict):
        try:
            detector_manufacturer = bl_config.detector_manufacturer

            if type(detector_manufacturer) is str:
                detector_manufacturer = detector_manufacturer.upper()
        except:
            detector_manufacturer = ""

        try:
            detector_type = bl_config.detector_type
        except:
            detector_type = ""

        try:
            detector_model = bl_config.detector_model
        except:
            detector_model = ""

        try:
            modes=("Software binned", "Unbinned", "Hardware binned")
            det_mode = int(mx_collect_dict['detector_mode'])
            detector_mode = modes[det_mode]
        except (KeyError, IndexError, ValueError, TypeError):
            detector_mode = ""

        return (detector_type, detector_manufacturer,
                detector_model, detector_mode)


    @staticmethod
    def from_bl_config(ws_client, bl_config):
        """
        Creates a beamLineSetup3VO from the bl_config dictionary.
        :rtype: beamLineSetup3VO
        """
        beamline_setup = None
        try:
            beamline_setup = ws_client.factory.create('ns0:beamLineSetup3VO')
        except:
            raise
        try:
            synchrotron_name = \
                             bl_config.synchrotron_name
            beamline_setup.synchrotronName = synchrotron_name
        except (IndexError, AttributeError), e:
            beamline_setup.synchrotronName = "ESRF"

        if bl_config.undulators:
          i = 1
          for und in bl_config.undulators:
            beamline_setup.__setattr__('undulatorType%d' % i, und.type)
            i += 1

        try:
          beamline_setup.monochromatorType = \
              bl_config.monochromator_type

          beamline_setup.focusingOptic = \
              bl_config.focusing_optic

          beamline_setup.beamDivergenceVertical = \
              bl_config.beam_divergence_vertical

          beamline_setup.beamDivergenceHorizontal = \
              bl_config.beam_divergence_horizontal

          beamline_setup.polarisation = \
              bl_config.polarisation

          beamline_setup.minExposureTimePerImage = \
              bl_config.minimum_exposure_time

          beamline_setup.goniostatMaxOscillationSpeed = \
              bl_config.maximum_phi_speed

          beamline_setup.goniostatMinOscillationWidth = \
              bl_config.minimum_phi_oscillation

        except:
            pass

        beamline_setup.setupDate = datetime.now()

        return beamline_setup


    @staticmethod
    def dcg_from_dc_params(ws_client, mx_collect_dict):
        """
        Creates a dataCollectionGroupWS3VO object from a mx_collect_dict.
        """

        group = None

        try:
            group = \
                  ws_client.factory.create('ns0:dataCollectionGroupWS3VO')
        except:
            raise
        else:
            try:
                group.actualContainerBarcode = \
                    mx_collect_dict['actualContainerBarcode']
            except:
                pass

            try:
                group.actualContainerSlotInSC = \
                    mx_collect_dict['actualContainerSlotInSC']
            except KeyError:
                pass


            try:
                group.actualSampleBarcode = \
                    mx_collect_dict['actualSampleBarcode']
            except KeyError:
                pass


            try:
                group.actualSampleSlotInContainer = \
                    mx_collect_dict['actualSampleSlotInContainer']
            except KeyError:
                pass


            try:
                group.blSampleId = \
                    mx_collect_dict['sample_reference']['blSampleId']
            except KeyError,diag:
                pass


            try:
                group.comments = mx_collect_dict['comments']
            except KeyError,diag:
                pass

            try:
                group.workflowId = mx_collect_dict['workflow_id']
            except KeyError,diag:
                pass

            group.endTime = datetime.now()

#         try:
#             group.crystalClass = mx_collect_dict['crystalClass']
#         except KeyError,diag:
#              pass

#         modes=("Software binned", "Unbinned", "Hardware binned")

#         try:
#             det_mode = int(mx_collect_dict['detector_mode'])
#             group.detectorMode = modes[det_mode]
#         except (KeyError, IndexError, ValueError, TypeError):
#             det_mode = 1
#             group.detectorMode = modes[det_mode]


            try:
                try:
                    helical_used = mx_collect_dict['helical']
                except:
                    helical_used = False
                else:
                    if helical_used:
                        mx_collect_dict['experiment_type'] = 'Helical'
                        mx_collect_dict['comment'] = 'Helical'

                try:
                    directory = mx_collect_dict['fileinfo']['directory']
                except:
                    directory = ''
                else:
                    if 'mesh' in directory:
                        mesh_used = True
                    else:
                        mesh_used = False

                    if mesh_used:
                        mx_collect_dict['experiment_type'] = 'Mesh'
                        comment = mx_collect_dict.get("comment", "")
                        if not comment:
                            try:
                                mx_collect_dict['comment'] = \
                                    'Mesh: phiz:' +  str(mx_collect_dict['motors'].values()[0]) + \
                                    ', phiy' + str(mx_collect_dict['motors'].values()[1])
                            except:
                                mx_collect_dict['comment'] = 'Mesh: Unknown motor positions'

                group.experimentType = mx_collect_dict['experiment_type']
            except KeyError,diag:
                pass


            try:
                group.sessionId = mx_collect_dict['sessionId']
            except:
                pass

            try:
                start_time = mx_collect_dict["collection_start_time"]
                start_time = datetime.\
                             strptime(start_time , "%Y-%m-%d %H:%M:%S")
                group.startTime = start_time
            except:
                pass

            try:
                group.dataCollectionGroupId = mx_collect_dict["group_id"]
            except:
                pass

            return group


    @staticmethod
    def from_data_collect_parameters(ws_client, mx_collect_dict):
        """
        Ceates a dataCollectionWS3VO from mx_collect_dict.
        :rtype: dataCollectionWS3VO
        """
        if len(mx_collect_dict['oscillation_sequence']) != 1:
            raise ISPyBArgumentError("ISPyBServer: number of oscillations" + \
                                     " must be 1 (until further notice...)")
        data_collection = None

        try:

            data_collection = \
                ws_client.factory.create('ns0:dataCollectionWS3VO')
        except:
            raise

        osc_seq = mx_collect_dict['oscillation_sequence'][0]

        try:
            data_collection.runStatus = mx_collect_dict["status"]
            data_collection.axisStart = osc_seq['start']

            data_collection.axisEnd = (\
                float(osc_seq['start']) +\
                    (float(osc_seq['range']) - float(osc_seq['overlap'])) *\
                    float(osc_seq['number_of_images']))

            data_collection.axisRange = osc_seq['range']
            data_collection.overlap = osc_seq['overlap']
            data_collection.numberOfImages = osc_seq['number_of_images']
            data_collection.startImageNumber = osc_seq['start_image_number']
            data_collection.numberOfPasses = osc_seq['number_of_passes']
            data_collection.exposureTime = osc_seq['exposure_time']
            data_collection.imageDirectory = \
                mx_collect_dict['fileinfo']['directory']

            if osc_seq.has_key('kappaStart'):
                if osc_seq['kappaStart']!=0 and osc_seq['kappaStart']!=-9999:
                    data_collection.rotationAxis = 'Omega'
                    data_collection.omegaStart = osc_seq['start']
                else:
                    data_collection.rotationAxis = 'Phi'
            else:
                data_collection.rotationAxis = 'Phi'
                osc_seq['kappaStart'] = -9999
                osc_seq['phiStart'] = -9999

            data_collection.kappaStart = osc_seq['kappaStart']
            data_collection.phiStart = osc_seq['phiStart']

        except KeyError,diag:
            err_msg = \
                "ISPyBClient: error storing a data collection (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        data_collection.detector2theta = 0

        try:
            data_collection.dataCollectionId = \
                int(mx_collect_dict['collection_id'])
        except KeyError:
            pass

        try:
            data_collection.wavelength = mx_collect_dict['wavelength']
        except KeyError,diag:
            pass

        res_at_edge = None
        try:
            try:
                res_at_edge = float(mx_collect_dict['resolution'])
            except:
                res_at_edge = float(mx_collect_dict['resolution']['lower'])
        except KeyError:
            try:
                res_at_edge = float(mx_collect_dict['resolution']['upper'])
            except:
                pass
        if res_at_edge is not None:
            data_collection.resolution = res_at_edge

        try:
            data_collection.resolutionAtCorner = \
                mx_collect_dict['resolutionAtCorner']
        except KeyError:
            pass

        try:
            data_collection.detectorDistance = \
                mx_collect_dict['detectorDistance']
        except KeyError,diag:
            pass

        try:
            data_collection.xbeam = mx_collect_dict['xBeam']
            data_collection.ybeam = mx_collect_dict['yBeam']
        except KeyError,diag:
            pass

        try:
            data_collection.beamSizeAtSampleX = \
                mx_collect_dict['beamSizeAtSampleX']
            data_collection.beamSizeAtSampleY = \
                mx_collect_dict['beamSizeAtSampleY']
        except KeyError:
            pass

        try:
            data_collection.beamShape = mx_collect_dict['beamShape']
        except KeyError:
            pass

        try:
            data_collection.slitGapHorizontal = \
                mx_collect_dict['slitGapHorizontal']
            data_collection.slitGapVertical = \
                mx_collect_dict['slitGapVertical']
        except KeyError:
            pass

        try:
            data_collection.imagePrefix = mx_collect_dict['fileinfo']['prefix']
        except KeyError,diag:
            pass

        try:
            data_collection.imageSuffix = mx_collect_dict['fileinfo']['suffix']
        except KeyError,diag:
            pass
        try:
            data_collection.fileTemplate = \
                mx_collect_dict['fileinfo']['template']
        except KeyError,diag:
            pass

        try:
            data_collection.dataCollectionNumber = \
                mx_collect_dict['fileinfo']['run_number']
        except KeyError,diag:
            pass

        try:
            data_collection.synchrotronMode = \
                mx_collect_dict['synchrotronMode']
            data_collection.flux = mx_collect_dict['flux']
        except KeyError,diag:
            pass

        try:
            data_collection.flux_end = mx_collect_dict['flux_end']
        except KeyError,diag:
            pass

        try:
            data_collection.transmission = mx_collect_dict["transmission"]
        except KeyError:
            pass

        try:
            data_collection.undulatorGap1 = mx_collect_dict["undulatorGap1"]
            data_collection.undulatorGap2 = mx_collect_dict["undulatorGap2"]
            data_collection.undulatorGap3 = mx_collect_dict["undulatorGap3"]
        except KeyError:
            pass

        try:
            data_collection.xtalSnapshotFullPath1 = \
                mx_collect_dict['xtalSnapshotFullPath1']
        except KeyError:
            pass
            
        try:  
            data_collection.xtalSnapshotFullPath2 = \
                mx_collect_dict['xtalSnapshotFullPath2']
        except KeyError:
            pass

        try:
            data_collection.xtalSnapshotFullPath3 = \
                mx_collect_dict['xtalSnapshotFullPath3']
        except KeyError:
            pass

        try: 
            data_collection.xtalSnapshotFullPath4 = \
                mx_collect_dict['xtalSnapshotFullPath4']
        except KeyError:
            pass

        try:
            data_collection.centeringMethod = \
                mx_collect_dict['centeringMethod']
        except KeyError :
            pass

        try:
            data_collection.actualCenteringPosition = \
                mx_collect_dict['actualCenteringPosition']
        except KeyError:
            pass


        try:
            data_collection.dataCollectionGroupId = mx_collect_dict["group_id"]
        except KeyError:
            pass


        try:
            data_collection.detectorId = mx_collect_dict["detector_id"]
        except KeyError:
            pass

        try:
             data_collection.strategySubWedgeOrigId = \
                 mx_collect_dict['screening_sub_wedge_id']
        except:
             pass

        try:
            start_time = mx_collect_dict["collection_start_time"]
            start_time = datetime.\
                         strptime(start_time , "%Y-%m-%d %H:%M:%S")
            data_collection.startTime = start_time
        except:
            pass

        data_collection.endTime = datetime.now()

        return data_collection

    def workflow_from_workflow_info(self, workflow_info_dict):
        """
        Ceates workflow3VO from worflow_info_dict.
        :rtype: workflow3VO
        """
        ws_client = None
        workflow_vo = None

        try:
            ws_client = Client(_WS_COLLECTION_URL,
                               cache = None)
            workflow_vo = \
                ws_client.factory.create('workflow3VO')
        except:
            raise

        try:
            if workflow_info_dict.get("workflow_id"):
                workflow_vo.workflowId = workflow_info_dict.get("workflow_id")
            workflow_vo.workflowType = workflow_info_dict.get("workflow_type", "MeshScan")
            workflow_vo.comments = workflow_info_dict.get("comments", "")
            workflow_vo.logFilePath = workflow_info_dict.get("log_file_path", "")
            workflow_vo.resultFilePath = workflow_info_dict.get("result_file_path", "")
            workflow_vo.status = workflow_info_dict.get("status", "")
            workflow_vo.workflowTitle = workflow_info_dict.get("title", "")
        except KeyError,diag:
            err_msg = \
                "ISPyBClient: error storing a workflow (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        return workflow_vo

    def workflow_mesh_from_workflow_info(self, workflow_info_dict):
        """
        Ceates workflowMesh3VO from worflow_info_dict.
        :rtype: workflowMesh3VO
        """
        ws_client = None
        workflow_mesh_vo = None

        try:
            ws_client = Client(_WS_COLLECTION_URL,
                               cache = None)
            workflow_mesh_vo = \
                ws_client.factory.create('workflowMeshWS3VO')
        except:
            raise

        try:
            if workflow_info_dict.get("workflow_mesh_id"):
                workflow_mesh_vo.workflowMeshId = workflow_info_dict.get("workflow_mesh_id")
            workflow_mesh_vo.cartographyPath = workflow_info_dict.get("cartography_path", "")
            workflow_mesh_vo.bestImageId = workflow_info_dict.get("best_image_id", "")
            workflow_mesh_vo.bestPositionId = workflow_info_dict.get("best_position_id")
            workflow_mesh_vo.value1 = workflow_info_dict.get("value_1")
            workflow_mesh_vo.value2 = workflow_info_dict.get("value_2")
            workflow_mesh_vo.value3 = workflow_info_dict.get("value_3")
            workflow_mesh_vo.value4 = workflow_info_dict.get("value_4")
        except KeyError,diag:
            err_msg = \
                "ISPyBClient: error storing a workflow mesh (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        return workflow_mesh_vo

    def grid_info_from_workflow_info(self, workflow_info_dict):
        """
        Ceates grid3VO from worflow_info_dict.
        :rtype: grid3VO
        """
        ws_client = None
        grid_info_vo = None

        try:
            ws_client = Client(_WS_COLLECTION_URL,
                               cache = None)
            grid_info_vo = \
                ws_client.factory.create('gridInfoWS3VO')
        except:
            raise

        try:
            if workflow_info_dict.get("grid_info_id"):
                grid_info_vo.gridInfoId = workflow_info_dict.get("grid_info_id")
            grid_info_vo.dx_mm = workflow_info_dict.get("dx_mm")
            grid_info_vo.dy_mm = workflow_info_dict.get("dy_mm")
            grid_info_vo.meshAngle = workflow_info_dict.get("mesh_angle")
            grid_info_vo.steps_x = workflow_info_dict.get("steps_x")
            grid_info_vo.steps_y = workflow_info_dict.get("steps_y")
            grid_info_vo.xOffset = workflow_info_dict.get("xOffset")
            grid_info_vo.yOffset = workflow_info_dict.get("yOffset")
        except KeyError,diag:
            err_msg = \
                "ISPyBClient: error storing a grid info (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        return grid_info_vo

    def workflow_step_from_workflow_info(self, workflow_info_dict):
        """
        Ceates workflow3VO from worflow_info_dict.
        :rtype: workflow3VO
        """
        ws_client = None
        workflow_vo = None

        try:
            ws_client = Client(_WS_COLLECTION_URL,
                               cache = None)
            workflow_step_vo = \
                ws_client.factory.create('workflowStep3VO')
        except:
            raise

        try:
            workflow_step_vo.workflowId = workflow_info_dict.get("workflow_id")
            workflow_step_vo["type"] = workflow_info_dict.get("workflow_type", "MeshScan")
            workflow_step_vo.status = workflow_info_dict.get("status", "")
            workflow_step_vo.folderPath = workflow_info_dict.get("result_file_path", "")
            workflow_step_vo.htmlResultFilePath = os.path.join(\
                workflow_step_vo.folderPath, "index.html")
            workflow_step_vo.resultFilePath = os.path.join(\
                workflow_step_vo.folderPath, "index.html")
            workflow_step_vo.comments = workflow_info_dict.get("comments", "")
            workflow_step_vo.crystalSizeX = workflow_info_dict.get("crystal_size_x")
            workflow_step_vo.crystalSizeY = workflow_info_dict.get("crystal_size_y")
            workflow_step_vo.crystalSizeZ = workflow_info_dict.get("crystal_size_z") 
            workflow_step_vo.maxDozorScore = workflow_info_dict.get("max_dozor_score")
        except KeyError,diag:
            err_msg = \
                "ISPyBClient: error storing a workflow (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        return workflow_step_vo

    def grid_info_from_workflow_info(self, workflow_info_dict):
        """
        Ceates grid3VO from worflow_info_dict.
        :rtype: grid3VO
        """
        ws_client = None
        grid_info_vo = None

        try:
            ws_client = Client(_WS_COLLECTION_URL,
                               cache = None)
            grid_info_vo = \
                ws_client.factory.create('gridInfoWS3VO')
        except:
            raise

        try:
            if workflow_info_dict.get("grid_info_id"):
                grid_info_vo.gridInfoId = workflow_info_dict.get("grid_info_id")
            grid_info_vo.dx_mm = workflow_info_dict.get("dx_mm")
            grid_info_vo.dy_mm = workflow_info_dict.get("dy_mm")
            grid_info_vo.meshAngle = workflow_info_dict.get("mesh_angle")
            grid_info_vo.steps_x = workflow_info_dict.get("steps_x")
            grid_info_vo.steps_y = workflow_info_dict.get("steps_y")
            grid_info_vo.xOffset = workflow_info_dict.get("xOffset")
            grid_info_vo.yOffset = workflow_info_dict.get("yOffset")
        except KeyError,diag:
            err_msg = \
                "ISPyBClient: error storing a grid info (%s)" % str(diag)
            raise ISPyBArgumentError(err_msg)

        return grid_info_vo


class ISPyBArgumentError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.value)
