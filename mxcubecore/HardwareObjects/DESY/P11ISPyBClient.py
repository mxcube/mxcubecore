
from mxcubecore.HardwareObjects.ISPyBClient import ISPyBClient

from requests import post
from urllib.parse import urljoin
import logging

class P11ISPyBClient(ISPyBClient):

    def init(self):
        self.simulated_proposal = self.get_property("proposal_simulated")

        if self.simulated_proposal == 1:
            self.simulated_prop_code = self.get_property("proposal_code_simulated")
            self.simulated_prop_number = self.get_property("proposal_number_simulated")
        else:
            self.simulated_prop_code = None
            self.simulated_prop_number = None
        logging.getLogger("HWR").debug("PROPOSAL SIMULATED is %s" % self.simulated_proposal)
        logging.getLogger("HWR").debug("PROPOSAL CODE is %s" % self.simulated_prop_code)
        logging.getLogger("HWR").debug("PROPOSAL NUMBE is %s" % self.simulated_prop_number)

        ISPyBClient.init(self)

    def update_data_collection(self, mx_collection, wait=False):
        mx_collection["beamline_name"] = "P11"
        ISPyBClient.update_data_collection(self, mx_collection, wait)

    #def _ispybLogin(self, login_id, psd):
    #  site = "DESY"
    #  rest_root = "https://ispybdev.desy.de/ispyb/ispyb-ws/rest/"
#
#        # self.log.debug("ISPyB Login - username: %s" % login_id)
#        # set development user and password
#        login_id = "ispybdev"
#        psd = "sM5pBZGgpH2P4hmS"
#
#        self.log.debug("ISPyB Login - username: %s" % login_id)
#        auth_url = urljoin(self.rest_root, "authenticate?site=" + self.site)
#        authenticated = False
#
#        try:
#            data = {"login": str(login_id), "password": str(psd)}
#            response = post(auth_url, data=data)
#            token = response.json().get("token")
#        except BaseException as e:
#            msg = "ISPyB Login failed. Reason %s" % str(e)
#            self.log.error(msg)
#        else:
#            authenticated = True
#            msg = "ISPyB username: %s. succesful login. token is: %s" % (login_id, token)
#            self.log.debug("   - " + msg)
#         
#        return authenticated, msg

