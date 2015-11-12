"""
A client for ISPyB Webservices. 
"""
import os
import logging
import gevent
from datetime import datetime
from requests import put, get, post

from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import HardwareObject

_CONNECTION_ERROR_MSG = "Could not connect to ISPyB, please verify that " + \
                        "the server is running and that your " + \
                        "configuration is correct"
_NO_TOKEN_MSG = "Could not connect to ISPyB, no valid REST token available."

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


class ISPyBRestClient(HardwareObject):
    """
    Web-service client for ISPyB.
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

    def init(self):
        """
        Descript. :
        """
        self.session_hwobj = self.getObjectByRole('session')
        if self.session_hwobj:
            self.beamline_name = self.session_hwobj.beamline_name
        else:
            self.beamline_name = 'ID:TEST'

        logging.getLogger("requests").setLevel(logging.WARNING)

        self.__rest_root = self.getProperty('restRoot')
        self.__rest_username = self.getProperty('restUserName')
        self.__rest_password = self.getProperty('restPass')

        self.__update_rest_token()

    def __update_rest_token(self):
        """
        Descript. : updates REST token if necessary
                    By default token expires in 3h so we are checking
                    the timestamp of the tocken and if it is older
                    than 3h we update the rest tocken
        """
        request_token = False
        if not self.__rest_token_timestamp:
            request_token = True 
        else:
           timedelta = datetime.now() - self.__rest_token_timestamp
           if timedelta.seconds > (3 * 60 * 60):  
               request_token = True

        if request_token: 
            try:
               logging.getLogger("ispyb_client").info("Requesting new RESTful token...")
               data_dict = {'login' : str(self.__rest_username),
                            'password' : str(self.__rest_password)}
               response = post(self.__rest_root + 'authenticate', data = data_dict)
               self.__rest_token = response.json().get('token') 
               self.__rest_token_timestamp = datetime.now()
               logging.getLogger("ispyb_client").info("RESTful token acquired")
            except:
               logging.getLogger("ispyb_client").exception(_NO_TOKEN_MSG)

    #@in_greenlet
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
               response = get(self.__rest_root + self.__rest_token + \
                   '/proposal/%s/list' % user_name)
               proposal_list = eval(str(response.text))
               for proposal in proposal_list:
                   temp_proposal_dict = {}
                   # Backward compatability with webservices
                   # Could be removed if webservices disapear 
                   temp_proposal_dict['Proposal'] = {}
                   temp_proposal_dict['Proposal']['type'] = str(proposal['Proposal_proposalType'])
                   if temp_proposal_dict['Proposal']['type'] in ('MX', 'MB'):
                       temp_proposal_dict['Proposal']['proposalId'] = proposal['Proposal_proposalId'] 
                       temp_proposal_dict['Proposal']['code'] = str(proposal['Proposal_proposalCode'])
                       temp_proposal_dict['Proposal']['number'] = proposal['Proposal_proposalNumber']
                       temp_proposal_dict['Proposal']['title'] = proposal['Proposal_title']
                       temp_proposal_dict['Proposal']['personId'] = proposal['Proposal_personId']

                       # gets all sessions for 
                       #proposal_txt = temp_proposal_dict['Proposal']['code'] + \
                       #               str(temp_proposal_dict['Proposal']['number'])
                       #sessions = self.get_proposal_sessions(temp_proposal_dict['Proposal']['proposalId'])
                       res_sessions = self.get_proposal_sessions(\
                           temp_proposal_dict['Proposal']['proposalId'])
                       #This could be fixed and removed from here
                       proposal_sessions = []
                       for session in res_sessions:
                           date_object = datetime.strptime(session['startDate'], '%b %d, %Y %I:%M:%S %p')
                           session['startDate'] = datetime.strftime(
                                 date_object, "%Y-%m-%d %H:%M:%S")
                           date_object = datetime.strptime(session['endDate'], '%b %d, %Y %I:%M:%S %p')
                           session['endDate'] = datetime.strftime(
                                 date_object, "%Y-%m-%d %H:%M:%S") 
                           proposal_sessions.append(session)

                       temp_proposal_dict['Sessions'] = proposal_sessions
                       result.append(temp_proposal_dict)
            except:
               logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)  
        else:
             logging.getLogger("ispyb_client").exception(_NO_TOKEN_MSG)        
        return result

    def get_proposal_sessions(self, proposal_id):
        self.__update_rest_token()
        session_list = []
        if self.__rest_token:
            try:
               response = get(self.__rest_root + self.__rest_token + \
                    '/proposal/%s/session/list' % proposal_id)
               session_list = response.json()
               #for session in all_sessions:
               #    if session['proposalVO']['proposalId'] == proposal_id:
               #session_list.append(all_sessions) 
            except:
               logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
        else:
             logging.getLogger("ispyb_client").exception(_NO_TOKEN_MSG)

        return session_list

    #@trace
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
             response = get(self.__rest_root + self.__rest_token + \
                 "/proposal/session/%d/localcontact" % session_id)
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


    def store_data_collection(self, mx_collection, beamline_setup = None):
        """
        Stores the data collection mx_collection, and the beamline setup
        if provided.

        :param mx_collection: The data collection parameters.
        :type mx_collection: dict
        
        :param beamline_setup: The beamline setup.
        :type beamline_setup: dict

        :returns: None

        """
        print "store_data_collection..." , mx_collection
        return None, None


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
        print "store_beamline_setup...", beamline_setup 
        pass


    def update_data_collection(self, mx_collection, wait=False):
        """
        Updates the datacollction mx_collection, this requires that the
        collectionId attribute is set and exists in the database.

        :param mx_collection: The dictionary with collections parameters.
        :type mx_collection: dict

        :returns: None
        """  
        print "update_data_collection... ", mx_collection
        pass


    def store_image(self, image_dict):
        """
        Stores the image (image parameters) <image_dict>
        
        :param image_dict: A dictonary with image pramaters.
        :type image_dict: dict

        :returns: None
        """
        print "store_image ", image_dict
        pass

    
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
        pass


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

    def _store_data_collection_group(self, group_data):
        self.update_rest_token()
        if self.__rest_token:
            try:
               response = get(self.__rest_root + self.__rest_token + '/proposal/%s/session/list' % self.__rest_username)
               all_sessions = response.json()
               for session in all_sessions:
                   if session['proposalVO']['proposalId'] == proposal_id:
                       session_list.append(session)
            except:
               logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
        else:
             logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)

        return session_list        
