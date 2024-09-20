from mxcubecore.BaseHardwareObjects import HardwareObject
import logging
import sys
import urllib.request

__credits__ = ["MXCuBE collaboration"]


class P11DoorInterlock(HardwareObject):
    
    
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.door_interlock_state = None
        self.simulationMode=False

    def init(self):
        self.door_interlock_state = self.STATES.READY

    def connected(self):
        self.set_is_ready(True)

    def disconnected(self):
        self.set_is_ready(False)

    def door_is_interlocked(self):
        return self.door_interlock_state in [self.STATES.READY]

    def get_state(self):
        return self.door_interlock_state

    def unlock(self):
        self.breakInterlockEH()
    
    def unlock_door_interlock(self):
        if self.door_interlock_state == "locked_active":
            self.door_interlock_state = "unlocked"
        self.emit("doorInterlockStateChanged", self.door_interlock_state, "")

    def breakInterlockEH(self):
        """Command to break the interlock by sending a request to a URL."""
        if not self.simulationMode:
            logging.info("Attempting to break interlock by opening EH")
            url = "https://ics.desy.de//tineinterface/?action=write&deviceName=G11_2_AbrkIntrlk"
            success = self.fetch_url(url)
            if success:
                logging.info("EH opened successfully")
                # Update the state to reflect that the interlock was broken
                self.emit("doorInterlockStateChanged", self.door_interlock_state, "")
            else:
                logging.error("Failed to open EH")

    def fetch_url(self, url, timeout=3, retries=10):
        """Fetch URL with retry mechanism."""
        for attempt in range(retries):
            try:
                result = urllib.request.urlopen(url, None, timeout).readlines()
                logging.info(f"Successfully fetched URL: {url}")
                return True  # Success
            except Exception as e:
                logging.error(f"Error fetching URL: {url} on attempt {attempt + 1}")
                logging.error(f"Error details: {sys.exc_info()}")
                if attempt + 1 == retries:
                    logging.error(f"All {retries} attempts failed.")
                    return False  # Failed after retries
