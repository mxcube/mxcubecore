"""
A client for ISPyB Webservices.
"""

from pyicat_plus.client.main import IcatClient

from mxcubecore.HardwareObjects.ICATLIMS import ICATLIMS


class LNLSLIMS(ICATLIMS):
    def init(self):
        self.url = self.get_property("ws_root")
        self.ingesters = self.get_property("queue_urls")
        self.investigations = []
        self.samples = []

        self.icatClient = IcatClient(
            icatplus_restricted_url="https://icat-plus.cnpem.br"
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

    def _create_icat_session(self, user_name: str, password: str):
        self.icat_session = self.icatClient.do_log_in(
            username=user_name, password=password, plugin="oidc"
        )

    def login(self, user_name, token, is_local_host):
        self.is_local_host = is_local_host
        session_manager, lims_username, sessions = super().login(
            user_name, token, self.session_manager
        )
        self.session_manager = session_manager
        self.add_user_and_shared_sessions(lims_username, sessions)
        if self.is_single_session_available():
            single_session = self.session_manager.sessions[0]
            self.set_active_session_by_id(single_session.session_id)

        return session_manager
