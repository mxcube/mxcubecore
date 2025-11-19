import logging

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.MAXIV.MAXIVMD3 import NoPositionBookmarkedError

log = logging.getLogger("user_level_log")


class PrepareOpenHutch:
    """
    Prepare beamline for opening the hutch door.

    - close safety shutter
    - close detector cover
    - close fast shutter
    - move detector to a safe position
    - put MD3 into 'Transfer' phase in case of OSC delivery mode
    - move MD3's `BeamstopPosition` and `CapillaryPosition` to `PARK` in case of HVE
    - if jungfrau is used, take pedestal
    """

    def __call__(self):
        try:
            # Ensure laser is stopped before opening the hutch
            laser = HWR.beamline.get_object_by_role("laser")
            laser.disarm()

            collect = HWR.beamline.collect
            diffractometer = HWR.beamline.diffractometer
            detector = HWR.beamline.detector

            log.info("Preparing experimental hutch for door opening.")

            collect.close_fast_shutter()
            collect.close_safety_shutter()
            collect.close_detector_cover()

            diffractometer.wait_device_ready()
            if HWR.beamline.is_hve_sample_delivery():
                # This is 'equivalent' of Transfer phase for HVE experiments
                log.info("Setting diffractometer to 'equivalent' of Transfer phase.")
                diffractometer.channel_dict["BeamstopPosition"].set_value("PARK")
                diffractometer.channel_dict["CapillaryPosition"].set_value("PARK")
            else:
                log.info("Setting diffractometer to Transfer phase.")
                diffractometer.set_phase("Transfer")

            log.info("Moving detector to safe position.")
            collect.move_detector_to_safe_position()

            if detector.get_property("model") == "JUNGFRAU":
                log.info("Collecting Jungfrau pedestal.")
                detector.pedestal()

        except Exception as ex:
            # Explicitly add raised exception into the log message,
            # so that it is shown to the user in the beamline action UI log.
            log.exception("Error preparing to open hutch.\nError was: '%s'", str(ex))  # noqa: TRY401


class MeasureFlux:
    def __call__(self):
        """
        calculate flux at sample position
        """
        flux_at_sample = HWR.beamline.collect.get_instant_flux()
        log.info("Flux at sample position is %.2e ph/s", flux_at_sample)


class SaveMD3Position:
    def __call__(self):
        HWR.beamline.diffractometer.bookmark_position()


class MoveToMD3SavedPosition:
    def __call__(self):
        try:
            HWR.beamline.diffractometer.goto_bookmarked_position()
        except NoPositionBookmarkedError:
            log.warning("No MD3 position saved.")
