"""
A client for ISPyB Webservices. 
"""

import logging
import gevent
import suds; logging.getLogger("suds").setLevel(logging.INFO)

from suds.transport.http import HttpAuthenticated
from suds.client import Client
from suds import WebFault
from suds.sudsobject import asdict
from urllib2 import URLError
from HardwareRepository.BaseHardwareObjects import HardwareObject
from datetime import datetime
from collections import namedtuple
from pprint import pformat

from ISPyBClient2 import *

# Production web-services:    http://160.103.210.1:8080/ispyb-ejb3/ispybWS/
# Test web-services:          http://160.103.210.4:8080/ispyb-ejb3/ispybWS/

# The WSDL root is configured in the hardware object XML file.
_WSDL_ROOT = '' 
_WS_BL_SAMPLE_URL = _WSDL_ROOT + 'ToolsForBLSampleWebService?wsdl'
_WS_SHIPPING_URL = _WSDL_ROOT + 'ToolsForShippingWebService?wsdl'
_WS_COLLECTION_URL = _WSDL_ROOT + 'ToolsForCollectionWebService?wsdl'
_WS_USERNAME = 'ispyadm'
_WS_PASSWORD = '1nv1$1ble'

_CONNECTION_ERROR_MSG = "Could not connect to ISPyB, please verify that " + \
                        "the server is running and that your " + \
                        "configuration is correct"


SampleReference = namedtuple('SampleReference', ['code',
                                                 'container_reference',
                                                 'sample_reference',
                                                 'container_code'])


class MaxLabISPyBClient2(ISPyBClient2):
    """
    Web-service client for ISPyB.
    """

    def __init__(self, name):
        ISPyBCLient2.__init__(self, name)
        self.__shipping = None
        self.__collection = None
        self.__tools_ws = None
        self.__translations = {}
        self.__disabled = False
        self.beamline_name = False
        
        logger = logging.getLogger('ispyb_client')
        
        try:
            formatter = \
                logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            hdlr = logging.FileHandler('/home/blissadm/log/ispyb_client.log')
            hdlr.setFormatter(formatter)
            logger.addHandler(hdlr) 
        except:
            pass

        logger.setLevel(logging.INFO)

      
    def init(self):
        """
        Init method declared by HardwareObject.
        """
        session_hwobj = self.getObjectByRole('session')
        
        try:
            # ws_root is a property in the configuration xml file
            if self.ws_root:
                global _WSDL_ROOT
                global _WS_BL_SAMPLE_URL
                global _WS_SHIPPING_URL
                global _WS_COLLECTION_URL
                global _WS_SCREENING_URL

                _WSDL_ROOT = self.ws_root.strip()
                _WS_BL_SAMPLE_URL = _WSDL_ROOT + \
                    'ToolsForBLSampleWebService?wsdl'
                _WS_SHIPPING_URL = _WSDL_ROOT + \
                    'ToolsForShippingWebService?wsdl'
                _WS_COLLECTION_URL = _WSDL_ROOT + \
                    'ToolsForCollectionWebService?wsdl'

                t1 = HttpAuthenticated(username = _WS_USERNAME, 
                                      password = _WS_PASSWORD)
                
                t2 = HttpAuthenticated(username = _WS_USERNAME, 
                                      password = _WS_PASSWORD)
                
                t3 = HttpAuthenticated(username = _WS_USERNAME, 
                                      password = _WS_PASSWORD)
                
                try: 
                    self.__shipping = Client(_WS_SHIPPING_URL, timeout = 3,
                                             transport = t1, cache = None)
                    self.__collection = Client(_WS_COLLECTION_URL, timeout = 3,
                                               transport = t2, cache = None)
                    self.__tools_ws = Client(_WS_BL_SAMPLE_URL, timeout = 3,
                                             transport = t3, cache = None)
                    
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
            proposals = session_hwobj['proposals']
            
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

        self.beamline_name = session_hwobj.beamline_name

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
                person = self.__shipping.service.findPersonByLogin(username)
            except WebFault, e:
                logging.getLogger("ispyb_client").warning(e.message)
                person = {}

            try:
                proposal = self.__shipping.service.findProposalByLogin(username)
                if not proposal:
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
                    findSessionsByCodeAndNumberAndBeamLine(proposal_code,
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

