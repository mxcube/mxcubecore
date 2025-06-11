from __future__ import print_function

import logging
import warnings
from typing import List

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractLims import AbstractLims
from mxcubecore.HardwareObjects.abstract.ISPyBDataAdapter import ISPyBDataAdapter
from mxcubecore.model.lims_session import (
    Lims,
    LimsSessionManager,
)


class ISPyBAbstractLIMS(AbstractLims):
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

        #
        # WebService related configuration
        #
        self.ws_root = None
        self.ws_username = None
        self.ws_password = None

    def init(self):
        super().init()
        self.pyispyb = self.get_object_by_role("pyispyb")
        self.icat_client = self.get_object_by_role("icat_client")

        self.samples = []
        self.authServerType = self.get_property("authServerType") or "ldap"
        if self.authServerType == "ldap":
            # Initialize ldap
            self.ldapConnection = self.get_object_by_role("ldapServer")
            if self.ldapConnection is None:
                logging.getLogger("HWR").debug("LDAP Server is not available")

        self.loginTranslate = self.get_property("loginTranslate") or True

        # ISPyB Credentials
        self.ws_root = self.get_property("ws_root")
        self.ws_username = self.get_property("ws_username") or None
        self.ws_password = str(self.get_property("ws_password")) or None

        self.proxy_address = self.get_property("proxy_address")
        if self.proxy_address:
            self.proxy = {"http": self.proxy_address, "https": self.proxy_address}
        else:
            self.proxy = {}

        try:
            self.base_result_url = self.get_property("base_result_url").strip()
        except AttributeError:
            pass

        self.adapter = self._create_data_adapter()
        logging.getLogger("HWR").debug("[ISPYB] Proxy address: %s" % self.proxy)

        # Add the porposal codes defined in the configuration xml file
        # to a directory. Used by translate()
        if hasattr(HWR.beamline.session, "proposals"):
            for proposal in HWR.beamline.session["proposals"]:
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

    def _create_data_adapter(self) -> ISPyBDataAdapter:
        return ISPyBDataAdapter(
            self.ws_root.strip(),
            self.proxy,
            self.ws_username,
            self.ws_password,
            self.beamline_name,
        )

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
        self.adapter.store_beamline_setup(session_id, bl_config)

    def _translate(self, code, what):
        try:
            translated = self._translations[code][what]
        except KeyError:
            translated = code
        return translated

    def echo(self):
        if not self.adapter._shipping:
            msg = "Error in echo: Could not connect to server."
            logging.getLogger("ispyb_client").warning(msg)
            raise Exception("Error in echo: Could not connect to server.")

        try:
            self.adapter._shipping._shipping.service.echo()
            return True
        except Exception as e:
            logging.getLogger("ispyb_client").error(str(e))

        return False

    def ldap_login(self, login_name, psd):
        warnings.warn(
            (
                "Using Authenticator from ISPyBClient is deprecated,"
                "use Authenticator to authenticate separately and then login to ISPyB"
            ),
            DeprecationWarning,
        )

        return self.ldapConnection.authenticate(login_name, psd)

    def ispyb_login(self, login_name, psd):
        raise NotImplementedError

    def store_data_collection(self, mx_collection, bl_config=None):
        return self._store_data_collection(mx_collection, bl_config)

    def update_data_collection(self, mx_collection):
        return self._update_data_collection(mx_collection)

    def finalize_data_collection(self, mx_collection):
        # Also upload the same data to icat if icat_client is available
        if self.icat_client:
            self.icat_client.store_data_collection(mx_collection)

        return self._update_data_collection(mx_collection)

    def _store_data_collection(self, mx_collection, bl_config=None):
        return self.adapter.store_data_collection(mx_collection, bl_config)

    def _update_data_collection(self, mx_collection):
        return self.adapter._update_data_collection(mx_collection)

    def update_bl_sample(self, bl_sample):
        return self.adapter.update_bl_sample(bl_sample)

    def store_image(self, image_dict):
        self.adapter.store_image(image_dict)

    def find_sample_by_sample_id(self, sample_id):
        for sample in self.samples:
            try:
                if int(sample.get("limsID")) == sample_id:
                    return sample
            except (TypeError, KeyError):
                pass
        return None

    def get_samples(self, lims_name):
        self.samples = []
        if self.session_manager.active_session is not None:
            self.samples = self.adapter.get_samples(
                self.session_manager.active_session.proposal_id
            )
            logging.getLogger("HWR").debug(
                "get_samples. %s samples retrieved. proposal_id=%s lims_name=%s"
                % (
                    len(self.samples),
                    self.session_manager.active_session.proposal_id,
                    lims_name,
                )
            )
        return self.samples

    def create_session(self, proposal_id: str):
        logging.getLogger("HWR").debug("create_session. proposal_id=%s" % proposal_id)
        session_manager = self.adapter.create_session(proposal_id, self.beamline_name)
        logging.getLogger("HWR").debug("Session created. proposal_id=%s" % proposal_id)
        return session_manager

    def store_energy_scan(self, energyscan_dict):
        return self.adapter.store_energy_scan(energyscan_dict)

    def associate_bl_sample_and_energy_scan(self, entry_dict):
        return self.adapter.associate_bl_sample_and_energy_scan(entry_dict)

    def get_data_collection(self, data_collection_id):
        return self.adapter.get_data_collection(self, data_collection_id)

    def get_session(self, session_id):
        return self.adapter.get_session(session_id)

    def store_xfe_spectrum(self, xfespectrum_dict):
        return self.adapter.store_xfe_spectrum(xfespectrum_dict)

    def is_connected(self):
        return self.login_ok

    def isInhouseUser(self, proposal_code, proposal_number):
        for proposal in self["inhouse"]:
            if proposal_code == proposal.code:
                if str(proposal_number) == str(proposal.number):
                    return True
        return False

    def _store_data_collection_group(self, group_data):
        return self.adapter._store_data_collection_group(group_data)

    def store_workflow(self, *args, **kwargs):
        try:
            return self._store_workflow(*args, **kwargs)
        except gevent.GreenletExit:
            raise
        except Exception:
            logging.exception("Could not store workflow")
            return None, None, None

    def store_robot_action(self, robot_action_dict):
        return self.adapter.store_robot_action(robot_action_dict)

    def create_mx_collection(self, collection_parameters):
        self.icat_client.create_mx_collection(collection_parameters)

    def create_ssx_collection(
        self, data_path, collection_parameters, beamline_parameters, extra_lims_values
    ):
        self.icat_client.create_ssx_collection(
            data_path, collection_parameters, beamline_parameters, extra_lims_values
        )
