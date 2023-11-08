import logging
import time
import gevent
import tango

from mxcubecore import HardwareRepository as HWR
from mxcubecore.CommandContainer import CommandObject
from mxcubecore.HardwareObjects.BeamlineActions import (
    BeamlineActions,
)

DET_SAFE_POSITION = 500  # mm


class PrepareOpenHutch:
    """
    Prepare beamline for opening the hutch door

    Close safety shutter, close detector cover and move detector to a safe area
    """
    def __call__(self, *args, **kw):
        try:
            logging.getLogger("HWR").info("Preparing experimental hutch for door openning.")
            if (
                HWR.beamline.safety_shutter is not None
                and HWR.beamline.safety_shutter.getShutterState() == "opened"
            ):
                logging.getLogger("HWR").info("Closing safety shutter...")
                HWR.safety_shutter.closeShutter()
                while HWR.beamline.safety_shutter.getShutterState() == "opened":
                    gevent.sleep(0.1)

            logging.getLogger("HWR").info("Closing detector cover...")

            close_det_cover = CloseDetectorCover()
            close_det_cover()
            if HWR.beamline.detector is not None:
                logging.getLogger("HWR").info("Moving detector to safe area...")
                try:
                    HWR.beamline.detector.distance_motor_hwobj.set_value(DET_SAFE_POSITION)
                except Exception:
                    logging.getLogger("HWR").warning("Could not move detector to safe position")
        except Exception as ex:
            logging.getLogger("HWR").exception("Could not PrepareOpenHutch")
            print(ex)


class CloseDetectorCover:
    def __call__(self, *args, **kw):
        """
        Close detector cover
        """
        try:
            logging.getLogger("HWR").info("Closing the detector cover")
            plc = tango.DeviceProxy('b312a/vac/plc-01')
            plc.B312A_E06_DIA_DETC01_ENAC = 1
            plc.B312A_E06_DIA_DETC01_CLC = 1
        except Exception:
            logging.getLogger("HWR").exception("Could not close the detector cover")
            pass


class OpenDetectorCover:
    def __call__(self, *args, **kw):
        """
        Open detector cover
        """
        try:
            logging.getLogger("HWR").info("Opening the detector cover")
            plc = tango.DeviceProxy('b312a/vac/plc-01')
            plc.B312A_E06_DIA_DETC01_ENAC = 1
            plc.B312A_E06_DIA_DETC01_OPC = 1
        except Exception:
            logging.getLogger("HWR").exception("Could not close the detector cover")
            pass


class BeamtimeEnd:
    def __call__(self, *args, **kw):
        """
        TBD
        """
        try:
            prepare_open_hutch = PrepareOpenHutch()
            prepare_open_hutch()
            cmd = self.getCommandObject('beamtime_end')
            cmd(wait=True)
        except Exception:
            logging.getLogger("HWR").error("Cannot end beamtime.")


class BeamtimeStart:
    def __call__(self, *args, **kw):
        """
        TBD
        """
        try:
            cmd = self.getCommandObject('beamtime_start')
            cmd(wait=True)
        except Exception:
            logging.getLogger("HWR").error("Cannot start beamtime.")


class MICROMAXBeamlineActions(BeamlineActions):
    def __init__(self, *args):
        super().__init__(*args)
