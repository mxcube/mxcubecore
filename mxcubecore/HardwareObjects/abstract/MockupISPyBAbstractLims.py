import logging
import warnings
from typing import List

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractLims import AbstractLims
from mxcubecore.HardwareObjects.abstract.ISPyBDataAdapter import ISPyBDataAdapter
from mxcubecore.model.lims_session import (
    Lims,
)


class MockupISPyBAbstractLims(AbstractLims):
    """
    Web-service client for ISPyB.
    """

    def __init__(self, name):
        super().__init__(name)
        self.ldapConnection = None
        self.pyispyb = None
        self._translations = {}
        self.authServerType = None
        self.loginTranslate = None
        self.base_result_url = None
        self.login_ok = False

    def init(self):
        pass

    def _create_data_adapter(self) -> ISPyBDataAdapter:
        pass

    def get_lims_name(self) -> List[Lims]:
        return [
            Lims(
                name="ISPyB",
                description="Information System for protein Crystallographic Beamlines",
            )
        ]

    def get_user_name(self):
        raise NotImplementedError

    def get_full_user_name(self):
        raise NotImplementedError

    def is_user_login_type(self):
        raise NotImplementedError

    def store_beamline_setup(self, session_id, bl_config):
        pass

    def _translate(self, code, what):
        pass

    def echo(self):
        pass

    def ldap_login(self, login_name, psd):
        pass

    def ispyb_login(self, login_name, psd):
        raise NotImplementedError

    def store_data_collection(self, mx_collection, bl_config=None):
        pass

    def update_data_collection(self, mx_collection):
        pass

    def finalize_data_collection(self, mx_collection):
        pass

    def _store_data_collection(self, mx_collection, bl_config=None):
        pass

    def _update_data_collection(self, mx_collection):
        pass

    def update_bl_sample(self, bl_sample):
        pass

    def store_image(self, image_dict):
        pass

    def find_sample_by_sample_id(self, sample_id):
        pass

    def get_samples(self, lims_name):
        pass

    def create_session(self, proposal_id: str):
        pass

    def store_energy_scan(self, energyscan_dict):
        pass

    def associate_bl_sample_and_energy_scan(self, entry_dict):
        pass

    def get_data_collection(self, data_collection_id):
        pass

    def get_session(self, session_id):
        pass

    def store_xfe_spectrum(self, xfespectrum_dict):
        pass

    def is_connected(self):
        pass

    def isInhouseUser(self, proposal_code, proposal_number):
        pass

    def _store_data_collection_group(self, group_data):
        pass

    def store_workflow(self, *args, **kwargs):
        pass

    def store_robot_action(self, robot_action_dict):
        pass

    def create_mx_collection(self, collection_parameters):
        pass

    def create_ssx_collection(
        self, data_path, collection_parameters, beamline_parameters, extra_lims_values
    ):
        pass