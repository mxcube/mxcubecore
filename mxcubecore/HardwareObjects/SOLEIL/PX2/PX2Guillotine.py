# -*- coding: utf-8 -*-
"""Tango Shutter Hardware Object
Example XML:
<object class = "TangoShutter">
  <username>label for users</username>
  <command type="tango" tangoname="my device" name="Open">Open</command>
  <command type="tango" tangoname="my device" name="Close">Close</command>
  <channel type="tango" name="State" tangoname="my device" polling="1000">State</channel>
</object>

"""

import logging
import time
from mxcubecore import BaseHardwareObjects
from mxcubecore import HardwareRepository as HWR


class PX2Guillotine(BaseHardwareObjects.HardwareObject):
    shutterState = {
        # 0:  'ON',
        # 1:  'OFF',
        "False": "CLOSED",
        "True": "OPENED",
        "0": "CLOSED",
        "1": "OPENED",
        "4": "INSERT",
        "5": "EXTRACT",
        "6": "MOVING",
        "7": "STANDBY",
        "8": "FAULT",
        "9": "INIT",
        "10": "RUNNING",
        "11": "ALARM",
        "12": "DISABLED",
        "13": "UNKNOWN",
        "-1": "FAULT",
        "None": "UNKNOWN",
        "UNKNOWN": "UNKNOWN",
        "CLOSE": "CLOSED",
        "OPEN": "OPENED",
        "INSERT": "CLOSED",
        "EXTRACT": "OPENED",
        "MOVING": "MOVING",
        "RUNNING": "MOVING",
        "_": "AUTOMATIC",
        "FAULT": "FAULT",
        "DISABLE": "DISABLED",
        "OFF": "FAULT",
        "STANDBY": "STANDBY",
        "ON": "UNKNOWN",
        "ALARM": "ALARM",
    }
    # shutterState = {
    # None: 'unknown',
    # 'UNKNOWN': 'unknown',
    # 'CLOSE': 'closed',
    # 'OPEN': 'opened',
    # 'INSERT': 'closed',
    # 'EXTRACT': 'opened',
    # 'MOVING': 'moving',
    # 'RUNNING':'moving',
    # '_': 'automatic',
    # 'FAULT': 'fault',
    # 'DISABLE': 'disabled',
    # 'OFF': 'fault',
    # 'STANDBY': 'standby',
    # 'ON': 'unknown'
    # }
    shutterStateString = {
        "ON": "white",
        "OFF": "#012345",
        "CLOSED": "#C03000",
        "CLOSE": "#FF00FF",
        "OPEN": "#00FF00",
        "OPENED": "#00FF00",
        "INSERT": "#EC3CDD",
        "EXTRACT": "#512345",
        "MOVING": "#663300",
        "STANDBY": "#009900",
        "FAULT": "#990000",
        "INIT": "#990000",
        "RUNNING": "#990000",
        "ALARM": "#990000",
        "DISABLED": "#EC3CDD",
        "UNKNOWN": "GRAY",
        "FAULT": "#FF0000",
    }

    def __init__(self, name):
        super().__init__(name)
        logging.info("Guillotine init ")

    def init(self):
        self._shutterStateValue = "UNKNOWN"
        self._currentDistance = "None"
        self._d_security = self.get_property("security_distance")
        self._d_home = self.get_property("safe_distance")
        try:
            self.shutChannel = self.get_channel_object("State")
            self.shutChannel.connect_signal("update", self.shutterStateChanged)

            self.pss = self.get_object_by_role("pss")

            self.connect(
                HWR.beamline.detector.distance,
                "valueChanged",
                self.shutterStateChanged,
            )
            self.connect(
                HWR.beamline.detector.distance,
                "valueChanged",
                self.updateDetectorDistance,
            )

            for command_name in ("_Insert", "_Extract"):
                setattr(self, command_name, self.get_command_object(command_name))

        except KeyError:
            logging.getLogger().warning("%s: cannot report State", self.name())

        try:
            self.pss_door = self.get_property("tangoname_pss")
        except Exception:
            logging.getLogger("HWR").error(
                "Guillotine I11-MA-CE/PSS/DB_DATA: tangopssDevice is not defined "
            )

        if self.pss_door is not None:
            self.memIntChan = self.get_channel_object("memInt")
            self.connect(self.memIntChan, "update", self.updateGuillotine)
        else:
            logging.getLogger("HWR").error("Guillotine: tangopssDevice is not defined ")

    def shutterStateChanged(self, value):
        #
        # emit signal
        #
        if isinstance(value, float):
            value = self.shutChannel.value
        self.shutterStateValue = str(value)
        self.emit("shutterStateChanged", (self.getShutterState(),))

    def getShutterState(self):
        # A tester dans les conditio
        # if self._currentDistance < self._d_security:
        # if self.pss.getWagoState() != "ready":
        #    return "disabled"
        if not self.checkDistance():
            return "disabled"
        return PX2Guillotine.shutterState.get(self.shutterStateValue, "UNKNOWN").lower()

    def updateDetectorDistance(self, value):
        logging.info("UpdateDetectorDistance")
        self._currentDistance = value  # self.detector_distance.res2dist(value)

    def moveGuillotine(self, state):
        if state == "Transfer":
            self.goToSecurityDistance()
        if state == "Collect":
            HWR.beamline.detector.distance.set_value(180)

    def updateGuillotine(self, value):
        # if open door close guillotine but test distance
        # if distance security ok else move detector to security distance
        # wait until distance is reached
        # if self.pss.getWagoState() != "ready":

        if not value:
            if self.checkDistance():
                self._Insert()
            else:
                self.goToSecurityDistance()
                # self.detector_distance.set_value(self._d_home)
                # time.sleep(1.0)# wait distance minimum to insert guillotine
                # self._Insert()

    def modeCollect(self):
        currentDistance = self._currentDistance
        logging.info(
            "PX2Guillotine - setting gonio currentPosition is   %s" % currentDistance
        )
        if self.isInsert():
            if not self.checkDistance():
                HWR.beamline.detector.distance.set_value(self._d_security)
                time.sleep(2.0)
                while HWR.beamline.detector.distance.motorIsMoving():
                    time.sleep(0.5)
                self._Extract()
                time.sleep(0.2)
                HWR.beamline.detector.distance.set_value(currentDistance)
                time.sleep(2.0)
                while HWR.beamline.detector.distance.motorIsMoving():
                    time.sleep(0.5)
            else:
                self._Extract()
                time.sleep(0.2)

    def checkDistance(self):
        logging.info("Current distance is %s" % self._currentDistance)
        if self._currentDistance < self._d_security:
            return False
        else:
            return True

    def isInsert(self):
        if str(self.shutChannel.value) == "INSERT":
            return True
        else:
            return False

    def goToSecurityDistance(self):
        if self._currentDistance < self._d_home:
            HWR.beamline.detector.distance.set_value(self._d_home)
        if str(self.shutChannel.value) == "EXTRACT":
            self._Insert()
        while HWR.beamline.detector.distance.motorIsMoving():
            time.sleep(0.5)

    def isShutterOk(self):
        return not self.getShutterState() in (
            "OFF",
            "UNKNOWN",
            "MOVING",
            "FAULT",
            "INSERT",
            "EXTRACT",
            "INIT",
            "DISABLED",
            "ERROR",
            "ALARM",
            "STANDBY",
        )

    def openShutter(self):
        logging.info("Guillotine extract")
        # if self.checkDistance():
        self._Extract()
        #    return
        logging.getLogger("user_level_log").error(
            " Detector is too closed to the gonio Guillotine couldn't be moved"
        )

    def closeShutter(self):
        logging.info("Guillotine insert")
        # if self.checkDistance():
        self._Insert()
        #    return
        logging.getLogger("user_level_log").error(
            " Detector is too closed to the gonio Guillotine couldn't be moved"
        )

    def setIn(self):
        self._Insert()

    def setOut(self):
        self._Extract()


def test_hwo(hwo):
    hwo.openShutter()
