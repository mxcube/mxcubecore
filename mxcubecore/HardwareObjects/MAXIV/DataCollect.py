"""
Contains code shared between BioMAX and MicroMAX for implementing
a data collection hardware object.
"""

from typing import Callable, Optional
import gevent
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect
from mxcubecore.HardwareObjects import TangoShutter
import socket


# max time we wait for safety shutter to open, in seconds
SAFETY_SHUTTER_TIMEOUT = 5.0
# max time we wait for detector cover to open or close, in seconds
DETECTOR_COVER_TIMEOUT = 10.0


def _poll_until(condition: Callable, timeout: float, timeout_error_messge: str):
    """
    poll until condition() returns True, give up after timeout seconds
    """
    with gevent.Timeout(timeout, Exception(timeout_error_messge)):
        while not condition():
            gevent.sleep(0.01)


def open_tango_shutter(shutter: TangoShutter, timeout: float, name: str):
    def wait_until_open():
        _poll_until(
            lambda: shutter.is_open,
            timeout,
            f"could not open the {name}",
        )

    # timeout as 0 to not wait
    shutter.open(timeout=0)
    wait_until_open()


def close_tango_shutter(shutter: TangoShutter, timeout: float, name: str):
    def wait_until_closed():
        _poll_until(
            lambda: not shutter.is_open,
            timeout,
            f"could not close the {name}",
        )

    shutter.close(timeout=0)
    wait_until_closed()


def parse_unit_cell_params(params: str) -> list[Optional[float]]:
    """
    Parse the comma separated unit cell parameters string of following format:

        '<cell_a>,<cell_b>,<cell_c>,<cell_alpha>,<cell_beta>,<cell_gamma>'

    Returns cell parameters as a list of floats. Any omitted parameter is set to None.
    """

    def parse():
        for param in params.split(","):
            if param == "":
                yield None
            else:
                yield float(param)

    return list(parse())


class DataCollect(AbstractCollect, HardwareObject):
    def open_safety_shutter(self):
        """
        send 'open' request to safety shutter and wait until it's open
        """
        self.log.info("Opening the safety shutter.")
        open_tango_shutter(
            self.safety_shutter_hwobj, SAFETY_SHUTTER_TIMEOUT, "safety shutter"
        )

    def close_safety_shutter(self):
        """
        send 'close' request to safety shutter and wait until it's closed
        """
        self.log.info("Closing the safety shutter.")
        close_tango_shutter(
            self.safety_shutter_hwobj, SAFETY_SHUTTER_TIMEOUT, "safety shutter"
        )

    def open_detector_cover(self):
        """
        send 'open' request to the detector cover and wait until it's open
        """
        try:
            self.log.info("Opening the detector cover.")
            open_tango_shutter(
                self.detector_cover_hwobj, DETECTOR_COVER_TIMEOUT, "detector cover"
            )
        except Exception:
            self.log.exception("Could not open the detector cover")
            raise RuntimeError("[COLLECT] Could not open the detector cover.")

    def close_detector_cover(self):
        """
        send 'close' request to the detector cover and wait until it's closed
        """
        try:
            self.log.info("Closing the detector cover")
            close_tango_shutter(
                self.detector_cover_hwobj, DETECTOR_COVER_TIMEOUT, "detector cover"
            )
        except Exception:
            self.log.exception("Could not close the detector cover")

    def open_fast_shutter(self):
        """
        Descript. : important to make sure it's passed, as we
                    don't open the fast shutter in MXCuBE
        """
        try:
            self.diffractometer_hwobj.open_fast_shutter()
        except Exception:
            self.user_log.exception("Error opening fast shutter.")
            raise

    def close_fast_shutter(self):
        """
        Descript. :
        """
        # to do, close the fast shutter as early as possible in case
        # MD3 fails to do so
        self.diffractometer_hwobj.close_fast_shutter()

    def get_mxcube_server_ip(self):
        """
        get the ip address of the mxcube server
        """
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)

    def get_header_appendix_sample_reference_dict(
        self, sample_reference_params: dict
    ) -> dict | None:
        """
        build the 'sample_reference' dictionary for the header appendix

        returns the dictionary or None if no sample reference parameters specified
        """

        def filter_empty_vals(**key_vals) -> dict | None:
            """
            build dictionary with specified key-values,
            don't include key-value pairs where value is None or ""

            if the result is an empty dictionary, returns None
            """
            res = {k: v for k, v in key_vals.items() if v}
            if len(res) == 0:
                return None

            return res

        #
        # deal with space group parameters
        #
        space_group = sample_reference_params.get("spacegroup", "")
        if space_group != "":
            # convert to PDB style of space group names
            space_group = self.autoprocessing_hwobj.find_spg_full_name(space_group)

        #
        # deal with unit cell parameters
        #
        a, b, c, alpha, beta, gamma = parse_unit_cell_params(
            sample_reference_params.get("cell", ",,,,,")
        )
        unit_cell = filter_empty_vals(
            a=a, b=b, c=c, alpha=alpha, beta=beta, gamma=gamma
        )

        return filter_empty_vals(space_group=space_group, unit_cell=unit_cell)
