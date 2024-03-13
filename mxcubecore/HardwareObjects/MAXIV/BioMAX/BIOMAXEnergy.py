from typing import Iterable
import sys
import time
import logging
import math
import numpy as np
from collections import deque
import gevent
from gevent import Timeout
import PyTango
from mxcubecore.TaskUtils import *
from mxcubecore.HardwareObjects import Energy
from mxcubecore.utils.units import ev_to_kev
from mxcubecore.HardwareObjects.abstract.AbstractEnergy import AbstractEnergy


def _ev_vals_to_kev(ev_vals: Iterable[float]) -> tuple[float]:
    """
    convert all values from eV to KeV
    """
    return tuple(ev_to_kev(ev) for ev in ev_vals)


class BIOMAXEnergy(AbstractEnergy):
    def __init__(self, *args, **kwargs):
        AbstractEnergy.__init__(self, *args, **kwargs)

    def init(self):
        super().init()
        self.moving = None
        self.default_en = None
        # To check beam stability
        self.total_counts = 0.0
        # This is the minimum number of counts on the beam detector. If below, there is no beam
        self.min_total_counts = 0.0000001
        # How many measurements of the beam position to average (to decrease the effect of noise)
        self.N = 4
        self.counts_now = deque(maxlen=self.N)
        # This is how much we allow the beam position to deviate (in microns)
        try:
            self.energy_motor = self.get_object_by_role("energy")
        except KeyError:
            logging.getLogger("HWR").warning("Energy: error initializing energy motor")

        if self.energy_motor is not None:
            self.energy_motor.connect("valueChanged", self.energy_position_changed)
            self.energy_motor.connect("stateChanged", self.energy_state_changed)

        self.get_energy_limits()

    def energy_position_changed(self, pos):
        wl = 12.3984 / pos
        if wl:
            self.emit("energyChanged", (pos / 1000, wl * 1000))
            self.emit("valueChanged", (pos / 1000,))

    def energy_state_changed(self, state):
        self.emit("stateChanged", (state))

    def get_value(self):
        return ev_to_kev(self.energy_motor.get_value())

    def get_current_energy(self):
        if self.energy_motor is not None:
            try:
                return self.get_value()
            except:
                logging.getLogger("HWR").exception(
                    "EnergyHO: could not read current energy"
                )
                return None
        return self.default_en

    def get_current_wavelength(self):
        current_en = self.get_current_energy()
        if current_en:
            curr_wave = 12.3984 / current_en
            return curr_wave
        return None

    def get_energy_limits(self):
        if self.energy_motor is not None:
            try:
                self._nominal_limits = _ev_vals_to_kev(self.energy_motor.get_limits())
            except:
                logging.getLogger("HWR").exception(
                    "EnergyHO: could not read energy motor limits"
                )

    def start_move_energy(self, value, wait=True, check_beam=True):
        try:
            value = float(value)
        except (TypeError, ValueError) as diag:
            logging.getLogger("user_level_log").error(
                "Energy: invalid energy (%s)" % value
            )
            return False

        current_en = self.get_current_energy()
        if current_en:
            if math.fabs(value - current_en) < 0.001:
                self.moving = False
                self.emit("moveEnergyFinished", ())
                logging.getLogger("user_level_log").debug(
                    "Energy: already at %g, not moving", current_en
                )
                return
        if self.check_limits(value) is False:
            return False

        self.moving = True
        self.emit("moveEnergyStarted", ())

        def change_egy():
            try:
                self.move_energy(value, wait=True, check_beam_end=check_beam)
            except:
                sys.excepthook(*sys.exc_info())
                self.moving = False
                self.emit("moveEnergyFailed", ())
            else:
                self.moving = False
                self.emit("moveEnergyFinished", ())

        if wait:
            change_egy()
        else:
            gevent.spawn(change_egy)

    def check_limits(self, value):
        limits = self.get_limits()
        if value >= limits[0] and value <= limits[1]:
            return True
        logging.getLogger("user_level_log").info("Requested value is out of limits")
        return False

    def move_energy(self, energy, wait=True, check_beam_end=True):
        current_en = self.get_current_energy()
        pos = math.fabs(current_en - energy)
        if pos < 0.001:
            logging.getLogger("user_level_log").debug(
                "Energy: already at %g, not moving", energy
            )
        else:
            logging.getLogger("user_level_log").debug(
                "Energy: moving energy to %g", energy
            )
            # self.energy_motor.move(energy * 1000)
            self.energy_motor._set_value(energy * 1000)
            self.energy_motor.wait_end_of_move(800)
            if check_beam_end:
                try:
                    self.check_beam()
                except RuntimeError as ex:
                    logging.getLogger("user_level_log").error(
                        "Check beam error: %s" % ex
                    )
                    logging.getLogger("HWR").error("Check beam error: %s" % ex)
                except Exception as ex:
                    logging.getLogger("HWR").warning("Check beam exception: %s" % ex)
                    logging.getLogger("user_level_log").error(
                        "Check beam exception: %s" % ex
                    )

    def sync_move(self, position, timeout=None):
        """
        Deprecated method - corresponds to move until move finished.
        """
        self.energy_motor.set_value(position)
        try:
            with Timeout(timeout):
                time.sleep(0.1)
                while self.is_moving():
                    time.sleep(0.1)
        except:
            raise Timeout

    def cancel_move_energy(self):
        logging.getLogger("user_level_log").info("Cancel Energy move")
        logging.getLogger("HWR").info("Cancel Energy move")
        self.energy_motor.stop()

    def check_beam(self):
        # check if mirror piezo feedback is running
        pidx = PyTango.DeviceProxy("b311a/ctl/pid-01")
        pidy = PyTango.DeviceProxy("b311a/ctl/pid-02")

        if (
            pidx.State() != PyTango.DevState.MOVING
            and pidy.State() != PyTango.DevState.MOVING
        ):
            # If the PID loop is not running the beam alignment should be done by hand
            raise Exception("Mirror piezo PID loop not running.")

        # check presence of beam in the hutch
        xbpm = PyTango.DeviceProxy("b311a/xbpm/02")
        self.total_counts = xbpm.S
        # self.output(self.total_counts)
        # Value decreased by 3 orders of magnitude since firmware upgrade of aems
        if self.total_counts < self.min_total_counts:
            # wait a little and check again
            time.sleep(5)
            logging.getLogger("HWR").info("Checking XBPM counts again!")
            self.total_counts = xbpm.S
            if self.total_counts < self.min_total_counts:
                raise Exception(
                    "There is no beam in the BCU. Check the front end shutters, the undulator gap and the NanoBPM regulation."
                )

        # How long we check for stable beam
        timeout = 120
        waittime = 0
        countsv = xbpm.Y
        countsh = xbpm.X
        self.counts_now.clear()

        with gevent.Timeout(120, RuntimeError("The beam is not stable.")):
            while (
                self.is_good_beam(self.N, countsv) == False
                or self.is_good_beam(self.N, countsh) == False
            ):
                countsv = xbpm.Y
                countsh = xbpm.X

                gevent.sleep(1)
        logging.getLogger("user_level_log").info("Beam is stable.")
        return True

    def is_good_beam(self, N, counts):
        self.counts_now.append(counts)
        if len(self.counts_now) < N:
            return False

        avg_now = np.sum(self.counts_now) / len(self.counts_now)

        if abs(avg_now) > 1.0:
            return False

        elif self.total_counts < self.min_total_counts:
            # No beam
            return False
        else:
            return True
