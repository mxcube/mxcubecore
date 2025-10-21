"""
A client for ISPyB Webservices.
"""

from mxcubecore.HardwareObjects.ICATLIMS import ICATLIMS
from pyicat_plus.client.main import IcatClient


class LNLSLIMS(ICATLIMS):

    def init(self):
        super().init()
        self.icatClient = IcatClient(
            icatplus_restricted_url=self.url,
            metadata_urls=["bcu-mq-01:61613"],
            reschedule_investigation_urls=["bcu-mq-01:61613"],
        )
