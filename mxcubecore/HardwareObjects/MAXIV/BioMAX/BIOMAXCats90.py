"""
  File:  BIOMAXCats90.py

  Description:  This module implements the hardware object for the Biomax ISARA operation

"""
import time
import logging
import gevent

from mxcubecore.HardwareObjects.Cats90 import Cats90
from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import SampleChangerState


class BIOMAXCats90(Cats90):
    def __init__(self, *args):
        """
        Description:
        """
        Cats90.__init__(self, *args)

    def init(self):
        Cats90.init(self)
        self._chnInSoak = self.get_channel_object("_chnInSoak")
        if self._chnInSoak is None:
            self._chnInSoak = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnInSoak",
                    "tangoname": self.tangoname,
                    "polling": 1000,
                },
                "InSoak",
            )

        self.safe_to_center = self.cats_pathsafe

    def cats_pathsafe_changed(self, value):
        self.cats_pathsafe = value
        self._updateState()
        time.sleep(1.0)
        # when cats_pathsafe turns true from false
        # reset safe_to_center to True
        if self.cats_pathsafe:
            self.safe_to_center = True
        self.emit("pathSafeChanged", (value,))

    def load(self, sample=None, wait=True):
        """
        Load a sample.
            overwrite original load() from GenericSampleChanger to allow finer decision
            on command to use (with or without barcode / or allow for wash in some cases)
            Implement that logic in _doLoad()
            Add initial verification about the Powered:
            (NOTE) In fact should be already as the power is considered in the state handling
        """
        if not self._chnPowered.getValue():
            raise Exception(
                "CATS power is not enabled. Please switch on arm power before transferring samples."
            )
            return

        self._updateState()  # remove software flags like Loading.
        logging.getLogger("HWR").debug(
            "  ***** ISARA *** load cmd .state is:  %s " % (self.state)
        )

        sample = self._resolveComponent(sample)
        self.assertNotCharging()

        # set safe_to_center to false
        self.safe_to_center = False
        self._executeTask(SampleChangerState.Loading, False, self._doLoad, sample)
        self.wait_safe_to_center_ready()

    def wait_safe_to_center_ready(self, timeout=-1):
        start = time.clock()
        while not self.safe_to_center:
            if timeout > 0:
                if (time.clock() - start) > timeout:
                    raise Exception("Timeout waiting ready")
            gevent.sleep(0.01)
