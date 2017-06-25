"""
A client for ISPyB Webservices. 
"""

import logging
import os
import datetime

from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import HardwareObject

# to simulate wrong loginID, use "wrong" for loginID
# to simulate wrong psd, use "wrong" for password
# to simulate ispybDown, but ldap login succeeds, use "ispybDown" for password
# to simulate no session scheduled, use "nosession" for password

class ISPyBClient2Mockup(HardwareObject):
    """
    Web-service client for ISPyB.
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.__translations = {}
        self.__disabled = False
        self.__test_proposal = None
        self.loginType = None

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
        self.session_hwobj = self.getObjectByRole('session')
        self.beamline_name = self.session_hwobj.beamline_name

        self.__test_proposal = {'status': {'code': 'ok'},
                'Person': {'personId': 1,
                           'laboratoryId': 1,
                           'login': None,
                           'familyName':'operator on IDTESTeh1'},
                'Proposal': {'code': 'idtest',
                             'title': 'operator on IDTESTeh1',
                             'personId': 1,
                             'number': '000',
                             'proposalId': 1,
                             'type': 'MX'},
                'Session': [{'scheduled': 0,
                             'startDate': '2013-06-11 00:00:00',
                             'endDate': '2023-06-12 07:59:59',
                             'beamlineName': self.beamline_name,
                             'timeStamp': datetime.datetime(2013, 6, 11, 9, 40, 36),
                             'comments': 'Session created by the BCM',
                             'sessionId': 34591,
                             'proposalId': 1, 'nbShifts': 3}],
                'Laboratory': {'laboratoryId': 1,
                               'name': 'TEST eh1'}}

    def get_login_type(self):
        self.loginType = self.getProperty("loginType") or "proposal"
        return self.loginType 

    def login (self,loginID, psd, ldap_connection=None):

        # to simulate wrong loginID
        if loginID == "wrong":
            return {'status':{ "code": "error", "msg": "loginID 'wrong' does not exist!" }, 'Proposal': None, 'Session': None} 
        # to simulate wrong psd
        if psd == "wrong":
	    return {'status':{ "code": "error", "msg": "Wrong password!" }, 'Proposal': None, 'Session': None}
        # to simulate ispybDown, but login succeed
        if psd == "ispybDown":
	    return {'status':{ "code": "ispybDown", "msg": "ispyb is down" }, 'Proposal': None, 'Session': None}
 
        new_session = False
        if psd == "nosession":
	    new_session=True
        prop=self.get_proposal(loginID,"")
	return {'status':{ "code": "ok", "msg": "Successful login" }, 'Proposal': prop['Proposal'],
                 'session': {"session": prop['Session'],"new_session_flag":new_session, "is_inhouse": False},
                 'local_contact': "BL Scientist",
                 'person': prop['Person'],
                 'laboratory': prop['Laboratory']}

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
        return self.__test_proposal

    def get_proposals_by_user(self, user_name):
        return [self.__test_proposal]

    def get_session_local_contact(self, session_id):
        return  {'personId': 1,
                 'laboratoryId': 1,
                 'login': None,
                 'familyName':'operator on ID14eh1'}


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



    def store_data_collection(self, mx_collection, beamline_setup=None):
        """
        Stores the data collection mx_collection, and the beamline setup
        if provided.

        :param mx_collection: The data collection parameters.
        :type mx_collection: dict
        
        :param beamline_setup: The beamline setup.
        :type beamline_setup: dict

        :returns: None

        """
        logging.getLogger("HWR").debug("Data collection parameters stored " + \
                                       "in ISPyB: %s" % str(mx_collection))
        logging.getLogger("HWR").debug("Beamline setup stored in ISPyB: %s" % \
                                       str(beamline_setup))

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
        return [{"cellA": 0.0, 
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
        "requiredResolution": 0.0
      }, 
      "experimentType": "Default", 
      "proteinAcronym": "A-TIM", 
      "sampleId": 515485, 
      "sampleLocation": "1", 
      "sampleName": "fghfg", 
      "smiles": None
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
        "requiredResolution": 0.0
      }, 
      "experimentType": "OSC", 
      "proteinAcronym": "B2 hexa", 
      "sampleId": 515419, 
      "sampleLocation": "1", 
      "sampleName": "sample"
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
        "requiredResolution": 0.0
      }, 
      "experimentType": "OSC", 
      "proteinAcronym": "B2 hexa", 
      "sampleId": 515420, 
      "sampleLocation": "2", 
      "sampleName": "sample"
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
        "requiredResolution": 0.0
      }, 
      "experimentType": "OSC", 
      "proteinAcronym": "B2 hexa", 
      "sampleId": 515421, 
      "sampleLocation": "3", 
      "sampleName": "sample"
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
        "requiredResolution": 0.0
      }, 
      "experimentType": "OSC", 
      "proteinAcronym": "B2 hexa", 
      "sampleId": 515422, 
      "sampleLocation": "5", 
      "sampleName": "sample"
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
        "requiredResolution": 0.0
      }, 
      "experimentType": "OSC", 
      "proteinAcronym": "B2 hexa", 
      "sampleId": 515423, 
      "sampleLocation": "6", 
      "sampleName": "sample"
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
        "requiredResolution": 0.0
      }, 
      "experimentType": "OSC", 
      "proteinAcronym": "B2 hexa", 
      "sampleId": 515424, 
      "sampleLocation": "7", 
      "sampleName": "sample"
    }]
    
        
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

    def create_session(self, session_dict):
        pass


    def update_session(self, session_dict):
        pass

    
    def store_energy_scan(self, energyscan_dict):
        pass

    
    def associate_bl_sample_and_energy_scan(self, entry_dict):
        pass

    
    def get_data_collection(self, data_collection_id):
        """
        Retrives the data collection with id <data_collection_id>

        :param data_collection_id: Id of data collection.
        :type data_collection_id: int

        :rtype: dict
        """
        pass

    
    def get_data_collection_id(self, dc_dict):
        pass

    
    def get_session(self, session_id):
        pass


    def store_xfe_spectrum(self, xfespectrum_dict):
        """
        Stores a xfe spectrum.

        :returns: A dictionary with the xfe spectrum id.
        :rtype: dict

        """
        pass

    
    def disable(self):
        self.__disabled = True

 
    def enable(self):
        self.__disabled = False


    def find_detector(self, type, manufacturer,
                      model, mode):
        """
        Returns the Detector3VO object with the characteristics
        matching the ones given.        
        """
        pass

    
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
        pass

    def store_autoproc_program(self, autoproc_program_dict):
        pass

    def store_workflow(self, *args, **kwargs):
        return 1, 1, 1

    def _store_workflow(self, info_dict):
        pass

    def store_image_quality_indicators(self, image_dict):
        pass

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
