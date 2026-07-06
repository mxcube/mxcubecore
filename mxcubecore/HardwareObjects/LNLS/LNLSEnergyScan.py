import os
import time

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractEnergyScan import AbstractEnergyScan


class LNLSEnergyScan(AbstractEnergyScan):
    """
    Energy Scan class for LNLS. It uses bluesky to launch the Energy Scan
    data collection.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSEnergyScan.LNLSEnergyScan
      configuration:
        elements:
          element:
            - energy: K
              symbol: Mn
            - energy: K
              symbol: Fe
            - energy: K
    """

    def __init__(self, name):
        super().__init__(name)
        self._bluesky_api = None

    def init(self):
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.energy = HWR.beamline.get_object_by_role("energy")
        self.ready_event = gevent.event.Event()

    def start_energy_scan(
        self,
        element,
        edge,
        directory,
        prefix,
        session_id=None,
        blsample_id=None,
        cpos=None,
    ):
        if self._bluesky_api.api.status()["manager_state"] == "executing_queue":
            raise RuntimeError("Another Bluesky plan is still running")

        self.emit("energyScanStarted", ())

        self.energy.update_state(self.STATES.BUSY)

        self.energy_scan_parameters["element"] = element
        self.energy_scan_parameters["edge"] = edge
        self.energy_scan_parameters["directory"] = directory
        os.makedirs(directory, exist_ok=True)
        self.energy_scan_parameters["prefix"] = prefix
        if session_id is not None:
            self.energy_scan_parameters["sessionId"] = session_id
            self.energy_scan_parameters["blSampleId"] = blsample_id
            self.energy_scan_parameters["startTime"] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        plan_kwargs = {
            "element": element,
            "edge": edge,
            "file_path": directory,
            "file_name": prefix,
            "num_steps": 200,
        }

        self._bluesky_api.execute_plan(
            plan_name="energy_scan",
            kwargs=plan_kwargs,
        )

        self.emit("energyScanFinished", (self.energy_scan_parameters,))
        self.ready_event.set()
        self.energy.update_state(self.STATES.READY)

    def do_chooch(self, elt, edge, scan_directory, archive_directory, prefix):
        return (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
