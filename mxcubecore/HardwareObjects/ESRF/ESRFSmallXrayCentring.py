#! /usr/bin/env python
# encoding: utf-8
#
# This file is part of MXCuBE.
#
# MXCuBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MXCuBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with MXCuBE.  If not, see <https://www.gnu.org/licenses/>.
"""
"""

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import json
import logging
import os
import time

import requests

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractXrayCentring import (
    AbstractXrayCentring,
)

__copyright__ = """ Copyright © 2016 - 2022 by MXCuBE Collaboration """
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "25/03/2022"
__category__ = "General"


class ESRFSmallXrayCentring(AbstractXrayCentring):
    def execute(self):
        """Executes the BES workflow SmallXrayCentring"""

        logging.getLogger("HWR").debug("Executes SmallXrayCentring workflow")
        workflow_name = "SmallXrayCentring"
        bes_host = "mxbes2-1707"
        bes_port = 38180
        task_group_node_id = self._data_collection_group._node_id
        dict_parameters = json.loads(json.dumps(HWR.beamline.workflow.dict_parameters))
        dict_parameters["sample_node_id"] = task_group_node_id
        dict_parameters["end_workflow_in_mxcube"] = False
        dict_parameters["workflow_id"] = HWR.beamline.xml_rpc_server.workflow_id
        logging.getLogger("HWR").info("Starting workflow {0}".format(workflow_name))
        logging.getLogger("HWR").info(
            "Starting a workflow on http://%s:%d/BES" % (bes_host, bes_port)
        )
        bes_url = "http://{0}:{1}".format(bes_host, bes_port)
        start_URL = os.path.join(bes_url, "RUN", workflow_name)
        logging.getLogger("HWR").info("BES start URL: %r" % start_URL)
        response = requests.post(start_URL, json=dict_parameters)
        if response.status_code == 200:
            request_id = response.text
            logging.getLogger("HWR").info(
                "Workflow started, request id: %r" % request_id
            )
        else:
            logging.getLogger("HWR").error("Workflow didn't start!")
            logging.getLogger("HWR").error(response.text)
        status_url = os.path.join(bes_url, "STATUS", str(request_id))
        logging.getLogger("HWR").info("STATUS URL: %r" % status_url)
        start_time = time.time()
        max_time = 600  # Max five minutes
        finished = False
        timed_out = False
        while not timed_out and not finished:
            response = requests.get(status_url)
            if response.text == "STARTED":
                logging.getLogger("HWR").info("Workflow still running...")
                time.sleep(1)
            elif response.text == "FINISHED":
                logging.getLogger("HWR").info("Workflow finished!")
                finished = True
            if time.time() > start_time + max_time:
                logging.getLogger("HWR").info("Workflow timed out!")
                timed_out = True
