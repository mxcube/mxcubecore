# -*- coding: utf-8 -*-

import time
import logging
import gevent

from HardwareRepository.Command.Tango import DeviceProxy

from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.TaskUtils import task


class EnvironmentPhase:

    TRANSFER = 0
    CENTRING = 1
    COLLECT = 2
    DEFAULT = 3
    BEAMVIEW = 4
    FLUOX = 5
    MANUALTRANSFER = 6
    INPROGRESS = 7
    VISUSAMPLE = 8

    phasedesc = {
        "TRANSFER": TRANSFER,
        "CENTRING": CENTRING,
        "COLLECT": COLLECT,
        "DEFAULT": DEFAULT,
        "BEAMVIEW": BEAMVIEW,
        "FLUOX": FLUOX,
        "MANUALTRANSFER": MANUALTRANSFER,
        "INPROGRESS": INPROGRESS,
        "VISUSAMPLE": VISUSAMPLE,
    }

    @staticmethod
    def phase(phasename):
        return EnvironmentPhase.phasedesc.get(phasename, None)


class EnvironemntState:
    UNKNOWN, ON, RUNNING, ALARM, FAULT = (0, 1, 10, 13, 14)  # Like PyTango stated

    # TangoStates = {
    #    Unknown     = 0
    #    On          = 1
    #    Loaded      = 2
    #    Loading     = 3
    #    Unloading   = 4
    #    Selecting   = 5
    #    Scanning    = 6
    #    Resetting   = 7
    #    Charging    = 8
    #    Moving      = 9
    #    Running     = 10
    #    StandBy     = 11
    #    Disabled    = 12
    #    Alarm       = 13
    #    Fault       = 14
    #    Initializing= 15
    #    Closing     = 16
    #    Off         = 17
    # }

    statedesc = {ON: "ON", RUNNING: "RUNNING", ALARM: "ALARM", FAULT: "FAULT"}

    @staticmethod
    def tostring(state):
        return SampleChangerState.statedesc.get(state, "Unknown")


class PX1Environment(Device):
    def __init__(self, name):
        Device.__init__(self, name)
        self.auth = None
        self.device = None

    def init(self):

        self.device = DeviceProxy(self.get_property("tangoname"))

        try:
            self.state_chan = self.get_channel_object("State")
            self.state_chan.connect_signal("update", self.stateChanged)

        except KeyError:
            logging.getLogger().warning("%s: cannot report State", self.name())

        try:
            self.chanAuth = self.get_channel_object("beamlineMvtAuthorized")
            self.chanAuth.connect_signal("update", self.setAuthorizationFlag)
            # state = self.state_chan.getValue()

        except KeyError:
            logging.getLogger().warning("%s: cannot report State", self.name())

        try:
            self.usingCapillaryChannel = self.get_channel_object("usingCapillary")
            self.setUsingCapillary(True)
        except BaseException:
            self.usingCapillaryChannel = None

        try:
            self.beamstopPositionChannel = self.get_channel_object("beamstopPosition")
        except BaseException:
            self.beamstopPositionChannel = None

        if self.device is not None:
            self.setIsReady(True)

            self.cmds = {
                EnvironmentPhase.TRANSFER: self.device.GoToTransfertPhase,
                EnvironmentPhase.CENTRING: self.device.GoToCentringPhase,
                EnvironmentPhase.COLLECT: self.device.GoToCollectPhase,
                EnvironmentPhase.DEFAULT: self.device.GoToDefaultPhase,
                # EnvironmentPhase.BEAMVIEW: self.device.GoToBeamViewPhase,
                EnvironmentPhase.FLUOX: self.device.GoToFluoXPhase,
                EnvironmentPhase.MANUALTRANSFER: self.device.GoToManualTransfertPhase,
                EnvironmentPhase.VISUSAMPLE: self.device.GoToVisuSamplePhase,
            }

    # ---- begin state handling
    #
    def stateChanged(self, value):
        self.emit("StateChanged", (value,))

    def get_state(self):
        state = str(self.state_chan.getValue())
        return state

    def isBusy(self, timeout=None):
        state = self.stateChan.getValue()
        return state not in [EnvironmentState.ON]

    def wait_ready(self, timeout=None):
        self._waitState(["ON"], timeout)

    def _waitState(self, states, timeout=None):
        if self.device is None:
            return

        _debut = time.time()
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            waiting = True
            while waiting:
                state = self.readState()
                if state in states:
                    waiting = False
                gevent.sleep(0.05)

    #
    # ------- end state handling
    # logging.debug("PX1environment: end _waitState in %.1f sec" % (time.time() - _debut))

    # ------- begin phase handling
    #
    def isPhaseTransfer(self):
        return self.device.readyForTransfert

    def isPhaseCollect(self):
        return self.readyForCollect()

    def isPhaseVisuSample(self):
        return self.device.readyForVisuSample

    def isPhaseFluoScan(self):
        return self.device.readyForFluoScan

    def readyForCentring(self):
        if self.device is not None:
            return self.device.readyForCentring
        else:
            return None

    def readyForCollect(self):
        if self.device is not None:
            return self.device.readyForCollect
        else:
            return None

    def readyForDefaultPosition(self):
        if self.device is not None:
            return self.device.readyForDefaultPosition
        else:
            return None

    def readyForFluoScan(self):
        if self.device is not None:
            return self.device.readyForFluoScan
        else:
            return None

    def readyForManualTransfer(self):
        if self.device is not None:
            return self.device.readyForManualTransfert
        else:
            return None

    def readyForTransfer(self):
        if self.device is not None:
            return self.device.readyForTransfert
        else:
            return None

    def readyForVisuSample(self):
        if self.device is not None:
            return self.device.readyForVisuSample
        else:
            return None

    def gotoPhase(self, phase):
        logging.debug("PX1environment.gotoPhase %s" % phase)
        cmd = self.cmds.get(phase, None)
        if cmd is not None:
            logging.debug("PX1environment.gotoPhase state %s" % self.readState())
            cmd()
        else:
            return None

    def setPhase(self, phase, timeout=120):
        self.gotoPhase(phase)
        self.waitPhase(phase, timeout)

    def readPhase(self):
        if self.device is not None:
            phasename = self.device.currentPhase
            return EnvironmentPhase.phase(phasename)
        else:
            return None

    def get_current_phase(self):
        return self.device.currentPhase

    getCurrentPhase = get_current_phase

    def getPhase(self):
        if self.device is not None:
            phasename = self.device.currentPhase
            return phasename
        else:
            return None

    def waitPhase(self, phase, timeout=None):
        if self.device is None:
            return
        logging.debug("PX1environment: start waitPhase")
        _debut = time.time()
        n = 0
        with gevent.Timeout(
            timeout, Exception("Timeout waiting for environment phase")
        ):
            waiting = True
            while waiting:
                n += 1
                _phaseread = self.readPhase()
                if phase == _phaseread:
                    waiting = False
                gevent.sleep(0.05)
        logging.debug(
            "PX1environment: end waitPhase in %.1f sec N= %d"
            % ((time.time() - _debut), n)
        )

    #
    # ------- end phase handling

    def gotoCentringPhase(self):
        if not self.readyForCentring() or self.getPhase() != "CENTRING":
            self.get_command_object("GoToCentringPhase")()
            time.sleep(0.1)

    def gotoCollectPhase(self):
        if not self.readyForCollect() or self.getPhase() != "COLLECT":
            self.get_command_object("GoToCollectPhase")()
            time.sleep(0.1)

    def gotoLoadingPhase(self):
        if not self.readyForTransfer():
            self.get_command_object("GoToTransfertPhase")()
            time.sleep(0.1)

    def gotoManualLoadingPhase(self):
        if not self.readyForTransfer():
            self.get_command_object("GoToManualTransfertPhase")()
            time.sleep(0.1)

    def gotoSampleViewPhase(self):
        if not self.readyForVisuSample():
            self.get_command_object("GoToVisuSamplePhase")()
            time.sleep(0.1)

    def gotoFluoScanPhase(self):
        if not self.readyForFluoScan():
            self.get_command_object("GoToFluoScanPhase")()
            time.sleep(0.1)

    def setAuthorizationFlag(self, value):
        # make here the logic with eventually other permits (like hardware permit)
        if value != self.auth:
            logging.getLogger("HWR").debug(
                "PX1Environment. received authorization from cryotong:  %s" % value
            )
            self.auth = value
            self.emit("operationPermitted", value)

    def getUsingCapillary(self):
        if self.usingCapillaryChannel is not None:
            return self.usingCapillaryChannel.getValue()

    def setUsingCapillary(self, value):
        self.capillary_value = value
        gevent.spawn(self._setUsingCapillary)

    @task
    def _setUsingCapillary(self):
        if self.usingCapillaryChannel is not None:
            self.usingCapillaryChannel.setValue(self.capillary_value)

    def getBeamstopPosition(self):
        if self.beamstopPositionChannel is not None:
            return self.beamstopPositionChannel.getValue()

    def setBeamstopPosition(self, value):
        self.beamstop_position = value
        gevent.spawn(self._setBeamstopPosition)

    @task
    def _setBeamstopPosition(self):
        if self.beamstopPositionChannel is not None:
            self.beamstopPositionChannel.setValue(self.beamstop_position)


def test_hwo(hwo):
    t0 = time.time()
    print("PX1 Environment (state) ", hwo.get_state())
    print("               phase is ", hwo.getCurrentPhase())
    print("        beamstop pos is ", hwo.getBeamstopPosition())

    # if not env.readyForTransfer():
    #    print "Going to transfer phase"
    #    env.setPhase(EnvironmentPhase.TRANSFER)
    #    print time.time() - t0
    # print "done"
    # env.waitPhase(EnvironmentPhase.TRANSFER)
