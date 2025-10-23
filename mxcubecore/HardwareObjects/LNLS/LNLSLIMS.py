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
        
    def is_single_session_available(self):
        """
        True if there is no active session and there is
        a single session available
        """
        return (
            self.session_manager.active_session is None
            and len(self.session_manager.sessions) == 1
        )
    
    def login(self, user_name, token, is_local_host=False):
        session_manager, lims_username, sessions = super().login(user_name, token, self.session_manager)
        self.session_manager = session_manager
        self.add_user_and_shared_sessions(lims_username, sessions)
        if self.is_single_session_available():
            single_session = self.session_manager.sessions[0]
            self.set_active_session_by_id(single_session.session_id)

        return session_manager