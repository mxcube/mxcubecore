import logging
import os
import traceback
from collections import namedtuple

import urllib2
from cookielib import CookieJar
from ISPyBClient import (
    _CONNECTION_ERROR_MSG,
    ISPyBClient,
)
from suds.client import Client
from suds.transport.http import HttpAuthenticated

from mxcubecore import HardwareRepository as HWR

# The WSDL root is configured in the hardware object XML file.
# _WS_USERNAME, _WS_PASSWORD have to be configured in the HardwareObject XML file.
_WSDL_ROOT = ""
_WS_BL_SAMPLE_URL = _WSDL_ROOT + "ToolsForBLSampleWebService?wsdl"
_WS_SHIPPING_URL = _WSDL_ROOT + "ToolsForShippingWebService?wsdl"
_WS_COLLECTION_URL = _WSDL_ROOT + "ToolsForCollectionWebService?wsdl"
_WS_AUTOPROC_URL = _WSDL_ROOT + "ToolsForAutoprocessingWebService?wsdl"
_WS_USERNAME = None
_WS_PASSWORD = None

SampleReference = namedtuple(
    "SampleReference",
    ["code", "container_reference", "sample_reference", "container_code"],
)


class SOLEILISPyBClient(ISPyBClient):
    def __init__(self, name):
        ISPyBClient.__init__(self, name)

        logger = logging.getLogger("ispyb_client")
        print("ISPYB")

        try:
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            hdlr = logging.FileHandler(
                "/home/experiences/proxima2a/com-proxima2a/MXCuBE_v2_logs/ispyb_client.log"
            )
            hdlr.setFormatter(formatter)
            logger.addHandler(hdlr)
        except Exception:
            pass

        logger.setLevel(logging.INFO)

    def init(self):
        """
        Init method declared by HardwareObject.
        """
        self.authServerType = self.get_property("authServerType") or "ldap"
        if self.authServerType == "ldap":
            # Initialize ldap
            self.ldapConnection = self.get_object_by_role("ldapServer")
            if self.ldapConnection is None:
                logging.getLogger("HWR").debug("LDAP Server is not available")

        self.loginType = self.get_property("loginType") or "proposal"
        self.loginTranslate = self.get_property("loginTranslate") or True
        self.beamline_name = HWR.beamline.session.beamline_name
        print("self.beamline_name init", self.beamline_name)

        self.ws_root = self.get_property("ws_root")
        self.ws_username = self.get_property("ws_username")
        if not self.ws_username:
            self.ws_username = _WS_USERNAME
        self.ws_password = self.get_property("ws_password")
        if not self.ws_password:
            self.ws_password = _WS_PASSWORD

        self.ws_collection = self.get_property("ws_collection")
        self.ws_shipping = self.get_property("ws_shipping")
        self.ws_tools = self.get_property("ws_tools")

        logging.info("SOLEILISPyBClient: Initializing SOLEIL ISPyB Client")
        logging.info("   - using http_proxy = %s " % os.environ["http_proxy"])

        try:

            if self.ws_root:
                logging.info(
                    "SOLEILISPyBClient: attempting to connect to %s" % self.ws_root
                )
                print("SOLEILISPyBClient: attempting to connect to %s" % self.ws_root)

                try:
                    self._shipping = self._wsdl_shipping_client()
                    self._collection = self._wsdl_collection_client()
                    self._tools_ws = self._wsdl_tools_client()
                    logging.debug(
                        "SOLEILISPyBClient: extracted from ISPyB values for shipping, collection and tools"
                    )
                except Exception:
                    print(traceback.print_exc())
                    logging.exception("SOLEILISPyBClient: %s" % _CONNECTION_ERROR_MSG)
                    return
        except Exception:
            print(traceback.print_exc())
            logging.getLogger("HWR").exception(_CONNECTION_ERROR_MSG)
            return
        try:
            proposals = HWR.beamline.session["proposals"]

            for proposal in proposals:
                code = proposal.code
                self._translations[code] = {}
                try:
                    self._translations[code]["ldap"] = proposal.ldap
                except AttributeError:
                    pass
                try:
                    self._translations[code]["ispyb"] = proposal.ispyb
                except AttributeError:
                    pass
                try:
                    self._translations[code]["gui"] = proposal.gui
                except AttributeError:
                    pass
        except IndexError:
            pass
        except Exception:
            pass

    def translate(self, code, what):
        """
        Given a proposal code, returns the correct code to use in the GUI,
        or what to send to LDAP, user office database, or the ISPyB database.
        """
        if what == "ispyb":
            return "mx"
        return ""

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

        trans = HttpAuthenticated(username=self.ws_username, password=self.ws_password)
        logging.info("_wsdl_client service_name %s - trans %s" % (service_name, trans))
        print("_wsdl_client service_name %s - trans %s" % (service_name, trans))

        trans.urlopener = url_opener
        urlbase = service_name + "?wsdl"
        locbase = service_name

        ws_root = self.ws_root.strip()

        url = ws_root + urlbase
        loc = ws_root + locbase

        print("_wsdl_client, url", url)
        ws_client = Client(url, transport=trans, timeout=3, location=loc, cache=None)

        return ws_client

    def prepare_collect_for_lims(self, mx_collect_dict):
        # Attention! directory passed by reference. modified in place

        prop = "EDNA_files_dir"
        path = mx_collect_dict[prop]
        ispyb_path = HWR.beamline.session.path_to_ispyb(path)
        mx_collect_dict[prop] = ispyb_path

        prop = "process_directory"
        path = mx_collect_dict["fileinfo"][prop]
        ispyb_path = HWR.beamline.session.path_to_ispyb(path)
        mx_collect_dict["fileinfo"][prop] = ispyb_path

        for i in range(4):
            try:
                prop = "xtalSnapshotFullPath%d" % (i + 1)
                path = mx_collect_dict[prop]
                ispyb_path = HWR.beamline.session.path_to_ispyb(path)
                logging.debug("SOLEIL ISPyBClient - %s is %s " % (prop, ispyb_path))
                mx_collect_dict[prop] = ispyb_path
            except Exception:
                pass

    def prepare_image_for_lims(self, image_dict):
        for prop in ["jpegThumbnailFileFullPath", "jpegFileFullPath"]:
            try:
                path = image_dict[prop]
                ispyb_path = HWR.beamline.session.path_to_ispyb(path)
                image_dict[prop] = ispyb_path
            except Exception:
                pass


def test_hwo(hwo):
    proposal_code = "mx"
    proposal_number = "20100023"
    proposal_psd = "tisabet"

    # proposal_number = '20160745'
    # proposal_psd = '087D2P3252'

    print("Trying to login to ispyb")
    info = hwo.login(proposal_number, proposal_psd)
    print("logging in returns: ", str(info))


def test():
    hwr = HWR.get_hardware_repository()
    hwr.connect()

    db = HWR.beamline.lims

    print("db", db)
    print("dir(db)", dir(db))
    # print 'db._SOLEILISPyBClientShipping', db._SOLEILISPyBClientShipping
    # print 'db.Shipping', db.Shipping

    proposal_code = "mx"
    proposal_number = "20100023"
    proposal_psd = "tisabet"

    info = db.get_proposal(proposal_code, proposal_number)  # proposal_number)
    print(info)

    info = db.login(proposal_number, proposal_psd)
    print(info)


if __name__ == "__main__":
    test()
