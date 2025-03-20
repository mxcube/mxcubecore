import abc
import logging
import os
import time

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.TaskUtils import error_cleanup


class AbstractEnergyScan(HardwareObject):
    """Energy Scan abstract class"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        super().__init__(name)
        self.data_collect_task = None
        self._egyscan_task = None
        self.scanning = False
        self.cpos = None
        self.energy_scan_parameters = {}

    def init(self):
        """Initialisation"""
        self.lims = HWR.beamline.lims
        if not self.lims:
            logging.getLogger().warning("EnergyScan: no lims set")

    def get_elements(self):
        """Get the configured in the file elements to be used
        Returns:
            (dict): Dictionary {"symbol": str, "energy": str}
        """
        try:
            return self.get_property("elements")["element"]
        except TypeError:
            return []

    def open_fast_shutter(self):
        """
        Open the fast shutter.
        """

    def close_fast_shutter(self):
        """
        Close the fast shutter.
        """

    def energy_scan_hook(self, energy_scan_parameters):
        """
        Execute actions, required before running the raw scan(like changing
        undulator gaps, move to a given energy... These are in general
        beamline specific actions.
        """

    def execute_energy_scan(self, energy_scan_parameters):
        """
        Execute the raw scan sequence. Here is where you pass whatever
        parameters you need to run the raw scan (e.g start/end energy,
        counting time, energy step...).
        """

    def get_static_parameters(self, config_file, element, edge):
        """
        Get any parameters, which are known before hand. Some of them are
        known from the theory, like the peak energy, others are equipment
        specific like the lower/upper ROI limits of the fluorescence detector.
        Usually these parameters are pre-defined in a file, but can also be
        calculated.
        The function should return a distionary with at least defined
        {'edgeEnergy': peak_energy} member, where 'edgeEnergy' is a
        compulsory key.
        It is convinient to put in the same dictionary the remote energy,
        the ROI min/max values.
        There are few more reserved key names:
        'eroi_min', 'eroi_max' - min and max ROI limits if you want ot set one.
        'findattEnergy' - energy to move to if you want to choose the attenuation
        for the scan.
        """
        return {}

    def set_mca_roi(self, eroi_min, eroi_max):
        """
        Configure the fluorescent detector ROI. The input is min/max energy.
        """

    def escan_prepare(self):
        """
        Set the nesessary equipment in position for the scan.
        No need to know the scan paramets.
        """

    def choose_attenuation(self):
        """
        Procedure to set the minimal attenuation in order no preserve
        the sample. Should be done at the energy after the edge.
        """

    def escan_cleanup(self):
        """Execute actions at the end of the scan"""

    def escan_postscan(self):
        """
        set the nesessary equipment in position after the scan
        """

    def do_energy_scan(self):
        """Execute the scan"""
        with error_cleanup(self.escan_cleanup):
            self.escan_prepare()
            self.energy_scan_hook(self.energy_scan_parameters)
            HWR.beamline.safety_shutter.open(timeout=10)
            self.choose_attenuation()
            self.close_fast_shutter()
            logging.getLogger("HWR").debug("Doing the scan, please wait...")
            self.execute_energy_scan(self.energy_scan_parameters)
            self.escan_postscan()
            self.close_fast_shutter()
            self.energy_scan_parameters["flux"] = HWR.beamline.flux.get_value()
            HWR.beamline.safety_shutter.close(timeout=10)
            # send finish sucessfully signal
            self.emit("energyScanFinished", (self.energy_scan_parameters,))
            self.ready_event.set()

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
        """Do the scan"""
        if self._egyscan_task and not self._egyscan_task.ready():
            raise RuntimeError("Scan already started.")

        self.emit("energyScanStarted", ())
        # Set the energy from the element and edge parameters
        static_pars_dict = {}
        static_pars_dict = self.get_static_parameters(
            self.get_property("config_file"), element, edge
        )
        self.cpos = cpos
        self.energy_scan_parameters = static_pars_dict
        self.energy_scan_parameters["element"] = element
        self.energy_scan_parameters["edge"] = edge
        self.energy_scan_parameters["directory"] = directory

        # Calculate the MCA ROI (if needed)
        try:
            self.set_mca_roi(static_pars_dict["eroi_min"], static_pars_dict["eroi_max"])
        except Exception:
            pass

        # create the directory if needed
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.energy_scan_parameters["prefix"] = prefix
        if session_id is not None:
            self.energy_scan_parameters["sessionId"] = session_id
            self.energy_scan_parameters["blSampleId"] = blsample_id
            self.energy_scan_parameters["startTime"] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        self._egyscan_task = gevent.spawn(self.do_energy_scan)

        """
        Use chooch to calculate edge and inflection point
        The brick expects the folowing parameters to be returned:
        pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, rm,
        chooch_graph_x, chooch_graph_y1, chooch_graph_y2, title)
        """
