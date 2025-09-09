import typing
import enum

from mxcubecore.TaskUtils import task
from mxcubecore.CommandContainer import CommandObject
from mxcubecore.HardwareObjects.BeamlineActions import (
    BeamlineActions,
    ControllerCommand,
    AnnotatedCommand,
)
from mxcubecore.utils.conversion import camel_to_snake
from mxcubecore import HardwareRepository as HWR

import gevent
import logging


class EnumArg(str, enum.Enum):
    centring = "Centring"
    data_collection = "DataCollection"
    beam_location = "BeamLocation"
    transfer = "Transfer"
    unknown = "Unknown"


class SimulatedAction:
    def __call__(self, *args, **kw):
        gevent.sleep(3)
        return args


class SimulatedActionError:
    def __call__(self, *args, **kw):
        raise RuntimeError("Simulated error")


class LongSimulatedAction:
    def __call__(self, *args, **kw):
        for i in range(10):
            gevent.sleep(1)
            logging.getLogger("user_level_log").info("%d, sleeping for 1 second", i + 1)

        return args


class Arg(typing.NamedTuple):
    name: str
    unit: str
    alias: str


# class Anneal2(AnnotatedCommand):
#     def __init__(self, *args):
#         super().__init__(*args)

#     # @argument(ArgMeta("time", "s", "time"))
#     def anneal2(self, time: float) -> None:
#         print("ANNEAL")
#         gevent.sleep(float(time))

# class Anneal2(AnnotatedCommand):
#     def __init__(self,*args):
#         super().__init__(*args)
#     def anneal2(self, data: float) -> None:
#         logging.getLogger("user_level_log").info(
#             f"Annealing for {data.exp_time} seconds"
#         )
#         gevent.sleep(data.exp_time)

class Anneal2(AnnotatedCommand):
    def __init__(self,*args):
        super().__init__(*args)
        self.md2 = HWR.beamline.diffractometer
        # import pdb
        # pdb.set_trace()
        if not self.md2:
            logging.getLogger('HWR').error("MD2 hardware object not found")
            print(f"Current state: {md2.rexPosition.get_value()}")
        self._stop_event = None
        self.safe_position = "PARK"
        self.cryo_position = "CRYO_IN"
    
    def anneal2(self, time: float) -> None:
        """执行退火：切换到 PARK，等待时间，切换回 CRYO_IN"""
        if time < 0.1 or time > 60:
            raise ValueError("Time must be between 0.1 and 60 seconds")

        self._stop_event = gevent.event.Event()
        try:
            # 检查当前状态
            current_state = self.get_cold_head_state()
            logging.getLogger("user_level_log").info("Current cold head state: %s", current_state)

            # 切换到 PARK
            self.switch_cold_head(self.safe_position)

            # 等待指定时间或停止信号
            logging.getLogger("user_level_log").info("Annealing for %s seconds", time)
            self._stop_event.wait(timeout=time)

            # 切换回 CRYO_IN
            self.switch_cold_head(self.cryo_position)

            logging.getLogger("user_level_log").info("Annealing completed")
        except Exception as e:
            logging.getLogger("user_level_log").error("Annealing failed: %s", str(e))
            # 确保冷头回到 CRYO_IN
            try:
                logging.getLogger("user_level_log").info("Switching cold head back to %s state", self.cryo_position)
                self.switch_cold_head(self.cryo_position)
            except Exception as e2:
                logging.getLogger("user_level_log").error("Failed to switch cold head back: %s", str(e2))
            raise
    
    def get_cold_head_state(self):
        if not self.md2 or not hasattr(self.md2,'rexPosition'):
            raise RuntimeError("MD2 rexPosition channnel not available")
        return self.md2.rexPosition.get_value()
    
    def switch_cold_head(self, position):
        """切换冷头状态"""
        valid_states = ["CRYO_IN", "CRYO_BACK", "PARK", "HUMIDIFIER"]
        if position not in valid_states:
            raise ValueError(f"Invalid cold head state. Must be one of {valid_states}.")

        if not self.md2 or not hasattr(self.md2, 'rexPosition'):
            raise RuntimeError("MD2 rexPosition channel not available")

        current_state = self.get_cold_head_state()
        if current_state == position:
            if not hasattr(self, 'last_logged_cold_head_state') or self.last_logged_cold_head_state != position:
                logging.getLogger("user_level_log").info("Cold head is already in %s state", position)
                self.last_logged_cold_head_state = position
            return

        logging.getLogger("user_level_log").info("Switching cold head to %s state", position)
        try:
            self.md2.rexPosition.set_value(position)
            self.md2._wait_ready(timeout=30)
            self.last_logged_cold_head_state = position
        except Exception as e:
            logging.getLogger("user_level_log").error("Failed to switch cold head to %s: %s", position, str(e))
            raise
        
    def stop(self):
        """停止退火，立即切换到 CRYO_IN"""
        if self._stop_event:
            self._stop_event.set()
            try:
                logging.getLogger("user_level_log").info("Stopping annealing, switching cold head to %s state", self.cryo_position)
                self.switch_cold_head(self.cryo_position)
            except Exception as e:
                logging.getLogger("user_level_log").error("Failed to switch cold head back: %s", str(e))


class QuickRealign2(AnnotatedCommand):
    def __init__(self, *args):
        super().__init__(*args)

    def quick_realign2(self) -> None:
        print("REALIGN")


class ComboTest2(AnnotatedCommand):
    def __init__(self, *args):
        super().__init__(*args)

    def combo_test2(self, combo_arg: EnumArg) -> None:
        print("COMBO")


class BeamlineActionsMockup(BeamlineActions):
    def __init__(self, *args):
        super().__init__(*args)