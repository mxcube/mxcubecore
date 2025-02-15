# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Oxford Cryostream, controlled by bliss.
Example xml_ configuration:

.. code-block:: xml

 <object class="ESRF.OxfordCryostream">
   <username>Cryostream</username>
   <object role="controller" href="/bliss"/>
   <cryostat>cryostream</cryostat>
   <interval>120</interval>
   <object role="monitor_temperature" href="/monitor_temperature"/>
 </object>
"""

import logging
import sys

from gevent import (
    Timeout,
    sleep,
    spawn,
)

from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator

CRYO_STATUS = ["OFF", "SATURATED", "READY", "WARNING", "FROZEN", "UNKNOWN"]
PHASE_ACTION = {
    "RAMP": "ramp",
    "COOL": "cool",
    "HOLD": "hold",
    "PLAT": "plat",
    "PURGE": "purge",
    "END": "end",
}


class OxfordCryostream(AbstractActuator):
    """Control of the Oxford Cryostream model 700, 800 and 1000"""

    def __init__(self, name):
        super().__init__(name)

        self.temp = None
        self.temp_threshold = None
        self._monitor_obj = None
        self._timeout = 5  # [s]
        self._hw_ctrl = None
        self.ctrl = None
        self.interval = None

    def _do_polling(self):
        """Do endless polling with predefined interval"""
        while True:
            try:
                self.force_emit_signals()
            except Exception:
                sys.excepthook(*sys.exc_info())
            sleep(self.interval)

    def init(self):
        """Initialisation"""
        controller = self.get_object_by_role("controller")
        cryostat = self.get_property("cryostat")
        self.interval = self.get_property("interval", 10)
        try:
            self.ctrl = getattr(controller, cryostat)
            spawn(self._do_polling)
            self._hw_ctrl = self.ctrl.controller._hw_controller
        except AttributeError as err:
            raise RuntimeError("Cannot use cryostream") from err

        self._monitor_obj = self.get_object_by_role("monitor_temperature")
        self.temp_threshold = self.get_property("temperature_threshold", 0.0)

    def force_emit_signals(self):
        """Forces to emit all signals."""
        self.emit("valueChanged", (self.get_value(),))
        self.emit("stateChanged", (self.get_state(),))

    def get_temperature(self):
        """Read the temperature.
        Returns:
            (float): The temperature [deg K]
        """
        try:
            return self.ctrl.input.read()
        except Exception:
            # try to read again
            temp = self.ctrl.input.read()
            if temp is None:
                return 9999.0
        return temp

    def get_value(self):
        return self.get_temperature()

    def _set_value(self, value=None):
        """Define the setpoint.
        Args:
           value(float): target temperature [deg K]
        """
        if value is not None:
            self.ctrl.setpoint = value

    def rampstate(self):
        """Read the state of the ramping.
        Returns:
            (str): Ramping state.
        """
        return self.ctrl.is_ramping()

    def start_action(self, phase="RAMP", target=None, rate=None):
        """Run phase action action.
        Args:
            phase(str): The phase action. Default value - RAMP
            target(float): Target temperature.
            rate:(float): Ramp rate.
        """
        if phase in PHASE_ACTION:
            action = getattr(self._hw_ctrl, PHASE_ACTION[phase])
            if rate:
                action(target, rate=rate)
            elif target:
                action(target)
            else:
                action()

    def stop_action(self, phase="HOLD"):
        """Stop action.
        Args:
            phase(str): Phase action.
        """
        if phase in PHASE_ACTION:
            getattr(self._hw_ctrl, PHASE_ACTION[phase])

    def pause(self, execute=True):
        """Pause the ramping.
        Args:
            execute(bool): True to pause, False to resume.
        """
        if execute:
            self._hw_ctrl.pause()
        else:
            self._hw_ctrl.resume()

    def get_specific_state(self):
        """Read the state of the controller.
        Returns:
            (str): The state.
        """
        try:
            return self._hw_ctrl.read_run_mode().upper()
        except (AttributeError, TypeError):
            return "UNKNOWN"

    def get_static_parameters(self):
        """Get predefined parameters.
        Returns:
            {list): Predefimed parameters.
        """
        return ["oxford", "K", "hour"]

    def get_params(self):
        """Read from the controller.
        Returns:
            (list): [target_temperature, ramp_rate, phase, run_mode]
        """
        target_temperature = self.ctrl.setpoint
        ramp_rate = self.ctrl.ramprate
        phase = self._hw_ctrl.read_phase().upper()
        run_mode = self._hw_ctrl.read_run_mode()
        self.temp = self.ctrl.input.read()
        return [target_temperature, ramp_rate, phase, run_mode]

    def check_temperature(self, threshold=None):
        """Check if the temperature is under the threshold.
        Args:
            threshold (float): Temperature threshold (optional)
        Returns:
            (bool): True if under the threshold, False otherwise.
        """
        threshold = threshold or self.temp_threshold
        logging.getLogger("user_level_log").info("Cryo temperature reading ...")
        cryo_temp = self.get_value()
        if cryo_temp > threshold:
            logging.getLogger("user_level_log").info("Cryo temperature too high ...")
            return False
        return True

    def wait_temperature(self, threshold=None, timeout=None):
        """Wait until the temperature is under the threshold.
        Args:
            threshold (float): Temperature threshold (optional)
            timeout (float): optional - timeout [s],
                             If timeout == 0: return at once and do not wait
                                              (default);
                             if timeout is None: wait forever.
        """
        if self._monitor_obj:
            try:
                check = self._monitor_obj.get_value().value
            except AttributeError:
                check = False
            if check is True:
                threshold = threshold or self.temp_threshold
                timeout = timeout or self._timeout
                with Timeout(timeout, RuntimeError("Temperature timeout")):
                    while not self.check_temperature(threshold=threshold):
                        sleep(0.5)
