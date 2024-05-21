import logging
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.BeamlineActions import BeamlineActions


log = logging.getLogger("HWR")


class PrepareOpenHutch:
    """
    Prepare beamline for opening the hutch door.

    - close safety shutter
    - close detector cover
    - move detector to a safe position
    - put MD3 into 'Transfer' phase
    - if jungfrau is used, take pedestal
    """

    def __call__(self, *args, **kw):
        try:
            collect = HWR.beamline.collect
            diffractometer = HWR.beamline.diffractometer
            detector = HWR.beamline.detector

            log.info("Preparing experimental hutch for door opening.")

            collect.close_safety_shutter()
            collect.close_detector_cover()

            log.info("Setting diffractometer to transfer phase.")
            diffractometer.wait_device_ready()
            diffractometer.set_phase("Transfer")

            log.info("Moving detector to safe position.")
            collect.move_detector_to_safe_position()

            if detector.get_property("model") == "JUNGFRAU":
                log.info("Collecting Jungfrau pedestal.")
                detector.pedestal()

        except Exception as ex:
            # Explicitly add raised exception into the log message,
            # so that it is shown to the user in the beamline action UI log.
            log.exception(f"Error preparing to open hutch.\nError was: '{str(ex)}'")


class CloseDetectorCover:
    def __call__(self, *args, **kw):
        """
        Close detector cover
        """
        HWR.beamline.collect.close_detector_cover()


class OpenDetectorCover:
    def __call__(self, *args, **kw):
        """
        Open detector cover
        """
        HWR.beamline.collect.open_detector_cover()


class BeamtimeEnd:
    def __call__(self, *args, **kw):
        """
        TBD
        """
        try:
            prepare_open_hutch = PrepareOpenHutch()
            prepare_open_hutch()
            cmd = self.getCommandObject("beamtime_end")
            cmd(wait=True)
        except Exception as ex:
            logging.getLogger("HWR").exception(
                "Cannot end beamtime. Error was {}".format(ex)
            )


class BeamtimeStart:
    def __call__(self, *args, **kw):
        """
        TBD: sardana macro not yet available in MicroMAX
        """
        try:
            cmd = self.getCommandObject("beamtime_start")
            cmd(wait=True)
        except Exception as ex:
            logging.getLogger("HWR").error(
                "Cannot start beamtime. Error was {}".format(ex)
            )


class MICROMAXBeamlineActions(BeamlineActions):
    def __init__(self, *args):
        super().__init__(*args)
