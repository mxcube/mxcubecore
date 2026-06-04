import itertools
import uuid

from mxcubecore.HardwareObjects.abstract.ISPyBAbstractLims import ISPyBAbstractLIMS
from mxcubecore.model.lims_session import (
    LimsSessionManager,
    Proposal,
    Session,
)

"""
A client for ISPyB Webservices.
"""

import logging


class MockupProposalTypeISPyBLims(ISPyBAbstractLIMS):
    """
    ISPyB proposal-based client
    """

    def __init__(self, name):
        super().__init__(name)

    def is_user_login_type(self):
        return False

    def get_proposals_by_user(self, login_id: str):
        raise Exception("Not implemented")

    def get_full_user_name(self):
        return self.get_user_name()

    def get_user_name(self):
        """
        Because it is a proposal based it returns the proposal plus the uuid4
        """
        pass

    def _authenticate(self, user_name, psd):
        pass

    def is_session_already_active_by_code(self, code: str, number: str) -> bool:
        pass

    def set_active_session_by_id(self, proposal_name: str) -> Session:
        pass

    def _get_proposal_code_and_number_by_proposal_name(self, proposal_name):
        pass

    def get_session_manager_by_code_number(
        self, code: str, number: str, is_local_host: bool
    ) -> LimsSessionManager:
        pass

    def get_session_manager_by_proposal_name(
        self, proposal_name: str, is_local_host: bool
    ) -> LimsSessionManager:
        pass

    def login(
        self, user_name: str, password: str, is_local_host: bool
    ) -> LimsSessionManager:
        pass