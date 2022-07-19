#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name] XalocISPyBClient

[Description]
HwObj used to interface the ISPyB database

[Signals]
- None
"""

#from __future__ import print_function

import logging

from mxcubecore.HardwareObjects.ISPyBClient import ISPyBClient, trace, utf_encode
from mxcubecore import HardwareRepository as HWR
from suds import WebFault
try:
    from urlparse import urljoin
    from urllib2 import URLError
except Exception:
    # Python3
    from urllib.parse import urljoin
    from urllib.error import URLError

from suds.sudsobject import asdict

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"


class XalocISPyBClient(ISPyBClient):
    
    def __init__(self, *args):
        ISPyBClient.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocISPyBClient")
    
    def init(self):
        ISPyBClient.init(self)
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
    
    def ldap_login(self, login_name, psd, ldap_connection):
        # overwrites standard ldap login  is ISPyBClient2.py
        #  to query for homeDirectory

        if ldap_connection is None:
            ldap_connection = self.ldapConnection

        ok, msg = ldap_connection.login(
            login_name, psd, fields=[
                "uid", "homeDirectory"])
        self.logger.debug("ALBA LDAP login success %s (msg: %s)" % (ok, msg))
        if ok:
            vals = ldap_connection.get_field_values()
            if 'homeDirectory' in vals:
                home_dir = vals['homeDirectory'][0]
                self.logger.debug("The homeDirectory for user %s is %s" %
                    (login_name, home_dir))
                HWR.beamline.session.set_ldap_homedir(home_dir)
        else:
            home_dir = '/tmp'
            HWR.beamline.session.set_ldap_homedir(home_dir)

        return ok, msg

    def translate(self, code, what):
        """
        Given a proposal code, returns the correct code to use in the GUI,
        or what to send to LDAP, user office database, or the ISPyB database.
        """
        self.logger.debug("Translating %s %s" % (code, what))
        if what == 'ldap':
            if code == 'mx':
                return 'u'

        if what == 'ispyb':
            if code == 'u' or code == 'uind-':
                return 'mx'

        return code

    def prepare_collect_for_lims(self, mx_collect_dict):
        # Attention! directory passed by reference. modified in place

        for i in range(4):
            try:
                prop = 'xtalSnapshotFullPath%d' % (i + 1)
                path = mx_collect_dict[prop]
                ispyb_path = HWR.beamline.session.path_to_ispyb(path)
                logging.debug("%s = %s " % (prop, ispyb_path))
                mx_collect_dict[prop] = ispyb_path
            except BaseException as e:
                logging.debug("Error when preparing collection for LIMS\n%s" % str(e))

    def prepare_image_for_lims(self, image_dict):
        for prop in ['jpegThumbnailFileFullPath', 'jpegFileFullPath']:
            try:
                path = image_dict[prop]
                ispyb_path = HWR.beamline.session.path_to_ispyb(path)
                image_dict[prop] = ispyb_path
            except BaseException as e:
                logging.debug("Error when preparing image for LIMS\n%s" % str(e))

    @trace
    def get_samples(self, proposal_id, session_id):
        response_samples = None

        if self._tools_ws:
            try:
                response_samples = self._tools_ws.service.findSampleInfoLightForProposal(
                    proposal_id, self.beamline_name
                )

                response_samples = [
                    utf_encode(asdict(sample)) for sample in response_samples
                ]
                #logging.getLogger("HWR").debug("%s" % response_samples)
                # response_samples holds an array of dictionaries. Each dictionary represents a sample. 
                # the basket location in the robot is held in the key containerSampleChangerLocation
                # the sample location in the basket is held in the key sampleLocation
                # eg sample_list[0]['containerSampleChangerLocation'] returns '1'
                # and sample_list[0]['sampleLocation'] returns '1'

            except WebFault as e:
                logging.getLogger("ispyb_client").exception(str(e))
            except URLError:
                logging.getLogger("ispyb_client").exception(_CONNECTION_ERROR_MSG)
        else:
            logging.getLogger("ispyb_client").exception(
                "Error in get_samples: could not connect to server"
            )

        self.emit("ispyb_sync_successful")

        return response_samples


def test_hwo(hwo):
    proposal = 'mx2018002222'
    pasw = '2222008102'

    info = hwo.login(proposal, pasw)
    # info = hwo.get_proposal(proposal_code, proposal_number)
    # info = hwo.get_proposal_by_username("u2020000007")
    print(info['status'])

    print("Getting associated samples")
    session_id = 58248
    proposal_id = 8250
    samples = hwo.get_samples(proposal_id, session_id)
    print(samples)
