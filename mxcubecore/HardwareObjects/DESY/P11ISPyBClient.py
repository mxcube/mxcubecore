# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """Copyright The MXCuBE Collaboration"""
__license__ = "LGPLv3+"

import logging
import ssl
from urllib.error import URLError

from suds import WebFault
from suds.transport import TransportError

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ISPyBClient import ISPyBClient

ssl._create_default_https_context = ssl._create_unverified_context


class P11ISPyBClient(ISPyBClient):
    def init(self):
        ISPyBClient.init(self)

        self.simulated_proposal = self.get_property("proposal_simulated")

        if self.simulated_proposal == 1:
            self.simulated_prop_code = self.get_property("proposal_code_simulated")
            self.simulated_prop_number = self.get_property("proposal_number_simulated")
        else:
            self.simulated_prop_code = None
            self.simulated_prop_number = None
        logging.getLogger("HWR").debug(
            "PROPOSAL SIMULATED is %s" % self.simulated_proposal
        )
        logging.getLogger("HWR").debug("PROPOSAL CODE is %s" % self.simulated_prop_code)
        logging.getLogger("HWR").debug(
            "PROPOSAL NUMBER is %s" % self.simulated_prop_number
        )

    def update_data_collection(self, mx_collection, wait=False):
        mx_collection["beamline_name"] = "P11"
        ISPyBClient.update_data_collection(self, mx_collection, wait)

    def _store_data_collection(self, mx_collection, bl_config=None):
        self.prepare_collect_for_lims(mx_collection)
        return ISPyBClient._store_data_collection(self, mx_collection, bl_config)

    def store_image(self, image_dict):
        self.prepare_image_for_lims(image_dict)
        return ISPyBClient.store_image(self, image_dict)

    def store_robot_action(self, robot_action_dict):
        # TODO ISPyB is not ready for now. This prevents from error 500 from the server.
        pass

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
                logging.debug("P11 ISPyBClient - %s is %s " % (prop, ispyb_path))
                mx_collect_dict[prop] = ispyb_path
            except RuntimeWarning("Can not get ISPyB path for %s" % prop):
                pass

    def prepare_image_for_lims(self, image_dict):
        for prop in ["jpegThumbnailFileFullPath", "jpegFileFullPath"]:
            try:
                path = image_dict[prop]
                ispyb_path = HWR.beamline.session.path_to_ispyb(path)
                image_dict[prop] = ispyb_path
            except RuntimeWarning("Can not prepare image path fir LIMS for %s" % prop):
                pass

    def get_proposal(self, proposal_code, proposal_number):
        logging.getLogger("HWR").debug(
            "ISPyB. Obtaining proposal for code=%s / prop_number=%s"
            % (proposal_code, proposal_number)
        )

        try:
            if self._shipping:
                # Attempt to fetch the proposal from ISPyB
                proposal = self._shipping.service.findProposal(
                    proposal_code, proposal_number
                )
            else:
                raise URLError("Shipping service unavailable")

            if proposal:
                proposal["code"] = proposal_code
                proposal["number"] = proposal_number
                return {"Proposal": proposal, "status": {"code": "ok"}}
        except (WebFault, URLError, TransportError) as e:
            # Log the error and fallback
            logging.getLogger("ispyb_client").exception(
                "Error fetching proposal. Returning fallback values."
            )
            return {
                "Proposal": {
                    "code": proposal_code,
                    "number": proposal_number,
                    "title": "Unknown Proposal",
                },
                "status": {"code": "error", "msg": "ISPyB is not connected."},
            }
