"""Class to search for all spec motors

template:
  <equipment class="MotorList">
    <specversion>spec host:spec name</specversion>
  </equipment>
"""

import logging
from HardwareRepository.BaseHardwareObjects import Equipment
import HardwareRepository.HardwareObjects.SpecMotor
from SpecClient_gevent import SpecConnectionsManager, SpecEventsDispatcher, SpecCommand
import types


class MotorList(Equipment):
    def init(self):
        self.allMotors = None
        self.motorListMacro = None
        self.gettingMotors = None
        try:
            self.specConnection = SpecConnectionsManager.SpecConnectionsManager().getConnection(
                self.specversion
            )
        except AttributeError:
            self.specConnection = None
            logging.getLogger("HWR").error("MotorList: you must specify a spec version")
        else:
            SpecEventsDispatcher.connect(
                self.specConnection, "connected", self.sConnected
            )
            SpecEventsDispatcher.connect(
                self.specConnection, "disconnected", self.sDisconnected
            )
            if self.isConnected():
                self.sConnected()

    def getMotorListFromSpec(self):
        return self.getMotorList()

    def getMotorList(self):
        return self.motorListMacro(wait=True, timeout=3)

    def sConnected(self):
        self.allMotors = None
        speccommand = SpecCommand.SpecCommand("_ho_MotorList", self.specConnection)
        speccommand.executeCommand(
            "def _ho_MotorList() '{local md[]; for (i=0; i<MOTORS; i++) {md[motor_mne(i)]=motor_name(i)}; return md}'",
            wait=True,
        )
        self.addCommand(
            {"name": "MotorListMacro", "type": "spec", "version": self.specversion},
            "_ho_MotorList()",
        )
        self.motorListMacro = self.getCommandObject("MotorListMacro")
        self.emit("connected", ())
        self.emit("motorListChanged", (self.specversion, self.getMotorList()))

    def isConnected(self):
        return self.specConnection is not None and self.specConnection.isSpecConnected()

    def sDisconnected(self):
        self.emit("motorListChanged", (self.specversion, {}))
        self.emit("disconnected", ())

    def getSpecVersion(self):
        try:
            ver = self.specversion
        except AttributeError:
            ver = None
        return ver
