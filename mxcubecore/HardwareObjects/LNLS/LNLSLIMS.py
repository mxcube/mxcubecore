"""
A client for ISPyB Webservices.
"""

from mxcubecore.HardwareObjects.ICATLIMS import ICATLIMS
from pyicat_plus.client.main import IcatClient


class LNLSLIMS(ICATLIMS):

    def init(self):
        self.url = self.get_property("ws_root")
        self.ingesters = self.get_property("queue_urls")
        self.investigations = []
        self.samples = []
        
        self.icatClient = IcatClient(
            icatplus_restricted_url="https://icat-plus.cnpem.br",
            metadata_urls=["10.39.50.51"],
            reschedule_investigation_urls=["10.39.50.51"],
        )