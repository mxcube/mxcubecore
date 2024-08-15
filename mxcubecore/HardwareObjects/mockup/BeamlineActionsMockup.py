from typing_extensions import Literal

from pydantic import BaseModel, Field
from mxcubecore.TaskUtils import task
from mxcubecore.CommandContainer import CommandObject
from mxcubecore.HardwareObjects.BeamlineActions import (
    BeamlineActions,
    ControllerCommand,
    AnnotatedCommand,
)
from mxcubecore.utils.conversion import camel_to_snake

import gevent
import logging


class SimpleFloat(BaseModel):
    exp_time: float = Field(100e-6, gt=0, lt=10, description="(s)")


class StringLiteral(BaseModel):
    phase: Literal["Centring", "DataCollection", "BeamLocation", "Transfer"] = Field(1)


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


class Anneal2(AnnotatedCommand):
    def __init__(self, *args):
        super().__init__(*args)

    def anneal2(self, data: SimpleFloat) -> None:
        logging.getLogger("user_level_log").info(
            f"Annealing for {data.exp_time} seconds"
        )
        gevent.sleep(data.exp_time)


class QuickRealign2(AnnotatedCommand):
    def __init__(self, *args):
        super().__init__(*args)

    def quick_realign2(self) -> None:
        for i in range(10):
            gevent.sleep(1)
            logging.getLogger("user_level_log").info("%d, sleeping for 1 second", i + 1)


class ComboTest2(AnnotatedCommand):
    def __init__(self, *args):
        super().__init__(*args)

    def combo_test2(self, data: StringLiteral) -> None:
        logging.getLogger("user_level_log").info(f"Selected {data.phase}")


class BeamlineActionsMockup(BeamlineActions):
    pass
