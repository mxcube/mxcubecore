# -*- coding: utf-8 -*-
# from SimpleDevice2c import SimpleDevice
from PyTango.gevent import DeviceProxy
import logging
import math

from mx3core.BaseHardwareObjects import Device

# from Command.Tango import TangoChannel


class PX2Attenuator(Device):
    stateAttenuator = {
        "ALARM": "error",
        "OFF": "error",
        "RUNNING": "moving",
        "MOVING": "moving",
        "STANDBY": "ready",
        "UNKNOWN": "changed",
        "EXTRACT": "outlimits",
    }

    def __init__(self, name):
        Device.__init__(self, name)

        self.labels = []
        self.attno = 0
        self.deviceOk = True
        self.nominal_value = None

    def init(self):
        #         cmdToggle = self.get_command_object('toggle')
        #         cmdToggle.connect_signal('connected', self.connected)
        #         cmdToggle.connect_signal('disconnected', self.disconnected)

        # Connect to device FP_Parser defined "tangoname" in the xml file
        try:
            # self.Attenuatordevice = SimpleDevice(self.get_property("tangoname"), verbose=False)
            self.Attenuatordevice = DeviceProxy(self.get_property("tangoname"))
        except Exception:
            self.errorDeviceInstance(self.get_property("tangoname"))

        try:
            # self.Attenuatordevice = SimpleDevice(self.get_property("tangoname"), verbose=False)
            self.Constdevice = DeviceProxy(self.get_property("tangoname_const"))
        except Exception:
            self.errorDeviceInstance(self.get_property("tangoname_const"))

        # Connect to device Primary slit horizontal defined "tangonamePs_h" in the
        # xml file
        try:
            # self.Ps_hdevice = SimpleDevice(self.get_property("tangonamePs_h"), verbose=False)
            self.Ps_hdevice = DeviceProxy(self.get_property("tangonamePs_h"))
        except Exception:
            self.errorDeviceInstance(self.get_property("tangonamePs_h"))

        # Connect to device Primary slit vertical defined "tangonamePs_v" in the
        # xml file
        try:
            # self.Ps_vdevice = SimpleDevice(self.get_property("tangonamePs_v"), verbose=False)
            self.Ps_vdevice = DeviceProxy(self.get_property("tangonamePs_v"))
        except Exception:
            self.errorDeviceInstance(self.get_property("tangonamePs_v"))

        if self.deviceOk:
            self.connected()

            self.chanAttState = self.get_channel_object("State")
            self.chanAttState.connect_signal("update", self.attStateChanged)
            self.chanAttFactor = self.get_channel_object("TrueTrans_FP")
            self.chanAttFactor.connect_signal("update", self.attFactorChanged)

    def getAtteConfig(self):
        return

    def getAttState(self):
        try:
            value1 = Ps_attenuatorPX2.stateAttenuator[self.Ps_hdevice.State().name]
            print(
                "State hslit : ",
                Ps_attenuatorPX2.stateAttenuator[self.Ps_hdevice.State().name],
            )
            value2 = Ps_attenuatorPX2.stateAttenuator[self.Ps_vdevice.State().name]
            print(
                "State vslit : ",
                Ps_attenuatorPX2.stateAttenuator[self.Ps_vdevice.State().name],
            )
            if value1 == "ready" and value2 == "ready":
                value = "ready"
            elif value1 == "error" or value2 == "error":
                value = "error"
            elif value1 == "moving" or value2 == "moving":
                value = "moving"
            elif value1 == "changed" or value == "changed":
                value = "changed"
            else:
                value = None
            logging.getLogger().debug("Attenuator state read from the device %s", value)

        except Exception:
            logging.getLogger("HWR").error(
                "%s getAttState : received value on channel is not a integer value",
                str(self.name()),
            )
            value = None
        return value

    def attStateChanged(self, channelValue):
        value = self.getAttState()
        logging.getLogger("HWR").error(
            "%s getAttState : new value is %s" % (str(self.name()), value)
        )
        self.emit("attStateChanged", (value,))

    def get_value(self):

        try:
            if (
                self.Attenuatordevice.TrueTrans_FP <= 100.0
            ):  # self.Attenuatordevice.Trans_FP  <= 100.0 :
                if self.nominal_value is not None:
                    value = self.nominal_value
                else:
                    value = float(self.Attenuatordevice.TrueTrans_FP) * 1.3587
            else:
                if self.nominal_value is not None:
                    value = self.nominal_value
                else:
                    value = float(self.Attenuatordevice.I_Trans) * 1.4646
            # Mettre une limite superieure car a une certaine ouverture de fentes on ne gagne plus rien en transmission
            # Trouver la valeur de transmission par mesure sur QBPM1 doit etre autour
            # de 120%
        except Exception:
            logging.getLogger("HWR").error(
                "%s get_value : received value on channel is not a float value",
                str(self.name()),
            )
            value = None
        return value

    def connected(self):
        self.set_is_ready(True)

    def disconnected(self):
        self.set_is_ready(False)

    def attFactorChanged(self, channelValue):
        try:
            logging.getLogger("HWR").info(
                "%s attFactorChanged : received value %s"
                % (str(self.name()), channelValue)
            )
            value = self.get_value()
        except Exception:
            logging.getLogger("HWR").error(
                "%s attFactorChanged : received value on channel is not a float value",
                str(self.name()),
            )
        else:
            logging.getLogger("HWR").info(
                "%s attFactorChanged : calculated value is %s"
                % (str(self.name()), value)
            )
            self.emit("attFactorChanged", (value,))

    def attToggleChanged(self, channelValue):
        try:
            value = int(channelValue)
        except Exception:
            logging.getLogger("HWR").error(
                "%s attToggleChanged : received value on channel is not a float value",
                str(self.name()),
            )
        else:
            self.emit("toggleFilter", (value,))

    def _set_value(self, value):
        self.nominal_value = float(value)
        try:
            if (
                self.Constdevice.FP_Area_FWHM <= 0.1
            ):  # Cas ou il n'y a pas de valeur dans le publisher PASSERELLE/CO/Primary_Slits
                logging.getLogger("HWR").error(
                    "Primary slits not correctly aligned", str(self.name())
                )
                self.Constdevice.FP_Area_FWHM = 0.5
                self.Constdevice.Ratio_FP_Gap = 0.5

            truevalue = (2.0 - math.sqrt(4 - 0.04 * value)) / 0.02
            print(" truevalue : ", truevalue)
            newGapFP_H = math.sqrt(
                (truevalue / 100.0)
                * self.Constdevice.FP_Area_FWHM
                / self.Constdevice.Ratio_FP_Gap
            )
            print(" Gap FP_H : ", newGapFP_H)
            self.Ps_hdevice.gap = newGapFP_H
            newGapFP_V = newGapFP_H * self.Constdevice.Ratio_FP_Gap
            print(" Gap FP_V : ", newGapFP_V)
            self.Ps_vdevice.gap = newGapFP_V
            # self.attFactorChanged(channelValue)
        except Exception:
            logging.getLogger("HWR").error(
                "%s set Transmission : received value on channel is not valid",
                str(self.name()),
            )
            value = None
        return value

    def toggle(self, value):
        return value

    def errorDeviceInstance(self, device):
        db = DeviceProxy("sys/database/dbds1")
        logging.getLogger().error(
            "Check Instance of Device server %s" % db.Dbget_deviceInfo(device)[1][3]
        )
        self.sDisconnected()


def test_hwo(hwo):
    print("Atten. factor", hwo.get_value())
