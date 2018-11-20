from HardwareRepository import HardwareRepository
import logging
import urllib2
import os

from suds.transport.http import HttpAuthenticated
from suds.client import Client

import ISPyBClient2
from ISPyBClient2 import _CONNECTION_ERROR_MSG


class ALBAISPyBClient(ISPyBClient2.ISPyBClient2):
    def ldap_login(self, login_name, psd, ldap_connection):
        # overwrites standard ldap login  is ISPyBClient2.py
        #  to query for homeDirectory

        if ldap_connection is None:
            ldap_connection = self.ldapConnection

        ok, msg = ldap_connection.login(
            login_name, psd, fields=["uid", "homeDirectory"]
        )

        if ok:
            vals = ldap_connection.get_field_values()
            if "homeDirectory" in vals:
                home_dir = vals["homeDirectory"][0]
                logging.getLogger("HWR").debug(
                    "  homeDirectory for user %s is %s" % (login_name, home_dir)
                )
                # self.session_hwobj.set_base_data_directories(home_dir, home_dir, home_dir)
                self.session_hwobj.set_ldap_homedir(home_dir)
        else:
            home_dir = "/tmp"
            self.session_hwobj.set_ldap_homedir(home_dir)

        return ok, msg

    def translate(self, code, what):
        """
        Given a proposal code, returns the correct code to use in the GUI,
        or what to send to LDAP, user office database, or the ISPyB database.
        """
        logging.getLogger("HWR").debug("translating %s %s" % (code, what))
        if what == "ldap":
            if code == "mx":
                return "u"

        if what == "ispyb":
            if code == "u":
                return "mx"

        return code

    def prepare_collect_for_lims(self, mx_collect_dict):
        # Attention! directory passed by reference. modified in place

        for i in range(4):
            try:
                prop = "xtalSnapshotFullPath%d" % (i + 1)
                path = mx_collect_dict[prop]
                ispyb_path = self.session_hwobj.path_to_ispyb(path)
                logging.debug("ALBA ISPyBClient - %s is %s " % (prop, ispyb_path))
                mx_collect_dict[prop] = ispyb_path
            except:
                pass

    def prepare_image_for_lims(self, image_dict):
        for prop in ["jpegThumbnailFileFullPath", "jpegFileFullPath"]:
            try:
                path = image_dict[prop]
                ispyb_path = self.session_hwobj.path_to_ispyb(path)
                image_dict[prop] = ispyb_path
            except:
                pass


def test_hwo(hwo):
    proposal = "mx2018012551"
    proposal = "mx2018002222"
    pasw = "2222008102"

    info = hwo.login(proposal, pasw)
    # info = hwo.get_proposal(proposal_code, proposal_number)
    # info = hwo.get_proposal_by_username("u2020000007")
    print info["status"]

    print "Getting associated samples"
    session_id = 58248
    proposal_id = 8250
    samples = hwo.get_samples(proposal_id, session_id)
    print samples
