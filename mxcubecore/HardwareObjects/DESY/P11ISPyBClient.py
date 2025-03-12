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

import itertools
import json
import os
import sys
import time
import traceback
import warnings
from collections import namedtuple
from datetime import datetime, timedelta
from pprint import pformat

try:
    from urllib2 import URLError
    from urlparse import urljoin
except Exception:
    # Python3
    from urllib.parse import urljoin
    from urllib.error import URLError

from suds import WebFault
from suds.client import Client
from suds.sudsobject import asdict

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.utils.conversion import string_types

"""
A client for ISPyB Webservices.
"""

import logging

import gevent

suds_encode = str.encode

if sys.version_info > (3, 0):
    suds_encode = bytes.decode

import logging
import ssl
from urllib.error import URLError

from suds import WebFault
from suds.transport import TransportError

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.DESY.ISPyBClient import ISPyBClient

ssl._create_default_https_context = ssl._create_unverified_context


class P11ISPyBClient(ISPyBClient):
    def init(self):
        ISPyBClient.init(self)

        self.simulated_proposal = self.get_property("proposal_simulated")
        self.beamline_name = "P11"

        if self.simulated_proposal == 1:
            self.simulated_prop_code = self.get_property("proposal_code_simulated")
            self.simulated_prop_number = self.get_property("proposal_number_simulated")

            logging.getLogger("HWR").debug(
                "PROPOSAL SIMULATED is %s" % self.simulated_proposal
            )
            logging.getLogger("HWR").debug(
                "SIMULATED PROPOSAL CODE is %s" % self.simulated_prop_code
            )
            logging.getLogger("HWR").debug(
                "SIMULATED PROPOSAL NUMBER is %s" % self.simulated_prop_number
            )
        else:
            self.simulated_prop_code = None
            self.simulated_prop_number = None

#    def update_data_collection(self, mx_collection, wait=False):
#        ISPyBClient.update_data_collection(self, mx_collection, wait)
#    
#    def _store_data_collection(self, mx_collection, bl_config=None):
#        # self.prepare_collect_for_lims(mx_collection)
#        
#        bl_config=HWR.beamline.collect.bl_config
#        print(bl_config)
#        return ISPyBClient._store_data_collection(self, mx_collection, bl_config)
#   
    def store_image(self, image_dict):
        self.prepare_image_for_lims(image_dict)
        return ISPyBClient.store_image(self, image_dict)
    
#    def store_robot_action(self, robot_action_dict):
#        # TODO ISPyB is not ready for now. This prevents from error 500 from the server.
#        pass



    def store_beamline_setup(self, session_id, bl_config):
        """
        Stores the beamline setup dict <bl_config>.

        :param session_id: The session id that the beamline_setup
                           should be associated with.
        :type session_id: int

        :param bl_config: The dictonary with beamline settings.
        :type bl_config: dict

        :returns beamline_setup_id: The database id of the beamline setup.
        :rtype: str

        
        from AbstractCollect.py:


        BeamlineConfig = collections.namedtuple(
        "BeamlineConfig",
            [
                "synchrotron_name",
                "directory_prefix",
                "default_exposure_time",
                "minimum_exposure_time",
                "detector_fileext",
                "detector_type",
                "detector_manufacturer",
                "detector_model",
                "detector_px",
                "detector_py",
                "detector_binning_mode",
                "undulators",
                "focusing_optic",
                "monochromator_type",
                "beam_divergence_vertical",
                "beam_divergence_horizontal",
                "polarisation",
                "input_files_server",
            ],
            )


        from: ./ispyb-ejb/src/main/java/ispyb/server/mx/vos/collections/Detector3VO.java

        public Detector3VO(Detector3VO vo){
		super();
		this.detectorId = vo.getDetectorId();
		this.detectorType = vo.getDetectorType();
		this.detectorManufacturer = vo.getDetectorManufacturer();
		this.detectorModel = vo.getDetectorModel();
		this.detectorPixelSizeHorizontal = vo.getDetectorPixelSizeHorizontal();
		this.detectorPixelSizeVertical = vo.getDetectorPixelSizeVertical();
		this.detectorSerialNumber = vo.getDetectorSerialNumber();
		this.detectorDistanceMax = vo.getDetectorDistanceMax();
		this.detectorDistanceMin = vo.getDetectorDistanceMin();
		this.trustedPixelValueRangeLower = vo.getTrustedPixelValueRangeLower();
		this.trustedPixelValueRangeUpper = vo.getTrustedPixelValueRangeUpper();
		this.sensorThickness = vo.getSensorThickness();
		this.overload = vo.getOverload();
		this.xGeoCorr = vo.getxGeoCorr();
		this.yGeoCorr = vo.getyGeoCorr();
		this.detectorMode = vo.getDetectorMode();
	}
(beamLineSetup3VO){
   beamDivergenceHorizontal = None
   beamDivergenceVertical = None
   beamLineSetupId = None
   CS = None
   focalSpotSizeAtSample = None
   focusingOptic = "KB Mirrors"
   goniostatMaxOscillationSpeed = None
   goniostatMinOscillationWidth = None
   maxExpTimePerDataCollection = None
   minExposureTimePerImage = None
   minTransmission = None
   monochromatorType = "Si (111)"
   polarisation = 1
   setupDate = "2025-02-21T18:41:26"
   synchrotronMode = "Machine studies"
   synchrotronName = "DESY"
   undulatorType1 = None
   undulatorType2 = None
   undulatorType3 = None
 }



        """

        blSetupId = 0
        if self._collection:

            session = {}

            try:
                session = self.get_session(session_id)
            except Exception:
                logging.getLogger("ispyb_client").exception(
                    "ISPyBClient: exception in store_beam_line_setup"
                )
            else:
                if session is not None:
                    try:

                        print(bl_config)

                        bl_config.beamDivergenceHorizontal = 0.5 
                        bl_config.beamDivergenceVertical = 0.5
                        bl_config.undulatorType1 = "U32"

                        blSetupId = self._collection.service.storeOrUpdateBeamLineSetup(
                            bl_config
                        )

                        session["beamLineSetupId"] = blSetupId
                        self.update_session(session)

                    except WebFault as e:
                        logging.getLogger("ispyb_client").exception(str(e))
                    except URLError:
                        logging.getLogger("ispyb_client").exception(
                            _CONNECTION_ERROR_MSG
                        )
        else:
            logging.getLogger("ispyb_client").exception(
                "Error in store_beamline_setup: could not connect" + " to server"
            )

        return blSetupId




    def _store_data_collection_group(self, group_data):
        """ """

        # Workaround to make the data collection work even if ISPyB is not available due to the beamtime is not opened.
        try:
            group_id = self._collection.service.storeOrUpdateDataCollectionGroup(
                group_data
            )
        except:
            group_id = 9999

        return group_id

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
