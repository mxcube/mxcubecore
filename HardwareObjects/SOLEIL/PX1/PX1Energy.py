# from qt import *

from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.HardwareObjects.abstract.AbstractEnergy import AbstractEnergy

from HardwareRepository.Command.Tango import DeviceProxy

import logging
import os
import time


class PX1Energy(Device, AbstractEnergy):

    energy_state = {
        "ALARM": "error",
        "FAULT": "error",
        "RUNNING": "moving",
        "MOVING": "moving",
        "STANDBY": "ready",
        "DISABLE": "error",
        "UNKNOWN": "unknown",
        "EXTRACT": "outlimits",
    }

    def init(self):

        self.moving = False

        self.doBacklashCompensation = False

        self.current_energy = None
        self.current_state = None

        try:
            self.monodevice = DeviceProxy(self.get_property("mono_device"))
        except Exception:
            self.errorDeviceInstance(self.get_property("mono_device"))

        # Nom du device bivu (Energy to gap) : necessaire pour amelioration du
        # positionnement de l'onduleur (Backlash)
        self.und_device = DeviceProxy(self.get_property("undulator_device"))
        self.doBacklashCompensation = self.get_property("backlash")

        # parameters for polling
        self.is_connected()

        self.energy_chan = self.get_channel_object("energy")
        self.energy_chan.connect_signal("update", self.energyChanged)

        self.stop_cmd = self.get_command_object("stop")

        self.state_chan = self.get_channel_object("state")
        self.state_chan.connect_signal("update", self.stateChanged)

    def connect_notify(self, signal):
        if signal == "energyChanged":
            logging.getLogger("HWR").debug(
                "PX1Energy. connect_notify. sending energy value %s" % self.get_value()
            )
            self.energyChanged(self.get_energy())

        if signal == "stateChanged":
            logging.getLogger("HWR").debug(
                "PX1Energy. connect_notify. sending state value %s" % self.get_state()
            )
            self.stateChanged(self.get_state())

        self.set_is_ready(True)

    def stateChanged(self, value):
        str_state = str(value)
        if str_state == "MOVING":
            self.moveEnergyCmdStarted()

        if self.current_state == "MOVING" or self.moving == True:
            if str_state != "MOVING":
                self.moveEnergyCmdFinished()

        self.current_state = str_state
        self.emit("stateChanged", self.energy_state[str_state])

    # function called during polling
    def energyChanged(self, value):

        if (
            self.current_energy is not None
            and abs(self.current_energy - value) < 0.0001
        ):
            return

        self.current_energy = value

        wav = self.get_wavelength()
        if wav is not None:
            self.emit("energyChanged", (value, wav))

    def isSpecConnected(self):
        return True

    def is_connected(self):
        return True

    def sConnected(self):
        self.emit("connected", ())

    def sDisconnected(self):
        self.emit("disconnected", ())

    def isDisconnected(self):
        return True

    def get_value(self):
        return self.energy_chan.get_value()

    def get_state(self):
        return str(self.state_chan.get_value())

    def getEnergyComputedFromCurrentGap(self):
        return self.und_device.energy

    def getCurrentUndulatorGap(self):
        return self.und_device.gap

    def get_wavelength(self):
        return self.monodevice.read_attribute("lambda").value

    def get_wavelength(self):
        return self.get_wavelength()

    def get_limits(self):
        chan_info = self.energy_chan.getInfo()
        return (float(chan_info.min_value), float(chan_info.max_value))

    def get_wavelength_limits(self):
        energy_min, energy_max = self.get_limits()

        # max is min and min is max
        max_lambda = self.energy_to_lambda(energy_min)
        min_lambda = self.energy_to_lambda(energy_max)

        return (min_lambda, max_lambda)

    def energy_to_lambda(self, value):
        # conversion is done by mono device
        self.monodevice.simEnergy = value
        return self.monodevice.simLambda

    def lambda_to_energy(self, value):
        # conversion is done by mono device
        self.monodevice.simLambda = value
        return self.monodevice.simEnergy

    def set_value(self, value, wait=False):
        value = float(value)

        backlash = 0.1  # en mm
        gaplimite = 5.5  # en mm

        if self.get_state() != "MOVING":
            if self.doBacklashCompensation:
                try:
                    # Recuperation de la valeur de gap correspondant a l'energie souhaitee
                    # self.und_device.autoApplyComputedParameters = False
                    self.und_device.energy = value
                    newgap = self.und_device.computedGap
                    actualgap = self.und_device.gap

                    #                    self.und_device.autoApplyComputedParameters = True

                    while str(self.und_device.State()) == "MOVING":
                        time.sleep(0.2)

                    # On applique le backlash que si on doit descendre en gap
                    if newgap < actualgap + backlash:
                        # Envoi a un gap juste en dessous (backlash)
                        if newgap - backlash > gaplimite:
                            self.und_device.gap = newgap - backlash
                            while str(self.und_device.State()) == "MOVING":
                                time.sleep(0.2)

                            self.energy_chan.set_value(value)
                        else:
                            self.und_device.gap = gaplimite
                            self.und_device.gap = newgap + backlash
                        time.sleep(1)
                except Exception:
                    logging.getLogger("HWR").error(
                        "%s: Cannot move undulator U20 : State device = %s",
                        self.name(),
                        str(self.und_device.State()),
                    )

            try:
                self.energy_chan.set_value(value)
                return value
            except Exception:
                logging.getLogger("HWR").error(
                    "%s: Cannot move Energy : State device = %s",
                    self.name(),
                    self.get_state(),
                )

        else:
            logging.getLogger("HWR").error(
                "%s: Cannot move Energy : State device = %s",
                self.name(),
                self.get_state(),
            )

    def set_wavelength(self, value, wait=False):
        egy_value = self.lambda_to_energy(float(value))
        logging.getLogger("HWR").debug(
            "%s: Moving wavelength to : %s (egy to %s" % (self.name(), value, egy_value)
        )
        self.set_valuey(egy_value)
        return value

    def cancelMoveEnergy(self):
        self.stop_cmd()
        self.moving = False

    def energyLimitsChanged(self, limits):
        egy_min, egy_max = limits

        lambda_min = self.energy_to_lambda(egy_min)
        lambda_max = self.energy_to_lambda(egy_max)

        wav_limits = (lambda_min, lambda_max)

        self.emit("energyLimitsChanged", (limits,))

        if None not in wav_limits:
            self.emit("wavelengthLimitsChanged", (wav_limits,))
        else:
            self.emit("wavelengthLimitsChanged", (None,))

    def moveEnergyCmdReady(self):
        if not self.moving:
            self.emit("moveEnergyReady", (True,))

    def moveEnergyCmdNotReady(self):
        if not self.moving:
            self.emit("moveEnergyReady", (False,))

    def moveEnergyCmdStarted(self):
        self.moving = True
        self.emit("moveEnergyStarted", ())

    def moveEnergyCmdFailed(self):
        self.moving = False
        self.emit("moveEnergyFailed", ())

    def moveEnergyCmdAborted(self):
        self.moving = False

    def moveEnergyCmdFinished(self):
        self.moving = False
        self.emit("moveEnergyFinished", ())

    def getPreviousResolution(self):
        return (None, None)

    def restoreResolution(self):
        return (False, "Resolution motor not defined")


def test_hwo(hwo):
    print(hwo.get_value())
    print(hwo.get_wavelength())
    print(hwo.get_limits())
    print(hwo.getCurrentUndulatorGap())
