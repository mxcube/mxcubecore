
from HardwareRepository import HardwareRepository
import logging
import urllib2
import os
from cookielib import CookieJar

from suds.transport.http import HttpAuthenticated
from suds.client import Client

import ISPyBClient2
from ISPyBClient2 import  _CONNECTION_ERROR_MSG

class SOLEILISPyBClient(ISPyBClient2.ISPyBClient2):

    def init(self):
        """
        Init method declared by HardwareObject.
        """
        self.session_hwobj = self.getObjectByRole('session')

        self.ws_username = self.getProperty('ws_username')
        self.ws_password = self.getProperty('ws_password')
        
        #self.ws_username = 'mx20100023' #self.getProperty('ws_username')
        #self.ws_password = 'tisabet' #self.getProperty('ws_password')
        
        self.ws_collection = self.getProperty('ws_collection')
        self.ws_shipping = self.getProperty('ws_shipping')
        self.ws_tools = self.getProperty('ws_tools')
        
        self.loginType = self.getProperty("loginType") or "proposal"
        self.loginTranslate = self.getProperty("loginTranslate") or True
        
        logging.debug("Initializing SOLEIL ISPyB Client")
        logging.debug("   - using http_proxy = %s " % os.environ['http_proxy'])

        try:

            if self.ws_root:
                logging.debug("self.ws_root %s" % self.ws_root)
                try: 
                    self._shipping = self._wsdl_shipping_client()
                    self._collection = self._wsdl_collection_client()
                    self._tools_ws = self._wsdl_tools_client()

                except: 
                    import traceback
                    print traceback.print_exc()
                #except URLError:
                    print "URLError"
                    logging.getLogger("ispyb_client")\
                        .exception(_CONNECTION_ERROR_MSG)
                    return
        except:
            import traceback
            print traceback.print_exc()
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
        except:
            pass
            #import traceback
            #traceback.print_exc()

        self.beamline_name = self.session_hwobj.beamline_name

    def translate(self, code, what):  
        """
        Given a proposal code, returns the correct code to use in the GUI,
        or what to send to LDAP, user office database, or the ISPyB database.
        """
        return code

    def _wsdl_shipping_client(self):
        return self._wsdl_client(self.ws_shipping)

    def _wsdl_tools_client(self):
        return self._wsdl_client(self.ws_tools)

    def _wsdl_collection_client(self):
        return self._wsdl_client(self.ws_collection)

    def _wsdl_client(self, service_name):

        # Handling of redirection at soleil needs cookie handling
        cj = CookieJar()
        url_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        trans = HttpAuthenticated(username = self.ws_username, password = self.ws_password)
        print '_wsdl_client %s' % service_name, trans
        trans.urlopener = url_opener
        urlbase = service_name + "?wsdl"
        locbase = service_name
       
        ws_root = self.ws_root.strip()

        url = ws_root + urlbase
        loc = ws_root + locbase

        ws_client = Client(url, transport=trans, timeout=3, \
                           location=loc, cache = None)

        return ws_client

    def prepare_collect_for_lims(self, mx_collect_dict):
        # Attention! directory passed by reference. modified in place

        for i in range(4):
            try: 
                prop = 'xtalSnapshotFullPath%d' % (i+1)
	        path = mx_collect_dict[prop] 
                ispyb_path = self.session_hwobj.path_to_ispyb( path )
                logging.debug("SOLEIL ISPyBClient - %s is %s " % (prop, ispyb_path))
	        mx_collect_dict[prop] = ispyb_path
            except:
                pass

    def prepare_image_for_lims(self, image_dict):
        for prop in [ 'jpegThumbnailFileFullPath', 'jpegFileFullPath']:
            try:
                path = image_dict[prop] 
                ispyb_path = self.session_hwobj.path_to_ispyb( path )
                image_dict[prop] = ispyb_path
            except:
                pass

def test():
    import os
    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    db = hwr.getHardwareObject("/dbconnection")
    proposal_code = 'mx'
    proposal_number = '20140088' #'20100023'
    
    info = db.get_proposal(proposal_code, proposal_number)# proposal_number)
    print info
 
if __name__ == '__main__':
    test()
