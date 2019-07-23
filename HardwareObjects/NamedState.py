from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Device

import logging


class NamedState(Device):
    def __init__(self, name):
        Device.__init__(self, name)
        self.stateList = []

    def _init(self):
        self.stateChan = self.getChannelObject("state")

        try:
            self.moveStateChan = self.getChannelObject("hardware_state")
        except KeyError:
            self.moveStateChan = None

        try:
            self.changeCmd = self.getCommandObject("command")
        except KeyError:
            self.changeCmd = None

        try:
            self.stateListChannel = self.getChannelObject("statelist")
        except KeyError:
            self.stateListChannel = None

        try:
            self.commandtype = self.getProperty("commandtype")
        except KeyError:
            self.commandtype = None

        self.stateChan.connectSignal("update", self.stateChanged)
        if self.moveStateChan:
            self.moveStateChan.connectSignal("update", self.hardwareStateChanged)

        Device._init(self)

    def init(self):
        self._getStateList()

    def connectNotify(self, signal):
        if signal == "stateChanged":
            self.emit(signal, (self.getState(),))

    def stateChanged(self, channelValue):
        logging.info("hw NamedState %s. got new value %s" % (self.name(), channelValue))
        self.setIsReady(True)
        self.emit("stateChanged", (self.getState(),))

    def hardwareStateChanged(self, channelValue):
        logging.info(
            "hw NamedState %s. Hardware state is now %s" % (self.name(), channelValue)
        )
        self.hdw_state = channelValue
        self.emit("hardwareStateChanged", (self.hdw_state,))

    def getStateList(self):
        return self.stateList

    def _getStateList(self):
        if self.stateListChannel is not None:
            # This is the case for ApertureDiameterList *configured as statelist
            # channel in xml
            statelist = self.stateListChannel.getValue()
            for statename in statelist:
                # cenvert in str because statename is numpy.int32 from Tango and deosn't
                self.stateList.append(str(statename))
        else:
            # This is the case where state names are listed in xml
            try:
                states = self["states"]
            except BaseException:
                logging.getLogger().error(
                    "%s does not define named states.", str(self.name())
                )
            else:
                for state in states:
                    statename = state.getProperty("name")
                    self.stateList.append(statename)

    def update_values(self):
        pass

    def getUserName(self):
        try:
            name = self.getProperty("username")
        except BaseException:
            name = None

        if name is None:
            name = ""
        return name

    def getCurrentState(self):
        return self.getState()

    def getState(self):
        try:
            stateValue = self.stateChan.getValue()
            if self.commandtype is not None and self.commandtype == "index":
                # this is the case of aperture diameters. the state channel gives only
                # the index in the list
                listvalue = self.stateList[int(stateValue)]
                return listvalue
            else:
                return stateValue
        except BaseException:
            import traceback

            logging.debug(traceback.format_exc())
            return "unknown"

    def setState(self, statename):

        self.emit("hardwareStateChanged", ("STANDBY",))
        logging.getLogger().exception(
            ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>..............changing state for %s to ws: %s."
            % (self.getUserName(), statename)
        )

        if self.commandtype == "index":
            logging.getLogger().info("   this is index mode. %s" % str(self.stateList))
            try:
                statevalue = self.stateList.index(statename)
                logging.getLogger().info(
                    "   this is index mode. setting actual value s to ws: %s."
                    % (statevalue)
                )
            except BaseException:
                logging.getLogger().exception(
                    "changing state for %s to ws: %s.failed. not such state"
                    % (self.getUserName(), statename)
                )
                self.emit("stateChanged", (self.getState(),))
                self.emit("hardwareStateChanged", ("ERROR",))
                return
        else:
            statevalue = unicode(statename)

        try:
            logging.getLogger().exception(
                "changing state for %s to ws: %s" % (self.getUserName(), statevalue)
            )
            if self.changeCmd is not None:
                logging.getLogger().exception("  - using command mode")
                self.changeCmd(statevalue)
            else:
                logging.getLogger().exception("  - using attribute mode")
                try:
                    # probleme de unicode tester en mettant un unicode
                    self.stateChan.setValue(statevalue)
                except BaseException:
                    logging.getLogger().exception("cannot write attribute")
                    self.emit("stateChanged", (self.getState(),))
                    self.emit("hardwareStateChanged", ("ERROR",))
        except BaseException:
            logging.getLogger().exception(
                "Cannot change state for %s to %s: " % (self.getUserName(), statevalue)
            )


def test():
    hwr = HardwareRepository.getHardwareRepository()
    hwr.connect()

    ap_pos = hwr.getHardwareObject("/aperture_position")
    ap_diam = hwr.getHardwareObject("/aperture_diameter")
    yag_pos = hwr.getHardwareObject("/scintillator")
    md2_phase = hwr.getHardwareObject("/md2j_phase")

    print("Aperture Position: ", ap_pos.getState())
    print("Aperture Diameter: ", ap_diam.getState())
    print("Yag Posiion: ", yag_pos.getState())
    print("MD2 Phase: ", md2_phase.getState())


if __name__ == "__main__":
    test()
