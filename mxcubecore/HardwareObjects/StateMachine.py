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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import logging
import time
from datetime import datetime

import yaml

from mxcubecore.BaseHardwareObjects import HardwareObject

__author__ = "EMBL Hamburg"
__credits__ = ["MXCuBE collaboration"]
__version__ = "2.3."


class StateMachine(HardwareObject):
    """Finite State Machine (FSM) is a mathematical model of a closed or
    opened loop discreet-event systems with well defined state.
    It is wildly used to define functioning system and control their
    execution. In the case of MX beamlines and MXCuBE FSM represents
    different state where certain action from a user is requested.
    It is possible to describe a sequence of user actions as a discreet
    state that are logically connected.
    For example, each MX experiment requires a crystal to be mounted on a
    goniostat. If not crystal is mounted then it makes no sense to
    continue an experiment.
    The actual transition logic is implemented in the update_fsm_state()
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.state_list = []
        self.condition_list = None
        self.transition_list = None
        self.current_state = None
        self.previous_state = ""
        self.history_state_list = []

    def init(self):
        with open(self.get_property("structure_file"), "r") as stream:
            data_loaded = yaml.load(stream)

        self.state_list = data_loaded["states"]
        self.condition_list = data_loaded["conditions"]
        self.transition_list = data_loaded["transitions"]
        self.current_state = data_loaded["initial_state"]
        self.previous_state = data_loaded["initial_state"]

        for condition in self.condition_list:
            condition["value"] = False
            if "desc" not in condition:
                condition["desc"] = condition["name"].title().replace("_", " ")

        for transition in self.transition_list:
            if not self.get_state_by_name(transition["source"]):
                logging.getLogger("HWR").error(
                    "Transition %s " % str(transition)
                    + "has a none existing source state: %s" % transition["source"]
                )
            if not self.get_state_by_name(transition["dest"]):
                logging.getLogger("HWR").error(
                    "Transition %s " % str(transition)
                    + "has a none existing destination state: %s" % transition["dest"]
                )

            if "conditions_true" not in transition:
                transition["conditions_true"] = []
            if "conditions_false" not in transition:
                transition["conditions_false"] = []
            if "conditions_false_or" not in transition:
                transition["conditions_false_or"] = []

            for condition_name in transition["conditions_true"]:
                if not self.get_condition_by_name(condition_name):
                    logging.getLogger("HWR").error(
                        "Transition %s " % str(transition)
                        + "has a none existing condition: %s" % condition_name
                    )
            for condition_name in transition["conditions_false"]:
                if not self.get_condition_by_name(condition_name):
                    logging.getLogger("HWR").error(
                        "Transition %s " % str(transition)
                        + "has a none existing condition: %s" % condition_name
                    )
            for condition_name in transition["conditions_false_or"]:
                if not self.get_condition_by_name(condition_name):
                    logging.getLogger("HWR").error(
                        "Transition %s " % str(transition)
                        + "has a none existing condition: %s" % condition_name
                    )

        self.update_fsm_state()

        self.bl_setup_hwobj = self.get_object_by_role("beamline_setup")
        for hwobj_name in dir(self.bl_setup_hwobj):
            if hwobj_name.endswith("hwobj"):
                # logging.getLogger("HWR").debug(\
                #     "StateMachine: Attaching hwobj: %s " % hwobj_name)
                self.connect(
                    getattr(self.bl_setup_hwobj, hwobj_name),
                    "fsmConditionChanged",
                    self.condition_changed,
                )
                getattr(self.bl_setup_hwobj, hwobj_name).re_emit_values()

    def get_state_by_name(self, state_name):
        for state in self.state_list:
            if state["name"] == state_name:
                return state

    def get_condition_by_name(self, condition_name):
        for condition in self.condition_list:
            if condition["name"] == condition_name:
                return condition

    def condition_changed(self, condition_name, value):
        """Event when condition of a hardware object has been changed"""

        condition = self.get_condition_by_name(condition_name)
        if condition:
            # logging.getLogger("HWR").debug(\
            #  "StateMachine: condition '%s' changed to '%s'" \
            #   % (condition_name, value))

            if condition["value"] != value:
                condition["value"] = value
                self.emit("conditionChanged", self.condition_list)
                self.update_fsm_state()
        else:
            logging.getLogger("HWR").debug(
                "StateMachine: condition '%s' not in the condition list"
                % condition_name
            )

    def update_fsm_state(self):
        """Updates state machine
        We look at the current state and available transitions from it
        If all conditions of a transition is met then the tranition is
        executed and signal is emitted.
        """
        for transition in self.transition_list:
            if transition["source"] == self.current_state:
                allow_transition = True
                for cond_name in transition["conditions_true"]:
                    cond = self.get_condition_by_name(cond_name)
                    if cond["value"] is False:
                        allow_transition = False
                for cond_name in transition["conditions_false"]:
                    cond = self.get_condition_by_name(cond_name)
                    if cond["value"] is True:
                        allow_transition = False
                for cond_name in transition["conditions_false_or"]:
                    cond = self.get_condition_by_name(cond_name)
                    if cond["value"] is False:
                        allow_transition = True

                if allow_transition:
                    self.current_state = transition["dest"]
                    break

        if self.previous_state != self.current_state:
            if self.history_state_list:
                self.history_state_list[-1]["end_time"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                self.history_state_list[-1]["total_time"] = str(
                    datetime.strptime(
                        self.history_state_list[-1]["end_time"], "%Y-%m-%d %H:%M:%S"
                    )
                    - datetime.strptime(
                        self.history_state_list[-1]["start_time"], "%Y-%m-%d %H:%M:%S"
                    )
                )

            history_state_item = {
                "current_state": self.current_state,
                "previous_state": self.previous_state,
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": "... ",
                "total_time": "",
            }
            self.history_state_list.append(history_state_item)
            self.previous_state = self.current_state
            logging.getLogger("HWR").debug(
                "StateMachine: current state " + "changed to : %s" % self.current_state
            )
            self.emit("stateChanged", self.history_state_list)

            self.update_fsm_state()

    def get_condition_list(self):
        """Returns list of conditions"""
        return self.condition_list

    def get_state_list(self):
        """Returns list of available state"""
        return self.state_list

    def get_transition_list(self):
        """Returns list of available transitions"""
        return self.transition_list

    def re_emit_values(self):
        """Reemits signals"""

        if len(self.history_state_list):
            self.emit("stateChanged", (self.history_state_list))
